#!/bin/bash
# Apply config.yml changes - download models and install custom nodes
# Run this after editing config.yml to apply changes without restarting

set -e

echo "============================================================"
echo "  ComfyUI Config Applier"
echo "============================================================"
echo ""

# Detect environment
if [ -d "/runpod-volume" ]; then
    echo "✓ Running in RunPod environment"
    ENVIRONMENT="runpod"
    COMFYUI_PATH="${COMFYUI_PATH:-/runpod-volume/ComfyUI}"
else
    echo "✓ Running in local environment"
    ENVIRONMENT="local"
    COMFYUI_PATH="${COMFYUI_PATH:-/workspace/ComfyUI}"
fi

echo "ComfyUI Path: $COMFYUI_PATH"
echo ""

# Determine config file location (priority order)
CONFIG_FILE=""
if [ -f "/runpod-volume/config.yml" ]; then
    CONFIG_FILE="/runpod-volume/config.yml"
    echo "Using config from: /runpod-volume/config.yml (persistent volume)"
elif [ -f "$COMFYUI_PATH/../config.yml" ]; then
    CONFIG_FILE="$COMFYUI_PATH/../config.yml"
    echo "Using config from: $COMFYUI_PATH/../config.yml (mounted volume)"
elif [ -f "/app/config.yml" ]; then
    CONFIG_FILE="/app/config.yml"
    echo "Using config from: /app/config.yml (baked-in default)"
else
    echo "✗ Error: config.yml not found!"
    echo ""
    echo "Expected locations:"
    echo "  - /runpod-volume/config.yml (RunPod)"
    echo "  - $COMFYUI_PATH/../config.yml (Local)"
    echo "  - /app/config.yml (Fallback)"
    exit 1
fi

echo ""

# Check if ComfyUI exists
if [ ! -d "$COMFYUI_PATH" ]; then
    echo "✗ Error: ComfyUI not found at $COMFYUI_PATH"
    echo ""
    echo "Please ensure ComfyUI is installed before running this script."
    exit 1
fi

echo "============================================================"
echo "  Installing Custom Nodes"
echo "============================================================"
echo ""

# Count active node entries
ACTIVE_NODES=$(grep -A 2 "^  - url:" "$CONFIG_FILE" | grep -v "^#" | grep "url:" | wc -l || echo "0")

if [ "$ACTIVE_NODES" -gt 0 ]; then
    echo "Found $ACTIVE_NODES custom node(s) to install"
    echo ""

    if [ -f "/app/install_nodes.py" ]; then
        python3 /app/install_nodes.py \
            --config "$CONFIG_FILE" \
            --comfyui-dir "$COMFYUI_PATH" \
            --max-workers 4 \
            || INSTALL_EXIT_CODE=$?

        if [ "${INSTALL_EXIT_CODE:-0}" -eq 0 ]; then
            echo ""
            echo "✓ Custom nodes installation complete"
        else
            echo ""
            echo "⚠ Some custom nodes failed to install (check logs above)"
        fi
    else
        echo "✗ Error: install_nodes.py not found at /app/install_nodes.py"
        exit 1
    fi
else
    echo "No custom nodes configured for installation (all commented out)"
fi

echo ""
echo "============================================================"
echo "  Downloading Models"
echo "============================================================"
echo ""

# Count active model entries
ACTIVE_MODELS=$(grep -A 2 "^  - url:" "$CONFIG_FILE" | grep -v "^#" | grep "url:" | wc -l || echo "0")

if [ "$ACTIVE_MODELS" -gt 0 ]; then
    echo "Found $ACTIVE_MODELS model(s) to download"
    echo ""

    if [ -f "/app/download_models.py" ]; then
        python3 /app/download_models.py \
            --config "$CONFIG_FILE" \
            --base-dir "$COMFYUI_PATH/models" \
            --parallel 3 \
            || DOWNLOAD_EXIT_CODE=$?

        if [ "${DOWNLOAD_EXIT_CODE:-0}" -eq 0 ]; then
            echo ""
            echo "✓ Model downloads complete"
        else
            echo ""
            echo "⚠ Some model downloads failed (check logs above)"
        fi
    else
        echo "✗ Error: download_models.py not found at /app/download_models.py"
        exit 1
    fi
else
    echo "No models configured for download (all commented out)"
fi

echo ""

# Update SHA for fast warm starts
SHA_FILE=""
if [ -d "/runpod-volume" ]; then
    SHA_FILE="/runpod-volume/.config-sha256"
elif [ -d "$COMFYUI_PATH/.." ]; then
    SHA_FILE="$COMFYUI_PATH/../.config-sha256"
fi

if [ -n "$SHA_FILE" ] && [ -f "$CONFIG_FILE" ]; then
    CURRENT_SHA=$(sha256sum "$CONFIG_FILE" | awk '{print $1}')
    echo "$CURRENT_SHA" > "$SHA_FILE"
    echo "✓ Config SHA updated for fast warm starts"
    echo "  SHA: ${CURRENT_SHA:0:16}..."
    echo ""
fi

echo "============================================================"
echo "  Configuration Applied Successfully!"
echo "============================================================"
echo ""
echo "Summary:"
echo "  • Custom nodes: $ACTIVE_NODES processed"
echo "  • Models: $ACTIVE_MODELS processed"
echo "  • Config file: $CONFIG_FILE"
echo ""
echo "Next steps:"
if [ "$ENVIRONMENT" = "runpod" ]; then
    echo "  1. Restart ComfyUI if it's running"
    echo "  2. Access ComfyUI at port 8188"
else
    echo "  1. Restart docker compose if needed: docker compose restart"
    echo "  2. Access ComfyUI at http://localhost:8188"
fi
echo ""
