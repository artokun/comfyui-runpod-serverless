# Custom Nodes Management Guide

Automatically install and manage ComfyUI custom nodes with version control using a unified YAML configuration.

## Quick Start

1. **Edit `config.yml`** - Add nodes you want to install:

```yaml
nodes:
  - url: https://github.com/ltdrdata/ComfyUI-Manager.git
    version: latest
  - url: https://github.com/kijai/ComfyUI-KJNodes.git
    version: v1.0.5
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

## Configuration Format

Edit `config.yml` to define your custom nodes:

```yaml
nodes:
  - url: <git_url>
    version: <version_specifier>
```

### Version Specifiers:

| Specifier | Description | Use Case | Example |
|-----------|-------------|----------|---------|
| `latest` | Latest stable release (git tag) | Production stability | `version: latest` |
| `nightly` | Latest commit on default branch | Bleeding edge features | `version: nightly` |
| `v1.2.3` | Specific version tag (semver) | Pin exact version | `version: v1.0.5` |
| `abc123` | Specific commit hash | Debug/test specific commit | `version: abc123def` |
| `develop` | Specific branch name | Test development branches | `version: develop` |

### Examples:

```yaml
nodes:
  # Latest stable release
  - url: https://github.com/ltdrdata/ComfyUI-Manager.git
    version: latest

  # Specific version
  - url: https://github.com/kijai/ComfyUI-KJNodes.git
    version: v1.0.5

  # Latest development
  - url: https://github.com/cubiq/ComfyUI_IPAdapter_plus.git
    version: nightly

  # Specific branch
  - url: https://github.com/user/custom-node.git
    version: main

  # Specific commit
  - url: https://github.com/user/custom-node.git
    version: abc123def456
```

## Version Specifier Details

### `latest` - Latest Stable Release

Uses the latest git tag:
```yaml
- url: https://github.com/kijai/ComfyUI-KJNodes.git
  version: latest
```

**Behavior:**
- Finds the most recent git tag
- Checks out that tag
- If no tags exist, falls back to `nightly`

**Best for:**
- Production deployments
- When you want stable, tested releases
- Projects that follow semantic versioning

### `nightly` - Latest Development

Uses the latest commit on the default branch:
```yaml
- url: https://github.com/cubiq/ComfyUI_IPAdapter_plus.git
  version: nightly
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

### `vX.Y.Z` - Specific Version

Pins to a specific semantic version tag:
```yaml
- url: https://github.com/kijai/ComfyUI-KJNodes.git
  version: v1.0.5
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

### Commit Hash - Specific Commit

Pins to an exact commit:
```yaml
- url: https://github.com/user/repo.git
  version: abc123def456789
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

### Branch Name - Specific Branch

Uses a specific branch:
```yaml
- url: https://github.com/user/repo.git
  version: develop
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

Test your config.yml before running the container:

```bash
# Dry run (show what would be installed)
python install_nodes.py --dry-run

# Install nodes manually
python install_nodes.py

# Force reinstall
python install_nodes.py --force

# Use custom config location
python install_nodes.py --config /path/to/config.yml
```

## Usage Patterns

### Starter Pack (Essential Nodes)

```yaml
nodes:
  # Package manager
  - url: https://github.com/ltdrdata/ComfyUI-Manager.git
    version: latest

  # Utility nodes
  - url: https://github.com/kijai/ComfyUI-KJNodes.git
    version: latest
```

### Production Setup (Pinned Versions)

```yaml
nodes:
  # Pin all nodes to specific versions for reproducibility
  - url: https://github.com/ltdrdata/ComfyUI-Manager.git
    version: v2.47
  - url: https://github.com/kijai/ComfyUI-KJNodes.git
    version: v1.0.5
  - url: https://github.com/cubiq/ComfyUI_IPAdapter_plus.git
    version: v1.2.3
  - url: https://github.com/Fannovel16/comfyui_controlnet_aux.git
    version: v1.0.0
```

### Development Setup (Mix of Stable and Bleeding Edge)

```yaml
nodes:
  # Core nodes: stable
  - url: https://github.com/ltdrdata/ComfyUI-Manager.git
    version: latest
  - url: https://github.com/kijai/ComfyUI-KJNodes.git
    version: latest

  # Testing new features: nightly
  - url: https://github.com/cubiq/ComfyUI_IPAdapter_plus.git
    version: nightly
  - url: https://github.com/user/experimental-nodes.git
    version: develop
```

### WAN Animate 2.2 Complete Setup

```yaml
nodes:
  # Required nodes for WAN Animate 2.2
  - url: https://github.com/ltdrdata/ComfyUI-Manager.git
    version: latest
  - url: https://github.com/kijai/ComfyUI-WanVideoWrapper.git
    version: latest
  - url: https://github.com/rgthree/rgthree-comfy.git
    version: latest
  - url: https://github.com/kijai/ComfyUI-KJNodes.git
    version: latest
  - url: https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
    version: latest
  - url: https://github.com/kijai/ComfyUI-segment-anything-2.git
    version: latest
  - url: https://github.com/9nate-drake/Comfyui-SecNodes.git
    version: latest
  - url: https://github.com/kijai/ComfyUI-WanAnimatePreprocess.git
    version: latest
```

## How It Works

### On Container Start

1. Checks if `config.yml` exists
2. Parses nodes section for entries
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
| Version is `nightly` | Always updates |
| Version is `latest` | Checks for newer tag |

## Troubleshooting

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
https://token@github.com/user/private-repo.git
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

# Install dependencies manually
pip install -r ComfyUI/custom_nodes/node-name/requirements.txt
```

### Node Conflicts

Some nodes conflict with each other. If you encounter issues, comment out or remove the conflicting node from `config.yml`.

## Advanced Usage

### Mixing Versions

```yaml
nodes:
  # Stable core
  - url: https://github.com/ltdrdata/ComfyUI-Manager.git
    version: v2.47

  # Latest features
  - url: https://github.com/kijai/ComfyUI-KJNodes.git
    version: latest

  # Bleeding edge experimental
  - url: https://github.com/user/experimental.git
    version: nightly

  # Testing specific commit
  - url: https://github.com/user/testing.git
    version: abc123def
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

# 3. Update config.yml
# Change version: v1.0.5 to version: v1.0.6

# 4. Restart container
docker compose restart
```

**To upgrade `latest` nodes:**

Just restart the container - it checks for newer tags automatically.

### Rolling Back

**If a node update breaks your workflow:**

```bash
# 1. Find previous version
cd ComfyUI/custom_nodes/broken-node
git log --oneline
git tag -l

# 2. Update config.yml to previous version
# Change to version: v1.0.4

# 3. Reinstall
python install_nodes.py --force --comfyui-dir ./ComfyUI
```

### Private Repositories

**Using personal access tokens:**

```yaml
nodes:
  # GitHub
  - url: https://YOUR_TOKEN@github.com/user/private-repo.git
    version: latest

  # GitLab
  - url: https://oauth2:YOUR_TOKEN@gitlab.com/user/private-repo.git
    version: latest
```

**Using SSH (advanced):**
- Mount SSH keys into container
- Use SSH URLs instead of HTTPS

## Integration with RunPod

### Option 1: Bake Nodes into Image

Add nodes to `config.yml` and deploy:
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

Create custom `config.yml` on RunPod volume:
```bash
# On RunPod network volume
cat > /runpod-volume/config.yml << EOF
nodes:
  - url: https://github.com/ltdrdata/ComfyUI-Manager.git
    version: latest
  - url: https://github.com/kijai/ComfyUI-KJNodes.git
    version: latest
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

1. **Production: Pin versions** - Use specific versions for stability
2. **Development: Use latest** - Use `latest` or `nightly` for features
3. **Document your choices** - Add YAML comments explaining why you pinned versions
4. **Test locally first** - Run `--dry-run` before deploying
5. **Group by purpose** - Organize config.yml with comments
6. **Version control config.yml** - Track changes in git
7. **Start minimal** - Only install nodes you actually use
8. **Review dependencies** - Check what each node installs

## Example config.yml with Comments

```yaml
# Custom Nodes Configuration

nodes:
  # ============================================================================
  # Essential QoL Pack
  # ============================================================================

  - url: https://github.com/ltdrdata/ComfyUI-Manager.git
    version: latest  # Package manager for ComfyUI

  - url: https://github.com/kijai/ComfyUI-KJNodes.git
    version: latest  # Utility nodes

  # ============================================================================
  # Image Generation Pack
  # ============================================================================

  - url: https://github.com/cubiq/ComfyUI_IPAdapter_plus.git
    version: latest  # IP Adapter nodes

  - url: https://github.com/Fannovel16/comfyui_controlnet_aux.git
    version: latest  # ControlNet preprocessors

  # ============================================================================
  # Video Generation Pack
  # ============================================================================

  - url: https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git
    version: latest  # AnimateDiff nodes

  - url: https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
    version: latest  # Video utilities
```

## Summary

The custom nodes management system provides:

- ✅ **Declarative configuration** - `config.yml` is your source of truth
- ✅ **Version control** - Pin to specific versions or track latest
- ✅ **Automatic installation** - Nodes install on container start
- ✅ **Git-based** - Proper version control, not buggy snapshots
- ✅ **Flexible** - Mix latest, nightly, and pinned versions
- ✅ **Reproducible** - Same nodes, same versions, every time

Edit `config.yml`, define your nodes, and let the system handle the rest!
