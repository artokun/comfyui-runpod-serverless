# Configuration Management Guide

This guide explains how to edit and apply `config.yml` changes for models and custom nodes.

## Quick Reference

**Edit config.yml:**
- **Jupyter Lab** (port 8888): Navigate to `/workspace/config.yml` and edit
- **Text editor**: `nano config.yml` or `vim config.yml`
- **VS Code Remote**: Connect to container and edit

**Apply changes:**
```bash
chmod +x apply_config.sh
./apply_config.sh
```

## Method 1: Edit via Jupyter Lab (Recommended for RunPod Pods)

### Step 1: Access Jupyter Lab
Open your browser:
- **Local**: http://localhost:8888
- **RunPod Pod**: Use port 8888 in your pod's connection info

No password required!

### Step 2: Navigate to config.yml
In Jupyter file browser:
- **RunPod Pods**: `/runpod-volume/config.yml` or `/workspace/config.yml`
- **Local**: `/workspace/config.yml`

### Step 3: Edit Configuration
Right-click `config.yml` → "Open With" → "Editor"

Example additions:
```yaml
models:
  - url: https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors
    destination: vae
    optional: false

nodes:
  - url: https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
    version: latest
```

Save the file (Ctrl+S or Cmd+S).

### Step 4: Apply Changes
Open a **Terminal** in Jupyter:
- Click the "+" button (new launcher)
- Click "Terminal" under "Other"

Run the apply script:
```bash
cd /app
chmod +x apply_config.sh
./apply_config.sh
```

This will:
- ✅ Install any new custom nodes
- ✅ Download any new models
- ✅ Skip already installed nodes/models (fast!)

### Step 5: Restart ComfyUI (if needed)
Most custom nodes require a ComfyUI restart:

**RunPod Pods:**
- Stop and restart the pod from RunPod console

**Local Docker Compose:**
```bash
docker compose restart
```

## Method 2: Local Terminal (Development)

### Step 1: Edit config.yml
```bash
nano config.yml
# or
code config.yml  # VS Code
```

### Step 2: Apply Changes
If running via docker-compose:
```bash
# Option A: Run script inside container
docker compose exec comfyui /app/apply_config.sh

# Option B: Restart container (applies automatically)
docker compose restart
```

If you have the workspace mounted locally:
```bash
chmod +x apply_config.sh
./apply_config.sh
```

## Method 3: Base64 Encoded (RunPod Endpoints)

For **RunPod Endpoints** (serverless), you can't edit files directly. Instead:

### Step 1: Prepare config.yml
Create or edit your `config.yml` file locally with desired models and nodes.

### Step 2: Encode to Base64
1. Visit **https://www.base64encode.org/**
2. Copy entire `config.yml` content
3. Paste into encoder
4. Click "ENCODE"
5. Copy the encoded result

### Step 3: Set Environment Variable
In RunPod Endpoint settings:
- Add environment variable: `CONFIG_YML`
- Paste the base64-encoded string
- Save and redeploy

The container will automatically decode and apply on startup!

## config.yml Format Reference

### Models Section
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

### Custom Nodes Section
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
- `nightly` - Latest commit on default branch (bleeding edge)
- `v1.2.3` - Specific version tag
- `abc1234` - Specific commit hash
- `main` - Track a specific branch

## Fast Warm Starts (SHA Caching)

The container uses SHA256 hashing to detect config changes and skip unnecessary downloads on warm starts:

**How it works:**
1. First run: Calculates SHA of `config.yml`, installs everything, stores SHA
2. Subsequent runs: Compares current SHA with stored SHA
3. If match: Skips all downloads/installs (seconds instead of minutes)
4. If differ: Applies updates and updates SHA

**SHA file locations:**
- RunPod: `/runpod-volume/.config-sha256`
- Local: `/workspace/.config-sha256`

**Force reinstall (if needed):**
```bash
# Delete SHA file to force full reinstall on next start
rm /runpod-volume/.config-sha256  # RunPod
# or
rm /workspace/.config-sha256  # Local
```

This is particularly important for RunPod Endpoints where warm start time directly impacts response latency.

## Troubleshooting

### "Permission denied" when running apply_config.sh
```bash
chmod +x apply_config.sh
./apply_config.sh
```

### "config.yml not found"
Check your current directory:
```bash
pwd
ls -la config.yml
```

Expected locations:
- **RunPod**: `/runpod-volume/config.yml` or `/workspace/config.yml`
- **Local**: `/workspace/config.yml`

### Models downloading slowly
The script uses:
- ✅ **hf_transfer** for HuggingFace (100-200+ MB/s on gigabit)
- ✅ **8-thread parallel chunks** for Civitai and others
- ✅ **Smart caching** - skips existing files

If still slow, check your network connection.

### Custom node installation fails
Common causes:
1. **Git URL typo** - Verify the repository URL
2. **Version doesn't exist** - Check the repo for valid tags/commits
3. **Missing dependencies** - Some nodes need system packages

Check the error message for details.

### Changes not taking effect
After running `apply_config.sh`, you must:
1. Restart ComfyUI (for custom nodes)
2. Refresh browser (for UI changes)

**Restart commands:**
- **RunPod Pod**: Stop and start from console
- **Local**: `docker compose restart`

## Best Practices

### 1. Test with optional: true
When adding new models, use `optional: true` initially:
```yaml
models:
  - url: https://example.com/large-model.safetensors
    destination: checkpoints
    optional: true  # Won't fail if download issues
```

### 2. Use specific versions for stability
For production, pin specific versions:
```yaml
nodes:
  - url: https://github.com/user/repo.git
    version: v1.2.3  # Not "latest" or "nightly"
```

### 3. Comment out unused entries
Keep your config.yml organized:
```yaml
models:
  - url: https://active-model.safetensors
    destination: checkpoints

  # Temporarily disabled for testing
  # - url: https://unused-model.safetensors
  #   destination: checkpoints
```

### 4. Back up working configs
Before making major changes:
```bash
cp config.yml config.yml.backup
```

In Jupyter, you can duplicate files by right-clicking → "Duplicate".

## Example Workflows

### Adding SDXL Support
1. Edit `config.yml`:
```yaml
models:
  - url: https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
    destination: checkpoints
    optional: false

  - url: https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors
    destination: vae
    optional: false
```

2. Run `apply_config.sh`
3. Restart ComfyUI
4. SDXL models available!

### Adding ControlNet
1. Edit `config.yml`:
```yaml
models:
  - url: https://huggingface.co/lllyasviel/ControlNet-v1-1/resolve/main/control_v11p_sd15_openpose.pth
    destination: controlnet
    optional: false

nodes:
  - url: https://github.com/Fannovel16/comfyui_controlnet_aux.git
    version: latest
```

2. Run `apply_config.sh`
3. Restart ComfyUI
4. ControlNet nodes available!

### Setting up Video Generation
1. Edit `config.yml`:
```yaml
nodes:
  - url: https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
    version: latest

  - url: https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git
    version: latest

models:
  - url: https://huggingface.co/guoyww/animatediff/resolve/main/mm_sd_v15_v2.ckpt
    destination: animatediff_models
    optional: false
```

2. Run `apply_config.sh`
3. Restart ComfyUI
4. Video generation ready!

## FAQ

**Q: Can I edit config.yml while ComfyUI is running?**
A: Yes! Edit anytime, then run `apply_config.sh` to apply changes. Restart ComfyUI for custom nodes to take effect.

**Q: Do I need to rebuild the Docker image?**
A: No! `config.yml` is on a volume. Just edit and run `apply_config.sh`.

**Q: How do I remove a model or custom node?**
A: Comment it out in `config.yml` (add `#` at start of lines) or delete the files manually from ComfyUI directories.

**Q: Can I use config.yml and CONFIG_YML env var together?**
A: CONFIG_YML env var takes priority and overwrites config.yml on startup. After that, you can edit the written config.yml.

**Q: Where can I find more custom nodes?**
A:
- ComfyUI Manager (browse in UI)
- https://github.com/topics/comfyui
- https://github.com/ltdrdata/ComfyUI-Manager (registry)

## Support

For issues or questions:
- GitHub Issues: https://github.com/YOUR-USERNAME/comfyui-runpod-handler/issues
- Documentation: See README.md and CLAUDE.md
