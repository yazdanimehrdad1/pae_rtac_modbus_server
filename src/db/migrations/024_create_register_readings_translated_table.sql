CREATE TABLE IF NOT EXISTS register_readings_translated (
    timestamp TIMESTAMPTZ NOT NULL,
    device_id INTEGER NOT NULL,
    register_address INTEGER NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    quality VARCHAR(50) NOT NULL DEFAULT 'good',
    register_name TEXT NULL,
    unit TEXT NULL,
    scale_factor DOUBLE PRECISION NULL,
    value_scaled DOUBLE PRECISION NOT NULL,
    enum_detail JSON NULL,
    bitfield_detail JSON NULL,
    PRIMARY KEY (timestamp, device_id, register_address),
    CONSTRAINT fk_register_readings_translated_device_id
        FOREIGN KEY (device_id)
        REFERENCES devices (id)
        ON DELETE CASCADE
);
