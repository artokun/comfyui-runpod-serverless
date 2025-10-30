# ComfyUI Installer Patterns Reference

This document consolidates best practices from production ComfyUI installers analyzed for the RunPod deployment.

## 📋 Scripts Analyzed

1. **QWEN-IMAGE-EDIT-PLUS-COMFYUI-MANAGER_AUTO_INSTALL.bat** - Windows local installer
2. **WAN-ANIMATE-AUTO_INSTALL-RUNPOD.sh** - Linux RunPod installer
3. **WAN-ANIMATE-COMFYUI-MANAGER_AUTO_INSTALL.bat** - Windows portable installer
4. **install_triton_and_sageattention_auto.bat** - Advanced optimization installer
5. **WAN-ANIMATE-MODELS-NODES_INSTALL.bat** - Safe dependency manager

## 🎯 Core Patterns

### 1. Helper Functions

All successful installers use these helper patterns:

#### grab (Download with Skip)
```bash
# Bash version (WAN-ANIMATE-RUNPOD.sh)
grab() {
  [[ -f "$1" ]] && { echo " • $(basename "$1") exists — skip"; return; }
  echo " • downloading $(basename "$1")"
  mkdir -p "$(dirname "$1")"
  curl -L --fail --progress-bar --show-error -o "$1" "$2"
}

# Usage:
grab "models/clip_vision/clip_vision_h.safetensors" \
     "$HF_BASE/clip_vision_h.safetensors?download=true"
```

```batch
REM Batch version (WAN-ANIMATE-COMFYUI-MANAGER.bat)
:grab
if not exist "%~dp1" mkdir "%~dp1"
if not exist "%~1" (
    echo   • downloading %~nx1
    curl -L -o "%~1" "%~2" --ssl-no-revoke
    if errorlevel 1 echo     [!] Download failed: %~nx1
) else (
    echo   • %~nx1 already present. Skipping
)
goto :eof
```

**Key Features:**
- Skip if file exists (resume capability)
- Create parent directories automatically
- Progress indication
- Error handling

#### clone (Git with Error Handling)
```bash
# Bash version
get_node() {
  local dir=$1 url=$2 flag=${3:-}
  if [[ -d "custom_nodes/$dir" ]]; then
    echo " [SKIP] $dir"
  else
    echo " • cloning $dir"
    git clone $flag "$url" "custom_nodes/$dir"
  fi
}
```

```batch
REM Batch version
:clone
git clone %* >nul 2>&1
if errorlevel 1 echo   [!] Clone failed: %~1
goto :eof
```

### 2. CUDA Version Detection

From `install_triton_and_sageattention_auto.bat` - the most sophisticated detection:

```batch
REM Step 1: Get torch version and CUDA version
"%PY%" -c "import torch; print(torch.__version__); print(getattr(torch.version,'cuda',None) or 'unknown')"

REM Step 2: Parse build tag from torch version (e.g., 2.8.0+cu128)
for /f "tokens=2 delims=+ " %%Z in ("%TORCH_VER%") do set "TORCH_TAG=%%Z"

REM Step 3: Map CUDA versions (handle edge cases)
if /i "%TORCH_TAG%"=="cu129" set "CUSHORT=cu128"  REM Map 12.9 to 12.8 wheels

REM Step 4: Fallback to torch.version.cuda parsing
for /f "tokens=1,2 delims=." %%C in ("%CUDA_VER%") do (
  if "%%C"=="12" (
    if "%%D"=="9" set "CUSHORT=cu128"  REM 12.9 → cu128
    if "%%D"=="8" set "CUSHORT=cu128"  REM 12.8 → cu128
    if "%%D"=="6" set "CUSHORT=cu126"  REM 12.6 → cu126
    if "%%D"=="4" set "CUSHORT=cu124"  REM 12.4 → cu124
  )
)
```

**Bash equivalent:**
```bash
# From WAN-ANIMATE-RUNPOD.sh
GPU_VENDOR="$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1 || true)"
if [[ "${WANT_TORCH_STACK}" == "auto" ]]; then
  if [[ -n "$GPU_VENDOR" ]]; then
    WANT_TORCH_STACK="cu128"
  else
    WANT_TORCH_STACK="keep"
  fi
fi
```

### 3. SageAttention Installation

From `install_triton_and_sageattention_auto.bat` - comprehensive wheel matrix:

```batch
REM Strategy: Try wheels in order of specificity, then fall back to source

REM 1. Torch 2.9+ universal wheels (preferred)
if "%TMAJOR%"=="2" if %TMINORNUM% GEQ 9 (
  if "%CUSHORT%"=="cu130" set "SAGE_URL=...cu130torch2.9.0andhigher.post4..."
  if "%CUSHORT%"=="cu128" set "SAGE_URL=...cu128torch2.9.0andhigher.post4..."
)

REM 2. Exact version wheels for Torch 2.5-2.9
if not defined SAGE_URL (
  if "%TMINOR%"=="8" if "%CUSHORT%"=="cu128" set "SAGE_URL=...cu128torch2.8.0.post3..."
  if "%TMINOR%"=="7" if "%CUSHORT%"=="cu128" set "SAGE_URL=...cu128torch2.7.1.post3..."
  if "%TMINOR%"=="6" if "%CUSHORT%"=="cu126" set "SAGE_URL=...cu126torch2.6.0.post3..."
  if "%TMINOR%"=="5" if "%CUSHORT%"=="cu124" set "SAGE_URL=...cu124torch2.5.1.post3..."
)

REM 3. Try installing common wheels directly
if not defined SAGE_URL (
  for %%W in (cu130_wheel cu128_wheel) do (
    "%PY%" -m pip install --no-cache-dir "%%W" && set "SAGE_URL=%%W" && goto :DONE
  )
)

REM 4. Source fallback
if not defined SAGE_URL (
  "%PY%" -m pip install --no-build-isolation "sageattention==1.0.6" || \
  "%PY%" -m pip install --no-build-isolation "git+https://github.com/woct0rdho/SageAttention.git"
)
```

**Bash version (WAN-ANIMATE-RUNPOD.sh):**
```bash
echo "Installing SageAttention…"
set +e
if ! $PYTHON -c "import sageattention"; then
  if ! $PIP install --no-build-isolation --prefer-binary "sageattention==1.0.6"; then
    echo " • Wheel not available; trying GitHub source…"
    need_pkg build-essential python3-dev
    $PIP install --no-build-isolation "git+https://github.com/woct0rdho/SageAttention.git" || true
  fi
fi
set -e
```

**Key Pattern:** Wheel → Fallback wheel → Source (graceful degradation)

### 4. Triton Installation

From `install_triton_and_sageattention_auto.bat`:

```batch
REM Version depends on PyTorch version
set "TRITON_SPEC=triton-windows<3.5"
if "%TMAJOR%"=="2" if %TMINORNUM% GEQ 9 (
  set "TRITON_SPEC=triton-windows<3.6"
)
"%PY%" -m pip install --no-cache-dir --upgrade "%TRITON_SPEC%"

REM Install Python 3.13 include/libs for Triton compilation
set "URL=https://github.com/woct0rdho/triton-windows/releases/download/v3.0.0-windows.post1/python_3.13.2_include_libs.zip"
curl -L "%URL%" -o python_libs.zip
7z x python_libs.zip -aoa -o"%PYTHON_DIR%" >nul
```

**Linux version (WAN-ANIMATE-RUNPOD.sh):**
```bash
$PIP install --no-input "triton==${PIN_TRITON}"  # 3.4.0 typically
```

**Why Windows needs special handling:**
- Triton requires compilation on Windows
- Needs Python include files and libs
- Uses woct0rdho/triton-windows builds
- Version constraints depend on PyTorch

### 5. Safe Dependency Management

From `WAN-ANIMATE-MODELS-NODES_INSTALL.bat` - production-grade safety:

```batch
REM 1. Lock current environment BEFORE changes
%PIP% freeze > "%BACKUPS%\freeze_%TIMESTAMP%.txt"
copy "%BACKUPS%\freeze_%TIMESTAMP%.txt" "%LOCKFILE%"

REM 2. Sanitize node requirements (remove problematic directives)
powershell -File sanitize_reqs.ps1 -In "requirements.txt" -Out "clean.txt"

REM 3. Install with constraints to prevent breakage
%PIP% install --isolated -i https://pypi.org/simple ^
  --prefer-binary --no-cache-dir ^
  --upgrade-strategy only-if-needed ^
  --constraint "%LOCKFILE%" ^
  -r "clean.txt"

REM 4. If needed, force mode (ignores constraints)
if "%DO_FORCE%"=="1" (
  %PIP% install --isolated --ignore-installed -r "clean.txt"
)

REM 5. Restore capability
if "%DO_RESTORE%"=="1" (
  %PIP% install --force-reinstall -r "%LAST_FREEZE%"
)
```

**PowerShell sanitizer (embedded in script):**
```powershell
# Remove problematic directives that break pip installs
$lines = Get-Content -LiteralPath $In -Raw -Encoding UTF8
$lines = $lines -split "`r?`n"
$lines = $lines | Where-Object { $_ -ne '' -and $_ -notmatch '^\s*#' }
$lines = $lines | Where-Object { $_ -notmatch '^\s*--(find-links|extra-index-url)\b' }
$lines = $lines | Where-Object { $_ -notmatch '^\s*-r\b' }  # Remove -r includes
$lines = $lines | ForEach-Object { $_ -replace '\s*@\s*file:(//)?/[^ \t]+','' }  # Remove file:// wheels
$lines = $lines | ForEach-Object { $_ -replace '\s*@\s*[A-Za-z]:\\[^\s]+','' }  # Remove Windows paths
$lines | Set-Content -LiteralPath $Out -Encoding UTF8
```

**Key Safety Features:**
- Timestamped backups before every change
- Constraint locks prevent version conflicts
- Sanitization removes problematic pip directives
- `--isolated` prevents user config interference
- `only-if-needed` upgrade strategy (conservative)
- Optional force mode when needed
- Restore to last known-good state

**Bash equivalent (WAN-ANIMATE-RUNPOD.sh):**
```bash
# More tolerant approach for RunPod
for dir in "${REQUIRED_NODES[@]}"; do
  req="custom_nodes/$dir/requirements.txt"
  [[ -f "$req" ]] || continue
  echo " • $req"
  pushd "$(dirname "$req")" >/dev/null
  $PIP install --no-input --prefer-binary --no-build-isolation \
    --upgrade-strategy only-if-needed -r requirements.txt \
  || $PIP install --no-input --prefer-binary -r requirements.txt || true
  popd >/dev/null
done
```

### 6. Environment Variable Hygiene

All scripts set these for consistent behavior:

```batch
REM Batch version
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PYTHONNOUSERSITE=1"
set "PYTHONUTF8=1"
set "PIP_CONFIG_FILE=NUL"
set "PIP_FIND_LINKS="
set "PIP_NO_INDEX="
```

```bash
# Bash version
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_ROOT_USER_ACTION=ignore
export PYTHONUNBUFFERED=1
export HF_HUB_ENABLE_HF_TRANSFER=1
export PYTHONNOUSERSITE=1
```

**Why this matters:**
- `PYTHONNOUSERSITE=1` prevents user site-packages interference
- `PIP_DISABLE_PIP_VERSION_CHECK=1` reduces pip noise
- `PYTHONUTF8=1` handles international characters (Windows)
- `HF_HUB_ENABLE_HF_TRANSFER=1` faster HuggingFace downloads
- `PIP_CONFIG_FILE=NUL` ignores user pip config

### 7. Dependency Pinning

From `WAN-ANIMATE-RUNPOD.sh` - production pins:

```bash
# Known-good versions for WAN Animate 2.2
PIN_XFORMERS="${PIN_XFORMERS:-0.0.32.post2}"
PIN_TRITON="${PIN_TRITON:-3.4.0}"
PIN_NUMPY="${PIN_NUMPY:-2.2.6}"
PIN_OPENCV="${PIN_OPENCV:-4.12.0.88}"
PIN_DIFFUSERS="${PIN_DIFFUSERS:-0.35.2}"
PIN_TRANSFORMERS="${PIN_TRANSFORMERS:-4.57.1}"
PIN_PEFT="${PIN_PEFT:-0.17.1}"
PIN_ACCELERATE="${PIN_ACCELERATE:-1.10.1}"
PIN_SAFETENSORS="${PIN_SAFETENSORS:-0.6.2}"
PIN_EINOPS="${PIN_EINOPS:-0.8.1}"
PIN_SENTENCEPIECE="${PIN_SENTENCEPIECE:-0.2.1}"
PIN_PILLOW_MIN="${PIN_PILLOW_MIN:-10.3.0}"

# Install with exact versions
$PIP install --no-input \
  "xformers==${PIN_XFORMERS}" \
  "triton==${PIN_TRITON}" \
  "numpy==${PIN_NUMPY}" \
  "opencv-python==${PIN_OPENCV}" \
  "diffusers==${PIN_DIFFUSERS}" \
  "transformers==${PIN_TRANSFORMERS}" \
  "peft==${PIN_PEFT}" \
  "accelerate==${PIN_ACCELERATE}"
```

**Why pin versions?**
- Reproducible builds
- Avoid breaking changes
- Environment variables allow overrides
- Can test newer versions before committing

### 8. PyTorch Installation Strategy

From `WAN-ANIMATE-RUNPOD.sh` - clean install:

```bash
# Clean conflicting packages first
$PIP uninstall -y torch torchvision torchaudio xformers triton numpy \
  opencv-python opencv-python-headless diffusers accelerate \
  transformers peft || true

# Install torch stack with correct index
$PIP install --no-input --upgrade-strategy only-if-needed \
  --index-url "https://download.pytorch.org/whl/${CUDA_TAG}" \
  --extra-index-url https://pypi.org/simple \
  "torch==${TORCH_VERSION}+${CUDA_TAG}" \
  "torchvision==${TORCHVISION_VERSION}+${CUDA_TAG}" \
  "torchaudio==${TORCHAUDIO_VERSION}+${CUDA_TAG}"
```

**Key Pattern:**
- Uninstall conflicts first (clean slate)
- Use PyTorch's wheel index as primary
- PyPI as fallback (`--extra-index-url`)
- Explicit CUDA tag in version (e.g., `2.8.0+cu128`)

### 9. Model Organization

All scripts organize models by type:

```
models/
├── clip_vision/
│   └── clip_vision_h.safetensors
├── detection/
│   ├── vitpose_h_wholebody_data.bin
│   ├── vitpose_h_wholebody_model.onnx
│   ├── vitpose-l-wholebody.onnx
│   └── yolov10m.onnx
├── diffusion_models/
│   └── Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors
├── loras/
│   ├── lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors
│   └── WanAnimate_relight_lora_fp16.safetensors
├── sams/
│   └── SeC-4B-fp16.safetensors
├── text_encoders/
│   └── umt5-xxl-enc-bf16.safetensors
└── vae/
    └── Wan2_1_VAE_bf16.safetensors
```

### 10. Node Installation Pattern

All scripts use the same node list:

```bash
REQUIRED_NODES=(
  "ComfyUI-Manager"              # ltdrdata/ComfyUI-Manager
  "ComfyUI-WanVideoWrapper"      # kijai/ComfyUI-WanVideoWrapper
  "rgthree-comfy"                # rgthree/rgthree-comfy
  "ComfyUI-KJNodes"              # kijai/ComfyUI-KJNodes
  "ComfyUI-VideoHelperSuite"     # Kosinkadink/ComfyUI-VideoHelperSuite
  "ComfyUI-segment-anything-2"   # kijai/ComfyUI-segment-anything-2
  "Comfyui-SecNodes"             # 9nate-drake/Comfyui-SecNodes
  "ComfyUI-WanAnimatePreprocess" # kijai/ComfyUI-WanAnimatePreprocess
)
```

## 🚀 Recommended Implementation for RunPod

### Dockerfile Best Practices

```dockerfile
# 1. Clean environment variables
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONNOUSERSITE=1
ENV PYTHONUNBUFFERED=1
ENV HF_HUB_ENABLE_HF_TRANSFER=1

# 2. Uninstall conflicts before installing torch
RUN pip3 uninstall -y torch torchvision torchaudio || true

# 3. Install PyTorch with correct index
RUN pip3 install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/${CUDA_TAG} \
    --extra-index-url https://pypi.org/simple \
    torch==${TORCH_VERSION}+${CUDA_TAG} \
    torchvision==${TORCHVISION_VERSION}+${CUDA_TAG} \
    torchaudio==${TORCHAUDIO_VERSION}+${CUDA_TAG}

# 4. Pin critical dependencies
RUN pip3 install --no-cache-dir \
    xformers==0.0.32.post2 \
    triton==3.4.0 \
    numpy==2.2.6 \
    diffusers==0.35.2 \
    transformers==4.57.1

# 5. SageAttention with fallback
RUN pip3 install --no-build-isolation --prefer-binary sageattention==1.0.6 || \
    pip3 install --no-build-isolation git+https://github.com/woct0rdho/SageAttention.git || \
    true
```

### Handler Integration

Your `handler.py` already implements the key patterns:

✅ Network volume detection with fallback
✅ Model path auto-discovery
✅ Clean error handling
✅ Execution timing
✅ Image URL generation

**Additional improvements based on installer patterns:**

```python
# Add environment hygiene
import os
os.environ["PYTHONNOUSERSITE"] = "1"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

# Add version reporting (like installer verification)
def report_versions():
    import torch
    import sys
    print(f"Python: {sys.version}")
    print(f"Torch: {torch.__version__}")
    print(f"CUDA: {torch.version.cuda}")
    print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")
    try:
        import xformers
        print(f"xformers: {xformers.__version__}")
    except:
        print("xformers: not installed")
    try:
        import sageattention
        print(f"SageAttention: {getattr(sageattention, '__version__', 'installed')}")
    except:
        print("SageAttention: not installed")
```

## 📊 Comparison Matrix

| Pattern | QWEN | WAN-RUNPOD | WAN-MANAGER | Triton/Sage | Models-Nodes | Our Setup |
|---------|------|------------|-------------|-------------|--------------|-----------|
| Helper functions (grab/clone) | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| Skip existing files | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| CUDA detection | ❌ | Basic | ❌ | Advanced | ❌ | Multi-arch |
| SageAttention | ❌ | Fallback | Wheel | Matrix | ❌ | Can add |
| Triton | ❌ | Pinned | Windows | Advanced | ❌ | Can add |
| Dependency locking | ❌ | Pins | ❌ | ❌ | Advanced | ❌ |
| Rollback capability | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| Network volumes | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| Environment isolation | Basic | ✅ | Basic | Basic | Advanced | ✅ |

## 💡 Key Takeaways

1. **Use helper functions** - Consistent download/clone patterns
2. **Skip existing files** - Resume capability, faster reruns
3. **Detect CUDA properly** - Parse torch version, handle edge cases
4. **Install SageAttention carefully** - Wheel matrix with source fallback
5. **Pin dependencies** - Reproducible builds, fewer surprises
6. **Lock environments** - Freeze before changes, rollback capability
7. **Sanitize requirements** - Remove problematic pip directives
8. **Isolated pip** - Prevent user config interference
9. **Clean uninstalls first** - Remove conflicts before installing
10. **Verify after install** - Import test, version reporting

## 🎯 What We Already Have Working

✅ Multi-architecture Docker builds (Ada/Blackwell)
✅ Network volume integration with fallback
✅ Model path auto-discovery
✅ Clean handler logic
✅ Local testing workflow
✅ Deployment automation

## 🔧 Optional Enhancements

Based on these installer patterns, we could add:

1. **SageAttention support** - Use the wheel matrix pattern
2. **Dependency locking** - Freeze environment for reproducibility
3. **Version reporting** - Show torch/CUDA/xformers versions on start
4. **Rollback capability** - Save working states
5. **Sanitized requirements** - If using custom nodes

**But:** Our current setup already follows the core pattern these scripts use:
- Lightweight handler + network volumes for production
- Clean local testing without Docker complexity
- Multi-architecture support with correct CUDA versions

The full installers are for **local development setups**, while RunPod benefits from the **simplified handler-only approach** we've implemented!
