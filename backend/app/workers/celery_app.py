from celery import Celery
from app.config import settings

celery_app = Celery(
    "ragentic",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.ingest_tasks",
        "app.workers.eval_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "check-retrieval-drift": {
            "task": "app.workers.eval_tasks.check_retrieval_drift",
            "schedule": 604800.0,  # every 7 days
        },
    },
)

from celery.signals import worker_ready

@worker_ready.connect
def warm_up_models(sender, **kwargs):
    print("[celery] Pre-warming embedding model into RAM...")
    try:
        from app.services.ingestion.embedder import get_text_model
        get_text_model()
        print("[celery] Embedding model pre-warmed and ready in RAM")
    except Exception as e:
        print(f"[celery] Warm up skipped: {e}")

