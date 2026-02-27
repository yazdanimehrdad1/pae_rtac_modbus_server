from typing import Dict, List, Optional

from fastapi import HTTPException, status

from schemas.db_models.orm_models import DevicePoint


def parse_register_addresses_from_query_param(
    register_addresses: Optional[str],
    points_by_address: Dict[int, DevicePoint],
) -> List[int]:
    if register_addresses:
        try:
            return [int(addr.strip()) for addr in register_addresses.split(",")]
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Invalid register_addresses format. Expected comma-separated "
                    "integers (e.g., '100,101,102')"
                ),
            ) from exc

    # If no register_addresses are provided, get all registers for the device
    return sorted(points_by_address.keys())
