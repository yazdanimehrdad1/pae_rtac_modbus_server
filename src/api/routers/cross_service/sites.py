"""Sites Manager cross-service endpoints."""

from typing import Any, Dict
import httpx
from fastapi import APIRouter, HTTPException, status

from config import settings
from logger import get_logger

router = APIRouter(prefix="/cross-service", tags=["cross-service"])
logger = get_logger(__name__)


@router.get("/sites")
async def get_sites() -> Dict[str, Any]:
    """
    Get all sites from the Sites Manager service.
    
    Makes a GET request to {{sites_manager_base_url}}/api/v1/sites
    
    Returns:
        Dictionary containing the sites data from Sites Manager
    """
    try:
        url = f"{settings.sites_manager_base_url}/api/v1/sites"
        logger.info(f"Making GET request to Sites Manager: {url}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            sites_data = response.json()
            logger.info(f"Successfully retrieved {len(sites_data) if isinstance(sites_data, list) else 'data'} from Sites Manager")
            return sites_data
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Sites Manager returned error status {e.response.status_code}: {e.response.text}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Sites Manager error: {e.response.text}"
        )
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to Sites Manager: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to connect to Sites Manager: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error calling Sites Manager: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )

