-- Migration: Rename aggregator modbus columns to standard names
-- Description: Align devices table columns with ORM fields
-- Created: 2026-01-23

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'modbus_aggregator_host'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'modbus_host'
    ) THEN
        ALTER TABLE devices RENAME COLUMN modbus_aggregator_host TO modbus_host;
        COMMENT ON COLUMN devices.modbus_host IS 'Modbus device hostname or IP address';
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'modbus__aggregator_port'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'modbus_port'
    ) THEN
        ALTER TABLE devices RENAME COLUMN modbus__aggregator_port TO modbus_port;
        COMMENT ON COLUMN devices.modbus_port IS 'Modbus TCP port (default: 502)';
    END IF;
END $$;
