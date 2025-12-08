"""
Register map CSV loader for startup initialization.

Loads register map CSV files from the config folder and syncs them to the database.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List, TypedDict
import json

from db.devices import get_device_id_by_name
from db.device_register_map import create_register_map, update_register_map, get_register_map_by_device_id
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


async def load_register_map_from_csv(
    csv_path: Path,
    device_name: Optional[str] = None
) -> DeviceLoadResult:
    """
    Load a single register map CSV file into the database.
    
    This function:
    1. Checks if device exists in database, returns error if not found
    2. Converts CSV to JSON format
    3. Creates register map in database only if it doesn't already exist
    
    Args:
        csv_path: Path to the CSV file
        device_name: Device name (required, should be provided from JSON config)
        
    Returns:
        DeviceLoadResult with metadata about the loaded device (success field indicates if loading succeeded)
    """
    try:
        if device_name is None:
            error_msg = f"Device name is required for CSV file: {csv_path}"
            logger.error(error_msg)
            return DeviceLoadResult(
                device_name="",
                device_id=0,
                success=False,
                device_created=False,
                register_map_created=False,
                error=error_msg
            )
        
        logger.info(f"Processing register map CSV for device: {device_name}")
        
        # Step 2: Check if device exists in database
        db_device_id = await get_device_id_by_name(device_name)
        
        if db_device_id is None:
            # Device doesn't exist, log error and return
            error_msg = f"Device '{device_name}' not found in database. Device must be created before loading register map."
            logger.error(error_msg)
            return DeviceLoadResult(
                device_name=device_name,
                device_id=0,
                success=False,
                device_created=False,
                register_map_created=False,
                error=error_msg
            )
        
        logger.debug(f"Device '{device_name}' found in database (ID: {db_device_id})")
        
        # Step 3: Convert CSV to JSON
        try:
            register_map_json = map_csv_to_json(csv_path)
        except Exception as e:
            error_msg = f"Failed to convert CSV to JSON for device '{device_name}': {e}"
            logger.error(error_msg)
            return DeviceLoadResult(
                device_name=device_name,
                device_id=db_device_id,
                success=False,
                device_created=False,
                register_map_created=False,
                error=error_msg
            )
        
        # Step 4: Create register map only if it doesn't already exist
        existing_map = await get_register_map_by_device_id(db_device_id)
        register_map_created = False
        
        if existing_map is None:
            # Create new register map
            try:
                await create_register_map(db_device_id, register_map_json)
                register_map_created = True
                logger.info(f"Created register map for device '{device_name}' (ID: {db_device_id})")
            except ValueError as e:
                # Map might have been created by another process
                logger.warning(f"Register map creation failed (may already exist): {e}")
                # Verify it now exists
                existing_map = await get_register_map_by_device_id(db_device_id)
                if existing_map is None:
                    error_msg = f"Could not create register map for device '{device_name}'"
                    logger.error(error_msg)
                    return DeviceLoadResult(
                        device_name=device_name,
                        device_id=db_device_id,
                        success=False,
                        device_created=False,
                        register_map_created=False,
                        error=error_msg
                    )
                else:
                    logger.info(f"Register map already exists for device '{device_name}' (ID: {db_device_id}), skipping")
        else:
            # Register map already exists, skip
            logger.info(f"Register map already exists for device '{device_name}' (ID: {db_device_id}), skipping")
        
        return DeviceLoadResult(
            device_name=device_name,
            device_id=db_device_id,
            success=True,
            device_created=False,  # Devices are not created in this function
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


def load_device_register_map_config(config_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    Load device to CSV file mapping from JSON config file.
    
    Reads the device_register_maps.json file from the config directory
    which maps device names to their associated CSV file paths and device_id.
    
    Expected JSON format:
    {
      "device-name": {
        "csv_file": "file.csv",
        "device_id": 1,
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
            device_mapping = json.load(f)
        
        if not isinstance(device_mapping, dict):
            logger.error(f"Invalid format in {config_file}: expected JSON object")
            return {}
        
        # Validate and normalize the config format
        normalized_mapping = {}
        for device_name, config_value in device_mapping.items():
            if isinstance(config_value, str):
                # Legacy format: just a string (CSV filename)
                normalized_mapping[device_name] = {
                    "csv_file": config_value,
                    "device_id": None,
                    "poll_address": None,
                    "poll_count": None,
                    "poll_kind": None,
                    "poll_enabled": True  # Default to enabled
                }
            elif isinstance(config_value, dict):
                # New format: object with csv_file, device_id, and optional polling config
                device_id_value = config_value.get("device_id")
                normalized_mapping[device_name] = {
                    "csv_file": config_value.get("csv_file"),
                    "device_id": device_id_value,
                    "poll_address": config_value.get("poll_address"),
                    "poll_count": config_value.get("poll_count"),
                    "poll_kind": config_value.get("poll_kind"),
                    "poll_enabled": config_value.get("poll_enabled", True)  # Default to enabled
                }
            else:
                logger.warning(f"Invalid config format for device '{device_name}', skipping")
                continue
        
        logger.info(f"Loaded device register map config with {len(normalized_mapping)} device(s)")
        return normalized_mapping
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON config file {config_file}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Failed to load device register map config from {config_file}: {e}")
        return {}


async def load_all_register_maps_from_config() -> Dict[str, DeviceLoadResult]:
    """
    Load all register map CSV files from the config folder using JSON mapping.
    
    Reads the device_register_maps.json file from the config directory which
    maps device names to their associated CSV file paths, then loads each
    CSV file into the database.
    
    Returns:
        Dictionary mapping device names to DeviceLoadResult metadata
    """
    config_dir = Path("config")
    results = {}
    
    # Load device to CSV file mapping from JSON config
    device_mapping = load_device_register_map_config(config_dir)
    
    if not device_mapping:
        logger.info("No device register map mappings found in config file")
        return results
    
    logger.info(f"Loading {len(device_mapping)} register map CSV file(s) into database...")
    
    for device_name, device_config in device_mapping.items():
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
        
        # Load the register map using the device name from the mapping
        result = await load_register_map_from_csv(
            csv_path,
            device_name
        )
        results[device_name] = result
    
    # Log summary
    successful = sum(1 for result in results.values() if result.get("success", False))
    failed = len(results) - successful
    
    if successful > 0:
        logger.info(f"Successfully loaded {successful} register map(s) into database")
    if failed > 0:
        logger.warning(f"Failed to load {failed} register map(s)")
    
    return results


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
    device_configs = load_device_register_map_config(config_dir)
    
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

