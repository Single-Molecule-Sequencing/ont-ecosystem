#!/bin/bash
# ONT Ecosystem Installer
#
# For Private Repository (recommended):
#   git clone git@github.com:Single-Molecule-Sequencing/ont-ecosystem.git
#   cd ont-ecosystem && ./install.sh
#
# For Public Repository:
#   curl -sSL https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/install.sh | bash

set -e

INSTALL_DIR="${ONT_ECOSYSTEM_HOME:-$HOME/.ont-ecosystem}"
REPO_URL="https://github.com/Single-Molecule-Sequencing/ont-ecosystem"
SSH_URL="git@github.com:Single-Molecule-Sequencing/ont-ecosystem.git"

echo "🧬 Installing ONT Ecosystem..."
echo "   Install directory: $INSTALL_DIR"

# Parse arguments
HPC_MODE=false
FORCE_CURL=false
for arg in "$@"; do
    case $arg in
        --hpc) HPC_MODE=true ;;
        --curl) FORCE_CURL=true ;;
    esac
done

# Create install directory
mkdir -p "$INSTALL_DIR"/{bin,config,skills,lib}

# Check if running from cloned repo or remote install
if [ -f "bin/ont_experiments.py" ]; then
    echo "📂 Installing from local repository..."
    cp bin/*.py "$INSTALL_DIR/bin/"
    cp -r lib/* "$INSTALL_DIR/lib/" 2>/dev/null || true
    cp -r skills/* "$INSTALL_DIR/skills/" 2>/dev/null || true
    cp -r registry "$INSTALL_DIR/" 2>/dev/null || true
    cp -r completions "$INSTALL_DIR/" 2>/dev/null || true
    cp -r textbook "$INSTALL_DIR/" 2>/dev/null || true
    cp -r data "$INSTALL_DIR/" 2>/dev/null || true

    # Store source repo path for updates
    REPO_PATH="$(pwd)"
    echo "REPO_SOURCE=$REPO_PATH" > "$INSTALL_DIR/config/source.conf"
elif [ "$FORCE_CURL" = true ]; then
    echo "📥 Downloading from GitHub (public repo mode)..."
    echo "   Note: This requires the repository to be public."
    for script in ont_experiments.py ont_align.py ont_pipeline.py end_reason.py ont_monitor.py dorado_basecall.py calculate_resources.py ont_endreason_qc.py experiment_db.py ont_config.py ont_context.py ont_manuscript.py ont_stats.py ont_check.py ont_help.py ont_update.py ont_backup.py ont_doctor.py; do
        curl -sSL "$REPO_URL/raw/main/bin/$script" -o "$INSTALL_DIR/bin/$script" 2>/dev/null || true
    done
else
    # Private repo mode - provide SSH clone instructions
    echo ""
    echo "❌ Remote installation requires the repository to be public."
    echo ""
    echo "For private repository access, clone via SSH first:"
    echo ""
    echo "   git clone $SSH_URL"
    echo "   cd ont-ecosystem"
    echo "   ./install.sh"
    echo ""
    echo "If you have a GitHub Personal Access Token, you can also use:"
    echo "   git clone https://<TOKEN>@github.com/Single-Molecule-Sequencing/ont-ecosystem.git"
    echo ""
    echo "Or if the repo is public, use: ./install.sh --curl"
    echo ""
    exit 1
fi

# Make scripts executable
chmod +x "$INSTALL_DIR/bin/"*.py 2>/dev/null || true

# Create environment file
cat > "$INSTALL_DIR/env.sh" << EOF
# ONT Ecosystem Environment
export ONT_ECOSYSTEM_HOME="$INSTALL_DIR"
export PATH="\$ONT_ECOSYSTEM_HOME/bin:\$PATH"
export PYTHONPATH="\$ONT_ECOSYSTEM_HOME:\$PYTHONPATH"
export ONT_REGISTRY_DIR="\${ONT_REGISTRY_DIR:-\$HOME/.ont-registry}"
export ONT_REFERENCES_DIR="\${ONT_REFERENCES_DIR:-\$HOME/.ont-references}"

# Shell completion (bash)
if [ -f "\$ONT_ECOSYSTEM_HOME/completions/ont-completion.bash" ]; then
    source "\$ONT_ECOSYSTEM_HOME/completions/ont-completion.bash"
fi
EOF

# HPC-specific configuration
if [ "$HPC_MODE" = true ]; then
    echo "🖥️  Configuring for HPC environment..."
    
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
echo "📦 Checking Python dependencies..."
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
echo "✅ ONT Ecosystem v3.0.0 installed successfully!"
echo ""
echo "To activate now, run:"
echo "   source $INSTALL_DIR/env.sh"
echo ""
echo "Quick start:"
echo "   ont_stats.py --brief                              # View ecosystem stats"
echo "   ont_experiments.py init --git                     # Initialize registry"
echo "   ont_experiments.py discover /path/to/data         # Discover experiments"
echo "   ont_manuscript.py list-figures                    # List figure generators"
echo ""
