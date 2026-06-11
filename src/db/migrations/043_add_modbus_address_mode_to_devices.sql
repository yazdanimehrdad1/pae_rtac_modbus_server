-- Add modbus_address_mode to devices table
-- 'zero_based': pymodbus sends address as-is (default)
-- 'one_based':  pymodbus sends address-1 so that device docs using 1-based numbering align
ALTER TABLE devices
    ADD COLUMN IF NOT EXISTS modbus_address_mode VARCHAR(20) NOT NULL DEFAULT 'zero_based';
