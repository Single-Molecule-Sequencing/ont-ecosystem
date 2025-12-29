# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ONT Ecosystem (v3.0) is a consolidated monorepo for Oxford Nanopore sequencing experiment management with provenance tracking, event-sourced registry, integrated analysis workflows, and publication-quality figure generation. Designed for bioinformatics researchers working with nanopore sequencing data.

## Common Commands

```bash
# Run tests
pytest tests/ -v                                    # All 180 tests
pytest tests/test_core.py -v                        # Core tests only
pytest tests/test_core.py::test_edit_distance_basic -v  # Single test
pytest tests/test_lib.py -v                         # Library module tests

# Lint/validate
make lint             # Check Python syntax for all bin/*.py
make validate         # Validate skill frontmatter (YAML in SKILL.md files)

# Install
make install          # Core dependencies only
make install-dev      # Full dev environment

# Project utilities
ont_doctor.py                    # Diagnose issues, suggest fixes
ont_doctor.py --fix              # Auto-fix common issues
ont_report.py --format markdown  # Generate project report
ont_version.py --skills          # Show all skill versions
ont_init.py project my-proj      # Create new project from template
ont_help.py                      # List all commands with examples
ont_changelog.py                 # Generate changelog from git history
ont_changelog.py stats           # Show commit statistics
```

## Architecture

### Single Source of Truth (SSOT)

Skills in `skills/*/scripts/` are the authoritative source. Scripts in `bin/` are either:
- **Orchestrators**: `ont_experiments.py`, `ont_manuscript.py`, `ont_context.py` (original code)
- **Wrappers**: Import from skills (e.g., `end_reason.py` → `skills/end-reason/scripts/end_reason.py`)
- **Utilities**: Standalone tools (`ont_doctor.py`, `ont_init.py`, `ont_version.py`, etc.)

### Pattern B Orchestration

All analysis runs through `ont_experiments.py` for automatic provenance tracking:

```bash
# Preferred (full provenance)
ont_experiments.py run <skill_name> <experiment_id> [options]

# Direct (no provenance)
end_reason.py /data/exp --json results.json
```

### Library Modules (`lib/`)

Shared utilities with lazy imports to minimize startup overhead:

| Module | Purpose |
|--------|---------|
| `lib.cli` | Terminal colors, progress bars, table formatting |
| `lib.io` | JSON/YAML I/O, atomic writes, checksums, file discovery |
| `lib.cache` | Memory and file-based caching with TTL |
| `lib.validation` | Schema validation, path validation, chainable validators |
| `lib.errors` | Standardized error classes with severity/category |
| `lib.timing` | Timer context manager, timing decorators |
| `lib.logging_config` | Logging setup and configuration |
| `lib.config` | Layered configuration (user/project), env overrides, HPC detection |
| `lib.parallel` | Thread/process pools, parallel_map, TaskQueue, retry wrappers |

Usage: `from lib import load_json, ProgressBar, ValidationError, Config, parallel_map`

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `ont_experiments.py` | bin/ | Core orchestration hub, experiment registry |
| `ont_manuscript.py` | bin/ | Figure/table generation, versioned artifacts |
| `ont_context.py` | bin/ | Unified experiment context, equation execution |
| `experiment_db.py` | bin/ | SQLite database operations |
| `ont_init.py` | bin/ | Project/experiment initialization wizard |
| `ont_doctor.py` | bin/ | Diagnostic tool with fix suggestions |
| `ont_version.py` | bin/ | Version management and bumping |
| `ont_changelog.py` | bin/ | Changelog generation from git history |
| Skills | skills/*/scripts/ | Authoritative analysis implementations |
| Equations | textbook/equations.yaml | 101 equations (14 computable with Python) |

### Figure/Table Generation

11 generators in `skills/manuscript/generators/`:
- **Figures (10)**: fig_end_reason_kde, fig_end_reason_pie, fig_quality_dist, fig_read_length, fig_yield_timeline, fig_n50_barplot, fig_metrics_heatmap, fig_coverage, fig_alignment_stats, fig_comparison
- **Tables (5)**: tbl_qc_summary, tbl_basecalling, tbl_alignment, tbl_comparison, tbl_experiment_summary

## Adding a New CLI Tool

1. Create script in `bin/ont_mytool.py` following the argparse pattern
2. Add tests to `tests/test_utilities.py`
3. Add to `pyproject.toml` scripts section: `ont-mytool = "bin.ont_mytool:main"`
4. Add shell completion to `completions/ont-completion.bash`
5. Register in `bin/ont_help.py` COMMANDS dict

## Adding a New Skill

1. Create `skills/my-skill/SKILL.md` with YAML frontmatter
2. Add implementation in `skills/my-skill/scripts/`
3. Register in `ANALYSIS_SKILLS` dict in `bin/ont_experiments.py:75`
4. Add wrapper in `bin/` if needed (import from skills/)
5. Add tests in `tests/`

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
- **Lazy imports**: Library modules use lazy imports in `lib/__init__.py`

## Dependencies

- **Required**: Python 3.9+, pyyaml
- **Analysis**: pysam, edlib, numpy, pandas, matplotlib, pod5, h5py
- **External**: minimap2, samtools, dorado (system-level)

## Testing

- CI runs Python 3.9, 3.10, 3.11, 3.12
- Tests skip gracefully when optional deps not installed
- Use `tmp_path` fixture for file-based tests
- Import scripts via `importlib.util.spec_from_file_location` pattern

## Core Frameworks (SMS Haplotype Textbook)

**Pipeline Factorization Theorem** (Chapter 4):
```
P(h,g,u,d,l,σ,r) = P(h)·P(g|h)·P(u|g)·P(d|u)·P(l|d)·P(σ|l)·P(r|σ)
```

Nine pipeline stages: h (Haplotype), g (Standard), u (Guide), d (Fragmentation), ℓ (Library), σ (Signal), r (Basecalling), C (Cas9 toggle), A (Adaptive toggle)

## Private Repository Installation

```bash
git clone git@github.com:Single-Molecule-Sequencing/ont-ecosystem.git
cd ont-ecosystem
./install.sh
source ~/.ont-ecosystem/env.sh
```

GITHUB_SYNC_ENABLED is False by default for private repos.
