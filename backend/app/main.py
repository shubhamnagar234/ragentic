from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import engine, Base

# Import all models so SQLAlchemy creates the tables
import app.models

# Import routers
from app.api import workspaces, sources


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Database tables created")
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


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ragentic-api",
        "environment": settings.ENVIRONMENT,
    }
