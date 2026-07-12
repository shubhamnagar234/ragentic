import uuid
from sqlalchemy import Column, Float, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class EvalScore(Base):
    __tablename__ = "eval_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(
        UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False
    )
    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True, index=True
    )
    source_id = Column(
        UUID(as_uuid=True), ForeignKey("sources.id"), nullable=True
    )
    faithfulness = Column(Float, nullable=True)
    context_precision = Column(Float, nullable=True)
    answer_relevance = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    message = relationship("Message", backref="eval_scores")
    source = relationship("Source", backref="eval_scores")

    def __repr__(self):
        return f"<EvalScore faithfulness={self.faithfulness}>"