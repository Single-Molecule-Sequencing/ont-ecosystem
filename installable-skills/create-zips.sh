#!/bin/bash
# Create ZIP files for Claude Desktop/Web installation
# Usage: ./create-zips.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ZIP_DIR="${SCRIPT_DIR}/zip"

echo "=============================================="
echo "ONT Ecosystem Skills ZIP Creator"
echo "=============================================="
echo ""

# Create zip output directory
mkdir -p "${ZIP_DIR}"

# List of skills to package
SKILLS=(
    "comprehensive-analysis"
    "dorado-bench-v2"
    "end-reason"
    "experiment-db"
    "greatlakes-sync"
    "manuscript"
    "ont-align"
    "ont-experiments-v2"
    "ont-metadata"
    "ont-monitor"
    "ont-pipeline"
    "ont-public-data"
    "registry-browser"
    "registry-explorer"
    "registry-scrutinize"
    "skill-maker"
)

# Create ZIP for each skill
for skill in "${SKILLS[@]}"; do
    skill_dir="${REPO_DIR}/skills/${skill}"

    if [ -d "$skill_dir" ] && [ -f "${skill_dir}/SKILL.md" ]; then
        echo "[+] Packaging: ${skill}"

        # Create temporary directory with skill structure
        tmp_dir=$(mktemp -d)
        mkdir -p "${tmp_dir}/${skill}"

        # Copy SKILL.md
        cp "${skill_dir}/SKILL.md" "${tmp_dir}/${skill}/"

        # Copy scripts if they exist
        if [ -d "${skill_dir}/scripts" ]; then
            cp -r "${skill_dir}/scripts" "${tmp_dir}/${skill}/"
        fi

        # Copy any additional .md files (reference docs)
        for md_file in "${skill_dir}"/*.md; do
            if [ -f "$md_file" ] && [ "$(basename "$md_file")" != "SKILL.md" ]; then
                cp "$md_file" "${tmp_dir}/${skill}/"
            fi
        done

        # Create ZIP file
        (cd "${tmp_dir}" && zip -r "${ZIP_DIR}/${skill}.zip" "${skill}" -x "*.pyc" -x "__pycache__/*")

        # Cleanup
        rm -rf "${tmp_dir}"

        echo "    Created: ${skill}.zip"
    else
        echo "[-] Skipped: ${skill} (SKILL.md not found)"
    fi
done

echo ""
echo "=============================================="
echo "ZIP Files Created!"
echo "=============================================="
echo ""
echo "Location: ${ZIP_DIR}/"
echo ""
echo "Files created:"
ls -la "${ZIP_DIR}"/*.zip 2>/dev/null || echo "  (none)"
echo ""
echo "Installation (Claude Desktop/Web):"
echo "  1. Go to Settings > Features > Custom Skills"
echo "  2. Upload the .zip file for each skill"
echo "  3. Restart Claude"
echo ""
