-- Migration: Drop unique constraint on modbus_device_id
-- Description: Allows duplicate Modbus unit/slave IDs across devices
-- Created: 2026-01-18

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'devices_device_id_key'
    ) THEN
        ALTER TABLE devices DROP CONSTRAINT devices_device_id_key;
    END IF;
END $$;
