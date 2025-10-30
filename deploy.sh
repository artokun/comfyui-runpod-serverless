#!/bin/bash
# Quick deploy script - builds and pushes to Docker Hub

set -e

ARCH=${1:-ada}

echo "=========================================="
echo "  Deploying ComfyUI RunPod: $ARCH"
echo "=========================================="
echo ""

# Check if valid architecture
if [[ "$ARCH" != "ada" && "$ARCH" != "blackwell" ]]; then
    echo "Error: Invalid architecture '$ARCH'"
    echo "Usage: ./deploy.sh [ada|blackwell]"
    exit 1
fi

# Build and push
./build.sh --arch $ARCH --push

echo ""
echo "=========================================="
echo "  ✓ Deployment Complete!"
echo "=========================================="
echo ""
echo "Image: alongbottom/comfyui-runpod:$ARCH"
echo ""
echo "Use in RunPod console to create/update your endpoint"
echo ""
