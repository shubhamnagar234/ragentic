from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, List


class ChatRequest(BaseModel):
    query: str
    workspace_id: UUID
    source_ids: Optional[List[UUID]] = None   # filter to specific sources


class SourceCitation(BaseModel):
    chunk_id: str
    score: float
    text_preview: str
    source_title: Optional[str] = None
    source_type: Optional[str] = None


class MessageResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    role: str
    content: str
    sources: Optional[List[SourceCitation]] = None
    confidence: Optional[str] = None
    retry_count: int
    created_at: datetime

    model_config = {"from_attributes": True}