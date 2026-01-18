-- Migration: Restructure devices table for new device schema
-- Description: Removes legacy site/polling columns, adds configs, restores global name uniqueness
-- Created: 2026-01-15

DO $$
BEGIN
    -- Add configs column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'configs'
    ) THEN
        ALTER TABLE devices
        ADD COLUMN configs JSON NOT NULL DEFAULT '[]'::json;
        COMMENT ON COLUMN devices.configs IS 'Device-specific configuration entries';
        RAISE NOTICE 'Added configs column to devices table.';
    END IF;

    -- Drop legacy polling config columns if present
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'poll_address'
    ) THEN
        ALTER TABLE devices DROP COLUMN poll_address;
        RAISE NOTICE 'Dropped poll_address column from devices table.';
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'poll_count'
    ) THEN
        ALTER TABLE devices DROP COLUMN poll_count;
        RAISE NOTICE 'Dropped poll_count column from devices table.';
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'poll_kind'
    ) THEN
        ALTER TABLE devices DROP COLUMN poll_kind;
        RAISE NOTICE 'Dropped poll_kind column from devices table.';
    END IF;

    -- Drop site_id column and related index if present
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'site_id'
    ) THEN
        ALTER TABLE devices DROP COLUMN site_id;
        RAISE NOTICE 'Dropped site_id column from devices table.';
    END IF;

    DROP INDEX IF EXISTS idx_devices_site_id;
    DROP INDEX IF EXISTS uq_devices_name_site_id;

    -- Restore global unique constraint on name if missing
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'devices_name_key'
          AND conrelid = 'devices'::regclass
    ) THEN
        ALTER TABLE devices ADD CONSTRAINT devices_name_key UNIQUE (name);
        RAISE NOTICE 'Added global unique constraint devices_name_key on devices.name.';
    END IF;

    -- Ensure device_id has no default
    BEGIN
        ALTER TABLE devices ALTER COLUMN device_id DROP DEFAULT;
    EXCEPTION
        WHEN others THEN
            -- Ignore if default doesn't exist
            NULL;
    END;

    COMMENT ON COLUMN devices.name IS 'Device name/identifier (globally unique)';
END $$;


