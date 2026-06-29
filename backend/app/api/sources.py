from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user
from app.models.source import Source
from app.models.workspace import Workspace
from app.schemas.source import SourceCreate, SourceResponse

router = APIRouter()


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

    result = await db.execute(
        select(Source).where(Source.workspace_id == workspace_id)
    )
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