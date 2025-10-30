# RunPod Deployment Guide

Deploy your ComfyUI handler to RunPod serverless endpoints.

## Overview

The deployment process:
1. Build lightweight production image (handler only)
2. Push to Docker Hub
3. Configure RunPod endpoint
4. Test and scale

## Prerequisites

- Docker Hub account
- RunPod account
- Local testing completed with `docker compose up`
- Workflows tested and working

## Step 1: Build Production Image

The production image is lightweight (~3GB) and uses pre-installed ComfyUI from network volumes.

```bash
# Build for your GPU architecture
./build.sh ada          # RTX 4090
./build.sh blackwell    # RTX 5090/6000 Pro
```

This builds `Dockerfile.production` which contains only the handler, not ComfyUI.

## Step 2: Deploy to Docker Hub

```bash
# Deploy (builds and pushes)
./deploy.sh ada

# Or manually:
docker login
docker push alongbottom/comfyui-runpod:ada
```

## Step 3: Configure RunPod Endpoint

### Create Serverless Endpoint

1. Go to [RunPod Serverless](https://www.runpod.io/console/serverless)
2. Click "New Endpoint"
3. Configure:

**Container Configuration:**
```
Image: alongbottom/comfyui-runpod:ada
```

**GPU Selection:**
- For `ada` build: RTX 4090, RTX 4000 Ada, L40, L40S
- For `blackwell` build: RTX 5090, RTX 6000 Pro (when available)

**Worker Configuration:**
```
Active Workers:    0-1
Max Workers:       5-10
Idle Timeout:      20-30s
Execution Timeout: 180-300s (3-5 minutes)
```

**Advanced Settings:**
```
FlashBoot:         Enabled
Container Disk:    10GB
Network Volume:    Attach your ComfyUI volume
```

### Network Volume Setup

Your network volume should have ComfyUI pre-installed:

```
/runpod-volume/
├── ComfyUI/           # Full ComfyUI installation
│   ├── main.py
│   ├── models/
│   │   ├── checkpoints/
│   │   ├── vae/
│   │   └── loras/
│   └── custom_nodes/
└── models/            # Or flat structure
    ├── checkpoints/
    ├── vae/
    └── loras/
```

The handler automatically detects network volumes and starts ComfyUI.

## Step 4: Test Endpoint

Get your endpoint ID from RunPod console, then test:

```bash
curl -X POST https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d @examples/example_request.json
```

Response:
```json
{
  "delayTime": 2453,
  "executionTime": 8324,
  "id": "sync-abc123",
  "output": {
    "status": "success",
    "prompt_id": "def456",
    "execution_time": 8.32,
    "images": [
      {
        "url": "https://...image.png",
        "filename": "ComfyUI_00001.png"
      }
    ]
  },
  "status": "COMPLETED"
}
```

## Architecture Comparison

### Local Development (Dockerfile)
```
Docker Container (8GB)
├── ComfyUI (included)
└── Handler
```

### Production (Dockerfile.production)
```
Docker Container (3GB)
└── Handler only
    ↓ uses
Network Volume
└── ComfyUI (pre-installed)
```

## Build Scripts

### build.sh

Builds the production image:

```bash
#!/bin/bash
ARCH=${1:-ada}
docker build \
  --platform linux/amd64 \
  --build-arg GPU_ARCH=$ARCH \
  -f Dockerfile.production \
  -t alongbottom/comfyui-runpod:$ARCH \
  .
```

### deploy.sh

Builds and pushes:

```bash
#!/bin/bash
ARCH=${1:-ada}

# Build
./build.sh $ARCH

# Push
docker push alongbottom/comfyui-runpod:$ARCH

echo "Deployed: alongbottom/comfyui-runpod:$ARCH"
echo "Use this in RunPod console"
```

## Endpoint Optimization

See [RUNPOD_CONFIG.md](RUNPOD_CONFIG.md) for detailed configuration templates based on your use case:

- **Development/Testing**: Minimal workers, short timeouts
- **Moderate Traffic**: Balanced configuration
- **High Volume**: Multiple workers, longer idle timeout

## GPU Architecture Selection

### Ada (RTX 4090)
- **CUDA**: 11.8
- **PyTorch**: 2.1.0+cu118
- **Image**: `alongbottom/comfyui-runpod:ada`
- **RunPod GPUs**: RTX 4090, RTX 4000 Ada, L40, L40S, A6000

### Blackwell (RTX 5090/6000 Pro)
- **CUDA**: 12.4
- **PyTorch**: 2.5.0+cu124
- **Image**: `alongbottom/comfyui-runpod:blackwell`
- **RunPod GPUs**: RTX 5090, RTX 6000 Pro (when available)
- **Performance**: 40-60% faster than Ada

## Workflow Migration

Your locally-tested workflows work without modification:

```python
# Local testing (docker compose)
response = requests.post('http://localhost:8000/runsync', json=payload)

# Production (RunPod)
response = requests.post(
    'https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync',
    headers={'Authorization': f'Bearer {API_KEY}'},
    json=payload
)
```

Same payload format, same response format!

## Cost Optimization

### Cold Start Optimization
1. **FlashBoot**: Enable for faster cold starts
2. **Active Workers**: Keep 1 active for instant response
3. **Network Volume**: Pre-installed ComfyUI loads faster

### Execution Optimization
1. **Right-size timeout**: Don't over-allocate
2. **GPU selection**: RTX 4090 is good price/performance
3. **Idle timeout**: Balance response time vs cost

### Example Costs

**RTX 4090 on RunPod** (~$0.34/hr):
- 1 image (SDXL): ~$0.001
- 10 images/hr: ~$0.01/hr
- 1000 images/day: ~$1/day

With 0 active workers, you only pay for execution time!

## Monitoring

### View Logs
RunPod Console → Endpoint → Request ID → Logs

### Check Performance
Monitor execution times to optimize:
- ComfyUI startup: Should be < 30s
- Workflow execution: Varies by complexity
- Total: Startup + execution + overhead

### Common Issues

**"Handler timeout"**
- Increase execution timeout
- Check ComfyUI is starting properly
- Verify models are on network volume

**"GPU out of memory"**
- Use smaller models
- Reduce batch size
- Use FP16 instead of FP32

**"Network volume not found"**
- Verify volume is attached
- Check volume has ComfyUI installed
- Ensure path is `/runpod-volume`

## Scaling

### Auto-scaling Behavior

```
Requests → Workers → GPUs
0         → 0       → $0/hr
1         → 1       → 1x GPU cost
10        → 5       → 5x GPU cost (with max=5)
```

Workers auto-scale between min and max based on queue depth.

### Recommendations

**Low Traffic** (< 10 req/hr):
- Active: 0
- Max: 3
- Idle timeout: 30s

**Medium Traffic** (10-100 req/hr):
- Active: 1
- Max: 5
- Idle timeout: 60s

**High Traffic** (> 100 req/hr):
- Active: 2-3
- Max: 10+
- Idle timeout: 120s
- Consider dedicated instances

## Network Volume Setup Script

If you need to set up ComfyUI on your network volume:

```bash
# SSH to a RunPod GPU instance with network volume mounted
cd /runpod-volume

# Install ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install -r requirements.txt

# Download models
mkdir -p models/checkpoints models/vae models/loras

# Test
python main.py --listen 0.0.0.0
```

Or use one of the installer scripts from `docs/INSTALLER_PATTERNS.md`.

## Updating

### Update Handler Code

1. Modify `handler.py` locally
2. Test with `docker compose up`
3. Rebuild and deploy:
```bash
./deploy.sh ada
```

4. RunPod pulls new image automatically on next cold start
5. Or restart workers manually in console

### Update ComfyUI

On your network volume:
```bash
cd /runpod-volume/ComfyUI
git pull
pip install -r requirements.txt --upgrade
```

Handler code doesn't need changes!

## Multiple Architectures

Deploy both architectures for flexibility:

```bash
# Deploy Ada
./deploy.sh ada

# Deploy Blackwell
./deploy.sh blackwell
```

Create separate RunPod endpoints:
- `my-endpoint-ada`: Uses RTX 4090
- `my-endpoint-blackwell`: Uses RTX 5090

Route traffic based on GPU availability and cost.

## Production Checklist

- [ ] Tested locally with `docker compose up`
- [ ] All workflows work correctly
- [ ] Models downloaded to network volume
- [ ] ComfyUI installed on network volume
- [ ] Built production image: `./build.sh ada`
- [ ] Pushed to Docker Hub: `./deploy.sh ada`
- [ ] Created RunPod endpoint
- [ ] Attached network volume
- [ ] Tested endpoint with curl
- [ ] Verified execution times acceptable
- [ ] Set appropriate timeout values
- [ ] Configured auto-scaling
- [ ] Set up monitoring/logging

## Support

Issues? Check:
1. [TESTING.md](TESTING.md) - Testing workflows
2. [RUNPOD_CONFIG.md](RUNPOD_CONFIG.md) - Configuration reference
3. [DOCKER_COMPOSE.md](DOCKER_COMPOSE.md) - Local development
4. RunPod Discord - Community support
