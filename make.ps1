# PowerShell script for managing Docker containers
# Usage: .\make.ps1 <command>

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host "Available commands:"
    Write-Host "  .\make.ps1 up-build   - Build and start containers"
    Write-Host "  .\make.ps1 up          - Start containers"
    Write-Host "  .\make.ps1 down        - Stop and remove containers"
    Write-Host "  .\make.ps1 build       - Build the Docker image (uses cache)"
    Write-Host "  .\make.ps1 rebuild     - Rebuild the Docker image (no cache, forces fresh build)"
    Write-Host "  .\make.ps1 up-rebuild  - Rebuild (no cache) and start containers"
    Write-Host "  .\make.ps1 restart     - Restart the containers"
    Write-Host "  .\make.ps1 logs       - View container logs"
    Write-Host "  .\make.ps1 shell      - Open a shell in the container"
    Write-Host "  .\make.ps1 ps         - View container status"
    Write-Host "  .\make.ps1 health     - Check service health"
    Write-Host "  .\make.ps1 clean      - Stop containers and remove images"
    Write-Host ""
    Write-Host "Development commands:"
    Write-Host "  .\make.ps1 test-setup - Prepare test environment (ensure containers are running)"
    Write-Host "  .\make.ps1 test       - Run tests (ensures containers are up first)"
    Write-Host ""
    Write-Host "Or use: make.ps1 <command>"
}

function Invoke-TestSetup {
    Write-Host "Preparing test environment..." -ForegroundColor Green
    Write-Host "Checking if Redis container is running..." -ForegroundColor Cyan
    
    $redisStatus = docker-compose ps redis 2>$null | Select-String "Up"
    if (-not $redisStatus) {
        Write-Host "Starting Redis container..." -ForegroundColor Yellow
        docker-compose up -d redis
    } else {
        Write-Host "Redis container is already running" -ForegroundColor Green
    }
    
    Write-Host "Waiting for Redis to be healthy..." -ForegroundColor Cyan
    $timeout = 30
    $ready = $false
    
    while ($timeout -gt 0) {
        try {
            $result = docker-compose exec -T redis redis-cli ping 2>$null
            if ($result -match "PONG") {
                Write-Host "Redis is ready!" -ForegroundColor Green
                $ready = $true
                break
            }
        } catch {
            # Continue waiting
        }
        Start-Sleep -Seconds 1
        $timeout--
    }
    
    if (-not $ready) {
        Write-Host "Warning: Redis health check timeout" -ForegroundColor Yellow
    }
}

switch ($Command.ToLower()) {
    "up-build" {
        Write-Host "Building and starting containers..." -ForegroundColor Green
        docker-compose up -d --build
    }
    "up" {
        Write-Host "Starting containers..." -ForegroundColor Green
        docker-compose up -d
    }
    "down" {
        Write-Host "Stopping containers..." -ForegroundColor Yellow
        docker-compose down
    }
    "build" {
        Write-Host "Building Docker image (using cache)..." -ForegroundColor Green
        docker-compose build
    }
    "rebuild" {
        Write-Host "Rebuilding Docker image (no cache - forces fresh build)..." -ForegroundColor Yellow
        docker-compose build --no-cache
    }
    "up-rebuild" {
        Write-Host "Rebuilding Docker image (no cache)..." -ForegroundColor Yellow
        docker-compose build --no-cache
        Write-Host "Starting containers..." -ForegroundColor Green
        docker-compose up -d
    }
    "restart" {
        Write-Host "Restarting containers..." -ForegroundColor Yellow
        docker-compose restart
    }
    "logs" {
        Write-Host "Viewing container logs (Ctrl+C to exit)..." -ForegroundColor Cyan
        docker-compose logs -f pae-rtac-server
    }
    "shell" {
        Write-Host "Opening shell in container..." -ForegroundColor Cyan
        docker-compose exec pae-rtac-server /bin/bash
    }
    "ps" {
        Write-Host "Container status:" -ForegroundColor Cyan
        docker-compose ps
    }
    "health" {
        Write-Host "Checking service health..." -ForegroundColor Cyan
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -ErrorAction Stop
            $response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
        }
        catch {
            Write-Host "Service not available" -ForegroundColor Red
            Write-Host $_.Exception.Message -ForegroundColor Red
        }
    }
    "clean" {
        Write-Host "Cleaning up containers and images..." -ForegroundColor Yellow
        docker-compose down
        docker rmi pae-rtac-server 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Image not found or already removed" -ForegroundColor Yellow
        }
    }
    "test-setup" {
        Invoke-TestSetup
    }
    "test" {
        Invoke-TestSetup
        
        Write-Host "Running tests..." -ForegroundColor Green
        $env:PYTHONPATH = "src"
        pytest tests/ -v
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Tests completed with exit code: $LASTEXITCODE" -ForegroundColor Yellow
        }
    }
    default {
        Show-Help
    }
}


