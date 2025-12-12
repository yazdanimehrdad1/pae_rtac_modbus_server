-- Migration: Add unique constraint on device_id column
-- Description: Ensures device_id (Modbus unit/slave ID) is unique across all devices
-- Created: 2025-12-07

-- Add unique constraint on device_id
ALTER TABLE devices ADD CONSTRAINT devices_device_id_key UNIQUE (device_id);

-- Create index for faster lookups (unique constraint automatically creates an index, but we can add a comment)
COMMENT ON CONSTRAINT devices_device_id_key ON devices IS 'Ensures Modbus unit/slave ID is unique across all devices';

