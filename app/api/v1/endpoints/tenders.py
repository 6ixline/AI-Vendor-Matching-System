"""Tender API endpoints"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.schemas.tender import Tender, TenderCreate
from app.services.matching import MatchingService
from app.api.deps import get_matching_service

router = APIRouter()


@router.post("/", response_model=dict, status_code=201)
async def create_tender(
    tender: TenderCreate,
    matching_service: MatchingService = Depends(get_matching_service)
):
    """Add a new tender to the system"""
    try:
        result = matching_service.add_tender(Tender(**tender.model_dump()))
        return {
            "status": "success",
            "message": "Tender added successfully",
            "tender_id": tender.tender_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tender_id}", response_model=dict)
async def get_tender(
    tender_id: str,
    matching_service: MatchingService = Depends(get_matching_service)
):
    """Get tender by ID"""
    tender = matching_service.db.get_tender(tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    return tender
