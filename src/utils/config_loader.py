"""
Register map CSV loader for startup initialization.

Loads register map CSV files from the config folder and syncs them to the database.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List, TypedDict, Tuple
import json

from db.devices import get_device_id_by_name, create_device
from db.device_register_map import create_register_map, update_register_map, get_register_map_by_device_id
from schemas.db_models.models import DeviceCreate
from utils.map_csv_to_json import map_csv_to_json
from config import settings
from logger import get_logger

logger = get_logger(__name__)


class DeviceLoadResult(TypedDict, total=False):
    """Result metadata from loading a device register map."""
    device_name: str
    device_id: int
    success: bool
    device_created: bool
    register_map_created: bool
    error: Optional[str]


async def create_and_store_device_from_config(
    device_name: str,
    device_config: Dict[str, Any]
) -> Tuple[Optional[int], bool]:
    """
    Create and store a device in the database from configuration.
    
    Args:
        device_name: Device name/identifier
        device_config: Device configuration dict with host, port, device_id, etc.
        
    Returns:
        Tuple of (device_id, device_created):
        - device_id: Database ID of the device (None if creation failed)
        - device_created: True if device was created, False if it already existed
    """
    # Check if device already exists
    db_device_id = await get_device_id_by_name(device_name)
    if db_device_id is not None:
        logger.debug(f"Device '{device_name}' already exists in database (ID: {db_device_id})")
        return db_device_id, False
    
    # Check for required fields
    host = device_config.get("host")
    if not host:
        error_msg = f"Cannot create device '{device_name}': missing required field 'host' in config."
        logger.error(error_msg)
        return None, False
    
    # Create device with config data
    try:
        device_create = DeviceCreate(
            name=device_name,
            host=host,
            port=device_config.get("port", 502),  # Default to 502
            device_id=device_config.get("device_id", 1),  # Default to 1
            description=device_config.get("description"),
            poll_address=device_config.get("poll_address"),
            poll_count=device_config.get("poll_count"),
            poll_kind=device_config.get("poll_kind"),
            poll_enabled=device_config.get("poll_enabled", True)
        )
        
        created_device = await create_device(device_create)
        db_device_id = created_device.id
        logger.info(f"Created device '{device_name}' (ID: {db_device_id})")
        return db_device_id, True
    except ValueError as e:
        # Device might have been created by another process, try to get it again
        db_device_id = await get_device_id_by_name(device_name)
        if db_device_id is None:
            error_msg = f"Failed to create device '{device_name}': {e}"
            logger.error(error_msg)
            return None, False
        logger.info(f"Device '{device_name}' was created by another process (ID: {db_device_id})")
        return db_device_id, False
    except Exception as e:
        error_msg = f"Unexpected error creating device '{device_name}': {e}"
        logger.error(error_msg, exc_info=True)
        return None, False


async def create_and_store_register_map_from_csv(
    csv_path: Path,
    device_name: str,
    device_id: int
) -> DeviceLoadResult:
    """
    Load a single register map CSV file into the database.
    
    This function:
    1. Converts CSV to JSON format
    2. Creates register map in database only if it doesn't already exist
    
    Args:
        csv_path: Path to the CSV file
        device_name: Device name (required)
        device_id: Database ID of the device (required)
        
    Returns:
        DeviceLoadResult with metadata about the loaded register map (success field indicates if loading succeeded)
    """
    try:
        logger.info(f"Processing register map CSV for device: {device_name}")
        
        # Step 1: Convert CSV to JSON
        try:
            register_map_json = map_csv_to_json(csv_path)
        except Exception as e:
            error_msg = f"Failed to convert CSV to JSON for device '{device_name}': {e}"
            logger.error(error_msg)
            return DeviceLoadResult(
                device_name=device_name,
                device_id=device_id,
                success=False,
                device_created=False,
                register_map_created=False,
                error=error_msg
            )
        
        # Step 2: Create register map only if it doesn't already exist
        existing_map = await get_register_map_by_device_id(device_id)
        register_map_created = False
        
        if existing_map is None:
            # Create new register map
            try:
                await create_register_map(device_id, register_map_json)
                register_map_created = True
                logger.info(f"Created register map for device '{device_name}' (ID: {device_id})")
            except ValueError as e:
                # Map might have been created by another process
                logger.warning(f"Register map creation failed (may already exist): {e}")
                # Verify it now exists
                existing_map = await get_register_map_by_device_id(device_id)
                if existing_map is None:
                    error_msg = f"Could not create register map for device '{device_name}'"
                    logger.error(error_msg)
                    return DeviceLoadResult(
                        device_name=device_name,
                        device_id=device_id,
                        success=False,
                        device_created=False,
                        register_map_created=False,
                        error=error_msg
                    )
                else:
                    logger.info(f"Register map already exists for device '{device_name}' (ID: {device_id}), skipping")
        else:
            # Register map already exists, skip
            logger.info(f"Register map already exists for device '{device_name}' (ID: {device_id}), skipping")
        
        return DeviceLoadResult(
            device_name=device_name,
            device_id=device_id,
            success=True,
            device_created=False,  # Device creation is handled separately
            register_map_created=register_map_created,
            error=None
        )
        
    except Exception as e:
        error_msg = f"Unexpected error loading register map from CSV '{csv_path}': {e}"
        logger.error(error_msg, exc_info=True)
        return DeviceLoadResult(
            device_name=device_name or "",
            device_id=0,
            success=False,
            device_created=False,
            register_map_created=False,
            error=error_msg
        )


def read_device_configs_from_json(config_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Read device configurations from JSON config file.
    
    Reads the device_register_maps.json file from the config directory
    which maps device names to their associated CSV file paths and device_id.
    
    Expected JSON format:
    {
      "device-name": {
        "csv_file": "file.csv",
        "host": "192.168.1.100",  # Required for device creation
        "port": 502,  # Optional, defaults to 502
        "device_id": 1,  # Optional, defaults to 1
        "description": "Device description",  # Optional
        "poll_address": 1400,
        "poll_count": 100,
        "poll_kind": "holding",
        "poll_enabled": true
      }
    }
    
    Args:
        config_dir: Path to the config directory
        
    Returns:
        Dictionary mapping device names to config objects with 'csv_file', 'device_id', 
        and optional polling configuration fields
    """
    config_file = config_dir / "device_register_maps.json"
    
    if not config_file.exists():
        logger.warning(f"Device register map config file not found: {config_file}")
        return {}
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            device_configs_mapping = json.load(f)
        
        if not isinstance(device_configs_mapping, dict):
            logger.error(f"Invalid format in {config_file}: expected JSON object")
            return {}
        
        # Validate and normalize the config format
        normalized_mapping = {}
        for device_name, config_value in device_configs_mapping.items():
            if isinstance(config_value, str):
                # Legacy format: just a string (CSV filename)
                # Note: Legacy format cannot create devices (missing required 'host' field)
                normalized_mapping[device_name] = {
                    "csv_file": config_value,
                    "host": None,  # Missing - device cannot be auto-created
                    "port": None,
                    "device_id": None,
                    "description": None,
                    "poll_address": None,
                    "poll_count": None,
                    "poll_kind": None,
                    "poll_enabled": True  # Default to enabled
                }
            elif isinstance(config_value, dict):
                # New format: object with csv_file, device_id, host, port, and optional polling config
                device_id_value = config_value.get("device_id")
                normalized_mapping[device_name] = {
                    "csv_file": config_value.get("csv_file"),
                    "host": config_value.get("host"),  # Required for device creation
                    "port": config_value.get("port"),  # Optional, defaults to 502
                    "device_id": device_id_value,  # Optional, defaults to 1
                    "description": config_value.get("description"),  # Optional
                    "poll_address": config_value.get("poll_address"),
                    "poll_count": config_value.get("poll_count"),
                    "poll_kind": config_value.get("poll_kind"),
                    "poll_enabled": config_value.get("poll_enabled", True)  # Default to enabled
                }
            else:
                logger.warning(f"Invalid config format for device '{device_name}', skipping")
                continue
        
        logger.info(f"Read device configs from JSON with {len(normalized_mapping)} device(s)")
        return normalized_mapping
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON config file {config_file}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Failed to load device register map config from {config_file}: {e}")
        return {}


def get_device_polling_config(device_name: str, config_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    Get polling configuration for a device from device_register_maps.json.
    
    Returns polling configuration with defaults from settings if not specified in JSON.
    
    Args:
        device_name: Device name/identifier
        config_dir: Optional path to config directory (defaults to settings-based path)
        
    Returns:
        Dictionary with polling configuration:
        {
            "poll_address": int,
            "poll_count": int,
            "poll_kind": str,
            "poll_enabled": bool
        }
        Returns None if device not found in config
    """
    if config_dir is None:
        # Default to config directory relative to project root
        config_dir = Path(__file__).parent.parent.parent / "config"
    
    # Load device config
    device_configs = read_device_configs_from_json(config_dir)
    
    if device_name not in device_configs:
        logger.warning(f"Device '{device_name}' not found in device_register_maps.json")
        return None
    
    device_config = device_configs[device_name]
    
    # Get polling config with defaults from settings
    polling_config = {
        "poll_address": device_config.get("poll_address") or settings.main_sel_751_poll_address,
        "poll_count": device_config.get("poll_count") or settings.main_sel_751_poll_count,
        "poll_kind": device_config.get("poll_kind") or settings.main_sel_751_poll_kind,
        "poll_enabled": device_config.get("poll_enabled", True)  # Default to enabled
    }
    
    return polling_config

# TODO: maybe consider getting it from the cache instead of the database also if creating in DB add to cache
async def load_device_configs() -> Dict[str, DeviceLoadResult]:
    """
    Load device configurations from file and initialize devices and register maps.
    
    Reads the device_register_maps.json file from the config directory which
    contains device configurations (host, port, device_id, CSV file paths, polling settings).
    
    For each device:
    1. Creates the device in the database if it doesn't exist (requires 'host' in config)
    2. Loads the register map CSV file into the database
    
    Required fields for device creation:
    - name: Device name (from JSON key)
    - host: Modbus device hostname or IP address (REQUIRED)
    
    Optional fields (with defaults):
    - port: Modbus TCP port (defaults to 502)
    - device_id: Modbus unit/slave ID (defaults to 1)
    - description: Device description
    - poll_address, poll_count, poll_kind, poll_enabled: Polling configuration
    
    Returns:
        Dictionary mapping device names to DeviceLoadResult metadata
    """
    config_dir = Path("config")
    results = {}
    
    # Load device to CSV file mapping from JSON config
    device_configs_mapping = read_device_configs_from_json(config_dir)
    
    if not device_configs_mapping:
        logger.info("No device register map mappings found in config file")
        return results
    
    logger.info(f"Loading {len(device_configs_mapping)} register map CSV file(s) into database...")
    
    for device_name, device_config in device_configs_mapping.items():
        csv_filename = device_config.get("csv_file")
        device_id_value = device_config.get("device_id")
        
        if not csv_filename:
            error_msg = f"CSV file not specified for device '{device_name}'"
            logger.error(error_msg)
            results[device_name] = DeviceLoadResult(
                device_name=device_name,
                device_id=0,
                success=False,
                device_created=False,
                register_map_created=False,
                error=error_msg
            )
            continue
        
        # Construct full path to CSV file (relative to config directory)
        csv_path = config_dir / csv_filename
        # TODO: lets add some smart mechanism to find a general csv file if it doesn't exist
        if not csv_path.exists():
            error_msg = f"CSV file not found for device '{device_name}': {csv_path}"
            logger.error(error_msg)
            results[device_name] = DeviceLoadResult(
                device_name=device_name,
                device_id=0,
                success=False,
                device_created=False,
                register_map_created=False,
                error=error_msg
            )
            continue
        
        # Step 1: Create device if it doesn't exist
        device_id, device_created = await create_and_store_device_from_config(
            device_name,
            device_config
        )
        
        if device_id is None:
            # Device creation failed
            error_msg = f"Failed to create or find device '{device_name}'"
            logger.error(error_msg)
            results[device_name] = DeviceLoadResult(
                device_name=device_name,
                device_id=0,
                success=False,
                device_created=False,
                register_map_created=False,
                error=error_msg
            )
            continue
        
        # Step 2: Load the register map
        result = await create_and_store_register_map_from_csv(
            csv_path,
            device_name,
            device_id
        )
        
        # Update result with device creation status
        result["device_created"] = device_created
        results[device_name] = result
    
    # Log summary
    successful = sum(1 for result in results.values() if result.get("success", False))
    failed = len(results) - successful
    devices_created = sum(1 for result in results.values() if result.get("device_created", False))
    register_maps_created = sum(1 for result in results.values() if result.get("register_map_created", False))
    
    if successful > 0:
        logger.info(
            f"Successfully processed {successful} device(s): "
            f"{devices_created} device(s) created, {register_maps_created} register map(s) created"
        )
    if failed > 0:
        logger.warning(f"Failed to process {failed} device(s)")
    
    return results

