#!/bin/bash
# ONT Ecosystem Installer
# Usage: curl -sSL https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/install.sh | bash

set -e

INSTALL_DIR="${ONT_ECOSYSTEM_HOME:-$HOME/.ont-ecosystem}"
REPO_URL="https://github.com/Single-Molecule-Sequencing/ont-ecosystem"

echo "ðŸ§¬ Installing ONT Ecosystem..."
echo "   Install directory: $INSTALL_DIR"

# Parse arguments
HPC_MODE=false
for arg in "$@"; do
    case $arg in
        --hpc) HPC_MODE=true ;;
    esac
done

# Create install directory
mkdir -p "$INSTALL_DIR"/{bin,config}

# Check if running from cloned repo or remote install
if [ -f "bin/ont_experiments.py" ]; then
    echo "ðŸ“ Installing from local repository..."
    cp bin/*.py "$INSTALL_DIR/bin/"
else
    echo "ðŸ“¥ Downloading from GitHub..."
    for script in ont_experiments.py ont_align.py ont_pipeline.py; do
        curl -sSL "$REPO_URL/raw/main/bin/$script" -o "$INSTALL_DIR/bin/$script"
    done
fi

# Make scripts executable
chmod +x "$INSTALL_DIR/bin/"*.py

# Create environment file
cat > "$INSTALL_DIR/env.sh" << EOF
# ONT Ecosystem Environment
export ONT_ECOSYSTEM_HOME="$INSTALL_DIR"
export PATH="\$ONT_ECOSYSTEM_HOME/bin:\$PATH"
export ONT_REGISTRY_DIR="\${ONT_REGISTRY_DIR:-\$HOME/.ont-registry}"
export ONT_REFERENCES_DIR="\${ONT_REFERENCES_DIR:-\$HOME/.ont-references}"
EOF

# HPC-specific configuration
if [ "$HPC_MODE" = true ]; then
    echo "ðŸ–¥ï¸  Configuring for HPC environment..."
    
    # Detect cluster
    if [ -d "/nfs/turbo" ]; then
        CLUSTER="greatlakes"
        cat >> "$INSTALL_DIR/env.sh" << 'EOF'

# Great Lakes HPC paths
export DORADO_MODELS="/nfs/turbo/umms-athey/dorado_models"
export ONT_REFERENCES="/nfs/turbo/umms-athey/references"
EOF
    elif [ -d "/nfs/dataden" ]; then
        CLUSTER="armis2"
        cat >> "$INSTALL_DIR/env.sh" << 'EOF'

# ARMIS2 HPC paths
export DORADO_MODELS="/nfs/dataden/umms-bleu-secure/programs/dorado_models"
export ONT_REFERENCES="/nfs/dataden/umms-bleu-secure/references"
EOF
    fi
    echo "   Detected cluster: ${CLUSTER:-unknown}"
fi

# Install Python dependencies
echo "ðŸ“¦ Checking Python dependencies..."
pip install --quiet pyyaml 2>/dev/null || echo "   Note: Install pyyaml manually if needed"

# Add to shell profile
SHELL_RC="$HOME/.bashrc"
[ -f "$HOME/.zshrc" ] && SHELL_RC="$HOME/.zshrc"

if ! grep -q "ont-ecosystem" "$SHELL_RC" 2>/dev/null; then
    echo "" >> "$SHELL_RC"
    echo "# ONT Ecosystem" >> "$SHELL_RC"
    echo "source $INSTALL_DIR/env.sh" >> "$SHELL_RC"
    echo "   Added to $SHELL_RC"
fi

echo ""
echo "âœ… ONT Ecosystem installed successfully!"
echo ""
echo "To activate now, run:"
echo "   source $INSTALL_DIR/env.sh"
echo ""
echo "Quick start:"
echo "   ont_experiments.py init --git"
echo "   ont_experiments.py discover /path/to/data --register"
echo ""
