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
else
    # Remote install - download from GitHub
    echo "📥 Downloading from GitHub..."
    
    SCRIPTS="ont_experiments.py ont_align.py ont_pipeline.py end_reason.py ont_monitor.py dorado_basecall.py calculate_resources.py ont_endreason_qc.py experiment_db.py ont_config.py ont_context.py ont_manuscript.py ont_stats.py ont_check.py ont_help.py ont_update.py ont_backup.py ont_doctor.py ont_report.py ont_hooks.py ont_version.py ont_init.py ont_changelog.py ont_dashboard.py ont_integrate.py ont_registry.py ont_textbook_export.py make_sbatch_from_cmdtxt.py"
    
    DOWNLOAD_COUNT=0
    for script in $SCRIPTS; do
        if curl -sSL "$REPO_URL/raw/main/bin/$script" -o "$INSTALL_DIR/bin/$script" 2>/dev/null; then
            DOWNLOAD_COUNT=$((DOWNLOAD_COUNT + 1))
        fi
    done
    
    # Download lib files
    for libfile in __init__.py cache.py cli.py config.py errors.py io.py logging_config.py parallel.py timing.py validation.py; do
        curl -sSL "$REPO_URL/raw/main/lib/$libfile" -o "$INSTALL_DIR/lib/$libfile" 2>/dev/null || true
    done
    
    # Download completion script
    mkdir -p "$INSTALL_DIR/completions"
    curl -sSL "$REPO_URL/raw/main/completions/ont-completion.bash" -o "$INSTALL_DIR/completions/ont-completion.bash" 2>/dev/null || true
    
    if [ "$DOWNLOAD_COUNT" -eq 0 ]; then
        echo ""
        echo "❌ Failed to download files. The repository may be private."
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
        exit 1
    fi
    
    echo "   Downloaded $DOWNLOAD_COUNT scripts"
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

# Check and fix numpy/matplotlib compatibility
echo "🔧 Checking numpy/matplotlib compatibility..."
check_numpy_matplotlib() {
    python3 -c "
import sys
try:
    import numpy as np
    np_version = tuple(int(x) for x in np.__version__.split('.')[:2])
except ImportError:
    print('numpy_missing')
    sys.exit(0)

try:
    import matplotlib
    mpl_version = tuple(int(x) for x in matplotlib.__version__.split('.')[:2])
except ImportError:
    print('matplotlib_missing')
    sys.exit(0)
except AttributeError as e:
    if '_ARRAY_API' in str(e):
        print('incompatible')
        sys.exit(1)
    raise

# numpy 2.x requires matplotlib 3.9+
if np_version[0] >= 2 and mpl_version < (3, 9):
    print('incompatible')
    sys.exit(1)
print('compatible')
" 2>/dev/null
}

COMPAT_STATUS=$(check_numpy_matplotlib)

if [ "$COMPAT_STATUS" = "incompatible" ]; then
    echo "   ⚠️  numpy/matplotlib version mismatch detected"
    echo ""
    echo "   Your numpy version (2.x) is incompatible with system matplotlib."
    echo "   To fix, run one of:"
    echo "     pip install 'numpy>=1.20,<2'    # Downgrade numpy (recommended)"
    echo "     pip install matplotlib>=3.9     # Upgrade matplotlib"
    echo ""
    echo "   Or use a virtual environment:"
    echo "     python3 -m venv ~/.ont-venv"
    echo "     source ~/.ont-venv/bin/activate"
    echo "     pip install numpy matplotlib pandas"
    echo ""
    # Try to fix automatically
    pip install --quiet 'numpy>=1.20,<2' 2>/dev/null && echo "   ✓ Installed numpy 1.x for compatibility" || true
elif [ "$COMPAT_STATUS" = "numpy_missing" ]; then
    echo "   Installing numpy..."
    pip install --quiet 'numpy>=1.20,<2' 2>/dev/null || echo "   Note: Install numpy manually"
elif [ "$COMPAT_STATUS" = "matplotlib_missing" ]; then
    echo "   Note: matplotlib not installed (optional for figure generation)"
    echo "   Install with: pip install matplotlib"
else
    echo "   ✓ numpy/matplotlib versions compatible"
fi

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
