#!/bin/bash
# Install all ONT Ecosystem skills for Claude Code/Desktop/Web
# Usage: ./install-all.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${HOME}/.claude"
COMMANDS_DIR="${CLAUDE_DIR}/commands"

echo "=============================================="
echo "ONT Ecosystem Skills Installer"
echo "=============================================="
echo ""

# Create Claude commands directory if it doesn't exist
mkdir -p "${COMMANDS_DIR}"

# List of skills to install
SKILLS=(
    "comprehensive-analysis"
    "dorado-bench-v2"
    "end-reason"
    "experiment-db"
    "manuscript"
    "ont-align"
    "ont-experiments-v2"
    "ont-metadata"
    "ont-monitor"
    "ont-pipeline"
    "skill-maker"
)

# Install each skill
for skill in "${SKILLS[@]}"; do
    if [ -f "${SCRIPT_DIR}/${skill}/${skill}.md" ]; then
        cp "${SCRIPT_DIR}/${skill}/${skill}.md" "${COMMANDS_DIR}/"
        echo "[+] Installed: /${skill}"
    else
        echo "[-] Skipped: /${skill} (not found)"
    fi
done

echo ""
echo "=============================================="
echo "Checking Python dependencies..."
echo "=============================================="

# Check for common dependencies
check_dep() {
    python3 -c "import $1" 2>/dev/null && echo "[+] $1" || echo "[-] $1 (missing)"
}

check_dep numpy
check_dep pandas
check_dep matplotlib
check_dep scipy
check_dep pod5
check_dep pysam
check_dep edlib
check_dep yaml
check_dep jinja2

echo ""
echo "=============================================="
echo "Installation Complete!"
echo "=============================================="
echo ""
echo "Available skills:"
for skill in "${SKILLS[@]}"; do
    echo "  /${skill}"
done
echo ""
echo "To install missing dependencies:"
echo "  pip install numpy pandas matplotlib scipy pod5 pysam edlib pyyaml jinja2"
echo ""
echo "Skills installed to: ${COMMANDS_DIR}/"
echo ""
echo "Usage: Type /<skill-name> in Claude to invoke a skill"
