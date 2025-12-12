-- Migration: Add polling configuration columns to devices table
-- Description: Adds polling configuration fields (address, count, kind, enabled) to devices table
-- Created: 2025-12-07

-- Add polling configuration columns
ALTER TABLE devices
ADD COLUMN IF NOT EXISTS poll_address INTEGER,
ADD COLUMN IF NOT EXISTS poll_count INTEGER,
ADD COLUMN IF NOT EXISTS poll_kind VARCHAR(20) DEFAULT 'holding',
ADD COLUMN IF NOT EXISTS poll_enabled BOOLEAN DEFAULT true;

-- Add comments to new columns
COMMENT ON COLUMN devices.poll_address IS 'Start address for polling Modbus registers';
COMMENT ON COLUMN devices.poll_count IS 'Number of registers to read during polling';
COMMENT ON COLUMN devices.poll_kind IS 'Register type: holding, input, coils, or discretes';
COMMENT ON COLUMN devices.poll_enabled IS 'Whether polling is enabled for this device';

