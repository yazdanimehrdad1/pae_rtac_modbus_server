-- Migration: Create sites table
-- Description: Stores site/location information where devices are deployed
-- Created: 2024-12-XX

-- Create sites table
CREATE TABLE IF NOT EXISTS sites (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    owner VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255) NOT NULL,
    operator VARCHAR(255) NOT NULL,
    capacity VARCHAR(255) NOT NULL,
    device_count INTEGER NOT NULL DEFAULT 0,
    description TEXT,
    coordinates JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_update TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_sites_owner ON sites(owner);
CREATE INDEX IF NOT EXISTS idx_sites_name ON sites(name);
CREATE INDEX IF NOT EXISTS idx_sites_created_at ON sites(created_at);

-- Add site_id column to devices table if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'devices' AND column_name = 'site_id'
    ) THEN
        ALTER TABLE devices 
        ADD COLUMN site_id VARCHAR(36) REFERENCES sites(id) ON DELETE SET NULL;
        
        CREATE INDEX IF NOT EXISTS idx_devices_site_id ON devices(site_id);
        
        COMMENT ON COLUMN devices.site_id IS 'Foreign key to sites table';
    END IF;
END $$;

-- Add comments to sites table
COMMENT ON TABLE sites IS 'Stores site/location information where devices are deployed';
COMMENT ON COLUMN sites.id IS 'Primary key, UUID string';
COMMENT ON COLUMN sites.owner IS 'Site owner';
COMMENT ON COLUMN sites.name IS 'Site name';
COMMENT ON COLUMN sites.location IS 'Site location';
COMMENT ON COLUMN sites.operator IS 'Site operator';
COMMENT ON COLUMN sites.capacity IS 'Site capacity';
COMMENT ON COLUMN sites.device_count IS 'Number of devices at this site (denormalized for performance)';
COMMENT ON COLUMN sites.description IS 'Optional site description';
COMMENT ON COLUMN sites.coordinates IS 'Geographic coordinates as JSON: {lat: float, lng: float}';
COMMENT ON COLUMN sites.created_at IS 'Timestamp when site record was created';
COMMENT ON COLUMN sites.updated_at IS 'Timestamp when site record was last updated';
COMMENT ON COLUMN sites.last_update IS 'Timestamp of last update (synced from external source)';

