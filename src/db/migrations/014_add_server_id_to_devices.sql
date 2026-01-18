-- Migration: Add server_id to devices table
-- Description: Adds server_id field to devices table
-- Created: 2026-01-15

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'devices' AND column_name = 'server_id'
    ) THEN
        ALTER TABLE devices
        ADD COLUMN server_id VARCHAR(255) NOT NULL DEFAULT 'default';
        
        ALTER TABLE devices
        ALTER COLUMN server_id DROP DEFAULT;
        
        COMMENT ON COLUMN devices.server_id IS 'Server identifier';
        
        RAISE NOTICE 'Added server_id column to devices table.';
    ELSE
        RAISE NOTICE 'Column server_id already exists on devices table, skipping.';
    END IF;
END $$;


