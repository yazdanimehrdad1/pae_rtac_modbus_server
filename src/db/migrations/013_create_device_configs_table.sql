-- Migration: Create device_configs table
-- Description: Stores device configuration payloads keyed by config ID
-- Created: 2026-01-15

CREATE TABLE IF NOT EXISTS device_configs (
    id VARCHAR(255) PRIMARY KEY,
    site_id INTEGER NOT NULL,
    device_id INTEGER NOT NULL,
    poll_address INTEGER NOT NULL,
    poll_count INTEGER NOT NULL,
    poll_kind VARCHAR(20) NOT NULL,
    registers JSON NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_device_configs_id ON device_configs(id);

COMMENT ON TABLE device_configs IS 'Stores device configuration payloads keyed by config ID';
COMMENT ON COLUMN device_configs.id IS 'Device config ID (e.g., siteID-deviceID-1)';
COMMENT ON COLUMN device_configs.site_id IS 'Site ID (4-digit number)';
COMMENT ON COLUMN device_configs.device_id IS 'Device ID (database primary key)';
COMMENT ON COLUMN device_configs.poll_address IS 'Start address for polling Modbus registers';
COMMENT ON COLUMN device_configs.poll_count IS 'Number of registers to read during polling';
COMMENT ON COLUMN device_configs.poll_kind IS 'Register type: holding, input, coils, or discretes';
COMMENT ON COLUMN device_configs.registers IS 'Register definitions';
COMMENT ON COLUMN device_configs.created_at IS 'Timestamp when config record was created';
COMMENT ON COLUMN device_configs.updated_at IS 'Timestamp when config record was last updated';


