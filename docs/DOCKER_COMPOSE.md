# Docker Compose Quick Start

The easiest way to run ComfyUI + RunPod Handler on Mac, Linux, or Windows.

## Quick Start (3 Commands)

```bash
# 1. Optional: Configure (skip if using default settings)
cp .env.example .env
# Edit .env if you want to change GPU_ARCH or mount models

# 2. Start everything
docker compose up

# 3. Open browser
# http://localhost:8188 - ComfyUI interface
# http://localhost:8000 - API endpoint
```

That's it! You'll see streaming logs in your terminal.

## What You Get

- ✅ **ComfyUI** on port 8188 - Design workflows visually
- ✅ **RunPod API** on port 8000 - Test your API requests
- ✅ **GPU acceleration** - Automatic GPU detection
- ✅ **Auto-restart** - Container restarts if it crashes
- ✅ **Streaming logs** - See everything in real-time

## Usage

### Start (with logs streaming)
```bash
docker compose up
```

Press `Ctrl+C` to stop.

### Start (in background)
```bash
docker compose up -d
```

### View logs
```bash
docker compose logs -f
```

### Stop
```bash
docker compose down
```

### Rebuild (after code changes)
```bash
docker compose up --build
```

### Restart
```bash
docker compose restart
```

## Configuration

### GPU Architecture

Edit `.env` file:
```bash
# For RTX 4090 (default)
GPU_ARCH=ada

# For RTX 5090 / RTX 6000 Pro
GPU_ARCH=blackwell
```

Or set inline:
```bash
GPU_ARCH=blackwell docker compose up
```

### Mount Models Directory

If you have models from another ComfyUI installation:

1. Edit `.env`:
```bash
# Mac
MODELS_PATH=/Users/yourname/ComfyUI/models

# Linux
MODELS_PATH=/home/yourname/ComfyUI/models

# Windows
MODELS_PATH=C:/ComfyUI/models
```

2. Edit `docker-compose.yml`, uncomment this line:
```yaml
    volumes:
      - ./output:/comfyui/output
      - ./workflows:/comfyui/user/workflows
      # Uncomment the line below:
      - ${MODELS_PATH}:/models  # <-- Uncomment this
```

3. Restart:
```bash
docker compose down
docker compose up
```

## Directory Structure

```
comfy-template/
├── output/              # Generated images (auto-created)
│   └── ComfyUI_*.png
├── workflows/           # Your workflow files (auto-created)
│   └── my_workflow.json
├── docker-compose.yml   # Docker Compose config
├── .env                 # Your configuration
└── .env.example         # Example configuration
```

## Platform-Specific Notes

### Mac (Apple Silicon)
Docker Compose works but **no GPU acceleration** (Docker doesn't support Metal).
Use for workflow design only, then deploy to RunPod for GPU generation.

### Mac (Intel with eGPU)
Should work with NVIDIA eGPU if NVIDIA Container Toolkit is installed.

### Linux
Works perfectly with native NVIDIA drivers.

### Windows (WSL2)
```bash
# From WSL2 terminal
cd /mnt/c/Users/yourname/code/comfy-template
docker compose up
```

### Windows (PowerShell/CMD)
```powershell
# From Windows terminal
cd C:\Users\yourname\code\comfy-template
docker compose up
```

## Common Commands

### Check if container is running
```bash
docker compose ps
```

### Execute command inside container
```bash
docker compose exec comfyui bash
```

### View GPU usage inside container
```bash
docker compose exec comfyui nvidia-smi
```

### Clean everything (remove volumes)
```bash
docker compose down -v
```

### Update to latest code
```bash
git pull
docker compose up --build
```

## Logs

### View all logs
```bash
docker compose logs
```

### View last 50 lines
```bash
docker compose logs --tail=50
```

### Follow logs (streaming)
```bash
docker compose logs -f
```

### View only ComfyUI startup
```bash
docker compose logs | grep "ComfyUI"
```

## Troubleshooting

### "Error: GPU not found"
```bash
# Check if NVIDIA drivers work
nvidia-smi

# Check if Docker can access GPU
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi

# If that fails, install NVIDIA Container Toolkit
```

### "Port 8188 already in use"
```bash
# Find what's using the port
lsof -i :8188  # Mac/Linux
netstat -ano | findstr "8188"  # Windows

# Stop that process or change docker-compose.yml ports
```

### "Cannot find GPU_ARCH"
Create `.env` file:
```bash
cp .env.example .env
```

### "Build failing"
```bash
# Clean build cache
docker compose build --no-cache

# Remove old images
docker system prune -a
```

### "Out of disk space"
```bash
# Check Docker disk usage
docker system df

# Clean up
docker system prune -a --volumes
```

## Testing the API

### Simple test (Mac/Linux)
```bash
curl -X POST http://localhost:8000/runsync \
  -H "Content-Type: application/json" \
  -d @example_request.json
```

### With jq for pretty output
```bash
curl -X POST http://localhost:8000/runsync \
  -H "Content-Type: application/json" \
  -d @example_request.json | jq
```

### Python example
```python
import requests
import json

with open('example_request.json') as f:
    payload = json.load(f)

response = requests.post('http://localhost:8000/runsync', json=payload)
print(response.json())
```

## Development Workflow

### 1. Start services
```bash
docker compose up
```

### 2. Design in ComfyUI
- Open http://localhost:8188
- Create your workflow
- Enable Dev Mode (Settings → Dev Mode)
- Save as API format to `workflows/my_workflow.json`

### 3. Test via API
```bash
# Edit example_request.json to use your workflow
# Then test:
curl -X POST http://localhost:8000/runsync \
  -H "Content-Type: application/json" \
  -d @example_request.json
```

### 4. Iterate
- Modify workflow in ComfyUI
- Re-export
- Test again
- Repeat!

### 5. Deploy to RunPod
```bash
# Build production image
./build.sh ada  # or build.ps1 on Windows

# Deploy
./deploy.sh ada  # or deploy.ps1 on Windows

# Use in RunPod: alongbottom/comfyui-runpod:ada
```

## Advanced Usage

### Override ports
```bash
# Use different ports
docker compose up -e COMFYUI_PORT=9000 -e API_PORT=9001
```

Edit `docker-compose.yml`:
```yaml
ports:
  - "${COMFYUI_PORT:-8188}:8188"
  - "${API_PORT:-8000}:8000"
```

### Multiple environments
```bash
# Create .env.ada for RTX 4090
GPU_ARCH=ada

# Create .env.blackwell for RTX 5090
GPU_ARCH=blackwell

# Use specific env file
docker compose --env-file .env.ada up
docker compose --env-file .env.blackwell up
```

### Run in production mode
```bash
# No auto-restart, run once
docker compose up --no-recreate
```

## Comparison with PowerShell Script

| Feature | docker compose up | quickstart.ps1 |
|---------|-------------------|----------------|
| Cross-platform | ✅ Mac/Linux/Windows | ❌ Windows only |
| Streaming logs | ✅ Built-in | ⚠️ Need -Detached |
| Configuration | ✅ .env file | ⚠️ Command args |
| Auto-restart | ✅ Yes | ❌ No |
| One command | ✅ Yes | ✅ Yes |
| Background mode | ✅ -d flag | ✅ -Detached |

## Why Docker Compose?

✅ **Cross-platform** - Same commands on Mac, Linux, Windows
✅ **Simple** - One command to start everything
✅ **Logs** - Streaming logs by default
✅ **Standard** - Docker Compose is industry standard
✅ **Declarative** - Configuration in YAML, not scripts
✅ **Powerful** - Easy to extend with more services

## Next Steps

1. ✅ Run `docker compose up`
2. 🎨 Open http://localhost:8188
3. 💾 Design and export workflows
4. 🧪 Test via http://localhost:8000
5. 🚀 Deploy to RunPod when ready

Same code, same workflows, works everywhere!
