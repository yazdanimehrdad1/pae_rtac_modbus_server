.PHONY: help up down build rebuild up-build up-rebuild restart logs shell clean ps health dev test-setup test lint fmt migrate run

# Default target
help:
	@echo "Available commands:"
	@echo "  make up       - Start the containers"
	@echo "  make up-build - Build and start containers"
	@echo "  make down     - Stop and remove containers"
	@echo "  make build     - Build the Docker image (uses cache)"
	@echo "  make rebuild   - Rebuild the Docker image (no cache, forces fresh build)"
	@echo "  make up-rebuild - Rebuild (no cache) and start containers"
	@echo "  make restart   - Restart the containers"
	@echo "  make logs     - View container logs"
	@echo "  make shell    - Open a shell in the container"
	@echo "  make ps       - View container status"
	@echo "  make health   - Check service health"
	@echo "  make clean    - Stop containers and remove images"
	@echo ""
	@echo "Development commands:"
	@echo "  make dev        - Start development environment"
	@echo "  make test-setup - Prepare test environment (ensure containers are running)"
	@echo "  make test       - Run tests (ensures containers are up first)"
	@echo "  make lint       - Run linters (ruff, mypy)"
	@echo "  make fmt        - Format code (black, ruff)"
	@echo "  make migrate    - Run database migrations"
	@echo "  make run        - Run service locally (non-Docker)"

# Start containers
up:
	docker-compose -f compose.yaml up -d

# Stop and remove containers
down:
	docker-compose -f compose.yaml down

# Build the Docker image (uses cache)
build:
	docker-compose -f compose.yaml build

# Rebuild the Docker image (no cache - forces fresh build)
rebuild:
	docker-compose -f compose.yaml build --no-cache

# Build and start containers
up-build:
	docker-compose -f compose.yaml up -d --build

# Rebuild and start containers (no cache)
up-rebuild:
	docker-compose -f compose.yaml build --no-cache
	docker-compose -f compose.yaml up -d

# Restart containers
restart:
	docker-compose -f compose.yaml restart

# View logs
logs:
	docker-compose -f compose.yaml logs -f pae-rtac-server

# Open a shell in the container
shell:
	docker-compose -f compose.yaml exec pae-rtac-server /bin/bash

# Clean up containers and images
clean:
	docker-compose -f compose.yaml down
	docker rmi pae-rtac-server 2>/dev/null || true

# View container status
ps:
	docker-compose -f compose.yaml ps

# Check service health
health:
	@curl -s http://localhost:8000/healthz || echo "Service not responding"

# Development commands
dev:
	@echo "Starting development environment..."
	# TODO: Add development setup (install deps, run tests, etc.)

# Prepare test environment - ensure Redis container is running
test-setup:
	@echo "Preparing test environment..."
	@echo "Checking if Redis container is running..."
	@docker-compose -f compose.yaml ps redis | grep -q "Up" || docker-compose -f compose.yaml up -d redis
	@echo "Waiting for Redis to be healthy..."
	@timeout=30; \
	while [ $$timeout -gt 0 ]; do \
		if docker-compose -f compose.yaml exec -T redis redis-cli ping > /dev/null 2>&1; then \
			echo "Redis is ready!"; \
			break; \
		fi; \
		sleep 1; \
		timeout=$$((timeout-1)); \
	done; \
	if [ $$timeout -eq 0 ]; then \
		echo "Warning: Redis health check timeout"; \
	fi

# Run tests - ensures containers are up first
test: test-setup
	@echo "Running tests..."
	@PYTHONPATH=src pytest tests/ -v

# Run linting
lint:
	@ruff check src/ tests/
	@mypy src/

# Format code
fmt:
	@black src/ tests/
	@ruff check --fix src/ tests/

# Run database migrations
migrate:
	@python scripts/migrate_db.py

# Run the service locally (non-Docker)
run:
	@cd src && python -m main


