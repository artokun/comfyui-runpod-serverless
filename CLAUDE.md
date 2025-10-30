# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

RunPod serverless worker that executes ComfyUI workflows via API. Handler bridges RunPod and ComfyUI, queues prompts, polls for completion, returns image URLs (optionally uploads to S3).

## Commands

```bash
# Local development
docker compose up                    # Start ComfyUI + handler
python examples/test_local.py        # Test without Docker

# Model management
python download_models.py            # Download models from models.txt
python download_models.py --dry-run  # Preview what will download

# Custom nodes
python install_nodes.py              # Install nodes from nodes.txt
python install_nodes.py --dry-run    # Preview what will install

# Deploy to RunPod
./deploy.sh ada                      # RTX 4090
./deploy.sh blackwell                # RTX 5090/6000 Pro

# Advanced
./build.sh --arch ada --push         # Build and push manually
```

Access locally: http://localhost:8188 (ComfyUI UI), http://localhost:8000 (API)

## Architecture

**Single Dockerfile with auto-install**: ComfyUI clones to `./ComfyUI` on first run. Models and custom nodes auto-install from `models.txt` and `nodes.txt` if configured. Persistent across rebuilds.

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
- **download_models.py** - Automated model downloader (parses models.txt)
- **install_nodes.py** - Custom node installer with version control (parses nodes.txt)
- **models.txt** - Model download config (URL -> destination format)
- **nodes.txt** - Custom nodes install config (git_url @ version format)
- **start.sh** - Container startup (auto-installs ComfyUI, nodes, models, starts services)
- **build.sh** - Multi-arch build script (targets production mode)
- **deploy.sh** - Wrapper for build + push
- **examples/test_local.py** - Test script simulating RunPod

## Model Management

Edit `models.txt` to configure automatic model downloads:

```
# Format: URL -> destination [flags]
https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors -> vae
https://civitai.com/api/download/models/12345 -> checkpoints /optional
```

Valid destinations: `checkpoints`, `vae`, `loras`, `controlnet`, `clip_vision`, `embeddings`, `upscale_models`, `diffusion_models`, `text_encoders`, etc.

Models download automatically on container start if missing. Use `/optional` or `/skip` flags to mark as skippable.

## Custom Nodes

Edit `nodes.txt` to configure automatic custom node installation:

```
# Format: git_url @ version
https://github.com/ltdrdata/ComfyUI-Manager.git @ latest
https://github.com/kijai/ComfyUI-KJNodes.git @ v1.0.5
https://github.com/cubiq/ComfyUI_IPAdapter_plus.git @ nightly
```

Version specifiers: `latest` (stable release), `nightly` (latest commit), `v1.2.3` (specific tag), commit hash, or branch name.

Nodes install automatically on container start if missing. Includes dependency installation.

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
- **Models not downloading**: Check `models.txt` format and network connectivity.
- **Custom nodes failing**: Check `nodes.txt` format, git URL validity, version exists.
- **Missing node in workflow**: Install required custom node via `nodes.txt`.
