# dopaPal Run Script for PowerShell

Write-Host "🧠✨ Starting dopaPal Local Stack..." -ForegroundColor Cyan

# 1. Environment configuration setup
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

# 2. Check if Docker is running
docker info >$null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error: Docker is not running. Please start Docker Desktop and try again." -ForegroundColor Red
    Exit 1
}

# 3. Boot containers
Write-Host "Building and launching containers..." -ForegroundColor Green
docker-compose up --build -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n🚀 dopaPal is running!" -ForegroundColor Green
    Write-Host "Backend API docs: http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host "To stop the stack, run: docker-compose down`n" -ForegroundColor Yellow
    Write-Host "--- Streaming Live Backend Logs [Press Ctrl+C to stop log stream] ---" -ForegroundColor Cyan
    docker-compose logs -f backend
} else {
    Write-Host "❌ Failed to start containers." -ForegroundColor Red
}
