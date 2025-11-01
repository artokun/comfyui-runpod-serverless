# Versioning and Auto-Deploy Guide

This project uses automated semantic versioning and deployment via GitHub Actions.

## How It Works

### 1. Conventional Commits Determine Version

When you merge to `main`, the version is automatically bumped based on commit messages:

| Commit Type | Version Bump | Example |
|-------------|--------------|---------|
| `feat:` | Minor (0.x.0) | `feat: add S3 upload support` → v0.2.0 |
| `fix:` | Patch (0.0.x) | `fix: handle timeout errors` → v0.1.1 |
| `feat!:` or `BREAKING CHANGE:` | Major (x.0.0) | `feat!: redesign API` → v1.0.0 |
| `docs:`, `chore:`, etc. | No bump | Documentation changes |

### 2. Auto-Deploy on Merge

When changes are merged to `main`:

1. **Version is calculated** from conventional commits
2. **Git tag is created** (e.g., `v1.2.3`)
3. **Docker images are built** for both Ada and Blackwell
4. **Images are pushed** to Docker Hub with tags:
   - `artokun/comfyui-runpod:v1.2.3-ada`
   - `artokun/comfyui-runpod:v1.2.3-blackwell`
   - `artokun/comfyui-runpod:ada` (updated to latest)
   - `artokun/comfyui-runpod:blackwell` (updated to latest)
5. **GitHub Release is created** with changelog

## Setup (One-Time)

### 1. Create Docker Hub Access Token

1. Go to https://hub.docker.com/settings/security
2. Click "New Access Token"
3. Name: `github-actions-deploy`
4. Permissions: **Read, Write, Delete**
5. Copy the token

### 2. Add GitHub Secrets

Go to your repo: **Settings** → **Secrets and variables** → **Actions**

Add these secrets:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `DOCKER_USERNAME` | `artokun` | Your Docker Hub username |
| `DOCKER_TOKEN` | `[your token]` | Access token from step 1 |

### 3. Done!

That's it! Now every merge to `main` will auto-deploy.

## Usage Examples

### Example 1: Bug Fix

```bash
git commit -m "fix: resolve timeout in ComfyUI polling"
```

**Result:** Patch bump (e.g., v0.1.0 → v0.1.1)

### Example 2: New Feature

```bash
git commit -m "feat: add WebSocket support for real-time progress"
```

**Result:** Minor bump (e.g., v0.1.1 → v0.2.0)

### Example 3: Breaking Change

```bash
git commit -m "feat!: redesign config.yml structure

BREAKING CHANGE: config.yml now requires YAML format, .txt files no longer supported"
```

**Result:** Major bump (e.g., v0.2.0 → v1.0.0)

### Example 4: Multiple Commits

```bash
git commit -m "docs: update README"
git commit -m "fix: handle edge case in model parser"
git commit -m "feat: add optional model flag"
```

**Result:** Minor bump (highest priority = feat)

## Conventional Commits Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

- **feat:** New feature
- **fix:** Bug fix
- **docs:** Documentation changes
- **style:** Code style changes (formatting, etc.)
- **refactor:** Code refactoring
- **perf:** Performance improvements
- **test:** Test changes
- **chore:** Maintenance tasks
- **ci:** CI/CD changes

### Breaking Changes

Add `!` after type or include `BREAKING CHANGE:` in footer:

```bash
feat!: remove legacy .txt config support
```

or

```bash
feat: new config format

BREAKING CHANGE: config.yml is now required, .txt files removed
```

## Tagging Strategy

### Version Tags (Pinnable)

```
artokun/comfyui-runpod:v1.2.3-ada
artokun/comfyui-runpod:v1.2.3-blackwell
```

Use these to pin to specific versions in production.

### Architecture Tags (Latest)

```
artokun/comfyui-runpod:ada
artokun/comfyui-runpod:blackwell
```

These always point to the latest release for that architecture.

## RunPod Usage

### Option 1: Always Latest (Recommended for Development)

```
Container Image: artokun/comfyui-runpod:ada
```

Gets the latest stable version automatically.

### Option 2: Pinned Version (Recommended for Production)

```
Container Image: artokun/comfyui-runpod:v1.2.3-ada
```

Stays on specific version until you manually update.

## Manual Deploy (If Needed)

If GitHub Actions fails or you need to deploy manually:

```bash
# Login to Docker Hub
docker login

# Deploy
./deploy.sh ada
./deploy.sh blackwell
```

## Workflow File

The workflow is defined in `.github/workflows/release.yml`

### When It Runs

- ✅ Push to `main` branch
- ❌ Changes only to `.md` files
- ❌ Changes only to `docs/` or `examples/`
- ❌ Pull requests (CI runs, but no deploy)

### What It Does

1. **version** job: Calculate new version from commits
2. **build-and-deploy** job: Build and push Docker images (runs in parallel for ada/blackwell)
3. **create-release** job: Create git tag and GitHub release

### Monitoring

Check workflow runs: **Actions** tab in GitHub

Each run shows:
- Version calculated
- Docker builds (ada and blackwell)
- Push to Docker Hub
- GitHub release creation

## Troubleshooting

### "Error: Authentication failed"

**Problem:** Docker Hub secrets not configured

**Solution:**
1. Check secrets in repo settings
2. Verify `DOCKER_USERNAME` and `DOCKER_TOKEN` are set
3. Ensure token has write permissions

### "No version bump needed"

**Problem:** No conventional commits since last tag

**Solution:**
- Use proper commit format (`feat:`, `fix:`, etc.)
- Or skip deploy by only changing docs

### "Tag already exists"

**Problem:** Version collision

**Solution:**
1. Delete old tag: `git tag -d v1.2.3 && git push --delete origin v1.2.3`
2. Re-run workflow

## Version History

See **Releases** page for full version history and changelogs.

## Best Practices

1. **Use conventional commits** - Enables automatic versioning
2. **Write meaningful commit messages** - They become your changelog
3. **Group related changes** - One PR per feature/fix when possible
4. **Test before merging** - CI must pass before merge to main
5. **Pin versions in production** - Use versioned tags for stability

## Example Workflow

1. Create feature branch: `git checkout -b feat/websocket-support`
2. Make changes and commit: `git commit -m "feat: add WebSocket progress tracking"`
3. Push and create PR: `git push origin feat/websocket-support`
4. CI runs tests automatically
5. Merge PR to main
6. GitHub Actions automatically:
   - Bumps version to v0.2.0 (minor bump for `feat:`)
   - Builds Docker images
   - Pushes to Docker Hub
   - Creates GitHub release
7. Check **Releases** page for new v0.2.0 release
8. Images available:
   - `artokun/comfyui-runpod:v0.2.0-ada`
   - `artokun/comfyui-runpod:ada` (updated)

Done! 🚀
