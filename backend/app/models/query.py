from sqlalchemy import Column, String, DateTime, Text, Integer, Float, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base


class Query(Base):
    __tablename__ = "queries"

    id = Column(String, primary_key=True, index=True)  # UUID as string
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    grade = Column(String, nullable=False)
    rounds = Column(Integer, nullable=False)
    query_text = Column(Text, nullable=False)  # Normalized query for search
    # Generation tracking
    status = Column(String, nullable=False, default="pending")  # pending, processing, completed, failed
    result = Column(Text, nullable=True)  # JSON string of generation result
    error_message = Column(Text, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # Token & cost tracking
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)