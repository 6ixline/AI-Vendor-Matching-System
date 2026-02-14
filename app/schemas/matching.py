"""Matching and response schemas"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class MatchResult(BaseModel):
    vendor_id: str
    company_name: str
    match_score: float = Field(ge=0, le=1)
    match_percentage: int
    match_reasons: List[str]
    vendor_details: Dict
    ranking: int


class MatchResponse(BaseModel):
    tender_id: str
    total_matches: int
    matches: List[MatchResult]
    search_time_ms: float


class FeedbackInput(BaseModel):
    tender_id: str
    vendor_id: str
    match_success: bool
    rating: Optional[int] = Field(None, ge=1, le=5)
    selected: bool = False
    comments: Optional[str] = None
    feedback_type: str = "manual"


class BulkVendorSync(BaseModel):
    vendors: List[dict]
    force_update: bool = False


class SyncResponse(BaseModel):
    synced: int
    updated: int
    failed: int
    errors: List[str] = Field(default_factory=list)
