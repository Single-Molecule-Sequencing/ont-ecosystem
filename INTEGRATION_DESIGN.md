# ONT Ecosystem: Holistic Integration Design

## Executive Summary

This document defines the authoritative architecture for the ont-ecosystem,
eliminating redundancy and establishing clear automation workflows for
iterative development by humans and AI agents.

**Key Metrics:**
- Current redundancy: ~15,000 lines of duplicate code/content
- Files to remove: 92+ redundant files
- Storage savings: ~1.7MB (30% reduction)
- Single sources of truth: 5 authoritative domains

---

## Part 1: Current State Analysis

### Redundancy Inventory

| Category | Redundant Files | Lines | Savings |
|----------|-----------------|-------|---------|
| Textbook backups | 51 files | ~2,000 | 193KB |
| Textbook REORGANIZED | 34 files | ~4,000 | 670KB |
| Registry duplicates | 4 files | 7,997 | 120KB |
| Bin script duplicates | 7 files | 5,116 | 80KB |
| Empty directories | 3 dirs | 0 | 0 |
| **TOTAL** | **99 items** | **~19,000** | **~1.1MB** |

### Divergence Issues

| File Pair | Divergence | Risk Level |
|-----------|------------|------------|
| bin/ont_experiments.py vs skills/ | +1,203 lines | CRITICAL |
| bin/experiment_db.py vs skills/ | +360 lines | HIGH |

---

## Part 2: Authoritative Source Architecture

### Principle: Single Source of Truth (SSOT)

Each domain has ONE authoritative source. All other instances are either:
- **Derived** (auto-generated from source)
- **Cached** (performance optimization)
- **Legacy** (scheduled for removal)

### Domain 1: Mathematics

```
AUTHORITATIVE: data/math/All_Math.tex (1,180 lines)
     │
     ├──► data/math/All_Math.pdf (compiled reference)
     │
     └──► textbook/equations.yaml (extracted database)
              │
              └──► registry/textbook/equations.yaml (REMOVE - duplicate)
```

**Rules:**
- All_Math.tex is the mathematical source of truth
- equations.yaml is derived via extraction scripts
- No other equation databases should exist

### Domain 2: Variables

```
AUTHORITATIVE: textbook/variables.yaml (3,532 lines)
     │
     ├──► Skills use variables via import
     │
     └──► registry/textbook/variables.yaml (REMOVE - duplicate)
```

### Domain 3: Skill Code

```
AUTHORITATIVE: skills/*/scripts/*.py
     │
     ├──► bin/*.py (DERIVED - symlinks or imports)
     │
     └──► Pattern B orchestration via ont_experiments.py
```

**Rules:**
- Skills directory is canonical for analysis code
- bin/ contains orchestration scripts and unique infrastructure
- No duplicate copies allowed

### Domain 4: Experiments

```
AUTHORITATIVE: ~/.ont-registry/ (runtime)
     │
     ├──► data/experiment_registry.json (static examples)
     │
     └──► registry/experiments.yaml (template/schema)
```

### Domain 5: Textbook Content

```
AUTHORITATIVE: textbook/src/chapters/*.tex (18 files)
     │
     ├──► textbook/extracted/ (derived figures/tables)
     │
     └──► haplotype_v6_complete_FIXED.tex (master document)
```

---

## Part 3: Target Directory Structure

```
ont-ecosystem/
├── bin/                              # Orchestration & infrastructure only
│   ├── ont_experiments.py            # Core orchestrator (KEEP - authoritative)
│   ├── ont_context.py                # Experiment context (KEEP - unique)
│   ├── ont_config.py                 # Configuration (KEEP - unique)
│   ├── ont_dashboard.py              # Web interface (KEEP - unique)
│   ├── ont_integrate.py              # Git integration (KEEP - unique)
│   ├── ont_manuscript.py             # Manuscript pipeline (KEEP - unique)
│   ├── ont_registry.py               # Permanent registry (KEEP - unique)
│   └── ont_textbook_export.py        # Textbook export (KEEP - unique)
│   # REMOVED: end_reason.py, ont_align.py, ont_monitor.py,
│   #          ont_pipeline.py, dorado_basecall.py, etc.
│
├── skills/                           # AUTHORITATIVE for analysis code
│   ├── dorado-bench-v2/
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   │   ├── dorado_basecall.py    # AUTHORITATIVE
│   │   │   ├── calculate_resources.py
│   │   │   └── make_sbatch_from_cmdtxt.py
│   │   └── assets/
│   ├── end-reason/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── end_reason.py         # AUTHORITATIVE
│   ├── ont-align/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── ont_align.py          # AUTHORITATIVE
│   ├── ont-experiments-v2/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── ont_experiments.py    # SYNC from bin/ (bin is authoritative)
│   ├── ont-monitor/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── ont_monitor.py        # AUTHORITATIVE
│   ├── ont-pipeline/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── ont_pipeline.py       # AUTHORITATIVE
│   ├── experiment-db/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── experiment_db.py      # SYNC from bin/ (bin is authoritative)
│   └── manuscript/
│       ├── SKILL.md
│       └── generators/
│
├── textbook/                         # AUTHORITATIVE for academic content
│   ├── equations.yaml                # AUTHORITATIVE (4,087 lines)
│   ├── variables.yaml                # AUTHORITATIVE (3,532 lines)
│   ├── haplotype_v6_complete_FIXED.tex
│   ├── compile_config.yaml
│   ├── equation_framework_v2.tex
│   ├── sms.sty
│   ├── references.bib
│   ├── CLAUDE.md
│   ├── src/
│   │   ├── chapters/                 # 18 files (KEEP current versions only)
│   │   └── appendices/               # 11 files
│   ├── extracted/
│   │   ├── metadata.json
│   │   ├── figures/                  # 15 current versions only
│   │   └── tables/                   # 87 current versions only
│   └── FAT/
│       └── scripts/                  # Extraction tools
│
├── data/
│   ├── math/
│   │   ├── All_Math.tex              # AUTHORITATIVE mathematical source
│   │   ├── All_Math.pdf              # Compiled reference
│   │   └── MATH_SKILLS_INTEGRATION.md
│   └── experiment_registry.json      # Static examples
│
├── registry/                         # Schemas and lightweight metadata
│   ├── INDEX.yaml
│   ├── experiments.yaml              # Template/schema
│   ├── pipeline/
│   │   └── stages.yaml
│   ├── schemas/                      # JSON Schemas (KEEP all)
│   └── textbook/                     # LIGHTWEIGHT references only
│       ├── chapters.yaml             # 136 lines (metadata)
│       ├── definitions.yaml          # 204 lines (schema)
│       ├── frameworks.yaml           # 246 lines (unique)
│       └── qc_gates.yaml             # 228 lines (unique)
│       # REMOVED: equations.yaml, equations_full.yaml,
│       #          variables.yaml, variables_full.yaml,
│       #          all_math_authoritative.yaml, database_schema.yaml
│
├── manuscripts/                      # Generated content (gitignored)
│   └── templates/                    # KEEP templates
│
├── dashboards/                       # React components
├── examples/                         # Configuration examples
├── tests/                            # Test suite
└── docs/                             # Documentation
```

---

## Part 4: Files to Remove

### Phase 1: Textbook Cleanup (85 files)

```bash
# Backup files (51 files)
rm textbook/src/chapters/*_backup_20251118_101124.tex
rm textbook/extracted/figures/*_backup_*.tex
rm textbook/extracted/tables/*_backup_*.tex

# REORGANIZED variants (34 files) - Archive first
git tag archive/reorganized-variants
rm textbook/src/chapters/*_REORGANIZED.tex
rm textbook/extracted/figures/*_REORGANIZED_*.tex
rm textbook/extracted/tables/*_REORGANIZED_*.tex

# Empty directories
rmdir textbook/output textbook/figures textbook/tables
```

### Phase 2: Registry Cleanup (6 files, 8,811 lines)

```bash
# Duplicate equation/variable databases
rm registry/textbook/equations.yaml        # 391 lines (subset)
rm registry/textbook/equations_full.yaml   # 4,087 lines (duplicate)
rm registry/textbook/variables.yaml        # 378 lines (subset)
rm registry/textbook/variables_full.yaml   # 3,532 lines (duplicate)
rm registry/textbook/all_math_authoritative.yaml  # 694 lines (redundant)
rm registry/textbook/database_schema.yaml  # Already in textbook/
```

### Phase 3: Bin Deduplication (7 files, 5,116 lines)

```bash
# Replace duplicates with imports or symlinks
rm bin/end_reason.py           # Use skills/end-reason/scripts/
rm bin/dorado_basecall.py      # Use skills/dorado-bench-v2/scripts/
rm bin/ont_align.py            # Use skills/ont-align/scripts/
rm bin/ont_monitor.py          # Use skills/ont-monitor/scripts/
rm bin/ont_pipeline.py         # Use skills/ont-pipeline/scripts/
rm bin/calculate_resources.py  # Use skills/dorado-bench-v2/scripts/
rm bin/make_sbatch_from_cmdtxt.py  # Use skills/dorado-bench-v2/scripts/
```

### Phase 4: Sync Diverged Files

```bash
# ont_experiments.py: bin/ is authoritative (+1,203 lines of enhancements)
cp bin/ont_experiments.py skills/ont-experiments-v2/scripts/

# experiment_db.py: bin/ is authoritative (+360 lines)
cp bin/experiment_db.py skills/experiment-db/scripts/
```

---

## Part 5: Automation Architecture

### Principle: Derivation Pipelines

All derived content is generated from authoritative sources via automated pipelines.

### Pipeline 1: Math → Equations Database

```
All_Math.tex ──► extract_equations.py ──► equations.yaml
     │
     └──► pdflatex ──► All_Math.pdf
```

**Trigger:** Changes to All_Math.tex
**Output:** Updated equations.yaml, All_Math.pdf
**Automation:** GitHub Actions or pre-commit hook

### Pipeline 2: Chapters → Extracted Content

```
src/chapters/*.tex ──► extract_figures_tables.py ──► extracted/
     │
     └──► compile.sh ──► SMS_Haplotype_Framework_Textbook.pdf
```

**Trigger:** Changes to chapter files
**Output:** Updated extracted figures/tables, PDF
**Automation:** GitHub Actions

### Pipeline 3: Experiments → Results → Figures

```
Experiment Data ──► ont_experiments.py run ──► results.json
     │
     └──► ont_manuscript.py figure ──► figures/*.pdf
```

**Trigger:** Analysis completion
**Output:** Publication-ready figures
**Automation:** Pattern B orchestration

### Pipeline 4: Variables → Documentation

```
variables.yaml ──► generate_variable_docs.py ──► Variable Reference
     │
     └──► appendixG_variable_master.tex
```

---

## Part 6: AI/Agentic Automation Design

### Claude Code Integration Points

#### 1. Skill Invocation (Existing)

```yaml
# CLAUDE.md instruction
When user asks to run analysis:
1. Use /end-reason skill for QC analysis
2. Use /ont-align skill for alignment
3. All results tracked via ont_experiments.py
```

#### 2. Content Generation (New)

```yaml
# Agentic workflow for figure generation
trigger: "generate figure for experiment X"
steps:
  1. Load experiment context via ont_context.py
  2. Select appropriate figure generator
  3. Run generator with experiment data
  4. Store versioned artifact
  5. Update textbook/extracted/ if applicable
```

#### 3. Iterative Math Updates (New)

```yaml
# Workflow for equation updates
trigger: "add equation for topic X"
steps:
  1. Add LaTeX to All_Math.tex (appropriate section)
  2. Run extract_equations.py to update equations.yaml
  3. Update MATH_SKILLS_INTEGRATION.md if skill-relevant
  4. Run tests to verify integration
  5. Commit with structured message
```

#### 4. Manuscript Scaffolding (New)

```yaml
# Workflow for new manuscript
trigger: "create manuscript about X"
steps:
  1. Select relevant experiments via ont_manuscript.py select
  2. Generate figures/tables via pipelines
  3. Create LaTeX scaffold with ont_integrate.py
  4. Link experiment provenance
  5. Initialize as separate git repo
```

### Hook System for Automation

```python
# ~/.claude/hooks/post-analysis.py
"""
Automatically triggered after any analysis completion
"""

def on_analysis_complete(experiment_id, analysis_type, results):
    # Auto-generate standard figures
    if analysis_type == "end_reasons":
        generate_end_reason_kde(experiment_id, results)

    # Sync to database
    sync_to_database(experiment_id, results)

    # Update manuscript artifacts if linked
    update_linked_manuscripts(experiment_id)
```

### Agent Roles

| Agent | Responsibility | Triggers |
|-------|---------------|----------|
| **Analysis Agent** | Run skills, collect results | User request, scheduled |
| **Figure Agent** | Generate visualizations | Analysis completion |
| **Math Agent** | Update equations, validate | Content changes |
| **Integration Agent** | Sync files, resolve conflicts | Git hooks |
| **Documentation Agent** | Update docs, cross-refs | Any content change |

---

## Part 7: Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ONT ECOSYSTEM DATA FLOW                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  AUTHORITATIVE SOURCES                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ All_Math.tex │  │equations.yaml│  │variables.yaml│  │ src/chapters/│   │
│  │   (Math)     │  │ (Equations)  │  │ (Variables)  │  │  (Content)   │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                 │                 │                 │            │
│         ▼                 ▼                 ▼                 ▼            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    DERIVATION PIPELINES                              │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │ extract_ │  │ validate_│  │ generate_│  │ compile  │            │   │
│  │  │equations │  │ database │  │ docs     │  │ latex    │            │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                 │                 │                 │            │
│         ▼                 ▼                 ▼                 ▼            │
│  DERIVED OUTPUTS                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ All_Math.pdf │  │  extracted/  │  │ appendices   │  │ Textbook.pdf │   │
│  │              │  │figures+tables│  │              │  │              │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                                             │
│  SKILLS (AUTHORITATIVE CODE)                                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │end-reason│ │ont-align │ │dorado-   │ │ont-      │ │ont-      │        │
│  │          │ │          │ │bench-v2  │ │monitor   │ │pipeline  │        │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘        │
│       │            │            │            │            │               │
│       └────────────┴────────────┴────────────┴────────────┘               │
│                                    │                                       │
│                                    ▼                                       │
│  ORCHESTRATION                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              ont_experiments.py (Pattern B)                          │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │ Registry │  │ Events   │  │ Pipeline │  │ Provenance│            │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                       │
│                                    ▼                                       │
│  OUTPUTS                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                     │
│  │ Results JSON │  │ Figures/     │  │ Manuscripts  │                     │
│  │              │  │ Tables       │  │              │                     │
│  └──────────────┘  └──────────────┘  └──────────────┘                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 8: Implementation Plan

### Phase 1: Cleanup (Immediate)

**Duration:** 1 session
**Risk:** Low

1. Remove 51 backup files from textbook/
2. Archive and remove 34 REORGANIZED files
3. Remove 6 duplicate registry files
4. Remove 7 duplicate bin scripts
5. Run tests to verify nothing broke

### Phase 2: Sync & Consolidate (Next)

**Duration:** 1 session
**Risk:** Medium

1. Sync ont_experiments.py to skills/ (bin is authoritative)
2. Sync experiment_db.py to skills/ (bin is authoritative)
3. Create wrapper imports in bin/ for removed scripts
4. Update documentation references
5. Run full test suite

### Phase 3: Automation Setup (Following)

**Duration:** 2 sessions
**Risk:** Low

1. Create derivation pipeline scripts
2. Set up GitHub Actions for auto-generation
3. Add pre-commit hooks for validation
4. Create AUTHORITATIVE_SOURCES.md
5. Update CLAUDE.md with automation instructions

### Phase 4: Agent Integration (Enhancement)

**Duration:** Ongoing
**Risk:** Low

1. Define agent roles and responsibilities
2. Create hook system for automation
3. Build figure generation pipelines
4. Implement manuscript scaffolding
5. Add iterative update workflows

---

## Part 9: Verification Checklist

### After Cleanup

- [ ] All 30 tests pass
- [ ] No broken imports
- [ ] Skills still invocable
- [ ] Pattern B orchestration works
- [ ] Textbook compiles

### After Consolidation

- [ ] Single source of truth for each domain
- [ ] No duplicate files
- [ ] All cross-references valid
- [ ] Documentation updated

### After Automation

- [ ] Derivation pipelines work
- [ ] Auto-generation triggers correctly
- [ ] Versioning preserved
- [ ] Agent workflows functional

---

## Appendix A: File Removal Commands

```bash
#!/bin/bash
# cleanup.sh - Execute from ont-ecosystem root

# Phase 1: Textbook cleanup
echo "Removing textbook backups..."
find textbook/src/chapters -name "*_backup_*" -delete
find textbook/extracted -name "*_backup_*" -delete

echo "Archiving REORGANIZED variants..."
git stash
git checkout -b archive/reorganized-variants
git add textbook/src/chapters/*_REORGANIZED.tex
git add textbook/extracted/*_REORGANIZED_*.tex
git commit -m "Archive: REORGANIZED textbook variants"
git checkout main
git stash pop

echo "Removing REORGANIZED files..."
find textbook/src/chapters -name "*_REORGANIZED*" -delete
find textbook/extracted -name "*_REORGANIZED*" -delete

# Phase 2: Registry cleanup
echo "Removing duplicate registry files..."
rm -f registry/textbook/equations.yaml
rm -f registry/textbook/equations_full.yaml
rm -f registry/textbook/variables.yaml
rm -f registry/textbook/variables_full.yaml
rm -f registry/textbook/all_math_authoritative.yaml
rm -f registry/textbook/database_schema.yaml

# Phase 3: Bin deduplication
echo "Removing duplicate bin scripts..."
rm -f bin/end_reason.py
rm -f bin/dorado_basecall.py
rm -f bin/ont_align.py
rm -f bin/ont_monitor.py
rm -f bin/ont_pipeline.py
rm -f bin/calculate_resources.py
rm -f bin/make_sbatch_from_cmdtxt.py

# Phase 4: Sync diverged
echo "Syncing diverged scripts..."
cp bin/ont_experiments.py skills/ont-experiments-v2/scripts/
cp bin/experiment_db.py skills/experiment-db/scripts/

echo "Cleanup complete. Run tests to verify."
pytest tests/ -v
```

---

## Appendix B: Wrapper Script Template

```python
#!/usr/bin/env python3
"""
bin/end_reason.py - Wrapper for skills/end-reason/scripts/end_reason.py

This file imports from the authoritative skill location.
Do not edit this file - edit the skill script instead.
"""

import sys
from pathlib import Path

# Add skills to path
skills_path = Path(__file__).parent.parent / "skills" / "end-reason" / "scripts"
sys.path.insert(0, str(skills_path))

from end_reason import main

if __name__ == "__main__":
    main()
```

---

## Appendix C: Authoritative Sources Reference

| Domain | Authoritative File | Format | Lines |
|--------|-------------------|--------|-------|
| Mathematics | data/math/All_Math.tex | LaTeX | 1,180 |
| Equations | textbook/equations.yaml | YAML | 4,087 |
| Variables | textbook/variables.yaml | YAML | 3,532 |
| Chapters | textbook/src/chapters/*.tex | LaTeX | ~15,000 |
| Skills | skills/*/scripts/*.py | Python | ~9,000 |
| Orchestration | bin/ont_experiments.py | Python | 2,946 |
| Experiments | ~/.ont-registry/ | YAML | Runtime |
| Schemas | registry/schemas/*.json | JSON | ~500 |

**Total Authoritative Content:** ~35,000 lines

**Removed Redundancy:** ~19,000 lines (35% reduction)
