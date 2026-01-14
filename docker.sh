#!/bin/bash

#############################################
# AI CyberX - Docker Management Script
# Manages existing Docker containers
#############################################

DOCKER_DIR="/root/AI_CyberX/infrastructure/docker"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to run docker-compose from the correct directory
compose_cmd() {
    cd "$DOCKER_DIR" && docker compose "$@"
}

case "$1" in
    start)
        echo -e "${BLUE}Starting AI CyberX containers...${NC}"
        compose_cmd up -d
        echo -e "${GREEN}✓ Containers started${NC}"
        ;;
    
    stop)
        echo -e "${YELLOW}Stopping AI CyberX containers...${NC}"
        compose_cmd down
        echo -e "${GREEN}✓ Containers stopped${NC}"
        ;;
    
    restart)
        echo -e "${BLUE}Restarting AI CyberX containers...${NC}"
        compose_cmd restart
        echo -e "${GREEN}✓ Containers restarted${NC}"
        ;;
    
    status|ps)
        echo -e "${BLUE}AI CyberX Container Status:${NC}"
        compose_cmd ps
        ;;
    
    logs)
        if [ -z "$2" ]; then
            echo -e "${BLUE}Showing logs for all services (Ctrl+C to exit):${NC}"
            compose_cmd logs -f
        else
            echo -e "${BLUE}Showing logs for $2 (Ctrl+C to exit):${NC}"
            compose_cmd logs -f "$2"
        fi
        ;;
    
    health)
        echo -e "${BLUE}Checking application health...${NC}"
        echo ""
        echo -e "${GREEN}Backend Health:${NC}"
        curl -s http://localhost:8000/health | python3 -m json.tool || echo "Backend not responding"
        echo ""
        echo -e "${GREEN}Frontend Status:${NC}"
        curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:3000 || echo "Frontend not responding"
        ;;
    
    exec)
        if [ -z "$2" ]; then
            echo -e "${RED}Error: Service name required${NC}"
            echo "Usage: ./docker.sh exec <service> [command]"
            echo "Example: ./docker.sh exec backend bash"
            exit 1
        fi
        SERVICE="$2"
        shift 2
        COMMAND="${@:-bash}"
        echo -e "${BLUE}Executing in $SERVICE: $COMMAND${NC}"
        compose_cmd exec "$SERVICE" $COMMAND
        ;;
    
    build)
        echo -e "${BLUE}Building AI CyberX containers...${NC}"
        compose_cmd build
        echo -e "${GREEN}✓ Build complete${NC}"
        ;;
    
    rebuild)
        echo -e "${BLUE}Rebuilding and restarting AI CyberX...${NC}"
        compose_cmd down
        compose_cmd build
        compose_cmd up -d
        echo -e "${GREEN}✓ Rebuild complete${NC}"
        ;;
    
    clean)
        echo -e "${YELLOW}Stopping and removing containers...${NC}"
        compose_cmd down -v
        echo -e "${GREEN}✓ Cleanup complete${NC}"
        ;;
    
    update)
        echo -e "${BLUE}Updating AI CyberX...${NC}"
        git pull
        compose_cmd down
        compose_cmd build
        compose_cmd up -d
        echo -e "${GREEN}✓ Update complete${NC}"
        ;;
    
    *)
        echo -e "${BLUE}AI CyberX Docker Management${NC}"
        echo ""
        echo "Usage: ./docker.sh <command> [options]"
        echo ""
        echo "Commands:"
        echo "  start          Start all containers"
        echo "  stop           Stop all containers"
        echo "  restart        Restart all containers"
        echo "  status|ps      Show container status"
        echo "  logs [service] Show logs (optional: specific service)"
        echo "  health         Check application health"
        echo "  exec <service> Execute command in container"
        echo "  build          Build container images"
        echo "  rebuild        Rebuild and restart all containers"
        echo "  clean          Stop and remove all containers and volumes"
        echo "  update         Pull latest code and rebuild"
        echo ""
        echo "Services: backend, frontend, postgres, redis"
        echo ""
        echo "Examples:"
        echo "  ./docker.sh start"
        echo "  ./docker.sh logs backend"
        echo "  ./docker.sh exec backend bash"
        echo "  ./docker.sh health"
        ;;
esac
