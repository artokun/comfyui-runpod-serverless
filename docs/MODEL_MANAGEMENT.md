# Model Management Guide

Automatically download and manage ComfyUI models using a unified YAML configuration.

## Quick Start

1. **Edit `config.yml`** - Add models you want to download:

```yaml
models:
  - url: https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors
    destination: vae
  - url: https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors
    destination: checkpoints
```

2. **Start container** - Models download automatically:

```bash
docker compose up
```

That's it! Models are downloaded on container start if they don't already exist.

## Configuration Format

Edit `config.yml` to define your models:

```yaml
models:
  - url: <download_url>
    destination: <model_directory>
    optional: <true|false>  # optional field
```

### Components:

- **url**: Direct download link (HuggingFace, Civitai, direct URLs)
- **destination**: Model directory (see valid destinations below)
- **optional**: Set to `true` to skip if download fails (defaults to `false`)

### Examples:

```yaml
models:
  # Required model (fails if download fails)
  - url: https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors
    destination: vae

  # Optional model (continues if download fails)
  - url: https://example.com/optional-lora.safetensors
    destination: loras
    optional: true

  # Civitai model
  - url: https://civitai.com/api/download/models/130072
    destination: checkpoints
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

```yaml
- url: https://huggingface.co/username/repo/resolve/main/model.safetensors
  destination: checkpoints
```

**Tips:**
- Use `resolve/main/` not `blob/main/`
- Add `?download=true` if needed
- Works with private repos if you set HF_TOKEN

### Civitai URLs

```yaml
- url: https://civitai.com/api/download/models/MODEL_ID
  destination: checkpoints
```

**Tips:**
- Get model ID from the Civitai page
- Use the API endpoint, not the web page URL
- May require API key for some models

### Direct URLs

```yaml
- url: https://example.com/path/to/model.safetensors
  destination: loras
```

**Tips:**
- Must be a direct download link
- Should end with valid model extension
- Must support HTTP GET requests

## Manual Download Testing

Test your config.yml before running the container:

```bash
# Dry run (show what would be downloaded)
python download_models.py --dry-run

# Download models manually
python download_models.py

# Force re-download
python download_models.py --force

# Use custom config location
python download_models.py --config /path/to/config.yml
```

## Usage Patterns

### Starter Pack (Minimal)

```yaml
models:
  # Just SDXL essentials
  - url: https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
    destination: checkpoints
  - url: https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors
    destination: vae
```

### Complete SDXL Setup

```yaml
models:
  # Base model
  - url: https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
    destination: checkpoints

  # Refiner
  - url: https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/resolve/main/sd_xl_refiner_1.0.safetensors
    destination: checkpoints

  # VAE
  - url: https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors
    destination: vae

  # ControlNet
  - url: https://huggingface.co/diffusers/controlnet-canny-sdxl-1.0/resolve/main/diffusion_pytorch_model.safetensors
    destination: controlnet
```

### Custom LoRA Collection

```yaml
models:
  # Style LoRAs
  - url: https://civitai.com/api/download/models/123456
    destination: loras  # Anime style

  - url: https://civitai.com/api/download/models/789012
    destination: loras  # Realistic style

  # Training LoRAs (optional)
  - url: https://example.com/my-custom-lora.safetensors
    destination: loras
    optional: true
```

## Advanced Features

### Optional Models

Mark models as optional to continue if download fails:

```yaml
models:
  - url: https://example.com/experimental-model.safetensors
    destination: checkpoints
    optional: true
```

### Organizing with Comments

Group models by purpose:

```yaml
# ============================================================================
# Base Models
# ============================================================================

models:
  - url: https://huggingface.co/.../sd_xl_base_1.0.safetensors
    destination: checkpoints

# ============================================================================
# Style LoRAs
# ============================================================================

  - url: https://civitai.com/api/download/models/123456
    destination: loras
```

## Automatic Download Behavior

### On Container Start

1. Checks if `config.yml` exists
2. Parses models section for entries
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

### "Invalid destination" Error

Use valid ComfyUI directory names:
```yaml
# Valid
- destination: checkpoints
- destination: loras

# Invalid
- destination: checkpoint   # Typo
- destination: my_models    # Not a standard directory
```

### Download Fails

**Network issues:**
```bash
# Check URL is accessible
curl -I "https://example.com/model.safetensors"

# Download manually for debugging
python download_models.py --verbose
```

**HuggingFace authentication:**
```bash
# Set token for private repos
export HF_TOKEN=your_token_here
python download_models.py
```

**Civitai API:**
```yaml
# Some models require API key
- url: https://civitai.com/api/download/models/123456?token=YOUR_KEY
  destination: checkpoints
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
3. **Mark experimental as optional** - Use `optional: true` for testing
4. **Test locally first** - Validate with `--dry-run` before deploying
5. **Version control** - Track your `config.yml` in git
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

## Integration with RunPod

### Option 1: Bake into Image

Add models to `config.yml` and deploy:
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

Create custom `config.yml` on RunPod volume:
```bash
# On RunPod network volume
cat > /runpod-volume/config.yml << EOF
models:
  - url: https://huggingface.co/.../model.safetensors
    destination: checkpoints
EOF
```

**Pros:**
- Smaller image
- Faster deploys
- Easy model updates

**Cons:**
- First run is slower
- Network dependency

## Example config.yml with Comments

```yaml
# Model Configuration

# ============================================================================
# SDXL Base Setup
# ============================================================================

models:
  - url: https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
    destination: checkpoints  # Main SDXL checkpoint

  - url: https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors
    destination: vae  # SDXL VAE for better quality

# ============================================================================
# ControlNet Models
# ============================================================================

  - url: https://huggingface.co/diffusers/controlnet-canny-sdxl-1.0/resolve/main/diffusion_pytorch_model.safetensors
    destination: controlnet  # Canny edge detection

# ============================================================================
# Custom LoRAs (Optional)
# ============================================================================

  - url: https://civitai.com/api/download/models/123456
    destination: loras
    optional: true  # Won't fail if unavailable

  - url: https://example.com/my-lora.safetensors
    destination: loras
    optional: true  # Custom training LoRA
```

## Summary

The model management system provides:

- ✅ **Simple declarative format** - Easy to read and edit YAML
- ✅ **Automatic downloads** - Models fetch on container start
- ✅ **Validation** - Parse errors caught before download
- ✅ **Flexible** - Works locally and in production
- ✅ **Optional models** - Gracefully handle failures
- ✅ **Version controllable** - Track model configs in git

Edit `config.yml`, define your models, and let the system handle the rest!
