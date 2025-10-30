#!/usr/bin/env python3
"""
Local testing script for the ComfyUI RunPod handler.

This script simulates the RunPod serverless environment locally,
allowing you to test your workflow with your 4090 GPU before deploying.

Usage:
    python test_local.py
"""

import json
import sys
from pathlib import Path

# Add parent directory to path to import handler
sys.path.insert(0, str(Path(__file__).parent.parent))

from handler import handler

def test_workflow():
    """Test the handler with an example workflow."""

    # Load example workflow
    script_dir = Path(__file__).parent
    workflow_path = script_dir / "example_workflow.json"

    try:
        with open(workflow_path, "r") as f:
            workflow = json.load(f)
    except FileNotFoundError:
        print("Error: example_workflow.json not found")
        print("Please create a workflow.json file or modify this script to use your workflow")
        sys.exit(1)

    # Create test event (simulates RunPod input)
    event = {
        "input": {
            "workflow": workflow,
            "overrides": [
                {
                    "node_id": "6",
                    "field": "inputs.text",
                    "value": "a beautiful sunset over mountains, vibrant colors, photorealistic, 4k"
                },
                {
                    "node_id": "3",
                    "field": "inputs.seed",
                    "value": 42
                },
                {
                    "node_id": "3",
                    "field": "inputs.steps",
                    "value": 25
                }
            ],
            "return_images": True,
            "timeout": 600,
            "use_websocket": False  # Disable WebSocket for local testing
        }
    }

    print("=" * 60)
    print("Testing ComfyUI Handler Locally")
    print("=" * 60)
    print("\nMake sure ComfyUI is running on http://127.0.0.1:8188")
    print("\nSending request to handler...")
    print("-" * 60)

    # Call the handler
    result = handler(event)

    # Print results
    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)
    print(json.dumps(result, indent=2))

    if result.get("status") == "success":
        print("\n[SUCCESS] Test completed successfully!")
        print(f"\nExecution time: {result.get('execution_time')}s")
        print(f"Models path: {result.get('models_path')}")

        if result.get("images"):
            print(f"\nGenerated {len(result['images'])} image(s):")
            for img in result["images"]:
                print(f"  - {img['filename']}")
                print(f"    URL: {img['url']}")
    else:
        print("\n[FAILED] Test failed!")
        print(f"Error: {result.get('error')}")
        sys.exit(1)

if __name__ == "__main__":
    test_workflow()
