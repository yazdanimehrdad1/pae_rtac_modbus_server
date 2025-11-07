.PHONY: help up down build restart logs shell clean ps health up-build dev test lint fmt migrate run

# Default target
help:
	@echo "Available commands:"
	@echo "  make up       - Start the containers"
	@echo "  make up-build - Build and start containers"
	@echo "  make down     - Stop and remove containers"
	@echo "  make build    - Build the Docker image"
	@echo "  make restart  - Restart the containers"
	@echo "  make logs     - View container logs"
	@echo "  make shell    - Open a shell in the container"
	@echo "  make ps       - View container status"
	@echo "  make health   - Check service health"
	@echo "  make clean    - Stop containers and remove images"
	@echo ""
	@echo "Development commands:"
	@echo "  make dev      - Start development environment"
	@echo "  make test     - Run tests"
	@echo "  make lint     - Run linters (ruff, mypy)"
	@echo "  make fmt      - Format code (black, ruff)"
	@echo "  make migrate  - Run database migrations"
	@echo "  make run      - Run service locally (non-Docker)"

# Start containers
up:
	docker-compose -f compose.yaml up -d

# Stop and remove containers
down:
	docker-compose -f compose.yaml down

# Build the Docker image
build:
	docker-compose -f compose.yaml build

# Build and start containers
up-build:
	docker-compose -f compose.yaml up -d --build

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

# Run tests
test:
	@pytest tests/ -v

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
	@python -m rtac_modbus_service.main


