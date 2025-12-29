# ONT Ecosystem

[![CI](https://github.com/Single-Molecule-Sequencing/ont-ecosystem/actions/workflows/ci.yml/badge.svg)](https://github.com/Single-Molecule-Sequencing/ont-ecosystem/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

A comprehensive **consolidated monorepo** (v3.0) for Oxford Nanopore sequencing experiment management with:
- **Full provenance tracking** via Pattern B orchestration
- **Event-sourced registry** with complete audit trail
- **Integrated analysis workflows** (QC, basecalling, alignment, monitoring)
- **SMS Haplotype Framework** (4000+ equations, textbook content)
- **Publication-quality figure/table generation**
- **Connected manuscript repository system**

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
ont-ecosystem/                    # Consolidated Monorepo v3.0
├── bin/                          # Orchestration + wrapper scripts
│   ├── ont_experiments.py        # Core orchestrator (AUTHORITATIVE)
│   ├── experiment_db.py          # Database operations (AUTHORITATIVE)
│   ├── ont_manuscript.py         # Figure/table generation
│   ├── ont_context.py            # Unified experiment view
│   ├── ont_registry.py           # Permanent registry
│   ├── ont_endreason_qc.py       # Enhanced QC visualization
│   ├── end_reason.py             # Wrapper → skills/end-reason/
│   ├── ont_align.py              # Wrapper → skills/ont-align/
│   └── dorado_basecall.py        # Wrapper → skills/dorado-bench-v2/
│
├── skills/                       # Analysis code (AUTHORITATIVE)
│   ├── end-reason/scripts/       # QC analysis source
│   ├── ont-align/scripts/        # Alignment source
│   ├── dorado-bench-v2/scripts/  # Basecalling source
│   ├── ont-monitor/scripts/      # Monitoring source
│   ├── ont-pipeline/scripts/     # Workflow source
│   └── experiment-db/scripts/    # Database source
│
├── textbook/                     # SMS Haplotype Framework (AUTHORITATIVE)
│   ├── equations.yaml            # 4087 equations
│   ├── variables.yaml            # 3532 variables
│   ├── sms.sty                   # LaTeX style package
│   └── src/chapters/             # 24 LaTeX chapter files
│
├── data/                         # Experiment data
│   └── experiment_registry.json  # 145 experiments
│
├── registry/                     # Schemas only (lightweight)
│   ├── INDEX.yaml                # Master index
│   └── schemas/                  # JSON schemas
│
├── dashboards/                   # React JSX components
├── examples/                     # Pipelines + HPC configs
├── tests/                        # 82 pytest tests
└── docs/                         # Architecture docs
```

See [AUTHORITATIVE_SOURCES.md](AUTHORITATIVE_SOURCES.md) for detailed source locations.

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

### Verify Installation

```bash
# Check system health
ont_check.py                      # Full health check
ont_check.py --json               # JSON output for automation

# View ecosystem statistics
ont_stats.py                      # Full statistics
ont_stats.py --brief              # One-line summary
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

## Claude Skills

Upload `.skill` files to Claude Projects for AI-assisted analysis:

```
skills/
├── ont-experiments-v2.skill
├── ont-align.skill
├── ont-pipeline.skill
├── end-reason.skill
├── dorado-bench-v2.skill
└── ont-monitor.skill
```

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
