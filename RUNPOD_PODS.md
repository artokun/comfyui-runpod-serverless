# RunPod GPU Pods Deployment

Deploy ComfyUI to RunPod GPU Pods with Jupyter notebook access for development and testing.

## What are Pods?

**Pods** are traditional GPU instances with:
- ✅ SSH and Jupyter notebook access
- ✅ Direct file system access
- ✅ Interactive development
- ✅ Pay-per-hour billing (running time only)

**Use Pods for:**
- Development and testing workflows
- Interactive ComfyUI design
- Experimenting with models/nodes
- Learning and prototyping

**Use Serverless Endpoints for:**
- Production API deployments
- Scale-to-zero cost savings
- Auto-scaling workloads
- See [RUNPOD_QUICKSTART.md](RUNPOD_QUICKSTART.md) instead

## Quick Start

### Step 1: Create Network Volume

1. Go to https://runpod.io/console/storage
2. Click **"New Network Volume"**
3. Configure:
   - **Name:** `comfyui-volume`
   - **Region:** Choose region with RTX 4090/5090
   - **Size:** 50 GB minimum
4. Click **"Create"**

### Step 2: Deploy Pod

1. Go to https://runpod.io/console/pods
2. Click **"Deploy"** or **"GPU Pods"**
3. Select GPU:
   - **RTX 4090** - Best value ($0.50-0.70/hr)
   - **RTX 5090** - Fastest (when available)
4. Configure:
   ```
   Container Image: artokun/comfyui-runpod-serverless:ada
   Container Disk: 20 GB
   Volume Mount: comfyui-volume → /runpod-volume
   Expose HTTP Ports: 8188, 8000
   ```

5. Environment Variables (Optional):
   ```
   COMFY_API_URL=http://127.0.0.1:8188
   COMFYUI_PATH=/runpod-volume/ComfyUI
   AUTO_UPDATE=false
   ```

6. Click **"Deploy"**

### Step 3: Access Your Pod

Once deployed, you'll see:
- **Connect** button → Opens Jupyter notebook
- **TCP Port Mappings** → External URL for ComfyUI UI

Click **Connect** to open Jupyter notebook.

## Configuration

### Method 1: Upload config.yml via Jupyter (Recommended)

1. Click **"Connect"** → Opens Jupyter notebook
2. Navigate to `/runpod-volume/`
3. Click **"Upload"** button
4. Select your `config.yml` file
5. Restart pod (or wait for next start)

**Done!** Your config persists on the volume.

### Method 2: Edit config.yml in Jupyter

1. Open Jupyter notebook
2. Navigate to `/runpod-volume/`
3. Create new text file → Rename to `config.yml`
4. Paste your configuration:

```yaml
models:
  - url: https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors
    destination: vae
  - url: https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors
    destination: checkpoints

nodes:
  - url: https://github.com/ltdrdata/ComfyUI-Manager.git
    version: latest
  - url: https://github.com/kijai/ComfyUI-KJNodes.git
    version: latest
```

5. Save and restart pod

### Method 3: Via Environment Variable (Optional)

In pod template environment variables:

```
CONFIG_YML=models:
  - url: https://huggingface.co/.../model.safetensors
    destination: checkpoints
nodes:
  - url: https://github.com/.../node.git
    version: latest
```

This writes config to `/runpod-volume/config.yml` on startup.

## Configuration Priority

The system uses this order (highest to lowest):

1. **CONFIG_YML env var** → Writes to `/runpod-volume/config.yml`
2. **config.yml on volume** → `/runpod-volume/config.yml` (editable)
3. **Baked-in default** → `/app/config.yml` (fallback)

**Recommendation:** Use Jupyter upload or edit for pods. It's simpler and persists!

## Access ComfyUI

### Web Interface

From pod details, find the **TCP Port Mappings**:
- **Port 8188** → ComfyUI web interface
- **Port 8000** → RunPod handler API

Click the URL to open ComfyUI.

### API Access

```python
import requests

# Get external URL from RunPod pod details
COMFY_URL = "https://xxxxxx-8188.proxy.runpod.net"

# Test ComfyUI is running
response = requests.get(f"{COMFY_URL}/")
print(response.status_code)  # Should be 200
```

## Workflow Development

### 1. Design in ComfyUI

Open ComfyUI web interface (port 8188) and create your workflow visually.

### 2. Export Workflow

- Enable Dev Mode: Settings → Dev Mode
- Save workflow: Save (API Format)
- Download the JSON file

### 3. Upload to Jupyter

- Open Jupyter notebook
- Navigate to `/runpod-volume/workflows/`
- Upload your workflow JSON

### 4. Test via API

```python
import requests
import json

HANDLER_URL = "https://xxxxxx-8000.proxy.runpod.net"

with open('/runpod-volume/workflows/my_workflow.json') as f:
    workflow = json.load(f)

response = requests.post(
    f"{HANDLER_URL}/runsync",
    json={
        "input": {
            "workflow": workflow,
            "overrides": [
                {"node_id": "6", "field": "inputs.text", "value": "a beautiful sunset"}
            ]
        }
    }
)

print(response.json())
```

## Cost Management

### Billing

Pods bill **per second** while running:
- RTX 4090: ~$0.50-0.70/hour
- RTX 5090: ~$1.50-2.00/hour (when available)

**Tip:** Stop pods when not in use to save costs!

### Stop/Start Pod

- **Stop:** Click **"Stop"** button (volume persists)
- **Start:** Click **"Start"** button (restores from volume)
- **Terminate:** Deletes pod (volume remains)

Your models, nodes, and config on the volume persist!

## Troubleshooting

### ComfyUI not loading

Check pod logs:
1. Pod details → **"Logs"** tab
2. Look for startup messages
3. Ensure port 8188 is exposed

### Models not downloading

1. Check `/runpod-volume/config.yml` exists
2. Check pod logs for download errors
3. Verify HuggingFace URLs are valid

### Out of memory

- Use smaller models or lower resolution
- Restart pod to clear GPU memory
- Upgrade to larger GPU

## Next Steps

- **Production deployment?** See [RUNPOD_QUICKSTART.md](RUNPOD_QUICKSTART.md) for serverless endpoints
- **Custom models?** See [Model Management](docs/MODEL_MANAGEMENT.md)
- **Custom nodes?** See [Custom Nodes](docs/CUSTOM_NODES.md)
- **Testing workflows?** See [Testing Guide](docs/TESTING.md)

## Support

- **GitHub Issues:** https://github.com/artokun/comfyui-runpod-serverless/issues
- **RunPod Discord:** https://discord.gg/runpod
- **ComfyUI Discord:** https://discord.gg/comfyui
