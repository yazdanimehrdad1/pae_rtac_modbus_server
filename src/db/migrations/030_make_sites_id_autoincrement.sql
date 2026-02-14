-- Migration: Make sites.id autoincrement
-- Description: Adds a sequence to sites.id to support automatic ID generation
-- Created: 2026-02-02

DO $$
DECLARE
    max_id INTEGER;
BEGIN
    -- Only proceed if the table exists
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sites') THEN
        -- Check if a default value already exists (which would mean it is already autoincrement)
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'sites' AND column_name = 'id' AND column_default IS NOT NULL
        ) THEN
            -- Find the current max ID to start the sequence from there
            SELECT COALESCE(MAX(id), 1000) INTO max_id FROM sites;
            
            -- Create the sequence starting after max_id
            EXECUTE 'CREATE SEQUENCE IF NOT EXISTS sites_id_seq START ' || (max_id + 1);
            
            -- Set the default value for the id column to use the sequence
            ALTER TABLE sites ALTER COLUMN id SET DEFAULT nextval('sites_id_seq');
            
            -- Associate the sequence with the column so it gets dropped if the column is dropped
            EXECUTE 'ALTER SEQUENCE sites_id_seq OWNED BY sites.id';
            
            RAISE NOTICE 'Added autoincrement sequence to sites.id starting at %', (max_id + 1);
        END IF;
    END IF;
END $$;
