from typing import List, Optional
from dataclasses import dataclass


@dataclass
class CollectionHealth:
    source_id: str
    baseline_score: float
    recent_avg_score: float
    is_degraded: bool
    drop_percentage: float


async def get_recent_scores(
    source_id: str,
    db,
    last_n: int = 20,
) -> List[float]:
    """
    Fetches the last N faithfulness scores for a source
    from the eval_scores table.
    """
    from sqlalchemy import select, desc
    from app.models.eval_score import EvalScore

    result = await db.execute(
        select(EvalScore.faithfulness)
        .where(EvalScore.source_id == source_id)
        .where(EvalScore.faithfulness.isnot(None))
        .order_by(desc(EvalScore.created_at))
        .limit(last_n)
    )
    scores = [row[0] for row in result.fetchall()]
    return scores


def compute_rolling_average(scores: List[float]) -> float:
    """
    Computes the average of a list of scores.
    Returns 0.0 if the list is empty.
    """
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def detect_drift(
    baseline_score: float,
    recent_scores: List[float],
    threshold: float = 0.1,
) -> CollectionHealth:
    """
    Detects if retrieval quality has drifted from baseline.
    Flags as degraded if rolling average drops more than threshold (10%).
    """
    recent_avg = compute_rolling_average(recent_scores)
    drop = baseline_score - recent_avg
    drop_percentage = (drop / baseline_score) if baseline_score > 0 else 0.0
    is_degraded = drop_percentage >= threshold

    return CollectionHealth(
        source_id="",
        baseline_score=baseline_score,
        recent_avg_score=recent_avg,
        is_degraded=is_degraded,
        drop_percentage=drop_percentage,
    )


async def check_all_collections(db) -> List[CollectionHealth]:
    """
    Runs drift detection across all sources.
    Called by the weekly Celery cron job.
    Returns list of CollectionHealth results.
    """
    from sqlalchemy import select
    from app.models.source import Source

    print("[drift_detector] Running drift detection across all collections...")

    result = await db.execute(select(Source).where(Source.status == "ready"))
    sources = result.scalars().all()

    health_results = []

    for source in sources:
        source_id = str(source.id)
        recent_scores = await get_recent_scores(source_id, db)

        if len(recent_scores) < 5:
            # Not enough data yet
            continue

        # Use first score as baseline if not stored separately
        baseline = recent_scores[-1]
        health = detect_drift(baseline, recent_scores[:-1])
        health.source_id = source_id

        if health.is_degraded:
            print(
                f"[drift_detector] Source {source_id} degraded: "
                f"{health.drop_percentage:.1%} drop from baseline"
            )
            # Mark source as degraded in DB
            source.status = "degraded"
            await db.commit()

        health_results.append(health)

    print(f"[drift_detector] Checked {len(health_results)} collections")
    return health_results
