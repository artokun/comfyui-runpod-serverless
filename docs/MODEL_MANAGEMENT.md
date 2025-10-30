# Model Management Guide

Automatically download and manage ComfyUI models using a simple declarative format.

## Quick Start

1. **Edit `models.txt`** - Uncomment models you want to download:

```
# Uncomment models you need:
https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors -> vae
https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors -> checkpoints
```

2. **Start container** - Models download automatically:

```bash
docker compose up
```

That's it! Models are downloaded on container start if they don't already exist.

## Format

Simple syntax: `URL -> destination`

```
<url> -> <destination> [/optional]
```

### Components:

- **URL**: Direct download link (HuggingFace, Civitai, direct URLs)
- **→**: Separator (arrow)
- **destination**: Model directory (see valid destinations below)
- **/optional**: Flag to skip if download fails (optional)

### Examples:

```
# Required model (fails if download fails)
https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors -> vae

# Optional model (continues if download fails)
https://example.com/optional-lora.safetensors -> loras /optional

# Civitai model
https://civitai.com/api/download/models/130072 -> checkpoints
```

## Valid Destinations

Models are organized by type in ComfyUI:

| Destination | Description | Examples |
|------------|-------------|----------|
| `checkpoints` | Base models (SD, SDXL, etc.) | .safetensors, .ckpt |
| `clip` | CLIP models | CLIP text encoders |
| `clip_vision` | CLIP vision models | CLIP image encoders |
| `configs` | Configuration files | .yaml, .json |
| `controlnet` | ControlNet models | Depth, pose, canny |
| `diffusion_models` | Diffusion models | Flux, AnimateDiff |
| `embeddings` | Textual inversions | .pt, .safetensors |
| `loras` | LoRA models | Style LoRAs, training LoRAs |
| `upscale_models` | Upscaling models | ESRGAN, RealESRGAN |
| `vae` | VAE models | sdxl_vae, sd-vae-ft |
| `sams` | Segment Anything Models | SAM, SAM2 |
| `detection` | Detection models | YOLO, pose detection |
| `text_encoders` | Text encoder models | T5, CLIP |
| `unet` | UNet models | Diffusion UNets |
| `style_models` | Style transfer models | Style adapters |
| `hypernetworks` | Hypernetwork models | Training hypernetworks |

## Supported URL Types

### HuggingFace URLs

```
https://huggingface.co/username/repo/resolve/main/model.safetensors -> checkpoints
```

**Tips:**
- Use `resolve/main/` not `blob/main/`
- Add `?download=true` if needed
- Works with private repos if you set HF_TOKEN

### Civitai URLs

```
https://civitai.com/api/download/models/MODEL_ID -> checkpoints
```

**Tips:**
- Get model ID from the Civitai page
- Use the API endpoint, not the web page URL
- May require API key for some models

### Direct URLs

```
https://example.com/path/to/model.safetensors -> loras
```

**Tips:**
- Must be a direct download link
- Should end with valid model extension
- Must support HTTP GET requests

## Manual Download Testing

Test your models.txt before running the container:

```bash
# Validate format only
python download_models.py --validate-only

# Dry run (show what would be downloaded)
python download_models.py --dry-run

# Download models manually
python download_models.py --verbose

# Force re-download
python download_models.py --force

# Parallel downloads (faster)
python download_models.py --parallel 4
```

## Usage Patterns

### Starter Pack (Minimal)

```
# Just SDXL essentials
https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors -> checkpoints
https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors -> vae
```

### Complete SDXL Setup

```
# Base model
https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors -> checkpoints

# Refiner
https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/resolve/main/sd_xl_refiner_1.0.safetensors -> checkpoints

# VAE
https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors -> vae

# ControlNet
https://huggingface.co/diffusers/controlnet-canny-sdxl-1.0/resolve/main/diffusion_pytorch_model.safetensors -> controlnet
```

### WAN Animate 2.2 (from example)

See the commented examples in `models.txt` for a complete WAN Animate setup.

### Custom LoRA Collection

```
# Style LoRAs
https://civitai.com/api/download/models/123456 -> loras  # Anime style
https://civitai.com/api/download/models/789012 -> loras  # Realistic style

# Training LoRAs
https://example.com/my-custom-lora.safetensors -> loras /optional
```

## Advanced Features

### Optional Models

Mark models as optional to continue if download fails:

```
https://example.com/experimental-model.safetensors -> checkpoints /optional
```

### Commenting

Comment out models you don't need:

```
# Currently not using these:
# https://huggingface.co/model1.safetensors -> checkpoints
# https://huggingface.co/model2.safetensors -> loras
```

### Organization

Group models by purpose:

```
# ============================================================================
# Base Models
# ============================================================================

https://huggingface.co/.../sd_xl_base_1.0.safetensors -> checkpoints

# ============================================================================
# Style LoRAs
# ============================================================================

https://civitai.com/api/download/models/123456 -> loras
```

## Automatic Download Behavior

### On Container Start

1. Checks if `models.txt` exists
2. Parses for active (uncommented) entries
3. Downloads missing models to appropriate directories
4. Skips existing files (use `--force` to re-download)
5. Continues even if optional models fail

### For Local Development

```bash
docker compose up
```

Models download before ComfyUI starts.

### For RunPod Deployment

Models baked into the image are downloaded during build:

```bash
./deploy.sh ada
```

Or download on first run from RunPod network volume.

## Troubleshooting

### "Invalid format" Error

Check your syntax:
```
✓ https://example.com/model.safetensors -> checkpoints
✗ https://example.com/model.safetensors->checkpoints  # Missing spaces
✗ https://example.com/model.safetensors > checkpoints  # Wrong arrow
```

### "Invalid destination" Error

Use valid ComfyUI directory names:
```
✓ -> checkpoints
✓ -> loras
✗ -> checkpoint   # Typo
✗ -> my_models    # Not a standard directory
```

### Download Fails

**Network issues:**
```bash
# Check URL is accessible
curl -I "https://example.com/model.safetensors"

# Use verbose mode for debugging
python download_models.py --verbose
```

**HuggingFace authentication:**
```bash
# Set token for private repos
export HF_TOKEN=your_token_here
python download_models.py
```

**Civitai API:**
```bash
# Some models require API key
# Add to URL: ?token=YOUR_API_KEY
https://civitai.com/api/download/models/123456?token=YOUR_KEY -> checkpoints
```

### File Permission Issues

On Linux/Mac, ensure models directory is writable:
```bash
chmod -R 755 ComfyUI/models
```

### Disk Space

Large models need space:
```bash
# Check available space
df -h ComfyUI/models

# SDXL base: ~7GB
# FLUX: ~24GB
# WAN Animate: ~30GB+
```

## Best Practices

1. **Start minimal** - Only download models you'll actually use
2. **Use comments** - Organize and document your model choices
3. **Mark experimental as optional** - Use `/optional` flag for testing
4. **Test locally first** - Validate with `--dry-run` before deploying
5. **Version control** - Track your `models.txt` in git
6. **Group by project** - Keep different model sets for different workflows

## Performance

### Download Times (approximate)

On typical broadband connection:

| Model Type | Size | Time |
|-----------|------|------|
| VAE | ~300MB | 30-60s |
| LoRA | ~100MB | 10-30s |
| SDXL Checkpoint | ~7GB | 10-20min |
| FLUX | ~24GB | 30-60min |
| WAN Animate Full | ~30GB+ | 45-90min |

### Parallel Downloads

Speed up with parallel downloads:
```bash
python download_models.py --parallel 4
```

**Note:** HuggingFace may rate-limit parallel downloads from the same IP.

## Integration with RunPod

### Option 1: Bake into Image

Uncomment models in `models.txt` and deploy:
```bash
./deploy.sh ada
```

Models download during image build and are baked in.

**Pros:**
- Instant startup on RunPod
- No network dependency

**Cons:**
- Larger image size
- Slower builds

### Option 2: Download on First Run

Leave `models.txt` commented out in image, create on RunPod volume:
```bash
# On RunPod network volume
echo "https://huggingface.co/.../model.safetensors -> checkpoints" > /runpod-volume/ComfyUI/models.txt
```

**Pros:**
- Smaller image
- Faster deploys
- Easy model updates

**Cons:**
- First run is slower
- Network dependency

## Example Workflows

### Quick SDXL Setup

```bash
# 1. Edit models.txt
nano models.txt

# 2. Uncomment SDXL lines
https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors -> checkpoints
https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors -> vae

# 3. Start
docker compose up
```

### Testing Models Locally

```bash
# Validate your models.txt
python download_models.py --validate-only

# Dry run
python download_models.py --dry-run

# Download
python download_models.py --verbose
```

### Deploying with Models

```bash
# 1. Uncomment models you need
nano models.txt

# 2. Test locally
docker compose up

# 3. Deploy to RunPod
./deploy.sh ada
```

## Summary

The model management system provides:

- ✅ **Simple declarative format** - Easy to read and edit
- ✅ **Automatic downloads** - Models fetch on container start
- ✅ **Validation** - Parse errors caught before download
- ✅ **Flexible** - Works locally and in production
- ✅ **Optional models** - Gracefully handle failures
- ✅ **Version controllable** - Track model configs in git

Edit `models.txt`, uncomment what you need, and let the system handle the rest!
