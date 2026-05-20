-- Migration: 036_add_category_to_device_points
-- Add category column to device_points to distinguish NATIVE, STANDARDIZED, and VIRTUAL points

CREATE TYPE device_point_category AS ENUM ('NATIVE', 'STANDARDIZED', 'VIRTUAL');

ALTER TABLE device_points
    ADD COLUMN category device_point_category NOT NULL DEFAULT 'NATIVE';
