#!/bin/bash
#############################################
# AI CyberX - SSL Certificate Initialization
# Creates initial certs and obtains Let's Encrypt
#############################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
DOMAIN="${DOMAIN:?DOMAIN environment variable is required}"
EMAIL="${SSL_EMAIL:?SSL_EMAIL environment variable is required}"
STAGING="${SSL_STAGING:-0}"

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$(dirname "$SCRIPT_DIR")"
NGINX_DIR="$DOCKER_DIR/nginx"
CERTBOT_DIR="$DOCKER_DIR/certbot"

echo -e "${BLUE}"
echo "======================================"
echo "   AI CyberX - SSL Initialization"
echo "======================================"
echo -e "${NC}"

echo -e "${BLUE}Domain: ${GREEN}$DOMAIN${NC}"
echo -e "${BLUE}Email:  ${GREEN}$EMAIL${NC}"

# Create directories
echo -e "${BLUE}Creating directories...${NC}"
mkdir -p "$NGINX_DIR/conf.d"
mkdir -p "$CERTBOT_DIR/www"
mkdir -p "$CERTBOT_DIR/conf"

# Check if certificates already exist
if [ -d "$CERTBOT_DIR/conf/live/$DOMAIN" ] && [ -f "$CERTBOT_DIR/conf/live/$DOMAIN/fullchain.pem" ]; then
    echo -e "${YELLOW}Certificates already exist for $DOMAIN${NC}"
    read -p "Do you want to regenerate? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}Keeping existing certificates.${NC}"
        exit 0
    fi
fi

# Download recommended TLS parameters
echo -e "${BLUE}Downloading TLS parameters...${NC}"
if [ ! -e "$CERTBOT_DIR/conf/options-ssl-nginx.conf" ]; then
    curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "$CERTBOT_DIR/conf/options-ssl-nginx.conf"
fi
if [ ! -e "$CERTBOT_DIR/conf/ssl-dhparams.pem" ]; then
    curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "$CERTBOT_DIR/conf/ssl-dhparams.pem"
fi
echo -e "${GREEN}TLS parameters ready.${NC}"

# Create dummy certificate for nginx to start
echo -e "${BLUE}Creating dummy certificate...${NC}"
CERT_PATH="$CERTBOT_DIR/conf/live/$DOMAIN"
mkdir -p "$CERT_PATH"

openssl req -x509 -nodes -newkey rsa:4096 -days 1 \
    -keyout "$CERT_PATH/privkey.pem" \
    -out "$CERT_PATH/fullchain.pem" \
    -subj "/CN=localhost" 2>/dev/null

echo -e "${GREEN}Dummy certificate created.${NC}"

# Generate nginx config from template
echo -e "${BLUE}Generating nginx configuration...${NC}"
export DOMAIN
envsubst '${DOMAIN}' < "$NGINX_DIR/conf.d/default.conf.template" > "$NGINX_DIR/conf.d/default.conf"
echo -e "${GREEN}Nginx configuration generated.${NC}"

# Start nginx with dummy certificate
echo -e "${BLUE}Starting nginx...${NC}"
cd "$DOCKER_DIR"
docker-compose -f docker-compose.prod.yml up -d nginx

# Wait for nginx
echo -e "${BLUE}Waiting for nginx to start...${NC}"
sleep 5

if ! docker ps | grep -q "cyberx-nginx"; then
    echo -e "${RED}Error: nginx failed to start!${NC}"
    docker logs cyberx-nginx 2>&1 | tail -20
    exit 1
fi
echo -e "${GREEN}Nginx started.${NC}"

# Delete dummy certificate
echo -e "${BLUE}Removing dummy certificate...${NC}"
rm -rf "$CERT_PATH"

# Request Let's Encrypt certificate
echo -e "${BLUE}Requesting Let's Encrypt certificate...${NC}"

STAGING_FLAG=""
if [ "$STAGING" = "1" ]; then
    STAGING_FLAG="--staging"
    echo -e "${YELLOW}Using Let's Encrypt staging environment${NC}"
fi

docker-compose -f docker-compose.prod.yml run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    $STAGING_FLAG \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN" \
    -d "www.$DOMAIN"

# Check if certificate was obtained
if [ ! -f "$CERTBOT_DIR/conf/live/$DOMAIN/fullchain.pem" ]; then
    echo -e "${RED}Error: Failed to obtain certificate!${NC}"
    exit 1
fi

echo -e "${GREEN}Certificate obtained!${NC}"

# Reload nginx
echo -e "${BLUE}Reloading nginx...${NC}"
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload

echo -e "${GREEN}"
echo "======================================"
echo "   SSL Certificate Ready!"
echo "======================================"
echo -e "${NC}"
echo ""
echo "Certificate location: $CERTBOT_DIR/conf/live/$DOMAIN/"
echo ""
echo "Auto-renewal is configured via certbot container."
echo ""
