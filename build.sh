#!/bin/bash
# Build script for unified ComfyUI RunPod Docker image
# Supports all modern NVIDIA GPUs (RTX 4090, RTX 5090, and beyond)

set -e

# Configuration
DOCKER_USERNAME="artokun"
IMAGE_NAME="comfyui-runpod"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Help message
show_help() {
    cat << EOF
Usage: ./build.sh [OPTIONS]

Build and optionally push the unified ComfyUI RunPod Docker image.
Works with all modern NVIDIA GPUs (RTX 4090, RTX 5090, and beyond).

Options:
    -p, --push           Push image to Docker Hub after building
    -t, --tag TAG        Tag for the image (default: latest)
    -f, --file FILE      Dockerfile to use (default: Dockerfile)
    --no-cache           Build without using cache
    -h, --help           Show this help message

Examples:
    # Build image
    ./build.sh

    # Build and push
    ./build.sh --push

    # Build with custom tag
    ./build.sh --tag v1.0.0 --push
EOF
}

# Default values
PUSH=false
CUSTOM_TAG="latest"
DOCKERFILE="Dockerfile"
NO_CACHE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--push)
            PUSH=true
            shift
            ;;
        -t|--tag)
            CUSTOM_TAG="$2"
            shift 2
            ;;
        -f|--file)
            DOCKERFILE="$2"
            shift 2
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Set image tag
IMAGE_TAG="${DOCKER_USERNAME}/${IMAGE_NAME}:${CUSTOM_TAG}"

echo -e "${GREEN}==============================================================${NC}"
echo -e "${GREEN}Building ComfyUI RunPod Worker (Unified Image)${NC}"
echo -e "${GREEN}==============================================================${NC}"
echo -e "Image tag:    ${YELLOW}${IMAGE_TAG}${NC}"
echo -e "Dockerfile:   ${YELLOW}${DOCKERFILE}${NC}"
echo -e "Push:         ${YELLOW}${PUSH}${NC}"
echo -e "GPU Support:  ${YELLOW}All modern NVIDIA GPUs (RTX 4090+, RTX 5090+)${NC}"
echo -e "${GREEN}==============================================================${NC}\n"

# Build the image (using production target for RunPod deployment)
echo -e "${GREEN}Building Docker image...${NC}"
docker build \
    --platform linux/amd64 \
    --target production \
    ${NO_CACHE} \
    -f ${DOCKERFILE} \
    -t ${IMAGE_TAG} \
    .

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ Build successful!${NC}"
    echo -e "Image: ${YELLOW}${IMAGE_TAG}${NC}\n"

    # Show image info
    echo -e "${GREEN}Image details:${NC}"
    docker images ${IMAGE_TAG} --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    echo ""

    # Push if requested
    if [ "$PUSH" = true ]; then
        echo -e "${GREEN}Pushing image to Docker Hub...${NC}"
        docker push ${IMAGE_TAG}

        if [ $? -eq 0 ]; then
            echo -e "\n${GREEN}✓ Push successful!${NC}"
            echo -e "Image available at: ${YELLOW}${IMAGE_TAG}${NC}\n"
        else
            echo -e "\n${RED}✗ Push failed!${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}Skipping push. Use --push to push to Docker Hub.${NC}\n"
    fi

    # Show usage instructions
    echo -e "${GREEN}==============================================================${NC}"
    echo -e "${GREEN}Next steps:${NC}"
    echo -e "${GREEN}==============================================================${NC}"

    if [ "$PUSH" = true ]; then
        echo -e "1. Go to RunPod console"
        echo -e "2. Create/update endpoint with image: ${YELLOW}${IMAGE_TAG}${NC}"
        echo -e "3. Compatible with all modern NVIDIA GPUs"
    else
        echo -e "1. Test locally: ${YELLOW}docker run --gpus all -p 8000:8000 ${IMAGE_TAG}${NC}"
        echo -e "2. Push to Docker Hub: ${YELLOW}./build.sh --push${NC}"
    fi

    echo -e "${GREEN}==============================================================${NC}\n"

else
    echo -e "\n${RED}✗ Build failed!${NC}"
    exit 1
fi
