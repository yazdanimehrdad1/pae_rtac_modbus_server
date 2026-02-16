"""ORM-to-Pydantic mappers for response models."""

from schemas.api_models import ConfigResponse
from schemas.db_models.orm_models import Config


def config_to_response(config: Config) -> ConfigResponse:
    return ConfigResponse(
        config_id=config.config_id,
        site_id=config.site_id,
        device_id=config.device_id,
        poll_kind=config.poll_kind,
        poll_start_index=config.poll_start_index,
        poll_count=config.poll_count,
        points=config.points,
        is_active=config.is_active,
        created_at=config.created_at,
        updated_at=config.updated_at,
        created_by=config.created_by,
    )
