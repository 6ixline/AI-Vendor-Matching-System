"""Vendor schemas"""

from pydantic import BaseModel, Field
from typing import List, Optional

class VendorBase(BaseModel):
    company_name: str
    description: Optional[str] = None
    industries: List[str] = Field(default_factory=list, description="Multiple industries")
    categories: List[str] = Field(default_factory=list, description="Multiple categories")
    products: List[str] = Field(default_factory=list, description="Full product list")
    business_type: str
    states: List[str] = Field(default_factory=list, description="Multiple states where vendor operates")
    annual_turnover: Optional[str] = None
    certifications: Optional[List[str]] = Field(default_factory=list, description="Multiple certifications")


class VendorCreate(VendorBase):
    vendor_id: str


class VendorUpdate(BaseModel):
    """Schema for updating vendor - all fields optional"""
    company_name: Optional[str] = None
    description: Optional[str] = None
    industries: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    products: Optional[List[str]] = None
    business_type: Optional[str] = None
    states: Optional[List[str]] = None
    annual_turnover: Optional[str] = None
    certifications: Optional[List[str]] = None


class Vendor(VendorBase):
    vendor_id: str
    
    class Config:
        from_attributes = True


class VendorInDB(Vendor):
    embedding_hash: Optional[str] = None
    last_updated: Optional[str] = None
