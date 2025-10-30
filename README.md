# ComfyUI RunPod Handler

[![CI](https://github.com/YOUR-USERNAME/comfyui-runpod-handler/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR-USERNAME/comfyui-runpod-handler/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)

Run ComfyUI locally with a RunPod-compatible API handler, then deploy to RunPod serverless.

> **Open Source**: This project is open source and welcomes contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Quick Start

```bash
docker compose up
```

Open your browser:
- **http://localhost:8188** - ComfyUI interface (design workflows)
- **http://localhost:8000** - API endpoint (test requests)

Press `Ctrl+C` to stop.

## What You Get

✅ ComfyUI auto-installs on first run (updateable, persistent)
✅ Full web interface for workflow design
✅ RunPod-compatible API handler
✅ Same workflow format locally and in production
✅ Streaming logs in your terminal
✅ Works on Mac, Linux, Windows

## Deploy to RunPod

**Choose Your Deployment Type:**

### 🚀 Serverless Endpoints (Production)
Auto-scaling API deployment with scale-to-zero cost savings:
- **[RunPod Serverless Quickstart →](RUNPOD_QUICKSTART.md)**
- Container Image: `artokun/comfyui-runpod-serverless:ada`
- Pay per execution, auto-scaling
- Perfect for production APIs

### 🔧 GPU Pods (Development)
Interactive development with Jupyter and SSH access:
- **[RunPod Pods Guide →](RUNPOD_PODS.md)**
- Container Image: `artokun/comfyui-runpod-serverless:ada`
- Pay per hour, full control
- Perfect for testing and workflow design

**GPU Options:**
- `ada` tag - RTX 4090 (CUDA 11.8, PyTorch 2.1.0)
- `blackwell` tag - RTX 5090/6000 Pro (CUDA 12.4, PyTorch 2.5.0)

Images auto-deploy via GitHub Actions on every release.

### Manual Deploy (Contributors)

```bash
./deploy.sh ada          # Build and push RTX 4090 image
./deploy.sh blackwell    # Build and push RTX 5090 image
```

## Configuration

Optional: Customize GPU architecture, enable auto-updates, or mount existing models.

```bash
cp .env.example .env
# Edit .env file
```

**GPU Architecture:**
- `ada` - RTX 4090 (CUDA 11.8, PyTorch 2.1.0) - default
- `blackwell` - RTX 5090/6000 Pro (CUDA 12.4, PyTorch 2.5.0) - 40-60% faster

**Auto-Update:**
Set `AUTO_UPDATE=true` in `.env` to automatically update ComfyUI on startup.

**Models Directory:**
Uncomment and set `MODELS_PATH` in `.env` to mount your existing models.

**How It Works:**
- ComfyUI is auto-cloned to `./ComfyUI` on first run
- Persistent across container rebuilds
- Update anytime: `cd ComfyUI && git pull`
- Or enable auto-updates with `AUTO_UPDATE=true`

**Models & Custom Nodes (No Rebuild Needed!):**

The default `config.yml` includes **SD 1.5 + ComfyUI Manager** for fast setup (~4GB model).

For advanced setups (WAN Animate 2.2, SDXL, etc.), copy `config.example.yml`:

```bash
# Option 1: Use advanced example (WAN Animate 2.2 - 11 models, 20+ nodes)
cp config.example.yml config.yml
docker compose restart

# Option 2: Edit default config manually
nano config.yml
docker compose restart

# Option 3: Mix and match from example
# Pick specific models/nodes from config.example.yml
```

**Configuration Files:**
- `config.yml` - Active config (lightweight SD 1.5 default)
- `config.example.yml` - Advanced reference (complete WAN Animate 2.2 setup)

**Key Features:**
- ✅ **Edit anytime** - No Docker rebuild needed
- ✅ **Smart caching** - Only downloads new/missing models
- ✅ **Lightning fast downloads** - hf_transfer acceleration (100-200 MB/s on gigabit)
- ✅ **Lightweight default** - Fast first build (4GB vs 30GB+)
- ✅ **Advanced example** - Complete WAN Animate setup available

**Cloud Deployment (RunPod/AWS/GCP):**
Override config via environment variable without rebuilding:
```bash
# In RunPod template environment variables:
CONFIG_YML=models:
  - url: https://huggingface.co/.../model.safetensors
    destination: checkpoints
nodes:
  - url: https://github.com/.../node.git
    version: latest
```

This writes the config on startup - perfect for cloud deployments!

## Directory Structure

```
comfy-template/
├── README.md                 # This file
├── docker-compose.yml        # Run with: docker compose up
├── Dockerfile                # Single Dockerfile (local dev + production)
├── .env.example              # Configuration template
│
├── handler.py                # RunPod worker logic
├── requirements.txt          # Python dependencies
├── start.sh                  # Container startup script (auto-install/update)
│
├── build.sh                  # Build production image
├── deploy.sh                 # Deploy to Docker Hub
├── update-comfyui.sh         # Manual ComfyUI update script
├── download_models.py        # Model downloader (auto-run by start.sh)
├── install_nodes.py          # Custom nodes installer (auto-run by start.sh)
├── config.yml                # Unified configuration (models + nodes)
│
├── ComfyUI/                  # Auto-created on first run
│   ├── main.py               # ComfyUI application
│   ├── models/               # Model files
│   ├── custom_nodes/         # Add custom nodes here
│   └── output → ../output    # Symlinked to project output
│
├── docs/                     # Documentation
│   ├── DOCKER_COMPOSE.md     # Docker Compose guide
│   ├── RUNPOD_DEPLOYMENT.md  # Deployment guide
│   ├── RUNPOD_CONFIG.md      # Endpoint configuration
│   ├── TESTING.md            # Testing workflows
│   └── INSTALLER_PATTERNS.md # Implementation reference
│
├── examples/                 # Examples and testing
│   ├── example_workflow.json # Sample workflow
│   ├── example_request.json  # Sample API request
│   └── test_local.py         # Test without Docker
│
├── models/                   # Model utilities
│   └── download_models.py    # Download models script
│
├── output/                   # Generated images (linked to ComfyUI)
└── workflows/                # Your workflows (linked to ComfyUI)
```

## Common Commands

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

# Test locally without Docker (requires ComfyUI running)
python examples/test_local.py

# Build for RunPod
./build.sh ada

# Deploy to production
./deploy.sh ada
```

## Workflow Development

### 1. Design Workflow
Open http://localhost:8188 and create your workflow visually.

### 2. Export for API
- Enable Dev Mode: Settings → Dev Mode
- Save workflow: Save (API Format)
- Save to `workflows/my_workflow.json`

### 3. Test via API

```bash
curl -X POST http://localhost:8000/runsync \
  -H "Content-Type: application/json" \
  -d @examples/example_request.json
```

Or with Python:

```python
import requests

with open('examples/example_request.json') as f:
    response = requests.post('http://localhost:8000/runsync', json=json.load(f))

print(response.json())
```

### 4. Deploy to RunPod

```bash
./deploy.sh ada
```

Configure in RunPod console - same workflows work immediately!

## Documentation

### Quick Start
- **[RunPod Quickstart](RUNPOD_QUICKSTART.md)** ⚡ - Deploy to RunPod in 5 minutes

### Deployment
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Overview of all deployment options
- **[RunPod Deployment](docs/RUNPOD_DEPLOYMENT.md)** - Complete RunPod setup
- **[Auto-Deploy](docs/AUTO_DEPLOY.md)** - Automated CI/CD with GitHub Actions
- **[Docker Hub Setup](docs/DOCKER_HUB_SETUP.md)** - For forkers only

### Configuration
- **[Model Management](docs/MODEL_MANAGEMENT.md)** - Automatic model downloads
- **[Custom Nodes](docs/CUSTOM_NODES.md)** - Installing custom nodes with version control
- **[Docker Compose](docs/DOCKER_COMPOSE.md)** - Local development guide

### Reference
- **[RunPod Configuration](docs/RUNPOD_CONFIG.md)** - Endpoint settings
- **[Testing Guide](docs/TESTING.md)** - Testing workflows and API
- **[Installer Patterns](docs/INSTALLER_PATTERNS.md)** - Implementation details

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

## Architecture

**Single Dockerfile with Two Targets:**

### Local Development (default target)
- Lightweight handler (~3GB image)
- ComfyUI auto-installed from filesystem
- Persistent and updateable
- Both ComfyUI UI and API handler
- Uses: `docker compose up`

### Production (production target)
- Same lightweight handler (~3GB image)
- Connects to pre-installed ComfyUI on RunPod network volume
- Optimized for RunPod serverless
- Uses: `./deploy.sh ada` (automatically targets production)

**Both use the same architecture** - handler connects to ComfyUI over HTTP. The only differences are:
1. CMD: Local runs `start.sh` (auto-installs ComfyUI), Production runs `handler.py` directly
2. ComfyUI location: Local filesystem vs RunPod network volume

## GPU Support

**Ada (RTX 4090)** - Default:
- CUDA 11.8
- PyTorch 2.1.0+cu118
- Tested and stable
- Great price/performance

**Blackwell (RTX 5090/6000 Pro)**:
- CUDA 12.4
- PyTorch 2.5.0+cu124
- 40-60% faster (when available)
- Premium pricing

Change architecture in `.env` file.

## Performance

**Expected generation times on RTX 4090:**
- SD 1.5: ~5-10 seconds
- SDXL: ~20-30 seconds
- FLUX: ~90-120 seconds

Times vary based on resolution, steps, and model complexity.

## Requirements

**Local Development:**
- Docker with GPU support
- NVIDIA GPU
- NVIDIA Container Toolkit

**Production:**
- Docker Hub account
- RunPod account
- Network volume with ComfyUI installed

## Platform Support

- ✅ **Linux**: Full GPU support
- ✅ **Windows**: Full GPU support (native or WSL2)
- ⚠️ **Mac**: Works for workflow design, no GPU acceleration (use RunPod for generation)

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

See [docs/DOCKER_COMPOSE.md](docs/DOCKER_COMPOSE.md) for more troubleshooting.

## Examples

See `examples/` directory for:
- Sample workflows in API format
- Example API requests
- Local testing without Docker

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details on:

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

## Community

- **Issues**: [GitHub Issues](https://github.com/YOUR-USERNAME/comfyui-runpod-handler/issues)
- **Discussions**: [GitHub Discussions](https://github.com/YOUR-USERNAME/comfyui-runpod-handler/discussions)
- **Code of Conduct**: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits

- Built using [ComfyUI](https://github.com/comfyanonymous/ComfyUI) by comfyanonymous
- Deployment patterns inspired by [WAN-ANIMATE](https://github.com/kijai/WAN-ANIMATE) and other production installers
- RunPod serverless infrastructure by [RunPod](https://www.runpod.io/)

## Acknowledgments

Special thanks to all [contributors](https://github.com/YOUR-USERNAME/comfyui-runpod-handler/graphs/contributors) who have helped improve this project!
