-- Migration: Create device_register_map table
-- Description: Stores device register map configuration as JSONB in a separate table
-- Created: 2025-01-13

CREATE TABLE IF NOT EXISTS device_register_map (
    id SERIAL PRIMARY KEY,
    device_id INTEGER NOT NULL UNIQUE,
    register_map JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Foreign key constraint to devices table
    CONSTRAINT fk_device_register_map_device
        FOREIGN KEY (device_id)
        REFERENCES devices(id)
        ON DELETE CASCADE
);

-- Create index on device_id for faster lookups (though UNIQUE already creates an index)
CREATE INDEX IF NOT EXISTS idx_device_register_map_device_id ON device_register_map(device_id);

-- Create GIN index on register_map for efficient JSON queries
-- This allows queries like: WHERE register_map @> '{"registers": [...]}'
CREATE INDEX IF NOT EXISTS idx_device_register_map_register_map ON device_register_map USING GIN (register_map);

-- Add comment to table
COMMENT ON TABLE device_register_map IS 'Stores device register map configuration as JSONB. One register map per device.';

-- Add comments to columns
COMMENT ON COLUMN device_register_map.id IS 'Primary key, auto-incrementing';
COMMENT ON COLUMN device_register_map.device_id IS 'Foreign key to devices table (one-to-one relationship)';
COMMENT ON COLUMN device_register_map.register_map IS 'Device register map configuration stored as JSONB. Structure matches map_csv_to_json output with metadata and registers array.';
COMMENT ON COLUMN device_register_map.created_at IS 'Timestamp when register map was created';
COMMENT ON COLUMN device_register_map.updated_at IS 'Timestamp when register map was last updated';

