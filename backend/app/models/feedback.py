import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, func, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(
        UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    score = Column(Integer, nullable=False)         # 1 (thumbs up) | -1 (thumbs down)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    message = relationship("Message", backref="feedbacks")
    user = relationship("User", backref="feedbacks")

    def __repr__(self):
        return f"<Feedback score={self.score}>"