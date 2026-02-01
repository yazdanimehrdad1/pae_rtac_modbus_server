-- Migration: Create device_points table
-- Description: Creates table to store flattened device points
-- Created: 2026-02-01

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'device_points') THEN
        CREATE TABLE device_points (
            id SERIAL PRIMARY KEY,
            site_id INTEGER NOT NULL,
            device_id INTEGER NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
            config_id VARCHAR(255) NOT NULL REFERENCES configs(config_id) ON DELETE CASCADE,
            address INTEGER NOT NULL,
            name VARCHAR(255) NOT NULL,
            size INTEGER NOT NULL,
            data_type VARCHAR(50) NOT NULL,
            scale_factor FLOAT,
            unit VARCHAR(50),
            enum_value VARCHAR(255),
            bitfield_value VARCHAR(255),
            CONSTRAINT fk_device_points_site_id FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE
        );

        CREATE INDEX idx_device_points_device_id ON device_points(device_id);
    END IF;
END $$;
