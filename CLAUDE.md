# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ONT Ecosystem is a comprehensive toolkit for Oxford Nanopore sequencing experiment management with provenance tracking, event-sourced registry, and integrated analysis workflows. It's designed for bioinformatics researchers working with nanopore sequencing data.

## Common Commands

```bash
# Install dependencies
make install          # Core dependencies only
make install-dev      # Full dev environment with pytest, pysam, edlib, etc.

# Run tests
pytest tests/ -v                    # All tests
pytest tests/test_core.py -v        # Core tests only
pytest tests/test_core.py::test_edit_distance_basic -v  # Single test

# Lint/validate
make lint             # Check Python syntax for all bin/*.py
make validate         # Validate skill frontmatter (YAML in SKILL.md files)

# Other
make clean            # Remove __pycache__, *.pyc, build artifacts
make package          # Create .skill zip packages
make dashboard        # Start web dashboard on port 8080
```

## Architecture

### Pattern B Orchestration

All analysis runs through `ont_experiments.py` for automatic provenance tracking. The core pattern is:

```bash
# Preferred (full provenance)
ont_experiments.py run <skill_name> <experiment_id> [options]

# Direct (no provenance) - avoid for production
end_reason.py /data/exp --json results.json
```

### Directory Structure

- **bin/**: Executable Python scripts - the primary entry points
  - `ont_experiments.py` - Core orchestration hub (Pattern B)
  - `ont_align.py` - Alignment + Levenshtein edit distance via edlib
  - `ont_pipeline.py` - Multi-step workflow orchestration
  - `end_reason.py` - Read end reason QC analysis
  - `dorado_basecall.py` - GPU basecalling workflows
  - `ont_monitor.py` - Real-time run monitoring

- **skills/**: Claude skill packages (each has SKILL.md with YAML frontmatter + scripts/)
  - Skills integrate with ont_experiments.py via the `ANALYSIS_SKILLS` dict in `ont_experiments.py:75`

- **dashboards/**: React JSX visualization components

- **examples/**: Pipeline and HPC config YAML files
  - `pipelines/`: Workflow definitions (pharmaco-clinical, qc-fast, research-full)
  - `configs/`: HPC configs (greatlakes, armis2, local)

### Event-Sourced Registry

Experiments are stored in `~/.ont-registry/` with full event history. Key files:
- `experiments.yaml` - Main registry
- Individual experiment directories with event logs

### Adding a New Skill

1. Create `skills/my-skill/SKILL.md` with YAML frontmatter (name, description required)
2. Add implementation in `skills/my-skill/scripts/`
3. Register in `ANALYSIS_SKILLS` dict in `bin/ont_experiments.py`
4. Add tests in `tests/`

## Dependencies

- **Required**: Python 3.9+, pyyaml
- **Analysis** (optional): pysam, edlib, numpy, pandas, matplotlib, pod5, h5py
- **External tools**: minimap2, samtools, dorado (system-level)

## Testing Notes

- Tests use `pytest` and are in `tests/`
- Some tests skip gracefully when optional deps (edlib, pysam) aren't installed
- CI runs against Python 3.9, 3.10, 3.11, 3.12

## Key Patterns

- Skill files use YAML frontmatter in SKILL.md (parsed via regex `^---\n(.*?)\n---`)
- HPC integration captures SLURM metadata automatically (job ID, nodes, GPUs)
- Event sourcing means all operations are logged and replayable

## Domain Memory System

Based on Anthropic's agent memory pattern, the repository includes a domain memory system for agent-friendly experiment management. This provides structured task tracking and progress logging that persists across agent sessions.

### Directory Structure

```
~/.ont-registry/
├── experiments.yaml              # Main registry
└── experiments/                  # Per-experiment domain memory
    └── exp-abc123/
        ├── tasks.yaml            # Machine-readable task backlog
        ├── PROGRESS.md           # Human-readable progress log
        └── CLAUDE.md             # Experiment-specific AI context (optional)
```

### Commands

```bash
# Initialize domain memory for an experiment
ont_experiments.py init-tasks exp-abc123 [--claude-md]

# View task backlog with status
ont_experiments.py tasks exp-abc123

# View progress log
ont_experiments.py progress exp-abc123

# Get next recommended task (agent-friendly)
ont_experiments.py next exp-abc123 [--json]
```

### Task States

| Status | Icon | Description |
|--------|------|-------------|
| `pending` | `○` | Not yet attempted |
| `in_progress` | `◐` | Currently running |
| `passing` | `✓` | Completed successfully |
| `failing` | `✗` | Failed, needs attention |
| `skipped` | `−` | Manually skipped |

### Bootup Ritual Pattern

The `bootup_check()` function implements the standardized bootup ritual for agents:

1. Load registry state
2. Load/initialize task state
3. Categorize tasks (pending, failing, passing)
4. Generate recommendations

```python
ctx = bootup_check("exp-abc123")
if ctx.failing_tasks:
    # Fix failing tasks first
elif ctx.pending_tasks:
    # Work on next pending task
```

### Agent Workflow

1. Call `ont_experiments.py next exp-id --json` to get machine-readable recommendation
2. Execute the recommended task via `ont_experiments.py run <task> exp-id`
3. Task status auto-updates based on exit code
4. Progress log auto-appends with execution details

## Consolidated Monorepo Architecture (v2.0)

This repository is now a **consolidated monorepo** containing all components:
- Analysis scripts and skills
- SMS Haplotype Framework Textbook (equations, variables, LaTeX sources)
- Reference documents (All_Math.pdf)
- Runtime registry

### Repository Structure

```
ont-ecosystem/                          # Single consolidated repository
├── bin/                                # Analysis scripts (16 Python scripts)
│   ├── ont_experiments.py              # Core orchestration hub
│   ├── ont_manuscript.py               # Figure/table generation
│   ├── ont_context.py                  # Unified experiment context
│   ├── ont_integrate.py                # Manuscript scaffolding
│   └── ...
├── skills/                             # Skill packages (8+ skills)
├── textbook/                           # SMS Haplotype Framework (AUTHORITATIVE)
│   ├── equations.yaml                  # 4087 lines - master equation database
│   ├── variables.yaml                  # 3532 lines - master variable database
│   ├── database_schema.yaml            # Schema for textbook database
│   ├── CLAUDE.md                       # Textbook AI guidance
│   ├── sms.sty                         # LaTeX style package
│   ├── references.bib                  # BibTeX references
│   ├── scripts/                        # Validation and compilation
│   │   ├── validate_database.py        # Database QC checks
│   │   ├── equation_database.py        # Python database API
│   │   └── compile.sh                  # LaTeX compilation
│   └── src/                            # LaTeX source files
│       ├── chapters/                   # 47 chapter .tex files
│       └── appendices/                 # 11 appendix .tex files
├── data/math/                          # Reference documents
│   └── All_Math.pdf                    # AUTHORITATIVE math reference (19 pages)
├── registry/                           # Runtime registry and schemas
│   ├── INDEX.yaml                      # Master index (v2.0.0 monorepo)
│   ├── experiments.yaml                # 145 registered experiments
│   └── schemas/                        # JSON Schema definitions
├── manuscripts/                        # Created manuscript repos (gitignored)
└── docs/                               # Documentation
```

### Authoritative Sources

| Component | Location | Lines/Size | Description |
|-----------|----------|------------|-------------|
| Equations | `textbook/equations.yaml` | 4087 | Master equation database |
| Variables | `textbook/variables.yaml` | 3532 | Master variable database |
| All_Math.pdf | `data/math/All_Math.pdf` | 19 pages | Takes precedence on conflicts |

### No External Dependencies

Previously required external repos are now consolidated:
- ~~D:\repos\SMS_textbook~~ → `textbook/`
- ~~C:\Users\farnu\Downloads\All_Math.pdf~~ → `data/math/All_Math.pdf`

### Core Frameworks

**Pipeline Factorization Theorem** (Chapter 4):
```
P(h,g,u,d,l,σ,r) = P(h)·P(g|h)·P(u|g)·P(d|u)·P(l|d)·P(σ|l)·P(r|σ)
```

Nine pipeline stages: h (Haplotype), g (Standard), u (Guide), d (Fragmentation), ℓ (Library), σ (Signal), r (Basecalling), C (Cas9 toggle), A (Adaptive toggle)

**SMA-SEER Learning System** (Chapters 11-13):
- **Measure**: SMA-seq generates reads from plasmid standards
- **Model**: SEER constructs confusion matrices and error models
- **Improve**: Basecaller fine-tuning using empirical models
- **Deploy**: Apply improved models to patient samples

**Purity Ceiling Theorem** (Chapter 5):
```
TPR ≤ π (True positive rate cannot exceed purity)
```

### Key Equations

| ID | Name | Formula | Stage |
|----|------|---------|-------|
| `eq_6_6` | Bayesian Posterior | P(h\|r) = P(r\|h)P(h) / ΣP(r\|h')P(h') | A |
| `eq_phred` | Phred Score | Q = -10 log₁₀(P_error) | r |
| `eq_sma` | Single Molecule Accuracy | SMA = Π(1 - p_i) | r |
| `eq_5_2` | Purity Ceiling | TPR ≤ π | g, A |

### Skill-to-Stage Mapping

| Skill | Pipeline Stage(s) | Key Equations |
|-------|-------------------|---------------|
| `end-reason` | σ | eq_signal_positive, eq_unblock_rate |
| `dorado-bench-v2` | r | eq_phred (1.1.1), eq_sma |
| `ont-align` | r | eq_levenshtein (1.1.2), eq_identity |
| `ont-monitor` | σ | eq_throughput, eq_pore_activity |
| `ont-pipeline` | r, A | eq_6_6 (Bayesian posterior) |

### Registry Index

All registry components are indexed in `registry/INDEX.yaml` (v2.0.0):

```yaml
# Key components
ont-ecosystem/
├── textbook/                     # AUTHORITATIVE (consolidated)
│   ├── equations.yaml            # 4087 lines
│   └── variables.yaml            # 3532 lines
├── data/math/
│   └── All_Math.pdf              # Reference (takes precedence on conflicts)
├── registry/
│   ├── INDEX.yaml                # Master index
│   ├── experiments.yaml          # 145 experiments
│   ├── pipeline/stages.yaml      # 9 pipeline stages
│   └── schemas/                  # JSON Schema validation
└── manuscripts/                  # Independent manuscript repos (via submodule)
```

### Database Validation

```bash
# Validate equations and variables databases
cd textbook && python scripts/validate_database.py
```

## Manuscript Generation System

The manuscript system provides publication-quality figure and table generation with versioned artifact storage.

### Key Scripts

- `ont_manuscript.py` - Main manuscript CLI (figure/table generation, export)
- `ont_context.py` - Unified experiment context across all system components
- `ont_textbook_export.py` - Export artifacts to SMS_textbook format
- `ont_config.py` - User configuration management

### Manuscript Commands

```bash
# List available pipelines, figures, tables
ont_manuscript.py list-pipelines
ont_manuscript.py list-figures
ont_manuscript.py list-tables

# Run pipeline (auto-generates figures/tables)
ont_manuscript.py pipeline qc-report exp-abc123
ont_manuscript.py pipeline full-analysis exp-abc123

# Generate specific figure
ont_manuscript.py figure fig_end_reason_kde exp-abc123 --format pdf
ont_manuscript.py figure fig_quality_dist exp-abc123 --format png

# Generate specific table
ont_manuscript.py table tbl_qc_summary exp-abc123 --format tex
ont_manuscript.py table tbl_basecalling exp-abc123 --format csv

# Export for manuscript
ont_manuscript.py export exp-abc123 ./my_paper --target latex
ont_manuscript.py export exp-abc123 ./web_report --target html

# Compare experiments
ont_manuscript.py compare exp-abc123 exp-def456 --json

# View experiment context
ont_context.py show exp-abc123 --json

# Export to SMS_textbook
ont_textbook_export.py exp-abc123 /mnt/d/repos/SMS_textbook
```

### Artifact Storage

Generated artifacts are stored with versioning:

```
~/.ont-manuscript/artifacts/
├── <experiment_id>/
│   ├── figures/
│   │   ├── fig_end_reason_kde/
│   │   │   ├── v1/
│   │   │   │   ├── fig_end_reason_kde.pdf
│   │   │   │   └── metadata.yaml
│   │   │   ├── v2/
│   │   │   └── latest -> v2
│   │   └── fig_quality_dist/
│   └── tables/
│       └── tbl_qc_summary/
```

### Available Pipelines

| Pipeline | Description | Auto-Figures | Auto-Tables |
|----------|-------------|--------------|-------------|
| qc-report | QC figures and summary | fig_end_reason_kde, fig_quality_dist | tbl_qc_summary |
| full-analysis | Complete analysis | All QC + coverage, alignment | All QC + basecalling, alignment |
| comparison | Multi-experiment | Overlay plots, box plots | Comparison table |
| summary-only | Tables only | None | tbl_experiment_summary |

### Configuration

User configuration is stored in `~/.ont-ecosystem/config.yaml`:

```bash
# Initialize config (auto-detects HPC cluster)
ont_config.py init

# View current config
ont_config.py show

# Set configuration values
ont_config.py set github.enabled true
ont_config.py set paths.textbook_dir /mnt/d/repos/SMS_textbook
```

## Installation (Private Repository)

For private repository access, install via SSH:

```bash
# Clone via SSH
git clone git@github.com:Single-Molecule-Sequencing/ont-ecosystem.git
cd ont-ecosystem
./install.sh

# Activate
source ~/.ont-ecosystem/env.sh

# Verify
ont_experiments.py --help
ont_manuscript.py list-pipelines
```

See `docs/INSTALLATION.md` for detailed instructions.

## Manuscript Repository Integration

Create and manage independent manuscript repositories that connect to ont-ecosystem via git submodule.

### Creating a New Manuscript

```bash
# Create a new paper manuscript
ont_integrate.py create-manuscript my-cyp2d6-paper --template paper

# Create a textbook chapter
ont_integrate.py create-manuscript chapter21-end-reason --template chapter

# Create supplementary materials
ont_integrate.py create-manuscript cyp2d6-supplement --template supplement

# Outputs to manuscripts/<name>/ (gitignored from ont-ecosystem)
```

### Manuscript Templates

| Template | Description | Includes |
|----------|-------------|----------|
| `paper` | Research paper | Abstract, methods, results, figures, tables |
| `chapter` | Textbook chapter | Equations, proofs, worked examples, exercises |
| `supplement` | Supplementary | Extended methods, additional figures, data tables |

### Connecting Manuscripts

```bash
# Connect manuscript to ont-ecosystem (adds submodule)
ont_integrate.py connect /path/to/my-manuscript

# Sync figures/tables from experiments to manuscript
ont_integrate.py sync /path/to/my-manuscript --experiments exp-abc123 exp-def456

# Check connection status
ont_integrate.py status
```

### Auto-Sync Features

When connected, manuscripts automatically:
- Inherit `equations.yaml` via submodule
- Sync figures from ont-ecosystem artifacts
- Share LaTeX style (`sms.sty`)
- Track provenance of generated figures/tables

### Manuscript Directory Structure

```
my-manuscript/                    # Independent git repo
├── ont-ecosystem/                # Submodule link
├── figures/                      # Synced from ont-ecosystem
│   └── fig_end_reason_kde.pdf
├── tables/                       # Synced from ont-ecosystem
│   └── tbl_qc_summary.tex
├── src/
│   └── main.tex                  # Uses \input{ont-ecosystem/textbook/sms.sty}
└── .manuscript.yaml              # Connection config
```
