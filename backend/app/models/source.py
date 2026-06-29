import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Source(Base):
    __tablename__ = "sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    source_type = Column(
        String, nullable=False
    )  # PDF, YOUTUBE, GITHUB, WEB, AUDIO, LOOM
    url = Column(String, nullable=True)  # original URL or filename
    title = Column(String, nullable=True)
    status = Column(
        String, default="queued"
    )  # queued, ingesting, ready, degraded, re-indexing
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    workspace = relationship("Workspace", backref="sources")

    def __repr__(self):
        return f"<Source {self.source_type} - {self.title}>"
