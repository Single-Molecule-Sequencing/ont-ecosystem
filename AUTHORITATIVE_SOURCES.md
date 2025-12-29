# Authoritative Sources

This document defines the Single Source of Truth (SSOT) for all components in the ONT Ecosystem.

**Rule:** Always edit the authoritative source. Derived files are regenerated, not edited directly.

---

## Quick Reference

| Component | Authoritative Location | Type |
|-----------|----------------------|------|
| Equations | `textbook/equations.yaml` | YAML database |
| Variables | `textbook/variables.yaml` | YAML database |
| Chapters | `textbook/src/chapters/*.tex` | LaTeX source |
| Analysis scripts | `skills/*/scripts/*.py` | Python source |
| Orchestration | `bin/ont_experiments.py` | Python source |
| Database funcs | `bin/experiment_db.py` | Python source |
| Experiment registry | `data/experiment_registry.json` | JSON database |

---

## Detailed Source Locations

### Mathematics & Equations

**Authoritative:** `textbook/equations.yaml` (4,087 equations)

```
textbook/
├── equations.yaml      # ← EDIT HERE (authoritative)
└── variables.yaml      # ← EDIT HERE (authoritative)
```

**Do NOT edit:**
- `registry/textbook/*.yaml` - Lightweight schema copies only

### Textbook Content

**Authoritative:** `textbook/src/chapters/`

```
textbook/src/chapters/
├── chapter1_populated.tex   # ← EDIT HERE
├── chapter2_populated.tex
├── ...
└── chapter24_populated.tex
```

**Derived (auto-generated):**
- `textbook/extracted/*/` - Content extracted from chapters

### Analysis Skills

**Authoritative:** `skills/*/scripts/`

| Skill | Authoritative Script |
|-------|---------------------|
| end-reason | `skills/end-reason/scripts/end_reason.py` |
| ont-align | `skills/ont-align/scripts/ont_align.py` |
| ont-monitor | `skills/ont-monitor/scripts/ont_monitor.py` |
| ont-pipeline | `skills/ont-pipeline/scripts/ont_pipeline.py` |
| dorado-bench | `skills/dorado-bench-v2/scripts/dorado_basecall.py` |
| experiment-db | `skills/experiment-db/scripts/experiment_db.py` |

**Wrappers (do NOT edit):**
- `bin/end_reason.py` → imports from `skills/end-reason/scripts/`
- `bin/ont_align.py` → imports from `skills/ont-align/scripts/`
- `bin/ont_monitor.py` → imports from `skills/ont-monitor/scripts/`
- `bin/ont_pipeline.py` → imports from `skills/ont-pipeline/scripts/`
- `bin/dorado_basecall.py` → imports from `skills/dorado-bench-v2/scripts/`
- `bin/calculate_resources.py` → imports from `skills/dorado-bench-v2/scripts/`
- `bin/make_sbatch_from_cmdtxt.py` → imports from `skills/dorado-bench-v2/scripts/`

### Orchestration & Infrastructure

**Authoritative:** `bin/` (unique scripts only)

| Script | Purpose |
|--------|---------|
| `bin/ont_experiments.py` | Core experiment orchestrator |
| `bin/experiment_db.py` | Database operations |
| `bin/ont_registry.py` | Permanent registry management |
| `bin/ont_dashboard.py` | Web interface |
| `bin/ont_config.py` | Configuration management |
| `bin/ont_context.py` | Experiment context |
| `bin/ont_integrate.py` | Git integration |
| `bin/ont_manuscript.py` | Manuscript pipelines |
| `bin/ont_endreason_qc.py` | Enhanced QC visualization |
| `bin/ont_textbook_export.py` | Textbook export |

### Experiment Data

**Authoritative:** `data/experiment_registry.json`

Contains 145 experiments with:
- Unique IDs
- Public dataset source links
- Sample metadata
- Analysis status

---

## Directory Structure

```
ont-ecosystem/
├── bin/                    # Orchestration (authoritative) + wrappers
│   ├── ont_experiments.py  # ← EDIT (authoritative)
│   ├── experiment_db.py    # ← EDIT (authoritative)
│   ├── end_reason.py       # wrapper → skills/
│   └── ...
├── skills/                 # Analysis code (authoritative)
│   ├── end-reason/
│   │   └── scripts/
│   │       └── end_reason.py  # ← EDIT HERE
│   ├── ont-align/
│   │   └── scripts/
│   │       └── ont_align.py   # ← EDIT HERE
│   └── ...
├── textbook/               # Content & math (authoritative)
│   ├── equations.yaml      # ← EDIT HERE
│   ├── variables.yaml      # ← EDIT HERE
│   ├── src/chapters/       # ← EDIT HERE
│   └── extracted/          # derived (auto-generated)
├── data/                   # Experiment data
│   └── experiment_registry.json  # ← EDIT HERE
└── registry/               # Lightweight schemas only
    └── textbook/           # do not edit (subset copies)
```

---

## Editing Workflow

### To update an equation:
```bash
# Edit the authoritative source
vim textbook/equations.yaml

# Test
pytest tests/ -k "equation"
```

### To update an analysis script:
```bash
# Edit the skill (authoritative source)
vim skills/end-reason/scripts/end_reason.py

# Test
pytest tests/

# The bin/ wrapper automatically uses the updated version
```

### To add a new experiment:
```bash
# Edit the registry
vim data/experiment_registry.json

# Or use the CLI
python bin/ont_experiments.py add <path>
```

---

## Migration Notes

As of v3.0, the following consolidations were made:

| Old Location | New Authoritative Location |
|--------------|---------------------------|
| `registry/textbook/equations_full.yaml` | `textbook/equations.yaml` |
| `registry/textbook/variables_full.yaml` | `textbook/variables.yaml` |
| `bin/end_reason.py` (full) | `skills/end-reason/scripts/end_reason.py` |
| `bin/ont_align.py` (full) | `skills/ont-align/scripts/ont_align.py` |

Wrapper scripts in `bin/` preserve backward compatibility.
