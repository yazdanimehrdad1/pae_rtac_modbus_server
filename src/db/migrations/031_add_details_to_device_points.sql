-- Migration: Add enum_detail and bitfield_detail to device_points
-- Description: Adds JSON columns to store point-specific detail mappings
-- Created: 2026-02-02

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'device_points' AND column_name = 'enum_detail') THEN
        ALTER TABLE device_points ADD COLUMN enum_detail JSON;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'device_points' AND column_name = 'bitfield_detail') THEN
        ALTER TABLE device_points ADD COLUMN bitfield_detail JSON;
    END IF;
END $$;
