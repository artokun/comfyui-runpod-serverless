#!/bin/bash
# Update ComfyUI - Smart update with git handling
# Based on ComfyUI portable update patterns

set -e

COMFYUI_DIR="${COMFYUI_PATH:-./ComfyUI}"
COMFYUI_REPO="https://github.com/comfyanonymous/ComfyUI.git"
BACKUP_BRANCH="backup_$(date +%Y%m%d_%H%M%S)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ComfyUI Update${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if ComfyUI exists
if [ ! -d "$COMFYUI_DIR" ]; then
    echo -e "${YELLOW}ComfyUI not found at: $COMFYUI_DIR${NC}"
    echo -e "${GREEN}Cloning ComfyUI...${NC}"
    git clone "$COMFYUI_REPO" "$COMFYUI_DIR"
    cd "$COMFYUI_DIR"
    echo -e "${GREEN}✓ ComfyUI cloned${NC}"
else
    echo -e "${GREEN}ComfyUI found at: $COMFYUI_DIR${NC}"
    cd "$COMFYUI_DIR"

    # Check if it's a git repo
    if [ ! -d ".git" ]; then
        echo -e "${RED}Error: $COMFYUI_DIR exists but is not a git repository${NC}"
        echo "Please remove it or specify a different path with COMFYUI_PATH"
        exit 1
    fi
fi

# Store current commit for rollback
CURRENT_COMMIT=$(git rev-parse HEAD)
echo "Current commit: $CURRENT_COMMIT"
echo ""

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}Uncommitted changes detected${NC}"
    echo "Creating backup branch: $BACKUP_BRANCH"
    git branch "$BACKUP_BRANCH" 2>/dev/null || echo "Backup branch already exists"

    echo "Stashing changes..."
    git stash push -m "Auto-stash before update $(date)"
    echo -e "${GREEN}✓ Changes stashed${NC}"
    echo ""
fi

# Fetch latest changes
echo -e "${GREEN}Fetching latest changes...${NC}"
git fetch origin

# Get current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Current branch: $CURRENT_BRANCH"

# Check if on master/main
if [ "$CURRENT_BRANCH" != "master" ] && [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${YELLOW}Not on master/main branch${NC}"
    echo "Checking out master..."
    git checkout master 2>/dev/null || git checkout main 2>/dev/null || {
        echo -e "${RED}Could not checkout master/main branch${NC}"
        exit 1
    }
fi

# Pull latest changes
echo -e "${GREEN}Pulling latest changes...${NC}"
if git pull --ff-only origin master 2>/dev/null || git pull --ff-only origin main 2>/dev/null; then
    echo -e "${GREEN}✓ Updated successfully (fast-forward)${NC}"
elif git pull --rebase origin master 2>/dev/null || git pull --rebase origin main 2>/dev/null; then
    echo -e "${GREEN}✓ Updated successfully (rebase)${NC}"
else
    echo -e "${RED}Update failed - conflicts detected${NC}"
    echo ""
    echo "Options:"
    echo "  1. Reset to latest (loses local changes): git reset --hard origin/master"
    echo "  2. Resolve conflicts manually: git status"
    echo "  3. Rollback: git checkout $BACKUP_BRANCH"
    exit 1
fi

NEW_COMMIT=$(git rev-parse HEAD)
echo ""

# Check if requirements.txt changed
if [ "$CURRENT_COMMIT" != "$NEW_COMMIT" ]; then
    echo -e "${GREEN}Changes detected: $CURRENT_COMMIT → $NEW_COMMIT${NC}"

    if git diff --name-only "$CURRENT_COMMIT" "$NEW_COMMIT" | grep -q "requirements.txt"; then
        echo -e "${YELLOW}requirements.txt changed, updating dependencies...${NC}"

        # Try to detect python
        if command -v python3 &> /dev/null; then
            PY=python3
        elif command -v python &> /dev/null; then
            PY=python
        else
            echo -e "${RED}Python not found, skipping pip install${NC}"
            echo "Install dependencies manually: pip install -r requirements.txt"
            PY=""
        fi

        if [ -n "$PY" ]; then
            $PY -m pip install -r requirements.txt --upgrade
            echo -e "${GREEN}✓ Dependencies updated${NC}"
        fi
    else
        echo "requirements.txt unchanged, skipping pip install"
    fi
else
    echo -e "${GREEN}Already up to date!${NC}"
fi

# Show summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Update Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "ComfyUI: $COMFYUI_DIR"
echo "Commit:  $NEW_COMMIT"

if [ "$CURRENT_COMMIT" != "$NEW_COMMIT" ]; then
    echo ""
    echo "Changes:"
    git log --oneline "$CURRENT_COMMIT..$NEW_COMMIT" | head -10
fi

# Check if we have stashed changes
if git stash list | grep -q "Auto-stash before update"; then
    echo ""
    echo -e "${YELLOW}You have stashed changes${NC}"
    echo "To restore: git stash pop"
fi

echo ""
echo "To rollback: git checkout $BACKUP_BRANCH"
echo ""
