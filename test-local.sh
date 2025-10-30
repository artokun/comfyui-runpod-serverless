#!/bin/bash
# Local testing script for ComfyUI + RunPod Handler
# Tests the full stack locally before deploying to RunPod

set -e

echo "========================================"
echo "  ComfyUI Local Test Suite"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
GPU_ARCH=${GPU_ARCH:-blackwell}  # Use blackwell for 5090
TEST_TIMEOUT=300  # 5 minutes

echo "Configuration:"
echo "  GPU Architecture: $GPU_ARCH"
echo "  Test Timeout: ${TEST_TIMEOUT}s"
echo ""

# Step 1: Build the image
echo -e "${YELLOW}Step 1: Building Docker image...${NC}"
docker compose build --build-arg GPU_ARCH=$GPU_ARCH

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Build failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Build successful${NC}"
echo ""

# Step 2: Start services
echo -e "${YELLOW}Step 2: Starting services...${NC}"
docker compose up -d

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Failed to start services!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Services started${NC}"
echo ""

# Step 3: Wait for ComfyUI to be ready
echo -e "${YELLOW}Step 3: Waiting for ComfyUI to be ready...${NC}"
RETRY_COUNT=0
MAX_RETRIES=60  # 5 minutes with 5s intervals

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8188/system_stats > /dev/null 2>&1; then
        echo -e "${GREEN}✓ ComfyUI is ready!${NC}"
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "  Waiting... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 5
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}✗ ComfyUI failed to start${NC}"
    echo "Showing logs:"
    docker compose logs comfyui
    docker compose down
    exit 1
fi
echo ""

# Step 4: Check handler is ready
echo -e "${YELLOW}Step 4: Checking handler endpoint...${NC}"
sleep 5  # Give handler a moment to start

if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Handler is responding${NC}"
else
    echo -e "${YELLOW}⚠ Handler might not be ready (this can be normal)${NC}"
fi
echo ""

# Step 5: Show service info
echo -e "${YELLOW}Step 5: Service Status${NC}"
docker compose ps
echo ""

# Step 6: Show installed nodes and models
echo -e "${YELLOW}Step 6: Checking installations...${NC}"
docker compose exec comfyui ls -la /comfyui/custom_nodes/ 2>/dev/null | head -20 || echo "  Custom nodes directory not yet created"
echo ""

# Success message
echo "========================================"
echo -e "${GREEN}  Local Test Complete!${NC}"
echo "========================================"
echo ""
echo "Services running:"
echo "  • ComfyUI UI:     http://localhost:8188"
echo "  • RunPod API:     http://localhost:8000"
echo ""
echo "Next steps:"
echo "  1. Open http://localhost:8188 to use ComfyUI"
echo "  2. Test the API with: curl http://localhost:8000/"
echo "  3. View logs with: docker compose logs -f"
echo "  4. Stop with: docker compose down"
echo ""
echo "When ready to deploy:"
echo "  ./deploy.sh $GPU_ARCH"
echo ""
