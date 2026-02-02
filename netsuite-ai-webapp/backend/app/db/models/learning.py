"""
Learning & Memory Models

Stores successful interactions and feedback to improve AI responses over time.
"""
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    Index,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class FeedbackType(str, PyEnum):
    POSITIVE = "positive"  # User liked the response
    NEGATIVE = "negative"  # User disliked the response
    CORRECTED = "corrected"  # User provided a correction


class InteractionType(str, PyEnum):
    DATA_QUERY = "data_query"
    GENERAL = "general"
    NETSUITE_HELP = "netsuite_help"


class QueryMemory(Base):
    """
    Stores successful query interactions for few-shot learning.
    
    When the AI generates a query that works well, we store it here
    and use similar past queries as examples for future prompts.
    """
    __tablename__ = "query_memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # The natural language question
    question = Column(Text, nullable=False, index=True)
    
    # The generated SQL that worked
    sql = Column(Text, nullable=False)
    
    # Query mode (postgres or netsuite)
    query_mode = Column(String(20), default="postgres")
    
    # Embedding vector for semantic similarity (stored as JSON array)
    # We'll use this to find similar past questions
    embedding = Column(Text, nullable=True)  # JSON array of floats
    
    # Metadata
    row_count = Column(Integer, nullable=True)  # How many rows returned
    execution_time_ms = Column(Integer, nullable=True)
    
    # Feedback tracking
    feedback_score = Column(Float, default=0.0)  # Aggregated score (-1 to 1)
    use_count = Column(Integer, default=0)  # Times used as example
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    
    # Soft delete for bad examples
    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index("ix_query_memory_active_score", "is_active", "feedback_score"),
    )


class UserFeedback(Base):
    """
    Stores user feedback on AI responses.
    
    This helps us:
    1. Improve query memory scores
    2. Track common mistakes
    3. Build training data for fine-tuning
    """
    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Link to query memory if applicable
    query_memory_id = Column(Integer, ForeignKey("query_memory.id"), nullable=True)
    query_memory = relationship("QueryMemory", backref="feedback")
    
    # The interaction details
    interaction_type = Column(Enum(InteractionType), nullable=False)
    user_message = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    sql_generated = Column(Text, nullable=True)
    
    # Feedback
    feedback_type = Column(Enum(FeedbackType), nullable=False)
    feedback_comment = Column(Text, nullable=True)  # User's explanation
    corrected_sql = Column(Text, nullable=True)  # If user provided correction
    
    # Metadata
    session_id = Column(String(100), nullable=True)  # To group conversations
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_user_feedback_type_created", "feedback_type", "created_at"),
    )


class LearningError(Base):
    """
    Tracks errors and mistakes to avoid repeating them.
    
    When a query fails or produces wrong results, we store it here
    to add as negative examples or warnings in future prompts.
    """
    __tablename__ = "learning_errors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # The question that caused the error
    question = Column(Text, nullable=False)
    
    # The bad SQL that was generated
    bad_sql = Column(Text, nullable=False)
    
    # Error details
    error_type = Column(String(100), nullable=False)  # e.g., "syntax_error", "wrong_table", "wrong_results"
    error_message = Column(Text, nullable=True)
    
    # The correction (if known)
    correct_sql = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)  # Why it was wrong
    
    # How many times this mistake pattern occurred
    occurrence_count = Column(Integer, default=1)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Is this still a relevant error to warn about?
    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index("ix_learning_errors_active", "is_active", "occurrence_count"),
    )
