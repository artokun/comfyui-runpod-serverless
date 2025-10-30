# Deployment Guide

Complete guide for deploying ComfyUI RunPod Handler.

## For Users: Deploy to RunPod

Most users should use the **official pre-built images** that auto-deploy on every release.

**Quick Start:**
1. Go to https://runpod.io/console/serverless
2. Create new template with image: `artokun/comfyui-runpod:ada`
3. Configure and deploy

See [RUNPOD_DEPLOYMENT.md](RUNPOD_DEPLOYMENT.md) for complete RunPod setup guide.

## For Maintainers: Auto-Deploy System

Images are automatically built and deployed via GitHub Actions on every merge to `main`.

**How it works:**
- Conventional commits determine version bumps
- Docker images built for Ada and Blackwell
- Pushed to Docker Hub automatically
- GitHub releases created with changelogs

See [AUTO_DEPLOY.md](AUTO_DEPLOY.md) for details.

## For Forkers: Deploy Your Own Version

If you've forked this repo to create your own deployment:

1. **Setup Docker Hub:** See [DOCKER_HUB_SETUP.md](DOCKER_HUB_SETUP.md)
2. **Update build.sh:** Change `DOCKER_USERNAME` to your username
3. **Deploy manually:** `./deploy.sh ada`

Or set up GitHub Actions with your own Docker Hub secrets.

## Deployment Options

| Audience | Method | Guide |
|----------|--------|-------|
| **Users** | Use official images | [RUNPOD_DEPLOYMENT.md](RUNPOD_DEPLOYMENT.md) |
| **Maintainer** | Auto-deploy (GitHub Actions) | [AUTO_DEPLOY.md](AUTO_DEPLOY.md) |
| **Forkers** | Manual deploy (your images) | [DOCKER_HUB_SETUP.md](DOCKER_HUB_SETUP.md) |

## Official Images

Pre-built images available on Docker Hub:

**Latest (recommended):**
- `artokun/comfyui-runpod:ada` - RTX 4090
- `artokun/comfyui-runpod:blackwell` - RTX 5090/6000 Pro

**Versioned (pinnable):**
- `artokun/comfyui-runpod:v1.2.3-ada`
- `artokun/comfyui-runpod:v1.2.3-blackwell`

See [Releases](https://github.com/artokun/comfyui-runpod-handler/releases) for version history.
