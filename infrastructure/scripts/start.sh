#!/bin/bash

# AI CyberX Platform Startup Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════╗"
echo "║           AI CyberX Platform Startup                 ║"
echo "║     AI-Powered Cybersecurity Learning Platform       ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}Warning: Running as root. Consider using a non-root user.${NC}"
fi

# Check for Podman
if ! command -v podman &> /dev/null; then
    echo -e "${RED}Error: Podman is not installed.${NC}"
    echo "Please install Podman first: https://podman.io/getting-started/installation"
    exit 1
fi

# Check for podman-compose
if ! command -v podman-compose &> /dev/null; then
    echo -e "${YELLOW}podman-compose not found. Installing...${NC}"
    pip3 install podman-compose
fi

# Navigate to infrastructure directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR/../podman"

# Check for .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}Please edit .env file with your API keys before continuing.${NC}"
        echo "Required: OPENAI_API_KEY or ANTHROPIC_API_KEY"
        read -p "Press Enter after editing .env or Ctrl+C to cancel..."
    else
        echo -e "${RED}Error: .env.example not found${NC}"
        exit 1
    fi
fi

# Source environment variables
source .env

# Start Podman socket for rootless (if needed)
echo -e "${GREEN}Ensuring Podman socket is running...${NC}"
systemctl --user start podman.socket 2>/dev/null || true

# Pull images
echo -e "${GREEN}Pulling required images...${NC}"
podman-compose pull

# Build custom images
echo -e "${GREEN}Building application images...${NC}"
podman-compose build

# Start services
echo -e "${GREEN}Starting services...${NC}"
podman-compose up -d

# Wait for services to be ready
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 10

# Check health
echo -e "${GREEN}Checking service health...${NC}"

# Check PostgreSQL
if podman exec cyberx-postgres pg_isready -U cyberx -d cyberx > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} PostgreSQL is ready"
else
    echo -e "  ${RED}✗${NC} PostgreSQL is not ready"
fi

# Check Redis
if podman exec cyberx-redis redis-cli ping > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} Redis is ready"
else
    echo -e "  ${RED}✗${NC} Redis is not ready"
fi

# Check Backend
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} Backend API is ready"
else
    echo -e "  ${RED}✗${NC} Backend API is not ready"
fi

# Check Frontend
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} Frontend is ready"
else
    echo -e "  ${RED}✗${NC} Frontend is not ready"
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗"
echo "║              AI CyberX is now running!                ║"
echo "╠═══════════════════════════════════════════════════════╣"
echo "║  Frontend:    http://localhost:3000                   ║"
echo "║  Backend API: http://localhost:8000                   ║"
echo "║  API Docs:    http://localhost:8000/docs              ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo ""
echo "Commands:"
echo "  View logs:     podman-compose logs -f"
echo "  Stop:          podman-compose down"
echo "  Restart:       podman-compose restart"
