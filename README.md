# ONT Ecosystem

[![CI](https://github.com/Single-Molecule-Sequencing/ont-ecosystem/actions/workflows/ci.yml/badge.svg)](https://github.com/Single-Molecule-Sequencing/ont-ecosystem/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive toolkit for Oxford Nanopore sequencing experiment management with **full provenance tracking**, **event-sourced registry**, and **integrated analysis workflows**.

## Quick Install

```bash
curl -sSL https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/install.sh | bash
source ~/.ont-ecosystem/env.sh
```

## Skills Overview

| Skill | Description | Key Features |
|-------|-------------|--------------|
| **ont-experiments-v2** | Core registry & orchestration | Event sourcing, Pattern B, pipeline integration |
| **ont-align** | Alignment & edit distance | minimap2/dorado, reference mgmt, Levenshtein |
| **ont-pipeline** | Workflow orchestration | Multi-step pipelines, unified QC, batch processing |
| **end-reason** | Read end reason QC | Adaptive sampling analysis, quality thresholds |
| **dorado-bench-v2** | Basecalling workflows | Model management, SLURM generation, GPU optimization |
| **ont-monitor** | Run monitoring | Live dashboard, time-series, alerts |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   ont-experiments-v2 (CORE)                      │
│  • Event-sourced registry (~/.ont-registry/)                     │
│  • Pattern B orchestration (wraps analysis skills)               │
│  • Pipeline integration and unified QC                           │
│  • HPC/SLURM metadata capture                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
    ┌─────────────┬───────────┼───────────┬─────────────┐
    ▼             ▼           ▼           ▼             ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│end-reason│ │dorado-  │ │ont-align│ │ont-     │ │ont-     │
│(QC)     │ │bench    │ │(align)  │ │monitor  │ │pipeline │
│         │ │(basecall)│ │         │ │         │ │         │
└─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
```

## Quick Start

```bash
# Initialize registry
ont_experiments.py init --git

# Discover experiments
ont_experiments.py discover /path/to/sequencing/data --register

# Run QC analysis
ont_experiments.py run end_reasons exp-abc123 --json qc.json

# Basecall with SUP model
ont_experiments.py run basecalling exp-abc123 --model sup@v5.0.0 --output calls.bam

# Align to reference
ont_experiments.py run alignment exp-abc123 --reference GRCh38 --output aligned.bam

# Run complete pipeline
ont_experiments.py pipeline run pharmaco-clinical exp-abc123

# View experiment history
ont_experiments.py history exp-abc123
```

## Feature Highlights

### Pattern B Orchestration

All analyses run through `ont-experiments` for automatic provenance tracking:

```bash
# ✗ Old way (no provenance)
end_reason.py /data/exp --json results.json

# ✓ New way (full provenance)
ont_experiments.py run end_reasons exp-abc123 --json results.json
```

Captures automatically:
- Full command with parameters
- Output file checksums
- Duration and exit code
- HPC metadata (SLURM job ID, nodes, GPUs)
- Results summary in registry

### Edit Distance (Levenshtein)

Fast sequence comparison using edlib:

```bash
# Direct comparison
ont_align.py editdist "ATGGGCGCCCCGCTGAGC" "ATGGGCACCCCGCTGAGC"
# → Edit distance: 1

# With CIGAR string
ont_align.py editdist "ACGT" "ACTT" --cigar --normalize
# → Edit distance: 2, CIGAR: 2=2X, Normalized: 0.5

# Batch comparison from files
ont_align.py editdist --query variants.fa --target refs.fa --output matrix.tsv --threads 8
```

Modes: NW (global), HW (semi-global), SHW (infix)

### Multi-Step Pipelines

Define and execute reproducible workflows:

```bash
# Run clinical pharmacogenomics pipeline
ont_experiments.py pipeline run pharmaco-clinical exp-abc123

# Resume failed pipeline
ont_experiments.py pipeline resume exp-abc123

# Generate unified QC report
ont_experiments.py pipeline report exp-abc123 --format html
```

### HPC Integration

Native SLURM support with GPU-aware job generation:

```bash
# Generate SLURM job for basecalling
dorado_basecall.py /path/to/pod5 --model sup@v5.0.0 \
  --slurm job.sh --partition spgpu --gpu-type a100

# Auto-detect HPC environment
ont_experiments.py run basecalling exp-abc123 --model sup@v5.0.0
# Automatically captures: job_id, partition, nodes, GPUs, walltime
```

## Repository Structure

```
ont-ecosystem/
├── bin/                          # Executable scripts
│   ├── ont_experiments.py        # Core orchestration
│   ├── ont_align.py              # Alignment + edit distance
│   ├── ont_pipeline.py           # Pipeline orchestration
│   ├── end_reason.py             # QC analysis
│   ├── ont_monitor.py            # Run monitoring
│   ├── dorado_basecall.py        # Basecalling
│   └── calculate_resources.py    # Resource estimation
├── skills/                       # Claude skill packages
│   ├── ont-experiments-v2/
│   ├── ont-align/
│   ├── ont-pipeline/
│   ├── end-reason/
│   ├── dorado-bench-v2/
│   └── ont-monitor/
├── dashboards/                   # React visualization components
│   ├── ont-experiments-dashboard.jsx
│   ├── ont-align-dashboard.jsx
│   └── ont-workflow-dashboard.jsx
├── docs/                         # Documentation
├── tests/                        # Unit tests
└── lib/                          # Shared libraries
```

## Installation

### One-line Install

```bash
curl -sSL https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/install.sh | bash
source ~/.ont-ecosystem/env.sh
```

### HPC Installation (Great Lakes / ARMIS2)

```bash
module load python/3.10
git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git
cd ont-ecosystem
./install.sh --hpc
source ~/.ont-ecosystem/env.sh
```

### Dependencies

```bash
# Core
pip install pyyaml

# Analysis
pip install pysam edlib numpy pandas matplotlib

# POD5/Fast5
pip install pod5 h5py

# Web dashboard
pip install flask

# External tools (system)
# minimap2, samtools, dorado
```

## Claude Integration

### Quick Setup for Claude Projects

1. **Upload configuration file**:
   ```
   CLAUDE.md                    # Comprehensive Claude guide
   ```

2. **Upload required skills**:
   ```
   skills/ont-experiments-v2.skill    # Core (always required)
   skills/end-reason.skill            # QC analysis
   skills/ont-align.skill             # Alignment
   skills/ont-pipeline.skill          # Pipelines
   ```

3. **Upload your experiment registry** (optional):
   ```
   registry/experiments.yaml
   ```

4. **Start using Claude** with natural language:
   ```
   "Analyze the end reasons for my latest SMAseq experiment"
   "Compare N50 across all my PromethION runs"
   "Run the pharmacogenomics pipeline on exp-abc123"
   ```

### Available Skills

| Skill | File | Purpose |
|-------|------|---------|
| **Core** | `ont-experiments-v2.skill` | Registry, orchestration, provenance |
| **QC** | `end-reason.skill` | End reason analysis, quality status |
| **Alignment** | `ont-align.skill` | Mapping, edit distance calculation |
| **Pipeline** | `ont-pipeline.skill` | Multi-step workflow orchestration |
| **Basecalling** | `dorado-bench-v2.skill` | GPU basecalling with HPC support |
| **Monitoring** | `ont-monitor.skill` | Real-time run monitoring |
| **Database** | `experiment-db.skill` | SQLite queries and export |

### Skill Sets by Use Case

```bash
# Minimal (experiment management only)
skills/ont-experiments-v2.skill

# QC Workflow
skills/ont-experiments-v2.skill
skills/end-reason.skill
skills/ont-monitor.skill

# SMAseq Analysis
skills/ont-experiments-v2.skill
skills/end-reason.skill
# + bin/ont_smaseq_readlen.py

# Clinical/Pharmacogenomics
skills/ont-experiments-v2.skill
skills/end-reason.skill
skills/ont-pipeline.skill
skills/dorado-bench-v2.skill
skills/ont-align.skill
```

### Updating Claude

When new versions are released:

1. Pull latest changes: `git pull origin main`
2. Re-upload updated `.skill` files to Claude Projects
3. Re-upload `CLAUDE.md` for updated instructions
4. Verify in conversation: "What version of ont-experiments is loaded?"

See **[CLAUDE.md](CLAUDE.md)** for complete setup and usage guide.

### Skill Development

To create new skills, see:
- **[docs/SKILL_TEMPLATE.md](docs/SKILL_TEMPLATE.md)** - Skill template and structure
- **[docs/SKILL_DEVELOPMENT.md](docs/SKILL_DEVELOPMENT.md)** - Development guide
- **[skills/MANIFEST.yaml](skills/MANIFEST.yaml)** - Skill registry

## Complete CYP2D6 Workflow

```bash
# 1. Register new PromethION run
ont_experiments.py register /nfs/turbo/umms-athey/runs/20240115 \
  --tags "cyp2d6,patient_cohort,batch1"

# 2. Monitor during sequencing
ont_experiments.py run monitoring exp-20240115 --live --interval 60

# 3. QC check after completion
ont_experiments.py run end_reasons exp-20240115 --json qc.json --plot qc.png

# 4. Basecall with SUP model on HPC
sbatch --partition=sigbio-a40 --gres=gpu:a40:1 --mem=100G --time=72:00:00 --wrap="\
  ont_experiments.py run basecalling exp-20240115 \
    --model sup@v5.0.0 \
    --output /scratch/basecalled.bam"

# 5. Align to T2T reference
ont_experiments.py run alignment exp-20240115 \
  --ref hs1 --output /scratch/aligned.bam

# 6. Run pharmacogenomics pipeline
ont_experiments.py pipeline run pharmaco-clinical exp-20240115

# 7. Review complete history
ont_experiments.py history exp-20240115

# 8. Export for documentation
ont_experiments.py export exp-20240115 > analysis_commands.sh
```

## Public Datasets

Access 35+ curated ONT Open Data datasets:

```bash
# List available datasets
ont_experiments.py public

# Filter by category
ont_experiments.py public --category cancer

# Fetch with auto-registration
ont_experiments.py fetch giab_2025.01 /data/public --register
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

Single Molecule Sequencing Lab, University of Michigan

## Related Repositories

| Repository | Description |
|------------|-------------|
| [dorado-bench](https://github.com/Single-Molecule-Sequencing/dorado-bench) | Dorado model benchmarking |
| [dorado-run](https://github.com/Single-Molecule-Sequencing/dorado-run) | Dorado execution tool |
| [End_Reason_nf](https://github.com/Single-Molecule-Sequencing/End_Reason_nf) | End reason Nextflow |
| [PGx-prep](https://github.com/Single-Molecule-Sequencing/PGx-prep) | PGx BAM preprocessing |
