"""
Learning Service

Provides intelligent memory and learning capabilities:
1. Store successful query interactions
2. Retrieve similar past examples for few-shot prompting
3. Track and learn from errors
4. Process user feedback
"""
import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import desc, func, text
from sqlalchemy.orm import Session

from app.db.models.learning import (
    FeedbackType,
    InteractionType,
    LearningError,
    QueryMemory,
    UserFeedback,
)

logger = logging.getLogger(__name__)


class LearningService:
    """Service for AI learning and memory operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # =========================================================================
    # QUERY MEMORY - Few-shot learning from past successes
    # =========================================================================
    
    def store_successful_query(
        self,
        question: str,
        sql: str,
        query_mode: str = "postgres",
        row_count: Optional[int] = None,
        execution_time_ms: Optional[int] = None,
    ) -> QueryMemory:
        """
        Store a successful query for future reference.
        
        Call this when a query executes successfully and returns valid results.
        """
        # Check if we already have a very similar query
        existing = self._find_exact_match(question, sql)
        if existing:
            existing.use_count += 1
            existing.last_used_at = datetime.utcnow()
            self.db.commit()
            return existing
        
        memory = QueryMemory(
            question=question.strip(),
            sql=sql.strip(),
            query_mode=query_mode,
            row_count=row_count,
            execution_time_ms=execution_time_ms,
            feedback_score=0.5,  # Neutral starting score
        )
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        
        logger.info(f"Stored new query memory: {memory.id}")
        return memory
    
    def _find_exact_match(self, question: str, sql: str) -> Optional[QueryMemory]:
        """Find an existing memory with the same question and SQL."""
        return self.db.query(QueryMemory).filter(
            QueryMemory.question == question.strip(),
            QueryMemory.sql == sql.strip(),
            QueryMemory.is_active == True,
        ).first()
    
    def get_similar_examples(
        self,
        question: str,
        query_mode: str = "postgres",
        limit: int = 3,
        min_score: float = 0.0,
    ) -> list[QueryMemory]:
        """
        Get similar past queries to use as few-shot examples.
        
        Uses keyword matching for now. Can be enhanced with embeddings later.
        """
        # Extract keywords from the question
        keywords = self._extract_keywords(question)
        
        if not keywords:
            return []
        
        # Build a query that matches any of the keywords
        # Weight by feedback score and recency
        query = self.db.query(QueryMemory).filter(
            QueryMemory.is_active == True,
            QueryMemory.query_mode == query_mode,
            QueryMemory.feedback_score >= min_score,
        )
        
        # Simple keyword matching using ILIKE
        keyword_filters = []
        for kw in keywords[:5]:  # Limit to top 5 keywords
            keyword_filters.append(QueryMemory.question.ilike(f"%{kw}%"))
        
        from sqlalchemy import or_
        query = query.filter(or_(*keyword_filters))
        
        # Order by score and recency
        results = query.order_by(
            desc(QueryMemory.feedback_score),
            desc(QueryMemory.last_used_at),
        ).limit(limit).all()
        
        # Update use count
        for memory in results:
            memory.use_count += 1
            memory.last_used_at = datetime.utcnow()
        self.db.commit()
        
        return results
    
    def _extract_keywords(self, question: str) -> list[str]:
        """Extract meaningful keywords from a question."""
        # Remove common stop words
        stop_words = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "shall", "can", "need", "dare",
            "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
            "into", "through", "during", "before", "after", "above", "below",
            "between", "under", "again", "further", "then", "once", "here",
            "there", "when", "where", "why", "how", "all", "each", "few",
            "more", "most", "other", "some", "such", "no", "nor", "not",
            "only", "own", "same", "so", "than", "too", "very", "just",
            "and", "but", "if", "or", "because", "until", "while", "what",
            "which", "who", "whom", "this", "that", "these", "those", "am",
            "show", "me", "get", "list", "find", "give", "tell", "i", "want",
            "please", "query", "data", "information", "details",
        }
        
        words = question.lower().split()
        keywords = [w.strip("?.,!") for w in words if w.strip("?.,!") not in stop_words and len(w) > 2]
        
        return keywords
    
    def format_examples_for_prompt(self, examples: list[QueryMemory]) -> str:
        """Format past examples for inclusion in LLM prompt."""
        if not examples:
            return ""
        
        lines = ["SUCCESSFUL PAST QUERIES (use as reference):"]
        for i, ex in enumerate(examples, 1):
            lines.append(f"\nExample {i}:")
            lines.append(f"Question: {ex.question}")
            lines.append(f"SQL: {ex.sql}")
        
        return "\n".join(lines)
    
    # =========================================================================
    # USER FEEDBACK - Learn from user corrections
    # =========================================================================
    
    def record_feedback(
        self,
        interaction_type: InteractionType,
        user_message: str,
        ai_response: str,
        feedback_type: FeedbackType,
        sql_generated: Optional[str] = None,
        feedback_comment: Optional[str] = None,
        corrected_sql: Optional[str] = None,
        session_id: Optional[str] = None,
        query_memory_id: Optional[int] = None,
    ) -> UserFeedback:
        """
        Record user feedback on an AI response.
        
        This updates the query memory score and can create error records.
        """
        feedback = UserFeedback(
            interaction_type=interaction_type,
            user_message=user_message,
            ai_response=ai_response,
            sql_generated=sql_generated,
            feedback_type=feedback_type,
            feedback_comment=feedback_comment,
            corrected_sql=corrected_sql,
            session_id=session_id,
            query_memory_id=query_memory_id,
        )
        self.db.add(feedback)
        
        # Update query memory score if linked
        if query_memory_id:
            memory = self.db.query(QueryMemory).get(query_memory_id)
            if memory:
                self._update_memory_score(memory, feedback_type)
        
        # If negative feedback with SQL, record as learning error
        if feedback_type in (FeedbackType.NEGATIVE, FeedbackType.CORRECTED) and sql_generated:
            self._record_error_from_feedback(
                question=user_message,
                bad_sql=sql_generated,
                correct_sql=corrected_sql,
                explanation=feedback_comment,
            )
        
        self.db.commit()
        self.db.refresh(feedback)
        
        logger.info(f"Recorded {feedback_type} feedback: {feedback.id}")
        return feedback
    
    def _update_memory_score(self, memory: QueryMemory, feedback_type: FeedbackType):
        """Update memory score based on feedback."""
        # Exponential moving average
        alpha = 0.3
        
        if feedback_type == FeedbackType.POSITIVE:
            new_value = 1.0
        elif feedback_type == FeedbackType.NEGATIVE:
            new_value = -1.0
        else:  # CORRECTED
            new_value = -0.5
        
        memory.feedback_score = alpha * new_value + (1 - alpha) * memory.feedback_score
        
        # Deactivate if score drops too low
        if memory.feedback_score < -0.5:
            memory.is_active = False
            logger.info(f"Deactivated low-scoring memory: {memory.id}")
    
    # =========================================================================
    # ERROR LEARNING - Track and avoid past mistakes
    # =========================================================================
    
    def record_error(
        self,
        question: str,
        bad_sql: str,
        error_type: str,
        error_message: Optional[str] = None,
        correct_sql: Optional[str] = None,
        explanation: Optional[str] = None,
    ) -> LearningError:
        """
        Record an error to learn from.
        
        Call this when:
        - SQL syntax error occurs
        - Query returns wrong results
        - User indicates the response was incorrect
        """
        # Check for existing similar error
        existing = self._find_similar_error(question, error_type)
        if existing:
            existing.occurrence_count += 1
            existing.last_occurred_at = datetime.utcnow()
            if correct_sql and not existing.correct_sql:
                existing.correct_sql = correct_sql
            if explanation and not existing.explanation:
                existing.explanation = explanation
            self.db.commit()
            return existing
        
        error = LearningError(
            question=question,
            bad_sql=bad_sql,
            error_type=error_type,
            error_message=error_message,
            correct_sql=correct_sql,
            explanation=explanation,
        )
        self.db.add(error)
        self.db.commit()
        self.db.refresh(error)
        
        logger.info(f"Recorded learning error: {error.id} ({error_type})")
        return error
    
    def _find_similar_error(self, question: str, error_type: str) -> Optional[LearningError]:
        """Find an existing error with similar question and type."""
        keywords = self._extract_keywords(question)[:3]
        if not keywords:
            return None
        
        query = self.db.query(LearningError).filter(
            LearningError.error_type == error_type,
            LearningError.is_active == True,
        )
        
        # Simple keyword match
        from sqlalchemy import and_, or_
        keyword_filters = [LearningError.question.ilike(f"%{kw}%") for kw in keywords]
        query = query.filter(or_(*keyword_filters))
        
        return query.first()
    
    def _record_error_from_feedback(
        self,
        question: str,
        bad_sql: str,
        correct_sql: Optional[str],
        explanation: Optional[str],
    ):
        """Record error from user feedback."""
        self.record_error(
            question=question,
            bad_sql=bad_sql,
            error_type="user_reported",
            error_message="User indicated this response was incorrect",
            correct_sql=correct_sql,
            explanation=explanation,
        )
    
    def get_relevant_errors(self, question: str, limit: int = 3) -> list[LearningError]:
        """Get errors relevant to the current question to warn the AI."""
        keywords = self._extract_keywords(question)
        if not keywords:
            return []
        
        query = self.db.query(LearningError).filter(
            LearningError.is_active == True,
        )
        
        from sqlalchemy import or_
        keyword_filters = [LearningError.question.ilike(f"%{kw}%") for kw in keywords[:5]]
        query = query.filter(or_(*keyword_filters))
        
        return query.order_by(
            desc(LearningError.occurrence_count),
        ).limit(limit).all()
    
    def format_errors_for_prompt(self, errors: list[LearningError]) -> str:
        """Format past errors as warnings for the LLM prompt."""
        if not errors:
            return ""
        
        lines = ["PAST MISTAKES TO AVOID:"]
        for error in errors:
            lines.append(f"\n- Question: {error.question[:100]}...")
            lines.append(f"  BAD SQL: {error.bad_sql[:100]}...")
            if error.explanation:
                lines.append(f"  Why wrong: {error.explanation}")
            if error.correct_sql:
                lines.append(f"  Correct approach: {error.correct_sql[:100]}...")
        
        return "\n".join(lines)
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_learning_stats(self) -> dict:
        """Get statistics about the learning system."""
        memory_count = self.db.query(func.count(QueryMemory.id)).filter(
            QueryMemory.is_active == True
        ).scalar()
        
        avg_score = self.db.query(func.avg(QueryMemory.feedback_score)).filter(
            QueryMemory.is_active == True
        ).scalar() or 0
        
        feedback_counts = dict(
            self.db.query(
                UserFeedback.feedback_type,
                func.count(UserFeedback.id)
            ).group_by(UserFeedback.feedback_type).all()
        )
        
        error_count = self.db.query(func.count(LearningError.id)).filter(
            LearningError.is_active == True
        ).scalar()
        
        return {
            "query_memories": memory_count,
            "average_memory_score": round(avg_score, 2),
            "feedback_counts": {k.value: v for k, v in feedback_counts.items()},
            "active_errors": error_count,
        }
