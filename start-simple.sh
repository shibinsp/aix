#!/bin/bash

set -e

echo "Starting AI CyberX Platform - Simple Mode"
echo "=========================================="

# Clean up any existing containers
docker compose -f docker-compose-root.yml down 2>/dev/null || true

# Start only the database services first
echo "Starting database services..."
docker compose -f docker-compose-root.yml up -d postgres redis

# Wait for databases to be ready
echo "Waiting for databases to be ready..."
sleep 15

# Check if databases are healthy
echo "Checking database health..."
docker ps | grep cyberx

# Start the backend and frontend
echo "Starting application services..."
docker compose -f docker-compose-root.yml up -d backend frontend

# Wait for services to start
echo "Waiting for services to start..."
sleep 10

# Check service status
echo "Service status:"
docker ps | grep cyberx

echo ""
echo "AI CyberX Platform started!"
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"