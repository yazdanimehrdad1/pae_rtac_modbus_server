"""Site management endpoints."""

from typing import List
from fastapi import APIRouter, HTTPException, status

from schemas.db_models.models import SiteComprehensiveResponse, SiteCreate, SiteUpdate, SiteResponse
from helpers.sites import get_complete_site_data
from db.sites import create_site, get_all_sites, get_site_by_id, update_site, delete_site
from logger import get_logger

router = APIRouter(prefix="/sites", tags=["sites"])
logger = get_logger(__name__)


@router.get("/", response_model=List[SiteResponse])
async def get_all_sites_endpoint():
    """
    Get all sites.
    
    Returns:
        List of all sites
    """
    try:
        sites = await get_all_sites()
        return sites
    except Exception as e:
        logger.error(f"Error getting all sites: {e}", exc_info=True)
        error_detail = {
            "error": "Failed to retrieve sites",
            "error_type": type(e).__name__,
            "message": str(e)
        }
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.post("/", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_new_site(site: SiteCreate):
    """
    Create a new site.
    
    Args:
        site: Site creation data
        
    Returns:
        Created site with ID and timestamps
        
    Raises:
        HTTPException: If site name already exists or database error occurs
    """
    try:
        created_site = await create_site(site)
        return created_site
    except ValueError as e:
        # Handle unique constraint violation (duplicate name) or validation errors
        error_msg = str(e)
        if "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "Site name already exists",
                    "message": error_msg,
                    "site_name": site.name
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation error",
                    "message": error_msg
                }
            )
    except RuntimeError as e:
        # Handle database errors from the database layer
        logger.error(f"Runtime error creating site: {e}", exc_info=True)
        error_detail = {
            "error": "Failed to create site",
            "error_type": "RuntimeError",
            "message": str(e)
        }
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )
    except Exception as e:
        logger.error(f"Unexpected error creating site: {e}", exc_info=True)
        # Include error details for better debugging
        error_detail = {
            "error": "Failed to create site",
            "error_type": type(e).__name__,
            "message": str(e)
        }
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(site_id: int):
    """
    Get a site by its ID (UUID).
    
    Args:
        site_id: Site UUID
        
    Returns:
        Site data
        
    Raises:
        HTTPException: If site not found
    """
    try:
        site = await get_site_by_id(site_id)
        if site is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site with id {site_id} not found"
            )
        return site
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting site: {e}", exc_info=True)
        error_detail = {
            "error": "Failed to retrieve site",
            "error_type": type(e).__name__,
            "message": str(e),
            "site_id": site_id
        }
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.put("/{site_id}", response_model=SiteResponse)
async def update_site_endpoint(site_id: int, site_update: SiteUpdate):
    """
    Update a site.
    
    Args:
        site_id: Site UUID
        site_update: Site update data (only provided fields will be updated)
        
    Returns:
        Updated site with new timestamps
        
    Raises:
        HTTPException: If site not found or name already exists
    """
    try:
        updated_site = await update_site(site_id, site_update)
        return updated_site
    except ValueError as e:
        # Handle not found or unique constraint violation
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
    except Exception as e:
        logger.error(f"Error updating site: {e}", exc_info=True)
        error_detail = {
            "error": "Failed to update site",
            "error_type": type(e).__name__,
            "message": str(e),
            "site_id": site_id
        }
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )

#TODO" lets make sure cascade delete is implemented and soft delete is implemented
@router.delete("/{site_id}", response_model=SiteResponse)
async def delete_site_endpoint(site_id: int):
    """
    Delete a site.
    
    Args:
        site_id: Site UUID
        
    Returns:
        Deleted site metadata
        
    Raises:
        HTTPException: If site not found
    """
    try:
        deleted_site = await delete_site(site_id)
        if deleted_site is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site with id {site_id} not found"
            )
        return deleted_site
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting site: {e}", exc_info=True)
        error_detail = {
            "error": "Failed to delete site",
            "error_type": type(e).__name__,
            "message": str(e),
            "site_id": site_id
        }
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )

@router.get("/comprehensive/{site_id}", response_model=SiteComprehensiveResponse)
async def get_comprehensive_site_endpoint(site_id: int):
    """
    Get a comprehensive site.
    
    Args:
        site_id: Site UUID
        
    Returns:
        Comprehensive site data with devices and configs
    """
    try:
        site = await get_complete_site_data(site_id)
        if site is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Site with id {site_id} not found"
            )
        return site
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting comprehensive site: {e}", exc_info=True)
        error_detail = {
            "error": "Failed to retrieve comprehensive site",
            "error_type": type(e).__name__,
            "message": str(e),
            "site_id": site_id
        }
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )
