# ComfyUI + RunPod Handler Dockerfile
# Lightweight handler that connects to ComfyUI over HTTP
# Works for both local development (with auto-install) and RunPod production
#
# Supports all modern NVIDIA GPUs: RTX 4090 (Ada), RTX 5090 (Blackwell), and beyond
# PyTorch 2.9.0 + CUDA 12.8 provides universal compatibility
#
# Local development: docker compose up (uses start.sh to auto-install ComfyUI)
# Production: docker build -f Dockerfile --target production (runs handler.py only)

# =============================================================================
# Base image - Universal GPU support
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

# Install system dependencies
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

# Upgrade pip
RUN python3 -m pip install --upgrade pip setuptools wheel

# Install PyTorch 2.9.0 + CUDA 12.8 (supports all modern GPUs: Ada, Blackwell, and beyond)
RUN echo "Installing PyTorch ${TORCH_VERSION} with CUDA ${CUDA_VERSION}..." && \
    pip3 install --no-cache-dir \
        --index-url ${TORCH_INDEX_URL} \
        --extra-index-url https://pypi.org/simple \
        torch==${TORCH_VERSION}+${CUDA_TAG} \
        torchvision==${TORCHVISION_VERSION}+${CUDA_TAG} \
        torchaudio==${TORCHAUDIO_VERSION}+${CUDA_TAG}

# Fetch and install ComfyUI's requirements.txt from GitHub
RUN wget -O /tmp/comfyui-requirements.txt \
    https://raw.githubusercontent.com/comfyanonymous/ComfyUI/master/requirements.txt && \
    pip3 install --no-cache-dir -r /tmp/comfyui-requirements.txt && \
    rm /tmp/comfyui-requirements.txt

# Install additional dependencies (xformers, performance optimizations)
RUN echo "Installing xformers (latest compatible with PyTorch ${TORCH_VERSION})..." && \
    pip3 install --no-cache-dir xformers transformers accelerate || \
    (echo "xformers install failed, continuing without it..." && pip3 install --no-cache-dir transformers accelerate)

# Install Triton for Linux (already built-in for CUDA-enabled PyTorch on Linux)
# Note: triton-windows is Windows-only, Linux uses triton from PyTorch
RUN pip3 install --no-cache-dir triton || echo "Triton install skipped (may be bundled with PyTorch)"

# Install SageAttention (performance optimization)
# Try prebuilt wheel first, fallback to source if needed
RUN pip3 install --no-cache-dir \
    https://github.com/thu-ml/SageAttention/releases/download/v2.2.0/sageattention-2.2.0-py3-none-any.whl \
    || pip3 install --no-cache-dir "git+https://github.com/thu-ml/SageAttention.git@v2.2.0" \
    || echo "SageAttention install failed - optional performance optimization"

# Install hf_transfer for faster HuggingFace downloads
RUN pip3 install --no-cache-dir hf_transfer

# Install handler dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy handler and startup files
COPY handler.py .
COPY s3_upload.py .
COPY start.sh .
COPY download_models.py .
COPY install_nodes.py .

# Copy unified config file
COPY config.yml .

RUN chmod +x /app/start.sh /app/download_models.py /app/install_nodes.py

# Environment variables
ENV COMFY_API_URL=http://127.0.0.1:8188
ENV COMFYUI_PATH=/comfyui

# Enable hf_transfer for faster HuggingFace downloads (optional but recommended)
ENV HF_HUB_ENABLE_HF_TRANSFER=1

# Expose ports
EXPOSE 8000 8188

# Labels
LABEL gpu_arch="${GPU_ARCH}"
LABEL cuda_version="${CUDA_VERSION}"
LABEL pytorch_version="${TORCH_VERSION}"
LABEL description="ComfyUI + RunPod Handler"

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8188/ || exit 1

# Default: Local development mode (auto-install ComfyUI + start handler)
CMD ["/app/start.sh"]

# =============================================================================
# Production target - Handler only (for RunPod serverless)
# =============================================================================

FROM final AS production

# Override CMD to run handler only (expects ComfyUI on RunPod volume)
CMD ["python3", "handler.py"]
