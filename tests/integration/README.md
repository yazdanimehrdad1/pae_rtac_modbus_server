# Integration tests

These require both postgres and redis to be up (`.\make.ps1 up` / `make up`), not just
redis — `make test` only starts redis.

Run with: `PYTHONPATH=src pytest tests/integration/ -v`

## Planned coverage

Tracked here rather than as empty stub modules, so `pytest` collection reflects what
actually exists.

### Redis cache (`cache/cache.py`, `api/routers/cache.py`)
- [ ] Connection and health checks
- [ ] Basic operations: set, get, delete
- [ ] Different value types (strings, dicts, lists)
- [ ] TTL expiry
- [ ] Increment/decrement
- [ ] Pattern-based clearing and key prefixing
- [ ] Error handling and reconnection
- [ ] Concurrent operations
- [ ] Invalid/expired keys
- [ ] Memory limits and eviction policies
- [ ] Cleanup on application shutdown

### Database round-trip (`db/`, `schemas/db_models/orm_models.py`)
- [ ] Write readings, read back, verify correctness
- [ ] Time-range queries (`device_points_readings`)
- [ ] Soft-delete / restore behavior on sites, devices, device points

### Polling pipeline (`helpers/modbus/`, `helpers/workers/device_poll.py`)
- [ ] Poll a Modbus device (against the sibling `mock-modbus-server`)
- [ ] Decode and sanitize the raw registers
- [ ] Persist to `device_points_readings`
- [ ] Verify the end-to-end flow, including scan-range chunking above
      `MODBUS_MAX_REGISTERS_PER_READ`
