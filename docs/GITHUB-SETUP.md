# ONT Ecosystem - GitHub Setup Instructions

## Quick Setup

### 1. Extract the Repository

```bash
tar -xzf ont-ecosystem-complete.tar.gz
cd ont-ecosystem-complete
```

### 2. Create the GitHub Repository

Go to: https://github.com/organizations/Single-Molecule-Sequencing/repositories/new

- **Name**: `ont-ecosystem`
- **Description**: `Oxford Nanopore experiment management with provenance tracking`
- **Visibility**: Public
- **Initialize**: Do NOT add README, .gitignore, or license (we have our own)

### 3. Push to GitHub

```bash
# Use the helper script
./push-to-github.sh
git push -u origin main
```

Or manually:
```bash
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
source ~/.ont-ecosystem/env.sh
```

## Repository Structure

```
ont-ecosystem/
├── bin/                          # Executable scripts (10 files)
│   ├── ont_experiments.py        # Core orchestration (55KB)
│   ├── ont_align.py              # Alignment + edit distance (36KB)
│   ├── ont_pipeline.py           # Pipeline orchestration (35KB)
│   ├── ont_monitor.py            # Run monitoring (46KB)
│   ├── end_reason.py             # QC analysis (20KB)
│   ├── dorado_basecall.py        # Basecalling (26KB)
│   ├── ont_registry.py           # Registry database
│   ├── ont_dashboard.py          # Web dashboard
│   ├── calculate_resources.py    # Resource estimation
│   └── make_sbatch_from_cmdtxt.py
├── skills/                       # Claude skill packages (6 skills)
│   ├── ont-experiments-v2/       # Core + .skill file
│   ├── ont-align/                # Alignment + .skill file
│   ├── ont-pipeline/             # Pipeline + .skill file
│   ├── end-reason/               # QC + .skill file
│   ├── dorado-bench-v2/          # Basecalling + .skill file
│   └── ont-monitor/              # Monitoring + .skill file
├── dashboards/                   # React visualization (4 files)
├── examples/
│   ├── pipelines/                # 3 pipeline YAML templates
│   └── configs/                  # 3 HPC configuration examples
├── docs/                         # Documentation
├── tests/                        # pytest test suite
├── lib/                          # Shared library
├── .github/workflows/ci.yml      # GitHub Actions CI
├── README.md                     # Main documentation
├── LICENSE                       # MIT License
├── CONTRIBUTING.md               # Contribution guide
├── Makefile                      # Build automation
├── pyproject.toml                # Python packaging
├── install.sh                    # One-line installer
└── push-to-github.sh             # GitHub push helper
```

## HPC Setup (Great Lakes)

```bash
# On Great Lakes
module load python/3.10

# Install
curl -sSL https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/install.sh | bash

# Or from local clone
git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git
cd ont-ecosystem
./install.sh --hpc

# Activate
source ~/.ont-ecosystem/env.sh

# Test
ont_experiments.py init
ont_experiments.py discover /nfs/turbo/umms-athey/runs --register
```

## Using Claude Skills

Upload `.skill` files from `skills/` directory to Claude Projects:

1. Go to Claude Projects
2. Create new project or open existing
3. Upload skill files:
   - `ont-experiments-v2.skill` - Core registry
   - `ont-align.skill` - Alignment
   - `ont-pipeline.skill` - Workflows
   - `end-reason.skill` - QC
   - `dorado-bench-v2.skill` - Basecalling
   - `ont-monitor.skill` - Monitoring

4. Claude can now assist with ONT analysis using these skills

## Integration with Existing Repos

| Existing Repo | Integration |
|--------------|-------------|
| [dorado-bench](https://github.com/Single-Molecule-Sequencing/dorado-bench) | Basecalling backend |
| [dorado-run](https://github.com/Single-Molecule-Sequencing/dorado-run) | Dorado execution |
| [End_Reason_nf](https://github.com/Single-Molecule-Sequencing/End_Reason_nf) | QC workflow |
| [PGx-prep](https://github.com/Single-Molecule-Sequencing/PGx-prep) | Sample prep |
