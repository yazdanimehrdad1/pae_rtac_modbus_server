-- Migration: Create device_points_readings table
-- Description: New normalized table that references device_points instead of storing denormalized data
-- Created: 2026-02-03

BEGIN;

-- Drop the old point_readings table if it exists
DROP TABLE IF EXISTS point_readings CASCADE;

-- Add unique constraints to device_points table
-- 1. Prevent duplicate point names per site/device
ALTER TABLE device_points 
ADD CONSTRAINT uq_device_point_site_device_name UNIQUE (site_id, device_id, name);

-- 2. Prevent duplicate derived points (bitfield/enum expansions) at the same address
ALTER TABLE device_points 
ADD CONSTRAINT uq_device_point_address_bitfield UNIQUE (site_id, device_id, address, bitfield_value);

-- Create the new device_points_readings table
CREATE TABLE IF NOT EXISTS device_points_readings (
    -- Composite primary key
    timestamp TIMESTAMPTZ NOT NULL,
    site_id INTEGER NOT NULL,
    device_id INTEGER NOT NULL,
    device_point_id INTEGER NOT NULL,
    
    -- Values
    raw_value DOUBLE PRECISION NULL,
    derived_value DOUBLE PRECISION NULL,
    
    -- Primary key (ensures uniqueness of timestamp + device_point_id)
    PRIMARY KEY (timestamp, device_point_id),
    
    -- Foreign key to sites
    CONSTRAINT fk_device_points_readings_site
        FOREIGN KEY (site_id)
        REFERENCES sites (id)
        ON DELETE CASCADE,

    -- Foreign key to devices
    CONSTRAINT fk_device_points_readings_device
        FOREIGN KEY (device_id)
        REFERENCES devices (device_id)
        ON DELETE CASCADE,

    -- Foreign key to device_points
    CONSTRAINT fk_device_points_readings_device_point
        FOREIGN KEY (device_point_id)
        REFERENCES device_points (id)
        ON DELETE CASCADE
);

-- Enforce uniqueness on device_point_id + timestamp to prevent duplicates
ALTER TABLE device_points_readings
ADD CONSTRAINT uq_device_points_readings_point_time UNIQUE (device_point_id, timestamp);

-- Create index for efficient queries
CREATE INDEX IF NOT EXISTS idx_device_points_readings_point_time 
ON device_points_readings (device_point_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_device_points_readings_site_device_time
ON device_points_readings (site_id, device_id, timestamp DESC);

-- Add comments
COMMENT ON TABLE device_points_readings IS 'Time-series readings for device points. Stores raw and derived values.';
COMMENT ON COLUMN device_points_readings.timestamp IS 'Timestamp when the reading was taken (UTC)';
COMMENT ON COLUMN device_points_readings.site_id IS 'Site ID (denormalized from device_points)';
COMMENT ON COLUMN device_points_readings.device_id IS 'Device ID (denormalized from device_points)';
COMMENT ON COLUMN device_points_readings.device_point_id IS 'Foreign key to device_points table';
COMMENT ON COLUMN device_points_readings.raw_value IS 'The raw value read from the device';
COMMENT ON COLUMN device_points_readings.derived_value IS 'The derived/calculated value (for bitfields, enums, scaled values)';

COMMIT;
