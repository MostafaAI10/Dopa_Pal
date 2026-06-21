#!/usr/bin/env bash
set -e

echo "Starting dopaPal local stack..."

if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker daemon is not running. Please launch Docker and try again."
    exit 1
fi

echo "Purging old container structures and volume caches..."
docker compose down --volumes --remove-orphans > /dev/null 2>&1

echo "Building backend from server folder..."
docker compose build --no-cache backend

echo "Booting service dependencies..."
docker compose up -d

echo
echo "dopaPal is running."
echo "Backend API docs: http://localhost:8000/docs"
echo "To stop the stack, run: docker compose down"
echo
echo "--- Streaming live backend logs [Press Ctrl+C to stop log stream] ---"
docker compose logs -f backend
