from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user
from app.models.eval_score import EvalScore
from app.models.message import Message
from app.models.source import Source

router = APIRouter()


@router.get("/{workspace_id}/analytics")
async def get_analytics(
    workspace_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns aggregate metrics for a workspace.
    Used in the analytics dashboard.
    """
    # Total query count
    query_count_result = await db.execute(
        select(func.count(Message.id)).where(
            Message.workspace_id == workspace_id,
            Message.role == "assistant",
        )
    )
    query_count = query_count_result.scalar() or 0

    # Average faithfulness score
    avg_faithfulness_result = await db.execute(
        select(func.avg(EvalScore.faithfulness)).where(
            EvalScore.faithfulness.isnot(None),
        )
    )
    avg_faithfulness = avg_faithfulness_result.scalar() or 0.0

    # Average context precision
    avg_precision_result = await db.execute(
        select(func.avg(EvalScore.context_precision)).where(
            EvalScore.context_precision.isnot(None),
        )
    )
    avg_precision = avg_precision_result.scalar() or 0.0

    # Retry rate
    retry_count_result = await db.execute(
        select(func.count(Message.id)).where(
            Message.workspace_id == workspace_id,
            Message.role == "assistant",
            Message.retry_count > 0,
        )
    )
    retry_count = retry_count_result.scalar() or 0
    retry_rate = (retry_count / query_count) if query_count > 0 else 0.0

    # Hallucination rate (1 - avg_faithfulness)
    hallucination_rate = 1.0 - float(avg_faithfulness)

    # Source count
    source_count_result = await db.execute(
        select(func.count(Source.id)).where(
            Source.workspace_id == workspace_id,
        )
    )
    source_count = source_count_result.scalar() or 0

    # Confidence distribution
    high_conf_result = await db.execute(
        select(func.count(Message.id)).where(
            Message.workspace_id == workspace_id,
            Message.confidence == "HIGH",
        )
    )
    high_conf = high_conf_result.scalar() or 0

    return {
        "workspace_id": str(workspace_id),
        "query_count": query_count,
        "source_count": source_count,
        "avg_faithfulness": round(float(avg_faithfulness), 3),
        "avg_context_precision": round(float(avg_precision), 3),
        "hallucination_rate": round(hallucination_rate, 3),
        "retry_rate": round(retry_rate, 3),
        "retry_count": retry_count,
        "confidence_distribution": {
            "high": high_conf,
            "total": query_count,
        },
    }


@router.get("/{workspace_id}/analytics/scores")
async def get_score_trend(
    workspace_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns RAGAS score history for trend chart.
    Used in the analytics dashboard line chart.
    """
    result = await db.execute(
        select(
            EvalScore.faithfulness,
            EvalScore.context_precision,
            EvalScore.answer_relevance,
            EvalScore.created_at,
        )
        .order_by(EvalScore.created_at.asc())
        .limit(100)
    )
    rows = result.fetchall()

    scores = [
        {
            "faithfulness": row.faithfulness,
            "context_precision": row.context_precision,
            "answer_relevance": row.answer_relevance,
            "date": row.created_at.isoformat(),
        }
        for row in rows
    ]

    return {"workspace_id": str(workspace_id), "scores": scores}
