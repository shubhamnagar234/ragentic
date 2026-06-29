from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Any


class ActionItem(BaseModel):
    owner: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[str] = None      # high | medium | low
    description: str


class ReportCreate(BaseModel):
    workspace_id: UUID
    title: str


class ReportResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    title: str
    summary: Optional[str] = None
    decisions: Optional[List[Any]] = None
    action_items: Optional[List[ActionItem]] = None
    open_questions: Optional[List[Any]] = None
    pdf_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}