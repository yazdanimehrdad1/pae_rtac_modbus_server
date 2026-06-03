"""
Sites controller.

Sits between the router and the DB/helper layers.
No cache layer — all reads and writes go directly to the DB.

To add caching in the future, only this file needs to be updated;
the router remains unchanged.
"""

from typing import List, Optional

import db.sites as sites_db
from helpers.sites import get_complete_site_data_with_points
from logger import get_logger
from schemas.api_models import (
    SiteComprehensiveResponse,
    SiteCreateRequest,
    SiteResponse,
    SiteUpdateRequest,
)

logger = get_logger(__name__)


async def get_all_sites() -> List[SiteResponse]:
    return await sites_db.get_all_sites()


async def get_site_by_id(site_id: int) -> Optional[SiteResponse]:
    return await sites_db.get_site_by_id(site_id)


async def create_site(site: SiteCreateRequest) -> SiteResponse:
    return await sites_db.create_site(site)


async def update_site(site_id: int, site_update: SiteUpdateRequest) -> SiteResponse:
    return await sites_db.update_site(site_id, site_update)


async def delete_site(site_id: int) -> Optional[SiteResponse]:
    return await sites_db.delete_site(site_id)


async def get_comprehensive_site(site_id: int) -> Optional[SiteComprehensiveResponse]:
    return await get_complete_site_data_with_points(site_id)
