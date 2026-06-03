-- Migration: 039_remove_enum_value_bitfield_value_is_derived
-- enum_value and bitfield_value were never written to or used in any logic.
-- is_derived was always hardcoded to false and never drove any branching.
-- The uq_device_point_address_bitfield constraint depended on bitfield_value.

DO $$
BEGIN
    -- Drop the constraint that depended on bitfield_value
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_device_point_address_bitfield'
          AND conrelid = 'device_points'::regclass
    ) THEN
        ALTER TABLE device_points DROP CONSTRAINT uq_device_point_address_bitfield;
        RAISE NOTICE 'Dropped constraint uq_device_point_address_bitfield';
    END IF;

    -- Also drop it if it was created as an index rather than a named constraint
    DROP INDEX IF EXISTS uq_device_point_address_bitfield;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'device_points' AND column_name = 'enum_value'
    ) THEN
        ALTER TABLE device_points DROP COLUMN enum_value;
        RAISE NOTICE 'Dropped column enum_value';
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'device_points' AND column_name = 'bitfield_value'
    ) THEN
        ALTER TABLE device_points DROP COLUMN bitfield_value;
        RAISE NOTICE 'Dropped column bitfield_value';
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'device_points' AND column_name = 'is_derived'
    ) THEN
        ALTER TABLE device_points DROP COLUMN is_derived;
        RAISE NOTICE 'Dropped column is_derived';
    END IF;
END $$;
