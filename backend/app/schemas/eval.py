from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class EvalScoreResponse(BaseModel):
    id: UUID
    message_id: UUID
    source_id: Optional[UUID] = None
    faithfulness: Optional[float] = None
    context_precision: Optional[float] = None
    answer_relevance: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FeedbackCreate(BaseModel):
    message_id: UUID
    score: int                          # 1 (thumbs up) | -1 (thumbs down)
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: UUID
    message_id: UUID
    user_id: UUID
    score: int
    comment: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}