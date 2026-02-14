-- Migration: 032_add_protocol_to_devices_and_byte_order_to_points
-- Add protocol to devices and byte_order to device_points

-- Add protocol to devices
ALTER TABLE devices ADD COLUMN protocol VARCHAR(20) NOT NULL DEFAULT 'Modbus';

-- Add byte_order to device_points
ALTER TABLE device_points ADD COLUMN byte_order VARCHAR(20) NOT NULL DEFAULT 'big-endian';
