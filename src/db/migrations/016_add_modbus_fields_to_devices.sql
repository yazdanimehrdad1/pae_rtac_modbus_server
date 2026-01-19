-- Migration: Rename device connection fields and add modbus_timeout
-- Description: Rename host/port/device_id to modbus_* and add optional timeout
-- Created: 2026-01-18

ALTER TABLE devices
    RENAME COLUMN host TO modbus_host;

ALTER TABLE devices
    RENAME COLUMN port TO modbus_port;

ALTER TABLE devices
    RENAME COLUMN device_id TO modbus_device_id;

ALTER TABLE devices
    ALTER COLUMN modbus_device_id SET DEFAULT 1;

ALTER TABLE devices
    ADD COLUMN IF NOT EXISTS modbus_timeout DOUBLE PRECISION;

COMMENT ON COLUMN devices.modbus_host IS 'Modbus device hostname or IP address';
COMMENT ON COLUMN devices.modbus_port IS 'Modbus TCP port (default: 502)';
COMMENT ON COLUMN devices.modbus_device_id IS 'Modbus unit/slave ID';
COMMENT ON COLUMN devices.modbus_timeout IS 'Optional Modbus timeout (seconds)';
