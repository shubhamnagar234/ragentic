import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, func, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    role = Column(String, nullable=False)           # user | assistant
    content = Column(Text, nullable=False)
    sources = Column(JSONB, nullable=True)          # [{chunk_id, score, text_preview}]
    confidence = Column(String, nullable=True)      # HIGH | MEDIUM | LOW
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    workspace = relationship("Workspace", backref="messages")
    user = relationship("User", backref="messages")

    def __repr__(self):
        return f"<Message {self.role} - {self.id}>"