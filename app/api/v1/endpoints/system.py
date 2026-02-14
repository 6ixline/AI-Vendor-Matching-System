"""System health and management endpoints"""

from fastapi import APIRouter, Depends
from app.api.deps import get_db

router = APIRouter()


@router.get("/health")
async def health_check(db = Depends(get_db)):
    try:
        stats = db.get_stats()
        return {
            "status": "healthy",
            "database": "connected",
            "stats": stats
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/stats")
async def get_statistics(db = Depends(get_db)):
    return db.get_stats()
