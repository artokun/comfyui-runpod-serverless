#!/usr/bin/env python3
"""
Optional model download script for RunPod's model caching feature.

This script is used if you want to pre-download models into the container
or leverage RunPod's cached models feature.

For most cases, using network volumes is simpler and more flexible.
"""

import os
import sys
from huggingface_hub import snapshot_download
from pathlib import Path

# Model configuration
MODELS = [
    {
        "repo_id": "stabilityai/stable-diffusion-xl-base-1.0",
        "local_dir": "/models/checkpoints/sdxl",
        "allow_patterns": ["*.safetensors", "*.json"],
    },
    # Add more models as needed
    # {
    #     "repo_id": "black-forest-labs/FLUX.1-dev",
    #     "local_dir": "/models/checkpoints/flux",
    #     "allow_patterns": ["*.safetensors"],
    # },
]

# RunPod model cache directory (if using RunPod's caching feature)
RUNPOD_MODELS_PATH = os.getenv("RUNPOD_MODELS_PATH", "/runpod-models")


def download_model(repo_id: str, local_dir: str, allow_patterns: list = None):
    """
    Download a model from Hugging Face Hub.

    Args:
        repo_id: HuggingFace repo ID (e.g., "stabilityai/stable-diffusion-xl-base-1.0")
        local_dir: Local directory to save the model
        allow_patterns: List of file patterns to download (e.g., ["*.safetensors"])
    """
    print(f"\n{'='*60}")
    print(f"Downloading: {repo_id}")
    print(f"To: {local_dir}")
    print(f"{'='*60}\n")

    try:
        # Create directory if it doesn't exist
        Path(local_dir).mkdir(parents=True, exist_ok=True)

        # Download the model
        snapshot_download(
            repo_id=repo_id,
            local_dir=local_dir,
            allow_patterns=allow_patterns,
            resume_download=True,
        )

        print(f"✓ Successfully downloaded {repo_id}\n")
        return True

    except Exception as e:
        print(f"✗ Error downloading {repo_id}: {e}\n")
        return False


def main():
    """Download all configured models."""
    print("\n" + "="*60)
    print("Model Download Script")
    print("="*60)
    print(f"RunPod models path: {RUNPOD_MODELS_PATH}")
    print(f"Models to download: {len(MODELS)}")
    print("="*60 + "\n")

    if not MODELS:
        print("No models configured. Edit MODELS list in this script.")
        return 0

    success_count = 0
    failed_models = []

    for model_config in MODELS:
        success = download_model(**model_config)
        if success:
            success_count += 1
        else:
            failed_models.append(model_config["repo_id"])

    # Summary
    print("\n" + "="*60)
    print("Download Summary")
    print("="*60)
    print(f"Successful: {success_count}/{len(MODELS)}")

    if failed_models:
        print(f"\nFailed downloads:")
        for model in failed_models:
            print(f"  - {model}")
        return 1
    else:
        print("\n✓ All models downloaded successfully!")
        return 0


if __name__ == "__main__":
    # Check if huggingface_hub is installed
    try:
        import huggingface_hub
    except ImportError:
        print("Error: huggingface_hub not installed")
        print("Install with: pip install huggingface_hub")
        sys.exit(1)

    sys.exit(main())
