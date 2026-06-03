-- Migration: 035_add_word_order_and_offset_to_device_points
-- Add word_order (register ordering for multi-register types) and
-- offset (linear scaling: final = raw * scale_factor + offset) to device_points

ALTER TABLE device_points ADD COLUMN word_order VARCHAR(20) NOT NULL DEFAULT 'msw_first';
ALTER TABLE device_points ADD COLUMN register_offset FLOAT NOT NULL DEFAULT 0.0;
