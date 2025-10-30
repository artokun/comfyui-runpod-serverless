# Custom Nodes Management Guide

Automatically install and manage ComfyUI custom nodes with version control using a simple declarative format.

## Quick Start

1. **Edit `nodes.txt`** - Uncomment nodes you want to install:

```
# Uncomment nodes you need:
https://github.com/ltdrdata/ComfyUI-Manager.git @ latest
https://github.com/kijai/ComfyUI-KJNodes.git @ v1.0.5
```

2. **Start container** - Nodes install automatically:

```bash
docker compose up
```

That's it! Custom nodes are installed on container start if they don't already exist.

## Why This Approach?

### vs. ComfyUI Manager
- ✅ **Declarative** - Nodes defined in version-controlled file
- ✅ **Reproducible** - Same nodes, same versions, every time
- ✅ **CI/CD friendly** - No manual clicking in UI
- ✅ **Version pinning** - Lock to specific versions

### vs. Snapshot System (Official RunPod)
- ✅ **Not buggy** - Snapshots are known to have issues
- ✅ **Git-based** - Proper version control, not JSON dumps
- ✅ **Flexible** - Mix latest, nightly, and pinned versions
- ✅ **Transparent** - Clear what version is installed

## Format

Simple syntax: `URL @ version`

```
<git_url> @ <version>
```

### Version Specifiers:

| Specifier | Description | Use Case | Example |
|-----------|-------------|----------|---------|
| `@latest` | Latest stable release (git tag) | Production stability | `@ latest` |
| `@nightly` | Latest commit on default branch | Bleeding edge features | `@ nightly` |
| `@v1.2.3` | Specific version tag (semver) | Pin exact version | `@ v1.0.5` |
| `@commit` | Specific commit hash | Debug/test specific commit | `@ abc123def` |
| `@branch` | Specific branch name | Test development branches | `@ develop` |

### Examples:

```
# Latest stable release
https://github.com/ltdrdata/ComfyUI-Manager.git @ latest

# Specific version
https://github.com/kijai/ComfyUI-KJNodes.git @ v1.0.5

# Latest development
https://github.com/cubiq/ComfyUI_IPAdapter_plus.git @ nightly

# Specific branch
https://github.com/user/custom-node.git @ main

# Specific commit
https://github.com/user/custom-node.git @ abc123def456
```

## Version Specifier Details

### `@latest` - Latest Stable Release

Uses the latest git tag:
```
https://github.com/kijai/ComfyUI-KJNodes.git @ latest
```

**Behavior:**
- Finds the most recent git tag
- Checks out that tag
- If no tags exist, falls back to `@nightly`

**Best for:**
- Production deployments
- When you want stable, tested releases
- Projects that follow semantic versioning

### `@nightly` - Latest Development

Uses the latest commit on the default branch:
```
https://github.com/cubiq/ComfyUI_IPAdapter_plus.git @ nightly
```

**Behavior:**
- Checks out default branch (main/master)
- Pulls latest commits
- Always updates on container start

**Best for:**
- Testing new features
- Development environments
- Nodes that don't use release tags
- When you need the absolute latest

### `@vX.Y.Z` - Specific Version

Pins to a specific semantic version tag:
```
https://github.com/kijai/ComfyUI-KJNodes.git @ v1.0.5
https://github.com/user/repo.git @ 2.1.0
```

**Behavior:**
- Checks out exact tag
- Never updates unless you change the version
- Works with or without 'v' prefix

**Best for:**
- Production deployments needing stability
- Avoiding breaking changes
- Reproducible builds
- CI/CD pipelines

### `@commit` - Specific Commit Hash

Pins to an exact commit:
```
https://github.com/user/repo.git @ abc123def456789
```

**Behavior:**
- Checks out specific commit
- Never updates
- Works with full or short (7+ chars) commit hash

**Best for:**
- Debugging specific issues
- Testing patches
- Absolute reproducibility
- When a tag doesn't exist for needed code

### `@branch` - Branch Name

Uses a specific branch:
```
https://github.com/user/repo.git @ develop
https://github.com/user/repo.git @ feature/new-nodes
```

**Behavior:**
- Checks out specified branch
- Pulls latest on that branch
- Updates on container restart

**Best for:**
- Testing pre-release features
- Development branches
- Feature branches
- Beta testing

## Manual Installation/Testing

Test your nodes.txt before running the container:

```bash
# Validate format only
python install_nodes.py --validate-only

# Dry run (show what would be installed)
python install_nodes.py --dry-run

# Install nodes manually
python install_nodes.py --verbose

# Force reinstall
python install_nodes.py --force

# Skip dependency installation
python install_nodes.py --skip-deps
```

## Usage Patterns

### Starter Pack (Essential Nodes)

```
# Package manager
https://github.com/ltdrdata/ComfyUI-Manager.git @ latest

# Utility nodes
https://github.com/kijai/ComfyUI-KJNodes.git @ latest
```

### Production Setup (Pinned Versions)

```
# Pin all nodes to specific versions for reproducibility
https://github.com/ltdrdata/ComfyUI-Manager.git @ v2.47
https://github.com/kijai/ComfyUI-KJNodes.git @ v1.0.5
https://github.com/cubiq/ComfyUI_IPAdapter_plus.git @ v1.2.3
https://github.com/Fannovel16/comfyui_controlnet_aux.git @ v1.0.0
```

### Development Setup (Mix of Stable and Bleeding Edge)

```
# Core nodes: stable
https://github.com/ltdrdata/ComfyUI-Manager.git @ latest
https://github.com/kijai/ComfyUI-KJNodes.git @ latest

# Testing new features: nightly
https://github.com/cubiq/ComfyUI_IPAdapter_plus.git @ nightly
https://github.com/user/experimental-nodes.git @ develop
```

### WAN Animate 2.2 Complete Setup

```
# Required nodes for WAN Animate 2.2
https://github.com/ltdrdata/ComfyUI-Manager.git @ latest
https://github.com/kijai/ComfyUI-WanVideoWrapper.git @ latest
https://github.com/rgthree/rgthree-comfy.git @ latest
https://github.com/kijai/ComfyUI-KJNodes.git @ latest
https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git @ latest
https://github.com/kijai/ComfyUI-segment-anything-2.git @ latest
https://github.com/9nate-drake/Comfyui-SecNodes.git @ latest
https://github.com/kijai/ComfyUI-WanAnimatePreprocess.git @ latest
```

## How It Works

### On Container Start

1. Checks if `nodes.txt` exists
2. Parses for active (uncommented) entries
3. For each node:
   - Clones repository if missing
   - Updates repository if already installed
   - Checks out specified version
   - Installs dependencies from `requirements.txt`
   - Updates git submodules
4. Continues to start ComfyUI

### Update Behavior

| Scenario | Behavior |
|----------|----------|
| Node doesn't exist | Clones and installs |
| Node exists, same version | Skips (fast startup) |
| Node exists, different version | Updates to new version |
| Version is `@nightly` | Always updates |
| Version is `@latest` | Checks for newer tag |

## Troubleshooting

### "Invalid format" Error

Check your syntax:
```
✓ https://github.com/user/repo.git @ latest
✗ https://github.com/user/repo.git@latest   # Missing spaces
✗ https://github.com/user/repo @ latest     # Missing .git
```

### "Clone failed" Error

**Common causes:**
1. Invalid URL
2. Private repository (needs authentication)
3. Network issues
4. Repository doesn't exist

**Solutions:**
```bash
# Test URL manually
git clone https://github.com/user/repo.git

# Check if repo exists
curl -I https://github.com/user/repo

# For private repos, use SSH or tokens
https://token@github.com/user/private-repo.git @ latest
```

### "Checkout failed" Error

**Common causes:**
1. Tag doesn't exist
2. Branch doesn't exist
3. Commit hash is invalid

**Solutions:**
```bash
# Check available tags
git ls-remote --tags https://github.com/user/repo.git

# Check available branches
git ls-remote --heads https://github.com/user/repo.git

# Verify commit exists
git ls-remote https://github.com/user/repo.git | grep abc123
```

### Dependencies Fail to Install

**Common causes:**
1. Missing system dependencies
2. Conflicting package versions
3. Pip timeout

**Solutions:**
```bash
# Install system dependencies first (in Dockerfile)
RUN apt-get install -y build-essential python3-dev

# Use --skip-deps to skip dependency installation
python install_nodes.py --skip-deps

# Install dependencies manually
pip install -r ComfyUI/custom_nodes/node-name/requirements.txt
```

### Node Conflicts

Some nodes conflict with each other:

**Solution:**
```
# Comment out conflicting node
# https://github.com/user/conflicting-node.git @ latest

# Use alternative
https://github.com/user/alternative-node.git @ latest
```

## Advanced Usage

### Mixing Versions

```
# Stable core
https://github.com/ltdrdata/ComfyUI-Manager.git @ v2.47

# Latest features
https://github.com/kijai/ComfyUI-KJNodes.git @ latest

# Bleeding edge experimental
https://github.com/user/experimental.git @ nightly

# Testing specific commit
https://github.com/user/testing.git @ abc123def
```

### Upgrading Nodes

**To upgrade pinned versions:**

```bash
# 1. Check current version
cd ComfyUI/custom_nodes/ComfyUI-KJNodes
git describe --tags

# 2. Check available versions
git fetch --tags
git tag -l

# 3. Update nodes.txt
# Change: @ v1.0.5
# To:     @ v1.0.6

# 4. Restart container
docker compose restart
```

**To upgrade `@latest` nodes:**

Just restart the container - it checks for newer tags automatically.

### Rolling Back

**If a node update breaks your workflow:**

```bash
# 1. Find previous version
cd ComfyUI/custom_nodes/broken-node
git log --oneline
git tag -l

# 2. Update nodes.txt to previous version
# https://github.com/user/broken-node.git @ v1.0.4

# 3. Restart with --force to reinstall
python install_nodes.py --force --comfyui-dir ./ComfyUI
```

### Private Repositories

**Using personal access tokens:**

```
# GitHub
https://YOUR_TOKEN@github.com/user/private-repo.git @ latest

# GitLab
https://oauth2:YOUR_TOKEN@gitlab.com/user/private-repo.git @ latest
```

**Using SSH (advanced):**
- Mount SSH keys into container
- Use SSH URLs instead of HTTPS

## Integration with RunPod

### Option 1: Bake Nodes into Image

Uncomment nodes in `nodes.txt` and deploy:
```bash
./deploy.sh ada
```

Nodes are installed during image build and baked in.

**Pros:**
- Instant startup on RunPod
- No network dependency
- Reproducible

**Cons:**
- Larger image size
- Slower builds
- Must rebuild to change nodes

### Option 2: Install on First Run

Leave `nodes.txt` mostly commented in image, create custom `nodes.txt` on RunPod volume:
```bash
# On RunPod network volume
cat > /runpod-volume/nodes.txt << EOF
https://github.com/ltdrdata/ComfyUI-Manager.git @ latest
https://github.com/kijai/ComfyUI-KJNodes.git @ latest
EOF
```

**Pros:**
- Smaller image
- Easy to update nodes
- Flexible

**Cons:**
- First run is slower
- Network dependency

## Best Practices

1. **Production: Pin versions** - Use `@v1.2.3` for stability
2. **Development: Use latest** - Use `@latest` or `@nightly` for features
3. **Document your choices** - Add comments explaining why you pinned versions
4. **Test locally first** - Run `--dry-run` before deploying
5. **Group by purpose** - Organize nodes.txt with comment sections
6. **Version control nodes.txt** - Track changes in git
7. **Start minimal** - Only install nodes you actually use
8. **Review dependencies** - Check what each node installs

## Example Workflows

### Clean Setup

```bash
# 1. Edit nodes.txt
nano nodes.txt

# 2. Uncomment nodes you need
https://github.com/ltdrdata/ComfyUI-Manager.git @ latest
https://github.com/kijai/ComfyUI-KJNodes.git @ latest

# 3. Start
docker compose up
```

### Update All Nodes

```bash
# For @latest nodes: Just restart
docker compose restart

# For pinned versions: Update nodes.txt then restart
nano nodes.txt  # Change v1.0.5 -> v1.0.6
docker compose restart
```

### Testing New Node

```bash
# 1. Add to nodes.txt
echo "https://github.com/user/new-node.git @ nightly" >> nodes.txt

# 2. Install without rebuilding
python install_nodes.py --comfyui-dir ./ComfyUI

# 3. Test in ComfyUI
# ...

# 4. If good, commit nodes.txt
git add nodes.txt
git commit -m "Add new-node for testing"
```

## Common Node Collections

### Essential QoL Pack
```
https://github.com/ltdrdata/ComfyUI-Manager.git @ latest
https://github.com/kijai/ComfyUI-KJNodes.git @ latest
https://github.com/ltdrdata/ComfyUI-Impact-Pack.git @ latest
```

### Image Generation Pack
```
https://github.com/cubiq/ComfyUI_IPAdapter_plus.git @ latest
https://github.com/Fannovel16/comfyui_controlnet_aux.git @ latest
https://github.com/ltdrdata/ComfyUI-Impact-Pack.git @ latest
```

### Video Generation Pack
```
https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git @ latest
https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git @ latest
https://github.com/Kosinkadink/ComfyUI-Advanced-ControlNet.git @ latest
```

### FLUX Pack
```
https://github.com/black-forest-labs/ComfyUI-Flux.git @ latest
https://github.com/city96/ComfyUI-GGUF.git @ latest
https://github.com/kijai/ComfyUI-Florence2.git @ latest
```

## Performance Notes

### Installation Times (approximate)

| Node | Size | Time | Dependencies |
|------|------|------|--------------|
| ComfyUI-Manager | ~5MB | 10-20s | Minimal |
| KJNodes | ~10MB | 20-40s | NumPy, CV2 |
| Impact-Pack | ~50MB | 1-2min | Many |
| VideoHelperSuite | ~20MB | 30-60s | FFmpeg deps |

### Tips for Faster Installation

1. **Install in parallel** (already done automatically)
2. **Use --skip-deps** during testing
3. **Cache Docker layers** - nodes install once per build
4. **Pre-download frequently used nodes** - bake into image

## Summary

The custom nodes management system provides:

- ✅ **Declarative configuration** - `nodes.txt` is your source of truth
- ✅ **Version control** - Pin to specific versions or track latest
- ✅ **Automatic installation** - Nodes install on container start
- ✅ **Git-based** - Proper version control, not buggy snapshots
- ✅ **Flexible** - Mix latest, nightly, and pinned versions
- ✅ **Reproducible** - Same nodes, same versions, every time

Edit `nodes.txt`, uncomment what you need, and let the system handle the rest!
