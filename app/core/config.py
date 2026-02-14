"""Application configuration"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "AI-Matching-System - Vendor-Tender Matching System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENV: str = "development"
    
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_VENDORS: str = "vendors"
    QDRANT_COLLECTION_TENDERS: str = "tenders"
    QDRANT_COLLECTION_FEEDBACK: str = "feedback"
    
    EMBEDDING_PROVIDER: str = "sentence-transformers"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # IP Whitelist - specific IP addresses allowed
    ALLOWED_IPS: List[str] = []
    
    # Domain Whitelist - domains allowed (checked via Origin/Referer headers)
    ALLOWED_DOMAINS: List[str] = []
    
    # CORS Origins - for cross-origin browser requests (requires full URL with scheme)
    ALLOWED_ORIGINS: List[str] = []
    
    DEFAULT_TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.2
    FEEDBACK_ADJUSTMENT_WEIGHT: float = 0.1
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()