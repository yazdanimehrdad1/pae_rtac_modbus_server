"""DataFrame conversion utilities."""

from pathlib import Path
from typing import Optional

import pandas as pd

from rtac_modbus_service.schemas.modbus_models import RegisterPoint, RegisterMap


def load_register_map_from_csv(csv_path: Path) -> RegisterMap:
    """
    Load register map from CSV file.
    
    CSV expected columns:
    - name: Register name/label
    - address: Modbus address (0-65535)
    - kind: Register type (holding, input, coils, discretes)
    - size: Number of registers/bits to read
    - unit_id: Optional Modbus unit ID
    - data_type: Optional data type (int16, uint16, int32, uint32, float32, bool)
    - scale_factor: Optional scale factor (default 1.0)
    - unit: Optional physical unit
    - tags: Optional comma-separated tags
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        RegisterMap object with validated points
    """
    df = pd.read_csv(csv_path, quotechar='"', escapechar='\\')
    
    # Convert DataFrame rows to RegisterPoint objects
    points = []
    for _, row in df.iterrows():
        # Handle optional fields
        point_data = {
            "name": str(row["name"]),
            "address": int(row["address"]),
            "kind": str(row["kind"]).lower(),
            "size": int(row["size"]),
        }
        
        # Optional fields
        if "unit_id" in df.columns and pd.notna(row.get("unit_id")):
            point_data["unit_id"] = int(row["unit_id"])
        
        if "data_type" in df.columns and pd.notna(row.get("data_type")):
            point_data["data_type"] = str(row["data_type"]).lower()
        
        if "scale_factor" in df.columns and pd.notna(row.get("scale_factor")):
            point_data["scale_factor"] = float(row["scale_factor"])
        
        if "unit" in df.columns and pd.notna(row.get("unit")):
            point_data["unit"] = str(row["unit"])
        
        if "tags" in df.columns and pd.notna(row.get("tags")):
            tags_str = str(row["tags"])
            point_data["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]
        
        points.append(RegisterPoint(**point_data))
    
    return RegisterMap(points=points)


def register_map_to_dataframe(register_map: RegisterMap) -> pd.DataFrame:
    """
    Convert RegisterMap to pandas DataFrame.
    
    Args:
        register_map: RegisterMap object
        
    Returns:
        DataFrame with register points
    """
    data = []
    for point in register_map.points:
        data.append({
            "name": point.name,
            "address": point.address,
            "kind": point.kind,
            "size": point.size,
            "unit_id": point.unit_id,
            "data_type": point.data_type,
            "scale_factor": point.scale_factor,
            "unit": point.unit,
            "tags": ",".join(point.tags) if point.tags else "",
        })
    
    return pd.DataFrame(data)


def create_register_map_template_csv(output_path: Path) -> None:
    """
    Create a template CSV file with example register points.
    
    Args:
        output_path: Path where to save the template CSV
    """
    template_data = {
        "name": ["Voltage_L1", "Current_L1", "Power_Active", "Status_Bit"],
        "address": [0, 1, 10, 100],
        "kind": ["holding", "holding", "holding", "coils"],
        "size": [1, 1, 2, 1],
        "unit_id": [1, 1, 1, 1],
        "data_type": ["uint16", "uint16", "uint32", "bool"],
        "scale_factor": [0.1, 0.01, 1.0, 1.0],
        "unit": ["V", "A", "W", ""],
        "tags": ["voltage,electrical", "current,electrical", "power,electrical", "status"],
    }
    
    df = pd.DataFrame(template_data)
    df.to_csv(output_path, index=False)
    print(f"Template CSV created at: {output_path}")

