-- Migration: Add read_from_aggregator to devices
-- Description: Adds read_from_aggregator flag to devices table (default true)
-- Created: 2026-01-18

ALTER TABLE devices
    ADD COLUMN IF NOT EXISTS read_from_aggregator BOOLEAN NOT NULL DEFAULT TRUE;

COMMENT ON COLUMN devices.read_from_aggregator IS 'Whether to read from edge aggregator';
