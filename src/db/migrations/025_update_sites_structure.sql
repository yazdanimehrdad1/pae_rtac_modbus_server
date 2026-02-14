-- Migration: Update sites structure for client_id and location JSON
-- Description: Rename owner to client_id and convert location to JSON
-- Created: 2026-01-31

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'sites'
    ) THEN
        -- Rename owner to client_id if needed
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'sites' AND column_name = 'owner'
        ) AND NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'sites' AND column_name = 'client_id'
        ) THEN
            ALTER TABLE sites RENAME COLUMN owner TO client_id;
        END IF;

        -- Ensure client_id is not null
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'sites' AND column_name = 'client_id'
        ) THEN
            ALTER TABLE sites ALTER COLUMN client_id SET NOT NULL;
        END IF;

        -- Convert location from text/varchar to jsonb with address fields
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'sites'
              AND column_name = 'location'
              AND data_type IN ('character varying', 'text')
        ) THEN
            ALTER TABLE sites
            ALTER COLUMN location TYPE JSONB
            USING (
                CASE
                    WHEN location IS NULL THEN NULL
                    ELSE jsonb_build_object(
                        'street', location,
                        'city', '',
                        'state', '',
                        'zip_code', NULL
                    )
                END
            );
        END IF;
    END IF;
END $$;

COMMENT ON COLUMN sites.client_id IS 'Client identifier';
COMMENT ON COLUMN sites.location IS 'Site location as JSON: {street: str, city: str, state: str, zip_code: int}';
