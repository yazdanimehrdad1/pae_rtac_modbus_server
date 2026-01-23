-- Migration: Change device name unique constraint from global to site-scoped
-- Description: Removes global UNIQUE constraint on devices.name and adds a composite unique constraint
--              on (name, site_id) so device names are unique within a site, but can be duplicated across sites.
--              Devices without a site_id (NULL) are allowed to have duplicate names for backward compatibility.
-- Created: 2024-12-XX

DO $$
BEGIN
    -- Drop the existing global unique constraint on name if it exists
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'devices_name_key' 
        AND conrelid = 'devices'::regclass
    ) THEN
        ALTER TABLE devices DROP CONSTRAINT devices_name_key;
        RAISE NOTICE 'Dropped global unique constraint devices_name_key on devices.name';
    END IF;
    
    -- Drop the index if it exists (the unique constraint may have created it)
    -- We'll recreate a non-unique index below
    IF EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE indexname = 'idx_devices_name'
    ) THEN
        DROP INDEX IF EXISTS idx_devices_name;
        RAISE NOTICE 'Dropped index idx_devices_name';
    END IF;
    
    -- Create a composite unique constraint on (name, site_id)
    -- This allows:
    -- - Same device name in different sites
    -- - Multiple devices with same name if site_id is NULL (for backward compatibility)
    -- - Only one device with a given name within a specific site
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'uq_devices_name_site_id' 
        AND conrelid = 'devices'::regclass
    ) THEN
        -- Use a partial unique index to handle NULL site_id values properly
        -- PostgreSQL allows multiple NULL values in a unique index
        CREATE UNIQUE INDEX IF NOT EXISTS uq_devices_name_site_id 
        ON devices(name, site_id) 
        WHERE site_id IS NOT NULL;
        
        COMMENT ON INDEX uq_devices_name_site_id IS 'Ensures device names are unique within a site (site_id must not be NULL)';
        
        RAISE NOTICE 'Created composite unique index uq_devices_name_site_id on devices(name, site_id)';
    END IF;
    
    -- Recreate the non-unique index on name for faster lookups
    CREATE INDEX IF NOT EXISTS idx_devices_name ON devices(name);
    
    -- Update the comment on the name column
    COMMENT ON COLUMN devices.name IS 'Device name/identifier (unique within a site when site_id is not NULL)';
END $$;


