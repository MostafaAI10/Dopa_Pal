#!/usr/bin/env bash
echo "🧠✨ Starting dopaPal Local Stack..."

# 1. Copy .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

# 2. Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker daemon is not running. Please launch Docker and try again."
    exit 1
fi

# 3. Hard Reset: Drop structures
echo "🧹 Purging old container structures and volume caches..."
docker compose down --volumes --remove-orphans > /dev/null 2>&1

# 4. Build and Launch
echo "🔨 Executing cold build from root definitions..."
docker compose build --no-cache backend
echo "🚀 Booting up service dependencies..."
docker compose up -d

if [ $? -eq 0 ]; then
    echo -e "\n🚀 dopaPal is running!"
    echo "Backend API docs: http://localhost:8000/docs"
    echo "To stop the stack, run: docker compose down"
    echo -e "\n--- Streaming Live Backend Logs [Press Ctrl+C to stop log stream] ---\n"
    docker compose logs -f backend
else
    echo "❌ Failed to start containers."
    exit 1
fi