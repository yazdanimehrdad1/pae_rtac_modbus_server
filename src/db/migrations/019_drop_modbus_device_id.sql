-- Migration: Drop modbus_device_id from devices
-- Description: Removes per-device Modbus unit/slave ID
-- Created: 2026-01-18

ALTER TABLE devices
    DROP COLUMN IF EXISTS modbus_device_id;
