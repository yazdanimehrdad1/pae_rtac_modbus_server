ALTER TABLE device_points ADD COLUMN IF NOT EXISTS poll_kind VARCHAR(20);

UPDATE device_points dp
SET poll_kind = c.poll_kind
FROM configs c
WHERE dp.config_id = c.config_id;
