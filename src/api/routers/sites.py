"""Site management endpoints."""

from typing import List
from fastapi import APIRouter, HTTPException, status

from schemas.db_models.models import (
    SiteComprehensiveResponse,
    SiteCreateRequest,
    SiteUpdate,
    SiteResponse,
    SiteDeleteResponse,
)
from helpers.sites import get_complete_site_data
from db.sites import create_site, get_all_sites, get_site_by_id, update_site, delete_site
from utils.exceptions import AppError, NotFoundError, ConflictError, ValidationError, InternalError
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
        return await get_all_sites()
    except AppError as e:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if isinstance(e, NotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(e, ConflictError):
            status_code = status.HTTP_409_CONFLICT
        elif isinstance(e, ValidationError):
            status_code = status.HTTP_400_BAD_REQUEST
            
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred"
        )


@router.post("/", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_new_site(site: SiteCreateRequest):
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
        return await create_site(site)
    except AppError as e:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if isinstance(e, NotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(e, ConflictError):
            status_code = status.HTTP_409_CONFLICT
        elif isinstance(e, ValidationError):
            status_code = status.HTTP_400_BAD_REQUEST
            
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred"
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
    except AppError as e:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if isinstance(e, NotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(e, ConflictError):
            status_code = status.HTTP_409_CONFLICT
        elif isinstance(e, ValidationError):
            status_code = status.HTTP_400_BAD_REQUEST
            
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=status_code, detail=detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred"
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
        return await update_site(site_id, site_update)
    except AppError as e:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if isinstance(e, NotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(e, ConflictError):
            status_code = status.HTTP_409_CONFLICT
        elif isinstance(e, ValidationError):
            status_code = status.HTTP_400_BAD_REQUEST
            
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred"
        )

#TODO" lets make sure cascade delete is implemented and soft delete is implemented
@router.delete("/{site_id}", response_model=SiteDeleteResponse)
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
        return {"site_id": deleted_site.site_id}
    except AppError as e:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if isinstance(e, NotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(e, ConflictError):
            status_code = status.HTTP_409_CONFLICT
        elif isinstance(e, ValidationError):
            status_code = status.HTTP_400_BAD_REQUEST
            
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=status_code, detail=detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred"
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
    except AppError as e:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if isinstance(e, NotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(e, ConflictError):
            status_code = status.HTTP_409_CONFLICT
        elif isinstance(e, ValidationError):
            status_code = status.HTTP_400_BAD_REQUEST
            
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=status_code, detail=detail)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred"
        )
