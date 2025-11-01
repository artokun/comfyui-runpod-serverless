# ComfyUI RunPod Handler

[![CI](https://github.com/artokun/comfyui-runpod-serverless/actions/workflows/ci.yml/badge.svg)](https://github.com/artokun/comfyui-runpod-serverless/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)

Run ComfyUI locally with a RunPod-compatible API handler, then deploy to RunPod serverless.

> **Open Source**: This project is open source and welcomes contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Quick Start

```bash
docker compose up
```

**First run:** The initial startup takes 15-20 minutes (downloads ComfyUI, installs custom nodes from `config.yml`, downloads models). Subsequent runs with the same config are ~30 seconds thanks to SHA-based caching.

Open your browser:
- **http://localhost:8188** - ComfyUI interface (design workflows)
- **http://localhost:8000** - API endpoint (test requests)
- **http://localhost:8888** - Jupyter Lab (edit config, manage files)

Press `Ctrl+C` to stop.

## What You Get

✅ ComfyUI auto-installs on first run (updateable, persistent)
✅ Full web interface for workflow design
✅ Jupyter Lab for config editing and file management
✅ RunPod-compatible API handler
✅ Same workflow format locally and in production
✅ Universal GPU support (RTX 4090, RTX 5090, and beyond)
✅ Fast warm starts with SHA-based config caching
✅ Streaming logs in your terminal
✅ Works on Mac, Linux, Windows

## Deploy to RunPod

**Choose Your Deployment Type:**

### 🚀 Serverless Endpoints (Production)
Auto-scaling API deployment with scale-to-zero cost savings:
- **[RunPod Serverless Guide →](RUNPOD_ENDPOINTS.md)**
- Container Image: `artokun/comfyui-runpod:latest`
- Pay per execution, auto-scaling
- Perfect for production APIs

### 🔧 GPU Pods (Development)
Interactive development with Jupyter and SSH access:
- **[RunPod Pods Guide →](RUNPOD_PODS.md)**
- Container Image: `artokun/comfyui-runpod:latest`
- Pay per hour, full control
- Perfect for testing and workflow design
- Includes Jupyter Lab on port 8888

**Unified Image (All Modern GPUs):**
- Single image with PyTorch 2.9.0 + CUDA 12.8
- Supports RTX 4090 (Ada), RTX 5090 (Blackwell), and beyond
- No separate tags needed - one image for all!

Images auto-deploy via GitHub Actions on every release.

### Manual Deploy (Contributors)

```bash
./deploy.sh          # Build and push unified image
```

## Configuration

Optional: Enable auto-updates or mount existing models.

```bash
cp .env.example .env
# Edit .env file
```

**Auto-Update:**
Set `AUTO_UPDATE=true` in `.env` to automatically update ComfyUI on startup.

**Models Directory:**
Uncomment and set `MODELS_PATH` in `.env` to mount your existing models.

**Jupyter Password (Optional):**
Set `JUPYTER_PASSWORD` in `.env` to enable password protection for Jupyter Lab:
```bash
JUPYTER_PASSWORD=your_secure_password
```
If not set, Jupyter Lab is accessible without authentication (default for local development).

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
- ✅ **Lightning fast downloads** - hf_transfer acceleration for HuggingFace (100-200+ MB/s on gigabit)
- ✅ **Parallel chunk downloads** - 8-thread acceleration for Civitai and other sources
- ✅ **Lightweight default** - Fast first build (4GB vs 30GB+)
- ✅ **Advanced example** - Complete WAN Animate setup available

**Cloud Deployment (RunPod/AWS/GCP):**
Override config via environment variable without rebuilding. **We recommend base64 encoding** to avoid formatting issues:

**Method 1: Base64 Encoded (Recommended)**
1. Prepare your `config.yml` file
2. Encode at **[https://www.base64encode.org/](https://www.base64encode.org/)** (copy file, paste, ENCODE)
3. Set in RunPod:
```bash
CONFIG_YML=bW9kZWxzOgogIC0gdXJsOiBodHRwczovL2h1Z2dpbmdmYWNlLmNvLy4uLi9tb2RlbC5zYWZldGVuc29ycwogICAgZGVzdGluYXRpb246IGNoZWNrcG9pbnRzCm5vZGVzOgogIC0gdXJsOiBodHRwczovL2dpdGh1Yi5jb20vLi4uL25vZGUuZ2l0CiAgICB2ZXJzaW9uOiBsYXRlc3Q=
```

**Method 2: Edit via Jupyter** (for live editing in Pods)
- Access Jupyter at port 8888 (no password)
- Navigate to `/workspace/config.yml` and edit
- Run `apply_config.sh` to apply changes instantly:
  ```bash
  cd /app && ./apply_config.sh
  ```
- See **[CONFIG_MANAGEMENT.md](CONFIG_MANAGEMENT.md)** for detailed guide

**Method 3: Plain YAML** (local only - has newline issues in RunPod)
```bash
CONFIG_YML=models:
  - url: https://huggingface.co/.../model.safetensors
    destination: checkpoints
```

Container automatically detects, decodes, and validates the config!

**Quick Apply Script:**

After editing `config.yml`, run `apply_config.sh` to instantly download models and install nodes without restarting:

```bash
# In Jupyter terminal or local terminal
cd /app
./apply_config.sh
```

See **[CONFIG_MANAGEMENT.md](CONFIG_MANAGEMENT.md)** for the complete configuration management guide.

## Directory Structure

```
comfy-template/
├── README.md                 # This file
├── CLAUDE.md                 # Project instructions for Claude Code
├── CONFIG_MANAGEMENT.md      # Configuration management guide
├── docker-compose.yml        # Run with: docker compose up
├── Dockerfile                # Single Dockerfile (universal GPU support)
├── .env.example              # Configuration template
│
├── handler.py                # RunPod worker logic
├── s3_upload.py              # S3 upload module
├── requirements.txt          # Python dependencies
├── start.sh                  # Container startup script (auto-install/update)
├── test_input.json           # Local test input for RunPod SDK
│
├── build.sh                  # Build production image
├── deploy.sh                 # Deploy to Docker Hub
├── download_models.py        # Model downloader (auto-run by start.sh)
├── install_nodes.py          # Custom nodes installer (auto-run by start.sh)
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
│   └── ...                   # Various guides
│
└── examples/                 # Examples and testing
    ├── example_workflow.json # Sample workflow
    ├── example_request.json  # Sample API request
    └── test_local.py         # Test without Docker
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
./build.sh

# Deploy to production
./deploy.sh
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
./deploy.sh
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

**Universal Image** - Supports all modern NVIDIA GPUs:
- CUDA 12.8
- PyTorch 2.9.0+cu128
- RTX 4090 (Ada, compute 8.9) ✓
- RTX 5090 (Blackwell, compute 12.0) ✓
- Future architectures supported out-of-the-box

Single unified image eliminates architecture-specific builds!

## Performance

**Expected generation times on RTX 4090:**
- SD 1.5: ~5-10 seconds
- SDXL: ~20-30 seconds
- FLUX: ~90-120 seconds

Times vary based on resolution, steps, and model complexity.

**Warm Start Optimization:**

The container uses SHA256 hashing to detect config changes:
- **First start**: Downloads models, installs nodes, stores config SHA (~2-5 minutes depending on config)
- **Warm starts (config unchanged)**: Skips all downloads/installs entirely (~5-10 seconds)
- **Config changed**: Only applies updates, then updates SHA

This dramatically improves RunPod Endpoint performance where warm start time directly impacts response latency. The SHA file (`.config-sha256`) is stored on persistent volume.

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
