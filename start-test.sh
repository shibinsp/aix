#!/bin/bash

echo "AI CyberX Platform - Test Startup"
echo "=================================="

# Check if we have the custom images
echo "Checking for existing images..."
BACKEND_IMAGE=$(docker images -q cyberx-backend 2>/dev/null || echo "")
FRONTEND_IMAGE=$(docker images -q cyberx-frontend 2>/dev/null || echo "")

if [ -z "$BACKEND_IMAGE" ] || [ -z "$FRONTEND_IMAGE" ]; then
    echo "Custom images not found. Building..."
    
    # Build backend with a simple timeout check
    echo "Building backend (this may take a while)..."
    (cd backend && docker build -t cyberx-backend -f ../infrastructure/docker/Dockerfile.backend .) &
    BACKEND_PID=$!
    
    # Wait up to 2 minutes for backend build
    for i in {1..24}; do
        if ! kill -0 $BACKEND_PID 2>/dev/null; then
            echo "Backend build completed!"
            break
        fi
        echo -n "."
        sleep 5
    done
    
    if kill -0 $BACKEND_PID 2>/dev/null; then
        echo "Backend build still running after timeout, continuing..."
    fi
    
    # Build frontend
    echo "Building frontend..."
    (cd frontend && docker build -t cyberx-frontend -f ../infrastructure/docker/Dockerfile.frontend .) &
    FRONTEND_PID=$!
    
    # Wait up to 2 minutes for frontend build
    for i in {1..24}; do
        if ! kill -0 $FRONTEND_PID 2>/dev/null; then
            echo "Frontend build completed!"
            break
        fi
        echo -n "."
        sleep 5
    done
    
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "Frontend build still running after timeout, continuing..."
    fi
else
    echo "Using existing images"
fi

# Start services
echo "Starting services..."
docker compose -f docker-compose-root.yml up -d

# Check status
echo "Waiting for services to start..."
sleep 10

echo "Service status:"
docker ps | grep cyberx || echo "Services still starting..."

echo ""
echo "Test startup complete!"
echo "You can check logs with: docker compose -f docker-compose-root.yml logs -f"
echo "Stop services with: docker compose -f docker-compose-root.yml down"