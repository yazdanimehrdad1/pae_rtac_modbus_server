-- Migration: Restructure sites.id to 4-digit integer
-- Description: Replaces UUID id with 4-digit integer id
-- Created: 2026-01-15

DO $$
DECLARE
    has_sites_table boolean;
    has_uuid_id boolean;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'sites'
    ) INTO has_sites_table;

    IF NOT has_sites_table THEN
        CREATE TABLE sites (
            id INTEGER PRIMARY KEY,
            owner VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL UNIQUE,
            location VARCHAR(255) NOT NULL,
            operator VARCHAR(255) NOT NULL,
            capacity VARCHAR(255) NOT NULL,
            device_count INTEGER NOT NULL DEFAULT 0,
            description TEXT,
            coordinates JSON,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_update TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        COMMENT ON COLUMN sites.id IS 'Primary key, 4-digit site ID';
        RETURN;
    END IF;

    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'sites' AND column_name = 'id' AND data_type = 'uuid'
    ) INTO has_uuid_id;

    IF has_uuid_id THEN
        ALTER TABLE sites ADD COLUMN id_int INTEGER;

        WITH ordered AS (
            SELECT id, ROW_NUMBER() OVER (ORDER BY created_at, name) AS rn
            FROM sites
        )
        UPDATE sites
        SET id_int = 999 + ordered.rn
        FROM ordered
        WHERE sites.id = ordered.id;

        ALTER TABLE sites DROP CONSTRAINT sites_pkey;
        ALTER TABLE sites DROP COLUMN id;
        ALTER TABLE sites RENAME COLUMN id_int TO id;
        ALTER TABLE sites ADD CONSTRAINT sites_pkey PRIMARY KEY (id);

        COMMENT ON COLUMN sites.id IS 'Primary key, 4-digit site ID';
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'sites' AND column_name = 'id' AND data_type = 'integer'
    ) THEN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'chk_sites_id_4_digits'
              AND conrelid = 'sites'::regclass
        ) THEN
            ALTER TABLE sites
                ADD CONSTRAINT chk_sites_id_4_digits
                CHECK (id BETWEEN 1000 AND 9999);
        END IF;
    END IF;
END $$;


