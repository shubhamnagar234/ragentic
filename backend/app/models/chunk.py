import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, func, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    text = Column(Text, nullable=False)
    page_num = Column(Integer, nullable=True)  # for PDFs
    start_time = Column(Float, nullable=True)  # for audio/video (seconds)
    end_time = Column(Float, nullable=True)  # for audio/video (seconds)
    chunk_type = Column(String, default="parent")  # parent or child
    parent_id = Column(UUID(as_uuid=True), nullable=True)  # for child chunks
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    source = relationship("Source", backref="chunks")

    def __repr__(self):
        return f"<Chunk {self.chunk_type} - {self.id}>"
