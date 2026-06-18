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

:: 3. Clean environment slate (Prevents cached volume/path bleeding)
echo Clean-purging old volume cache entries...
docker compose down --volumes >nul 2>&1

:: 4. Boot and force an isolated rebuild of the backend service
echo Building and launching containers...
docker compose up --build -d

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