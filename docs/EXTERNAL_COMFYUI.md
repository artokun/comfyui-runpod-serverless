# ComfyUI Auto-Install Guide

ComfyUI is now automatically installed from your filesystem for maximum flexibility.

## How It Works (New Default)

```bash
docker compose up
```

When you run this for the first time:
1. ComfyUI is automatically cloned to `./ComfyUI`
2. Dependencies are installed
3. Output and workflows directories are linked
4. ComfyUI starts with the handler

**Benefits:**
- ✅ **Auto-install** - No manual setup needed
- ✅ **Updateable** - `cd ComfyUI && git pull` or set `AUTO_UPDATE=true`
- ✅ **Persistent** - survives container rebuilds
- ✅ **Modifiable** - edit code directly on your filesystem
- ✅ **Custom nodes** - add/remove anytime
- ✅ **Share models** - symlink to existing models
- ✅ **Use outside Docker** - run ComfyUI directly too
- ✅ **Smaller images** - 3GB vs 8GB

## Quick Start

### First Run (Automatic)

```bash
docker compose up
```

That's it! On first run:
- ComfyUI is automatically cloned to `./ComfyUI`
- Dependencies are installed
- Services start

### Optional: Enable Auto-Updates

```bash
cp .env.example .env
# Edit .env and set:
AUTO_UPDATE=true
```

Now ComfyUI will automatically update on every container start.

## Directory Structure

After setup:

```
comfy-template/
├── ComfyUI/                     # ← ComfyUI on filesystem
│   ├── main.py
│   ├── models/                  # ← Can symlink to existing
│   │   ├── checkpoints/
│   │   ├── vae/
│   │   └── loras/
│   ├── custom_nodes/            # ← Add/remove anytime
│   ├── output → ../output       # ← Symlink to project
│   └── user/default/workflows → ../workflows
│
├── output/                      # Generated images
├── workflows/                   # Your workflows
└── docker-compose.yml           # Has both modes
```

## Updating ComfyUI

### Option 1: Auto-Update (Recommended)

Set in `.env`:
```bash
AUTO_UPDATE=true
```

ComfyUI will automatically update on container start. It will:
- Pull latest changes
- Update dependencies if requirements.txt changed
- Handle conflicts gracefully

### Option 2: Manual Update

```bash
cd ComfyUI
git pull
pip install -r requirements.txt --upgrade
```

Restart container:
```bash
docker compose restart
```

### Option 3: Update Script

```bash
./update-comfyui.sh
```

Smart update with stashing, backup branches, and conflict handling.

No rebuild needed for any method!

## Adding Custom Nodes

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/user/custom-node.git
cd custom-node
pip install -r requirements.txt  # if exists
```

Restart:
```bash
docker compose restart
```

## Sharing Models

### Option 1: Manual Symlinks (After First Run)

After first `docker compose up`, ComfyUI will exist at `./ComfyUI`:

```bash
cd ComfyUI/models
rm -rf checkpoints  # Remove empty dir
ln -s /path/to/your/checkpoints checkpoints
ln -s /path/to/your/vae vae
ln -s /path/to/your/loras loras
```

### Option 2: Mount in Docker Compose

Edit `docker-compose.yml`:

```yaml
comfyui:
  volumes:
    - ${COMFYUI_PATH:-./ComfyUI}:/comfyui
    - /path/to/your/models:/comfyui/models  # Add this
```

## Configuration

In `.env`:

```bash
# GPU architecture
GPU_ARCH=ada

# Path to ComfyUI (default: ./ComfyUI)
COMFYUI_PATH=./ComfyUI

# Auto-update on container start (default: false)
AUTO_UPDATE=false
```

## Common Workflows

### Development Workflow

```bash
# 1. First run (auto-installs)
docker compose up

# 2. Make changes to ComfyUI
cd ComfyUI/custom_nodes
git clone https://github.com/...

# 3. Restart to apply
docker compose restart

# 4. View logs
docker compose logs -f
```

### Testing Updates

```bash
# Option 1: Enable auto-update
echo "AUTO_UPDATE=true" >> .env
docker compose restart

# Option 2: Manual update
cd ComfyUI && git pull
docker compose restart

# Option 3: Use update script
./update-comfyui.sh
docker compose restart
```

## Architecture Details

**Current (Auto-Install):**
- ComfyUI lives on filesystem at `./ComfyUI`
- Container mounts it via volume
- Auto-installs if missing
- Optionally auto-updates
- Persistent across rebuilds
- 3GB container image

**Old Bundled (Deprecated):**
- ComfyUI baked into container
- Updates require rebuild
- Custom nodes lost on rebuild
- 8GB container image
- Available as `Dockerfile.bundled` if needed

## Using ComfyUI Outside Docker

Since ComfyUI lives on your filesystem, you can use it directly:

```bash
cd ComfyUI
python main.py --listen 0.0.0.0 --port 8188
```

Same installation, same models, just without Docker!

## Reverting to Bundled Mode

If you need the old bundled mode (not recommended):

```bash
# Build from bundled Dockerfile
docker compose build --build-arg DOCKERFILE=Dockerfile.bundled

# Or manually
docker build -f Dockerfile.bundled -t comfyui:ada .
```

The auto-install mode is superior in every way - only use bundled if you have a specific reason.

## Troubleshooting

### "Permission denied"

On Linux, ComfyUI directory needs proper ownership:

```bash
sudo chown -R $USER:$USER ./ComfyUI
```

### "ComfyUI not found"

Check `.env` has correct path:

```bash
COMFYUI_PATH=./ComfyUI
```

Or set when running:

```bash
COMFYUI_PATH=./ComfyUI docker compose --profile external up
```

### "Models not loading"

Check symlinks:

```bash
ls -la ComfyUI/models/
```

Should show symlinks (→) pointing to your model directories.

### "Container won't start"

Check logs:

```bash
docker compose logs
```

Common issues:
- Git not installed in container
- Network issues cloning ComfyUI
- Permissions on Mac/Linux
- COMFYUI_PATH misconfigured

## Best Practices

1. **Enable auto-updates** - Set `AUTO_UPDATE=true` for effortless updates
2. **Keep ComfyUI updated** - Or manually `cd ComfyUI && git pull` regularly
3. **Symlink models** - Share between installations
4. **Version control workflows** - They're in `./workflows/`
5. **Add custom nodes freely** - They persist across rebuilds

## Performance

Auto-install mode has minimal overhead:

- **First run**: +30-60s (cloning ComfyUI)
- **Subsequent runs**: Instant (no rebuild needed)
- **ComfyUI startup**: Same as bundled
- **Generation speed**: Identical (both use same GPU)

The first-run delay is a one-time cost for permanent flexibility!

## Architecture Diagram

```
┌─────────────────────────┐
│   Docker Container      │
│                         │
│   ┌──────────────────┐  │
│   │  ComfyUI (mount) │←─┼─→ Filesystem ./ComfyUI/
│   │   (http://8188)  │  │   - Auto-cloned if missing
│   └──────────────────┘  │   - Auto-updated if enabled
│          ↕              │   - Persistent
│   ┌──────────────────┐  │
│   │   Handler        │  │
│   │   (port 8000)    │  │
│   └──────────────────┘  │
└─────────────────────────┘
         ↕
    GPU Hardware
```

Handler connects to ComfyUI over HTTP, same as production RunPod deployment.

## Integration with RunPod

The auto-install mode is for **local development only**. RunPod deployment still uses the lightweight handler-only image with ComfyUI pre-installed on network volumes.

Local workflow:
1. **Develop** with auto-install mode (updateable, persistent)
2. **Test** your workflows locally
3. **Deploy** with `./deploy.sh` (handler-only image)

Both use the same handler code, so workflows work identically.

## Summary

Auto-install ComfyUI mode gives you:

- ⚡ **Zero setup** - Just run `docker compose up`
- 🔄 **Easy updates** - Manual or automatic
- 💾 **Persistence** - Survives container rebuilds
- 🔧 **Flexibility** - Modify and extend easily
- 📦 **Model sharing** - Symlink to existing collections
- 🚀 **Faster rebuilds** - 3GB vs 8GB images

Perfect for development while maintaining production compatibility!
