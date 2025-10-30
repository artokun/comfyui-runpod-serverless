#!/bin/bash
# Build script for multi-architecture Docker images

set -e

# Configuration
DOCKER_USERNAME="alongbottom"
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

Build and optionally push ComfyUI RunPod Docker images for different GPU architectures.

Options:
    -a, --arch ARCH       GPU architecture: "ada" (RTX 4090) or "blackwell" (RTX 5090/6000 Pro)
                         Default: ada
    -p, --push           Push image to Docker Hub after building
    -t, --tag TAG        Additional tag for the image (default: GPU_ARCH name)
    -f, --file FILE      Dockerfile to use (default: Dockerfile)
    --no-cache           Build without using cache
    -h, --help           Show this help message

Examples:
    # Build for RTX 4090 (Ada)
    ./build.sh --arch ada

    # Build for RTX 6000 Pro (Blackwell) and push
    ./build.sh --arch blackwell --push

    # Build both and push
    ./build.sh --arch ada --push && ./build.sh --arch blackwell --push

    # Build with custom tag
    ./build.sh --arch ada --tag latest --push
EOF
}

# Default values
GPU_ARCH="ada"
PUSH=false
CUSTOM_TAG=""
DOCKERFILE="Dockerfile"
NO_CACHE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--arch)
            GPU_ARCH="$2"
            shift 2
            ;;
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

# Validate architecture
if [[ "$GPU_ARCH" != "ada" && "$GPU_ARCH" != "blackwell" ]]; then
    echo -e "${RED}Error: Invalid architecture '$GPU_ARCH'. Must be 'ada' or 'blackwell'.${NC}"
    exit 1
fi

# Set image tag
if [[ -n "$CUSTOM_TAG" ]]; then
    IMAGE_TAG="${DOCKER_USERNAME}/${IMAGE_NAME}:${CUSTOM_TAG}"
else
    IMAGE_TAG="${DOCKER_USERNAME}/${IMAGE_NAME}:${GPU_ARCH}"
fi

echo -e "${GREEN}==============================================================${NC}"
echo -e "${GREEN}Building ComfyUI RunPod Worker${NC}"
echo -e "${GREEN}==============================================================${NC}"
echo -e "Architecture: ${YELLOW}${GPU_ARCH}${NC}"
echo -e "Image tag:    ${YELLOW}${IMAGE_TAG}${NC}"
echo -e "Dockerfile:   ${YELLOW}${DOCKERFILE}${NC}"
echo -e "Push:         ${YELLOW}${PUSH}${NC}"
echo -e "${GREEN}==============================================================${NC}\n"

# Build the image (using production target for RunPod deployment)
echo -e "${GREEN}Building Docker image...${NC}"
docker build \
    --platform linux/amd64 \
    --target production \
    --build-arg GPU_ARCH=${GPU_ARCH} \
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

    # Show labels
    echo -e "${GREEN}Build configuration:${NC}"
    docker inspect ${IMAGE_TAG} --format='GPU Arch: {{index .Config.Labels "gpu_arch"}}'
    docker inspect ${IMAGE_TAG} --format='CUDA Version: {{index .Config.Labels "cuda_version"}}'
    docker inspect ${IMAGE_TAG} --format='PyTorch Version: {{index .Config.Labels "pytorch_version"}}'
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
        echo -e "3. Select ${YELLOW}${GPU_ARCH}${NC} compatible GPUs"
    else
        echo -e "1. Test locally: ${YELLOW}docker run --gpus all -p 8000:8000 ${IMAGE_TAG}${NC}"
        echo -e "2. Push to Docker Hub: ${YELLOW}./build.sh --arch ${GPU_ARCH} --push${NC}"
    fi

    echo -e "${GREEN}==============================================================${NC}\n"

else
    echo -e "\n${RED}✗ Build failed!${NC}"
    exit 1
fi
