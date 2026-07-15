from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, List


class ChatRequest(BaseModel):
    query: str
    workspace_id: UUID
    session_id: Optional[UUID] = None
    source_ids: Optional[List[UUID]] = None   # filter to specific sources


class SourceCitation(BaseModel):
    chunk_id: str
    score: float
    text_preview: str
    full_text: Optional[str] = None
    source_title: Optional[str] = None
    source_type: Optional[str] = None


class EvalScoreResponse(BaseModel):
    faithfulness: Optional[float] = None
    context_precision: Optional[float] = None
    answer_relevance: Optional[float] = None

    model_config = {"from_attributes": True}

class MessageResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    role: str
    content: str
    sources: Optional[List[SourceCitation]] = None
    confidence: Optional[str] = None
    retry_count: int
    feedback: Optional[str] = None
    created_at: datetime
    eval_scores: Optional[List[EvalScoreResponse]] = []

    model_config = {"from_attributes": True}

class MessageFeedbackRequest(BaseModel):
    feedback: Optional[str] = None   # "UP", "DOWN", or None