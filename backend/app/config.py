from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Qdrant
    QDRANT_URL: str
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION: str
    QDRANT_VECTOR_DIM: int

    # Redis
    REDIS_URL: str

    # Storage (optional — only needed when R2 is used)
    R2_ACCOUNT_ID: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_BUCKET_NAME: str

    # LLM — required, no defaults
    GEMINI_API_KEY: str
    GROQ_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    GITHUB_TOKEN: Optional[str] = None

    # LLM Models
    LLM_PRIMARY_MODEL: str
    LLM_LITE_MODEL: str
    LLM_FALLBACK_MODEL: str
    LLM_VISION_MODEL: str

    # Embedding and Reranker Models
    EMBEDDING_MODEL_TEXT: str
    EMBEDDING_MODEL_CODE: str
    RERANKER_MODEL: str

    # Auth — required, no defaults
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Observability
    LANGCHAIN_TRACING_V2: str
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str
    SENTRY_DSN: Optional[str] = None

    # App
    ENVIRONMENT: str
    ALLOWED_ORIGINS: list[str]

    class Config:
        env_file = ".env"


settings = Settings()