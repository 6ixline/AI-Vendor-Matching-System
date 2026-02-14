"""Vendor management endpoints"""

from fastapi import APIRouter, HTTPException, Depends, status
from app.schemas.vendor import Vendor, VendorCreate, VendorUpdate
from app.schemas.matching import BulkVendorSync, SyncResponse
from app.services.matching import MatchingService
from app.api.deps import get_matching_service

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_vendor(
    vendor: VendorCreate,
    service: MatchingService = Depends(get_matching_service)
):
    """Add a new vendor to the system"""
    try:
        result = service.add_vendor(Vendor(**vendor.model_dump()))
        return {
            "success": True,
            "message": "Vendor added successfully",
            "vendor_id": vendor.vendor_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{vendor_id}")
async def get_vendor(
    vendor_id: str,
    service: MatchingService = Depends(get_matching_service)
):
    """Get vendor details by ID"""
    vendor = service.db.get_vendor(vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return {"success": True, "vendor": vendor}


@router.put("/{vendor_id}")
async def update_vendor(
    vendor_id: str,
    vendor_update: VendorUpdate,
    service: MatchingService = Depends(get_matching_service)
):
    """
    Update vendor information
    
    - Only provided fields will be updated
    - Vendor embedding will be regenerated
    """
    try:
        # Convert to dict, excluding None values
        update_data = vendor_update.model_dump(exclude_none=True)
        
        if not update_data:
            raise HTTPException(
                status_code=400, 
                detail="No update data provided"
            )
        
        result = service.update_vendor(vendor_id, update_data)
        
        return {
            "success": True,
            "message": "Vendor updated successfully",
            "vendor_id": vendor_id,
            "updated_fields": result["updated_fields"]
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{vendor_id}")
async def partial_update_vendor(
    vendor_id: str,
    vendor_update: VendorUpdate,
    service: MatchingService = Depends(get_matching_service)
):
    """
    Partial update vendor (same as PUT, for REST compliance)
    """
    return await update_vendor(vendor_id, vendor_update, service)


@router.post("/sync", response_model=SyncResponse)
async def sync_vendors(
    sync_data: BulkVendorSync,
    service: MatchingService = Depends(get_matching_service)
):
    """Bulk vendor sync from external system"""
    try:
        result = service.sync_vendors_batch(
            vendors=sync_data.vendors,
            force_update=sync_data.force_update
        )
        return SyncResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{vendor_id}")
async def delete_vendor(
    vendor_id: str,
    service: MatchingService = Depends(get_matching_service)
):
    """Delete a vendor from the system"""
    try:
        vendor = service.db.get_vendor(vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        
        service.db.delete_vendor(vendor_id)
        
        return {
            "success": True,
            "message": "Vendor deleted successfully",
            "vendor_id": vendor_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
