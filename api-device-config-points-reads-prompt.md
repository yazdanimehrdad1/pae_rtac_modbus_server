## Prompt: Device Points, Configs, and Register Readings API Client

Build a client/service that calls **device points**, **device configs**, and **register readings** endpoints.

Base URL: `{{base_url}}/api`  
Auth: none (unless specified elsewhere)  
Content-Type: `application/json`

---

### 1) Device Configs
**Create config**  
`POST /configs/site/{site_id}/device/{device_id}`  
Path params: `site_id` (int), `device_id` (int)

Body example:
```json
{
  "poll_kind": "holding",
  "poll_start_index": 1400,
  "poll_count": 36,
  "points": [
    {
      "name": "M_FREQ",
      "address": 1400,
      "size": 1,
      "data_type": "bitfield32",
      "scale_factor": 0.1,
      "unit": "Hz",
      "bitfield_detail": {
        "01": "On",
        "02": "Off"
      }
    },
    {
      "name": "M_FREQS",
      "address": 1401,
      "size": 1,
      "data_type": "uint16",
      "scale_factor": 0.1,
      "unit": "Hz"
    }
  ],
  "is_active": true,
  "created_by": "operator@example.com"
}
```

**Get config by id**  
`GET /configs/{config_id}`  
Path params: `config_id` (string)

**Update config**  
`PUT /configs/{config_id}`  
Body example:
```json
{
  "is_active": false
}
```

**Delete config**  
`DELETE /configs/{config_id}`

---

### 2) Device Points (Read-only)
**Get all points for device**  
`GET /device-points/site/{site_id}/device/{device_id}`  
Path params: `site_id` (int), `device_id` (int)

Example:
```
GET /device-points/site/1001/device/1
```

---

### 3) Register Readings
**Latest readings (per register, grouped by address)**  
`GET /register_readings/site/{site_id}/device/{device_id}/latest`  
Query params:
- `register_addresses` (optional, comma-separated list like `1400,1401`)

Example:
```
GET /register_readings/site/1001/device/1/latest?register_addresses=1400,1401
```

**Latest N readings per point**  
`GET /register_readings/site/{site_id}/device/{device_id}/latest-n`  
Query params:
- `latest_n` (int, default 1)
- `register_addresses` (optional, comma-separated)

Example:
```
GET /register_readings/site/1001/device/1/latest-n?latest_n=5&register_addresses=1400,1401
```

**Time series**  
`GET /register_readings/timeseries/site/{site_id}/device/{device_id}`  
Query params:
- `register_addresses` (optional, comma-separated)
- `start_time` (optional, ISO format `2025-01-18T08:00:00Z`)
- `end_time` (optional, ISO format `2025-01-18T09:00:00Z`)
- `limit` (optional, int, default 1000, max 10000)

Example:
```
GET /register_readings/timeseries/site/1001/device/1?register_addresses=1400,1401&start_time=2025-01-18T08:00:00Z&end_time=2025-01-18T09:00:00Z&limit=1000
```

---

### Expected behavior
- Handle `404` for missing site/device/config.
- Send/parse JSON bodies for create/update.
- Parse readings responses and handle grouped results by register address.
