"""Device points CRUD operations."""

from typing import Optional
from sqlalchemy import select

from db.connection import get_async_session_factory
from schemas.api_models import DevicePointData
from schemas.api_models.requests import DevicePointCreateRequest, DevicePointUpdateRequest, DevicePointsBulkRequest
from schemas.api_models.responses import DevicePointResponse
from schemas.db_models.orm_models import Device, DevicePoint
from helpers.device_points.scan_range_computation import compute_device_scan_ranges
from utils.exceptions import InternalError, NotFoundError, ConflictError, ValidationError


async def _recompute_scan_ranges(session, device_id: int) -> None:
    """Recompute and persist scan ranges unless device is locked. Must be called inside an open session before commit."""
    device_result = await session.execute(select(Device).where(Device.device_id == device_id))
    device = device_result.scalar_one_or_none()
    if device is None or device.scan_ranges_locked:
        return

    points_result = await session.execute(
        select(DevicePoint).where(DevicePoint.device_id == device_id, DevicePoint.category == "NATIVE")
    )
    native_responses = [
        DevicePointResponse.model_validate(p, from_attributes=True)
        for p in points_result.scalars().all()
    ]
    ranges = compute_device_scan_ranges(native_responses)
    device.scan_ranges = ranges.model_dump()


async def create_device_points(device_points_list: list[DevicePointData]) -> bool:
    """
    Persist a list of DevicePointData to the database.
    Uniqueness is guaranteed by the caller (validate_device_points_uniqueness).
    """
    if not device_points_list:
        return True
    try:
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            new_points = [DevicePoint(**point.model_dump()) for point in device_points_list]
            session.add_all(new_points)
            await session.commit()
        return True
    except Exception as e:
        raise InternalError(f"Failed to create device points: {str(e)}")


async def get_device_points(device_id: int, category: str | None = None) -> list[DevicePoint]:
    """Get all points for a specific device, optionally filtered by category."""
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        query = (
            select(DevicePoint)
            .where(DevicePoint.device_id == device_id)
            .order_by(DevicePoint.address.asc())
        )
        if category is not None:
            query = query.where(DevicePoint.category == category.upper())
        result = await session.execute(query)
        return list(result.scalars().all())


async def get_device_point(point_id: int) -> Optional[DevicePoint]:
    """Get a single device point by primary key."""
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(DevicePoint).where(DevicePoint.id == point_id))
        return result.scalar_one_or_none()


async def create_device_point(
    site_id: int, device_id: int, data: DevicePointCreateRequest
) -> DevicePoint:
    """
    Create a single device point directly (Config-free).
    Validates NATIVE-specific fields and triggers scan range recompute.
    """
    if data.category == "NATIVE":
        if data.poll_kind is None:
            raise ValidationError("poll_kind is required for NATIVE points")
        if data.address is None:
            raise ValidationError("address is required for NATIVE points")

    session_factory = get_async_session_factory()
    async with session_factory() as session:
        existing = await session.execute(
            select(DevicePoint).where(
                DevicePoint.device_id == device_id,
                DevicePoint.name == data.name,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError(f"A point named '{data.name}' already exists on device {device_id}")

        new_point = DevicePoint(
            site_id=site_id,
            device_id=device_id,
            name=data.name,
            poll_kind=data.poll_kind,
            address=data.address if data.address is not None else 0,
            size=data.size,
            data_type=data.data_type,
            scale_factor=data.scale_factor,
            unit=data.unit,
            byte_order=data.byte_order,
            word_order=data.word_order,
            register_offset=data.register_offset,
            bitfield_detail=data.bitfield_detail,
            enum_detail=data.enum_detail,
            category=data.category,
        )
        session.add(new_point)
        await session.flush()
        await _recompute_scan_ranges(session, device_id)
        await session.commit()
        await session.refresh(new_point)
        return new_point


async def update_device_point(
    point_id: int, data: DevicePointUpdateRequest
) -> DevicePoint:
    """Update a device point and trigger scan range recompute."""
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(DevicePoint).where(DevicePoint.id == point_id))
        point = result.scalar_one_or_none()
        if point is None:
            raise NotFoundError(f"Device point {point_id} not found")

        if data.name is not None:
            existing = await session.execute(
                select(DevicePoint).where(
                    DevicePoint.device_id == point.device_id,
                    DevicePoint.name == data.name,
                    DevicePoint.id != point_id,
                )
            )
            if existing.scalar_one_or_none() is not None:
                raise ConflictError(f"A point named '{data.name}' already exists on device {point.device_id}")
            point.name = data.name

        if data.poll_kind is not None:
            point.poll_kind = data.poll_kind
        if data.address is not None:
            point.address = data.address
        if data.size is not None:
            point.size = data.size
        if data.data_type is not None:
            point.data_type = data.data_type
        if data.scale_factor is not None:
            point.scale_factor = data.scale_factor
        if data.unit is not None:
            point.unit = data.unit
        if data.byte_order is not None:
            point.byte_order = data.byte_order
        if data.word_order is not None:
            point.word_order = data.word_order
        if data.register_offset is not None:
            point.register_offset = data.register_offset
        if data.bitfield_detail is not None:
            point.bitfield_detail = data.bitfield_detail
        if data.enum_detail is not None:
            point.enum_detail = data.enum_detail

        device_id = point.device_id
        await _recompute_scan_ranges(session, device_id)
        await session.commit()
        await session.refresh(point)
        return point


async def delete_device_point(point_id: int) -> bool:
    """Delete a device point and trigger scan range recompute."""
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(DevicePoint).where(DevicePoint.id == point_id))
        point = result.scalar_one_or_none()
        if point is None:
            return False

        device_id = point.device_id
        await session.delete(point)
        await session.flush()
        await _recompute_scan_ranges(session, device_id)
        await session.commit()
        return True


async def bulk_upsert_device_points(
    site_id: int, device_id: int, bulk: DevicePointsBulkRequest
) -> list[DevicePoint]:
    """
    Upsert multiple device points in one transaction.
    Points are matched by name: existing names are updated, new names are created.
    Scan range recompute runs once at the end.
    """
    for point in bulk.points:
        if point.category == "NATIVE":
            if point.poll_kind is None:
                raise ValidationError(f"poll_kind is required for NATIVE point '{point.name}'")
            if point.address is None:
                raise ValidationError(f"address is required for NATIVE point '{point.name}'")

    session_factory = get_async_session_factory()
    async with session_factory() as session:
        existing_result = await session.execute(
            select(DevicePoint).where(DevicePoint.device_id == device_id)
        )
        existing_by_name: dict[str, DevicePoint] = {
            p.name: p for p in existing_result.scalars().all()
        }

        upserted: list[DevicePoint] = []
        for data in bulk.points:
            if data.name in existing_by_name:
                point = existing_by_name[data.name]
                if data.poll_kind is not None:
                    point.poll_kind = data.poll_kind
                if data.address is not None:
                    point.address = data.address
                if data.size is not None:
                    point.size = data.size
                if data.data_type is not None:
                    point.data_type = data.data_type
                if data.scale_factor is not None:
                    point.scale_factor = data.scale_factor
                if data.unit is not None:
                    point.unit = data.unit
                if data.byte_order is not None:
                    point.byte_order = data.byte_order
                if data.word_order is not None:
                    point.word_order = data.word_order
                if data.register_offset is not None:
                    point.register_offset = data.register_offset
                if data.bitfield_detail is not None:
                    point.bitfield_detail = data.bitfield_detail
                if data.enum_detail is not None:
                    point.enum_detail = data.enum_detail
                upserted.append(point)
            else:
                new_point = DevicePoint(
                    site_id=site_id,
                    device_id=device_id,
                    name=data.name,
                    poll_kind=data.poll_kind,
                    address=data.address if data.address is not None else 0,
                    size=data.size,
                    data_type=data.data_type,
                    scale_factor=data.scale_factor,
                    unit=data.unit,
                    byte_order=data.byte_order,
                    word_order=data.word_order,
                    register_offset=data.register_offset,
                    bitfield_detail=data.bitfield_detail,
                    enum_detail=data.enum_detail,
                    category=data.category,
                )
                session.add(new_point)
                upserted.append(new_point)

        await session.flush()
        await _recompute_scan_ranges(session, device_id)
        await session.commit()

        for pt in upserted:
            await session.refresh(pt)
        return upserted
