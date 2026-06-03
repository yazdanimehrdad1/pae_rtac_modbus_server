from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Literal, Optional

from helpers.device_points import get_device_points
from api.controllers.devices import get_device_by_id
from schemas.api_models import DevicePointResponse
from utils.exceptions import AppError

router = APIRouter(
    prefix="/device-points",
    tags=["device-points"],
)

@router.get("/site/{site_id}/device/{device_id}", response_model=List[DevicePointResponse])
async def get_points_for_device(
    site_id: int,
    device_id: int,
    category: Optional[Literal["NATIVE", "STANDARDIZED", "VIRTUAL"]] = Query(
        default=None,
        description="Filter points by category",
    ),
):
    """
    Get all registered points for a specific device.
    """
    try:
        await get_device_by_id(site_id, device_id)
        points = await get_device_points(device_id, category=category)
        if not points:
            return []
        return points
    except AppError as e:
        detail = {"error": type(e).__name__, "message": e.message}
        if e.payload:
            detail.update(e.payload)
        raise HTTPException(status_code=e.http_status_code, detail=detail)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching device points: {str(e)}"
        )
