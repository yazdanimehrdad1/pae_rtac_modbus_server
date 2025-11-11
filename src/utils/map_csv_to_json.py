"""
CSV to JSON conversion utilities.

Converts register map CSV files to JSON format.
"""

from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

import pandas as pd

from logger import get_logger

logger = get_logger(__name__)


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
        if "unit_id" in df.columns and pd.notna(row.get("unit_id")):
            register["unit_id"] = int(row["unit_id"])
        
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

