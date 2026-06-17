"""Site management endpoints."""

from typing import List, Literal
from fastapi import APIRouter, HTTPException, Query, status

from schemas.api_models import (
    SiteComprehensiveResponse,
    SiteCreateRequest,
    SiteUpdateRequest,
    SiteResponse,
    SiteDeleteResponse,
)
from api.controllers.sites import (
    create_site,
    delete_site,
    get_all_sites,
    get_comprehensive_site,
    get_site_by_id,
    restore_site,
    update_site,
)
from utils.exceptions import AppError
from logger import get_logger

router = APIRouter(prefix="/sites", tags=["sites"])
logger = get_logger(__name__)


@router.get("/", response_model=List[SiteResponse])
async def get_all_sites_endpoint(
    include_deleted: bool = Query(False, description="Include soft-deleted sites"),
):
    try:
        return await get_all_sites(include_deleted=include_deleted)
    except AppError as e:
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=e.http_status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal server error occurred")


@router.post("/", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_new_site(site: SiteCreateRequest):
    try:
        return await create_site(site)
    except AppError as e:
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=e.http_status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal server error occurred")


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: int,
    include_deleted: bool = Query(False, description="Return the site even if soft-deleted"),
):
    try:
        site = await get_site_by_id(site_id, include_deleted=include_deleted)
    except AppError as e:
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=e.http_status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal server error occurred")

    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Site with id {site_id} not found")
    return site


@router.put("/{site_id}", response_model=SiteResponse)
async def update_site_endpoint(site_id: int, site_update: SiteUpdateRequest):
    try:
        return await update_site(site_id, site_update)
    except AppError as e:
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=e.http_status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal server error occurred")


@router.delete("/{site_id}", response_model=SiteDeleteResponse)
async def delete_site_endpoint(
    site_id: int,
    mode: Literal["soft", "hard"] = Query(
        "soft",
        description="soft: preserves site_id — restorable via /restore. hard: permanent deletion, requires confirm=true and no active devices.",
    ),
    confirm: bool = Query(False, description="Must be true to execute a hard delete"),
):
    try:
        deleted_site = await delete_site(site_id, mode=mode, confirm=confirm)
    except AppError as e:
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=e.http_status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal server error occurred")

    if deleted_site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Site with id {site_id} not found")
    return SiteDeleteResponse(site_id=deleted_site.site_id, mode=mode)


@router.post("/{site_id}/restore", response_model=SiteResponse)
async def restore_site_endpoint(site_id: int):
    """Restore a soft-deleted site, all its soft-deleted devices, and their soft-deleted points."""
    try:
        site = await restore_site(site_id)
    except AppError as e:
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=e.http_status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal server error occurred")

    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Site with id {site_id} not found")
    return site


@router.get("/comprehensive/{site_id}", response_model=SiteComprehensiveResponse)
async def get_comprehensive_site_endpoint(site_id: int):
    try:
        site = await get_comprehensive_site(site_id)
    except AppError as e:
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=e.http_status_code, detail=detail)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal server error occurred")

    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Site with id {site_id} not found")
    return site
