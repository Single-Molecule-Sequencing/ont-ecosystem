# ONT Ecosystem - Complete System Guide

## System Overview

The ONT Ecosystem is a comprehensive toolkit for Oxford Nanopore sequencing experiment management with **~29,000 lines of code**, featuring:

- **Event-sourced registry** for full provenance tracking
- **Pattern B orchestration** routing all analysis through a central hub
- **7 specialized skills** for different analysis tasks
- **Pipeline Factorization Theorem** integration from SMS Haplotype Framework Textbook
- **Domain memory system** for AI agent workflows

```
                           ONT ECOSYSTEM ARCHITECTURE
    ═══════════════════════════════════════════════════════════════════════

                        ┌─────────────────────────────────┐
                        │         USER INTERFACE          │
                        │   CLI / Web Dashboard / Claude  │
                        └───────────────┬─────────────────┘
                                        │
                        ┌───────────────▼─────────────────┐
                        │     ont_experiments.py          │
                        │   ══════════════════════════    │
                        │   CORE ORCHESTRATION HUB        │
                        │   (Pattern B - 2,944 lines)     │
                        │                                 │
                        │   • Event-sourced registry      │
                        │   • Skill dispatch              │
                        │   • HPC metadata capture        │
                        │   • Domain memory management    │
                        │   • GitHub sync                 │
                        └───────────────┬─────────────────┘
                                        │
            ┌───────────────────────────┼───────────────────────────┐
            │                           │                           │
    ┌───────▼───────┐           ┌───────▼───────┐           ┌───────▼───────┐
    │ ANALYSIS      │           │ ORCHESTRATION │           │ DATA ACCESS   │
    │ SKILLS        │           │ LAYER         │           │ LAYER         │
    ├───────────────┤           ├───────────────┤           ├───────────────┤
    │ • end-reason  │           │ ont_pipeline  │           │ experiment_db │
    │   (σ stage)   │           │   (1,028 ln)  │           │   (769 ln)    │
    │               │           │               │           │               │
    │ • ont-monitor │           │ Workflows:    │           │ • Discovery   │
    │   (σ stage)   │           │ • pharmaco    │           │ • SQLite DB   │
    │               │           │ • qc-fast     │           │ • Queries     │
    │ • dorado-bench│           │ • research    │           │               │
    │   (r stage)   │           │               │           │ Public Data:  │
    │               │           │               │           │ • 35+ datasets│
    │ • ont-align   │           │               │           │ • S3 access   │
    │   (r stage)   │           │               │           │               │
    └───────────────┘           └───────────────┘           └───────────────┘
            │                           │                           │
            └───────────────────────────┼───────────────────────────┘
                                        │
                        ┌───────────────▼─────────────────┐
                        │         REGISTRY SYSTEM         │
                        │   ══════════════════════════    │
                        │                                 │
                        │   ~/.ont-registry/              │
                        │   ├── experiments.yaml          │
                        │   └── experiments/              │
                        │       └── exp-id/               │
                        │           ├── tasks.yaml        │
                        │           └── PROGRESS.md       │
                        │                                 │
                        │   registry/                     │
                        │   ├── INDEX.yaml                │
                        │   ├── textbook/ (10K lines)     │
                        │   ├── pipeline/stages.yaml      │
                        │   └── schemas/*.json            │
                        └─────────────────────────────────┘
```

## Component Inventory

### Executable Scripts (bin/) - 9,845 lines

| Script | Lines | Stage | Purpose |
|--------|-------|-------|---------|
| `ont_experiments.py` | 2,944 | Core | Event-sourced registry & Pattern B orchestration |
| `ont_monitor.py` | 1,242 | σ | Real-time and retrospective run monitoring |
| `ont_align.py` | 1,060 | r | Alignment & Levenshtein edit distance |
| `ont_pipeline.py` | 1,028 | r,A | Multi-step workflow orchestration |
| `dorado_basecall.py` | 833 | r | GPU basecalling with model management |
| `experiment_db.py` | 769 | - | SQLite experiment database builder |
| `ont_endreason_qc.py` | 591 | σ | Enhanced KDE-based end reason QC |
| `end_reason.py` | 580 | σ | Read end reason QC analysis |
| `make_sbatch_from_cmdtxt.py` | 251 | - | SLURM batch script generator |
| `ont_dashboard.py` | 228 | - | Web dashboard (Flask) |
| `ont_registry.py` | 197 | - | Registry query tool |
| `calculate_resources.py` | 122 | - | GPU resource estimation |

### Skills (skills/) - 7 packages

| Skill | Stage | Scripts | Purpose |
|-------|-------|---------|---------|
| **ont-experiments-v2** | Core | ont_experiments.py | Registry & orchestration |
| **end-reason** | σ | end_reason.py | Signal termination analysis |
| **ont-monitor** | σ | ont_monitor.py | Run monitoring |
| **dorado-bench-v2** | r | dorado_basecall.py, calculate_resources.py | GPU basecalling |
| **ont-align** | r | ont_align.py | Alignment & edit distance |
| **ont-pipeline** | r,A | ont_pipeline.py | Workflow orchestration |
| **experiment-db** | - | experiment_db.py, experiment_montage.py | Database building |

### Registry System - 10,207 lines

```
registry/
├── INDEX.yaml                 # Master index of all components
├── experiments.yaml           # Pre-built experiment registry (145 experiments)
│
├── textbook/                  # SMS Haplotype Framework Textbook content
│   ├── equations_full.yaml    # 4,087 lines - complete equation database
│   ├── variables_full.yaml    # 3,532 lines - variable definitions
│   ├── all_math_authoritative.yaml  # AUTHORITATIVE math from All_Math PDF
│   ├── frameworks.yaml        # SMA-SEER & Pipeline Factorization
│   ├── definitions.yaml       # Formal theorems
│   ├── qc_gates.yaml          # QC thresholds
│   └── chapters.yaml          # Chapter index
│
├── pipeline/
│   └── stages.yaml            # 9 pipeline stages with skill mappings
│
└── schemas/                   # JSON Schema validation
    ├── experiment.json
    ├── equation.json
    ├── pipeline_stage.json
    ├── task.json
    └── task_list.json
```

## Pipeline Factorization Theorem

The core mathematical framework from SMS Haplotype Framework Textbook (Chapter 4):

```
                    PIPELINE FACTORIZATION THEOREM (CE.1)
    ═══════════════════════════════════════════════════════════════════════

    P(h,g,u,d,ℓ,σ,r) = P(h)·P(g|h)·P(u|g)·P(d|u,C)·P(ℓ|d,C)·P(σ|ℓ,A)·P(r|σ,A)


    ┌──────┐    ┌──────┐    ┌──────┐    ┌──────┐    ┌──────┐    ┌──────┐    ┌──────┐
    │  h   │───▶│  g   │───▶│  u   │───▶│  d   │───▶│  ℓ   │───▶│  σ   │───▶│  r   │
    │      │    │      │    │      │    │      │    │      │    │      │    │      │
    │ P(h) │    │P(g|h)│    │P(u|g)│    │P(d|u)│    │P(ℓ|d)│    │P(σ|ℓ)│    │P(r|σ)│
    └──────┘    └──────┘    └──────┘    └──────┘    └──────┘    └──────┘    └──────┘
       │           │           │           │           │           │           │
       │           │           │           │           │           │           │
       ▼           ▼           ▼           ▼           ▼           ▼           ▼
    Haplotype  Standard    Guide      Post-Cas9   Library    Signal    Basecalling
    Selection  Assembly    Design     Fragment    Loading    Acquire

       │           │           │           │           │           │           │
       ▼           ▼           ▼           ▼           ▼           ▼           ▼
       PGx      Golden      Cas9        Cas9        HTC        ONT        AI/
               Gate     Enrichment  Enrichment              Adaptive   Basecaller

                                                               │           │
                                                               ▼           ▼
                                                           end-reason  dorado-bench
                                                           ont-monitor ont-align

    Toggle Variables:
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │  C = Cas9 Toggle (0 or 1)     │  A = Adaptive Sampling Toggle (0 or 1)     │
    │  Affects: d, ℓ stages         │  Affects: σ, r stages                       │
    └─────────────────────────────────────────────────────────────────────────────┘
```

### Stage-to-Skill Mapping

| Stage | Symbol | Probability | Skills | Key Equations |
|-------|--------|-------------|--------|---------------|
| Haplotype Selection | h | P(h) | - | Population genetics |
| Standard Construction | g | P(g\|h) | - | Purity: π |
| Guide Design | u | P(u\|g) | - | gRNA efficiency |
| Post-Cas9 Fragmentation | d | P(d\|u,C) | - | Fragment distribution |
| Library Loading | ℓ | P(ℓ\|d,C) | - | Loading efficiency |
| **Signal Acquisition** | **σ** | **P(σ\|ℓ,A)** | **end-reason, ont-monitor** | signal_positive, unblock_rate |
| **Basecalling** | **r** | **P(r\|σ,A)** | **dorado-bench, ont-align** | Phred (1.1.1), Levenshtein (1.1.2) |
| Cas9 Toggle | C | P(C) | - | Binary switch |
| Adaptive Toggle | A | P(A) | - | Binary switch |

## Data Flow Architecture

```
                           DATA FLOW THROUGH SYSTEM
    ═══════════════════════════════════════════════════════════════════════

    INPUT DATA                    ANALYSIS                     OUTPUT
    ──────────                    ────────                     ──────

    ┌──────────────┐
    │  POD5/FAST5  │──────┐
    │  Raw Signals │      │
    └──────────────┘      │       ┌─────────────────────┐      ┌──────────────┐
                          ├──────▶│    end_reason.py    │─────▶│ QC Report    │
    ┌──────────────┐      │       │    ont_endreason_qc │      │ JSON + PNG   │
    │  Sequencing  │──────┤       └─────────────────────┘      └──────────────┘
    │  Summary.txt │      │
    └──────────────┘      │       ┌─────────────────────┐      ┌──────────────┐
                          ├──────▶│   ont_monitor.py    │─────▶│ Dashboard    │
    ┌──────────────┐      │       │   (live/snapshot)   │      │ JSON + PNG   │
    │  MinKNOW     │──────┤       └─────────────────────┘      └──────────────┘
    │  Logs        │      │
    └──────────────┘      │       ┌─────────────────────┐      ┌──────────────┐
                          │       │  dorado_basecall.py │      │ BAM File     │
    ┌──────────────┐      ├──────▶│  (GPU basecalling)  │─────▶│ Q-scores     │
    │  Reference   │      │       └─────────────────────┘      │ Statistics   │
    │  Genome      │──────┤                                    └──────────────┘
    └──────────────┘      │
                          │       ┌─────────────────────┐      ┌──────────────┐
    ┌──────────────┐      │       │    ont_align.py     │      │ Aligned BAM  │
    │  FASTQ/BAM   │──────┴──────▶│ (minimap2 + edlib)  │─────▶│ Edit Distance│
    │  Reads       │              └─────────────────────┘      │ Coverage     │
    └──────────────┘                                           └──────────────┘


                          ALL RESULTS LOGGED TO REGISTRY
                          ──────────────────────────────

                          ┌─────────────────────────────────┐
                          │     ~/.ont-registry/            │
                          │                                 │
                          │  experiments.yaml               │
                          │  ┌─────────────────────────────┐│
                          │  │ exp-abc123:                 ││
                          │  │   events:                   ││
                          │  │   - type: analysis          ││
                          │  │     tool: end_reason.py     ││
                          │  │     results:                ││
                          │  │       quality_grade: A      ││
                          │  │       signal_positive: 92%  ││
                          │  │     exit_code: 0            ││
                          │  │     duration: 45.2s         ││
                          │  └─────────────────────────────┘│
                          └─────────────────────────────────┘
```

## Domain Memory System

Based on Anthropic's agent memory patterns for stateful AI workflows:

```
                          DOMAIN MEMORY ARCHITECTURE
    ═══════════════════════════════════════════════════════════════════════

    ~/.ont-registry/experiments/
    └── exp-abc123/
        │
        ├── tasks.yaml              # Machine-readable task backlog
        │   ┌────────────────────────────────────────────────────────────┐
        │   │ tasks:                                                     │
        │   │   - name: end_reasons                                      │
        │   │     status: passing          ✓                             │
        │   │     pipeline_stage: σ                                      │
        │   │     attempts: 1                                            │
        │   │                                                            │
        │   │   - name: basecalling                                      │
        │   │     status: in_progress      ◐                             │
        │   │     pipeline_stage: r                                      │
        │   │     dependencies: [end_reasons]                            │
        │   │                                                            │
        │   │   - name: alignment                                        │
        │   │     status: pending          ○                             │
        │   │     pipeline_stage: r                                      │
        │   │     dependencies: [basecalling]                            │
        │   └────────────────────────────────────────────────────────────┘
        │
        └── PROGRESS.md             # Human-readable progress log
            ┌────────────────────────────────────────────────────────────┐
            │ # Progress Log: exp-abc123                                 │
            │                                                            │
            │ ## 2025-12-28 14:30 - end_reasons                          │
            │ - ✓ Ran end_reasons                                        │
            │ - Exit code: 0                                             │
            │ - Duration: 45.2s                                          │
            │ - quality_grade: A                                         │
            │ - signal_positive_pct: 92.5%                               │
            │                                                            │
            │ ## 2025-12-28 15:00 - basecalling                          │
            │ - ◐ Started basecalling with SUP model                     │
            │ - GPU: A100 (SLURM job 12345678)                           │
            └────────────────────────────────────────────────────────────┘


    TASK STATE MACHINE
    ══════════════════

         ○ pending
             │
             ▼
         ◐ in_progress
            ╱  ╲
           ╱    ╲
          ▼      ▼
      ✓ passing  ✗ failing
                    │
                    ▼
                 − skipped


    BOOTUP RITUAL (for AI agents)
    ══════════════════════════════

    1. ont_experiments.py next exp-id --json
       │
       ▼
    ┌─────────────────────────────────────────┐
    │ {                                       │
    │   "experiment_id": "exp-abc123",        │
    │   "pending_tasks": ["alignment"],       │
    │   "failing_tasks": [],                  │
    │   "next_task": {                        │
    │     "name": "alignment",                │
    │     "runnable": true,                   │
    │     "command": "ont_experiments.py      │
    │                 run alignment exp-abc123"│
    │   }                                     │
    │ }                                       │
    └─────────────────────────────────────────┘
```

## GitHub Integration

### Repository Structure

```
    https://github.com/Single-Molecule-Sequencing/ont-ecosystem
    ═══════════════════════════════════════════════════════════════════════

    ont-ecosystem/
    │
    ├── .github/
    │   └── workflows/
    │       └── ci.yml              # GitHub Actions CI/CD
    │
    ├── bin/                        # 12 executable scripts (9,845 lines)
    ├── skills/                     # 7 skill packages
    ├── registry/                   # Domain knowledge (10,207 lines)
    ├── tests/                      # 30 tests (816 lines)
    ├── docs/                       # Documentation
    ├── dashboards/                 # React visualization components
    ├── examples/                   # Pipeline & HPC configs
    │
    ├── README.md                   # Project overview
    ├── CLAUDE.md                   # AI assistant guidance
    ├── pyproject.toml              # Package configuration
    ├── Makefile                    # Build automation
    └── install.sh                  # One-line installer
```

### CI/CD Pipeline

```
    GITHUB ACTIONS WORKFLOW (ci.yml)
    ═══════════════════════════════════════════════════════════════════════

    ┌─────────────────────────────────────────────────────────────────────┐
    │                         ON: push / pull_request                     │
    └───────────────────────────────┬─────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
            ┌───────▼───────┐               ┌───────▼───────┐
            │     TEST      │               │     LINT      │
            │               │               │               │
            │ Matrix:       │               │ py_compile    │
            │ Python 3.9    │               │ all bin/*.py  │
            │ Python 3.10   │               │               │
            │ Python 3.11   │               └───────┬───────┘
            │ Python 3.12   │                       │
            │               │                       │
            │ Steps:        │                       │
            │ 1. Checkout   │                       │
            │ 2. Setup Py   │                       │
            │ 3. Install    │                       │
            │ 4. Syntax     │                       │
            │ 5. Frontmatter│                       │
            │ 6. pytest     │                       │
            └───────┬───────┘                       │
                    │                               │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │          RESULTS              │
                    │                               │
                    │  ✓ 30/30 tests passing        │
                    │  ✓ All syntax valid           │
                    │  ✓ All frontmatter valid      │
                    └───────────────────────────────┘
```

### Installation Methods

```
    INSTALLATION OPTIONS
    ═══════════════════════════════════════════════════════════════════════

    METHOD 1: One-Line Install (Recommended)
    ─────────────────────────────────────────

    $ curl -sSL https://raw.githubusercontent.com/Single-Molecule-Sequencing/\
           ont-ecosystem/main/install.sh | bash
    $ source ~/.ont-ecosystem/env.sh


    METHOD 2: Git Clone
    ────────────────────

    $ git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git
    $ cd ont-ecosystem
    $ make install      # Core dependencies
    $ make install-dev  # Full development environment


    METHOD 3: HPC Installation (Great Lakes / ARMIS2)
    ──────────────────────────────────────────────────

    $ module load python/3.10
    $ git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git
    $ cd ont-ecosystem
    $ ./install.sh --hpc
    $ source ~/.ont-ecosystem/env.sh


    DEPENDENCY TIERS
    ════════════════

    CORE (Required):
    ├── pyyaml >= 6.0
    └── jsonschema >= 4.0

    ANALYSIS (Optional but Recommended):
    ├── pysam >= 0.21.0        # BAM processing
    ├── edlib >= 1.3.9         # Edit distance
    ├── numpy >= 1.20          # Numerical ops
    ├── pandas >= 1.5          # Data frames
    ├── matplotlib >= 3.5      # Visualization
    ├── scipy >= 1.7           # KDE smoothing
    ├── pod5 >= 0.3.0          # POD5 format
    └── h5py >= 3.0            # FAST5 format

    EXTERNAL TOOLS:
    ├── minimap2 >= 2.20       # Alignment
    ├── samtools >= 1.15       # BAM processing
    ├── dorado >= 1.1.1        # Basecalling
    └── git                    # Registry sync
```

## Complete Workflow Example

```
    PHARMACOGENOMICS WORKFLOW: CYP2D6 Analysis
    ═══════════════════════════════════════════════════════════════════════

    STEP 1: Initialize Registry
    ───────────────────────────
    $ ont_experiments.py init --git

    Created: ~/.ont-registry/
             ├── experiments.yaml
             └── .git/


    STEP 2: Discover Experiments
    ────────────────────────────
    $ ont_experiments.py discover /nfs/turbo/umms-athey/runs/2024 --register

    Found: 15 experiments
    Registered: exp-20240115, exp-20240116, ...


    STEP 3: Initialize Domain Memory
    ─────────────────────────────────
    $ ont_experiments.py init-tasks exp-20240115

    Created: ~/.ont-registry/experiments/exp-20240115/
             ├── tasks.yaml (5 pending tasks)
             └── PROGRESS.md


    STEP 4: Check Next Task
    ───────────────────────
    $ ont_experiments.py next exp-20240115

    NEXT: end_reasons (pending)
    Run: ont_experiments.py run end_reasons exp-20240115


    STEP 5: Run QC Analysis
    ───────────────────────
    $ ont_experiments.py run end_reasons exp-20240115 --json qc.json --plot qc.png

    ✓ Analysis complete
    ✓ Quality grade: A
    ✓ Signal positive: 92.5%
    ✓ Event logged to registry


    STEP 6: Basecall with SUP Model (HPC)
    ──────────────────────────────────────
    $ sbatch --partition=spgpu --gres=gpu:a100:1 --mem=100G --time=72:00:00 --wrap="\
        ont_experiments.py run basecalling exp-20240115 \
          --model sup@v5.0.0 \
          --output /scratch/basecalled.bam"

    Submitted batch job 12345678


    STEP 7: Align to Reference
    ──────────────────────────
    $ ont_experiments.py run alignment exp-20240115 \
        --ref hs1 --output /scratch/aligned.bam

    ✓ Mapped reads: 1.2M
    ✓ Mapping rate: 98.7%


    STEP 8: Run Pipeline
    ────────────────────
    $ ont_experiments.py pipeline run pharmaco-clinical exp-20240115

    Step 1/5: qc ................ ✓
    Step 2/5: basecall .......... ✓
    Step 3/5: align ............. ✓
    Step 4/5: variants .......... ✓
    Step 5/5: pharmcat .......... ✓


    STEP 9: View History
    ────────────────────
    $ ont_experiments.py history exp-20240115

    Event History for exp-20240115 (CYP2D6 Run 1)
    ═══════════════════════════════════════════════
    [2024-01-15 10:00] discovered - Found experiment
    [2024-01-15 10:05] registered - Registered with tags: cyp2d6,clinical
    [2024-01-15 14:30] analysis - end_reasons: grade=A, sp=92.5%
    [2024-01-15 16:00] analysis - basecalling: model=sup@v5.0.0
    [2024-01-16 10:00] analysis - alignment: mapped=98.7%
    [2024-01-16 12:00] pipeline - pharmaco-clinical: COMPLETE


    STEP 10: Export Commands
    ────────────────────────
    $ ont_experiments.py export exp-20240115 > analysis_commands.sh

    # Reproducible command history saved
```

## Key Equations Reference

From the SMS Haplotype Framework Textbook (All_Math PDF - AUTHORITATIVE):

| ID | Name | LaTeX | Usage |
|----|------|-------|-------|
| 1.1.1 | Phred to Error | `p = 10^{-Q/10}` | Basecalling quality |
| 1.1.2 | Levenshtein | `d(s,r) ∈ ℕ₀` | Edit distance |
| 5.2 | Purity Ceiling | `TPR ≤ π` | Physical limits |
| 6.6 | Bayesian Posterior | `P(h\|r) = P(r\|h)P(h) / ΣP(r\|h')P(h')` | Classification |
| CE.1 | Pipeline Factorization | `P(h,g,u,d,ℓ,σ,r) = ...` | Core framework |

## Quick Reference

### Common Commands

```bash
# Registry
ont_experiments.py init --git                    # Initialize
ont_experiments.py discover /path --register    # Discover & register
ont_experiments.py list                          # List experiments
ont_experiments.py info exp-id                   # Show details
ont_experiments.py history exp-id                # Event history

# Analysis (Pattern B)
ont_experiments.py run end_reasons exp-id        # QC
ont_experiments.py run basecalling exp-id        # Basecall
ont_experiments.py run alignment exp-id          # Align

# Domain Memory
ont_experiments.py init-tasks exp-id             # Initialize
ont_experiments.py tasks exp-id                  # View tasks
ont_experiments.py next exp-id --json            # Get next task

# Pipeline
ont_experiments.py pipeline run <name> exp-id    # Run pipeline
ont_experiments.py pipeline resume exp-id        # Resume failed

# Math Registry
ont_experiments.py math list                     # List equations
ont_experiments.py stages                        # Pipeline stages
ont_experiments.py validate                      # Schema validation
```

### Test Suite

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_core.py::test_edit_distance_basic -v

# Results: 30/30 passing
```

## Current Status

- **Tests:** 30/30 passing
- **GitHub:** https://github.com/Single-Molecule-Sequencing/ont-ecosystem
- **Modified files:** 72+ files ready to commit
- **Experiments registered:** 145 (461.4M reads, 828.2 GB bases)
- **Equations:** 4,087 lines synced from textbook
- **Variables:** 3,532 lines synced from textbook
