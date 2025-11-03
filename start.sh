#!/bin/bash
# Startup script for ComfyUI + RunPod Handler
# Starts both ComfyUI server and RunPod handler

set -e

echo "=================================================="
echo "  ComfyUI + RunPod Handler Startup"
echo "=================================================="
echo ""

# PyTorch and CUDA versions (inherited from Dockerfile ENV or set here)
export CUDA_VERSION="${CUDA_VERSION:-12.8}"
export CUDA_TAG="${CUDA_TAG:-cu128}"
export TORCH_VERSION="${TORCH_VERSION:-2.9.0}"
export TORCHVISION_VERSION="${TORCHVISION_VERSION:-0.24.0}"
export TORCHAUDIO_VERSION="${TORCHAUDIO_VERSION:-2.9.0}"
export TORCH_INDEX_URL="${TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu128}"

# Detect environment
if [ -d "/runpod-volume" ]; then
    echo "✓ Running in RunPod environment"
    ENVIRONMENT="runpod"
    MODELS_PATH="/runpod-volume"
    COMFYUI_PATH="/runpod-volume/ComfyUI"
    PYTHON_PACKAGES_DIR="/runpod-volume/python-packages"
else
    echo "✓ Running in local environment"
    ENVIRONMENT="local"
    MODELS_PATH="${MODELS_PATH:-/comfyui/models}"
    COMFYUI_PATH="${COMFYUI_PATH:-/comfyui}"
    # Use workspace parent for Python packages (persists across rebuilds)
    PYTHON_PACKAGES_DIR="/workspace/python-packages"
fi

# ============================================================
# Python Package Persistence (Volume-First Architecture)
# ============================================================
#
# All Python packages install DIRECTLY to volume (not container!)
# Container is minimal - just runtime environment
#
# Flow:
# 1. Set PIP_TARGET to volume directory
# 2. Set PYTHONPATH to use volume packages
# 3. First run: Install PyTorch, ComfyUI deps to volume
# 4. Subsequent runs: Packages already on volume, skip install!

# Create volume package directory
mkdir -p "$PYTHON_PACKAGES_DIR"

# Configure pip to install to volume directory
export PIP_TARGET="$PYTHON_PACKAGES_DIR"

# Prepend volume packages to PYTHONPATH
export PYTHONPATH="$PYTHON_PACKAGES_DIR:${PYTHONPATH:-}"

echo "✓ Python packages install to: $PYTHON_PACKAGES_DIR"
echo "  Container is minimal shell - all packages on volume"

# On first run, install core dependencies to volume
if [ ! -f "$PYTHON_PACKAGES_DIR/.core-deps-installed" ]; then
    echo ""
    echo "=================================================="
    echo "  First Run: Installing Core Dependencies to Volume"
    echo "=================================================="
    echo ""
    echo "Installing PyTorch ${TORCH_VERSION} + CUDA ${CUDA_VERSION}..."
    echo "This is a one-time install (~10GB, takes 3-5 minutes)"
    echo ""

    # Install PyTorch (will go to volume via PIP_TARGET)
    # Using uv for 10-100x faster downloads with parallel connections
    # --index-strategy unsafe-best-match: Check all indexes for CUDA builds
    uv pip install --system --no-cache \
        --index-strategy unsafe-best-match \
        --index-url ${TORCH_INDEX_URL} \
        --extra-index-url https://pypi.org/simple \
        torch==${TORCH_VERSION}+${CUDA_TAG} \
        torchvision==${TORCHVISION_VERSION}+${CUDA_TAG} \
        torchaudio==${TORCHAUDIO_VERSION}+${CUDA_TAG}

    if [ $? -eq 0 ]; then
        echo "✓ PyTorch installed to volume"
    else
        echo "✗ PyTorch installation failed"
        exit 1
    fi

    echo ""
    echo "Installing ComfyUI dependencies..."

    # Fetch and install ComfyUI requirements
    wget -O /tmp/comfyui-requirements.txt \
        https://raw.githubusercontent.com/comfyanonymous/ComfyUI/master/requirements.txt
    uv pip install --system --no-cache -r /tmp/comfyui-requirements.txt
    rm /tmp/comfyui-requirements.txt

    echo "✓ ComfyUI dependencies installed"

    echo ""
    echo "Installing additional dependencies..."

    # Install accelerate
    uv pip install --system --no-cache accelerate

    # Install triton
    uv pip install --system --no-cache triton || echo "Triton skipped (may be bundled)"

    # Install SageAttention (performance optimization with pre-built wheels)
    # Note: Version 1.0.6 has pre-built wheels, no compilation needed
    # Newer versions (2.x) require CUDA compiler which adds 343MB to container
    uv pip install --system --no-cache --no-build-isolation sageattention==1.0.6 \
        && echo "✓ SageAttention installed successfully" \
        || echo "⚠ SageAttention skipped (optional performance optimization)"

    # Install hf_transfer for faster downloads
    uv pip install --system --no-cache hf_transfer

    echo "✓ Additional dependencies installed"

    # Mark as complete
    touch "$PYTHON_PACKAGES_DIR/.core-deps-installed"

    echo ""
    echo "=================================================="
    echo "  Core Dependencies Installed to Volume!"
    echo "=================================================="
    echo ""
    echo "✓ All packages now persist across container rebuilds"
    echo "✓ Future startups will be instant (no reinstall)"
    echo "=================================================="
    echo ""
else
    echo "✓ Core dependencies already on volume (skipping install)"
fi

# Check if ComfyUI exists, if not clone it
if [ ! -f "$COMFYUI_PATH/main.py" ]; then
    echo ""
    echo "ComfyUI not found at: $COMFYUI_PATH"
    echo "Cloning ComfyUI..."

    # Handle volume mounts: Docker Compose may create subdirectories for nested volume mounts
    # We need to clone into a directory that may have these subdirs (output, user, etc.)
    if [ -d "$COMFYUI_PATH" ]; then
        # Save any volume-mounted subdirectories
        TEMP_BACKUP=$(mktemp -d)
        if [ -d "$COMFYUI_PATH/output" ]; then
            mv "$COMFYUI_PATH/output" "$TEMP_BACKUP/" 2>/dev/null || true
        fi
        if [ -d "$COMFYUI_PATH/user" ]; then
            mv "$COMFYUI_PATH/user" "$TEMP_BACKUP/" 2>/dev/null || true
        fi

        # Remove the directory to allow clean clone
        rm -rf "$COMFYUI_PATH"
    fi

    mkdir -p "$(dirname "$COMFYUI_PATH")"
    git clone https://github.com/comfyanonymous/ComfyUI.git "$COMFYUI_PATH"

    # Restore volume-mounted subdirectories if they existed
    if [ -d "$TEMP_BACKUP" ]; then
        if [ -d "$TEMP_BACKUP/output" ]; then
            rm -rf "$COMFYUI_PATH/output"
            mv "$TEMP_BACKUP/output" "$COMFYUI_PATH/" 2>/dev/null || true
        fi
        if [ -d "$TEMP_BACKUP/user" ]; then
            rm -rf "$COMFYUI_PATH/user"
            mv "$TEMP_BACKUP/user" "$COMFYUI_PATH/" 2>/dev/null || true
        fi
        rm -rf "$TEMP_BACKUP"
    fi

    echo "Installing ComfyUI dependencies..."
    cd "$COMFYUI_PATH"
    uv pip install --system --no-cache -r requirements.txt

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
                    uv pip install --system --no-cache --upgrade -r requirements.txt
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

# Copy helper files to workspace for easy access from Jupyter
WORKSPACE_DIR=""
if [ -d "/runpod-volume" ]; then
    WORKSPACE_DIR="/runpod-volume"
else
    WORKSPACE_DIR="$COMFYUI_PATH/.."
fi

# Copy apply_config.sh if not exists
if [ ! -f "$WORKSPACE_DIR/apply_config.sh" ] && [ -f "/app/apply_config.sh" ]; then
    cp /app/apply_config.sh "$WORKSPACE_DIR/"
    chmod +x "$WORKSPACE_DIR/apply_config.sh"
    echo "✓ Copied apply_config.sh to workspace"
fi

# Copy CONFIG_MANAGEMENT.md if not exists
if [ ! -f "$WORKSPACE_DIR/CONFIG_MANAGEMENT.md" ] && [ -f "/app/CONFIG_MANAGEMENT.md" ]; then
    cp /app/CONFIG_MANAGEMENT.md "$WORKSPACE_DIR/"
    echo "✓ Copied CONFIG_MANAGEMENT.md to workspace"
fi

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

    # Try to detect and decode base64 encoding
    CONFIG_CONTENT=""
    IS_BASE64=false

    # Check if it looks like base64 (no newlines, only valid base64 chars)
    if echo "$CONFIG_YML" | grep -qE '^[A-Za-z0-9+/=]+$'; then
        echo "Detected possible base64 encoding, attempting decode..."

        # Try to decode
        DECODED=$(echo "$CONFIG_YML" | base64 -d 2>/dev/null)

        if [ $? -eq 0 ] && [ -n "$DECODED" ]; then
            # Validate it's valid YAML by checking for basic structure
            if echo "$DECODED" | grep -qE '^(models:|nodes:|#)'; then
                echo "✓ Successfully decoded base64 config"
                CONFIG_CONTENT="$DECODED"
                IS_BASE64=true
            else
                echo "⚠ Warning: Decoded content doesn't look like valid config.yml"
                echo "   Expected 'models:' or 'nodes:' sections"
                echo "   Treating as plain text..."
                CONFIG_CONTENT="$CONFIG_YML"
            fi
        else
            echo "⚠ Warning: Base64 decode failed, treating as plain text"
            CONFIG_CONTENT="$CONFIG_YML"
        fi
    else
        # Contains newlines or special chars, treat as plain YAML
        CONFIG_CONTENT="$CONFIG_YML"
    fi

    # Write config to volume
    echo "$CONFIG_CONTENT" > "$VOLUME_CONFIG"

    if [ $? -eq 0 ]; then
        echo "✓ Config written to persistent volume"

        # Validate YAML structure
        if ! echo "$CONFIG_CONTENT" | grep -qE '(models:|nodes:)'; then
            echo ""
            echo "⚠ Warning: Config may be invalid!"
            echo "   Expected sections: 'models:' and/or 'nodes:'"
            echo "   Please verify your config.yml format"
        fi

        echo ""
        echo "Config management options:"
        echo "  - Pods: Edit via Jupyter (port 8888) at $VOLUME_CONFIG"
        echo "  - Endpoints: Update CONFIG_YML env var to regenerate"
        if [ "$IS_BASE64" = true ]; then
            echo "  - Base64 encode at: https://www.base64encode.org/"
        fi
        echo ""
    else
        echo "✗ Failed to write config (using default)"
    fi
    echo "=================================================="
    echo ""
fi

# ============================================================
# Configuration Change Detection (SHA-based for fast warm starts)
# ============================================================

# Determine config file location (priority order)
CONFIG_FILE=""
if [ -f "/runpod-volume/config.yml" ]; then
    CONFIG_FILE="/runpod-volume/config.yml"
elif [ -f "$COMFYUI_PATH/../config.yml" ]; then
    CONFIG_FILE="$COMFYUI_PATH/../config.yml"
elif [ -f "/app/config.yml" ]; then
    CONFIG_FILE="/app/config.yml"
fi

# Determine SHA storage location (persistent volume)
SHA_FILE=""
if [ -d "/runpod-volume" ]; then
    SHA_FILE="/runpod-volume/.config-sha256"
elif [ -d "$COMFYUI_PATH/.." ]; then
    SHA_FILE="$COMFYUI_PATH/../.config-sha256"
fi

# Calculate current config SHA
CURRENT_SHA=""
if [ -n "$CONFIG_FILE" ] && [ -f "$CONFIG_FILE" ]; then
    CURRENT_SHA=$(sha256sum "$CONFIG_FILE" | awk '{print $1}')
fi

# Check if config changed
CONFIG_CHANGED=true
SKIP_INSTALL=false

if [ -n "$CURRENT_SHA" ] && [ -n "$SHA_FILE" ] && [ -f "$SHA_FILE" ]; then
    STORED_SHA=$(cat "$SHA_FILE" 2>/dev/null || echo "")

    if [ "$CURRENT_SHA" = "$STORED_SHA" ]; then
        echo "=================================================="
        echo "  Fast Warm Start: Config Unchanged"
        echo "=================================================="
        echo ""
        echo "✓ Config SHA matches stored hash"
        echo "  SHA: ${CURRENT_SHA:0:16}..."
        echo ""
        echo "Skipping model downloads and node installations for fast startup."
        echo "This significantly reduces warm start time!"
        echo ""
        echo "To force reinstall, delete: $SHA_FILE"
        echo "=================================================="
        echo ""
        CONFIG_CHANGED=false
        SKIP_INSTALL=true
    else
        echo "=================================================="
        echo "  Config Changed - Applying Updates"
        echo "=================================================="
        echo ""
        echo "Previous SHA: ${STORED_SHA:0:16}..."
        echo "Current SHA:  ${CURRENT_SHA:0:16}..."
        echo ""
        echo "Config has changed, applying updates..."
        echo "=================================================="
        echo ""
    fi
elif [ -n "$CURRENT_SHA" ]; then
    echo "=================================================="
    echo "  First Run - Installing from Config"
    echo "=================================================="
    echo ""
    echo "Config SHA: ${CURRENT_SHA:0:16}..."
    echo ""
    echo "This is the first run or cache was cleared."
    echo "Installing models and custom nodes..."
    echo "=================================================="
    echo ""
fi

# Install custom nodes from config.yml
# Priority: volume config → baked-in config

if [ "$SKIP_INSTALL" = false ]; then
    echo "Checking for custom nodes to install..."

    if [ -f "/runpod-volume/config.yml" ]; then
        echo "Using config from: /runpod-volume/config.yml (persistent volume)"
    elif [ -f "$COMFYUI_PATH/../config.yml" ]; then
        echo "Using config from: $COMFYUI_PATH/../config.yml (mounted volume)"
    elif [ -f "/app/config.yml" ]; then
        echo "Using config from: /app/config.yml (baked-in default)"
    fi
fi

if [ "$SKIP_INSTALL" = false ]; then
    if [ -n "$CONFIG_FILE" ] && [ -f "/app/install_nodes.py" ]; then
            # Count active node entries
            ACTIVE_NODES=$(grep -A 2 "^  - url:" "$CONFIG_FILE" | grep -v "^#" | grep "url:" | wc -l || echo "0")

            if [ "$ACTIVE_NODES" -gt 0 ]; then
                echo "Found $ACTIVE_NODES custom node(s) to install"

                python3 /app/install_nodes.py \
                    --config "$CONFIG_FILE" \
                    --comfyui-dir "$COMFYUI_PATH" \
                    --max-workers 2 \
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
fi

# Download models from config.yml

if [ "$SKIP_INSTALL" = false ]; then
    echo "Checking for models to download..."

    # Config file already determined above
    if [ -f "/runpod-volume/config.yml" ]; then
        echo "Using config from: /runpod-volume/config.yml (persistent volume)"
    elif [ -f "$COMFYUI_PATH/../config.yml" ]; then
        echo "Using config from: $COMFYUI_PATH/../config.yml (mounted volume)"
    elif [ -f "/app/config.yml" ]; then
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

    # Update SHA after successful installation
    if [ -n "$CURRENT_SHA" ] && [ -n "$SHA_FILE" ]; then
        echo "$CURRENT_SHA" > "$SHA_FILE"
        echo "✓ Config SHA updated: ${CURRENT_SHA:0:16}..."
        echo "  Future warm starts will be faster!"
        echo ""
    fi
fi

# Orphaned nodes check removed - batch UV installation in Phase 2
# already handles all dependencies for nodes in config.yml

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

# Start Jupyter in background (skip in endpoint mode for fast cold starts)
if [ "$RUN_MODE" != "endpoint" ] && [ "$RUN_MODE" != "serverless" ]; then
    echo "Starting Jupyter server on port 8888..."

    # Configure Jupyter authentication
    JUPYTER_AUTH_ARGS=""
    if [ -n "$JUPYTER_PASSWORD" ]; then
        echo "  🔒 Password protection enabled"
        JUPYTER_AUTH_ARGS="--ServerApp.token='$JUPYTER_PASSWORD' --ServerApp.password=''"
    else
        echo "  🔓 No password required (set JUPYTER_PASSWORD env to enable)"
        JUPYTER_AUTH_ARGS="--ServerApp.token='' --ServerApp.password=''"
    fi

    cd /app
    jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root \
        $JUPYTER_AUTH_ARGS \
        --ServerApp.allow_origin='*' \
        --ServerApp.root_dir="$COMFYUI_PATH/.." &
    JUPYTER_PID=$!
    echo "  PID: ${JUPYTER_PID}"
    echo ""
else
    echo "Skipping Jupyter (endpoint mode - optimized for cold starts)"
    JUPYTER_PID=""
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

echo "=================================================="
echo "  Startup Complete!"
echo "=================================================="
echo ""
echo "Services running:"
echo "  • ComfyUI:      http://localhost:8188"
echo "  • RunPod API:   http://localhost:8000"
if [ -n "$JUPYTER_PID" ]; then
    echo "  • Jupyter Lab:  http://localhost:8888"
fi
echo ""

if [ "$ENVIRONMENT" = "local" ]; then
    echo "Local Development Mode:"
    echo "  1. Open http://localhost:8188 to design workflows"
    if [ -n "$JUPYTER_PID" ]; then
        echo "  2. Use Jupyter (port 8888) for testing and file management"
        echo "  3. Test handler: Create workflows in examples/ directory"
    else
        echo "  2. Test handler: Create workflows in examples/ directory"
    fi
    echo ""
fi

echo "Logs:"
if [ -n "$JUPYTER_PID" ]; then
    echo "  • Jupyter PID:  ${JUPYTER_PID}"
fi
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
    [ -n "$JUPYTER_PID" ] && kill $JUPYTER_PID 2>/dev/null || true
    echo "Shutdown complete"
    exit 0
}

# Trap SIGTERM and SIGINT
trap shutdown SIGTERM SIGINT

# Wait for processes
if [ -n "$JUPYTER_PID" ]; then
    wait $JUPYTER_PID $COMFYUI_PID $HANDLER_PID
else
    wait $COMFYUI_PID $HANDLER_PID
fi

# If we get here, one of the processes died unexpectedly
echo "⚠ A service has stopped unexpectedly!"
shutdown
