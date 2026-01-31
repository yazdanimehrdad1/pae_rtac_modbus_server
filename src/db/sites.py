"""
Site database operations.

Handles CRUD operations for sites table.
Uses SQLAlchemy 2.0+ async ORM.
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from db.connection import get_async_session_factory
from schemas.db_models.models import SiteCreate, SiteUpdate, SiteResponse
from schemas.db_models.orm_models import Device, Site
from logger import get_logger

logger = get_logger(__name__)


SITE_ID_MIN = 1000
SITE_ID_MAX = 9999
SITE_ID_ATTEMPTS = 5


async def _generate_site_id(session: AsyncSession) -> int:
    result = await session.execute(select(Site.id))
    used_ids = {row[0] for row in result.all() if row[0] is not None}
    for candidate in range(SITE_ID_MIN, SITE_ID_MAX + 1):
        if candidate not in used_ids:
            return candidate
    raise ValueError("No available site_id values")


async def create_site(site: SiteCreate) -> SiteResponse:
    """
    Create a new site in the database.
    
    Args:
        site: Site creation data
        
    Returns:
        Created site with ID and timestamps
        
    Raises:
        ValueError: If site name already exists
        IntegrityError: For other database constraint violations
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        try:
            # Check if site name already exists
            existing_site = await session.execute(
                select(Site).where(Site.name == site.name)
            )
            if existing_site.scalar_one_or_none() is not None:
                raise ValueError(f"Site with name '{site.name}' already exists")
            
            # Convert location and coordinates to dicts for storage
            location_dict = site.location.model_dump()
            coordinates_dict = None
            if site.coordinates:
                coordinates_dict = {"lat": site.coordinates.lat, "lng": site.coordinates.lng}
            
            for attempt in range(SITE_ID_ATTEMPTS):
                site_id = await _generate_site_id(session)
                new_site = Site(
                    id=site_id,
                    client_id=site.client_id,
                    name=site.name,
                    location=location_dict,
                    operator=site.operator,
                    capacity=site.capacity,
                    description=site.description,
                    coordinates=coordinates_dict,
                    device_count=0  # New sites start with 0 devices
                )
                
                session.add(new_site)
                try:
                    await session.flush()
                    logger.info(f"Created site: {site.name} (ID: {new_site.id})")
                    
                    await session.commit()
                    
                    # Convert coordinates/location back to models if present
                    coordinates = None
                    if new_site.coordinates:
                        from schemas.db_models.models import Coordinates
                        coordinates = Coordinates(lat=new_site.coordinates["lat"], lng=new_site.coordinates["lng"])
                    location = None
                    if new_site.location:
                        from schemas.db_models.models import Location
                        location = Location(**new_site.location)
                    
                    return SiteResponse(
                        site_id=new_site.id,
                        client_id=new_site.client_id,
                        name=new_site.name,
                        location=location,
                        operator=new_site.operator,
                        capacity=new_site.capacity,
                        device_count=new_site.device_count,
                        description=new_site.description,
                        coordinates=coordinates,
                        created_at=new_site.created_at,
                        updated_at=new_site.updated_at,
                        last_update=new_site.last_update
                    )
                except IntegrityError as e:
                    await session.rollback()
                    error_text = str(e).lower()
                    if "site_pkey" in error_text and attempt < SITE_ID_ATTEMPTS - 1:
                        session.expunge(new_site)
                        continue
                    raise
            
            raise RuntimeError("Unable to create site after multiple site_id attempts")
            
        except IntegrityError as e:
            await session.rollback()
            error_msg = str(e)
            # Check if it's a unique constraint violation
            if "unique" in error_msg.lower() or "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                logger.warning(f"Site name '{site.name}' already exists: {error_msg}")
                raise ValueError(f"Site with name '{site.name}' already exists") from e
            else:
                logger.error(f"Database integrity error creating site '{site.name}': {error_msg}", exc_info=True)
                raise ValueError(f"Database constraint violation: {error_msg}") from e
        except Exception as e:
            await session.rollback()
            error_msg = str(e)
            error_type = type(e).__name__
            logger.error(f"Database error creating site '{site.name}': {error_type}: {error_msg}", exc_info=True)
            raise RuntimeError(f"Failed to create site '{site.name}': {error_type}: {error_msg}") from e


async def get_all_sites() -> List[SiteResponse]:
    """
    Get all sites from the database.
    
    Returns:
        List of all sites
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(Site).order_by(Site.created_at.desc()))
        sites = result.scalars().all()
        
        site_responses = []
        for site in sites:
            # Convert coordinates/location to models if present
            coordinates = None
            if site.coordinates:
                from schemas.db_models.models import Coordinates
                coordinates = Coordinates(lat=site.coordinates["lat"], lng=site.coordinates["lng"])
            location = None
            if site.location:
                from schemas.db_models.models import Location
                location = Location(**site.location)
            
            site_responses.append(SiteResponse(
                site_id=site.id,
                client_id=site.client_id,
                name=site.name,
                location=location,
                operator=site.operator,
                capacity=site.capacity,
                device_count=site.device_count,
                description=site.description,
                coordinates=coordinates,
                created_at=site.created_at,
                updated_at=site.updated_at,
                last_update=site.last_update
            ))
        
        return site_responses


async def get_site_by_id(site_id: int) -> Optional[SiteResponse]:
    """
    Get a site by its ID (UUID).
    
    Args:
        site_id: Site UUID
        
    Returns:
        Site data with associated devices if found, None otherwise
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(Site).where(Site.id == site_id)
        )
        site = result.scalar_one_or_none()
        
        if site is None:
            return None
        
        # Convert coordinates/location to models if present
        coordinates = None
        if site.coordinates:
            from schemas.db_models.models import Coordinates
            coordinates = Coordinates(lat=site.coordinates["lat"], lng=site.coordinates["lng"])
        location = None
        if site.location:
            from schemas.db_models.models import Location
            location = Location(**site.location)
        
        return SiteResponse(
            site_id=site.id,
            client_id=site.client_id,
            name=site.name,
            location=location,
            operator=site.operator,
            capacity=site.capacity,
            device_count=site.device_count,
            description=site.description,
            coordinates=coordinates,
            devices=None,
            created_at=site.created_at,
            updated_at=site.updated_at,
            last_update=site.last_update
        )


async def update_site(site_id: int, site_update: SiteUpdate) -> SiteResponse:
    """
    Update a site in the database.
    
    Args:
        site_id: Site UUID
        site_update: Site update data (only provided fields will be updated)
        
    Returns:
        Updated site with new timestamps
        
    Raises:
        ValueError: If site not found or name already exists
        IntegrityError: For other database constraint violations
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        try:
            # Get existing site
            result = await session.execute(
                select(Site).where(Site.id == site_id)
            )
            site = result.scalar_one_or_none()
            
            if site is None:
                raise ValueError(f"Site with id {site_id} not found")
            
            # Update only provided fields
            if site_update.client_id is not None:
                site.client_id = site_update.client_id
            if site_update.name is not None:
                site.name = site_update.name
            if site_update.location is not None:
                site.location = site_update.location.model_dump()
            if site_update.operator is not None:
                site.operator = site_update.operator
            if site_update.capacity is not None:
                site.capacity = site_update.capacity
            if site_update.description is not None:
                site.description = site_update.description
            if site_update.coordinates is not None:
                site.coordinates = {"lat": site_update.coordinates.lat, "lng": site_update.coordinates.lng}
            elif site_update.coordinates is False:  # Allow clearing coordinates by passing None
                site.coordinates = None
            
            # Update last_update timestamp
            site.last_update = datetime.now(timezone.utc)
            
            # Commit the transaction
            await session.commit()
            
            # Refresh to get the latest data (including updated_at)
            await session.refresh(site)
            
            logger.info(f"Updated site with id {site_id}")
            
            # Convert coordinates/location to models if present
            coordinates = None
            if site.coordinates:
                from schemas.db_models.models import Coordinates
                coordinates = Coordinates(lat=site.coordinates["lat"], lng=site.coordinates["lng"])
            location = None
            if site.location:
                from schemas.db_models.models import Location
                location = Location(**site.location)
            
            return SiteResponse(
                site_id=site.id,
                client_id=site.client_id,
                name=site.name,
                location=location,
                operator=site.operator,
                capacity=site.capacity,
                device_count=site.device_count,
                description=site.description,
                coordinates=coordinates,
                created_at=site.created_at,
                updated_at=site.updated_at,
                last_update=site.last_update
            )
            
        except IntegrityError as e:
            await session.rollback()
            # Check if it's a unique constraint violation
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                logger.warning(f"Site name already exists")
                raise ValueError("Site with this name already exists") from e
            else:
                logger.error(f"Database integrity error updating site: {e}")
                raise
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error updating site: {e}")
            raise


async def delete_site(site_id: int) -> Optional[SiteResponse]:
    """
    Delete a site from the database.
    
    Args:
        site_id: Site UUID
        
    Returns:
        SiteResponse with metadata of the deleted site if found, None if not found
        
    Raises:
        Exception: For database errors
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        try:
            # Get the site to delete
            result = await session.execute(
                select(Site).where(Site.id == site_id)
            )
            site = result.scalar_one_or_none()
            
            if site is None:
                logger.warning(f"Site with id {site_id} not found for deletion")
                return None
            
            device_result = await session.execute(
                select(Device.device_id).where(Device.site_id == site_id)
            )
            device_ids = [row[0] for row in device_result.all()]
            if device_ids:
                joined_ids = ", ".join(str(device_id) for device_id in device_ids)
                raise ValueError(
                    f"Site with id {site_id} has associated devices: {joined_ids}"
                )

            # Convert coordinates/location to models if present
            coordinates = None
            if site.coordinates:
                from schemas.db_models.models import Coordinates
                coordinates = Coordinates(lat=site.coordinates["lat"], lng=site.coordinates["lng"])
            location = None
            if site.location:
                from schemas.db_models.models import Location
                location = Location(**site.location)
            
            # Store site data before deletion
            site_response = SiteResponse(
                site_id=site.id,
                client_id=site.client_id,
                name=site.name,
                location=location,
                operator=site.operator,
                capacity=site.capacity,
                device_count=site.device_count,
                description=site.description,
                coordinates=coordinates,
                created_at=site.created_at,
                updated_at=site.updated_at,
                last_update=site.last_update
            )
            
            # Delete the site
            site_name_to_delete = site.name
            await session.delete(site)
            await session.flush()  # Flush to check for constraint violations before commit
            
            await session.commit()
            
            logger.info(f"Successfully deleted site '{site_name_to_delete}' with id {site_id}")
            return site_response
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error deleting site: {e}")
            raise

