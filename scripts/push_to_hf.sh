#!/bin/bash
set -e

# Script to deploy to Hugging Face Space
# Usage: ./scripts/push_to_hf.sh [patch|minor|major]

PART="${1:-patch}"

echo "1. Bumping version ($PART)..."
python3 scripts/bump_version.py "$PART"

NEW_VER=$(python3 -c "import sys; sys.path.insert(0, '.'); from src.version import __version__; print(__version__)")

echo "2. Staging version files..."
git add src/version.py

if ! git diff --cached --quiet; then
    git commit -m "chore(release): bump version to v${NEW_VER}"
fi

echo "3. Pushing to space remote (Hugging Face)..."
git push space main

echo "🚀 Successfully pushed v${NEW_VER} to Hugging Face Space!"
