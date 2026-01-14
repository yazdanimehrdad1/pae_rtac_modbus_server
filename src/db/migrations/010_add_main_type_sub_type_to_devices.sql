-- Migration: Add main_type and sub_type to devices table
-- Description: Adds main_type (required) and sub_type (optional) fields to devices table
-- Created: 2024-12-XX

DO $$
BEGIN
    -- Add main_type column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'main_type'
    ) THEN
        ALTER TABLE devices 
        ADD COLUMN main_type VARCHAR(255) NOT NULL DEFAULT 'unknown';
        
        -- Remove default after adding (since it's required going forward)
        ALTER TABLE devices 
        ALTER COLUMN main_type DROP DEFAULT;
        
        CREATE INDEX IF NOT EXISTS idx_devices_main_type ON devices(main_type);
        
        COMMENT ON COLUMN devices.main_type IS 'Device main type (required)';
        
        RAISE NOTICE 'Added main_type column to devices table.';
    ELSE
        RAISE NOTICE 'Column main_type already exists on devices table, skipping.';
    END IF;

    -- Add sub_type column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'sub_type'
    ) THEN
        ALTER TABLE devices 
        ADD COLUMN sub_type VARCHAR(255);
        
        CREATE INDEX IF NOT EXISTS idx_devices_sub_type ON devices(sub_type);
        
        COMMENT ON COLUMN devices.sub_type IS 'Device sub type (optional)';
        
        RAISE NOTICE 'Added sub_type column to devices table.';
    ELSE
        RAISE NOTICE 'Column sub_type already exists on devices table, skipping.';
    END IF;
END $$;

