-- Migration: Update devices table structure
-- Description: Rename connection fields, add type/vendor/model, drop configs/main/sub type
-- Created: 2026-01-31

DO $$
BEGIN
    -- Rename primary key column to device_id
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'id'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'device_id'
    ) THEN
        ALTER TABLE devices RENAME COLUMN id TO device_id;
    END IF;

    -- Rename modbus fields to standard names
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'modbus_host'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'host'
    ) THEN
        ALTER TABLE devices RENAME COLUMN modbus_host TO host;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'modbus_port'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'port'
    ) THEN
        ALTER TABLE devices RENAME COLUMN modbus_port TO port;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'modbus_timeout'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'timeout'
    ) THEN
        ALTER TABLE devices RENAME COLUMN modbus_timeout TO timeout;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'modbus_server_id'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'server_address'
    ) THEN
        ALTER TABLE devices RENAME COLUMN modbus_server_id TO server_address;
    END IF;

    -- Add new fields
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'type'
    ) THEN
        ALTER TABLE devices ADD COLUMN type VARCHAR(50);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'vendor'
    ) THEN
        ALTER TABLE devices ADD COLUMN vendor VARCHAR(255);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'model'
    ) THEN
        ALTER TABLE devices ADD COLUMN model VARCHAR(255);
    END IF;

    -- Backfill type from main_type if available
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'main_type'
    ) THEN
        UPDATE devices
        SET type = main_type
        WHERE type IS NULL AND main_type IS NOT NULL;
    END IF;

    -- Enforce not null on type when possible
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'type'
    ) AND NOT EXISTS (
        SELECT 1 FROM devices WHERE type IS NULL
    ) THEN
        ALTER TABLE devices ALTER COLUMN type SET NOT NULL;
    END IF;

    -- Enforce not null on server_address when possible
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'server_address'
    ) AND NOT EXISTS (
        SELECT 1 FROM devices WHERE server_address IS NULL
    ) THEN
        ALTER TABLE devices ALTER COLUMN server_address SET NOT NULL;
    END IF;

    -- Drop legacy columns if present
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'main_type'
    ) THEN
        ALTER TABLE devices DROP COLUMN main_type;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'sub_type'
    ) THEN
        ALTER TABLE devices DROP COLUMN sub_type;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'configs'
    ) THEN
        ALTER TABLE devices DROP COLUMN configs;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'modbus_device_id'
    ) THEN
        ALTER TABLE devices DROP COLUMN modbus_device_id;
    END IF;

    -- Add host/port index if missing
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'devices' AND indexname = 'idx_devices_host_port'
    ) THEN
        CREATE INDEX idx_devices_host_port ON devices(host, port);
    END IF;
END $$;

COMMENT ON COLUMN devices.device_id IS 'Primary key, auto-incrementing';
COMMENT ON COLUMN devices.host IS 'Device hostname or IP address';
COMMENT ON COLUMN devices.port IS 'Device port (default: 502)';
COMMENT ON COLUMN devices.timeout IS 'Optional timeout (seconds)';
COMMENT ON COLUMN devices.server_address IS 'Server address';
COMMENT ON COLUMN devices.type IS 'Device type';
COMMENT ON COLUMN devices.vendor IS 'Device vendor';
COMMENT ON COLUMN devices.model IS 'Device model';
