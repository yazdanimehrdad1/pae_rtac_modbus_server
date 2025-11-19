# Time-Series Table Implementation Plan

## Overview

This document outlines the step-by-step plan to create a TimescaleDB hypertable for storing Modbus register readings and integrating it with the existing polling system.

**Current State:**
- Data is polled from Modbus devices via scheduler (`src/scheduler/jobs.py`)
- Data is currently stored in Redis cache only
- Database has `devices` and `device_register_map` tables
- Migration system exists (`scripts/migrate_db.py`)

**Target State:**
- Create `register_readings` hypertable in TimescaleDB
- Store all polled register data in the database
- Keep Redis cache for fast latest-value queries (optional)
- Enable time-series queries for frontend visualization

---

## Phase 1: Database Schema Creation

### Step 1.1: Create Migration File
- **File:** `src/db/migrations/003_create_register_readings_table.sql`
- **Purpose:** Create the time-series table schema
- **Actions:**
  1. Create `register_readings` table with all required columns
  2. Add foreign key constraint to `devices` table
  3. Add table and column comments
  4. Create primary key on `(timestamp, device_id, register_address)`

### Step 1.2: Convert to Hypertable
- **In same migration file**
- **Purpose:** Enable TimescaleDB features (chunking, compression)
- **Actions:**
  1. Ensure TimescaleDB extension is enabled
  2. Convert table to hypertable with daily chunking
  3. Verify hypertable creation

### Step 1.3: Create Indexes
- **In same migration file**
- **Purpose:** Optimize query performance
- **Actions:**
  1. Create composite index: `(device_id, register_address, timestamp DESC)`
  2. Optional: Create partial index for quality filtering
  3. Verify indexes are created

### Step 1.4: Set Up TimescaleDB Policies
- **In same migration file (or separate migration)**
- **Purpose:** Automate compression and retention
- **Actions:**
  1. Add compression policy (compress data older than 7 days)
  2. Add retention policy (drop data older than 1 year - configurable)
  3. Verify policies are active

### Step 1.5: Create Continuous Aggregates (Optional)
- **In same migration file or separate migration**
- **Purpose:** Pre-aggregate data for faster queries on longer time ranges
- **Actions:**
  1. Create hourly aggregate materialized view
  2. Set up refresh policy for continuous aggregate
  3. Verify aggregate is working

---

## Phase 2: Database Access Layer

### Step 2.1: Create Database Module
- **File:** `src/db/register_readings.py`
- **Purpose:** Database operations for register_readings table
- **Functions to create:**
  1. `insert_register_reading()` - Insert single reading
  2. `insert_register_readings_batch()` - Batch insert (for efficiency)
  3. `get_latest_reading()` - Get latest value for a register
  4. `get_readings_time_range()` - Get readings for time range
  5. `get_device_readings_latest()` - Get latest readings for all registers of a device

### Step 2.2: Batch Insert Strategy
- **Purpose:** Efficiently insert multiple readings at once
- **Approach:**
  - Use `asyncpg.copy_records_to_table()` for bulk inserts
  - Or use `INSERT ... VALUES` with multiple rows
  - Batch size: 100-1000 rows per insert (configurable)
  - Handle errors gracefully (log failed inserts, continue with rest)

### Step 2.3: Data Quality Handling
- **Purpose:** Track data quality (good/bad/uncertain)
- **Approach:**
  - Set quality='good' by default
  - Set quality='bad' if Modbus read fails
  - Set quality='uncertain' if value is out of expected range
  - Allow manual quality updates via API (future)

---

## Phase 3: Integration with Polling System

### Step 3.1: Modify Polling Job
- **File:** `src/scheduler/jobs.py`
- **Function:** `cron_job_poll_modbus_registers()`
- **Changes:**
  1. After successful Modbus read and mapping
  2. Before/after storing in Redis cache
  3. Call database insert function to store readings
  4. Handle database errors gracefully (log, don't fail entire job)
  5. Get device_id from device name (lookup in devices table)

### Step 3.2: Device ID Resolution
- **Purpose:** Map device name to device_id for database storage
- **Approach:**
  - Option A: Lookup device_id from devices table using device name
  - Option B: Pass device_id as parameter to polling job
  - Option C: Cache device_id mapping in memory (refresh on startup)
  - **Recommendation:** Option C (cache) for performance

### Step 3.3: Register Metadata Denormalization
- **Purpose:** Store register_name, data_type, unit in each reading (avoid joins)
- **Approach:**
  - When inserting readings, also fetch register metadata from register_map
  - Include register_name, data_type, unit in insert
  - This makes queries faster (no joins needed)

### Step 3.4: Error Handling
- **Purpose:** Ensure polling job continues even if database insert fails
- **Approach:**
  - Wrap database insert in try/except
  - Log errors but don't raise
  - Continue with Redis cache storage
  - Track failed inserts for monitoring

---

## Phase 4: Multi-Device Support

### Step 4.1: Device Iteration in Polling Job
- **Current:** Polls single device (main-sel-751)
- **Target:** Poll all active devices from database
- **Changes:**
  1. Query devices table for all active devices
  2. For each device:
     - Get device connection info (host, port, unit_id)
     - Get register map for device
     - Poll registers
     - Store readings in database
  3. Handle device-specific errors (one device failure doesn't stop others)

### Step 4.2: Device-Specific Register Maps
- **Purpose:** Each device may have different register map
- **Approach:**
  - Load register map from `device_register_map` table (already exists)
  - Use device-specific register map for polling
  - Store readings with correct register_address and metadata

### Step 4.3: Parallel Polling (Optional)
- **Purpose:** Poll multiple devices concurrently
- **Approach:**
  - Use `asyncio.gather()` to poll devices in parallel
  - Limit concurrency (e.g., max 5 devices at once)
  - Handle timeouts and errors per device

---

## Phase 5: API Endpoints (Future)

### Step 5.1: Query Endpoints
- **File:** `src/api/routers/register_readings.py` (new)
- **Endpoints to create:**
  1. `GET /api/register_readings/latest/{device_id}` - Latest readings for device
  2. `GET /api/register_readings/{device_id}/{register_address}` - Time series for specific register
  3. `GET /api/register_readings/{device_id}` - Time series for all registers (with filters)
  4. `GET /api/register_readings/range` - Query with time range, device, registers

### Step 5.2: Response Models
- **File:** `src/schemas/api_models/register_readings.py` (new)
- **Models:**
  1. `RegisterReadingResponse` - Single reading
  2. `RegisterReadingsTimeSeriesResponse` - Array of readings with metadata
  3. `RegisterReadingsQueryRequest` - Query parameters (device_id, register_address, time_range)

---

## Phase 6: Testing & Validation

### Step 6.1: Migration Testing
- **Actions:**
  1. Run migration on test database
  2. Verify table creation
  3. Verify hypertable conversion
  4. Verify indexes creation
  5. Verify compression/retention policies

### Step 6.2: Insert Testing
- **Actions:**
  1. Test single insert
  2. Test batch insert
  3. Test error handling (invalid device_id, etc.)
  4. Verify data quality flags

### Step 6.3: Query Testing
- **Actions:**
  1. Test latest value queries
  2. Test time range queries
  3. Test multi-register queries
  4. Verify query performance (< 100ms for typical queries)

### Step 6.4: Integration Testing
- **Actions:**
  1. Run polling job
  2. Verify data is stored in database
  3. Verify Redis cache still works (if keeping it)
  4. Monitor for errors

### Step 6.5: Performance Testing
- **Actions:**
  1. Test with 30 devices, 100 registers each
  2. Test with 5-second polling
  3. Monitor insert performance
  4. Monitor query performance
  5. Monitor database size growth

---

## Phase 7: Monitoring & Maintenance

### Step 7.1: Logging
- **Purpose:** Track database operations
- **Actions:**
  1. Log successful inserts (count, device_id)
  2. Log failed inserts (error details)
  3. Log query performance (slow queries)
  4. Log compression/retention policy execution

### Step 7.2: Metrics (Future)
- **Purpose:** Monitor database health
- **Metrics:**
  1. Insert rate (rows/second)
  2. Query latency (p50, p95, p99)
  3. Database size
  4. Chunk count
  5. Compression ratio

### Step 7.3: Maintenance Tasks
- **Purpose:** Keep database healthy
- **Tasks:**
  1. Monitor chunk count (too many chunks = performance issue)
  2. Monitor index bloat
  3. Monitor compression effectiveness
  4. Review retention policy (adjust as needed)

---

## Implementation Order

### Phase 1: Database Setup (Do First)
1. Create migration file with table, hypertable, indexes, policies
2. Test migration on development database
3. Run migration on production

### Phase 2: Database Access Layer (Do Second)
1. Create `register_readings.py` module
2. Implement insert functions
3. Test insert functions

### Phase 3: Integration (Do Third)
1. Modify polling job to insert into database
2. Test with single device
3. Test with multiple devices

### Phase 4: Multi-Device (Do Fourth)
1. Update polling job to iterate all devices
2. Test parallel polling (if implementing)
3. Monitor performance

### Phase 5: API Endpoints (Do Later)
1. Create API endpoints
2. Test endpoints
3. Document endpoints

### Phase 6: Testing (Throughout)
- Test each phase as you implement it
- Don't move to next phase until current phase is tested

### Phase 7: Monitoring (Ongoing)
- Set up logging from the start
- Add metrics as needed
- Regular maintenance reviews

---

## Key Decisions to Make

### Decision 1: Keep Redis Cache?
- **Option A:** Keep Redis for latest values, use DB for history
  - Pros: Fast latest value queries, less DB load
  - Cons: Data duplication, sync complexity
- **Option B:** Remove Redis, use DB only
  - Pros: Single source of truth, simpler
  - Cons: More DB load for latest value queries
- **Recommendation:** Option A initially, migrate to Option B later if needed

### Decision 2: Batch Insert Size
- **Options:** 100, 500, 1000 rows per batch
- **Recommendation:** Start with 500, adjust based on performance

### Decision 3: Compression Policy
- **Options:** Compress after 1 day, 7 days, 30 days
- **Recommendation:** 7 days (balance between storage and query performance)

### Decision 4: Retention Policy
- **Options:** Keep 6 months, 1 year, 2 years
- **Recommendation:** 1 year initially, adjust based on requirements

### Decision 5: Continuous Aggregates
- **Options:** Create now, create later, don't create
- **Recommendation:** Create now (hourly aggregates) for better long-term query performance

### Decision 6: Error Handling Strategy
- **Options:** Fail fast, log and continue, retry failed inserts
- **Recommendation:** Log and continue (don't fail entire polling job)

---

## File Structure

```
src/
├── db/
│   ├── migrations/
│   │   └── 003_create_register_readings_table.sql  (NEW)
│   ├── register_readings.py  (NEW)
│   └── ...
├── scheduler/
│   └── jobs.py  (MODIFY)
├── api/
│   └── routers/
│       └── register_readings.py  (NEW - Future)
└── schemas/
    └── api_models/
        └── register_readings.py  (NEW - Future)
```

---

## Success Criteria

1. ✅ Migration runs successfully
2. ✅ Table created and converted to hypertable
3. ✅ Indexes created and verified
4. ✅ Compression/retention policies active
5. ✅ Polling job stores data in database
6. ✅ Data is queryable (latest values, time ranges)
7. ✅ Query performance is acceptable (< 100ms for typical queries)
8. ✅ Error handling works (failed inserts don't crash job)
9. ✅ Multi-device polling works
10. ✅ Database size growth is as expected

---

## Next Steps

1. **Review this plan** - Make sure all steps are clear
2. **Make key decisions** - Answer the decision questions above
3. **Start with Phase 1** - Create migration file
4. **Test incrementally** - Test each phase before moving on
5. **Document as you go** - Update this plan with actual implementation details

---

## Questions to Answer Before Starting

1. Do we keep Redis cache or remove it?
2. What batch insert size should we use?
3. What compression policy interval? (7 days recommended)
4. What retention policy? (1 year recommended)
5. Should we create continuous aggregates now or later?
6. How should we handle device_id lookup? (cache recommended)
7. Should we poll devices in parallel or sequentially?

