# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ONT Ecosystem (v3.0) is a consolidated monorepo for Oxford Nanopore sequencing experiment management with provenance tracking, event-sourced registry, integrated analysis workflows, and publication-quality figure generation. Designed for bioinformatics researchers working with nanopore sequencing data.

## Common Commands

```bash
# Run tests
pytest tests/ -v                                    # All 44 tests
pytest tests/test_core.py -v                        # Core tests only
pytest tests/test_core.py::test_edit_distance_basic -v  # Single test
pytest tests/test_integration.py -v                 # Integration tests

# Lint/validate
make lint             # Check Python syntax for all bin/*.py
make validate         # Validate skill frontmatter (YAML in SKILL.md files)

# Install
make install          # Core dependencies only
make install-dev      # Full dev environment

# Manuscript generation
ont_manuscript.py list-figures                      # List 10 figure generators
ont_manuscript.py list-tables                       # List 5 table generators
ont_manuscript.py list-pipelines                    # List 4 pipelines

# Equation system
ont_context.py equations                            # List all 101 equations
ont_context.py equations --computable               # List 14 computable equations
```

## Architecture

### Single Source of Truth (SSOT)

Skills in `skills/*/scripts/` are the authoritative source. Scripts in `bin/` are either:
- **Orchestrators**: `ont_experiments.py`, `ont_manuscript.py`, `ont_context.py` (original code)
- **Wrappers**: Import from skills (e.g., `end_reason.py` → `skills/end-reason/scripts/end_reason.py`)

### Pattern B Orchestration

All analysis runs through `ont_experiments.py` for automatic provenance tracking:

```bash
# Preferred (full provenance)
ont_experiments.py run <skill_name> <experiment_id> [options]

# Direct (no provenance)
end_reason.py /data/exp --json results.json
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `ont_experiments.py` | bin/ | Core orchestration hub, experiment registry |
| `ont_manuscript.py` | bin/ | Figure/table generation, versioned artifacts |
| `ont_context.py` | bin/ | Unified experiment context, equation execution |
| `experiment_db.py` | bin/ | SQLite database operations |
| Skills | skills/*/scripts/ | Authoritative analysis implementations |
| Equations | textbook/equations.yaml | 101 equations (14 computable with Python) |
| Variables | textbook/variables.yaml | 3532 variable definitions |

### Figure/Table Generation

11 generators in `skills/manuscript/generators/`:

```bash
# Figure generators (10)
fig_end_reason_kde      # KDE plot by end reason
fig_end_reason_pie      # End reason pie/donut chart
fig_quality_dist        # Q-score distribution
fig_read_length         # Read length distribution
fig_yield_timeline      # Cumulative yield over time
fig_n50_barplot         # N50 comparison bar chart
fig_metrics_heatmap     # QC metrics heatmap
fig_coverage            # Coverage depth plot
fig_alignment_stats     # Alignment statistics
fig_comparison          # Multi-experiment comparison

# Table generators (5)
tbl_qc_summary, tbl_basecalling, tbl_alignment, tbl_comparison, tbl_experiment_summary
```

### Equation Execution System

Equations in `textbook/equations.yaml` with Python implementations can be computed:

```python
# In ont_context.py
from ont_context import load_equations, compute_equation, Equation

equations = load_equations()
# QC.1-12, STAT.1-2 have Python implementations
```

Safe eval with restricted builtins (abs, min, max, sum, sqrt, log, log10).

## Directory Structure

```
ont-ecosystem/
├── bin/                          # Scripts (orchestrators + wrappers)
├── skills/                       # AUTHORITATIVE analysis code
│   ├── end-reason/scripts/       # End reason QC
│   ├── ont-align/scripts/        # Alignment
│   ├── dorado-bench-v2/scripts/  # Basecalling
│   ├── ont-monitor/scripts/      # Monitoring
│   ├── ont-pipeline/scripts/     # Workflow orchestration
│   ├── experiment-db/scripts/    # Database
│   └── manuscript/generators/    # 11 figure/table generators
├── textbook/                     # SMS Haplotype Framework
│   ├── equations.yaml            # 4087 lines, 101 equations
│   ├── variables.yaml            # 3532 lines
│   └── src/chapters/             # 24 LaTeX chapter files
├── data/
│   ├── experiment_registry.json  # 145 experiments
│   └── math/All_Math.pdf         # Reference (takes precedence on conflicts)
├── registry/                     # Schemas and index
├── tests/                        # 44 pytest tests
└── examples/                     # Pipelines + HPC configs
```

## Adding a New Skill

1. Create `skills/my-skill/SKILL.md` with YAML frontmatter:
   ```yaml
   ---
   name: my-skill
   description: Brief description
   ---
   ```
2. Add implementation in `skills/my-skill/scripts/`
3. Register in `ANALYSIS_SKILLS` dict in `bin/ont_experiments.py:75`
4. Add wrapper in `bin/` if needed (import from skills/)
5. Add tests in `tests/`

## Adding a New Generator

1. Create `skills/manuscript/generators/gen_my_figure.py`
2. Implement `generate_*()` function following existing patterns
3. Register in `FIGURE_GENERATORS` or `TABLE_GENERATORS` in `bin/ont_manuscript.py`
4. Update `skills/manuscript/SKILL.md` documentation
5. Add import test to `.github/workflows/ci.yml`

## Adding Computable Equations

Add Python implementation to equation in `textbook/equations.yaml`:

```yaml
'QC.X':
  id: 'QC.X'
  title: My equation
  latex: formula
  python: "variable_a * variable_b"  # Uses context variables
  pipeline_stage: basecalling
```

Variables available: `total_reads`, `total_bases`, `mean_qscore`, `median_qscore`, `n50`, `mean_length`, `pass_reads`, `fail_reads`, `signal_positive_pct`, `unblock_pct`

## Key Patterns

- **Skill frontmatter**: YAML in SKILL.md parsed via regex `^---\n(.*?)\n---`
- **Event sourcing**: All operations logged in `~/.ont-registry/`
- **HPC integration**: Captures SLURM metadata (job ID, nodes, GPUs)
- **Artifact versioning**: Figures/tables stored with version history in `~/.ont-manuscript/artifacts/`

## Dependencies

- **Required**: Python 3.9+, pyyaml
- **Analysis**: pysam, edlib, numpy, pandas, matplotlib, pod5, h5py
- **External**: minimap2, samtools, dorado (system-level)

## Testing

- CI runs Python 3.9, 3.10, 3.11, 3.12
- Tests skip gracefully when optional deps not installed
- Integration tests use real experiment registry data

## Core Frameworks (SMS Haplotype Textbook)

**Pipeline Factorization Theorem** (Chapter 4):
```
P(h,g,u,d,l,σ,r) = P(h)·P(g|h)·P(u|g)·P(d|u)·P(l|d)·P(σ|l)·P(r|σ)
```

Nine pipeline stages: h (Haplotype), g (Standard), u (Guide), d (Fragmentation), ℓ (Library), σ (Signal), r (Basecalling), C (Cas9 toggle), A (Adaptive toggle)

**Key Equations**:
- `eq_6_6`: Bayesian Posterior - P(h|r) = P(r|h)P(h) / ΣP(r|h')P(h')
- `eq_phred`: Phred Score - Q = -10 log₁₀(P_error)
- `QC.3`: Error probability - 10^(-Q/10)

## Private Repository Installation

```bash
git clone git@github.com:Single-Molecule-Sequencing/ont-ecosystem.git
cd ont-ecosystem
./install.sh
source ~/.ont-ecosystem/env.sh
```

GITHUB_SYNC_ENABLED is False by default for private repos.
