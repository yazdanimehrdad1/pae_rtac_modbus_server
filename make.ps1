# PowerShell script for managing Docker containers
# Usage: .\make.ps1 <command>

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host "Available commands:"
    Write-Host "  .\make.ps1 up-build  - Build and start containers"
    Write-Host "  .\make.ps1 up         - Start containers"
    Write-Host "  .\make.ps1 down       - Stop and remove containers"
    Write-Host "  .\make.ps1 build     - Build the Docker image"
    Write-Host "  .\make.ps1 restart    - Restart the containers"
    Write-Host "  .\make.ps1 logs       - View container logs"
    Write-Host "  .\make.ps1 shell      - Open a shell in the container"
    Write-Host "  .\make.ps1 ps         - View container status"
    Write-Host "  .\make.ps1 health     - Check service health"
    Write-Host "  .\make.ps1 clean      - Stop containers and remove images"
    Write-Host ""
    Write-Host "Or use: make.ps1 <command>"
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
        Write-Host "Building Docker image..." -ForegroundColor Green
        docker-compose build
    }
    "restart" {
        Write-Host "Restarting containers..." -ForegroundColor Yellow
        docker-compose restart
    }
    "logs" {
        Write-Host "Viewing container logs (Ctrl+C to exit)..." -ForegroundColor Cyan
        docker-compose logs -f modbus-api
    }
    "shell" {
        Write-Host "Opening shell in container..." -ForegroundColor Cyan
        docker-compose exec modbus-api /bin/bash
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
        docker rmi modbus-api 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Image not found or already removed" -ForegroundColor Yellow
        }
    }
    default {
        Show-Help
    }
}


