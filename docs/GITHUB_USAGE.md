# GitHub Usage Guide

## Repository

**URL:** https://github.com/Single-Molecule-Sequencing/ont-ecosystem

## How It Works on GitHub

### 1. Automated CI/CD

When you push to GitHub, the CI pipeline automatically:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GitHub Actions Workflow                         │
└─────────────────────────────────────────────────────────────────────────┘

    git push origin main
         │
         ▼
┌────────────────────┐
│    TRIGGER         │
│  push / PR         │
└────────┬───────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐ ┌───────┐
│ TEST  │ │ LINT  │
│       │ │       │
│ 3.9   │ │ check │
│ 3.10  │ │ all   │
│ 3.11  │ │ .py   │
│ 3.12  │ │       │
└───┬───┘ └───┬───┘
    │         │
    └────┬────┘
         │
         ▼
    ┌────────────┐
    │  RESULTS   │
    │            │
    │ ✓ 30 tests │
    │ ✓ syntax   │
    │ ✓ valid    │
    └────────────┘
```

### 2. One-Line Installation

Users can install directly from GitHub:

```bash
# Direct install
curl -sSL https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/install.sh | bash
source ~/.ont-ecosystem/env.sh

# Verify installation
ont_experiments.py --help
```

### 3. Public Registry Sync

The experiment registry can sync from GitHub:

```python
# In ont_experiments.py
GITHUB_REGISTRY_URL = "https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/registry/experiments.yaml"

# Users can fetch updates:
ont_experiments.py sync --from-github
```

### 4. Public Dataset Access

35+ curated ONT Open Data datasets accessible via GitHub registry:

```bash
# List public datasets
ont_experiments.py public

# Fetch with auto-registration
ont_experiments.py fetch giab_2025.01 /data/public --register
```

## Workflow: Contributing Changes

### 1. Fork and Clone

```bash
gh repo fork Single-Molecule-Sequencing/ont-ecosystem
git clone https://github.com/YOUR_USERNAME/ont-ecosystem.git
cd ont-ecosystem
```

### 2. Create Feature Branch

```bash
git checkout -b feature/my-improvement
```

### 3. Make Changes

```bash
# Edit files
vim bin/my_script.py

# Run tests locally
pytest tests/ -v

# All tests should pass
```

### 4. Commit with Convention

```bash
git add -A
git commit -m "Add feature: description of change

- Detailed bullet points
- About what changed

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 5. Push and Create PR

```bash
git push origin feature/my-improvement

# Create pull request
gh pr create --title "Add feature" --body "Description..."
```

### 6. CI Runs Automatically

```
PR Created → GitHub Actions → Tests Run → Results Posted
```

## Release Process

### Versioning

```
MAJOR.MINOR.PATCH

Current: v2.3.0
- MAJOR: Breaking API changes
- MINOR: New features (e.g., KDE visualization)
- PATCH: Bug fixes
```

### Creating a Release

```bash
# Tag the release
git tag -a v2.4.0 -m "Release v2.4.0 - Domain Memory System"

# Push tag
git push origin v2.4.0

# GitHub automatically creates release
```

## Repository Badges

Add these to README.md:

```markdown
[![CI](https://github.com/Single-Molecule-Sequencing/ont-ecosystem/actions/workflows/ci.yml/badge.svg)](https://github.com/Single-Molecule-Sequencing/ont-ecosystem/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
```

## Files in Repository

```
ont-ecosystem/                    # GitHub root
├── .github/
│   └── workflows/
│       └── ci.yml               # CI/CD pipeline
│
├── bin/                         # 12 scripts (9,845 lines)
├── skills/                      # 7 skill packages
├── registry/                    # Domain knowledge
│   ├── INDEX.yaml              # Master index
│   ├── textbook/               # Math content (10K lines)
│   ├── pipeline/               # Stage definitions
│   └── schemas/                # JSON Schema
│
├── tests/                       # 30 tests (816 lines)
├── docs/                        # Documentation
│   ├── COMPLETE_SYSTEM_GUIDE.md
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── TUTORIALS.md
│   └── GITHUB_USAGE.md
│
├── examples/                    # Configs
│   ├── pipelines/              # Workflow definitions
│   └── configs/                # HPC configs
│
├── dashboards/                  # React components
├── data/                        # Pre-built data
│
├── README.md                    # Main documentation
├── CLAUDE.md                    # AI guidance
├── CONTRIBUTING.md              # Contribution guide
├── LICENSE                      # MIT License
├── pyproject.toml               # Package config
├── Makefile                     # Build automation
└── install.sh                   # Installer script
```

## Current Status

**Commits on main:**
```
289db99 Add End Reason QC v2.0 with KDE visualization
aa3783e Add files via upload
defaa34 Add experiment registry
8918dd3 Update tests for v2.3.0 and experiment-db skill
784ba79 ONT Ecosystem v2.3.0 - Comprehensive experiment registry
```

**Pending Changes:** 72 modified files ready to commit

**To commit current changes:**
```bash
git add -A
git commit -m "Add domain memory, textbook integration, comprehensive docs

- Domain memory system v2.0 with task dependencies
- Pipeline stages with skill mappings
- Registry INDEX.yaml master index
- Comprehensive system documentation
- GitHub usage guide

🤖 Generated with Claude Code
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

git push origin main
```
