-- Add soft-delete support to devices table.
-- When deleted_at is set, the device is logically deleted but its device_id and
-- all associated readings remain intact so references do not break.
ALTER TABLE devices ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ NULL;
