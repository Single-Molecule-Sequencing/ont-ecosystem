# Changelog

All notable changes to the ONT Ecosystem project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2024-12-29

### Added

#### Manuscript Generation System
- `ont_manuscript.py` - Full CLI for figure/table generation with versioned artifact storage
- 10 figure generators in `skills/manuscript/generators/`:
  - `gen_end_reason_kde.py` - KDE plot by end reason
  - `gen_end_reason_pie.py` - End reason pie/donut chart
  - `gen_quality_distribution.py` - Q-score distribution histogram
  - `gen_read_length_distribution.py` - Read length distribution
  - `gen_yield_timeline.py` - Cumulative yield over time
  - `gen_n50_barplot.py` - N50 comparison bar chart
  - `gen_metrics_heatmap.py` - QC metrics heatmap across experiments
  - `gen_comparison_plot.py` - Multi-experiment 4-panel comparison
  - Coverage and alignment stats generators
- 5 table generators: QC summary, basecalling, alignment, comparison, experiment summary
- 4 manuscript pipelines: qc-report, full-analysis, comparison, summary-only
- Versioned artifact storage in `~/.ont-manuscript/artifacts/`

#### Equation Execution System
- `ont_context.py` - Unified experiment context with equation computation
- 14 computable equations with Python implementations (QC.1-12, STAT.1-2)
- Safe eval with restricted builtins (abs, min, max, sum, sqrt, log, log10)
- CLI commands: `equations`, `compute`, `show`
- Variable binding from experiment context

#### Integration Tests
- `tests/test_integration.py` - 10 tests using real experiment registry data
- Equation execution and variable binding tests
- Generator registry validation
- End-to-end computation verification

#### Enhanced CI/CD
- `test-equations` job validates equation loading and computable equations
- `test-generators` job tests all 11 generators
- Python 3.9, 3.10, 3.11, 3.12 matrix testing

### Changed

#### Single Source of Truth (SSOT) Architecture
- Skills in `skills/*/scripts/` are now the authoritative source
- Scripts in `bin/` are either orchestrators or wrappers importing from skills
- Wrapper pattern: `bin/end_reason.py` imports from `skills/end-reason/scripts/end_reason.py`

#### Updated Documentation
- Completely rewritten `CLAUDE.md` (207 lines, focused and concise)
- Updated `skills/manuscript/SKILL.md` with all generators
- Added `AUTHORITATIVE_SOURCES.md` documenting SSOT locations

### Fixed
- Chapter sorting TypeError in equation listing (string vs int keys)
- Git LFS hook issues blocking push operations
- None value handling in experiment registry statistics

## [2.3.0] - 2024-12-28

### Added
- Experiment registry with 145 experiments
- `experiment_db.py` for SQLite database operations
- `data/experiment_registry.json` with full experiment metadata

## [2.2.0] - 2024-12-27

### Added
- Enhanced QC visualization with `ont_endreason_qc.py`
- KDE plots with zoom panels
- Multi-zoom panel layouts

## [2.1.0] - 2024-12-26

### Added
- Domain memory system for agent-friendly experiment management
- Task tracking with bootup ritual pattern
- Progress logging across agent sessions

## [2.0.0] - 2024-12-25

### Added
- Consolidated monorepo architecture
- SMS Haplotype Framework textbook integration
- `textbook/equations.yaml` (4087 lines, 101 equations)
- `textbook/variables.yaml` (3532 lines)
- Registry index (`registry/INDEX.yaml`)

### Changed
- Consolidated external repos into monorepo
- All textbook content now in `textbook/` directory

## [1.0.0] - 2024-12-20

### Added
- Initial release
- Pattern B orchestration via `ont_experiments.py`
- Event-sourced registry in `~/.ont-registry/`
- Skills: end-reason, dorado-bench-v2, ont-align, ont-monitor, ont-pipeline
- HPC/SLURM integration with automatic metadata capture
- Edit distance computation via edlib

---

## Summary of Versions

| Version | Date | Key Features |
|---------|------|--------------|
| 3.0.0 | 2024-12-29 | Manuscript system, equation execution, SSOT architecture |
| 2.3.0 | 2024-12-28 | Experiment registry (145 experiments) |
| 2.2.0 | 2024-12-27 | Enhanced QC visualization |
| 2.1.0 | 2024-12-26 | Domain memory system |
| 2.0.0 | 2024-12-25 | Consolidated monorepo |
| 1.0.0 | 2024-12-20 | Initial release |
