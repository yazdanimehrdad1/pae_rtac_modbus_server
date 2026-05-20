"""Validation functions for device config points."""

from pydantic import BaseModel, Field

from schemas.api_models import ConfigPoint

from logger import get_logger

from constants import MODBUS_MAX_REGISTERS_PER_READ as MAX_MODBUS_POLL_REGISTER_COUNT

logger = get_logger(__name__)


class PointsValidationResult(BaseModel):
    errors: list[str] = Field(default_factory=list)
    min_register_number: int = 0
    poll_count: int = 0

    @property
    def is_valid(self) -> bool:
        return not self.errors


def normalize_and_validate_points(points: list[ConfigPoint]) -> list[str]:
    """
    Set defaults on each point in-place, then validate cross-field constraints.
    Returns a list of error strings (empty = valid).
    """
    errors = []
    for point in points:
        if point.scale_factor in ("", None):
            point.scale_factor = 1.0
        if point.unit in ("", None):
            point.unit = "unit"
        if point.data_type == "bitfield" and not point.bitfield_detail:
            errors.append(f"Point bitfield detail is required for bitfield type at point {point.address}")
        if point.data_type == "enum" and not point.enum_detail:
            errors.append(f"Point enum detail is required for enum type at point {point.address}")
    return errors


def compute_poll_range(points: list[ConfigPoint]) -> tuple[int, int, int]:
    """
    Compute min point address, max point end, and poll count.
    """
    min_register_number = min(point.address for point in points)
    max_register_end = max(point.address + point.size - 1 for point in points)
    poll_count = max_register_end - min_register_number + 1
    return min_register_number, max_register_end, poll_count


def validate_duplicate_points(points: list[ConfigPoint]) -> str | None:
    """
    Check for overlapping point address ranges.
    Returns an error string if an overlap is found, otherwise None.
    """
    ranges: list[tuple[int, int, int]] = []  # (start, end, index)
    for idx, point in enumerate(points):
        start = point.address
        end = point.address + point.size - 1

        for r_start, r_end, r_idx in ranges:
            if start <= r_end and end >= r_start:
                return (
                    f"Point at index {idx} (address {start}-{end}) overlaps "
                    f"with point at index {r_idx} (address {r_start}-{r_end})"
                )
        ranges.append((start, end, idx))
    return None


def validate_poll_range_consistency(
    poll_count: int,
    min_register_number: int,
    max_register_end: int,
    payload_poll_start_index: int,
) -> str | None:
    """
    Validate poll count does not exceed the Modbus maximum.
    Logs a warning if the computed start address differs from the requested poll_start_index.
    Returns: Error message if poll count exceeds max, else None.
    """
    if poll_count > MAX_MODBUS_POLL_REGISTER_COUNT:
        return "The number of points to poll exceeds the maximum allowed, consider adding multiple configs"

    if min_register_number != payload_poll_start_index:
        logger.warning(
            "Min point address does not match requested poll_start_index; overriding with computed value",
            extra={
                "min_register_number": min_register_number,
                "max_register_end": max_register_end,
                "computed_poll_count": poll_count,
                "payload_poll_start_index": payload_poll_start_index,
            },
        )

    return None


def validate_point_addresses(poll_start_index: int, points: list[ConfigPoint]) -> PointsValidationResult:
    """
    Single entry point for config point validation. All errors are collected
    and returned — nothing is raised. Check .is_valid before proceeding.
    """
    errors: list[str] = []
    field_errors = normalize_and_validate_points(points)
    if field_errors:
        errors.extend(field_errors)
    duplicate_error = validate_duplicate_points(points)
    if duplicate_error:
        errors.append(duplicate_error)
    min_register_number, max_register_end, poll_count = compute_poll_range(points)
    range_error = validate_poll_range_consistency(
        poll_count=poll_count,
        min_register_number=min_register_number,
        max_register_end=max_register_end,
        payload_poll_start_index=poll_start_index,
    )
    if range_error:
        errors.append(range_error)
    return PointsValidationResult(
        errors=errors,
        min_register_number=min_register_number,
        poll_count=poll_count,
    )
