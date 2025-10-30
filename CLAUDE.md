# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

RunPod serverless worker that executes ComfyUI workflows via API. Handler bridges RunPod and ComfyUI, queues prompts, polls for completion, returns image URLs (optionally uploads to S3).

## Commands

```bash
# Local development
docker compose up                    # Start ComfyUI + handler
python examples/test_local.py        # Test without Docker

# Configuration management
python download_models.py            # Download models from config.yml
python download_models.py --dry-run  # Preview what will download
python install_nodes.py              # Install nodes from config.yml
python install_nodes.py --dry-run    # Preview what will install

# Deploy to RunPod
./deploy.sh ada                      # RTX 4090
./deploy.sh blackwell                # RTX 5090/6000 Pro

# Advanced
./build.sh --arch ada --push         # Build and push manually
```

Access locally: http://localhost:8188 (ComfyUI UI), http://localhost:8000 (API)

## Architecture

**Single Dockerfile with auto-install**: ComfyUI clones to `./ComfyUI` on first run. Models and custom nodes auto-install from `config.yml` if configured. Persistent across rebuilds.

**Handler flow** (handler.py):
1. Receives job from RunPod
2. Applies `overrides` to workflow nodes (dot-notation: `"inputs.text"` → `workflow["6"]["inputs"]["text"]`)
3. POSTs to `/prompt`, polls `/history/{id}` via WebSocket or HTTP until done
4. Extracts images, optionally uploads to S3, returns URLs

**GPU variants**:
- `ada`: CUDA 11.8, PyTorch 2.1.0 (RTX 4090, default)
- `blackwell`: CUDA 12.4, PyTorch 2.5.0 (RTX 5090/6000 Pro)

**Performance optimizations**: Includes SageAttention v2.2.0, Triton, hf_transfer for faster downloads.

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

Edit `config.yml` to configure models and custom nodes:

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
