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
    Write-Host "  .\make.ps1 format     - Format all Python files (black, ruff)"
    Write-Host "  .\make.ps1 lint       - Run ruff linter (CI-enforced; via Docker)"
    Write-Host "  .\make.ps1 lint-fix   - Auto-fix lint issues with ruff (via Docker)"
    Write-Host ""
    Write-Host "Cloud cost control (GKE):"
    Write-Host "  .\make.ps1 cloud-down - Stop all billable compute (scale to 0 + stop Cloud SQL)"
    Write-Host "  .\make.ps1 cloud-up   - Start Cloud SQL and bring everything back ready"
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
        Write-Host "Building and starting services..." -ForegroundColor Green
        docker-compose build
        docker-compose up -d postgres redis
        Write-Host "Waiting for PostgreSQL to be healthy..." -ForegroundColor Cyan
        $timeout = 60
        $ready = $false
        while ($timeout -gt 0) {
            try {
                $env:POSTGRES_USER = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "rtac_user" }
                $result = docker-compose exec -T postgres pg_isready -U $env:POSTGRES_USER 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "PostgreSQL is ready!" -ForegroundColor Green
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
            Write-Host "ERROR: PostgreSQL health check timeout" -ForegroundColor Red
            exit 1
        }
        Write-Host "Starting application service (migrations will run automatically)..." -ForegroundColor Green
        docker-compose up -d pae-rtac-server
    }
    "up" {
        Write-Host "Starting services..." -ForegroundColor Green
        docker-compose up -d postgres redis
        Write-Host "Waiting for PostgreSQL to be healthy..." -ForegroundColor Cyan
        $timeout = 60
        $ready = $false
        while ($timeout -gt 0) {
            try {
                $env:POSTGRES_USER = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "rtac_user" }
                $result = docker-compose exec -T postgres pg_isready -U $env:POSTGRES_USER 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "PostgreSQL is ready!" -ForegroundColor Green
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
            Write-Host "ERROR: PostgreSQL health check timeout" -ForegroundColor Red
            exit 1
        }
        Write-Host "Starting application service (migrations will run automatically)..." -ForegroundColor Green
        docker-compose up -d pae-rtac-server
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
        Write-Host "Rebuilding and starting services..." -ForegroundColor Yellow
        docker-compose build --no-cache
        docker-compose up -d postgres redis
        Write-Host "Waiting for PostgreSQL to be healthy..." -ForegroundColor Cyan
        $timeout = 60
        $ready = $false
        while ($timeout -gt 0) {
            try {
                $env:POSTGRES_USER = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "rtac_user" }
                $result = docker-compose exec -T postgres pg_isready -U $env:POSTGRES_USER 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "PostgreSQL is ready!" -ForegroundColor Green
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
            Write-Host "ERROR: PostgreSQL health check timeout" -ForegroundColor Red
            exit 1
        }
        Write-Host "Starting application service (migrations will run automatically)..." -ForegroundColor Green
        docker-compose up -d pae-rtac-server
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
    "format" {
        Write-Host "Formatting Python files with black..." -ForegroundColor Green
        docker-compose -f docker-compose.yaml exec pae-rtac-server black src/
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Error running black in container" -ForegroundColor Red
            exit $LASTEXITCODE
        }
        
        Write-Host "Running ruff to fix import sorting and other issues..." -ForegroundColor Green
        docker-compose -f docker-compose.yaml exec pae-rtac-server ruff check --fix src/
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Ruff found issues (some may be non-fixable)" -ForegroundColor Yellow
        }
        
        Write-Host "Formatting complete!" -ForegroundColor Green
    }
    "lint" {
        # Runs ruff in a throwaway container (no local Python needed on this machine).
        # ruff is the CI-blocking gate; keep it clean before pushing.
        Write-Host "Running ruff linter (via Docker)..." -ForegroundColor Green
        docker run --rm -v "${PWD}:/app" -w /app python:3.11-slim bash -c "pip install -q ruff && ruff check src/ tests/"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Ruff found issues. Run '.\make.ps1 lint-fix' to auto-fix what it can." -ForegroundColor Yellow
            exit $LASTEXITCODE
        }
        Write-Host "Lint clean!" -ForegroundColor Green
    }
    "lint-fix" {
        # Auto-fixes what ruff can (imports, typing, whitespace). B904 exception
        # chaining is not auto-fixable and must be fixed by hand.
        Write-Host "Auto-fixing lint issues with ruff (via Docker)..." -ForegroundColor Green
        docker run --rm -v "${PWD}:/app" -w /app python:3.11-slim bash -c "pip install -q ruff && ruff check --fix src/ tests/"
        Write-Host "Done. Re-run '.\make.ps1 lint' to see anything left (e.g. B904 needs manual fixes)." -ForegroundColor Green
    }
    "cloud-down" {
        # Stop all billable GCP compute (app + redis + ArgoCD -> 0, Cloud SQL stopped).
        # Data is preserved; idle cost ~= Cloud SQL storage only.
        $proj = "prd-pae-rtac-server"; $sql = "rtac-pg-prod"; $ns = "rtac-modbus-prod"
        Write-Host ">> Stopping ArgoCD (so it won't scale things back up)..." -ForegroundColor Yellow
        kubectl -n argocd scale statefulset --all --replicas=0
        kubectl -n argocd scale deploy --all --replicas=0
        Write-Host ">> Removing HPA (it would otherwise force min replicas)..." -ForegroundColor Yellow
        kubectl -n $ns delete hpa pae-rtac-server --ignore-not-found
        Write-Host ">> Scaling app + redis to 0..." -ForegroundColor Yellow
        kubectl -n $ns scale deploy pae-rtac-server redis --replicas=0
        Write-Host ">> Stopping Cloud SQL..." -ForegroundColor Yellow
        gcloud sql instances patch $sql --project=$proj --activation-policy=NEVER --quiet
        Write-Host ">> cloud-down complete. Billing minimized (data preserved)." -ForegroundColor Green
    }
    "cloud-up" {
        # Start Cloud SQL, bring ArgoCD back, scale workloads up, let ArgoCD reconcile.
        $proj = "prd-pae-rtac-server"; $sql = "rtac-pg-prod"; $ns = "rtac-modbus-prod"
        Write-Host ">> Starting Cloud SQL..." -ForegroundColor Green
        gcloud sql instances patch $sql --project=$proj --activation-policy=ALWAYS --quiet
        Write-Host ">> Waiting for Cloud SQL to be RUNNABLE..." -ForegroundColor Cyan
        do {
            Start-Sleep -Seconds 10
            $state = gcloud sql instances describe $sql --project=$proj --format="value(state)"
            Write-Host "   ...state=$state"
        } while ($state -ne "RUNNABLE")
        Write-Host ">> Bringing ArgoCD back..." -ForegroundColor Green
        kubectl -n argocd scale statefulset --all --replicas=1
        kubectl -n argocd scale deploy --all --replicas=1
        kubectl -n argocd rollout status statefulset/argocd-application-controller --timeout=180s
        kubectl -n argocd rollout status deploy/argocd-repo-server --timeout=120s
        Write-Host ">> Scaling redis + app back up..." -ForegroundColor Green
        kubectl -n $ns scale deploy redis --replicas=1
        kubectl -n $ns rollout status deploy/redis --timeout=120s
        kubectl -n $ns scale deploy pae-rtac-server --replicas=2
        kubectl -n $ns rollout status deploy/pae-rtac-server --timeout=240s
        Write-Host ">> Nudging ArgoCD to reconcile (recreates HPA, marks Synced)..." -ForegroundColor Green
        kubectl -n argocd annotate application pae-rtac-server-prod argocd.argoproj.io/refresh=hard --overwrite | Out-Null
        Write-Host ">> cloud-up complete. App is ready." -ForegroundColor Green
    }
    default {
        Show-Help
    }
}


