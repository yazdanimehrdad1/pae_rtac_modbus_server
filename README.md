# Modbus TCP FastAPI Microservice

A FastAPI-based REST API service for communicating with Modbus TCP servers using pymodbus.

## Features

- **GET /health**: Health check endpoint with connection test and small read verification
- **POST /read**: Read holding registers, input registers, coils, or discrete inputs
- Robust error handling with proper HTTP status codes
- Environment variable configuration
- Clean connection management (no socket leaks)
- **Distributed Scheduler**: APScheduler with Redis-based leader election for multi-replica Kubernetes deployments

## Scheduler Implementation

The service includes a distributed scheduler system for periodic Modbus polling and data storage jobs. **Step 1**: Added APScheduler dependency to requirements.txt for async job scheduling. **Step 2**: Configured scheduler settings in config.py including leader lock TTL, heartbeat interval, and pod identification. **Step 3**: Implemented Redis-based distributed locking system with leader election and per-job execution locks in scheduler/locks.py. **Step 4**: Created scheduler engine in scheduler/engine.py that wraps all jobs with lock verification before execution. **Step 5**: Integrated scheduler lifecycle into FastAPI app startup/shutdown hooks for automatic initialization and cleanup.

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

The service uses environment variables for configuration. You can set them in two ways:

### Option 1: Using .env file (Recommended)

Create or edit `.env` file in the project root with your Modbus server settings:
```env
MODBUS_HOST=192.168.1.100
MODBUS_PORT=502
MODBUS_UNIT_ID=1
MODBUS_TIMEOUT_S=5.0
MODBUS_RETRIES=3
```

The `.env` file is automatically loaded when the service starts.

### Option 2: Environment Variables

Set the following environment variables:

**Linux/Mac:**
```bash
export MODBUS_HOST="192.168.1.100"      # Default: localhost
export MODBUS_PORT="502"                 # Default: 502
export MODBUS_UNIT_ID="1"                # Default: 1
export MODBUS_TIMEOUT_S="5.0"            # Default: 5.0
export MODBUS_RETRIES="3"                # Default: 3
```

**Windows PowerShell:**
```powershell
$env:MODBUS_HOST="192.168.1.100"
$env:MODBUS_PORT="502"
$env:MODBUS_UNIT_ID="1"
$env:MODBUS_TIMEOUT_S="5.0"
$env:MODBUS_RETRIES="3"
```

## Running Locally

### Option 1: Using Makefile/Make Script (Recommended - Simplest)

**Windows (PowerShell):**
```powershell
# Configure your external Modbus server in .env file first
.\make.ps1 up-build

# View all available commands
.\make.ps1
```

**Linux/Mac:**
```bash
# Configure your external Modbus server in .env file first
make up-build

# View all available commands
make help
```

**Common commands:**
```bash
# Windows PowerShell
.\make.ps1 up-build   # Build and start containers
.\make.ps1 up         # Start containers
.\make.ps1 down       # Stop containers
.\make.ps1 logs       # View logs
.\make.ps1 restart    # Restart containers
.\make.ps1 health     # Check service health
.\make.ps1 ps         # View container status

# Linux/Mac
make up-build   # Build and start containers
make up         # Start containers
make down       # Stop containers
make logs       # View logs
make restart    # Restart containers
make health     # Check service health
make ps         # View container status
```

The API will be available at `http://localhost:8000`

### Option 2: Using Docker Compose Directly

**Configure your external Modbus server in `.env` file:**
```bash
MODBUS_HOST=192.168.1.100  # Your external Modbus server IP
MODBUS_PORT=502
MODBUS_UNIT_ID=1
```

**Then start the service:**
```bash
docker-compose up --build
```

**Or set environment variables directly:**
```bash
MODBUS_HOST=192.168.1.100 docker-compose up --build
```

### Option 3: Direct Python Execution

Start the service with uvicorn:

```bash
uvicorn modbus_service:app --host 0.0.0.0 --port 8000 --reload
```

Or run directly:

```bash
python modbus_service.py
```

The API will be available at `http://localhost:8000`

API documentation (Swagger UI) available at: `http://localhost:8000/docs`

## Docker Details

### Architecture Decision

**Single Container Approach:** The FastAPI service and Modbus client are kept in the same container because:
- The Modbus client is a Python library/module, not a separate service
- They share the same Python process - no network boundary needed
- Simpler deployment, debugging, and resource management
- Standard microservice pattern

### Docker Commands

**Build the image:**
```bash
docker build -t pae-rtac-server .
```

**Run the container:**
```bash
docker run -p 8000:8000 \
  -e MODBUS_HOST=192.168.1.100 \
  -e MODBUS_PORT=502 \
  pae-rtac-server
```

**Run with docker-compose (connects to external Modbus server):**
```bash
# Make sure MODBUS_HOST is set in .env or as environment variable
docker-compose up --build
```

**Stop services:**
```bash
docker-compose down
```

**View logs:**
```bash
docker-compose logs -f pae-rtac-server
```

## Example curl Commands

### Health Check

```bash
curl -X GET "http://localhost:8000/health" | jq
```

Expected response:
```json
{
  "ok": true,
  "host": "192.168.1.100",
  "port": 502,
  "unit_id": 1,
  "detail": "Connection and read test successful"
}
```

### Read Holding Registers

```bash
curl -X POST "http://localhost:8000/read" \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "holding",
    "address": 0,
    "count": 10,
    "unit_id": 1
  }' | jq
```

Expected response:
```json
{
  "ok": true,
  "kind": "holding",
  "address": 0,
  "count": 10,
  "unit_id": 1,
  "data": [1234, 5678, 9012, 3456, 7890, 1234, 5678, 9012, 3456, 7890]
}
```

### Read Input Registers

```bash
curl -X POST "http://localhost:8000/read" \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "input",
    "address": 0,
    "count": 5
  }' | jq
```

### Read Coils

```bash
curl -X POST "http://localhost:8000/read" \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "coils",
    "address": 0,
    "count": 8
  }' | jq
```

### Read Discrete Inputs

```bash
curl -X POST "http://localhost:8000/read" \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "discretes",
    "address": 0,
    "count": 16
  }' | jq
```

## Error Handling

The service translates Modbus errors into appropriate HTTP status codes:

- **400 Bad Request**: Invalid Modbus parameters or illegal function/data address
- **503 Service Unavailable**: Connection failures
- **504 Gateway Timeout**: Request timeouts
- **500 Internal Server Error**: Unexpected errors

Example error response:
```json
{
  "detail": "Illegal data address - The data address received is not valid"
}
```

## Future Enhancements

The code includes TODO comments for:
- Persistent pooled client connections
- Prometheus metrics integration
- Batch polling multiple addresses
- Word/byte-order conversions for 32/64-bit values

## Testing with a Modbus Simulator

For local testing, you can use a Modbus simulator like:
- [ModbusPal](https://modbuspal.sourceforge.net/)
- [pymodbus simulator](https://pymodbus.readthedocs.io/en/latest/source/example/simulator.html)

Then point the service to `localhost:502` and test the endpoints.

