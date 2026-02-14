"""API dependencies"""

from app.db.qdrant import QdrantDB
from app.services.embedding import EmbeddingService
from app.services.matching import MatchingService
from app.services.feedback import FeedbackService
from app.core.config import settings

# Global instances (initialized on startup)
_db = None
_embedding_service = None
_matching_service = None
_feedback_service = None


def initialize_services():
    """Initialize all services (called on app startup)"""
    global _db, _embedding_service, _matching_service, _feedback_service
    
    _db = QdrantDB()
    _db.initialize_collections()
    
    _embedding_service = EmbeddingService()
    _matching_service = MatchingService(_db, _embedding_service, similarity_threshold=settings.SIMILARITY_THRESHOLD)
    _feedback_service = FeedbackService(_db, _embedding_service)


def get_db() -> QdrantDB:
    """Get database instance"""
    return _db


def get_embedding_service() -> EmbeddingService:
    """Get embedding service"""
    return _embedding_service


def get_matching_service() -> MatchingService:
    """Get matching service"""
    return _matching_service


def get_feedback_service() -> FeedbackService:
    """Get feedback service"""
    return _feedback_service
