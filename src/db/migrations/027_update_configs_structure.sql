-- Migration: Update device configs to configs schema
-- Description: Rename device_configs table/columns and add config fields
-- Created: 2026-01-31

DO $$
BEGIN
    -- Rename table if needed
    IF EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'device_configs'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'configs'
    ) THEN
        ALTER TABLE device_configs RENAME TO configs;
    END IF;

    -- Rename columns if needed
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'configs' AND column_name = 'id'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'configs' AND column_name = 'config_id'
    ) THEN
        ALTER TABLE configs RENAME COLUMN id TO config_id;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'configs' AND column_name = 'poll_address'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'configs' AND column_name = 'poll_start_index'
    ) THEN
        ALTER TABLE configs RENAME COLUMN poll_address TO poll_start_index;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'configs' AND column_name = 'registers'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'configs' AND column_name = 'points'
    ) THEN
        ALTER TABLE configs RENAME COLUMN registers TO points;
    END IF;

    -- Add new columns if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'configs' AND column_name = 'is_active'
    ) THEN
        ALTER TABLE configs ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT true;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'configs' AND column_name = 'created_by'
    ) THEN
        ALTER TABLE configs ADD COLUMN created_by VARCHAR(255) NOT NULL DEFAULT 'system';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'configs' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE configs ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
    END IF;

    -- Remove default for created_by if added
    BEGIN
        ALTER TABLE configs ALTER COLUMN created_by DROP DEFAULT;
    EXCEPTION
        WHEN others THEN
            NULL;
    END;

    -- Add foreign keys if missing
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_configs_site_id'
          AND conrelid = 'configs'::regclass
    ) THEN
        ALTER TABLE configs
        ADD CONSTRAINT fk_configs_site_id
        FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_configs_device_id'
          AND conrelid = 'configs'::regclass
    ) THEN
        ALTER TABLE configs
        ADD CONSTRAINT fk_configs_device_id
        FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE;
    END IF;

    -- Ensure index on config_id
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'configs' AND indexname = 'idx_configs_config_id'
    ) THEN
        CREATE INDEX idx_configs_config_id ON configs(config_id);
    END IF;
END $$;

COMMENT ON TABLE configs IS 'Stores versioned polling configuration payloads keyed by config ID';
COMMENT ON COLUMN configs.config_id IS 'Config ID (e.g., siteID-deviceID-1)';
COMMENT ON COLUMN configs.site_id IS 'Site ID (4-digit number)';
COMMENT ON COLUMN configs.device_id IS 'Device ID (database primary key)';
COMMENT ON COLUMN configs.poll_kind IS 'Register type: holding, input, or coils';
COMMENT ON COLUMN configs.poll_start_index IS 'Start index for polling Modbus registers';
COMMENT ON COLUMN configs.poll_count IS 'Number of registers to read during polling';
COMMENT ON COLUMN configs.points IS 'Point definitions';
COMMENT ON COLUMN configs.is_active IS 'Whether this config is active';
COMMENT ON COLUMN configs.created_by IS 'Config creator identifier';
COMMENT ON COLUMN configs.created_at IS 'Timestamp when config record was created';
COMMENT ON COLUMN configs.updated_at IS 'Timestamp when config record was last updated';
