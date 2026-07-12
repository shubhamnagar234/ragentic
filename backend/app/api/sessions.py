from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user
from app.models.workspace import Workspace
from app.models.session import Session
from app.schemas.session import SessionCreate, SessionResponse

router = APIRouter()


async def verify_workspace(
    workspace_id: str,
    user_id: str,
    db: AsyncSession,
) -> Workspace:
    result = await db.execute(
        select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.user_id == UUID(user_id),
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    return workspace


@router.get(
    "/{workspace_id}/sessions",
    response_model=list[SessionResponse],
)
async def get_sessions(
    workspace_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace(workspace_id, user_id, db)

    result = await db.execute(
        select(Session)
        .where(Session.workspace_id == workspace_id)
        .order_by(desc(Session.created_at))
    )
    return result.scalars().all()


@router.post(
    "/{workspace_id}/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    workspace_id: UUID,
    payload: SessionCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace(workspace_id, user_id, db)

    session = Session(
        workspace_id=UUID(workspace_id) if isinstance(workspace_id, str) else workspace_id,
        user_id=UUID(user_id),
        title=payload.title,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return session


@router.delete(
    "/{workspace_id}/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_session(
    workspace_id: str,
    session_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace(workspace_id, user_id, db)

    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.workspace_id == workspace_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    await db.delete(session)
    await db.commit()
