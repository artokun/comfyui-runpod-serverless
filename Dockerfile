# ComfyUI + RunPod Handler Dockerfile (Minimal Shell)
# Container is minimal - only system dependencies and runtime
# All Python packages install to volume for true persistence
#
# Architecture:
# - Container: Ubuntu + Python + system libs (~2-3GB)
# - Volume: PyTorch, ComfyUI, all deps, models, nodes (persistent)

# =============================================================================
# Minimal base - just runtime environment
# =============================================================================

FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu22.04 AS final

ENV CUDA_VERSION=12.8
ENV CUDA_TAG=cu128
ENV TORCH_VERSION=2.9.0
ENV TORCHVISION_VERSION=0.24.0
ENV TORCHAUDIO_VERSION=2.9.0
ENV TORCH_INDEX_URL=https://download.pytorch.org/whl/cu128

# Environment hygiene
ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONNOUSERSITE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONUTF8=1

# Install ONLY system dependencies (no Python packages yet)
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    wget \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Make python3.10 default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1

# Install uv (Rust-based pip replacement - 10-100x faster, parallel downloads)
# https://github.com/astral-sh/uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Install ONLY handler's core dependencies (small, needed for container runtime)
# PyTorch, ComfyUI deps, etc. will install to volume in start.sh
WORKDIR /app
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Copy handler and startup files
COPY handler.py .
COPY s3_upload.py .
COPY start.sh .
COPY entrypoint.sh .
COPY download_models.py .
COPY install_nodes.py .
COPY test_input.json .
COPY apply_config.sh .

# Copy unified config file
COPY config.yml .

RUN chmod +x /app/start.sh /app/entrypoint.sh /app/download_models.py /app/install_nodes.py /app/apply_config.sh

# Environment variables
ENV COMFY_API_URL=http://127.0.0.1:8188
ENV COMFYUI_PATH=/comfyui
ENV RUN_MODE=production

# Enable hf_transfer for faster HuggingFace downloads
ENV HF_HUB_ENABLE_HF_TRANSFER=1

# Expose ports
EXPOSE 8000 8188 8888

# Labels
LABEL cuda_version="${CUDA_VERSION}"
LABEL pytorch_version="${TORCH_VERSION}"
LABEL description="ComfyUI + RunPod Handler - Minimal Shell (Volume-First Architecture)"

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8188/ || exit 1

# Unified entrypoint (uses RUN_MODE env to decide what to run)
ENTRYPOINT ["/app/entrypoint.sh"]
