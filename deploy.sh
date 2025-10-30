#!/bin/bash
# Quick deploy script - builds and pushes the unified image
# Supports all modern NVIDIA GPUs (RTX 4090, RTX 5090, and beyond)

set -e

echo "Building and pushing unified ComfyUI RunPod image..."
echo "Compatible with all modern NVIDIA GPUs"
echo ""

./build.sh --push

echo ""
echo "✓ Deployment complete!"
echo "Image: artokun/comfyui-runpod:latest"
echo ""
echo "Ready to use on RunPod with any modern NVIDIA GPU!"
