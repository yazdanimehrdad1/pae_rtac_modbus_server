-- Migration: Add site_id to devices table
-- Description: Adds site_id foreign key to devices and indexes it
-- Created: 2026-01-15

DO $$
BEGIN
    -- If sites.id is varchar/text, convert to integer and remap devices.site_id
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'sites'
          AND column_name = 'id'
          AND data_type IN ('character varying', 'text')
    ) THEN
        -- Drop existing FK from devices.site_id (varchar) if present
        IF EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'devices_site_id_fkey'
              AND conrelid = 'devices'::regclass
        ) THEN
            ALTER TABLE devices DROP CONSTRAINT devices_site_id_fkey;
        END IF;
        IF EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'fk_devices_site_id'
              AND conrelid = 'devices'::regclass
        ) THEN
            ALTER TABLE devices DROP CONSTRAINT fk_devices_site_id;
        END IF;

        ALTER TABLE sites ADD COLUMN id_int INTEGER;
        
        WITH ordered AS (
            SELECT id, ROW_NUMBER() OVER (ORDER BY created_at, name) AS rn
            FROM sites
        )
        UPDATE sites
        SET id_int = 999 + ordered.rn
        FROM ordered
        WHERE sites.id = ordered.id;

        -- Map devices.site_id (varchar) to new integer ids
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'devices' AND column_name = 'site_id'
        ) THEN
            ALTER TABLE devices ADD COLUMN site_id_int INTEGER;
            UPDATE devices
            SET site_id_int = sites.id_int
            FROM sites
            WHERE devices.site_id = sites.id;
        END IF;
        
        ALTER TABLE sites DROP CONSTRAINT sites_pkey;
        ALTER TABLE sites DROP COLUMN id;
        ALTER TABLE sites RENAME COLUMN id_int TO id;
        ALTER TABLE sites ADD CONSTRAINT sites_pkey PRIMARY KEY (id);
        
        COMMENT ON COLUMN sites.id IS 'Primary key, 4-digit site ID';

        -- Swap devices.site_id to integer
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'devices' AND column_name = 'site_id_int'
        ) THEN
            ALTER TABLE devices DROP COLUMN site_id;
            ALTER TABLE devices RENAME COLUMN site_id_int TO site_id;
        END IF;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'site_id'
    ) THEN
        ALTER TABLE devices
        ADD COLUMN site_id INTEGER;
        
        CREATE INDEX IF NOT EXISTS idx_devices_site_id ON devices(site_id);
        
        COMMENT ON COLUMN devices.site_id IS 'Site ID (required)';
    END IF;

    -- Add FK only if types match
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'sites' AND column_name = 'id' AND data_type = 'integer'
    ) AND NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_devices_site_id'
          AND conrelid = 'devices'::regclass
    ) THEN
        ALTER TABLE devices
        ADD CONSTRAINT fk_devices_site_id
        FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE;
    END IF;

    -- If there are no devices, we can enforce NOT NULL
    IF NOT EXISTS (SELECT 1 FROM devices) THEN
        ALTER TABLE devices ALTER COLUMN site_id SET NOT NULL;
    END IF;
END $$;


