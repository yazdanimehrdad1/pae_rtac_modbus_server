.PHONY: help up down build rebuild up-build up-rebuild restart logs shell clean ps health dev test-setup test lint format migrate apply-migration run

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
	@echo "  make format     - Format code (black, ruff)"
	@echo "  make migrate    - Run database migrations"
	@echo "  make apply-migration - Apply database migrations (in container)"
	@echo "  make run        - Run service locally (non-Docker)"

# Start containers (ensures postgres is healthy, then starts services)
up:
	@echo "Starting services..."
	@docker-compose -f docker-compose.yaml up -d postgres redis
	@echo "Waiting for PostgreSQL to be healthy..."
	@timeout=60; \
	while [ $$timeout -gt 0 ]; do \
		if docker-compose -f docker-compose.yaml exec -T postgres pg_isready -U $$POSTGRES_USER 2>/dev/null || docker-compose -f docker-compose.yaml exec -T postgres pg_isready -U rtac_user 2>/dev/null; then \
			echo "PostgreSQL is ready!"; \
			break; \
		fi; \
		sleep 1; \
		timeout=$$((timeout-1)); \
	done; \
	if [ $$timeout -eq 0 ]; then \
		echo "ERROR: PostgreSQL health check timeout"; \
		exit 1; \
	fi
	@echo "Starting application service (migrations will run automatically)..."
	@docker-compose -f docker-compose.yaml up -d pae-rtac-server

# Stop and remove containers
down:
	docker-compose -f docker-compose.yaml down

# Build the Docker image (uses cache)
build:
	docker-compose -f docker-compose.yaml build

# Rebuild the Docker image (no cache - forces fresh build)
rebuild:
	docker-compose -f docker-compose.yaml build --no-cache

# Build and start containers
up-build:
	@echo "Building and starting services..."
	@docker-compose -f docker-compose.yaml build
	@docker-compose -f docker-compose.yaml up -d postgres redis
	@echo "Waiting for PostgreSQL to be healthy..."
	@timeout=60; \
	while [ $$timeout -gt 0 ]; do \
		if docker-compose -f docker-compose.yaml exec -T postgres pg_isready -U $$POSTGRES_USER 2>/dev/null || docker-compose -f docker-compose.yaml exec -T postgres pg_isready -U rtac_user 2>/dev/null; then \
			echo "PostgreSQL is ready!"; \
			break; \
		fi; \
		sleep 1; \
		timeout=$$((timeout-1)); \
	done; \
	if [ $$timeout -eq 0 ]; then \
		echo "ERROR: PostgreSQL health check timeout"; \
		exit 1; \
	fi
	@echo "Starting application service (migrations will run automatically)..."
	@docker-compose -f docker-compose.yaml up -d pae-rtac-server

# Rebuild and start containers (no cache)
up-rebuild:
	@echo "Rebuilding and starting services..."
	@docker-compose -f docker-compose.yaml build --no-cache
	@docker-compose -f docker-compose.yaml up -d postgres redis
	@echo "Waiting for PostgreSQL to be healthy..."
	@timeout=60; \
	while [ $$timeout -gt 0 ]; do \
		if docker-compose -f docker-compose.yaml exec -T postgres pg_isready -U $$POSTGRES_USER 2>/dev/null || docker-compose -f docker-compose.yaml exec -T postgres pg_isready -U rtac_user 2>/dev/null; then \
			echo "PostgreSQL is ready!"; \
			break; \
		fi; \
		sleep 1; \
		timeout=$$((timeout-1)); \
	done; \
	if [ $$timeout -eq 0 ]; then \
		echo "ERROR: PostgreSQL health check timeout"; \
		exit 1; \
	fi
	@echo "Starting application service (migrations will run automatically)..."
	@docker-compose -f docker-compose.yaml up -d pae-rtac-server

# Restart containers
restart:
	docker-compose -f docker-compose.yaml restart

# View logs
logs:
	docker-compose -f docker-compose.yaml logs -f pae-rtac-server

# Open a shell in the container
shell:
	docker-compose -f docker-compose.yaml exec pae-rtac-server /bin/bash

# Clean up containers and images
clean:
	docker-compose -f docker-compose.yaml down
	docker rmi pae-rtac-server 2>/dev/null || true

# View container status
ps:
	docker-compose -f docker-compose.yaml ps

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
	@docker-compose -f docker-compose.yaml ps redis | grep -q "Up" || docker-compose -f docker-compose.yaml up -d redis
	@echo "Waiting for Redis to be healthy..."
	@timeout=30; \
	while [ $$timeout -gt 0 ]; do \
		if docker-compose -f docker-compose.yaml exec -T redis redis-cli ping > /dev/null 2>&1; then \
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
format:
	@echo "Formatting Python files with black..."
	@docker-compose -f docker-compose.yaml exec pae-rtac-server black src/ 2>/dev/null || echo "Note: Running black in container..."
	@echo "Running ruff to fix import sorting and other issues..."
	@docker-compose -f docker-compose.yaml exec pae-rtac-server ruff check --fix src/ 2>/dev/null || echo "Note: Running ruff in container..."
	@echo "Formatting complete!"


# Run database migrations
migrate:
	@python scripts/migrate_db.py

# Apply database migrations (in container)
apply-migration:
	@docker-compose -f docker-compose.yaml exec pae-rtac-server python scripts/migrate_db.py

# Run the service locally (non-Docker)
run:
	@cd src && python -m main


