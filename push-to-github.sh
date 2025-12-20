#!/bin/bash
# Push ONT Ecosystem updates to GitHub

set -e

echo "========================================"
echo "ONT Ecosystem - GitHub Push Script"
echo "========================================"

# Check if git is available
if ! command -v git &> /dev/null; then
    echo "Error: git is not installed"
    exit 1
fi

# Initialize git if needed
if [ ! -d .git ]; then
    echo "Initializing git repository..."
    git init
    git branch -M main
fi

# Add all files
echo "Staging all files..."
git add -A

# Create commit
COMMIT_MSG="Update: Combined read length + end reason analysis tool

- Added ont_readlen_endreason.py with combined analysis
- Semi-transparent overlaid distributions by end reason class
- Cross-experiment summary plots (4-panel)
- Detailed 4-panel per-experiment analysis
- Comprehensive statistics per end reason class
- Updated SKILL.md documentation
- Added test_readlen_endreason.py test suite"

git commit -m "$COMMIT_MSG" || echo "Nothing to commit"

# Check if remote exists
if ! git remote | grep -q origin; then
    echo ""
    echo "No remote configured. To push to GitHub, run:"
    echo "  git remote add origin https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git"
    echo "  git push -u origin main"
else
    echo ""
    echo "Pushing to GitHub..."
    git push origin main
fi

echo ""
echo "Done!"
