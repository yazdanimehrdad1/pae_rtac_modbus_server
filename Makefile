.PHONY: help up down build restart logs shell clean ps health up-build

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

# Start containers
up:
	docker-compose up -d

# Stop and remove containers
down:
	docker-compose down

# Build the Docker image
build:
	docker-compose build

# Build and start containers
up-build:
	docker-compose up -d --build

# Restart containers
restart:
	docker-compose restart

# View logs
logs:
	docker-compose logs -f modbus-api

# Open a shell in the container
shell:
	docker-compose exec modbus-api /bin/bash

# Clean up containers and images
clean:
	docker-compose down
	docker rmi modbus-api 2>/dev/null || true

# View container status
ps:
	docker-compose ps

# Check health
health:
	@python -c "import urllib.request, json; print(json.dumps(json.loads(urllib.request.urlopen('http://localhost:8000/health').read()), indent=2))" 2>/dev/null || echo "Service not available"

