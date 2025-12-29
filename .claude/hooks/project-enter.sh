#!/bin/bash
# Auto-install ONT Ecosystem skills when entering the project
# This hook runs when Claude enters the ont-ecosystem project

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CLAUDE_DIR="${HOME}/.claude"
SKILLS_DIR="${CLAUDE_DIR}/skills"
COMMANDS_DIR="${CLAUDE_DIR}/commands"

# Create directories if needed
mkdir -p "${SKILLS_DIR}" "${COMMANDS_DIR}"

# Sync skills from installable-skills/
if [ -d "${REPO_DIR}/installable-skills" ]; then
    for skill_dir in "${REPO_DIR}/installable-skills"/*/; do
        skill_name=$(basename "$skill_dir")
        skill_file="${skill_dir}${skill_name}.md"
        if [ -f "$skill_file" ]; then
            cp "$skill_file" "${SKILLS_DIR}/"
            cp "$skill_file" "${COMMANDS_DIR}/"
        fi
    done
fi

# Output status (silent by default, uncomment for debugging)
# echo "ONT Ecosystem skills synced to ~/.claude/"
