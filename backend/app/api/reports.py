from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user
from app.models.report import Report
from app.models.workspace import Workspace
from app.schemas.report import ReportCreate, ReportResponse

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


@router.get(
    "/{workspace_id}/reports",
    response_model=list[ReportResponse],
)
async def get_reports(
    workspace_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(workspace_id, user_id, db)

    result = await db.execute(
        select(Report)
        .where(Report.workspace_id == workspace_id)
        .order_by(Report.created_at.desc())
    )
    return result.scalars().all()


@router.get(
    "/{workspace_id}/reports/{report_id}",
    response_model=ReportResponse,
)
async def get_report(
    workspace_id: UUID,
    report_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(workspace_id, user_id, db)

    result = await db.execute(
        select(Report).where(
            Report.id == report_id,
            Report.workspace_id == workspace_id,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    return report


@router.delete(
    "/{workspace_id}/reports/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_report(
    workspace_id: UUID,
    report_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_workspace_access(workspace_id, user_id, db)

    result = await db.execute(
        select(Report).where(
            Report.id == report_id,
            Report.workspace_id == workspace_id,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    await db.delete(report)
    await db.commit()
