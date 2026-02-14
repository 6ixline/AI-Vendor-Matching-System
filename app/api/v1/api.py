"""API v1 router configuration"""

from fastapi import APIRouter
from app.api.v1.endpoints import vendors, matching, feedback, system

api_router = APIRouter()

api_router.include_router(vendors.router, prefix="/vendors", tags=["Vendors"])
api_router.include_router(matching.router, prefix="/matching", tags=["Matching"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])
api_router.include_router(system.router, prefix="/system", tags=["System"])
