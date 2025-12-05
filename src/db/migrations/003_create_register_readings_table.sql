-- Migration: Create register_readings table
-- Description: Stores time-series data for Modbus register readings from all devices
-- Created: 2025-01-18
CREATE TABLE IF NOT EXISTS register_readings (
    -- Core identification
    timestamp TIMESTAMPTZ NOT NULL,
    device_id INTEGER NOT NULL,
    register_address INTEGER NOT NULL,
    
    -- Value
    value DOUBLE PRECISION NOT NULL,
    
    -- Quality/Status (important for historians)
    quality TEXT NOT NULL DEFAULT 'good',  -- 'good', 'bad', 'uncertain', 'substituted'
    
    -- Denormalized for performance (avoid joins)
    register_name TEXT,  -- From register_map, for faster queries
    unit TEXT,           -- 'V', 'A', 'kW', '°C', etc.
    
    -- Primary key (composite)
    PRIMARY KEY (timestamp, device_id, register_address),
    
    -- Foreign key constraint to devices table
    CONSTRAINT fk_register_readings_device
        FOREIGN KEY (device_id)
        REFERENCES devices(id)
        ON DELETE CASCADE
);

-- Add comments to table
COMMENT ON TABLE register_readings IS 'Time-series data for Modbus register readings. Stores historical values from all devices for historian and frontend visualization.';

-- Add comments to columns
COMMENT ON COLUMN register_readings.timestamp IS 'Timestamp when the reading was taken (UTC)';
COMMENT ON COLUMN register_readings.device_id IS 'Foreign key to devices table';
COMMENT ON COLUMN register_readings.register_address IS 'Modbus register address';
COMMENT ON COLUMN register_readings.value IS 'The actual register value';
COMMENT ON COLUMN register_readings.quality IS 'Data quality flag: good, bad, uncertain, or substituted';
COMMENT ON COLUMN register_readings.register_name IS 'Register name (denormalized from register_map for performance)';
COMMENT ON COLUMN register_readings.unit IS 'Unit of measurement (denormalized from register_map)';

-- Create primary index for query performance
-- This index optimizes the most common query patterns:
-- - Latest value queries: WHERE device_id = X AND register_address = Y ORDER BY timestamp DESC
-- - Time-series queries: WHERE device_id = X AND register_address = Y AND timestamp BETWEEN ...
CREATE INDEX IF NOT EXISTS idx_register_readings_device_register_time 
ON register_readings (device_id, register_address, timestamp DESC);

COMMENT ON INDEX idx_register_readings_device_register_time IS 
'Composite index for efficient queries filtering by device_id, register_address, and timestamp. Optimizes latest value and time-series queries.';

