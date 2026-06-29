from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.eval_tasks.check_retrieval_drift")
def check_retrieval_drift():
    """
    Weekly cron task — checks RAGAS score history per collection.
    If rolling average drops 10% from baseline → marks collection as degraded.
    This will be expanded in Phase 3 when we build drift_detector.py.
    """
    print("[check_retrieval_drift] Running weekly drift detection...")

    # Placeholder — actual drift detection will be wired here
    # from app.services.eval.drift_detector import detect_drift
    # detect_drift()

    return {"status": "completed"}
