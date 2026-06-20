@echo off
setlocal enabledelayedexpansion
echo 🧠✨ Starting dopaPal Local Stack...

:: 1. Copy .env if it doesn't exist
if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
)

:: 2. Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Error: Docker is not running. Please start Docker Desktop and try again.
    pause
    exit /b 1
)

:: 3. Hard Reset: Drop containers, networks, and anonymous volume configurations
echo 🧹 Purging old container structures and volume caches...
docker compose down --volumes --remove-orphans >nul 2>&1

:: 4. Build and Launch: Force clear cache and pull fresh base layers
echo 🔨 Executing cold build from root definitions...
docker compose build --no-cache backend
echo 🚀 Booting up service dependencies...
docker compose up -d

if %errorlevel% equ 0 (
    echo.
    echo 🚀 dopaPal is running!
    echo Backend API docs: http://localhost:8000/docs
    echo To stop the stack, run: docker compose down
    echo.
    echo --- Streaming Live Backend Logs [Press Ctrl+C to stop log stream] ---
    docker compose logs -f backend
) else (
    echo ❌ Failed to start containers.
    pause
)