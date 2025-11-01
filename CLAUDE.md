# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

RunPod serverless worker that executes ComfyUI workflows via API. Handler bridges RunPod and ComfyUI, queues prompts, polls for completion, returns image URLs (optionally uploads to S3).

## Commands

```bash
# Local development
docker compose up                    # Start ComfyUI + handler
python examples/test_local.py        # Test without Docker

# Configuration management (NO REBUILD NEEDED!)
nano config.yml                      # Edit models/nodes
docker compose restart               # Apply changes instantly

# Advanced configuration commands
python download_models.py            # Download models from config.yml
python download_models.py --dry-run  # Preview what will download
python install_nodes.py              # Install nodes from config.yml
python install_nodes.py --dry-run    # Preview what will install

# Deploy to RunPod (works with all modern GPUs)
./deploy.sh                          # Build and push unified image

# Advanced
./build.sh --push                    # Build and push manually
```

Access locally: http://localhost:8188 (ComfyUI UI), http://localhost:8000 (API), http://localhost:8888 (Jupyter Lab)

**Local workspace**: Everything persists in `./workspace/` directory:
- `./workspace/ComfyUI/` - ComfyUI installation
- `./workspace/ComfyUI/output/` - Generated images
- `./workspace/ComfyUI/user/default/workflows/` - Saved workflows

## Architecture

**Single Dockerfile with auto-install**: ComfyUI clones to `./workspace/ComfyUI` (local) or `/runpod-volume/ComfyUI` (RunPod) on first run. Models and custom nodes auto-install from `config.yml` if configured. Fully persistent across restarts.

**Default configuration**: Minimal setup (SD 1.5 + ComfyUI Manager, ~4GB) for fast builds. Advanced setups (WAN Animate 2.2, ~30GB) available in `config.example.yml`.

**Fast warm starts (SHA-based caching)**: Container calculates SHA256 hash of `config.yml` and stores it on persistent volume (`.config-sha256`). On subsequent starts, if SHA matches, model downloads and node installations are skipped entirely for instant warm starts. Critical for RunPod Endpoint performance where every second counts. To force reinstall, delete the SHA file.

**Handler flow** (handler.py):
1. Receives job from RunPod
2. Applies `overrides` to workflow nodes (dot-notation: `"inputs.text"` → `workflow["6"]["inputs"]["text"]`)
3. POSTs to `/prompt`, polls `/history/{id}` via WebSocket or HTTP until done
4. Extracts images, optionally uploads to S3, returns URLs

**Universal GPU support**: Single unified image with PyTorch 2.9.0 + CUDA 12.8 supports all modern NVIDIA GPUs (RTX 4090, RTX 5090, and beyond)

**Performance optimizations**: Includes SageAttention v2.2.0, Triton, hf_transfer for 3-5x faster HuggingFace downloads (100-200 MB/s on gigabit connections).

**Environment detection**: Uses `/runpod-volume` in RunPod, `MODELS_PATH` locally.

## Key Files

- **handler.py** - Main worker with S3 upload support, WebSocket monitoring
- **s3_upload.py** - Optional S3 upload module (requires boto3 + BUCKET_* env vars)
- **download_models.py** - Automated model downloader (parses config.yml)
- **install_nodes.py** - Custom node installer with version control (parses config.yml)
- **config.yml** - Unified configuration for models and custom nodes
- **start.sh** - Container startup (auto-installs ComfyUI, nodes, models, starts services)
- **build.sh** - Multi-arch build script (targets production mode)
- **deploy.sh** - Wrapper for build + push
- **examples/test_local.py** - Test script simulating RunPod

## Configuration (config.yml)

**Important: config.yml is mounted as a volume - edit anytime without rebuilding!**

Edit `config.yml` to configure models and custom nodes.

**Quick Apply (No Restart):**
```bash
# After editing config.yml
cd /app
./apply_config.sh
```

This instantly downloads models and installs custom nodes without restarting the container. See **[CONFIG_MANAGEMENT.md](CONFIG_MANAGEMENT.md)** for the complete guide.

```yaml
# Models section
models:
  - url: https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors
    destination: vae
    optional: false

# Custom nodes section
nodes:
  - url: https://github.com/ltdrdata/ComfyUI-Manager.git
    version: latest
```

**Model destinations**: `checkpoints`, `vae`, `loras`, `controlnet`, `clip_vision`, `embeddings`, `upscale_models`, `diffusion_models`, `text_encoders`, etc.

**Node versions**: `latest` (stable release), `nightly` (latest commit), `v1.2.3` (specific tag), commit hash, or branch name.

Both auto-install on container start if configured. Models support `optional: true` flag.

## Runtime Configuration Override

### Method 1: Base64 Encoded (Recommended for RunPod)

**Best for**: RunPod Pods/Endpoints - avoids newline/formatting issues in environment variables.

1. Prepare your `config.yml` file with desired models and custom nodes
2. Encode it at **https://www.base64encode.org/** (copy entire file content, paste, click ENCODE)
3. Set as environment variable in RunPod:

```bash
# RunPod Environment Variables
CONFIG_YML=bW9kZWxzOgogIC0gdXJsOiBodHRwczovL2h1Z2dpbmdmYWNlLmNvLy4uLi9tb2RlbC5zYWZldGVuc29ycwogICAgZGVzdGluYXRpb246IGNoZWNrcG9pbnRzCm5vZGVzOgogIC0gdXJsOiBodHRwczovL2dpdGh1Yi5jb20vLi4uL2N1c3RvbS1ub2RlLmdpdAogICAgdmVyc2lvbjogbGF0ZXN0
```

The container automatically detects base64 encoding, decodes it, validates the format, and writes to persistent volume.

### Method 2: Plain YAML (Alternative)

For local/docker-compose deployments:

```bash
# Set CONFIG_YML environment variable with entire config content
CONFIG_YML="models:
  - url: https://huggingface.co/.../model.safetensors
    destination: checkpoints
nodes:
  - url: https://github.com/.../custom-node.git
    version: latest"
```

### Method 3: Edit via Jupyter (RunPod Pods)

**Best for**: Live editing in running Pods without redeployment.

1. Access Jupyter at port 8888 (no password by default; set `JUPYTER_PASSWORD` env to enable)
2. Navigate to `/workspace/config.yml` (Pods) or `/runpod-volume/config.yml` (Serverless)
3. Edit directly in Jupyter and save
4. Open Terminal in Jupyter and run:
   ```bash
   cd /app
   chmod +x apply_config.sh
   ./apply_config.sh
   ```
5. Restart ComfyUI if needed

See **[CONFIG_MANAGEMENT.md](CONFIG_MANAGEMENT.md)** for detailed instructions.

### Method 4: Bake into Custom Image

**Best for**: Seamless workflow-specific Pods for sharing/production.

1. Fork this repository
2. Replace `config.yml` with your custom configuration
3. Build and push: `docker build -t yourusername/comfyui-custom:latest . && docker push yourusername/comfyui-custom:latest`
4. Deploy your custom image on RunPod

**Priority order**: CONFIG_YML env (highest) → volume config.yml → baked-in /app/config.yml (fallback)

## S3 Upload (Optional)

Set environment variables to enable S3 upload:
- `BUCKET_ENDPOINT_URL` - S3 endpoint
- `BUCKET_ACCESS_KEY_ID` - Access key
- `BUCKET_SECRET_ACCESS_KEY` - Secret key
- `BUCKET_NAME` - Bucket name (default: "comfyui-outputs")

Handler automatically uploads images to S3 if configured and returns S3 URLs instead of local URLs.

## Workflow Format

Export from ComfyUI as "Save (API Format)". Nodes are string keys with `class_type` and `inputs`:

```json
{
  "6": {
    "class_type": "CLIPTextEncode",
    "inputs": { "text": "prompt", "clip": ["4", 1] }
  }
}
```

Override example: `{"node_id": "6", "field": "inputs.text", "value": "new prompt"}`

## Common Issues

- **"Node not found"**: Node ID doesn't exist in workflow. Check IDs are strings.
- **Timeout**: Increase `timeout` param or optimize workflow.
- **Connection error**: ComfyUI not running on `COMFY_API_URL`.
- **GPU not found**: Install NVIDIA Container Toolkit.
- **Models not downloading**: Check `config.yml` models section format and network connectivity.
- **Custom nodes failing**: Check `config.yml` nodes section format, git URL validity, version exists.
- **Missing node in workflow**: Install required custom node via `config.yml` nodes section.

## Contributing

This is an open-source project. Contributions welcome!

**Setup for contributors**:
```bash
pip install -r requirements-dev.txt  # Install dev dependencies
pre-commit install                   # Setup git hooks
pytest                               # Run tests
```

**Key areas**:
- Tests: `tests/` directory (pytest framework, aim for >70% coverage)
- Code style: Black, flake8, isort, mypy (enforced by pre-commit hooks)
- CI/CD: GitHub Actions (`.github/workflows/`)
- Docs: Update README.md and CLAUDE.md for user-facing changes

**Commit format**: Follow [Conventional Commits](https://www.conventionalcommits.org/)
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `test:` - Tests
- `refactor:` - Code changes without feature/fix

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.
