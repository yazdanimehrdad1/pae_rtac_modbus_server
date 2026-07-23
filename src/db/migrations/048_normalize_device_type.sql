-- Migration: 048_normalize_device_type
-- Canonicalize devices.type to UPPERCASE and constrain it to the supported vocabulary.
--
-- The API previously accepted a 5-value mixed-case list (meter, relay, RTAC, inverter,
-- BESS) that disagreed with the standardized-point registry keys (BESS, ES, INVERTER, PV,
-- GENERATOR, LOADBANK, RELAY, IED). The vocabulary below is the union of both, so no
-- previously-valid type is lost and the 5 orphaned point templates become reachable.
--
-- Order matters: the UPDATE must run before the constraint is added, otherwise existing
-- lowercase rows (e.g. 'relay') violate it. If any row holds a type outside this list the
-- migration fails loudly — that is intentional, not something to work around.

UPDATE devices SET type = UPPER(type);

ALTER TABLE devices ADD CONSTRAINT devices_type_check
    CHECK (type IN ('BESS','ES','INVERTER','PV','GENERATOR',
                    'LOADBANK','RELAY','IED','METER','RTAC'));
