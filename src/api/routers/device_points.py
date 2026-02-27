from fastapi import APIRouter, HTTPException, status
from typing import List

from helpers.device_points import get_device_points
from helpers.devices import get_device_cache_db
from schemas.api_models import DevicePointResponse

router = APIRouter(
    prefix="/device-points",
    tags=["device-points"],
)

@router.get("/site/{site_id}/device/{device_id}", response_model=List[DevicePointResponse])
async def get_points_for_device(site_id: int, device_id: int):
    """
    Get all registered points for a specific device.
    """
    try:
        device = await get_device_cache_db(site_id, device_id)
        if device is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device '{device_id}' not found for site '{site_id}'",
            )
        points = await get_device_points(device_id)
        if not points:
            return []
        return points
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching device points: {str(e)}"
        )
