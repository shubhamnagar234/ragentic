import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    decisions = Column(JSONB, nullable=True)
    action_items = Column(JSONB, nullable=True)     # [{owner, deadline, priority, description}]
    open_questions = Column(JSONB, nullable=True)
    pdf_url = Column(String, nullable=True)         # R2 file URL
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    workspace = relationship("Workspace", backref="reports")

    def __repr__(self):
        return f"<Report {self.title}>"