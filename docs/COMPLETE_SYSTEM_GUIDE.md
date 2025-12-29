# ONT Ecosystem v3.0 - Complete System Guide

A comprehensive guide to the Oxford Nanopore Sequencing Experiment Management System.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Core Components](#core-components)
6. [Skills Reference](#skills-reference)
7. [Tutorials](#tutorials)
8. [Pipeline Workflows](#pipeline-workflows)
9. [HPC Integration](#hpc-integration)
10. [API Reference](#api-reference)
11. [Troubleshooting](#troubleshooting)

---

## System Overview

### What is ONT Ecosystem?

ONT Ecosystem is a comprehensive experiment management system for Oxford Nanopore sequencing data with **~29,000 lines of code**. It provides:

- **Provenance Tracking**: Complete audit trail for all analyses
- **Event-Sourced Registry**: Immutable history of operations
- **Modular Skills**: 10 analysis packages for different tasks
- **HPC Integration**: Native SLURM support with GPU optimization
- **Publication Support**: Automated figure/table generation
- **Mathematical Framework**: 4,000+ equations from SMS textbook

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ONT ECOSYSTEM v3.0                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         USER INTERFACE                               │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐    │   │
│  │  │   CLI    │  │  Slash   │  │   Web    │  │ GitHub Actions   │    │   │
│  │  │ Commands │  │ Commands │  │Dashboard │  │    Workflows     │    │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘    │   │
│  └───────┼─────────────┼─────────────┼─────────────────┼──────────────┘   │
│          │             │             │                 │                   │
│          └─────────────┴──────┬──────┴─────────────────┘                   │
│                               ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    ORCHESTRATION LAYER                               │   │
│  │                                                                      │   │
│  │  ┌──────────────────────────────────────────────────────────────┐   │   │
│  │  │                  ont_experiments.py                           │   │   │
│  │  │                  (Pattern B Orchestrator)                     │   │   │
│  │  │                                                               │   │   │
│  │  │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐    │   │   │
│  │  │   │ create  │  │   run   │  │ history │  │   export    │    │   │   │
│  │  │   │ discover│  │ pipeline│  │  show   │  │   public    │    │   │   │
│  │  │   └─────────┘  └─────────┘  └─────────┘  └─────────────┘    │   │   │
│  │  └──────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                               │                                             │
│          ┌────────────────────┼────────────────────┐                       │
│          ▼                    ▼                    ▼                       │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐                 │
│  │    SKILLS     │   │   REGISTRY    │   │   DATABASE    │                 │
│  │               │   │               │   │               │                 │
│  │ ┌───────────┐ │   │ experiments/  │   │  SQLite DB    │                 │
│  │ │end-reason │ │   │ ├── exp-001/  │   │ ┌───────────┐ │                 │
│  │ │ont-align  │ │   │ │   events.yml│   │ │experiments│ │                 │
│  │ │dorado-    │ │   │ │   tasks.yml │   │ │statistics │ │                 │
│  │ │ bench     │ │   │ ├── exp-002/  │   │ │end_reasons│ │                 │
│  │ │ont-pipe   │ │   │ └── ...       │   │ └───────────┘ │                 │
│  │ │manuscript │ │   │               │   │               │                 │
│  │ │...        │ │   │ experiments   │   │               │                 │
│  │ └───────────┘ │   │   .yaml       │   │               │                 │
│  └───────────────┘   └───────────────┘   └───────────────┘                 │
│          │                    │                    │                       │
│          └────────────────────┼────────────────────┘                       │
│                               ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         DATA LAYER                                   │   │
│  │                                                                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐    │   │
│  │  │  POD5    │  │   BAM    │  │   VCF    │  │   bedMethyl      │    │   │
│  │  │  FAST5   │  │  FASTQ   │  │   BED    │  │   Figures/Tables │    │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pipeline Factorization

The system implements the Pipeline Factorization Theorem from the SMS Haplotype textbook:

```
P(h,g,u,d,ℓ,σ,r) = P(h)·P(g|h)·P(u|g)·P(d|u,C)·P(ℓ|d,C)·P(σ|ℓ,A)·P(r|σ,A)

┌─────────────────────────────────────────────────────────────────────────┐
│                    PIPELINE FACTORIZATION STAGES                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  BIOLOGICAL                    EXPERIMENTAL                COMPUTATIONAL│
│  ───────────                   ────────────                ─────────────│
│                                                                         │
│  ┌───┐      ┌───┐      ┌───┐      ┌───┐      ┌───┐      ┌───┐      ┌───┐
│  │ h │ ──▶  │ g │ ──▶  │ u │ ──▶  │ d │ ──▶  │ ℓ │ ──▶  │ σ │ ──▶  │ r │
│  │   │      │   │      │   │      │   │      │   │      │   │      │   │
│  │Hap│      │Std│      │Gui│      │Frg│      │Lib│      │Sig│      │Bas│
│  └───┘      └───┘      └───┘      └───┘      └───┘      └───┘      └───┘
│    │          │          │          │          │          │          │
│    │          │          │    ┌─────┴────┐     │    ┌─────┴────┐     │
│    │          │          │    │    C     │     │    │    A     │     │
│    │          │          │    │(Cas9     │     │    │(Adaptive │     │
│    │          │          │    │ toggle)  │     │    │ toggle)  │     │
│    │          │          │    └──────────┘     │    └──────────┘     │
│    │          │          │                     │                     │
│    ▼          ▼          ▼                     ▼                     ▼
│  Sample    Sample     Guide                Library              Basecalled
│  Origin    Type       RNA                  Prep                 Sequences
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

Stages:
  h = Haplotype (diploid, population)
  g = Standard (reference genome)
  u = Guide (guide RNA for Cas9)
  d = Fragmentation (shearing method)
  ℓ = Library (preparation chemistry)
  σ = Signal (raw nanopore signal)
  r = Basecall (sequence output)
  C = Cas9 toggle (enrichment)
  A = Adaptive toggle (real-time selection)
```

---

## Architecture

### Directory Structure

```
ont-ecosystem/
│
├── bin/                          # 29 Python scripts
│   ├── ont_experiments.py        # Core orchestrator (3,576 lines)
│   ├── experiment_db.py          # SQLite database
│   ├── ont_endreason_qc.py       # KDE visualization
│   ├── ont_manuscript.py         # Figure generation
│   └── ...                       # Wrappers & utilities
│
├── skills/                       # 10 analysis packages
│   ├── end-reason/               # QC analysis
│   ├── ont-align/                # Alignment
│   ├── dorado-bench-v2/          # Basecalling
│   ├── ont-pipeline/             # Workflows
│   ├── ont-monitor/              # Monitoring
│   ├── experiment-db/            # Database
│   ├── manuscript/               # Figures/tables
│   ├── ont-experiments-v2/       # Registry
│   └── comprehensive-analysis/   # Full analysis
│
├── lib/                          # 12 library modules
│   ├── cli.py                    # Terminal formatting
│   ├── io.py                     # File I/O
│   ├── config.py                 # Configuration
│   ├── validation.py             # Data validation
│   └── ...
│
├── textbook/                     # Mathematical framework
│   ├── equations.yaml            # 4,087 equations
│   ├── variables.yaml            # 3,532 variables
│   └── src/chapters/             # 24 LaTeX chapters
│
├── data/                         # Experiment data
│   └── experiment_registry.json  # 145 experiments
│
├── examples/                     # Templates
│   ├── configs/                  # HPC configurations
│   └── pipelines/                # Workflow definitions
│
├── tests/                        # 96+ pytest tests
├── docs/                         # Documentation
└── .github/workflows/            # 29 GitHub Actions
```

### Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           DATA FLOW                                       │
└──────────────────────────────────────────────────────────────────────────┘

                    ┌───────────────┐
                    │  Raw Data     │
                    │  (POD5/FAST5) │
                    └───────┬───────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                         DISCOVERY PHASE                                    │
│                                                                            │
│  ont_experiments.py discover /data/sequencing_run                          │
│                                                                            │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────┐           │
│  │ Find POD5/     │ ─▶ │ Extract        │ ─▶ │ Register in    │           │
│  │ FAST5 files    │    │ Metadata       │    │ Registry       │           │
│  └────────────────┘    └────────────────┘    └────────────────┘           │
└───────────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                         QC ANALYSIS PHASE                                  │
│                                                                            │
│  ont_experiments.py run end_reasons exp-001 --json qc.json                 │
│                                                                            │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────┐           │
│  │ Load POD5      │ ─▶ │ Calculate End  │ ─▶ │ Generate QC    │           │
│  │ Files          │    │ Reasons        │    │ Report/Plot    │           │
│  └────────────────┘    └────────────────┘    └────────────────┘           │
│                                                                            │
│  Output: { signal_positive: 85%, unblock: 10%, ... }                       │
└───────────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                       BASECALLING PHASE                                    │
│                                                                            │
│  ont_experiments.py run basecalling exp-001 --model sup@v5.0.0             │
│                                                                            │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────┐           │
│  │ Generate SLURM │ ─▶ │ Run Dorado     │ ─▶ │ Output BAM     │           │
│  │ Job Script     │    │ Basecaller     │    │ with Stats     │           │
│  └────────────────┘    └────────────────┘    └────────────────┘           │
│                                                                            │
│  Output: calls.bam, basecalling_stats.json                                 │
└───────────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                        ALIGNMENT PHASE                                     │
│                                                                            │
│  ont_experiments.py run alignment exp-001 --reference GRCh38               │
│                                                                            │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────┐           │
│  │ Load BAM       │ ─▶ │ Run minimap2   │ ─▶ │ Calculate      │           │
│  │ Reads          │    │ Alignment      │    │ Coverage/MAPQ  │           │
│  └────────────────┘    └────────────────┘    └────────────────┘           │
│                                                                            │
│  Output: aligned.bam, alignment_stats.json                                 │
└───────────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                      DOWNSTREAM ANALYSIS                                   │
│                                                                            │
│  Variant Calling ─────────▶ VCF files                                     │
│  Methylation ─────────────▶ bedMethyl                                     │
│  Pharmacogenomics ────────▶ CYP2D6 diplotypes                             │
│  Assembly ────────────────▶ Contigs                                       │
│                                                                            │
└───────────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                       MANUSCRIPT OUTPUT                                    │
│                                                                            │
│  ont_manuscript.py figure fig_end_reason_kde exp-001 --format pdf          │
│                                                                            │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────┐           │
│  │ Load Results   │ ─▶ │ Generate       │ ─▶ │ Export         │           │
│  │ from Registry  │    │ Visualization  │    │ PDF/PNG/LaTeX  │           │
│  └────────────────┘    └────────────────┘    └────────────────┘           │
└───────────────────────────────────────────────────────────────────────────┘
```

### Event Sourcing Model

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       EVENT SOURCING MODEL                                │
└──────────────────────────────────────────────────────────────────────────┘

    Command                    Event Store                    State
    ───────                    ───────────                    ─────

┌──────────────┐           ┌──────────────────┐         ┌──────────────────┐
│ run          │           │ ~/.ont-registry/ │         │ Current State    │
│ end_reasons  │──────────▶│                  │────────▶│                  │
│ exp-001      │           │ experiments.yaml │         │ exp-001:         │
└──────────────┘           │                  │         │   status: active │
                           │ experiments/     │         │   analyses: 3    │
                           │   exp-001/       │         │   last_run: ...  │
                           │     events.yaml  │         │                  │
                           └──────────────────┘         └──────────────────┘

Events are immutable and append-only:

events.yaml:
┌────────────────────────────────────────────────────────────────┐
│ - id: evt-001                                                  │
│   timestamp: 2024-01-15T10:30:00Z                              │
│   type: analysis                                               │
│   skill: end_reasons                                           │
│   command: "ont_experiments.py run end_reasons exp-001 ..."    │
│   duration: 45.2s                                              │
│   exit_code: 0                                                 │
│   outputs:                                                     │
│     - path: qc.json                                            │
│       checksum: sha256:abc123...                               │
│   results:                                                     │
│     signal_positive_pct: 85.2                                  │
│     quality_status: OK                                         │
│   hpc:                                                         │
│     slurm_job_id: 12345                                        │
│     partition: gpu                                             │
│     nodes: 1                                                   │
└────────────────────────────────────────────────────────────────┘
```

---

## Installation

### Quick Install

```bash
# Clone the repository
git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git
cd ont-ecosystem

# Run installer
./install.sh

# Source environment
source ~/.ont-ecosystem/env.sh
```

### Manual Install

```bash
# Install Python dependencies
pip install -e .

# Or with all optional dependencies
pip install -e ".[all]"

# Initialize registry
ont_experiments.py init
```

### Verify Installation

```bash
# Check installation
ont_doctor.py

# Run tests
pytest tests/ -v

# View help
ont_help.py
```

---

## Quick Start

### 1. Discover Experiments

```bash
# Discover experiments in a data directory
ont_experiments.py discover /path/to/sequencing/data

# List discovered experiments
ont_experiments.py list
```

### 2. Run QC Analysis

```bash
# Analyze end reasons
ont_experiments.py run end_reasons exp-001 --json qc.json --plot qc.png

# View results
cat qc.json
```

### 3. View History

```bash
# Show experiment details
ont_experiments.py show exp-001

# View analysis history
ont_experiments.py history exp-001
```

### 4. Generate Figures

```bash
# Create publication figure
ont_manuscript.py figure fig_end_reason_kde exp-001 --format pdf
```

---

## Core Components

### ont_experiments.py - Central Orchestrator

The hub of the ecosystem. All analyses flow through this script.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       ont_experiments.py                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  COMMANDS:                                                              │
│  ─────────                                                              │
│                                                                         │
│  ┌──────────────┬────────────────────────────────────────────────────┐ │
│  │ init         │ Initialize experiment registry                      │ │
│  ├──────────────┼────────────────────────────────────────────────────┤ │
│  │ discover     │ Find experiments in data directories               │ │
│  ├──────────────┼────────────────────────────────────────────────────┤ │
│  │ create       │ Create new experiment with metadata                │ │
│  ├──────────────┼────────────────────────────────────────────────────┤ │
│  │ run          │ Execute analysis skill with provenance             │ │
│  ├──────────────┼────────────────────────────────────────────────────┤ │
│  │ pipeline     │ Run multi-step workflow                            │ │
│  ├──────────────┼────────────────────────────────────────────────────┤ │
│  │ list         │ List experiments with filters                      │ │
│  ├──────────────┼────────────────────────────────────────────────────┤ │
│  │ show         │ Display experiment details                         │ │
│  ├──────────────┼────────────────────────────────────────────────────┤ │
│  │ history      │ View event audit trail                             │ │
│  ├──────────────┼────────────────────────────────────────────────────┤ │
│  │ export       │ Generate command scripts                           │ │
│  ├──────────────┼────────────────────────────────────────────────────┤ │
│  │ public       │ Access public datasets (GIAB, etc.)                │ │
│  └──────────────┴────────────────────────────────────────────────────┘ │
│                                                                         │
│  ANALYSIS SKILLS:                                                       │
│  ────────────────                                                       │
│                                                                         │
│  end_reasons    basecalling    alignment    variants                    │
│  methylation    cyp2d6         pharmcat     monitoring                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Skills Reference

### Available Skills

| Skill | Command | Description |
|-------|---------|-------------|
| End Reason | `/end-reason` | QC analysis of read end reasons |
| Alignment | `/ont-align` | Sequence alignment and edit distance |
| Basecalling | `/dorado-bench` | GPU basecalling with HPC support |
| Pipeline | `/ont-pipeline` | Multi-step workflow orchestration |
| Monitor | `/ont-monitor` | Real-time sequencing monitoring |
| Database | `/experiment-db` | SQLite experiment queries |
| Manuscript | `/manuscript` | Figure and table generation |
| Experiments | `/ont-experiments` | Registry management |
| Full Analysis | `/comprehensive-analysis` | Complete analysis workflow |

### End Reason Quality Thresholds

```
End Reason Categories:
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  signal_positive ████████████████████████████ 85% (Normal)     │
│                                                                │
│  unblock_mux_change ████████ 10% (Adaptive sampling)           │
│                                                                │
│  data_service_unblock ██ 3% (Basecall rejection)               │
│                                                                │
│  mux_change █ 1.5% (Pore multiplex)                            │
│                                                                │
│  signal_negative ░ 0.5% (Signal lost)                          │
│                                                                │
└────────────────────────────────────────────────────────────────┘

Quality Thresholds:
  OK:    signal_positive >= 75%
  CHECK: signal_positive < 75% OR anomalies detected
  FAIL:  signal_positive < 50%
```

---

## Tutorials

### Tutorial 1: First Analysis

```bash
# 1. Initialize (first time only)
ont_experiments.py init

# 2. Discover experiments
ont_experiments.py discover /data/sequencing_runs/20240115_HG002

# 3. Run QC
ont_experiments.py run end_reasons exp-20240115-HG002 --json qc.json

# 4. View results
ont_experiments.py show exp-20240115-HG002
```

### Tutorial 2: Complete Pipeline

```bash
# Run pharmacogenomics pipeline
ont_experiments.py pipeline run pharmaco-clinical exp-001

# Generate figures
ont_manuscript.py figure fig_end_reason_kde exp-001 --format pdf
```

### Tutorial 3: HPC Workflow

```bash
# Generate SLURM script
dorado_basecall.py generate --pod5 /data --model sup --output job.sbatch

# Submit to SLURM
sbatch job.sbatch
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Registry not found | Run `ont_experiments.py init` |
| POD5 read error | Install `pod5` package |
| GPU not detected | Check CUDA and `nvidia-smi` |

### Diagnostic Commands

```bash
ont_doctor.py          # System check
ont_doctor.py --fix    # Auto-fix issues
ont_help.py            # View all commands
```

---

## Version History

- **v3.0** - Complete ecosystem with 10 skills, 29 workflows
- **v2.3** - Experiment registry with 145 experiments
- **v2.0** - Event sourcing and provenance tracking

---

*Generated by ONT Ecosystem v3.0*
