# Auto-Deploy & Versioning Summary

Automated CI/CD pipeline is now configured! Here's what was set up:

## What Was Added

### 1. GitHub Actions Workflow (`.github/workflows/release.yml`)

Automatically runs when code is merged to `main`:

- ✅ **Version Calculation** - Determines version bump from conventional commits
- ✅ **Multi-Arch Build** - Builds both Ada and Blackwell images in parallel
- ✅ **Docker Hub Push** - Pushes images with version tags
- ✅ **GitHub Release** - Creates release with changelog

### 2. Documentation

- **`.github/workflows/VERSION_GUIDE.md`** - Complete guide to versioning and auto-deploy
- **`.github/workflows/SETUP.md`** - One-time setup instructions for GitHub secrets
- **`CONTRIBUTING.md`** - Updated with versioning info and deployment details
- **`README.md`** - Updated to reference official auto-deployed images

## How It Works

### Commit → Version Bump

```bash
git commit -m "feat: add websocket support"  # → v0.x.0 (minor bump)
git commit -m "fix: resolve timeout bug"      # → v0.0.x (patch bump)
git commit -m "feat!: redesign API"           # → x.0.0 (major bump)
```

### Merge → Auto-Deploy

1. **PR merged to `main`**
2. GitHub Actions triggers
3. Version calculated (e.g., v1.2.3)
4. Docker images built:
   - `artokun/comfyui-runpod:v1.2.3-ada`
   - `artokun/comfyui-runpod:v1.2.3-blackwell`
5. Architecture tags updated:
   - `artokun/comfyui-runpod:ada` → latest
   - `artokun/comfyui-runpod:blackwell` → latest
6. GitHub release created with changelog
7. Done! 🚀

## Setup Required (One-Time)

To enable auto-deploy, you need to:

### 1. Create Docker Hub Access Token

1. Go to https://hub.docker.com/settings/security
2. Create new token: `github-actions-deploy`
3. Permissions: Read, Write, Delete
4. Copy the token

### 2. Add GitHub Secrets

Go to: **Settings** → **Secrets and variables** → **Actions**

Add two secrets:

| Secret | Value |
|--------|-------|
| `DOCKER_USERNAME` | `artokun` |
| `DOCKER_TOKEN` | [your access token] |

### 3. Test It

```bash
git commit --allow-empty -m "chore: test auto-deploy"
git push origin main
```

Check **Actions** tab to see workflow run!

## Version Strategy

### Semantic Versioning

Following [SemVer](https://semver.org/): `MAJOR.MINOR.PATCH`

- **MAJOR** - Breaking changes (`feat!:` or `BREAKING CHANGE:`)
- **MINOR** - New features (`feat:`)
- **PATCH** - Bug fixes (`fix:`)

### Docker Tags

For each release (e.g., v1.2.3), creates:

**Versioned tags (pinnable):**
- `artokun/comfyui-runpod:v1.2.3-ada`
- `artokun/comfyui-runpod:v1.2.3-blackwell`

**Architecture tags (latest):**
- `artokun/comfyui-runpod:ada`
- `artokun/comfyui-runpod:blackwell`

## RunPod Usage

### Recommended: Use Latest

```
Container Image: artokun/comfyui-runpod:ada
```

Always gets the latest stable version automatically.

### Optional: Pin Version

```
Container Image: artokun/comfyui-runpod:v1.2.3-ada
```

Stays on specific version until manually updated.

## Benefits

### For Maintainers

- ✅ **No manual deployment** - Merge and forget
- ✅ **Automatic versioning** - No need to decide version numbers
- ✅ **Changelog generation** - Commit messages become changelog
- ✅ **Release notes** - Auto-generated with each release
- ✅ **Multi-arch builds** - Ada and Blackwell built in parallel

### For Contributors

- ✅ **No Docker Hub needed** - Just test locally
- ✅ **Clear commit format** - Know what version bump your change causes
- ✅ **Automatic testing** - CI runs on every PR
- ✅ **Fast feedback** - See build status immediately

### For Users

- ✅ **Always up-to-date** - Latest images auto-published
- ✅ **Version pinning** - Can pin to specific version if needed
- ✅ **Release notes** - Clear changelog for each version
- ✅ **Stable tags** - Ada and Blackwell tags always work

## Workflow Diagram

```
┌─────────────────┐
│  Merge to main  │
└────────┬────────┘
         │
         ▼
┌────────────────────────────┐
│  Calculate Version         │
│  (from commit messages)    │
│  v0.1.0 → v0.2.0          │
└────────┬───────────────────┘
         │
         ▼
┌────────────────────────────┐
│  Build Docker Images       │
│  ┌──────────┐ ┌──────────┐│
│  │   Ada    │ │Blackwell ││
│  └──────────┘ └──────────┘│
└────────┬───────────────────┘
         │
         ▼
┌────────────────────────────┐
│  Push to Docker Hub        │
│  - v0.2.0-ada              │
│  - v0.2.0-blackwell        │
│  - ada (updated)           │
│  - blackwell (updated)     │
└────────┬───────────────────┘
         │
         ▼
┌────────────────────────────┐
│  Create GitHub Release     │
│  - Tag: v0.2.0             │
│  - Changelog               │
│  - Docker pull commands    │
└────────────────────────────┘
```

## Example Scenarios

### Scenario 1: Bug Fix

```bash
# Commit
git commit -m "fix: resolve timeout in polling"

# Merge to main
# → v1.2.3 → v1.2.4 (patch bump)
# → Images built and pushed automatically
```

### Scenario 2: New Feature

```bash
# Commit
git commit -m "feat: add S3 upload support"

# Merge to main
# → v1.2.4 → v1.3.0 (minor bump)
# → Images built and pushed automatically
```

### Scenario 3: Breaking Change

```bash
# Commit
git commit -m "feat!: redesign config.yml format

BREAKING CHANGE: Old .txt config files no longer supported"

# Merge to main
# → v1.3.0 → v2.0.0 (major bump)
# → Images built and pushed automatically
```

## Monitoring

### View Workflows

Go to: **Actions** tab in GitHub

See:
- Running workflows
- Build logs
- Success/failure status
- Build times

### Check Releases

Go to: **Releases** page

See:
- All versions
- Changelogs
- Docker pull commands
- Release dates

### Docker Hub

Go to: https://hub.docker.com/r/artokun/comfyui-runpod

See:
- All image tags
- Pull counts
- Last updated
- Image sizes

## Manual Override

If GitHub Actions is down or you need manual control:

```bash
# Login to Docker Hub
docker login -u artokun

# Build and deploy
./deploy.sh ada
./deploy.sh blackwell

# Create release manually
git tag v1.2.3
git push origin v1.2.3
gh release create v1.2.3 --generate-notes
```

## Troubleshooting

### Workflow doesn't trigger

- Check workflow file exists: `.github/workflows/release.yml`
- Verify push is to `main` branch
- Ensure changes aren't only `.md` files

### Authentication failed

- Verify GitHub secrets are set
- Check Docker Hub token is valid
- Ensure token has write permissions

### No version bump

- Use conventional commit format
- At least one `feat:` or `fix:` commit needed
- Check a previous tag exists (`git tag`)

## Next Steps

1. ✅ **Setup GitHub secrets** (see SETUP.md)
2. ✅ **Test with empty commit**
3. ✅ **Verify images on Docker Hub**
4. ✅ **Check GitHub release created**

Then just:
- Write code
- Use conventional commits
- Merge to main
- Done! 🎉

## Documentation

- **[VERSION_GUIDE.md](.github/workflows/VERSION_GUIDE.md)** - Complete versioning guide
- **[SETUP.md](.github/workflows/SETUP.md)** - GitHub Actions setup
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines with versioning
- **[Conventional Commits](https://www.conventionalcommits.org/)** - Commit format spec

---

**Your CI/CD pipeline is ready!** 🚀

Every merge to `main` will now automatically:
- Calculate version
- Build Docker images
- Push to Docker Hub
- Create GitHub release

No manual intervention needed!
