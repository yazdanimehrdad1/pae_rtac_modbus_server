-- Migration: Add is_derived to device_points
-- Description: Adds a boolean field to distinguish between raw and derived points
-- Created: 2026-02-02

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'device_points' AND column_name = 'is_derived') THEN
        ALTER TABLE device_points ADD COLUMN is_derived BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END $$;
