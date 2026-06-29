from app.workers.celery_app import celery_app


@celery_app.task(bind=True, name="app.workers.ingest_tasks.ingest_source")
def ingest_source(
    self, source_id: str, workspace_id: str, source_type: str, url: str = None
):
    """
    Main ingestion task — routes to the correct ingestor based on source_type.
    This will be expanded in Week 2 when we build the actual ingestors.
    """
    try:
        self.update_state(state="STARTED", meta={"source_id": source_id})

        # Placeholder — actual ingestors will be wired here
        # from app.services.ingestion.pdf_ingestor import ingest_pdf
        # from app.services.ingestion.video_ingestor import ingest_video
        # from app.services.ingestion.web_ingestor import ingest_web

        print(
            f"[ingest_source] Starting ingestion for source_id={source_id}, type={source_type}"
        )

        return {
            "status": "completed",
            "source_id": source_id,
        }

    except Exception as exc:
        self.update_state(
            state="FAILURE",
            meta={"source_id": source_id, "error": str(exc)},
        )
        raise exc
