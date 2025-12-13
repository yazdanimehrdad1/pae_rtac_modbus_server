-- Migration: Add scale_factor column to register_readings table
-- Description: Adds scale_factor column to store scale factor for register values (denormalized from register_map)
-- Created: 2025-12-13

-- Add scale_factor column
ALTER TABLE register_readings
ADD COLUMN IF NOT EXISTS scale_factor DOUBLE PRECISION;

-- Add comment to column
COMMENT ON COLUMN register_readings.scale_factor IS 'Scale factor to apply to raw value (denormalized from register_map for performance)';

