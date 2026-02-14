"""Matching endpoints - Core recommendation engine"""

from fastapi import APIRouter, HTTPException, Depends, Query
from app.schemas.tender import Tender, TenderCreate
from app.schemas.matching import MatchResponse
from app.services.matching import MatchingService
from app.api.deps import get_matching_service

router = APIRouter()


@router.post("/recommend", response_model=MatchResponse)
async def get_vendor_recommendations(
    tender: TenderCreate,
    top_k: int = Query(5, ge=1, le=20, description="Number of vendors to recommend"),
    service: MatchingService = Depends(get_matching_service)
):
    """
    Get top N vendor recommendations for a tender
    
    """
    try:
        result = service.find_matching_vendors(
            Tender(**tender.model_dump()), 
            top_k=top_k
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error generating recommendations: {str(e)}"
        )


@router.post("/quick-match")
async def quick_match(
    tender: TenderCreate,
    service: MatchingService = Depends(get_matching_service)
):
    """Quick match endpoint returning simplified response"""
    try:
        result = service.find_matching_vendors(Tender(**tender.model_dump()), top_k=5)
        
        return {
            "success": True,
            "tender_id": tender.tender_id,
            "vendor_ids": [m.vendor_id for m in result.matches],
            "match_count": result.total_matches,
            "search_time_ms": result.search_time_ms
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
