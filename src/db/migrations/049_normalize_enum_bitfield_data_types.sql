-- Migration: 049_normalize_enum_bitfield_data_types
-- Give the semantic data types explicit width suffixes so register count is derivable
-- from the type name, matching how numeric types already work (int32 -> 2 registers).
--
--   enum        -> enum16 / enum32
--   bitfield    -> bitfield16 / bitfield32
--   status_word -> status_word16 / status_word32
--
-- Width is chosen from the existing `size`: size>=2 gets the 32-bit variant, else 16-bit.
-- Today only one row exists (point 95: enum, size=1 -> enum16); the bitfield/status_word
-- statements are no-ops now but keep the normalization complete.

UPDATE device_points SET data_type = CASE WHEN size >= 2 THEN 'enum32' ELSE 'enum16' END
    WHERE data_type = 'enum';

UPDATE device_points SET data_type = CASE WHEN size >= 2 THEN 'bitfield32' ELSE 'bitfield16' END
    WHERE data_type = 'bitfield';

UPDATE device_points SET data_type = CASE WHEN size >= 2 THEN 'status_word32' ELSE 'status_word16' END
    WHERE data_type = 'status_word';
