from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class SourceCreate(BaseModel):
    url: Optional[str] = None
    source_type: str
    title: Optional[str] = None


class SourceResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    source_type: str
    url: Optional[str] = None
    title: Optional[str] = None
    status: str
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}