# Local Testing Guide

This guide walks you through testing your ComfyUI RunPod worker locally with your 4090 GPU before deploying.

## Prerequisites

- ComfyUI installed and running locally
- Python 3.10+
- Your models already downloaded
- NVIDIA 4090 GPU with drivers installed

## Setup Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` and set your models path:

```bash
MODELS_PATH=C:/path/to/your/ComfyUI/models
```

This path should point to where your ComfyUI models are stored. The handler will use this locally and automatically switch to `/runpod-volume` when deployed.

### 3. Start ComfyUI

Make sure ComfyUI is running on the default port:

```bash
# In your ComfyUI directory
python main.py
```

Verify it's accessible at `http://127.0.0.1:8188`

### 4. Prepare Your Workflow

Export your workflow from ComfyUI in API format:

1. Open ComfyUI in browser
2. Load your workflow
3. Enable Dev mode (Settings → Dev mode)
4. Click "Save (API Format)"
5. Save as `my_workflow.json` in this directory

### 5. Run Quick Test

Use the provided test script:

```bash
python test_local.py
```

This will:
- Load `example_workflow.json`
- Apply sample overrides
- Execute the workflow
- Print the results

Expected output:
```
============================================================
Testing ComfyUI Handler Locally
============================================================

Make sure ComfyUI is running on http://127.0.0.1:8188

Sending request to handler...
------------------------------------------------------------
Using local models path: C:/ComfyUI/models
Queuing prompt...
Prompt queued with ID: abc-123-def
Waiting for completion...
Execution completed

============================================================
RESULT
============================================================
{
  "status": "success",
  "prompt_id": "abc-123-def",
  "models_path": "C:/ComfyUI/models",
  "execution_time": 12.34,
  "image_count": 1,
  "images": [
    {
      "url": "http://127.0.0.1:8188/view?filename=...",
      "filename": "ComfyUI_00001.png",
      "node_id": "9"
    }
  ]
}

✓ Test completed successfully!

Execution time: 12.34s
Models path: C:/ComfyUI/models

Generated 1 image(s):
  - ComfyUI_00001.png
    URL: http://127.0.0.1:8188/view?filename=...
```

### 6. Test with Your Workflow

Edit `test_local.py` to use your workflow:

```python
# Load your workflow instead
with open("my_workflow.json", "r") as f:
    workflow = json.load(f)

# Customize overrides for your specific nodes
event = {
    "input": {
        "workflow": workflow,
        "overrides": [
            {
                "node_id": "6",  # Your prompt node ID
                "field": "inputs.text",
                "value": "your custom prompt here"
            },
            # Add more overrides as needed
        ]
    }
}
```

### 7. Test Different Scenarios

Create multiple test files for different use cases:

**test_sd15.py** - Test SD 1.5 workflows
**test_sdxl.py** - Test SDXL workflows
**test_flux.py** - Test FLUX workflows

## Docker Testing (Advanced)

To test the exact environment that will run in RunPod:

### 1. Update docker-compose.yml

Edit the volumes section:

```yaml
volumes:
  - C:/path/to/your/ComfyUI/models:/models
```

### 2. Run with Docker Compose

```bash
docker-compose up
```

This starts a containerized version of the worker with GPU access.

### 3. Test the Docker Worker

In another terminal:

```bash
curl -X POST http://localhost:8000 \
  -H "Content-Type: application/json" \
  -d @example_request.json
```

## Troubleshooting

### "Connection refused" error

**Problem**: Can't connect to ComfyUI API

**Solutions**:
- Verify ComfyUI is running: `http://127.0.0.1:8188` in browser
- Check if another process is using port 8188
- Update `COMFY_API_URL` in `.env` if using different port

### "Node not found" warning

**Problem**: Override references non-existent node ID

**Solutions**:
- Check your workflow's node IDs in the JSON
- Node IDs are usually numbers like "3", "6", "10"
- Open workflow in ComfyUI dev mode to see node numbers

### Models not loading

**Problem**: ComfyUI can't find models

**Solutions**:
- Verify `MODELS_PATH` points to correct directory
- Check that models exist in subdirectories (checkpoints/, vae/, etc.)
- Ensure model names in workflow match actual filenames

### GPU not being used

**Problem**: Running on CPU instead of GPU

**Solutions**:
- Check NVIDIA drivers: `nvidia-smi`
- Verify ComfyUI is configured to use GPU
- For Docker: Ensure docker-compose has GPU configuration

### Timeout errors

**Problem**: Workflow takes too long

**Solutions**:
- Increase timeout in test script: `"timeout": 1200`
- Reduce steps in workflow for testing
- Check if GPU is actually being used

## Performance Benchmarking

Time your local runs to estimate RunPod costs:

```python
# In your test script
start = time.time()
result = handler(event)
duration = time.time() - start

print(f"Execution took: {duration:.2f}s")
print(f"Estimated RunPod cost: ${duration * GPU_COST_PER_SECOND:.4f}")
```

## Next Steps

Once local testing works perfectly:

1. Push updated Docker image: `docker push alongbottom/comfyui-runpod:latest`
2. Upload models to RunPod network volume
3. Deploy/update your RunPod endpoint
4. Test remote endpoint with Postman
5. Monitor first few production runs

## Tips

- **Start simple**: Test with basic SD 1.5 workflow first
- **Verify models**: Ensure model names match exactly
- **Test overrides**: Try all parameter overrides you plan to use
- **Check outputs**: Verify image URLs are accessible
- **Monitor resources**: Watch GPU usage with `nvidia-smi`
- **Keep logs**: Save successful test results for comparison

## Common Workflows to Test

1. **Text-to-Image**: Basic prompt → image generation
2. **Image-to-Image**: Input image + prompt → modified image
3. **Batch Processing**: Multiple prompts in sequence
4. **ControlNet**: Image guidance + prompt
5. **Inpainting**: Masked edits to existing images
6. **LoRA Application**: Model + LoRA + prompt

Test each workflow type you plan to use in production!
