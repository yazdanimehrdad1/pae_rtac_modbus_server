-- Migration: 037_make_device_point_config_id_nullable
-- STANDARDIZED and VIRTUAL points are not derived from a config, so config_id must be nullable.

ALTER TABLE device_points ALTER COLUMN config_id DROP NOT NULL;
