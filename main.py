"""Main AI-Matching-System FastAPI application"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from logging.handlers import RotatingFileHandler
import os
from app.core.config import settings
from app.api.v1.api import api_router
from app.api.deps import initialize_services
from app.utils.DomainIPWhitelistMiddleware import DomainIPWhitelistMiddleware

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=10485760,
            backupCount=5
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI-Matching-System Vendor-Tender Matching System...")
    try:
        initialize_services()
        logger.info("All services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    yield
    
    logger.info("Shutting down application...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered vendor-tender matching and recommendation system",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add Domain/IP Whitelist Middleware
allowed_ips = getattr(settings, 'ALLOWED_IPS', [])
allowed_domains = getattr(settings, 'ALLOWED_DOMAINS', [])

if allowed_ips or allowed_domains:
    app.add_middleware(DomainIPWhitelistMiddleware)
    logger.info("=" * 80)
    logger.info("ACCESS CONTROL ENABLED")
    logger.info(f"   Allowed IPs: {allowed_ips}")
    logger.info(f"   Allowed Domains: {allowed_domains}")
    logger.info("=" * 80)
else:
    logger.warning("=" * 80)
    logger.warning("ACCESS CONTROL DISABLED - ALL ACCESS ALLOWED")
    logger.warning("=" * 80)

# Add CORS Middleware (for cross-origin browser requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/")
async def root():
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    from app.api.deps import get_db
    try:
        db = get_db()
        stats = db.get_stats()
        return {
            "status": "healthy",
            "version": settings.APP_VERSION,
            "stats": stats
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
