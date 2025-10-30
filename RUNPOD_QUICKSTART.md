# RunPod Serverless Endpoint Quickstart

Deploy ComfyUI as a serverless API endpoint with auto-scaling and scale-to-zero cost savings.

## Pods vs Serverless Endpoints

**Choose Serverless Endpoints if:**
- ✅ Production API deployment
- ✅ Auto-scaling needed
- ✅ Pay per execution (scale to zero)
- ✅ No server management

**Choose GPU Pods if:**
- 🔧 Development and testing
- 🔧 Interactive ComfyUI design
- 🔧 Need SSH/Jupyter access
- 🔧 See [RUNPOD_PODS.md](RUNPOD_PODS.md) instead

## Prerequisites

1. **RunPod Account** - Sign up at https://runpod.io
2. **Payment Method** - Add to your RunPod account
3. **Network Volume** - For persistent models/nodes (recommended)

That's it! No Docker Hub account or manual builds needed.

## Step 1: Create Template

1. Go to https://runpod.io/console/serverless
2. Click **"New Template"**
3. Configure:

```
Name: ComfyUI Handler - Ada (RTX 4090)
Container Image: artokun/comfyui-runpod:ada
Container Disk: 20 GB

Environment Variables (Optional - defaults are set):
  # All have sensible defaults, only add if customizing:
  # COMFY_API_URL=http://127.0.0.1:8188 (default)
  # COMFYUI_PATH=/runpod-volume/ComfyUI (default)
  # AUTO_UPDATE=false (default)

Expose HTTP Ports (Optional):
  Leave blank (for API-only deployment)
  Or enter: 8188 (to access ComfyUI UI for debugging)
```

For **RTX 5090/6000 Pro**, use `artokun/comfyui-runpod:blackwell`

4. Click **"Save Template"**

## Step 2: Create Network Volume (Required)

1. Go to **Storage** → **Network Volumes**
2. Click **"New Network Volume"**
3. Configure:
   - **Name:** `comfyui-volume`
   - **Region:** Choose region with RTX 4090/5090 availability
   - **Size:** 100 GB (recommended for models + ComfyUI)
4. Click **"Create"**

**Why a volume is required:**
- ComfyUI installs to `/runpod-volume/ComfyUI` (persistent)
- Models stored permanently (no re-download between runs)
- Custom nodes persist
- Much faster cold starts after first run

## Step 3: Create Endpoint

1. Go back to **Serverless**
2. Click **"New Endpoint"**
3. Configure:

```
Name: comfyui-ada-4090
Select Template: ComfyUI Handler - Ada (RTX 4090)
Select Network Volume: comfyui-volume (optional)

GPUs:
  ☑ RTX 4090
  Min Workers: 0
  Max Workers: 3

Advanced:
  Idle Timeout: 5 seconds
  Execution Timeout: 600 seconds
  Max Concurrent Requests: 1
```

4. Click **"Deploy"**

## Step 4: Test Your Endpoint

Get your endpoint ID from the RunPod console.

### Test with cURL

```bash
export RUNPOD_ENDPOINT_ID="your-endpoint-id"
export RUNPOD_API_KEY="your-api-key"

curl -X POST "https://api.runpod.ai/v2/${RUNPOD_ENDPOINT_ID}/runsync" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d @examples/example_request.json
```

### Test with Python

```python
import requests
import json
import os

ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")
API_KEY = os.getenv("RUNPOD_API_KEY")

with open("examples/example_request.json") as f:
    payload = json.load(f)

response = requests.post(
    f"https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync",
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    },
    json=payload
)

print(json.dumps(response.json(), indent=2))
```

## Customization

### Custom Models/Nodes (Recommended - No Rebuild!)

**Easy Method: Use CONFIG_YML Environment Variable**

Paste your `config.yml` content as `CONFIG_YML` environment variable in template settings. On startup, this writes to `/runpod-volume/config.yml` (persistent):

1. Go to your template settings
2. Add environment variable:
   ```
   CONFIG_YML=models:
     - url: https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors
       destination: vae
   nodes:
     - url: https://github.com/ltdrdata/ComfyUI-Manager.git
       version: latest
   ```
3. Save template
4. Workers will use this config on startup
5. **Bonus:** File persists on volume, survives restarts!

**Alternative: Direct Volume Edit**

If you have SSH access to network volume:
```bash
cd /runpod-volume
nano config.yml
# Edit and save
```

Next worker startup will use the edited config.

**Configuration Priority:**
1. 🥇 CONFIG_YML env var → Writes to volume (persistent)
2. 🥈 config.yml on volume → Can be edited directly
3. 🥉 Baked-in default → Fallback if nothing else

See [Model Management](docs/MODEL_MANAGEMENT.md) and [Custom Nodes](docs/CUSTOM_NODES.md) guides.

### Optional Environment Variables

Only add these if you need to customize default behavior:

**S3 Upload (for direct S3 image upload):**
```
BUCKET_ENDPOINT_URL=https://s3.amazonaws.com
BUCKET_ACCESS_KEY_ID=your-key
BUCKET_SECRET_ACCESS_KEY=your-secret
BUCKET_NAME=comfyui-outputs
```

**Auto-Update ComfyUI (not recommended - adds 10-30s startup time):**
```
AUTO_UPDATE=true
```

**All core settings have sensible defaults** - you typically don't need to set anything!

## GPU Options

### Ada (RTX 4090) - Default

```
Container Image: artokun/comfyui-runpod:ada
GPU: RTX 4090
```

- CUDA 11.8
- PyTorch 2.1.0
- Great price/performance
- Widely available

### Blackwell (RTX 5090/6000 Pro) - Premium

```
Container Image: artokun/comfyui-runpod:blackwell
GPU: RTX 5090 or RTX 6000 Pro
```

- CUDA 12.4
- PyTorch 2.5.0
- 40-60% faster
- Premium pricing
- Limited availability

## Troubleshooting

### "ComfyUI not found"

**Solution:** ComfyUI will auto-install on first run. Adds 2-3 minutes to startup.

Or pre-install on network volume (see docs/RUNPOD_DEPLOYMENT.md)

### "Timeout"

**Solutions:**
- Increase execution timeout in endpoint settings
- Use smaller models
- Reduce resolution/steps

### "Model not found"

**Solutions:**
- Add models to `config.yml`
- Or manually download to network volume

### "Out of memory"

**Solutions:**
- Use smaller batch sizes
- Use quantized models (fp8)
- Reduce resolution

### Should I expose ports?

**For serverless endpoints, typically no.**

- **Production API deployment:** Leave "Expose HTTP Ports" blank
  - RunPod automatically routes API requests to your handler (port 8000)
  - ComfyUI runs internally on port 8188 (handler connects via localhost)
  - No external port access needed

- **Debugging with ComfyUI UI:** Enter `8188` in "Expose HTTP Ports"
  - Access ComfyUI web interface at `https://{endpoint-id}-8188.proxy.runpod.net`
  - Useful for designing workflows interactively
  - Testing models and nodes
  - **Note:** Exposes UI publicly (use with caution)

**Recommendation:** Leave blank for production, only expose for development/debugging.

## Cost Estimation

**RTX 4090 pricing (approximate):**
- Idle: $0.00/hour (scale to zero)
- Active: ~$0.50-0.70/hour
- Per workflow: ~$0.01-0.03

**RTX 5090 pricing (approximate):**
- Idle: $0.00/hour (scale to zero)
- Active: ~$1.50-2.00/hour
- Per workflow: ~$0.01-0.07

**Tips to reduce costs:**
- Scale to zero (min workers: 0)
- Set short idle timeout (5 seconds)
- Batch multiple images
- Use appropriate resolution

## Performance

**Expected generation times on RTX 4090:**
- SD 1.5: ~5-10 seconds
- SDXL: ~20-30 seconds
- FLUX: ~90-120 seconds

**RTX 5090 is 40-60% faster** when available.

## Next Steps

1. ✅ Create template with official image
2. ✅ Create network volume (optional)
3. ✅ Create endpoint
4. ✅ Test with example workflow
5. ✅ Customize models/nodes in `config.yml`
6. ✅ Deploy!

## Complete Documentation

- **[RunPod Deployment](docs/RUNPOD_DEPLOYMENT.md)** - Full deployment guide
- **[Model Management](docs/MODEL_MANAGEMENT.md)** - Managing models
- **[Custom Nodes](docs/CUSTOM_NODES.md)** - Installing custom nodes
- **[API Testing](docs/TESTING.md)** - Testing workflows

## Support

- **GitHub Issues:** https://github.com/artokun/comfyui-runpod-handler/issues
- **RunPod Discord:** https://discord.gg/runpod
- **ComfyUI Discord:** https://discord.gg/comfyui

---

**Ready to deploy?** Just create a template with `artokun/comfyui-runpod:ada` and you're done! 🚀
