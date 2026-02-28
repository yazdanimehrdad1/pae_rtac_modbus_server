"""DataFrame conversion utilities."""


import pandas as pd

from schemas.modbus_models import RegisterMap

# TODO: this DF should also contain the values read for each register
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
            "register_name": point.name,
            "register_address": point.address,
            "kind": point.kind,
            "size": point.size,
            "device_id": point.device_id,
            "data_type": point.data_type,
            "scale_factor": point.scale_factor,
            "unit": point.unit,
            "tags": ",".join(point.tags) if point.tags else "",
        })
    
    return pd.DataFrame(data)


