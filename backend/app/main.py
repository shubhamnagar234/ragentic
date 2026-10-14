from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import engine, Base
from app.middleware.logging import LoggingMiddleware
from sqlalchemy import text

# Import all models so SQLAlchemy creates the tables
import app.models

# Import routers
from app.api import workspaces, sources, chat, analytics, reports, sessions


async def init_qdrant():
    """
    Creates Qdrant collection on startup if it doesn't exist.
    """
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams

    client = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY or None,
    )

    collection_name = settings.QDRANT_COLLECTION

    # Check if collection exists
    existing = client.get_collections().collections
    existing_names = [c.name for c in existing]

    if collection_name not in existing_names:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.QDRANT_VECTOR_DIM,
                distance=Distance.COSINE,
            ),
        )
        print(f"[main] [OK] Qdrant collection '{collection_name}' created")
    else:
        print(f"[main] [OK] Qdrant collection '{collection_name}' already exists")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            await conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS feedback VARCHAR"))
            await conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS session_id UUID REFERENCES sessions(id)"))

            # Add workspace_id to eval_scores for per-workspace analytics scoping
            await conn.execute(text(
                "ALTER TABLE eval_scores ADD COLUMN IF NOT EXISTS workspace_id UUID REFERENCES workspaces(id)"
            ))

            # Auto-create default sessions for existing workspaces
            await conn.execute(text("""
                INSERT INTO sessions (id, workspace_id, user_id, title)
                SELECT gen_random_uuid(), id, user_id, 'Default Chat'
                FROM workspaces w
                WHERE NOT EXISTS (
                    SELECT 1 FROM sessions s WHERE s.workspace_id = w.id
                )
            """))

            # Backfill session_id for existing messages
            await conn.execute(text("""
                UPDATE messages m
                SET session_id = (
                    SELECT id FROM sessions s WHERE s.workspace_id = m.workspace_id LIMIT 1
                )
                WHERE session_id IS NULL
            """))
        except Exception as e:
            print(f"Skipping alter table: {e}")
    print("[main] [OK] Database tables created")

    await init_qdrant()

    # Pre-warm embedder and reranker so user queries never experience cold-start delays
    try:
        from app.services.ingestion.embedder import get_text_model
        from app.services.retrieval.reranker import get_reranker
        get_text_model()
        get_reranker()
        print("[main] [OK] Embedder & Reranker models pre-warmed in RAM")
    except Exception as e:
        print(f"[main] Model pre-warm skipped: {e}")

    yield

    # Shutdown
    await engine.dispose()
    print("[main] [OK] Database connections closed")


app = FastAPI(
    title="RAGENTIC API",
    description="Multimodal AI Knowledge Workspace",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(
    workspaces.router,
    prefix="/api/workspaces",
    tags=["workspaces"],
)
app.include_router(
    sources.router,
    prefix="/api/workspaces",
    tags=["sources"],
)
app.include_router(
    chat.router,
    prefix="/api/workspaces",
    tags=["chat"],
)
app.include_router(
    analytics.router,
    prefix="/api/workspaces",
    tags=["analytics"],
)
app.include_router(
    reports.router,
    prefix="/api/workspaces",
    tags=["reports"],
)
app.include_router(
    sessions.router,
    prefix="/api/workspaces",
    tags=["sessions"],
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ragentic-api",
        "environment": settings.ENVIRONMENT,
    }
