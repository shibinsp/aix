#!/bin/bash
#############################################
# AI CyberX - Production Deployment Script
#############################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$(dirname "$DOCKER_DIR")")"

COMPOSE_FILE="$DOCKER_DIR/docker-compose.prod.yml"
ENV_FILE="$PROJECT_ROOT/.env.production"

echo -e "${CYAN}"
echo "========================================"
echo "   AI CyberX - Production Deployment"
echo "========================================"
echo -e "${NC}"

#############################################
# Helper Functions
#############################################

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

wait_for_healthy() {
    local container=$1
    local max_attempts=${2:-30}
    local attempt=1

    echo -n "Waiting for $container"
    while [ $attempt -le $max_attempts ]; do
        if docker ps --filter "name=$container" --filter "health=healthy" | grep -q "$container"; then
            echo ""
            log_ok "$container is healthy"
            return 0
        fi
        echo -n "."
        sleep 2
        ((attempt++))
    done
    echo ""
    log_error "$container failed health check"
    return 1
}

#############################################
# Step 1: Check Prerequisites
#############################################
echo -e "${BLUE}Step 1: Checking prerequisites...${NC}"

# Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker not installed!"
    echo "Install: curl -fsSL https://get.docker.com | sh"
    exit 1
fi
log_ok "Docker installed"

# Docker Compose
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
    log_ok "Docker Compose v2 installed"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
    log_ok "Docker Compose v1 installed"
else
    log_error "Docker Compose not found!"
    exit 1
fi

# Docker daemon
if ! docker info > /dev/null 2>&1; then
    log_error "Docker daemon not running!"
    echo "Start: sudo systemctl start docker"
    exit 1
fi
log_ok "Docker daemon running"

#############################################
# Step 2: Environment Configuration
#############################################
echo ""
echo -e "${BLUE}Step 2: Checking environment...${NC}"

if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$PROJECT_ROOT/.env.production.example" ]; then
        log_warn ".env.production not found. Creating from template..."
        cp "$PROJECT_ROOT/.env.production.example" "$ENV_FILE"
        echo ""
        echo -e "${YELLOW}Please edit $ENV_FILE with your values:${NC}"
        echo "  - DOMAIN (your domain)"
        echo "  - SSL_EMAIL (for Let's Encrypt)"
        echo "  - SECRET_KEY (openssl rand -hex 32)"
        echo "  - POSTGRES_PASSWORD"
        echo "  - MISTRAL_API_KEY (or other AI key)"
        exit 1
    else
        log_error "No .env template found!"
        exit 1
    fi
fi

# Load environment
set -a
source "$ENV_FILE"
set +a

# Validate required vars
REQUIRED_VARS=("DOMAIN" "SSL_EMAIL" "SECRET_KEY" "POSTGRES_PASSWORD")
MISSING=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING+=("$var")
    fi
done

if [ ${#MISSING[@]} -ne 0 ]; then
    log_error "Missing required variables:"
    for var in "${MISSING[@]}"; do
        echo "  - $var"
    done
    exit 1
fi

# Check AI keys
if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$MISTRAL_API_KEY" ] && [ -z "$GEMINI_API_KEY" ]; then
    log_error "At least one AI API key required (MISTRAL_API_KEY recommended)"
    exit 1
fi

log_ok "Environment configuration valid"
log_info "Domain: $DOMAIN"

#############################################
# Step 3: SSL Certificates
#############################################
echo ""
echo -e "${BLUE}Step 3: SSL certificates...${NC}"

CERT_PATH="$DOCKER_DIR/certbot/conf/live/$DOMAIN"
if [ -f "$CERT_PATH/fullchain.pem" ] && [ -f "$CERT_PATH/privkey.pem" ]; then
    log_ok "SSL certificates exist"
else
    log_warn "SSL certificates not found. Initializing..."
    export DOMAIN SSL_EMAIL SSL_STAGING
    bash "$SCRIPT_DIR/init-ssl.sh"
fi

#############################################
# Step 4: Nginx Configuration
#############################################
echo ""
echo -e "${BLUE}Step 4: Nginx configuration...${NC}"

NGINX_TEMPLATE="$DOCKER_DIR/nginx/conf.d/default.conf.template"
NGINX_CONF="$DOCKER_DIR/nginx/conf.d/default.conf"

if [ -f "$NGINX_TEMPLATE" ]; then
    export DOMAIN
    envsubst '${DOMAIN}' < "$NGINX_TEMPLATE" > "$NGINX_CONF"
    log_ok "Nginx configuration generated"
else
    log_error "Nginx template not found!"
    exit 1
fi

#############################################
# Step 5: Build Images
#############################################
echo ""
echo -e "${BLUE}Step 5: Building Docker images...${NC}"

cd "$DOCKER_DIR"

log_info "Pulling base images..."
$COMPOSE_CMD -f "$COMPOSE_FILE" pull postgres redis nginx certbot 2>/dev/null || true

log_info "Building application images..."
$COMPOSE_CMD -f "$COMPOSE_FILE" build backend frontend

log_ok "Docker images built"

#############################################
# Step 6: Stop Existing Services
#############################################
echo ""
echo -e "${BLUE}Step 6: Stopping existing services...${NC}"

$COMPOSE_CMD -f "$COMPOSE_FILE" down --remove-orphans 2>/dev/null || true
log_ok "Existing services stopped"

#############################################
# Step 7: Start Database Services
#############################################
echo ""
echo -e "${BLUE}Step 7: Starting databases...${NC}"

$COMPOSE_CMD -f "$COMPOSE_FILE" up -d postgres redis

wait_for_healthy "cyberx-postgres" 60
wait_for_healthy "cyberx-redis" 30

#############################################
# Step 8: Database Migrations
#############################################
echo ""
echo -e "${BLUE}Step 8: Running migrations...${NC}"

$COMPOSE_CMD -f "$COMPOSE_FILE" up -d backend
sleep 15

log_info "Executing Alembic migrations..."
if docker exec cyberx-backend alembic upgrade head; then
    log_ok "Migrations completed"
else
    log_error "Migrations failed!"
    log_warn "Check logs: docker logs cyberx-backend"
    exit 1
fi

#############################################
# Step 9: Start All Services
#############################################
echo ""
echo -e "${BLUE}Step 9: Starting all services...${NC}"

$COMPOSE_CMD -f "$COMPOSE_FILE" up -d

wait_for_healthy "cyberx-backend" 60
wait_for_healthy "cyberx-frontend" 60

sleep 5
if docker ps | grep -q "cyberx-nginx.*Up"; then
    log_ok "Nginx running"
else
    log_error "Nginx failed!"
    docker logs cyberx-nginx
    exit 1
fi

#############################################
# Step 10: Verification
#############################################
echo ""
echo -e "${BLUE}Step 10: Verifying deployment...${NC}"

# Backend health
HEALTH=$(curl -sf http://localhost:8000/health 2>/dev/null || echo "FAILED")
if echo "$HEALTH" | grep -q "healthy"; then
    log_ok "Backend API healthy"
else
    log_warn "Backend health: $HEALTH"
fi

# HTTPS
HTTPS_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "https://$DOMAIN/health" 2>/dev/null || echo "000")
if [ "$HTTPS_STATUS" = "200" ]; then
    log_ok "HTTPS endpoint working"
else
    log_warn "HTTPS status: $HTTPS_STATUS (check DNS)"
fi

#############################################
# Summary
#############################################
echo ""
echo -e "${GREEN}"
echo "========================================"
echo "   Deployment Complete!"
echo "========================================"
echo -e "${NC}"
echo ""
echo -e "${CYAN}Access:${NC}"
echo "  Frontend:  https://$DOMAIN"
echo "  API Docs:  https://$DOMAIN/api/v1/docs"
echo "  Health:    https://$DOMAIN/health"
echo ""
echo -e "${CYAN}Commands:${NC}"
echo "  Logs:    $COMPOSE_CMD -f $COMPOSE_FILE logs -f"
echo "  Stop:    $COMPOSE_CMD -f $COMPOSE_FILE down"
echo "  Restart: $COMPOSE_CMD -f $COMPOSE_FILE restart"
echo ""
