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
from app.api import workspaces, sources, chat, analytics, reports


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
        print(f"✓ Qdrant collection '{collection_name}' created")
    else:
        print(f"✓ Qdrant collection '{collection_name}' already exists")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Safely add feedback column to existing table
        try:
            await conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS feedback VARCHAR"))
        except Exception as e:
            print(f"Skipping alter table: {e}")
    print("✓ Database tables created")

    await init_qdrant()

    yield

    # Shutdown
    await engine.dispose()
    print("✓ Database connections closed")


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


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ragentic-api",
        "environment": settings.ENVIRONMENT,
    }
