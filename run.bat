@echo off
setlocal enabledelayedexpansion

echo Starting dopaPal local stack...

if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
)

docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Docker is not running. Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo Purging old container structures and volume caches...
docker compose down --volumes --remove-orphans >nul 2>&1

echo Building backend from server folder...
docker compose build --no-cache backend

echo Booting service dependencies...
docker compose up -d

if %errorlevel% equ 0 (
    echo.
    echo dopaPal is running.
    echo Backend API docs: http://localhost:8000/docs
    echo To stop the stack, run: docker compose down
    echo.
    echo --- Streaming live backend logs [Press Ctrl+C to stop log stream] ---
    docker compose logs -f backend
) else (
    echo Failed to start containers.
    pause
)
