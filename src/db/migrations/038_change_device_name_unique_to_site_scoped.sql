-- Migration: 038_change_device_name_unique_to_site_scoped
-- Device names must be unique per site, not globally.
-- Migration 011 re-added devices_name_key (global) after 009 removed it — this fixes that.

DO $$
BEGIN
    -- Drop global unique constraint if it still exists
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'devices_name_key'
          AND conrelid = 'devices'::regclass
    ) THEN
        ALTER TABLE devices DROP CONSTRAINT devices_name_key;
        RAISE NOTICE 'Dropped global unique constraint devices_name_key';
    END IF;

    -- Drop old site-scoped index if a previous attempt left one
    DROP INDEX IF EXISTS uq_devices_name_site_id;

    -- Create composite unique index scoped to (name, site_id)
    CREATE UNIQUE INDEX uq_devices_name_site_id
        ON devices (name, site_id)
        WHERE site_id IS NOT NULL;

    RAISE NOTICE 'Created site-scoped unique index uq_devices_name_site_id on devices(name, site_id)';
END $$;
