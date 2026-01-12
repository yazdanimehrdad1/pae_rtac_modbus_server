"""
CSV to JSON conversion utilities.

Converts register map CSV files to JSON format.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

import pandas as pd

from schemas.modbus_models import RegisterMap, RegisterPoint
from db.device_register_map import get_register_map, create_register_map
from db.connection import get_db_pool
from logger import get_logger

logger = get_logger(__name__)




# TODO: adjust this when creating the route for importing register maps via csv
def map_csv_to_json(
    csv_path: Path
) -> Dict[str, Any]:
    """
    Convert register map CSV file to JSON format.
    
    Reads the CSV file and converts it to a JSON structure with:
    - metadata: file information
    - registers: array of register objects
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        Dictionary representation of the CSV data
        
    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV file is invalid or empty
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    logger.info(f"Reading CSV file: {csv_path}")
    
    # Read CSV file
    try:
        df = pd.read_csv(csv_path, quotechar='"', escapechar='\\')
    except Exception as e:
        raise ValueError(f"Failed to read CSV file: {e}")
    
    if df.empty:
        raise ValueError("CSV file is empty")
    
    logger.info(f"Loaded {len(df)} rows from CSV")
    
    # Convert DataFrame to list of dictionaries
    registers = []
    for _, row in df.iterrows():
        register = {}
        
        # Required fields
        if "address" in df.columns and pd.notna(row.get("address")):
            register["address"] = int(row["address"])
        
        if "name" in df.columns and pd.notna(row.get("name")):
            register["name"] = str(row["name"]).strip()
        
        if "kind" in df.columns and pd.notna(row.get("kind")):
            register["kind"] = str(row["kind"]).strip().lower()
        
        if "size" in df.columns and pd.notna(row.get("size")):
            register["size"] = int(row["size"])
        
        # Optional fields
        if "device_id" in df.columns and pd.notna(row.get("device_id")):
            register["device_id"] = int(row["device_id"])
        
        if "data_type" in df.columns and pd.notna(row.get("data_type")):
            register["data_type"] = str(row["data_type"]).strip().lower()
        
        if "scale_factor" in df.columns and pd.notna(row.get("scale_factor")):
            register["scale_factor"] = float(row["scale_factor"])
        
        if "unit" in df.columns and pd.notna(row.get("unit")):
            unit_value = str(row["unit"]).strip()
            register["unit"] = unit_value if unit_value else None
        
        if "tags" in df.columns and pd.notna(row.get("tags")):
            tags_value = str(row["tags"]).strip()
            register["tags"] = tags_value if tags_value else None
        
        registers.append(register)
    
    # Build JSON structure
    json_data = {
        "metadata": {
            "source_file": str(csv_path),
            "total_registers": len(registers),
            "columns": list(df.columns),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        },
        "registers": registers
    }
    
    return json_data


def json_to_register_map(json_data: Dict[str, Any]) -> RegisterMap:
    """
    Convert JSON structure (from map_csv_to_json) to RegisterMap object.
    
    Args:
        json_data: Dictionary with 'metadata' and 'registers' keys from map_csv_to_json
        
    Returns:
        RegisterMap object with RegisterPoint objects
    """
    registers = json_data.get("registers", [])
    points = []
    
    for reg in registers:
        point_data = {
            "name": reg["name"],
            "address": reg["address"],
            "kind": reg["kind"],
            "size": reg["size"],
        }
        
        # Optional fields
        if "device_id" in reg and reg["device_id"] is not None:
            point_data["device_id"] = reg["device_id"]
        
        if "data_type" in reg and reg["data_type"] is not None:
            point_data["data_type"] = reg["data_type"]
        
        if "scale_factor" in reg and reg["scale_factor"] is not None:
            point_data["scale_factor"] = reg["scale_factor"]
        
        if "unit" in reg and reg["unit"] is not None:
            point_data["unit"] = reg["unit"]
        
        if "tags" in reg and reg["tags"] is not None:
            point_data["tags"] = reg["tags"]
        
        points.append(RegisterPoint(**point_data))
    
    return RegisterMap(points=points)

#TODO: adjust this function to get register map for a device if it exist in cache and if not from db , and if none exists then return none
# async def get_register_map_for_device(device_id: int, site_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
#     """
# lets make this function to obtain register map for a device if it exist in cache and if not from db , and if none exists then return none
#     """
#     try:
#         # If site_id is not provided, get it from the device
#         if site_id is None:
#             from db.devices import get_device_by_id
#             device = await get_device_by_id(device_id)
#             if device and device.site_id:
#                 site_id = device.site_id
#             else:
#                 # Device has no site_id, can't query register map (site_id is required)
#                 logger.warning(f"Device ID {device_id} has no site_id. Cannot retrieve register map without site_id.")
#                 return None
        
#         # Use the validated function with site_id
#         register_map = await get_register_map(device_id, site_id=site_id)
#         if register_map is not None:
#             logger.info(f"Register map found in DB for device ID: {device_id}")
#             return register_map
#         else:
#             logger.warning(f"Register map not found in DB for device ID: {device_id}")
#             return None
#     except Exception as e:
#         logger.warning(f"Error querying DB for register map for device ID '{device_id}': {e}")
#         return None

