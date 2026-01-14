#!/bin/bash

#############################################
# AI CyberX - Root Directory Startup Script
#############################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "======================================"
echo "   AI CyberX - Starting Platform"
echo "======================================"
echo -e "${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker daemon is not running!${NC}"
    echo "Please start Docker Desktop or run: sudo systemctl start docker"
    exit 1
fi

echo -e "${GREEN}✓ Docker daemon is running${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}No .env file found. Creating from template...${NC}"
    
    if [ -f infrastructure/docker/.env.example ]; then
        cp infrastructure/docker/.env.example .env
        echo -e "${GREEN}✓ Created .env file${NC}"
        echo -e "${YELLOW}Please edit .env file and add your configuration:${NC}"
        echo "  - SECRET_KEY (required)"
        echo "  - POSTGRES_PASSWORD (required)"
        echo "  - At least one AI API key (OPENAI_API_KEY, ANTHROPIC_API_KEY, MISTRAL_API_KEY, or GEMINI_API_KEY)"
        echo ""
        echo "Generate SECRET_KEY with: openssl rand -hex 32"
        echo ""
        read -p "Press Enter to continue after editing .env file..."
    else
        echo -e "${RED}Error: .env.example not found!${NC}"
        exit 1
    fi
fi

# Validate required environment variables
echo -e "${BLUE}Validating environment configuration...${NC}"

source .env

if [ -z "$SECRET_KEY" ]; then
    echo -e "${RED}Error: SECRET_KEY is not set in .env${NC}"
    exit 1
fi

if [ -z "$POSTGRES_PASSWORD" ]; then
    echo -e "${RED}Error: POSTGRES_PASSWORD is not set in .env${NC}"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$MISTRAL_API_KEY" ] && [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${YELLOW}Warning: No AI API keys configured. Some features will not work.${NC}"
fi

echo -e "${GREEN}✓ Environment configuration valid${NC}"

# Stop existing containers
echo -e "${BLUE}Stopping existing containers...${NC}"
docker compose -f docker-compose-root.yml down 2>/dev/null || true

# Remove any existing custom images to force rebuild
echo -e "${BLUE}Cleaning up old images...${NC}"
docker rmi cyberx-backend 2>/dev/null || true
docker rmi cyberx-frontend 2>/dev/null || true

# Pull base images only
echo -e "${BLUE}Pulling base Docker images...${NC}"
docker pull postgres:15-alpine
docker pull redis:7-alpine

# Build containers
echo -e "${BLUE}Building application containers...${NC}"

# Build backend from backend directory
cd backend
echo -e "${BLUE}Building backend...${NC}"
docker build -t cyberx-backend -f ../infrastructure/docker/Dockerfile.backend .
cd ..

# Build frontend from frontend directory
cd frontend
echo -e "${BLUE}Building frontend...${NC}"
docker build -t cyberx-frontend -f ../infrastructure/docker/Dockerfile.frontend .
cd ..

echo -e "${GREEN}✓ Containers built successfully${NC}"

# Start services
echo -e "${BLUE}Starting services...${NC}"
docker compose -f docker-compose-root.yml up -d

# Wait for services to be healthy
echo -e "${BLUE}Waiting for services to be healthy...${NC}"
sleep 10

# Check service health
echo -e "${BLUE}Checking service health...${NC}"

check_service() {
    local service=$1
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker ps | grep -q "$service.*healthy\|Up"; then
            echo -e "${GREEN}✓ $service is healthy${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    echo -e "${RED}✗ $service failed to start${NC}"
    return 1
}

check_service "cyberx-postgres"
check_service "cyberx-redis"
check_service "cyberx-backend"
check_service "cyberx-frontend"

# Test backend health endpoint
echo -e "${BLUE}Testing backend API...${NC}"
if curl -sf http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✓ Backend API is responding${NC}"
else
    echo -e "${YELLOW}⚠ Backend API is not responding yet (may need more time)${NC}"
fi

# Test frontend
echo -e "${BLUE}Testing frontend...${NC}"
if curl -sf http://localhost:3000 > /dev/null; then
    echo -e "${GREEN}✓ Frontend is responding${NC}"
else
    echo -e "${YELLOW}⚠ Frontend is not responding yet (may need more time)${NC}"
fi

echo ""
echo -e "${GREEN}======================================"
echo "   AI CyberX Started Successfully!"
echo "======================================${NC}"
echo ""
echo -e "${BLUE}Access the application:${NC}"
echo "  • Frontend:  http://localhost:3000"
echo "  • Backend:   http://localhost:8000"
echo "  • API Docs:  http://localhost:8000/docs"
echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo "  • View logs:        docker compose -f docker-compose-root.yml logs -f"
echo "  • Stop services:    docker compose -f docker-compose-root.yml down"
echo "  • Restart:          docker compose -f docker-compose-root.yml restart"
echo "  • View status:      docker compose -f docker-compose-root.yml ps"
echo ""
echo -e "${GREEN}Happy learning! 🚀${NC}"