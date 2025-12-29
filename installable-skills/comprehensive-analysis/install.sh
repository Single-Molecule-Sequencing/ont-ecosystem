#!/bin/bash
# Install comprehensive-analysis skill for Claude Code/Desktop/Web
# Usage: ./install.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_NAME="comprehensive-analysis"
CLAUDE_DIR="${HOME}/.claude"
COMMANDS_DIR="${CLAUDE_DIR}/commands"

echo "Installing ${SKILL_NAME} skill for Claude..."

# Create Claude commands directory if it doesn't exist
mkdir -p "${COMMANDS_DIR}"

# Copy the skill command file
cp "${SCRIPT_DIR}/${SKILL_NAME}.md" "${COMMANDS_DIR}/"

echo "Skill installed to: ${COMMANDS_DIR}/${SKILL_NAME}.md"

# Check for Python dependencies
echo ""
echo "Checking Python dependencies..."
MISSING_DEPS=""

python3 -c "import numpy" 2>/dev/null || MISSING_DEPS="${MISSING_DEPS} numpy"
python3 -c "import pandas" 2>/dev/null || MISSING_DEPS="${MISSING_DEPS} pandas"
python3 -c "import matplotlib" 2>/dev/null || MISSING_DEPS="${MISSING_DEPS} matplotlib"
python3 -c "import scipy" 2>/dev/null || MISSING_DEPS="${MISSING_DEPS} scipy"

if [ -n "${MISSING_DEPS}" ]; then
    echo "Missing dependencies:${MISSING_DEPS}"
    echo ""
    echo "Install with: pip install${MISSING_DEPS}"
else
    echo "All dependencies installed."
fi

echo ""
echo "Installation complete!"
echo ""
echo "Usage in Claude:"
echo "  /comprehensive-analysis /path/to/experiment -o output/"
echo "  /comprehensive-analysis /path/to/experiment -o output/ --full"
echo ""
echo "Or run directly:"
echo "  python3 ${SCRIPT_DIR}/../../skills/comprehensive-analysis/scripts/comprehensive_analysis.py \\"
echo "      /path/to/experiment -o output/"
