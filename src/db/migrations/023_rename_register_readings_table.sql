-- Rename register_readings table to register_readings_raw
ALTER TABLE IF EXISTS register_readings
RENAME TO register_readings_raw;
