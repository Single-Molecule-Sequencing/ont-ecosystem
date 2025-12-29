# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ONT Ecosystem (v3.0) is a consolidated monorepo for Oxford Nanopore sequencing experiment management with provenance tracking, event-sourced registry, integrated analysis workflows, and publication-quality figure generation.

## Skills (Slash Commands)

Skills are automatically installed to `~/.claude/commands/`. List available skills: `make skills-list`

Key skills: `/comprehensive-analysis`, `/end-reason`, `/ont-experiments-v2`, `/ont-align`, `/ont-pipeline`, `/ont-monitor`, `/dorado-bench-v2`, `/experiment-db`, `/manuscript`, `/skill-maker`, `/ont-public-data`, `/registry-browser`, `/greatlakes-sync`

```bash
# Quick analysis with sampling (30s)
/comprehensive-analysis /path/to/experiment -o output/

# End reason QC
/end-reason /path/to/pod5 --json results.json --plot qc.png

# Run with provenance tracking (Pattern B - preferred)
ont_experiments.py run end_reasons exp-001 --json qc.json

# Great Lakes discovery and sync
greatlakes_sync.py discover --submit     # Submit SLURM discovery job
greatlakes_sync.py review --latest       # Review discovered experiments
greatlakes_sync.py apply --latest --commit --push  # Apply and sync to GitHub
```

See `.claude/skills.md` for complete documentation. Skills auto-sync from `installable-skills/`.

## Common Commands

```bash
# Testing
pytest tests/ -v                                    # All tests
pytest tests/test_core.py -v                        # Core tests only
pytest tests/test_core.py::test_edit_distance_basic -v  # Single test by name
pytest -k "qscore"                                  # Tests matching pattern
pytest tests/test_lib.py -v                         # Library module tests

# Lint/validate
make lint             # Check Python syntax for all bin/*.py
make validate         # Validate skill frontmatter (YAML in SKILL.md files)

# Install
make install          # Core dependencies only
make install-dev      # Full dev environment

# Diagnostics
ont_doctor.py                    # Diagnose issues, suggest fixes
ont_doctor.py --fix              # Auto-fix common issues
ont_help.py                      # List all commands with examples
make help                        # Show all Makefile targets

# Experiment management
ont_experiments.py init --git              # Initialize registry with git tracking
ont_experiments.py discover /path --register  # Find and register experiments
ont_experiments.py run end_reasons exp-001 --json qc.json  # Run with provenance
ont_experiments.py history exp-001         # View experiment event history
```

## Architecture

### Single Source of Truth (SSOT)

**CRITICAL: Always edit `skills/*/scripts/`, never edit `bin/` wrappers directly.**

| Type | Location | Edit? |
|------|----------|-------|
| Analysis code | `skills/*/scripts/*.py` | ✓ EDIT HERE |
| Orchestrators | `bin/ont_experiments.py`, `bin/ont_manuscript.py`, `bin/ont_context.py` | ✓ EDIT HERE |
| Wrappers | `bin/end_reason.py`, `bin/ont_align.py`, etc. | ✗ Auto-imports from skills |
| Utilities | `bin/ont_doctor.py`, `bin/ont_init.py`, etc. | ✓ EDIT HERE |

See `AUTHORITATIVE_SOURCES.md` for complete source location mapping.

### Pattern B Orchestration

All analysis runs through `ont_experiments.py` for automatic provenance tracking:

```bash
# Preferred (full provenance)
ont_experiments.py run <skill_name> <experiment_id> [options]

# Direct (no provenance)
end_reason.py /data/exp --json results.json
```

### Library Modules (`lib/`)

Shared utilities with lazy imports. Usage: `from lib import load_json, ProgressBar, Config, parallel_map, mean_qscore`

Key modules: `cli` (terminal UI), `io` (JSON/YAML), `cache`, `validation`, `errors`, `timing`, `config`, `parallel`, `qscore`

### Figure/Table Generation

15 generators in `skills/manuscript/generators/`. List: `make list-figures` or `make list-tables`

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
- **Wrapper pattern**: `bin/` wrappers import from `skills/*/scripts/` to maintain SSOT

## Fundamental Rules

### Q-Score Averaging (CRITICAL)

**Q-scores are logarithmic (Phred scale) and MUST NOT be averaged directly.**

The correct procedure for calculating mean Q-score:
1. Convert each Q-score to error probability: `P = 10^(-Q/10)`
2. Average the probabilities: `P_avg = mean(P_i)`
3. Convert back to Q-score: `Q_avg = -10 * log10(P_avg)`

**Why this matters:** Direct averaging of Q-scores underestimates error rates. For example:
- Q10 (10% error) + Q30 (0.1% error) averaged directly = Q20
- Correct probability-space average = Q10.4 (weighted toward higher error)

**Use the canonical implementation:**
```python
from lib import mean_qscore

# Correct way to average Q-scores
avg_q = mean_qscore(qscores)  # Uses probability space internally

# Also available:
from lib import weighted_mean_qscore, qscore_to_probability, probability_to_qscore
```

**This rule applies to all current and future code in this project.**

## Dependencies

- **Required**: Python 3.9+, pyyaml
- **Analysis**: pysam, edlib, numpy, pandas, matplotlib, pod5, h5py
- **External**: minimap2, samtools, dorado (system-level)

## Testing

- CI runs Python 3.9, 3.10, 3.11, 3.12, 3.13
- Tests skip gracefully when optional deps (pysam, edlib, etc.) not installed
- Use `tmp_path` fixture for file-based tests
- Import scripts via `importlib.util.spec_from_file_location` pattern

Test files: `test_core.py` (registry, provenance), `test_lib.py` (library modules), `test_utilities.py` (CLI tools), `test_generators.py` (figures/tables), `test_integration.py` (end-to-end), `test_endreason_qc.py` (QC)

## Core Frameworks (SMS Haplotype Textbook)

**Pipeline Factorization Theorem** (Chapter 4):
```
P(h,g,u,d,l,σ,r) = P(h)·P(g|h)·P(u|g)·P(d|u)·P(l|d)·P(σ|l)·P(r|σ)
```

Nine pipeline stages: h (Haplotype), g (Standard), u (Guide), d (Fragmentation), ℓ (Library), σ (Signal), r (Basecalling), C (Cas9 toggle), A (Adaptive toggle)

## Skill Installation

Skills auto-install when entering the project. Manual install:

```bash
cd installable-skills && ./install-all.sh
```

## Private Repository Installation

```bash
git clone git@github.com:Single-Molecule-Sequencing/ont-ecosystem.git
cd ont-ecosystem
./install.sh
source ~/.ont-ecosystem/env.sh
```

GITHUB_SYNC_ENABLED is False by default for private repos.
