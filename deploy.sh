#!/bin/bash
# Deployment script for ComfyUI + RunPod Handler
# Usage: ./deploy.sh [ada|blackwell]

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

GPU_ARCH=${1:-blackwell}
DOCKER_USERNAME=${DOCKER_USERNAME:-artokun}
IMAGE_NAME="$DOCKER_USERNAME/comfyui-runpod"
TAG="$GPU_ARCH"

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}  ComfyUI RunPod Deployment${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""
echo "Configuration:"
echo "  GPU Architecture: $GPU_ARCH"
echo "  Docker Image: $IMAGE_NAME:$TAG"
echo ""

# Check if logged into Docker Hub
echo -e "${YELLOW}Checking Docker Hub authentication...${NC}"
if ! docker info | grep -q "Username:"; then
    echo -e "${RED}Not logged into Docker Hub!${NC}"
    echo "Please run: docker login"
    exit 1
fi
echo -e "${GREEN}✓ Authenticated${NC}"
echo ""

# Build production image
echo -e "${YELLOW}Building production image...${NC}"
docker build \
    --target production \
    --build-arg GPU_ARCH=$GPU_ARCH \
    -t $IMAGE_NAME:$TAG \
    -t $IMAGE_NAME:$GPU_ARCH-latest \
    .

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Build failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Build successful${NC}"
echo ""

# Push to Docker Hub
echo -e "${YELLOW}Pushing to Docker Hub...${NC}"
docker push $IMAGE_NAME:$TAG
docker push $IMAGE_NAME:$GPU_ARCH-latest

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Push failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Push successful${NC}"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Image pushed to: $IMAGE_NAME:$TAG"
echo ""
echo "Next steps:"
echo "  1. Go to https://runpod.io/console/serverless"
echo "  2. Create a new template with image: $IMAGE_NAME:$TAG"
echo "  3. Follow RUNPOD_QUICKSTART.md for configuration"
echo ""
