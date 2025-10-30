# Docker Hub Setup Guide

Quick guide to set up Docker Hub for deploying your ComfyUI RunPod handler.

> **Note for Contributors:** If you're contributing to this project, you **don't need** to follow this guide. Just test locally with `docker compose up`. Only the maintainer needs to push images to Docker Hub.
>
> **Note for Forkers:** If you've forked this repo to create your own deployment, follow this guide and change `DOCKER_USERNAME` in `build.sh` to your username.

## Step 1: Create Docker Hub Account

1. Go to https://hub.docker.com/signup
2. Sign up (free account is fine)
3. Verify your email address

## Step 2: Login to Docker Hub

### Option A: Username + Password

```bash
docker login
```

Enter your username and password when prompted.

### Option B: Username + Access Token (Recommended)

Access tokens are more secure than using your password directly.

1. Login to Docker Hub website
2. Go to **Account Settings** → **Security** → https://hub.docker.com/settings/security
3. Click **"New Access Token"**
4. Name: `comfyui-deploy` (or whatever you prefer)
5. Access permissions: **Read, Write, Delete**
6. Click **"Generate"**
7. **Copy the token immediately** (you won't see it again!)

Then login:

```bash
docker login -u YOUR_USERNAME
Password: [paste your access token here]
```

**Save your token securely!** You'll need it for CI/CD later.

## Step 3: Verify Login

```bash
# Check you're logged in
docker info | grep Username

# Or
docker info | grep -i username
```

Should output: `Username: yourusername`

## Step 4: Update build.sh with Your Username (Forkers Only)

**Only needed if you forked this repo for your own deployment!**

Open `build.sh` and change line 7:

```bash
# Current (official repo)
DOCKER_USERNAME="alongbottom"

# Change to your username if you forked
DOCKER_USERNAME="yourusername"
```

**Example:**

```bash
# Configuration
DOCKER_USERNAME="johnsmith"
IMAGE_NAME="comfyui-runpod"
```

**Leave as `alongbottom` if you're just contributing code to this repo!**

## Step 5: Test Build and Push

### Build Only (No Push)

```bash
./build.sh --arch ada
```

This builds the image locally without pushing.

### Build and Push

```bash
./build.sh --arch ada --push
```

This builds and pushes to Docker Hub.

**What happens:**
1. Builds Docker image
2. Tags as `yourusername/comfyui-runpod:ada`
3. Pushes to Docker Hub

## Step 6: Verify on Docker Hub

1. Go to https://hub.docker.com
2. Login
3. Go to **Repositories**
4. You should see `comfyui-runpod` with the `ada` tag

## Quick Deploy

Once set up, deploying is simple:

```bash
# Deploy Ada (RTX 4090)
./deploy.sh ada

# Deploy Blackwell (RTX 5090/6000 Pro)
./deploy.sh blackwell
```

## Troubleshooting

### "denied: requested access to the resource is denied"

**Problem:** Not logged in or wrong credentials

**Solution:**
```bash
docker logout
docker login
```

### "Error response from daemon: Get https://registry-1.docker.io/v2/: unauthorized"

**Problem:** Invalid credentials or expired token

**Solution:**
1. Generate a new access token
2. Login again with new token

### "Cannot connect to the Docker daemon"

**Problem:** Docker Desktop not running

**Solution:**
- **Windows:** Start Docker Desktop
- **Linux:** `sudo systemctl start docker`
- **Mac:** Start Docker Desktop app

### "Username should be lowercase"

**Problem:** Docker Hub usernames must be lowercase

**Solution:** Use lowercase version in `build.sh`:
```bash
DOCKER_USERNAME="johnsmith"  # Not "JohnSmith"
```

## Image Naming Convention

Your images will be named:

```
yourusername/comfyui-runpod:ada
yourusername/comfyui-runpod:blackwell
```

**Example:** If your username is `johnsmith`:
- `johnsmith/comfyui-runpod:ada`
- `johnsmith/comfyui-runpod:blackwell`

## Using in RunPod

When configuring your RunPod endpoint:

1. Go to RunPod Console
2. Create/Edit Endpoint
3. Template Settings
4. **Container Image:** `yourusername/comfyui-runpod:ada`

Replace `yourusername` with your actual Docker Hub username!

## Security Best Practices

✅ **DO:**
- Use access tokens instead of passwords
- Set token permissions to only what you need
- Rotate tokens periodically
- Store tokens securely (password manager)

❌ **DON'T:**
- Commit tokens to git
- Share tokens publicly
- Use your password in CI/CD
- Leave tokens in plain text files

## Next Steps

1. ✅ Create Docker Hub account
2. ✅ Login via command line
3. ✅ Update `build.sh` with your username
4. ✅ Test build: `./build.sh --arch ada`
5. ✅ Push image: `./build.sh --arch ada --push`
6. ✅ Verify on Docker Hub website
7. ✅ Deploy to RunPod with your image

## Summary Commands

```bash
# 1. Login
docker login -u yourusername

# 2. Update build.sh (change DOCKER_USERNAME)
nano build.sh  # or your preferred editor

# 3. Build and push
./deploy.sh ada

# 4. Verify
docker images | grep comfyui-runpod

# 5. Check on Docker Hub
open https://hub.docker.com/r/yourusername/comfyui-runpod
```

You're ready to deploy! 🚀
