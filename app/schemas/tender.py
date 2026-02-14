"""Tender schemas"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class TenderBase(BaseModel):
    tender_title: str
    brief_description: str
    industry: str = Field(..., description="Single industry")
    categories: List[str] = Field(default_factory=list, description="Multiple categories")
    subcategory: Optional[str] = Field(None, description="Single subcategory")
    products: Optional[List[str]] = Field(
        default_factory=list, 
        description="Optional: Required products/services for this tender"
    )
    state_preference: Literal["pan_india", "specific_states"] = Field(
        ..., 
        description="Either 'pan_india' or 'specific_states'"
    )
    states: List[str] = Field(
        default_factory=list, 
        description="Specific states if state_preference is 'specific_states'"
    )
    required_annual_turnover: Optional[str] = None
    required_certifications: List[str] = Field(default_factory=list, description="Multiple required certifications")
    buyer_id: Optional[str] = None
    posted_date: Optional[str] = None
    expiry_date: Optional[str] = None


class TenderCreate(TenderBase):
    tender_id: str


class Tender(TenderBase):
    tender_id: str
    
    class Config:
        from_attributes = True


class TenderMatch(Tender):
    top_k: int = Field(default=5, ge=1, le=20)
