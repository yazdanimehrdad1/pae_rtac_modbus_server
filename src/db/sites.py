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
from sqlalchemy.orm import selectinload

from db.connection import get_async_session_factory
from schemas.db_models.models import SiteCreate, SiteUpdate, SiteResponse, DeviceListItem
from schemas.db_models.orm_models import Site, Device
from logger import get_logger

logger = get_logger(__name__)


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
            
            # Convert coordinates to dict if provided
            coordinates_dict = None
            if site.coordinates:
                coordinates_dict = {"lat": site.coordinates.lat, "lng": site.coordinates.lng}
            
            # Create new Site instance
            new_site = Site(
                owner=site.owner,
                name=site.name,
                location=site.location,
                operator=site.operator,
                capacity=site.capacity,
                description=site.description,
                coordinates=coordinates_dict,
                device_count=0  # New sites start with 0 devices
            )
            
            # Add to session and flush to get the ID
            session.add(new_site)
            await session.flush()  # Flush to get the ID without committing
            
            logger.info(f"Created site: {site.name} (ID: {new_site.id})")
            
            # Commit the transaction
            await session.commit()
            
            # Note: We don't need to refresh since timestamps are set by database defaults
            # and are already available in the object after flush/commit
            
            # Convert coordinates back to Coordinates model if present
            coordinates = None
            if new_site.coordinates:
                from schemas.db_models.models import Coordinates
                coordinates = Coordinates(lat=new_site.coordinates["lat"], lng=new_site.coordinates["lng"])
            
            return SiteResponse(
                id=new_site.id,
                owner=new_site.owner,
                name=new_site.name,
                location=new_site.location,
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
            # Convert coordinates to Coordinates model if present
            coordinates = None
            if site.coordinates:
                from schemas.db_models.models import Coordinates
                coordinates = Coordinates(lat=site.coordinates["lat"], lng=site.coordinates["lng"])
            
            site_responses.append(SiteResponse(
                id=site.id,
                owner=site.owner,
                name=site.name,
                location=site.location,
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


async def get_site_by_id(site_id: str) -> Optional[SiteResponse]:
    """
    Get a site by its ID (UUID).
    
    Args:
        site_id: Site UUID
        
    Returns:
        Site data with associated devices if found, None otherwise
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        # Eagerly load devices relationship
        result = await session.execute(
            select(Site)
            .where(Site.id == site_id)
            .options(selectinload(Site.devices))
        )
        site = result.scalar_one_or_none()
        
        if site is None:
            return None
        
        # Convert coordinates to Coordinates model if present
        coordinates = None
        if site.coordinates:
            from schemas.db_models.models import Coordinates
            coordinates = Coordinates(lat=site.coordinates["lat"], lng=site.coordinates["lng"])
        
        # Convert devices to DeviceListItem models
        devices = []
        if site.devices:
            for device in site.devices:
                devices.append(DeviceListItem(
                    id=device.id,
                    name=device.name,
                    host=device.host,
                    port=device.port,
                    device_id=device.device_id,
                    description=device.description,
                    main_type=device.main_type,
                    sub_type=device.sub_type,
                    port=device.port,
                    device_id=device.device_id,
                    description=device.description,
                    poll_address=device.poll_address,
                    poll_count=device.poll_count,
                    poll_kind=device.poll_kind,
                    poll_enabled=device.poll_enabled if device.poll_enabled is not None else True,
                    site_id=device.site_id,
                    created_at=device.created_at,
                    updated_at=device.updated_at
                ))
        
        return SiteResponse(
            id=site.id,
            owner=site.owner,
            name=site.name,
            location=site.location,
            operator=site.operator,
            capacity=site.capacity,
            device_count=site.device_count,
            description=site.description,
            coordinates=coordinates,
            devices=devices,
            created_at=site.created_at,
            updated_at=site.updated_at,
            last_update=site.last_update
        )


async def update_site(site_id: str, site_update: SiteUpdate) -> SiteResponse:
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
            if site_update.owner is not None:
                site.owner = site_update.owner
            if site_update.name is not None:
                site.name = site_update.name
            if site_update.location is not None:
                site.location = site_update.location
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
            
            # Convert coordinates to Coordinates model if present
            coordinates = None
            if site.coordinates:
                from schemas.db_models.models import Coordinates
                coordinates = Coordinates(lat=site.coordinates["lat"], lng=site.coordinates["lng"])
            
            return SiteResponse(
                id=site.id,
                owner=site.owner,
                name=site.name,
                location=site.location,
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


async def delete_site(site_id: str) -> Optional[SiteResponse]:
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
            
            # Convert coordinates to Coordinates model if present
            coordinates = None
            if site.coordinates:
                from schemas.db_models.models import Coordinates
                coordinates = Coordinates(lat=site.coordinates["lat"], lng=site.coordinates["lng"])
            
            # Store site data before deletion
            site_response = SiteResponse(
                id=site.id,
                owner=site.owner,
                name=site.name,
                location=site.location,
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
            session.delete(site)
            await session.flush()  # Flush to check for constraint violations before commit
            
            await session.commit()
            
            logger.info(f"Successfully deleted site '{site_name_to_delete}' with id {site_id}")
            return site_response
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error deleting site: {e}")
            raise

