"""Validation functions for device config points."""

from schemas.api_models import ConfigPoint
from schemas.api_models.validation import PointValidationError, PointAddressValidationResult
from utils.exceptions import ConflictError
from logger import get_logger

logger = get_logger(__name__)

MAX_MODBUS_POLL_REGISTER_COUNT = 125


def set_point_defaults(points: list[ConfigPoint]) -> None:
    """
    Set default values for point fields in-place.
    """
    for point in points:
        if point.scale_factor in ("", None):
            point.scale_factor = 1.0
        if point.unit in ("", None):
            point.unit = "unit"


def _get_point_attr(point: ConfigPoint, key: str, default=None):
    if hasattr(point, key):
        return getattr(point, key, default)
    return default


def compute_poll_range(points: list) -> tuple[int, int, int]:
    """
    Compute min point address, max point end, and poll count.
    """
    addresses = [_get_point_attr(point, "address") for point in points]
    sizes = [_get_point_attr(point, "size", 1) for point in points]
    min_register_number = min(addresses)
    max_register_end = max(
        address + size - 1
        for address, size in zip(addresses, sizes)
    )
    poll_count = max_register_end - min_register_number + 1
    return min_register_number, max_register_end, poll_count


def validate_duplicate_points(points: list) -> None:
    """
    Validate no duplicate or overlapping point address ranges exist.
    """
    ranges: list[tuple[int, int, int]] = []  # (start, end, index)
    for idx, point in enumerate(points):
        if isinstance(point, dict):
            point_data = point
        elif hasattr(point, "model_dump"):
            point_data = point.model_dump()
        else:
            point_data = vars(point)

        addr = point_data.get("address")
        size = point_data.get("size", 1)
        if addr is None:
            continue

        start = addr
        end = addr + size - 1

        # Check for overlaps with previously processed points
        for r_start, r_end, r_idx in ranges:
            if start <= r_end and end >= r_start:
                raise ConflictError(
                    f"Point at index {idx} (address {start}-{end}) overlaps with point at index {r_idx} (address {r_start}-{r_end})",
                    payload={
                        "error_type": "Overlapping point addresses",
                        "overlap": {
                            "point1": {"index": r_idx, "address": r_start, "end": r_end},
                            "point2": {"index": idx, "address": start, "end": end}
                        }
                    }
                )
        ranges.append((start, end, idx))


def validate_point_addresses(poll_start_index: int, points: list) -> PointAddressValidationResult:
    """
    Validate point addresses are within allowed poll range.
    Returns: PointAddressValidationResult
    """
    validate_duplicate_points(points)
    max_address = poll_start_index + MAX_MODBUS_POLL_REGISTER_COUNT
    result = PointAddressValidationResult()
    for idx, point in enumerate(points):
        if isinstance(point, dict):
            point_data = point
        elif hasattr(point, "model_dump"):
            point_data = point.model_dump()
        else:
            point_data = vars(point)

        point_address = point_data.get("address")
        point_size = point_data.get("size")

        if point_address is None:
            result.missing_fields.append(
                PointValidationError(
                    index=idx,
                    field="address",
                    message=f"The 'points[{idx}].address' field is required",
                )
            )
            continue
        if point_size is None:
            result.missing_fields.append(
                PointValidationError(
                    index=idx,
                    field="size",
                    message=f"The 'points[{idx}].size' field is required",
                )
            )
            continue
        if not point_data.get("name"):
            result.missing_fields.append(
                PointValidationError(
                    index=idx,
                    field="name",
                    message=f"The 'points[{idx}].name' field is required",
                )
            )
            continue
        if not point_data.get("data_type"):
            result.missing_fields.append(
                PointValidationError(
                    index=idx,
                    field="data_type",
                    message=f"The 'points[{idx}].data_type' field is required",
                )
            )
            continue

        if point_address < poll_start_index:
            result.invalid_registers.append(
                PointValidationError(
                    index=idx,
                    address=point_address,
                    error=(
                        f"address ({point_address}) is less than poll_start_index "
                        f"({poll_start_index})"
                    ),
                )
            )
            continue

        max_register_address = point_address + point_size - 1
        if max_register_address > max_address:
            result.invalid_registers.append(
                PointValidationError(
                    index=idx,
                    address=point_address,
                    size=point_size,
                    max_address=max_register_address,
                    error=(
                        f"address ({point_address}) + size ({point_size}) - 1 = "
                        f"{max_register_address} exceeds poll_start_index + {MAX_MODBUS_POLL_REGISTER_COUNT} "
                        f"({max_address})"
                    ),
                )
            )

    return result


def validate_config_points_fields(points: list) -> list[str]:
    """
    Validate the fields of the points in the config.
    Returns: list of error messages.
    """
    errors = []
    for point in points:
        addr = point.address
        if not point.name:
            errors.append(f"Point name is required for point {addr}")
        if addr is None:
            errors.append(f"Point address is required")
        if not point.size:
            errors.append(f"Point size is required for point {addr}")
        if not point.data_type:
            errors.append(f"Point data type is required for point {addr}")
        if point.data_type not in ["enum", "bitfield"] and point.scale_factor is None:
            errors.append(f"Point scale factor is required for point {addr}")
        if point.data_type not in ["enum", "bitfield"] and not point.unit:
            errors.append(f"Point unit is required for point {addr}")
        if point.data_type == "bitfield" and not point.bitfield_detail:
            errors.append(f"Point bitfield detail is required for bitfield type at point {addr}")
        if point.data_type == "enum" and not point.enum_detail:
            errors.append(f"Point enum detail is required for enum type at point {addr}")

    return errors


def validate_poll_range_consistency(
    poll_count: int,
    min_register_number: int,
    max_register_end: int,
    points: list,
    payload_poll_start_index: int,
    payload_poll_count: int,
) -> str | None:
    """
    Validate poll count limits and consistency with payload values.
    Returns: Error message if poll count exceeds max, else None.
    """
    if poll_count > MAX_MODBUS_POLL_REGISTER_COUNT:
        return "The number of points to poll exceeds the maximum allowed, consider adding multiple configs"

    if min_register_number != payload_poll_start_index or poll_count != payload_poll_count:
        logger.warning(
            "Min point address or poll count does not match the config; overriding with computed values",
            extra={
                "min_register_number": min_register_number,
                "max_register_end": max_register_end,
                "computed_poll_count": poll_count,
                "payload_poll_start_index": payload_poll_start_index,
                "payload_poll_count": payload_poll_count,
            },
        )

    return None
