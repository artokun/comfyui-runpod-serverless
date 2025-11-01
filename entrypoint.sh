#!/bin/bash
# Unified entrypoint for ComfyUI RunPod image
# Supports local development, production pods, and serverless endpoints

set -e

# Determine run mode
RUN_MODE="${RUN_MODE:-production}"

case "$RUN_MODE" in
    development|dev|local)
        echo "Starting in DEVELOPMENT mode (ComfyUI + Handler + Jupyter)"
        exec /app/start.sh
        ;;
    production|prod)
        echo "Starting in PRODUCTION mode (ComfyUI + Handler + Jupyter)"
        exec /app/start.sh
        ;;
    endpoint|serverless)
        echo "Starting in ENDPOINT mode (ComfyUI + Handler - optimized for cold starts)"
        exec /app/start.sh
        ;;
    *)
        echo "ERROR: Unknown RUN_MODE: $RUN_MODE"
        echo "Valid values: development, production, endpoint"
        exit 1
        ;;
esac
