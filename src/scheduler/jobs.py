"""Polling jobs for Modbus data collection."""

from db.sites import get_all_sites
from logger import get_logger
from utils.poll_device import poll_modbus_registers_per_site

logger = get_logger(__name__)


async def cron_job_poll_modbus_registers_all_sites() -> None:
    """
    Scheduled job to poll Modbus registers for all sites.
    """
    logger.info("Starting Modbus polling job for all sites")
    try:
        all_sites = await get_all_sites()
        logger.info(f"Retrieved {len(all_sites)} site(s) from database")
        for site in all_sites:
            await poll_modbus_registers_per_site(site.site_id)
    except Exception as e:
        logger.error(f"Error in Modbus polling job for all sites: {e}", exc_info=True)
        # Don't re-raise - let scheduler handle retry on next interval



    """
    Scheduled job to poll Modbus registers for all sites.
    """
    logger.info("Starting Modbus polling job for all sites")
    try:
        all_sites = await get_all_sites()
        logger.info(f"Retrieved {len(all_sites)} site(s) from database")
        for site in all_sites:
            await poll_modbus_registers_per_site(site.site_id)
    except Exception as e:
        logger.error(f"Error in Modbus polling job for all sites: {e}", exc_info=True)
        # Don't re-raise - let scheduler handle retry on next interval