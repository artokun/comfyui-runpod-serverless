import runpod
import requests
import json
import time
import os
from typing import Dict, Any, List, Optional, Set
import uuid
from pathlib import Path
import threading
import base64
import re
import tempfile

# Import S3 upload functionality
try:
    from s3_upload import is_s3_configured, upload_file_to_s3, upload_bytes_to_s3
    S3_UPLOAD_AVAILABLE = True
except ImportError:
    S3_UPLOAD_AVAILABLE = False
    print("Warning: s3_upload module not available. S3 upload will be disabled.")

COMFY_API_URL = os.getenv("COMFY_API_URL", "http://127.0.0.1:8188")
COMFY_WS_URL = os.getenv("COMFY_WS_URL", COMFY_API_URL.replace("http://", "ws://").replace("https://", "wss://") + "/ws")

# Network volume support with local fallback
# In RunPod: /runpod-volume
# Locally: Set MODELS_PATH environment variable or use ./models
RUNPOD_VOLUME_PATH = "/runpod-volume"
LOCAL_MODELS_PATH = os.getenv("MODELS_PATH", "./models")

# Determine which path to use
if os.path.exists(RUNPOD_VOLUME_PATH):
    MODELS_BASE_PATH = RUNPOD_VOLUME_PATH
    print(f"Using RunPod network volume: {RUNPOD_VOLUME_PATH}")
else:
    MODELS_BASE_PATH = LOCAL_MODELS_PATH
    print(f"Using local models path: {LOCAL_MODELS_PATH}")


def apply_overrides(workflow: Dict[str, Any], overrides: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Apply overrides to workflow nodes.

    Overrides format:
    [
        {
            "node_id": "3",
            "field": "inputs.seed",
            "value": 12345
        },
        {
            "node_id": "6",
            "field": "inputs.text",
            "value": "a beautiful landscape"
        }
    ]
    """
    workflow_copy = json.loads(json.dumps(workflow))

    for override in overrides:
        node_id = str(override.get("node_id"))
        field = override.get("field")
        value = override.get("value")

        if node_id not in workflow_copy:
            print(f"Warning: Node {node_id} not found in workflow")
            continue

        # Parse nested field path (e.g., "inputs.seed")
        field_parts = field.split(".")
        current = workflow_copy[node_id]

        # Navigate to the parent of the target field
        for part in field_parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set the final value
        current[field_parts[-1]] = value
        print(f"Applied override: Node {node_id}, {field} = {value}")

    return workflow_copy


def check_server(max_retries: int = 50, delay: float = 0.05) -> None:
    """
    Check if ComfyUI server is reachable.

    Args:
        max_retries: Maximum number of connection attempts (default: 50)
        delay: Delay between retries in seconds (default: 0.05)

    Raises:
        Exception: If server is not reachable after all retries
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{COMFY_API_URL}/system_stats", timeout=2)
            if response.status_code == 200:
                print(f"ComfyUI server is reachable (attempt {attempt + 1})")
                return
        except requests.RequestException:
            pass

        if attempt < max_retries - 1:
            time.sleep(delay)

    raise Exception(f"ComfyUI server at {COMFY_API_URL} is not reachable after {max_retries} attempts")


def decode_base64_image(image_data: str) -> bytes:
    """
    Decode base64 image data, handling data URI prefix if present.

    Args:
        image_data: Base64 encoded image string, optionally with data URI prefix
                   (e.g., "data:image/png;base64,iVBORw0KG..." or just "iVBORw0KG...")

    Returns:
        Decoded image bytes
    """
    # Strip data URI prefix if present (e.g., "data:image/png;base64,")
    if image_data.startswith("data:"):
        # Match pattern: data:image/<type>;base64,<data>
        match = re.match(r'data:image/[^;]+;base64,(.+)', image_data)
        if match:
            image_data = match.group(1)
        else:
            # Try simpler pattern without image type
            image_data = image_data.split(",", 1)[-1]

    # Decode base64
    return base64.b64decode(image_data)


def upload_image(filename: str, image_bytes: bytes, overwrite: bool = True) -> Dict[str, Any]:
    """
    Upload an image to ComfyUI via the /upload/image endpoint.

    Args:
        filename: Name for the uploaded file
        image_bytes: Image data as bytes
        overwrite: Whether to overwrite existing file (default: True)

    Returns:
        Response from ComfyUI upload endpoint

    Raises:
        requests.RequestException: If upload fails
    """
    # Determine content type from filename extension
    extension = filename.lower().split('.')[-1]
    content_type_map = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp'
    }
    content_type = content_type_map.get(extension, 'image/png')

    # Upload using multipart/form-data
    files = {'image': (filename, image_bytes, content_type)}
    data = {'overwrite': 'true' if overwrite else 'false'}

    response = requests.post(f"{COMFY_API_URL}/upload/image", files=files, data=data)
    response.raise_for_status()

    return response.json()


def process_input_images(images: List[Dict[str, Any]], errors: List[str]) -> None:
    """
    Process and upload base64 encoded input images.

    Args:
        images: List of image objects with 'name' and 'data' fields
        errors: List to append non-fatal errors to
    """
    if not images:
        return

    print(f"Processing {len(images)} input images...")

    for idx, image_obj in enumerate(images):
        try:
            if not isinstance(image_obj, dict):
                errors.append(f"Image {idx}: Invalid format, expected object with 'name' and 'data' fields")
                continue

            filename = image_obj.get("name")
            image_data = image_obj.get("data")

            if not filename:
                errors.append(f"Image {idx}: Missing 'name' field")
                continue

            if not image_data:
                errors.append(f"Image {idx}: Missing 'data' field")
                continue

            # Decode base64 image
            image_bytes = decode_base64_image(image_data)

            # Upload to ComfyUI
            result = upload_image(filename, image_bytes)
            print(f"Uploaded image: {filename} ({len(image_bytes)} bytes)")

        except base64.binascii.Error as e:
            errors.append(f"Image {idx} ({filename}): Base64 decode error - {str(e)}")
        except requests.RequestException as e:
            errors.append(f"Image {idx} ({filename}): Upload failed - {str(e)}")
        except Exception as e:
            errors.append(f"Image {idx} ({filename}): Unexpected error - {str(e)}")


def queue_prompt(workflow: Dict[str, Any], comfyorg_api_key: Optional[str] = None) -> str:
    """
    Queue a prompt in ComfyUI and return the prompt ID.

    Args:
        workflow: The ComfyUI workflow to execute
        comfyorg_api_key: Optional Comfy.org API key for authentication with paid API nodes

    Returns:
        The prompt ID
    """
    payload = {
        "prompt": workflow,
        "client_id": str(uuid.uuid4())
    }

    # Inject Comfy.org API key if provided
    if comfyorg_api_key:
        payload["extra_data"] = {
            "api_key_comfy_org": comfyorg_api_key
        }
        print("Comfy.org API key injected into workflow")

    response = requests.post(f"{COMFY_API_URL}/prompt", json=payload)
    response.raise_for_status()

    result = response.json()
    prompt_id = result.get("prompt_id")

    if not prompt_id:
        raise Exception(f"Failed to queue prompt: {result}")

    return prompt_id


def get_history(prompt_id: str) -> Optional[Dict[str, Any]]:
    """Get the history/results for a prompt ID."""
    response = requests.get(f"{COMFY_API_URL}/history/{prompt_id}")
    response.raise_for_status()

    history = response.json()
    return history.get(prompt_id)


def wait_for_completion(prompt_id: str, timeout: int = 600, poll_interval: int = 2, use_websocket: bool = True) -> Dict[str, Any]:
    """
    Wait for a prompt to complete and return the results.

    Attempts to use WebSocket for real-time monitoring if use_websocket=True,
    falls back to polling if WebSocket is unavailable or fails.

    Args:
        prompt_id: The prompt ID to wait for
        timeout: Maximum time to wait in seconds
        poll_interval: How often to check for completion in seconds (polling mode)
        use_websocket: Whether to attempt WebSocket monitoring first (default: True)

    Returns:
        The completed prompt history
    """
    # Try WebSocket first if enabled
    if use_websocket:
        print("Attempting WebSocket monitoring...")
        client_id = str(uuid.uuid4())
        history = wait_for_completion_ws(prompt_id, client_id, timeout)
        if history:
            return history
        print("WebSocket failed, falling back to polling...")

    # Fall back to polling
    print("Using polling mode...")
    start_time = time.time()

    while True:
        if time.time() - start_time > timeout:
            raise TimeoutError(f"Prompt {prompt_id} did not complete within {timeout} seconds")

        history = get_history(prompt_id)

        if history and history.get("status", {}).get("completed", False):
            return history

        time.sleep(poll_interval)


def get_output_images(history: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Extract output image information from history.

    Returns:
        List of dicts with 'filename', 'subfolder', 'type' for each output image
    """
    images = []

    outputs = history.get("outputs", {})
    for node_id, node_output in outputs.items():
        if "images" in node_output:
            for image_info in node_output["images"]:
                images.append({
                    "filename": image_info.get("filename"),
                    "subfolder": image_info.get("subfolder", ""),
                    "type": image_info.get("type", "output"),
                    "node_id": node_id
                })

    return images


def get_image_url(filename: str, subfolder: str = "", folder_type: str = "output") -> str:
    """Generate the URL to download an image from ComfyUI."""
    params = f"filename={filename}&subfolder={subfolder}&type={folder_type}"
    return f"{COMFY_API_URL}/view?{params}"


def download_image_from_comfy(filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
    """
    Download image bytes from ComfyUI.

    Args:
        filename: Image filename
        subfolder: Subfolder path
        folder_type: Folder type (output, input, temp)

    Returns:
        Image bytes

    Raises:
        requests.RequestException: If download fails
    """
    url = get_image_url(filename, subfolder, folder_type)
    response = requests.get(url)
    response.raise_for_status()
    return response.content


def process_images_with_s3(output_images: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Process output images and upload to S3 if configured, otherwise return ComfyUI URLs.

    Args:
        output_images: List of image info dicts from get_output_images()

    Returns:
        List of processed image dicts with URL, filename, type, and node_id
    """
    use_s3 = S3_UPLOAD_AVAILABLE and is_s3_configured()

    if use_s3:
        print("S3 is configured - uploading images to S3")
    else:
        print("S3 not configured - returning ComfyUI URLs")

    processed_images = []

    for img in output_images:
        filename = img["filename"]
        subfolder = img["subfolder"]
        folder_type = img["type"]
        node_id = img["node_id"]

        if use_s3:
            try:
                # Download image from ComfyUI
                print(f"Downloading image: {filename}")
                image_bytes = download_image_from_comfy(filename, subfolder, folder_type)

                # Generate unique object name with timestamp to avoid collisions
                timestamp = int(time.time() * 1000)
                object_name = f"{timestamp}_{filename}"

                # Upload to S3
                print(f"Uploading to S3: {object_name}")
                upload_result = upload_bytes_to_s3(
                    file_bytes=image_bytes,
                    object_name=object_name,
                    content_type="image/png"  # Default to PNG, could be improved
                )

                if upload_result["success"]:
                    processed_images.append({
                        "url": upload_result["url"],
                        "filename": filename,
                        "type": "s3_url",
                        "node_id": node_id
                    })
                    print(f"Successfully uploaded to S3: {upload_result['url']}")
                else:
                    # Fallback to ComfyUI URL if S3 upload fails
                    print(f"S3 upload failed: {upload_result.get('error')} - falling back to ComfyUI URL")
                    processed_images.append({
                        "url": get_image_url(filename, subfolder, folder_type),
                        "filename": filename,
                        "type": "comfyui_url",
                        "node_id": node_id
                    })

            except Exception as e:
                # Fallback to ComfyUI URL if any error occurs
                print(f"Error processing image for S3: {str(e)} - falling back to ComfyUI URL")
                processed_images.append({
                    "url": get_image_url(filename, subfolder, folder_type),
                    "filename": filename,
                    "type": "comfyui_url",
                    "node_id": node_id
                })
        else:
            # S3 not configured, use ComfyUI URLs
            processed_images.append({
                "url": get_image_url(filename, subfolder, folder_type),
                "filename": filename,
                "type": "comfyui_url",
                "node_id": node_id
            })

    return processed_images


def get_models_path() -> str:
    """Get the models base path (network volume or local)."""
    return MODELS_BASE_PATH


def health_check(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Health check endpoint for RunPod.

    Tests if the handler is running and if ComfyUI is reachable.

    Returns:
        Dict with status and comfyui_reachable flag
    """
    comfyui_reachable = False

    try:
        # Try to reach ComfyUI's /system_stats endpoint (or any basic endpoint)
        response = requests.get(f"{COMFY_API_URL}/system_stats", timeout=5)
        comfyui_reachable = response.status_code == 200
    except Exception as e:
        print(f"ComfyUI health check failed: {str(e)}")

    return {
        "status": "healthy",
        "comfyui_reachable": comfyui_reachable,
        "comfy_api_url": COMFY_API_URL
    }


def get_available_models() -> Dict[str, List[str]]:
    """
    Fetch available models from ComfyUI's /object_info endpoint.

    Returns:
        Dictionary mapping model types to lists of available model names.
        Example: {
            "checkpoints": ["model1.safetensors", "model2.ckpt"],
            "vae": ["vae1.pt"],
            "loras": ["lora1.safetensors"]
        }
    """
    try:
        response = requests.get(f"{COMFY_API_URL}/object_info")
        response.raise_for_status()
        object_info = response.json()

        models = {}

        # Extract checkpoint models
        if "CheckpointLoaderSimple" in object_info:
            checkpoint_input = object_info["CheckpointLoaderSimple"]["input"]
            if "required" in checkpoint_input and "ckpt_name" in checkpoint_input["required"]:
                models["checkpoints"] = checkpoint_input["required"]["ckpt_name"][0]

        # Extract VAE models
        if "VAELoader" in object_info:
            vae_input = object_info["VAELoader"]["input"]
            if "required" in vae_input and "vae_name" in vae_input["required"]:
                models["vae"] = vae_input["required"]["vae_name"][0]

        # Extract LoRA models
        if "LoraLoader" in object_info:
            lora_input = object_info["LoraLoader"]["input"]
            if "required" in lora_input and "lora_name" in lora_input["required"]:
                models["loras"] = lora_input["required"]["lora_name"][0]

        # Extract ControlNet models
        if "ControlNetLoader" in object_info:
            controlnet_input = object_info["ControlNetLoader"]["input"]
            if "required" in controlnet_input and "control_net_name" in controlnet_input["required"]:
                models["controlnet"] = controlnet_input["required"]["control_net_name"][0]

        return models

    except Exception as e:
        print(f"Warning: Failed to fetch available models: {e}")
        return {}


def validate_workflow_models(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that models referenced in the workflow are available.

    Args:
        workflow: ComfyUI workflow dictionary

    Returns:
        Dictionary with validation results:
        {
            "valid": bool,
            "missing_models": List[Dict],  # List of missing model references
            "available_models": Dict       # Available models by type
        }
    """
    available_models = get_available_models()
    missing_models = []

    # Model field mappings: node class_type -> (field_name, model_type)
    model_fields = {
        "CheckpointLoaderSimple": ("ckpt_name", "checkpoints"),
        "CheckpointLoader": ("ckpt_name", "checkpoints"),
        "VAELoader": ("vae_name", "vae"),
        "LoraLoader": ("lora_name", "loras"),
        "LoraLoaderModelOnly": ("lora_name", "loras"),
        "ControlNetLoader": ("control_net_name", "controlnet"),
    }

    for node_id, node_data in workflow.items():
        class_type = node_data.get("class_type", "")

        if class_type in model_fields:
            field_name, model_type = model_fields[class_type]

            # Get the model name from node inputs
            model_name = node_data.get("inputs", {}).get(field_name)

            if model_name and model_type in available_models:
                available = available_models[model_type]

                if model_name not in available:
                    missing_models.append({
                        "node_id": node_id,
                        "class_type": class_type,
                        "model_type": model_type,
                        "model_name": model_name,
                        "available_models": available
                    })

    return {
        "valid": len(missing_models) == 0,
        "missing_models": missing_models,
        "available_models": available_models
    }


def wait_for_completion_ws(prompt_id: str, client_id: str, timeout: int = 600) -> Optional[Dict[str, Any]]:
    """
    Wait for prompt completion using WebSocket for real-time updates.
    Falls back to None if WebSocket is unavailable or fails.

    Args:
        prompt_id: The prompt ID to wait for
        client_id: Client ID for WebSocket connection
        timeout: Maximum time to wait in seconds

    Returns:
        The completed prompt history, or None if WebSocket failed
    """
    try:
        import websocket

        completion_event = threading.Event()
        result_data = {"history": None, "error": None}

        def on_message(ws, message):
            try:
                data = json.loads(message)
                msg_type = data.get("type")

                # Log progress updates
                if msg_type == "progress":
                    progress_data = data.get("data", {})
                    value = progress_data.get("value", 0)
                    max_value = progress_data.get("max", 0)
                    if max_value > 0:
                        percent = (value / max_value) * 100
                        print(f"Progress: {percent:.1f}% ({value}/{max_value})")

                # Check for execution completion
                elif msg_type == "executing":
                    executing_data = data.get("data", {})
                    node = executing_data.get("node")

                    # node is None when execution completes
                    if node is None and executing_data.get("prompt_id") == prompt_id:
                        print("Execution completed (WebSocket)")
                        # Fetch final history
                        history = get_history(prompt_id)
                        result_data["history"] = history
                        completion_event.set()
                        ws.close()

                # Check for execution errors
                elif msg_type == "execution_error":
                    error_data = data.get("data", {})
                    if error_data.get("prompt_id") == prompt_id:
                        result_data["error"] = f"Execution error: {error_data}"
                        completion_event.set()
                        ws.close()

            except Exception as e:
                print(f"Error processing WebSocket message: {e}")

        def on_error(ws, error):
            print(f"WebSocket error: {error}")
            result_data["error"] = str(error)
            completion_event.set()

        def on_close(ws, close_status_code, close_msg):
            print(f"WebSocket closed: {close_status_code} - {close_msg}")
            completion_event.set()

        def on_open(ws):
            print(f"WebSocket connected to {COMFY_WS_URL}")

        # Create WebSocket connection
        ws_url = f"{COMFY_WS_URL}?clientId={client_id}"
        ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )

        # Run WebSocket in a separate thread
        ws_thread = threading.Thread(target=ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()

        # Wait for completion or timeout
        completed = completion_event.wait(timeout=timeout)

        if not completed:
            print("WebSocket timeout")
            ws.close()
            return None

        if result_data["error"]:
            print(f"WebSocket error occurred: {result_data['error']}")
            return None

        return result_data["history"]

    except ImportError:
        print("websocket-client not installed, falling back to polling")
        return None
    except Exception as e:
        print(f"WebSocket monitoring failed: {e}, falling back to polling")
        return None


def handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    RunPod handler for ComfyUI workflow execution with WebSocket monitoring, model validation,
    S3 upload support, Comfy.org API key support, and base64 image input support.

    Expected input format:
    {
        "input": {
            "workflow": { ... },         # ComfyUI workflow in API format
            "overrides": [               # Optional array of node overrides
                {
                    "node_id": "3",
                    "field": "inputs.seed",
                    "value": 12345
                }
            ],
            "images": [                  # Optional: Base64 encoded input images
                {
                    "name": "input_image.png",
                    "data": "data:image/png;base64,iVBORw0KG..." # or just base64 without prefix
                }
            ],
            "return_images": true,       # Optional: whether to return image URLs (default: true)
            "timeout": 600,              # Optional: max execution time in seconds (default: 600)
            "use_websocket": true,       # Optional: use WebSocket for progress monitoring (default: true)
            "validate_models": false,    # Optional: validate workflow models before execution (default: false)
            "comfyorg_api_key": "..."    # Optional: Comfy.org API key for paid API nodes
        }
    }

    WebSocket Monitoring:
    - Real-time progress updates and execution monitoring via WebSocket
    - Automatically falls back to HTTP polling if WebSocket fails
    - Set "use_websocket": false to disable and use polling only
    - Requires websocket-client package (included in requirements.txt)

    Model Validation:
    - Optionally validate that all models referenced in the workflow are available
    - Set "validate_models": true to enable pre-execution validation
    - Returns helpful error if workflow references missing models
    - Uses /object_info endpoint to fetch available models

    Base64 Image Upload:
    - Provide "images" array with base64 encoded image data
    - Supports data URI format (data:image/png;base64,...) or plain base64
    - Images are uploaded to ComfyUI before workflow execution
    - Non-fatal errors are collected and returned in response

    Comfy.org API Key:
    - Provide "comfyorg_api_key" in job input, OR
    - Set COMFYORG_API_KEY environment variable as fallback
    - Required for workflows using paid API nodes from Comfy.org
    - Get your API key from https://platform.comfy.org/

    S3 Configuration (optional):
    Set these environment variables to enable S3 upload:
    - BUCKET_ENDPOINT_URL: S3 endpoint URL
    - BUCKET_ACCESS_KEY_ID: S3 access key ID
    - BUCKET_SECRET_ACCESS_KEY: S3 secret access key
    - BUCKET_NAME: S3 bucket name (optional, defaults to "comfyui-outputs")

    Returns:
    {
        "status": "success",
        "prompt_id": "...",
        "models_path": "...",            # Path being used for models
        "s3_enabled": true/false,        # Whether S3 upload is configured
        "images": [
            {
                "url": "http://..." or "https://s3...",
                "filename": "...",
                "type": "s3_url" or "comfyui_url",
                "node_id": "..."
            }
        ],
        "errors": ["..."],               # Non-fatal errors (only present if errors occurred)
        "validation": { ... },           # Model validation results (only if validate_models=true)
        "execution_time": 12.34
    }
    """
    # Initialize non-fatal errors list
    errors = []

    try:
        start_time = time.time()

        job_input = event.get("input", {})

        # Validate required inputs
        if "workflow" not in job_input:
            return {
                "error": "Missing required field: workflow"
            }

        workflow = job_input["workflow"]
        overrides = job_input.get("overrides", [])
        return_images = job_input.get("return_images", True)
        timeout = job_input.get("timeout", 600)
        input_images = job_input.get("images", [])
        use_websocket = job_input.get("use_websocket", True)
        validate_models = job_input.get("validate_models", False)

        # Get Comfy.org API key from input or environment variable
        comfyorg_api_key = job_input.get("comfyorg_api_key") or os.getenv("COMFYORG_API_KEY")

        # Process and upload input images if provided
        if input_images:
            process_input_images(input_images, errors)

        # Apply overrides if provided
        if overrides:
            workflow = apply_overrides(workflow, overrides)

        # Validate models if requested
        validation_result = None
        if validate_models:
            print("Validating workflow models...")
            validation_result = validate_workflow_models(workflow)
            if not validation_result["valid"]:
                missing = validation_result["missing_models"]
                error_msg = f"Workflow validation failed: {len(missing)} missing model(s). "
                for m in missing[:3]:  # Show first 3 missing models
                    error_msg += f"\nNode {m['node_id']}: Model '{m['model_name']}' ({m['model_type']}) not found."
                if len(missing) > 3:
                    error_msg += f"\n...and {len(missing) - 3} more missing model(s)."
                return {
                    "error": error_msg,
                    "status": "validation_error",
                    "validation": validation_result
                }
            print("Model validation passed")

        # Check server connectivity before queuing
        print("Checking ComfyUI server connectivity...")
        check_server()

        # Queue the prompt
        print("Queuing prompt...")
        prompt_id = queue_prompt(workflow, comfyorg_api_key=comfyorg_api_key)
        print(f"Prompt queued with ID: {prompt_id}")

        # Wait for completion
        print("Waiting for completion...")
        history = wait_for_completion(prompt_id, timeout=timeout, use_websocket=use_websocket)
        print("Execution completed")

        execution_time = time.time() - start_time

        # Check if S3 is enabled
        s3_enabled = S3_UPLOAD_AVAILABLE and is_s3_configured()

        # Build response
        response = {
            "status": "success",
            "prompt_id": prompt_id,
            "models_path": MODELS_BASE_PATH,
            "s3_enabled": s3_enabled,
            "execution_time": round(execution_time, 2)
        }

        # Extract and process image URLs if requested
        if return_images:
            output_images = get_output_images(history)
            # Process images with S3 upload if configured, otherwise use ComfyUI URLs
            response["images"] = process_images_with_s3(output_images)
            response["image_count"] = len(output_images)

        # Include non-fatal errors if any occurred
        if errors:
            response["errors"] = errors

        # Include validation result if model validation was performed
        if validation_result:
            response["validation"] = validation_result

        return response

    except TimeoutError as e:
        return {
            "error": str(e),
            "status": "timeout"
        }
    except requests.RequestException as e:
        return {
            "error": f"ComfyUI API error: {str(e)}",
            "status": "api_error"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "error"
        }


if __name__ == "__main__":
    runpod.serverless.start({
        "handler": handler,
        "health_check": health_check
    })
