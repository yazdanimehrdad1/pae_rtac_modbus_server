-- Migration: Rename server_id to modbus_server_id
-- Description: Moves server_id to integer modbus_server_id with default 1
-- Created: 2026-01-18

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'server_id'
    ) THEN
        ALTER TABLE devices
            ADD COLUMN IF NOT EXISTS modbus_server_id INTEGER;

        UPDATE devices
        SET modbus_server_id = CASE
            WHEN server_id ~ '^\d+$' THEN server_id::INTEGER
            ELSE 1
        END;

        ALTER TABLE devices
            ALTER COLUMN modbus_server_id SET NOT NULL,
            ALTER COLUMN modbus_server_id SET DEFAULT 1;

        ALTER TABLE devices
            DROP COLUMN server_id;

        COMMENT ON COLUMN devices.modbus_server_id IS 'Modbus server identifier';
    END IF;
END $$;
