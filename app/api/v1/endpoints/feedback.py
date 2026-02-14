"""Feedback endpoints for learning"""

from fastapi import APIRouter, HTTPException, Depends
from app.schemas.matching import FeedbackInput
from app.services.feedback import FeedbackService
from app.api.deps import get_feedback_service

router = APIRouter()


@router.post("/")
async def submit_feedback(
    feedback: FeedbackInput,
    service: FeedbackService = Depends(get_feedback_service)
):
    try:
        result = service.process_feedback(feedback)
        return {
            "success": True,
            "message": "Feedback processed",
            "details": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
