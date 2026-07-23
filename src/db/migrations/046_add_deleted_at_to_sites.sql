-- Add soft-delete support to sites table.
-- Soft-deleting a site cascades (at the application layer) to all its devices and their points.
ALTER TABLE sites ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ NULL;
