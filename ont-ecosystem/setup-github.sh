#!/bin/bash
#
# Setup script for ont-ecosystem repository
# Run this after extracting ont-ecosystem.tar.gz
#

set -e

REPO_URL="https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git"

echo "=============================================="
echo "ONT Ecosystem GitHub Setup"
echo "=============================================="
echo ""

# Check if we're in the right directory
if [[ ! -f "install.sh" ]] || [[ ! -f "README.md" ]]; then
    echo "Error: Run this script from the ont-ecosystem directory"
    exit 1
fi

# Check for git
if ! command -v git &> /dev/null; then
    echo "Error: git is required"
    exit 1
fi

# Initialize git if needed
if [[ ! -d ".git" ]]; then
    echo "Initializing git repository..."
    git init
    git branch -M main
fi

# Add all files
echo "Adding files..."
git add -A

# Check if there are changes to commit
if git diff --cached --quiet; then
    echo "No changes to commit"
else
    echo "Creating initial commit..."
    git commit -m "Initial commit: ONT Ecosystem v2.1

- Core registry with event-sourced experiment tracking
- Pattern B orchestration for analysis workflows
- Analysis skills: end-reason, dorado-bench, ont-align, ont-monitor
- Web dashboard with REST API
- Auto-install with HPC detection (Great Lakes, ARMIS2)
- 18 unit tests passing
- CI/CD with GitHub Actions"
fi

# Check if remote exists
if git remote get-url origin &> /dev/null; then
    echo "Remote 'origin' already configured"
else
    echo ""
    echo "To push to GitHub, run:"
    echo ""
    echo "  # First create the repository on GitHub:"
    echo "  # https://github.com/organizations/Single-Molecule-Sequencing/repositories/new"
    echo "  # Name: ont-ecosystem"
    echo "  # Description: Oxford Nanopore experiment management with provenance tracking"
    echo "  # Public, no README/LICENSE (we have our own)"
    echo ""
    echo "  # Then push:"
    echo "  git remote add origin ${REPO_URL}"
    echo "  git push -u origin main"
fi

echo ""
echo "=============================================="
echo "Setup complete!"
echo "=============================================="
echo ""
echo "Next steps:"
echo "  1. Create repository at: https://github.com/organizations/Single-Molecule-Sequencing/repositories/new"
echo "  2. Run: git remote add origin ${REPO_URL}"
echo "  3. Run: git push -u origin main"
echo ""
echo "After pushing, the install command will be:"
echo "  curl -sSL https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/install.sh | bash"
echo ""
