#!/bin/bash
# Startup script for ComfyUI + RunPod Handler
# Starts both ComfyUI server and RunPod handler

set -e

echo "=================================================="
echo "  ComfyUI + RunPod Handler Startup"
echo "=================================================="
echo ""

# Detect environment
if [ -d "/runpod-volume" ]; then
    echo "✓ Running in RunPod environment"
    ENVIRONMENT="runpod"
    MODELS_PATH="/runpod-volume"
    COMFYUI_PATH="/runpod-volume/ComfyUI"
else
    echo "✓ Running in local environment"
    ENVIRONMENT="local"
    MODELS_PATH="${MODELS_PATH:-/comfyui/models}"
    COMFYUI_PATH="${COMFYUI_PATH:-/comfyui}"
fi

# Check if ComfyUI exists, if not clone it
if [ ! -f "$COMFYUI_PATH/main.py" ]; then
    echo ""
    echo "ComfyUI not found at: $COMFYUI_PATH"
    echo "Cloning ComfyUI..."

    # Remove empty directory if it exists
    if [ -d "$COMFYUI_PATH" ] && [ -z "$(ls -A "$COMFYUI_PATH")" ]; then
        rmdir "$COMFYUI_PATH"
    fi

    mkdir -p "$(dirname "$COMFYUI_PATH")"
    git clone https://github.com/comfyanonymous/ComfyUI.git "$COMFYUI_PATH"

    echo "Installing ComfyUI dependencies..."
    cd "$COMFYUI_PATH"
    pip3 install -r requirements.txt --no-cache-dir

    echo "✓ ComfyUI installed"
    echo ""
else
    echo "✓ ComfyUI found at: $COMFYUI_PATH"

    # Update ComfyUI if AUTO_UPDATE is enabled
    if [ "${AUTO_UPDATE:-false}" = "true" ] && [ -d "$COMFYUI_PATH/.git" ]; then
        echo "Auto-update enabled, checking for updates..."
        cd "$COMFYUI_PATH"

        # Store current commit
        CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")

        # Try to update
        if git pull --ff-only 2>/dev/null; then
            NEW_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")

            if [ "$CURRENT_COMMIT" != "$NEW_COMMIT" ]; then
                echo "✓ Updated to: $NEW_COMMIT"

                # Update dependencies if requirements.txt changed
                if git diff --name-only "$CURRENT_COMMIT" "$NEW_COMMIT" 2>/dev/null | grep -q "requirements.txt"; then
                    echo "Updating dependencies..."
                    pip3 install -r requirements.txt --upgrade --no-cache-dir
                fi
            else
                echo "Already up to date"
            fi
        else
            echo "⚠ Could not auto-update (conflicts or no git), continuing with current version"
        fi
        echo ""
    fi
fi

echo "  GPU Architecture: ${GPU_ARCH:-ada}"
echo "  CUDA Version: ${CUDA_VERSION:-11.8}"
echo "  PyTorch Version: ${PYTORCH_VERSION:-2.1.0}"
echo "  Models Path: ${MODELS_PATH}"
echo "  Environment: ${ENVIRONMENT}"
echo ""

# Configuration hierarchy:
# 1. CONFIG_YML env var → writes to volume (persistent, editable)
# 2. config.yml on volume (source of truth)
# 3. /app/config.yml (baked-in fallback)

# Handle CONFIG_YML environment variable (for RunPod/cloud deployments)
if [ -n "$CONFIG_YML" ]; then
    echo "=================================================="
    echo "  CONFIG_YML Environment Variable Detected"
    echo "=================================================="

    # Determine volume config path
    if [ -d "/runpod-volume" ]; then
        VOLUME_CONFIG="/runpod-volume/config.yml"
    else
        VOLUME_CONFIG="$COMFYUI_PATH/../config.yml"
    fi

    echo "Writing config to: $VOLUME_CONFIG"

    # Create parent directory if needed
    mkdir -p "$(dirname "$VOLUME_CONFIG")"

    # Write environment variable content to persistent volume
    echo "$CONFIG_YML" > "$VOLUME_CONFIG"

    if [ $? -eq 0 ]; then
        echo "✓ Config written to persistent volume"
        echo ""
        echo "This file will persist across restarts and can be edited:"
        echo "  - Pods: Upload via Jupyter or edit directly"
        echo "  - Endpoints: Update CONFIG_YML env var to regenerate"
        echo ""
    else
        echo "✗ Failed to write config (using default)"
    fi
    echo "=================================================="
    echo ""
fi

# Install custom nodes from config.yml
# Priority: volume config → baked-in config
echo "Checking for custom nodes to install..."

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
fi

if [ -n "$CONFIG_FILE" ] && [ -f "/app/install_nodes.py" ]; then
        # Count active node entries
        ACTIVE_NODES=$(grep -A 2 "^  - url:" "$CONFIG_FILE" | grep -v "^#" | grep "url:" | wc -l || echo "0")

        if [ "$ACTIVE_NODES" -gt 0 ]; then
            echo "Found $ACTIVE_NODES custom node(s) to install"

            python3 /app/install_nodes.py \
                --config "$CONFIG_FILE" \
                --comfyui-dir "$COMFYUI_PATH" \
                --max-workers 4 \
                || INSTALL_EXIT_CODE=$?

            if [ "${INSTALL_EXIT_CODE:-0}" -eq 0 ]; then
                echo "✓ Custom nodes installation complete"
            else
                echo "⚠ Some custom nodes failed to install (check logs above)"
            fi
        else
            echo "No custom nodes configured for installation (all commented out)"
        fi
else
    echo "⚠ config.yml or install_nodes.py not found, skipping custom node installation"
fi
echo ""

# Download models from config.yml
echo "Checking for models to download..."

# Determine config file location (priority order - same as nodes)
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
fi

if [ -n "$CONFIG_FILE" ] && [ -f "/app/download_models.py" ]; then
        # Count active model entries
        ACTIVE_MODELS=$(grep -A 2 "^  - url:" "$CONFIG_FILE" | grep -v "^#" | grep "url:" | wc -l || echo "0")

        if [ "$ACTIVE_MODELS" -gt 0 ]; then
            echo "Found $ACTIVE_MODELS model(s) to download"

            python3 /app/download_models.py \
                --config "$CONFIG_FILE" \
                --base-dir "$COMFYUI_PATH/models" \
                --parallel 3 \
                || DOWNLOAD_EXIT_CODE=$?

            if [ "${DOWNLOAD_EXIT_CODE:-0}" -eq 0 ]; then
                echo "✓ Model downloads complete"
            else
                echo "⚠ Some model downloads failed (check logs above)"
            fi
        else
            echo "No models configured for download (all commented out)"
        fi
else
    echo "⚠ download_models.py not found, skipping model downloads"
fi
echo ""

# Check GPU availability
echo "Checking GPU..."
if python3 -c "import torch; assert torch.cuda.is_available(), 'GPU not available'"; then
    GPU_NAME=$(python3 -c "import torch; print(torch.cuda.get_device_name(0))")
    GPU_MEMORY=$(python3 -c "import torch; print(f'{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB')")
    echo "✓ GPU Available: ${GPU_NAME} (${GPU_MEMORY})"
else
    echo "⚠ WARNING: No GPU detected! Performance will be severely degraded."
fi
echo ""

# Create symlinks for models if in RunPod and volume exists
if [ "$ENVIRONMENT" = "runpod" ] && [ -d "/runpod-volume" ]; then
    echo "Setting up model symlinks..."

    # Only create symlinks if the source directories exist
    [ -d "/runpod-volume/checkpoints" ] && ln -sf /runpod-volume/checkpoints /comfyui/models/checkpoints && echo "  ✓ Linked checkpoints"
    [ -d "/runpod-volume/vae" ] && ln -sf /runpod-volume/vae /comfyui/models/vae && echo "  ✓ Linked vae"
    [ -d "/runpod-volume/loras" ] && ln -sf /runpod-volume/loras /comfyui/models/loras && echo "  ✓ Linked loras"
    [ -d "/runpod-volume/embeddings" ] && ln -sf /runpod-volume/embeddings /comfyui/models/embeddings && echo "  ✓ Linked embeddings"
    [ -d "/runpod-volume/controlnet" ] && ln -sf /runpod-volume/controlnet /comfyui/models/controlnet && echo "  ✓ Linked controlnet"
    [ -d "/runpod-volume/upscale_models" ] && ln -sf /runpod-volume/upscale_models /comfyui/models/upscale_models && echo "  ✓ Linked upscale_models"

    echo ""
fi

# Start ComfyUI in background
echo "Starting ComfyUI server on port 8188..."
cd "$COMFYUI_PATH"
python3 main.py --listen 0.0.0.0 --port 8188 &
COMFYUI_PID=$!
echo "  PID: ${COMFYUI_PID}"
echo ""

# Wait for ComfyUI to be ready
echo "Waiting for ComfyUI to start..."
RETRIES=30
WAIT_TIME=2

for i in $(seq 1 $RETRIES); do
    if curl -s http://127.0.0.1:8188/ > /dev/null 2>&1; then
        echo "✓ ComfyUI is ready!"
        break
    fi

    if [ $i -eq $RETRIES ]; then
        echo "✗ ComfyUI failed to start after ${RETRIES} attempts"
        kill $COMFYUI_PID 2>/dev/null || true
        exit 1
    fi

    echo "  Attempt $i/${RETRIES}... waiting ${WAIT_TIME}s"
    sleep $WAIT_TIME
done
echo ""

# Start RunPod handler
echo "Starting RunPod handler on port 8000..."
cd /app
python3 handler.py &
HANDLER_PID=$!
echo "  PID: ${HANDLER_PID}"
echo ""

# Wait for handler to be ready (if running in local mode)
if [ "$ENVIRONMENT" = "local" ]; then
    echo "Waiting for handler to start..."
    sleep 3

    if curl -s http://127.0.0.1:8000/ > /dev/null 2>&1; then
        echo "✓ Handler is ready!"
    else
        echo "⚠ Handler may not be responding (this is normal for RunPod mode)"
    fi
    echo ""
fi

echo "=================================================="
echo "  Startup Complete!"
echo "=================================================="
echo ""
echo "Services running:"
echo "  • ComfyUI:      http://localhost:8188"
echo "  • RunPod API:   http://localhost:8000"
echo ""

if [ "$ENVIRONMENT" = "local" ]; then
    echo "Local Development Mode:"
    echo "  1. Open http://localhost:8188 to design workflows"
    echo "  2. Export workflow in API format"
    echo "  3. Test with: curl -X POST http://localhost:8000 -d @example_request.json"
    echo ""
fi

echo "Logs:"
echo "  • ComfyUI PID:  ${COMFYUI_PID}"
echo "  • Handler PID:  ${HANDLER_PID}"
echo ""
echo "Press Ctrl+C to stop all services"
echo "=================================================="
echo ""

# Function to handle shutdown
shutdown() {
    echo ""
    echo "Shutting down services..."
    kill $HANDLER_PID 2>/dev/null || true
    kill $COMFYUI_PID 2>/dev/null || true
    echo "Shutdown complete"
    exit 0
}

# Trap SIGTERM and SIGINT
trap shutdown SIGTERM SIGINT

# Wait for processes
wait $COMFYUI_PID $HANDLER_PID

# If we get here, one of the processes died unexpectedly
echo "⚠ A service has stopped unexpectedly!"
shutdown
