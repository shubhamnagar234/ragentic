from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class WorkspaceCreate(BaseModel):
    name: str


class WorkspaceUpdate(BaseModel):
    name: str


class WorkspaceResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}