# ComfyUI + RunPod Handler

Run ComfyUI locally with a RunPod-compatible API handler, then deploy to RunPod serverless.

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

When you're ready for production:

```bash
./deploy.sh ada          # RTX 4090
./deploy.sh blackwell    # RTX 5090/6000 Pro
```

Then configure your RunPod endpoint with: `alongbottom/comfyui-runpod:ada`

Same workflows, same API format, just runs on RunPod's GPUs!

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

**Model Management:**
Edit `models.txt` to specify which models to download automatically:
```
# Simple format: URL -> destination
https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors -> vae
```
Models download automatically on container start if missing.

**Custom Nodes:**
Edit `nodes.txt` to specify which custom nodes to install:
```
# Simple format: URL @ version
https://github.com/ltdrdata/ComfyUI-Manager.git @ latest
https://github.com/kijai/ComfyUI-KJNodes.git @ v1.0.5
```
Nodes install automatically on container start with full version control.

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
├── models.txt                # Model download configuration
├── nodes.txt                 # Custom nodes configuration
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

- **[Custom Nodes Guide](docs/CUSTOM_NODES.md)** - Automatic custom nodes installation with version control
- **[Model Management Guide](docs/MODEL_MANAGEMENT.md)** - Automatic model downloads
- **[Docker Compose Guide](docs/DOCKER_COMPOSE.md)** - Detailed local development guide
- **[External ComfyUI](docs/EXTERNAL_COMFYUI.md)** - Mount ComfyUI from filesystem (updateable)
- **[RunPod Deployment](docs/RUNPOD_DEPLOYMENT.md)** - Deploy to production
- **[RunPod Configuration](docs/RUNPOD_CONFIG.md)** - Endpoint settings reference
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

Issues and PRs welcome! This project uses patterns from production ComfyUI installers - see [docs/INSTALLER_PATTERNS.md](docs/INSTALLER_PATTERNS.md).

## License

MIT

## Credits

Built using ComfyUI by comfyanonymous. Deployment patterns inspired by WAN-ANIMATE and other production installers.
