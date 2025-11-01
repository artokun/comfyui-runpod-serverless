# GitHub Actions Setup

One-time setup for automated deployment.

## Prerequisites

1. Docker Hub account (`artokun`)
2. GitHub repository with Actions enabled

## Setup Steps

### Step 1: Create Docker Hub Access Token

1. Go to https://hub.docker.com/settings/security
2. Click **"New Access Token"**
3. Configure:
   - **Name:** `github-actions-deploy`
   - **Access permissions:** Read, Write, Delete
4. Click **"Generate"**
5. **Copy the token** (you won't see it again!)

### Step 2: Add GitHub Secrets

1. Go to your GitHub repository
2. Navigate to: **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"**
4. Add these secrets:

#### Secret 1: DOCKER_USERNAME

- **Name:** `DOCKER_USERNAME`
- **Value:** `artokun`
- Click **"Add secret"**

#### Secret 2: DOCKER_TOKEN

- **Name:** `DOCKER_TOKEN`
- **Value:** [paste the access token from Step 1]
- Click **"Add secret"**

### Step 3: Verify Setup

1. Make a test commit to `main`:
   ```bash
   git commit --allow-empty -m "chore: test auto-deploy setup"
   git push origin main
   ```

2. Check the **Actions** tab in GitHub
3. You should see the "Release and Deploy" workflow running
4. If it succeeds, check:
   - **Releases** page for new release
   - Docker Hub for new images

### Step 4: Create Initial Tag (Optional)

If this is the first time setting up versioning, create an initial tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

This sets the starting point for version bumps.

## Troubleshooting

### Workflow doesn't run

**Check:**
- Workflow file exists: `.github/workflows/release.yml`
- Repository has Actions enabled
- Push is to `main` branch
- Changes are not only to `.md` files

### Authentication failed

**Check:**
- `DOCKER_USERNAME` secret is set correctly
- `DOCKER_TOKEN` secret is set correctly
- Token has write permissions
- Token hasn't expired

### Build fails

**Check:**
- Dockerfile exists and is valid
- All required files are in repository
- Build works locally: `./build.sh --arch ada`

### Version not bumping

**Check:**
- Commit messages use conventional format
- At least one commit since last tag uses `feat:` or `fix:`
- Previous tag exists

## How It Works

### Trigger

Workflow runs when:
- Code is pushed to `main` branch
- Changes are not only to documentation

### Jobs

1. **version:** Calculates new version from commit messages
2. **build-and-deploy:** Builds Docker images (parallel for ada/blackwell)
3. **create-release:** Creates git tag and GitHub release

### Version Calculation

Based on conventional commits since last tag:

| Commit Type | Bump | Example |
|-------------|------|---------|
| `feat:` | Minor | v0.1.0 → v0.2.0 |
| `fix:` | Patch | v0.1.0 → v0.1.1 |
| `feat!:` | Major | v0.1.0 → v1.0.0 |
| `docs:` | None | No version bump |

### Docker Tags Created

For version `v1.2.3`:

- `artokun/comfyui-runpod:v1.2.3-ada`
- `artokun/comfyui-runpod:v1.2.3-blackwell`
- `artokun/comfyui-runpod:ada` (updated)
- `artokun/comfyui-runpod:blackwell` (updated)

## Manual Override

If you need to deploy manually:

```bash
# Login to Docker Hub
docker login -u artokun

# Deploy
./deploy.sh ada
./deploy.sh blackwell

# Create release manually
gh release create v1.2.3 --generate-notes
```

## Monitoring

### View Workflow Runs

1. Go to **Actions** tab
2. Click on "Release and Deploy"
3. View recent runs

### Check Logs

Click on any workflow run to see:
- Version calculation
- Build logs (ada and blackwell)
- Push status
- Release creation

### Notifications

GitHub will notify you:
- When workflow fails
- When new release is created

## Security Notes

- **Never commit secrets** to the repository
- **Use access tokens** instead of passwords
- **Rotate tokens** periodically
- **Limit token permissions** to what's needed (Read, Write, Delete for Docker Hub)

## Next Steps

After setup:

1. ✅ Secrets are configured
2. ✅ Test workflow runs successfully
3. ✅ Docker images are on Docker Hub
4. ✅ Releases appear on GitHub

Now just:
- Merge PRs to `main`
- CI/CD handles the rest!

## Reference

- [Versioning Guide](VERSION_GUIDE.md) - How versioning works
- [Conventional Commits](https://www.conventionalcommits.org/) - Commit format spec
- [GitHub Actions Docs](https://docs.github.com/en/actions) - GitHub Actions reference

---

**All set!** Every merge to `main` will now automatically deploy. 🚀
