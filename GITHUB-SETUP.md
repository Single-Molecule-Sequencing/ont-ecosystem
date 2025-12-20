# ONT Ecosystem - GitHub Setup Instructions

## Quick Setup

### 1. Extract the repository

```bash
tar -xzf ont-ecosystem.tar.gz
cd ont-ecosystem
```

### 2. Create the GitHub repository

Go to: https://github.com/organizations/Single-Molecule-Sequencing/repositories/new

- **Name**: `ont-ecosystem`
- **Description**: `Oxford Nanopore experiment management with provenance tracking`
- **Visibility**: Public
- **Initialize**: Do NOT add README, .gitignore, or license (we have our own)

### 3. Push to GitHub

```bash
# Initialize and push
git init
git add -A
git commit -m "Initial commit: ONT Ecosystem v2.1"
git branch -M main
git remote add origin https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git
git push -u origin main
```

Or use the helper script:
```bash
./setup-github.sh
git remote add origin https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git
git push -u origin main
```

### 4. Verify

After pushing, the repository will be at:
https://github.com/Single-Molecule-Sequencing/ont-ecosystem

GitHub Actions CI will automatically run on push.

## Install Command

Once pushed, anyone can install with:

```bash
curl -sSL https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/install.sh | bash
```

## Repository Structure

```
ont-ecosystem/
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ install.sh              # One-line installer
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ setup-github.sh         # Helper for GitHub setup
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ README.md               # Main documentation
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ CONTRIBUTING.md         # Contribution guide
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ LICENSE                 # MIT License
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ pyproject.toml          # Python packaging
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ .gitignore
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ .github/workflows/
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ ci.yml              # GitHub Actions CI
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ bin/
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ont_experiments.py  # Core orchestration
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ont_monitor.py      # Run monitoring
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ ont_align.py        # Alignment
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ end_reason.py       # QC analysis
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ ont_dashboard.py    # Web UI
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ lib/
Ã¢â€â€š   Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ __init__.py
Ã¢â€â€š   Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ ont_core.py         # Shared library
Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ tests/
    Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ __init__.py
    Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ test_core.py        # Unit tests
```

## Integration with Existing Repos

The ont-ecosystem integrates with your existing repositories:

| Existing Repo | Integration |
|--------------|-------------|
| dorado-bench | Use as basecalling backend |
| dorado-run | Integrated via dorado-bench skill |
| End_Reason_nf | Python version included as skill |
| PGx-prep | Can orchestrate via Pattern B |

## HPC Setup (Great Lakes)

```bash
# On Great Lakes
module load python/3.10

# Install
curl -sSL https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/install.sh | bash

# Or with local clone
git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git
cd ont-ecosystem
./install.sh --hpc

# Activate
source ~/.ont-ecosystem/env.sh

# Test
ont_experiments.py init
ont_experiments.py discover /nfs/turbo/umms-athey/runs --register
```
