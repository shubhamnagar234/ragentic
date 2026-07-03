from app.workers.celery_app import celery_app
import asyncio


@celery_app.task(bind=True, name="app.workers.ingest_tasks.ingest_source")
def ingest_source(
    self, source_id: str, workspace_id: str, source_type: str, url: str = None
):
    """
    Main ingestion task — routes to correct ingestor based on source_type.
    """
    try:
        self.update_state(state="STARTED", meta={"source_id": source_id})
        print(
            f"[ingest_source] Starting ingestion: source_id={source_id}, type={source_type}, url={url}"
        )

        # Run async ingestion in sync Celery context
        asyncio.run(_ingest_async(source_id, workspace_id, source_type, url))

        return {"status": "completed", "source_id": source_id}

    except Exception as exc:
        print(f"[ingest_source] Failed: {exc}")
        raise exc


async def _ingest_async(
    source_id: str, workspace_id: str, source_type: str, url: str = None
):
    """
    Async ingestion pipeline — runs inside Celery worker.
    """
    from app.database import AsyncSessionLocal
    from app.models.source import Source
    from app.services.ingestion.embedder import embed_chunks
    from app.services.retrieval.sparse import save_index_to_redis
    from sqlalchemy import select
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct
    from app.config import settings
    import uuid

    async with AsyncSessionLocal() as db:
        # Update source status to ingesting
        result = await db.execute(select(Source).where(Source.id == source_id))
        source = result.scalar_one_or_none()
        if not source:
            raise ValueError(f"Source {source_id} not found")

        source.status = "ingesting"
        await db.commit()

        try:
            chunks = []
            title = None

            # Route to correct ingestor
            if source_type == "YOUTUBE" or source_type == "LOOM":
                from app.services.ingestion.video_ingestor import ingest_video

                chunks, title = await ingest_video(url, source_id)

            elif source_type == "PDF":
                from app.services.ingestion.pdf_ingestor import ingest_pdf

                chunks = await ingest_pdf(url, source_id)
                title = url.split("/")[-1] if url else "PDF"

            elif source_type == "WEB":
                from app.services.ingestion.web_ingestor import ingest_web

                chunks, title = await ingest_web(url, source_id)

            elif source_type == "GITHUB":
                from app.services.ingestion.github_ingestor import ingest_github

                chunks, title = await ingest_github(url, source_id)

            else:
                raise ValueError(f"Unknown source type: {source_type}")

            if not chunks:
                raise ValueError("No chunks produced from ingestion")

            # Embed child chunks
            is_code = source_type == "GITHUB"
            embedded = embed_chunks(chunks, is_code=is_code)

            print(f"[ingest_source] Embedded {len(embedded)} child chunks")

            # Store in Qdrant
            client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY or None,
            )

            points = []
            for item in embedded:
                points.append(
                    PointStruct(
                        id=item["chunk_id"],
                        vector=item["vector"],
                        payload={
                            "text": item["text"],
                            "parent_id": item["parent_id"],
                            "source_id": source_id,
                            "workspace_id": workspace_id,
                            "page_num": item.get("page_num"),
                            "start_time": item.get("start_time"),
                            "end_time": item.get("end_time"),
                            **item.get("metadata", {}),
                        },
                    )
                )

            if points:
                client.upsert(
                    collection_name=settings.QDRANT_COLLECTION,
                    points=points,
                )
                print(f"[ingest_source] Upserted {len(points)} vectors to Qdrant")

            # Store parent chunks in PostgreSQL
            from app.models.chunk import Chunk as ChunkModel

            parent_chunks = [c for c in chunks if c.chunk_type == "parent"]
            for chunk in parent_chunks:
                import uuid
                db_chunk = ChunkModel(
                    id=uuid.UUID(chunk.chunk_id),
                    source_id=uuid.UUID(source_id),
                    text=chunk.text,
                    page_num=chunk.page_num,
                    start_time=chunk.start_time,
                    end_time=chunk.end_time,
                    chunk_type="parent",
                )
                db.add(db_chunk)

            # Build BM25 index
            all_chunk_dicts = [
                {
                    "chunk_id": item["chunk_id"],
                    "text": item["text"],
                    "source_id": source_id,
                }
                for item in embedded
            ]
            save_index_to_redis(workspace_id, all_chunk_dicts)
            print(f"[ingest_source] BM25 index saved to Redis")

            # Update source status to ready
            source.status = "ready"
            source.title = title or url
            source.chunk_count = len(embedded)
            await db.commit()

            print(
                f"[ingest_source] ✓ Ingestion complete: {len(embedded)} chunks, title={title}"
            )

        except Exception as e:
            await db.rollback()
            source.status = "failed"
            await db.commit()
            raise e
