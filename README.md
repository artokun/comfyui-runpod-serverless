# ComfyUI RunPod Handler

[![CI](https://github.com/artokun/comfyui-runpod-serverless/actions/workflows/ci.yml/badge.svg)](https://github.com/artokun/comfyui-runpod-serverless/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)

Run ComfyUI locally with a RunPod-compatible API handler, then deploy to RunPod serverless or GPU pods.

> **Open Source**: This project is open source and welcomes contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Quick Start

```bash
docker compose up
```

**First run:** Initial startup downloads ComfyUI, installs dependencies with **uv** (10-100x faster than pip!), and configures models/nodes from `config.yml`. First run ~2-3 minutes, subsequent runs ~10-30 seconds thanks to volume-first architecture and SHA-based caching.

Open your browser:
- **http://localhost:8188** - ComfyUI interface (design workflows)
- **http://localhost:8000** - API endpoint (test requests)
- **http://localhost:8888** - Jupyter Lab (edit config, manage files)

Press `Ctrl+C` to stop.

## What You Get

✅ **Lightning-fast package installation** - uv package manager (10-100x faster than pip)
✅ **Volume-first architecture** - Minimal 8.7GB container, everything persists on volume
✅ **Universal GPU support** - PyTorch 2.9.0 + CUDA 12.8 (RTX 4090, RTX 5090, future GPUs)
✅ **Blazing downloads** - hf_transfer for HuggingFace (100-200+ MB/s), parallel chunks for others
✅ **ComfyUI auto-installs** on first run (updateable, persistent)
✅ **Full web interface** for workflow design
✅ **Jupyter Lab** for config editing and file management
✅ **RunPod-compatible API** handler
✅ **SHA-based config caching** - Skip reinstalls when config unchanged
✅ **Works everywhere** - Mac, Linux, Windows

## Table of Contents

- [Deploy to RunPod](#deploy-to-runpod)
  - [Serverless Endpoints (Production)](#-serverless-endpoints-production)
  - [GPU Pods (Development)](#-gpu-pods-development)
- [Configuration](#configuration)
  - [Editing config.yml](#editing-configyml)
  - [Applying Changes](#applying-changes)
  - [config.yml Format](#configyml-format-reference)
- [Local Development](#local-development)
- [Architecture](#architecture)
- [API Format](#api-format)
- [Contributing](#contributing)

---

## Deploy to RunPod

### Choose Your Deployment Type

**🚀 Serverless Endpoints** - Auto-scaling production APIs with scale-to-zero
**🔧 GPU Pods** - Interactive development with Jupyter and SSH access

---

## 🚀 Serverless Endpoints (Production)

Deploy ComfyUI as a serverless API endpoint with auto-scaling and scale-to-zero cost savings.

### Prerequisites

1. **RunPod Account** - Sign up at https://runpod.io
2. **Payment Method** - Add to your RunPod account
3. **Network Volume** - For persistent models/nodes (recommended)

### Step 1: Create Template

1. Go to https://runpod.io/console/serverless
2. Click **"New Template"**
3. Configure:

```
Name: ComfyUI Handler
Container Image: artokun/comfyui-runpod:latest
Container Disk: 20 GB

Environment Variables (Optional - all have defaults):
  RUN_MODE=endpoint              # Skips Jupyter for fast cold starts
  # AUTO_UPDATE=false            # (default)
  # COMFY_API_URL=http://127.0.0.1:8188  # (default)

Expose HTTP Ports:
  Leave blank (API-only)
  Or: 8188 (for debugging ComfyUI UI)
```

4. Click **"Save Template"**

### Step 2: Create Network Volume

1. Go to **Storage** → **Network Volumes**
2. Click **"New Network Volume"**
3. Configure:
   - **Name:** `comfyui-volume`
   - **Region:** Choose region with GPU availability
   - **Size:** 100 GB (recommended for models + ComfyUI)
4. Click **"Create"**

**Why volume is required:**
- ComfyUI installs to `/runpod-volume/ComfyUI` (persistent)
- Models stored permanently (no re-download)
- Custom nodes persist
- Faster cold starts after first run

### Step 3: Create Endpoint

1. Go back to **Serverless**
2. Click **"New Endpoint"**
3. Configure:

```
Name: comfyui-production
Select Template: ComfyUI Handler
Select Network Volume: comfyui-volume

GPUs:
  ☑ RTX 4090 (or RTX 5090)
  Min Workers: 0
  Max Workers: 3

Advanced:
  Idle Timeout: 5 seconds
  Execution Timeout: 600 seconds
  Max Concurrent Requests: 1
```

4. Click **"Deploy"**

### Step 4: Test Your Endpoint

```bash
export RUNPOD_ENDPOINT_ID="your-endpoint-id"
export RUNPOD_API_KEY="your-api-key"

curl -X POST "https://api.runpod.ai/v2/${RUNPOD_ENDPOINT_ID}/runsync" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d @examples/example_request.json
```

### Cost Estimation (Serverless)

**RTX 4090:**
- Idle: $0.00/hour (scale to zero)
- Active: ~$0.50-0.70/hour
- Per workflow: ~$0.01-0.03

**RTX 5090:**
- Idle: $0.00/hour
- Active: ~$1.50-2.00/hour
- Per workflow: ~$0.01-0.07

**Tips to reduce costs:**
- Scale to zero (min workers: 0)
- Set short idle timeout (5 seconds)
- Batch multiple images
- Use appropriate resolution

---

## 🔧 GPU Pods (Development)

Deploy ComfyUI to RunPod GPU Pods for interactive development with Jupyter notebook access.

### What are Pods?

**Pods** are traditional GPU instances with:
- ✅ SSH and Jupyter notebook access
- ✅ Direct file system access
- ✅ Interactive development
- ✅ Pay-per-hour billing (running time only)

**Use Pods for:** Development, testing, interactive ComfyUI design, experimenting
**Use Serverless for:** Production APIs, auto-scaling, scale-to-zero cost savings

### Quick Start (Pods)

#### Step 1: Create Network Volume

1. Go to https://runpod.io/console/storage
2. Click **"New Network Volume"**
3. Configure:
   - **Name:** `comfyui-volume`
   - **Region:** Choose region with RTX 4090/5090
   - **Size:** 50 GB minimum
4. Click **"Create"**

#### Step 2: Deploy Pod

1. Go to https://runpod.io/console/pods
2. Click **"Deploy"** or **"GPU Pods"**
3. Select GPU: **RTX 4090** ($0.50-0.70/hr) or **RTX 5090**
4. Configure:
   ```
   Container Image: artokun/comfyui-runpod:latest
   Container Disk: 50 GB
   Volume Mount: comfyui-volume → /runpod-volume
   Expose HTTP Ports: 8188, 8000, 8888

   Environment Variables:
   RUN_MODE=production  # Enables Jupyter Lab
   ```
5. Click **"Deploy"**

#### Step 3: Access Your Pod

Once deployed:
- **Connect** button → Opens Jupyter notebook
- **TCP Port Mappings** → External URLs for ports

**Access points:**
- **Port 8188** → ComfyUI web interface
- **Port 8000** → RunPod handler API
- **Port 8888** → Jupyter Lab

### Cost Management (Pods)

Pods bill **per second** while running:
- RTX 4090: ~$0.50-0.70/hour
- RTX 5090: ~$1.50-2.00/hour

**Tip:** Stop pods when not in use! Your volume data persists.

- **Stop:** Click "Stop" button (volume persists)
- **Start:** Click "Start" button (restores from volume)
- **Terminate:** Deletes pod (volume remains)

---

## Configuration

### Editing config.yml

The `config.yml` file controls which models and custom nodes are installed. It's mounted as a volume, so **you can edit anytime without rebuilding the Docker image!**

**Default config:**
Minimal setup with SD 1.5 + ComfyUI Manager (~4GB) for fast builds.

**Advanced example:**
See `config.example.yml` for complete WAN Animate 2.2 setup with 11 models and 20+ nodes (~30GB).

#### Method 1: Edit via Jupyter Lab (Recommended for RunPod)

**Step 1:** Access Jupyter Lab
- **Local:** http://localhost:8888
- **RunPod Pod:** Port 8888 in pod connection info

**Step 2:** Navigate to config.yml
- **RunPod:** `/runpod-volume/config.yml` or `/workspace/config.yml`
- **Local:** `/workspace/config.yml`

**Step 3:** Edit and save (Ctrl+S or Cmd+S)

```yaml
models:
  - url: https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors
    destination: vae
    optional: false

nodes:
  - url: https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
    version: latest
```

**Step 4:** Apply changes (see [Applying Changes](#applying-changes) below)

#### Method 2: Local Terminal (Development)

```bash
nano config.yml
# or
code config.yml  # VS Code
```

Then restart container:
```bash
docker compose restart
```

#### Method 3: Base64 Encoded (RunPod Endpoints)

For **RunPod Endpoints** (serverless), set as environment variable:

1. Prepare your `config.yml` file
2. Encode at **https://www.base64encode.org/** (copy file, paste, ENCODE)
3. Set in RunPod template settings:
   ```bash
   CONFIG_YML=<base64-encoded-string>
   ```

The container automatically decodes and applies on startup!

**Configuration Priority:**
1. 🥇 `CONFIG_YML` env var → Writes to volume (persistent)
2. 🥈 `config.yml` on volume → Can be edited directly
3. 🥉 Baked-in default → Fallback

### Applying Changes

After editing `config.yml`, run the apply script to install new models/nodes without restarting:

**Via Jupyter Terminal:**
```bash
cd /app
chmod +x apply_config.sh
./apply_config.sh
```

**Via Docker:**
```bash
docker compose exec comfyui /app/apply_config.sh
```

**What it does:**
- ✅ Installs new custom nodes
- ✅ Downloads new models
- ✅ Skips already installed nodes/models (fast!)

**Then restart ComfyUI** (custom nodes require restart):
- **RunPod Pods:** Stop and start pod from console
- **Local:** `docker compose restart`

### config.yml Format Reference

#### Models Section

```yaml
models:
  - url: https://huggingface.co/model.safetensors
    destination: checkpoints  # Where to place the model
    optional: false            # Skip if download fails?

  - url: https://civitai.com/api/download/models/123456
    destination: loras
    optional: true
```

**Supported destinations:**
- `checkpoints` - Main model checkpoints
- `vae` - VAE models
- `loras` - LoRA models
- `controlnet` - ControlNet models
- `clip_vision` - CLIP vision models
- `embeddings` - Text embeddings
- `upscale_models` - Upscaler models
- `diffusion_models` - Diffusion models
- `text_encoders` - Text encoder models

#### Custom Nodes Section

```yaml
nodes:
  - url: https://github.com/user/repo.git
    version: latest     # Latest stable release (tag)

  - url: https://github.com/user/repo.git
    version: nightly    # Latest commit (bleeding edge)

  - url: https://github.com/user/repo.git
    version: v1.2.3     # Specific tag

  - url: https://github.com/user/repo.git
    version: abc1234    # Specific commit hash

  - url: https://github.com/user/repo.git
    version: main       # Specific branch
```

**Version options:**
- `latest` - Latest stable release tag (recommended)
- `nightly` - Latest commit on default branch
- `v1.2.3` - Specific version tag
- `abc1234` - Specific commit hash
- `main` - Track a specific branch

### Fast Warm Starts (SHA Caching)

The container uses SHA256 hashing to detect config changes:

1. **First run:** Calculates SHA of `config.yml`, installs everything, stores SHA
2. **Subsequent runs:** Compares current SHA with stored SHA
3. **If match:** Skips all downloads/installs (seconds instead of minutes!)
4. **If different:** Applies updates and updates SHA

**SHA file locations:**
- RunPod: `/runpod-volume/.config-sha256`
- Local: `/workspace/.config-sha256`

**Force reinstall:**
```bash
rm /runpod-volume/.config-sha256  # RunPod
rm /workspace/.config-sha256      # Local
```

This dramatically improves RunPod Endpoint cold start performance!

---

## Local Development

### Environment Variables

Optional: Enable auto-updates or mount existing models.

```bash
cp .env.example .env
# Edit .env file
```

**Auto-Update:**
```bash
AUTO_UPDATE=true  # Update ComfyUI on startup
```

**Models Directory:**
```bash
MODELS_PATH=/path/to/existing/models  # Mount existing models
```

**Jupyter Password:**
```bash
JUPYTER_PASSWORD=your_secure_password  # Enable password protection
```

If not set, Jupyter Lab is accessible without authentication (default for local development).

### Workflow Development

#### 1. Design in ComfyUI

Open http://localhost:8188 and create your workflow visually.

#### 2. Export for API

- Enable Dev Mode: Settings → Dev Mode
- Save workflow: Save (API Format)
- Save to `workflows/my_workflow.json`

#### 3. Test via API

```bash
curl -X POST http://localhost:8000/runsync \
  -H "Content-Type: application/json" \
  -d @examples/example_request.json
```

Or with Python:

```python
import requests
import json

with open('examples/example_request.json') as f:
    response = requests.post('http://localhost:8000/runsync', json=json.load(f))

print(response.json())
```

#### 4. Deploy to RunPod

```bash
./deploy.sh
```

Same workflows work immediately in production!

### Common Commands

```bash
# Start services (with logs)
docker compose up

# Start in background
docker compose up -d
docker compose logs -f   # View logs

# Stop services
docker compose down

# Rebuild after changes
docker compose up --build

# Test locally without Docker
python examples/test_local.py

# Build for RunPod
./build.sh

# Deploy to production
./deploy.sh
```

---

## Architecture

### Volume-First Design

**Container:** Minimal shell (~8.7GB) with CUDA runtime + system dependencies only
**Volume:** All Python packages, PyTorch, ComfyUI, models, custom nodes (persistent)

**Why?**
- ✅ No wasted disk space from package duplication
- ✅ True persistence across container rebuilds
- ✅ Faster deployments (smaller images)
- ✅ Easy updates without image rebuilds

**How it works:**
1. Container sets `PIP_TARGET=/workspace/python-packages` (volume)
2. All packages install directly to volume using **uv** (10-100x faster than pip!)
3. Container is stateless, volume holds everything important
4. Rebuild container anytime, data persists!

### Package Manager: uv

This project uses **uv** (https://github.com/astral-sh/uv), a Rust-based pip replacement that's **10-100x faster**:

- ✅ Parallel downloads across all your bandwidth
- ✅ Resolves 166 packages in <1 second
- ✅ Installs packages in milliseconds
- ✅ Perfect for 2Gbps+ connections

Your downloads will fly at **100-200+ MB/s** instead of the old 15 MB/s with pip!

### Runtime Modes

Configure via `RUN_MODE` environment variable:

- **`development`** (default local) - ComfyUI + Handler + Jupyter Lab
- **`production`** (RunPod Pods) - ComfyUI + Handler + Jupyter Lab
- **`endpoint`** (RunPod Serverless) - ComfyUI + Handler only (skips Jupyter for fast cold starts)

### GPU Support

**Universal Image** - One image for all modern NVIDIA GPUs:
- CUDA 12.8
- PyTorch 2.9.0+cu128
- RTX 4090 (Ada, compute 8.9) ✓
- RTX 5090 (Blackwell, compute 12.0) ✓
- Future architectures supported out-of-the-box!

No architecture-specific builds needed!

### Performance

**Expected generation times on RTX 4090:**
- SD 1.5: ~5-10 seconds
- SDXL: ~20-30 seconds
- FLUX: ~90-120 seconds

RTX 5090 is 40-60% faster when available.

**Download speeds:**
- **HuggingFace:** 100-200+ MB/s (hf_transfer enabled)
- **Civitai/Others:** Parallel 8-thread chunks
- **PyPI packages:** Parallel downloads via uv

---

## API Format

### Request

```json
{
  "input": {
    "workflow": { /* ComfyUI workflow in API format */ },
    "overrides": [
      {
        "node_id": "6",
        "field": "inputs.text",
        "value": "a beautiful sunset"
      },
      {
        "node_id": "3",
        "field": "inputs.seed",
        "value": 42
      }
    ]
  }
}
```

### Response

```json
{
  "status": "success",
  "prompt_id": "abc-123",
  "execution_time": 8.32,
  "images": [
    {
      "url": "http://127.0.0.1:8188/view?filename=ComfyUI_00001.png",
      "filename": "ComfyUI_00001.png"
    }
  ]
}
```

---

## Directory Structure

```
comfy-template/
├── README.md                 # This file
├── CLAUDE.md                 # Project instructions for Claude Code
├── docker-compose.yml        # Run with: docker compose up
├── Dockerfile                # Universal GPU support (all in one!)
├── .env.example              # Configuration template
│
├── handler.py                # RunPod worker logic
├── s3_upload.py              # S3 upload module
├── requirements.txt          # Python dependencies
├── start.sh                  # Container startup script
├── entrypoint.sh             # Entrypoint script
├── test_input.json           # Local test input for RunPod SDK
│
├── build.sh                  # Build production image
├── deploy.sh                 # Deploy to Docker Hub
├── download_models.py        # Model downloader
├── install_nodes.py          # Custom nodes installer
├── apply_config.sh           # Apply config changes without restart
├── config.yml                # Unified configuration (models + nodes)
│
├── workspace/                # Persistent workspace (local dev)
│   └── ComfyUI/              # Auto-created on first run
│       ├── main.py           # ComfyUI application
│       ├── models/           # Model files
│       ├── custom_nodes/     # Custom nodes
│       └── output/           # Generated images
│
├── docs/                     # Documentation
└── examples/                 # Examples and testing
    ├── example_workflow.json
    ├── example_request.json
    └── test_local.py
```

---

## Requirements

**Local Development:**
- Docker with GPU support
- NVIDIA GPU
- NVIDIA Container Toolkit

**Production:**
- Docker Hub account
- RunPod account
- Network volume (recommended)

## Platform Support

- ✅ **Linux**: Full GPU support
- ✅ **Windows**: Full GPU support (native or WSL2)
- ⚠️ **Mac**: Works for workflow design, no GPU acceleration (use RunPod for generation)

---

## Troubleshooting

### "GPU not found"
```bash
# Test GPU access
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
```

### "Port already in use"
```bash
# Find what's using port 8188
lsof -i :8188          # Mac/Linux
netstat -ano | findstr "8188"   # Windows
```

### "Build failing"
```bash
# Clean build
docker compose build --no-cache
```

### "ComfyUI not loading" (RunPod Pods)

Check pod logs:
1. Pod details → "Logs" tab
2. Look for startup messages
3. Ensure ports 8188, 8000, 8888 exposed

### "Models downloading slowly"

The scripts use:
- ✅ **uv** for Python packages (10-100x faster)
- ✅ **hf_transfer** for HuggingFace (100-200+ MB/s)
- ✅ **8-thread parallel chunks** for Civitai

If still slow, check your network connection.

### "Custom node installation fails"

Common causes:
1. **Git URL typo** - Verify repository URL
2. **Version doesn't exist** - Check repo for valid tags
3. **Missing dependencies** - Some nodes need system packages

Check error messages for details.

---

## Examples

See `examples/` directory for:
- Sample workflows in API format
- Example API requests
- Local testing without Docker

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on:

- 🐛 **Reporting bugs**
- ✨ **Proposing features**
- 🔧 **Submitting pull requests**
- 📝 **Improving documentation**

### Quick Start for Contributors

```bash
# Fork and clone the repo
git clone https://github.com/YOUR-USERNAME/comfyui-runpod-handler.git
cd comfyui-runpod-handler

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Start development environment
docker compose up
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed instructions.

---

## Community

- **Issues**: [GitHub Issues](https://github.com/YOUR-USERNAME/comfyui-runpod-handler/issues)
- **Discussions**: [GitHub Discussions](https://github.com/YOUR-USERNAME/comfyui-runpod-handler/discussions)
- **Code of Conduct**: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Credits

- Built using [ComfyUI](https://github.com/comfyanonymous/ComfyUI) by comfyanonymous
- Package management powered by [uv](https://github.com/astral-sh/uv) by Astral
- Deployment patterns inspired by [WAN-ANIMATE](https://github.com/kijai/WAN-ANIMATE)
- RunPod serverless infrastructure by [RunPod](https://www.runpod.io/)

---

## Acknowledgments

Special thanks to all [contributors](https://github.com/YOUR-USERNAME/comfyui-runpod-handler/graphs/contributors) who have helped improve this project!
