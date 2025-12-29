# Cleanup Manifest

This document lists all redundant files identified for removal.

**Total Files to Remove:** 113 files
**Estimated Space Savings:** ~1.2MB

---

## Summary

| Category | Count | Size Est. |
|----------|-------|-----------|
| Chapter backups | 12 | ~155KB |
| Chapter REORGANIZED | 12 | ~600KB |
| Extracted backups | 39 | ~40KB |
| Extracted REORGANIZED | 43 | ~50KB |
| Registry duplicates | 6 | ~280KB |
| Bin duplicates | 7 | ~80KB |
| **TOTAL** | **119** | **~1.2MB** |

---

## Phase 1: Textbook Cleanup (106 files)

### Chapter Backups (12 files) - REMOVE

```
textbook/src/chapters/chapter4_populated_backup_20251118_101124.tex
textbook/src/chapters/chapter5_populated_backup_20251118_101124.tex
textbook/src/chapters/chapter6_populated_backup_20251118_101124.tex
textbook/src/chapters/chapter7_populated_backup_20251118_101124.tex
textbook/src/chapters/chapter8_populated_backup_20251118_101124.tex
textbook/src/chapters/chapter9_populated_backup_20251118_101124.tex
textbook/src/chapters/chapter10_populated_backup_20251118_101124.tex
textbook/src/chapters/chapter11_populated_backup_20251118_101124.tex
textbook/src/chapters/chapter12_populated_backup_20251118_101124.tex
textbook/src/chapters/chapter13_populated_backup_20251118_101124.tex
textbook/src/chapters/chapter14_populated_backup_20251118_101124.tex
textbook/src/chapters/chapter18_populated_backup_20251118_101124.tex
```

### Chapter REORGANIZED (12 files) - REMOVE

```
textbook/src/chapters/chapter4_populated_REORGANIZED.tex
textbook/src/chapters/chapter5_populated_REORGANIZED.tex
textbook/src/chapters/chapter6_populated_REORGANIZED.tex
textbook/src/chapters/chapter7_populated_REORGANIZED.tex
textbook/src/chapters/chapter8_populated_REORGANIZED.tex
textbook/src/chapters/chapter9_populated_REORGANIZED.tex
textbook/src/chapters/chapter10_populated_REORGANIZED.tex
textbook/src/chapters/chapter11_populated_REORGANIZED.tex
textbook/src/chapters/chapter12_populated_REORGANIZED.tex
textbook/src/chapters/chapter13_populated_REORGANIZED.tex
textbook/src/chapters/chapter14_populated_REORGANIZED.tex
textbook/src/chapters/chapter15_populated_REORGANIZED.tex
```

### Extracted Backups (39 files) - REMOVE

All files matching: `textbook/extracted/*/*_backup_*`

### Extracted REORGANIZED (43 files) - REMOVE

All files matching: `textbook/extracted/*/*_REORGANIZED_*`

---

## Phase 2: Registry Cleanup (6 files)

### Duplicates to REMOVE

```
registry/textbook/equations.yaml         # 391 lines - subset of textbook/
registry/textbook/equations_full.yaml    # 4,087 lines - duplicate of textbook/
registry/textbook/variables.yaml         # 378 lines - subset of textbook/
registry/textbook/variables_full.yaml    # 3,532 lines - duplicate of textbook/
registry/textbook/all_math_authoritative.yaml  # 694 lines - redundant
registry/textbook/database_schema.yaml   # 311 lines - duplicate of textbook/
```

### Files to KEEP

```
registry/textbook/chapters.yaml          # 136 lines - unique metadata
registry/textbook/definitions.yaml       # 204 lines - unique schema defs
registry/textbook/frameworks.yaml        # 246 lines - unique framework defs
registry/textbook/qc_gates.yaml          # 228 lines - unique QC thresholds
```

---

## Phase 3: Bin Deduplication (7 files)

### Scripts to REMOVE (exact duplicates of skills/)

```
bin/end_reason.py           # → skills/end-reason/scripts/
bin/dorado_basecall.py      # → skills/dorado-bench-v2/scripts/
bin/ont_align.py            # → skills/ont-align/scripts/
bin/ont_monitor.py          # → skills/ont-monitor/scripts/
bin/ont_pipeline.py         # → skills/ont-pipeline/scripts/
bin/calculate_resources.py  # → skills/dorado-bench-v2/scripts/
bin/make_sbatch_from_cmdtxt.py  # → skills/dorado-bench-v2/scripts/
```

### Scripts to KEEP (unique or authoritative)

```
bin/ont_experiments.py      # AUTHORITATIVE - core orchestrator
bin/experiment_db.py        # AUTHORITATIVE - enhanced version
bin/ont_context.py          # UNIQUE - experiment context
bin/ont_config.py           # UNIQUE - configuration management
bin/ont_dashboard.py        # UNIQUE - web interface
bin/ont_endreason_qc.py     # UNIQUE - v2.0 KDE visualization
bin/ont_integrate.py        # UNIQUE - git integration
bin/ont_manuscript.py       # UNIQUE - manuscript pipelines
bin/ont_registry.py         # UNIQUE - permanent registry
bin/ont_textbook_export.py  # UNIQUE - textbook export
```

---

## Phase 4: Sync Diverged Files

After cleanup, sync the authoritative bin/ versions to skills/:

```bash
# ont_experiments.py: bin has +1,203 lines of enhancements
cp bin/ont_experiments.py skills/ont-experiments-v2/scripts/

# experiment_db.py: bin has +360 lines
cp bin/experiment_db.py skills/experiment-db/scripts/
```

---

## Execution Commands

```bash
#!/bin/bash
# Run from ont-ecosystem root

# Phase 1: Textbook
find textbook/src/chapters -name "*_backup_*" -delete
find textbook/src/chapters -name "*_REORGANIZED*" -delete
find textbook/extracted -name "*_backup_*" -delete
find textbook/extracted -name "*_REORGANIZED*" -delete

# Phase 2: Registry
rm -f registry/textbook/equations.yaml
rm -f registry/textbook/equations_full.yaml
rm -f registry/textbook/variables.yaml
rm -f registry/textbook/variables_full.yaml
rm -f registry/textbook/all_math_authoritative.yaml
rm -f registry/textbook/database_schema.yaml

# Phase 3: Bin
rm -f bin/end_reason.py
rm -f bin/dorado_basecall.py
rm -f bin/ont_align.py
rm -f bin/ont_monitor.py
rm -f bin/ont_pipeline.py
rm -f bin/calculate_resources.py
rm -f bin/make_sbatch_from_cmdtxt.py

# Phase 4: Sync
cp bin/ont_experiments.py skills/ont-experiments-v2/scripts/
cp bin/experiment_db.py skills/experiment-db/scripts/

# Verify
pytest tests/ -v
```

---

## Post-Cleanup Verification

After cleanup, verify:

1. [ ] All 30 tests pass
2. [ ] Skills can be invoked: `/end-reason`, `/ont-align`, etc.
3. [ ] Pattern B works: `ont_experiments.py run end_reasons <exp>`
4. [ ] No broken imports in remaining files
5. [ ] Textbook equations.yaml is accessible
6. [ ] Variables.yaml is accessible
