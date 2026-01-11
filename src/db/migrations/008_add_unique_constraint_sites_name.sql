-- Migration: Add unique constraint to sites.name
-- Description: Ensures site names are unique
-- Created: 2024-12-XX

-- Add unique constraint to sites.name
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'sites_name_key' 
        AND conrelid = 'sites'::regclass
    ) THEN
        ALTER TABLE sites ADD CONSTRAINT sites_name_key UNIQUE (name);
        COMMENT ON CONSTRAINT sites_name_key ON sites IS 'Ensures site names are unique';
    END IF;
END $$;

