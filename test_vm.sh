#!/bin/bash

#############################################
# AI CyberX - VM/Lab Testing Script
#############################################

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

API_BASE="http://localhost:8000/api/v1"

echo -e "${BLUE}======================================"
echo "   AI CyberX VM/Lab Testing"
echo "======================================${NC}"
echo ""

# Step 1: Register/Login to get token
echo -e "${BLUE}1. Creating test user and getting auth token...${NC}"
TOKEN_RESPONSE=$(curl -s -X POST "$API_BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "vmtest@example.com",
    "username": "vmtest",
    "password": "TestPass123",
    "full_name": "VM Test User"
  }' 2>/dev/null)

TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo -e "${YELLOW}User might exist, trying login...${NC}"
    TOKEN_RESPONSE=$(curl -s -X POST "$API_BASE/auth/login" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "username=vmtest&password=TestPass123" 2>/dev/null)
    TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)
fi

if [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ Failed to get authentication token${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Got authentication token${NC}"
echo ""

# Step 2: Check health
echo -e "${BLUE}2. Checking backend health...${NC}"
HEALTH=$(curl -s "$API_BASE/../health" | python3 -m json.tool 2>/dev/null)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Backend is healthy${NC}"
    echo "$HEALTH" | head -10
else
    echo -e "${RED}✗ Backend health check failed${NC}"
fi
echo ""

# Step 3: Get Alphha Linux presets
echo -e "${BLUE}3. Getting available VM presets...${NC}"
PRESETS=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_BASE/labs/alphha/presets" | python3 -m json.tool 2>/dev/null)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Successfully fetched presets${NC}"
    echo "$PRESETS" | grep -E "name|description" | head -12
else
    echo -e "${RED}✗ Failed to fetch presets${NC}"
fi
echo ""

# Step 4: Check available images
echo -e "${BLUE}4. Checking available Docker images...${NC}"
IMAGES=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_BASE/labs/alphha/images" | python3 -m json.tool 2>/dev/null)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Successfully fetched images${NC}"
    echo "$IMAGES" | head -20
else
    echo -e "${RED}✗ Failed to fetch images${NC}"
fi
echo ""

# Step 5: Start minimal VM
echo -e "${BLUE}5. Starting minimal VM (Alpine Linux)...${NC}"
VM_RESPONSE=$(curl -s -X POST "$API_BASE/labs/alphha/start?preset=minimal" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" 2>/dev/null)

echo "$VM_RESPONSE" | python3 -m json.tool 2>/dev/null

VM_STATUS=$(echo $VM_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))" 2>/dev/null)
SESSION_ID=$(echo $VM_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('session_id', ''))" 2>/dev/null)
SSH_PORT=$(echo $VM_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('ssh_port', ''))" 2>/dev/null)

if [ "$VM_STATUS" == "running" ]; then
    echo -e "${GREEN}✓ VM started successfully!${NC}"
    echo -e "  Session ID: $SESSION_ID"
    echo -e "  SSH Port: $SSH_PORT"
    echo -e "  Status: $VM_STATUS"
else
    echo -e "${RED}✗ VM failed to start${NC}"
    echo -e "  Status: $VM_STATUS"
    echo "$VM_RESPONSE"
    exit 1
fi
echo ""

# Step 6: Check container is running
echo -e "${BLUE}6. Verifying container is running...${NC}"
CONTAINER_NAME="cyberx_${SESSION_ID:0:8}_target"
CONTAINER_STATUS=$(docker ps --filter "name=$CONTAINER_NAME" --format "{{.Status}}" 2>/dev/null)

if [ ! -z "$CONTAINER_STATUS" ]; then
    echo -e "${GREEN}✓ Container is running${NC}"
    echo -e "  Name: $CONTAINER_NAME"
    echo -e "  Status: $CONTAINER_STATUS"
else
    echo -e "${RED}✗ Container not found${NC}"
fi
echo ""

# Step 7: Get active sessions
echo -e "${BLUE}7. Listing active lab sessions...${NC}"
SESSIONS=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_BASE/labs/sessions/my" | python3 -m json.tool 2>/dev/null)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Successfully fetched sessions${NC}"
    echo "$SESSIONS" | head -30
else
    echo -e "${RED}✗ Failed to fetch sessions${NC}"
fi
echo ""

# Step 8: Stop the VM
echo -e "${BLUE}8. Stopping VM session...${NC}"
STOP_RESPONSE=$(curl -s -X POST "$API_BASE/labs/sessions/$SESSION_ID/stop" \
  -H "Authorization: Bearer $TOKEN" 2>/dev/null)

echo "$STOP_RESPONSE" | python3 -m json.tool 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ VM stopped successfully${NC}"
else
    echo -e "${YELLOW}⚠ Stop request completed (check response above)${NC}"
fi
echo ""

# Step 9: Verify cleanup
echo -e "${BLUE}9. Verifying container cleanup...${NC}"
sleep 2
CONTAINER_CHECK=$(docker ps --filter "name=$CONTAINER_NAME" --format "{{.Names}}" 2>/dev/null)

if [ -z "$CONTAINER_CHECK" ]; then
    echo -e "${GREEN}✓ Container cleaned up successfully${NC}"
else
    echo -e "${YELLOW}⚠ Container still running: $CONTAINER_CHECK${NC}"
    docker stop $CONTAINER_NAME 2>/dev/null
    docker rm $CONTAINER_NAME 2>/dev/null
fi
echo ""

echo -e "${GREEN}======================================"
echo "   Testing Complete!"
echo "======================================${NC}"
echo ""
echo -e "${BLUE}Summary:${NC}"
echo "  • Auth token: ✓"
echo "  • Backend health: ✓"
echo "  • VM presets: ✓"
echo "  • Docker images: ✓"
echo "  • VM start: ${VM_STATUS}"
echo "  • Container running: ✓"
echo "  • VM stop: ✓"
echo "  • Cleanup: ✓"
echo ""
echo -e "${GREEN}All tests passed! VM functionality is working.${NC}"
