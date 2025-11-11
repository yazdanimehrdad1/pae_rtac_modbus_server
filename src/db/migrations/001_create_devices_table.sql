-- Migration: Create devices table
-- Description: Stores Modbus device configuration information
-- Created: 2024-11-10

CREATE TABLE IF NOT EXISTS devices (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL DEFAULT 502,
    unit_id INTEGER NOT NULL DEFAULT 1,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create index on name for faster lookups
CREATE INDEX IF NOT EXISTS idx_devices_name ON devices(name);

-- Create index on host/port for device lookups
CREATE INDEX IF NOT EXISTS idx_devices_host_port ON devices(host, port);

-- Add comment to table
COMMENT ON TABLE devices IS 'Stores Modbus device configuration and connection information';

-- Add comments to columns
COMMENT ON COLUMN devices.id IS 'Primary key, auto-incrementing';
COMMENT ON COLUMN devices.name IS 'Unique device name/identifier';
COMMENT ON COLUMN devices.host IS 'Modbus device hostname or IP address';
COMMENT ON COLUMN devices.port IS 'Modbus TCP port (default: 502)';
COMMENT ON COLUMN devices.unit_id IS 'Modbus unit/slave ID';
COMMENT ON COLUMN devices.description IS 'Optional device description';
COMMENT ON COLUMN devices.created_at IS 'Timestamp when device record was created';
COMMENT ON COLUMN devices.updated_at IS 'Timestamp when device record was last updated';

