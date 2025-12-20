#!/bin/bash
# Push ONT Ecosystem to GitHub
# Run this after extracting the tarball

set -e

echo "🧬 ONT Ecosystem GitHub Push Helper"
echo ""

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "skills" ]; then
    echo "❌ Error: Run this from the ont-ecosystem directory"
    echo "   cd ont-ecosystem && ./push-to-github.sh"
    exit 1
fi

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📦 Initializing git repository..."
    git init
    git add -A
    git commit -m "ONT Ecosystem v2.1 - Complete Package"
    git branch -M main
fi

# Set remote
REPO_URL="https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git"
echo "🔗 Setting remote to: $REPO_URL"

if git remote get-url origin 2>/dev/null; then
    git remote set-url origin "$REPO_URL"
else
    git remote add origin "$REPO_URL"
fi

echo ""
echo "📤 Ready to push!"
echo ""
echo "Run the following command to push:"
echo ""
echo "   git push -u origin main"
echo ""
echo "If you need to force push (overwrite remote):"
echo ""
echo "   git push -u origin main --force"
echo ""
