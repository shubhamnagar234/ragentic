from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import os
import shutil

from app.database import get_db
from app.dependencies import get_current_user
from app.models.source import Source
from app.models.workspace import Workspace
from app.schemas.source import SourceCreate, SourceResponse
from app.workers.ingest_tasks import ingest_source

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def verify_workspace_access(
    workspace_id: UUID,
    user_id: str,
    db: AsyncSession,
) -> Workspace:
    result = await db.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.user_id == user_id,
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    return workspace


@router.post(
    "/{workspace_id}/sources",
    response_model=SourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_source(
    workspace_id: UUID,
    payload: SourceCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(workspace_id, user_id, db)

    source = Source(
        workspace_id=workspace_id,
        source_type=payload.source_type,
        url=payload.url,
        title=payload.title,
        status="queued",
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)

    # Trigger Celery ingestion task

    try:
        ingest_source.delay(
            source_id=str(source.id),
            workspace_id=str(workspace_id),
            source_type=payload.source_type,
            url=payload.url,
        )
        print(f"[sources] ✓ Queued ingestion task for source {source.id}")
    except Exception as e:
        print(f"[sources] ✗ Failed to queue task: {e}")

    return source


@router.post(
    "/{workspace_id}/sources/upload",
    response_model=SourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_source(
    workspace_id: UUID,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(workspace_id, user_id, db)

    # Ensure uploads directory exists
    upload_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    # Save file locally
    file_path = os.path.join(upload_dir, f"{workspace_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Determine source type based on extension
    filename_lower = file.filename.lower() if file.filename else ""
    source_type = "PDF"  # Default
    if filename_lower.endswith((".mp3", ".wav", ".m4a")):
        source_type = "AUDIO"
    elif filename_lower.endswith((".mp4", ".mov")):
        source_type = "VIDEO"

    source = Source(
        workspace_id=workspace_id,
        source_type=source_type,
        url=file_path,
        title=file.filename,
        status="queued",
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)

    try:
        ingest_source.delay(
            source_id=str(source.id),
            workspace_id=str(workspace_id),
            source_type=source_type,
            url=file_path,
        )
        print(f"[sources] ✓ Queued upload task for source {source.id}")
    except Exception as e:
        print(f"[sources] ✗ Failed to queue upload task: {e}")

    return source


@router.post(
    "/{workspace_id}/sources/{source_id}/retry",
    response_model=SourceResponse,
)
async def retry_source(
    workspace_id: UUID,
    source_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(workspace_id, user_id, db)

    result = await db.execute(
        select(Source).where(
            Source.id == source_id,
            Source.workspace_id == workspace_id,
        )
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )

    # Reset status
    source.status = "queued"
    await db.commit()
    await db.refresh(source)

    try:
        ingest_source.delay(
            source_id=str(source.id),
            workspace_id=str(workspace_id),
            source_type=source.source_type,
            url=source.url,
        )
        print(f"[sources] ✓ Queued retry task for source {source.id}")
    except Exception as e:
        print(f"[sources] ✗ Failed to queue retry task: {e}")

    return source

@router.get(
    "/{workspace_id}/sources",
    response_model=list[SourceResponse],
)
async def get_sources(
    workspace_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(workspace_id, user_id, db)

    result = await db.execute(select(Source).where(Source.workspace_id == workspace_id))
    return result.scalars().all()


@router.get(
    "/{workspace_id}/sources/{source_id}",
    response_model=SourceResponse,
)
async def get_source(
    workspace_id: UUID,
    source_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(workspace_id, user_id, db)

    result = await db.execute(
        select(Source).where(
            Source.id == source_id,
            Source.workspace_id == workspace_id,
        )
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )
    return source


@router.delete(
    "/{workspace_id}/sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_source(
    workspace_id: UUID,
    source_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(workspace_id, user_id, db)

    result = await db.execute(
        select(Source).where(
            Source.id == source_id,
            Source.workspace_id == workspace_id,
        )
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )
    await db.delete(source)
    await db.commit()
