-- Migration: 047_drop_register_offset_from_device_points
-- Remove register_offset from device_points. It was added in migration 035 as the
-- linear offset in `final = raw * scale_factor + register_offset`, but was never used:
-- every row held the 0.0 default, so decoding is unchanged by its removal.
-- Scaling continues via scale_factor alone: final = raw * scale_factor.

ALTER TABLE device_points DROP COLUMN IF EXISTS register_offset;
