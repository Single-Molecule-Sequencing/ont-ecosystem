# ONT Ecosystem Architecture

## Overview

ONT Ecosystem is a consolidated monorepo (v2.0) for Oxford Nanopore sequencing experiment management, providing:
- Event-sourced experiment registry with full provenance
- Analysis skill packages (end-reason, alignment, basecalling, monitoring)
- Mathematical framework from the SMS Haplotype Textbook
- Publication-quality figure/table generation
- Connected manuscript repository system

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ONT ECOSYSTEM v2.0                                │
│                         Consolidated Monorepo                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        USER INTERFACE LAYER                          │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │  CLI Commands          │  Web Dashboards      │  Skill Invocations  │   │
│  │  ont_experiments.py    │  ont_dashboard.py    │  /end-reason        │   │
│  │  ont_manuscript.py     │  React JSX (4)       │  /dorado-bench      │   │
│  │  ont_integrate.py      │  Port 8080           │  /ont-align         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      ORCHESTRATION LAYER                             │   │
│  │                    (Pattern B - Provenance)                          │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                      │   │
│  │   ont_experiments.py ─────────────────────────────────────────┐     │   │
│  │   (Core Hub)                                                   │     │   │
│  │     │                                                          │     │   │
│  │     ├── Experiment Registration                                │     │   │
│  │     ├── Event Logging                                          │     │   │
│  │     ├── Provenance Tracking                                    │     │   │
│  │     ├── HPC Metadata Capture (SLURM)                          │     │   │
│  │     └── Skill Dispatch                                         │     │   │
│  │                                                          │     │     │   │
│  │   ont_context.py ◄─────────────────────────────────────┘     │     │   │
│  │   (Unified View)                                               │     │   │
│  │     │                                                          │     │   │
│  │     ├── Registry + Events                                      │     │   │
│  │     ├── Database Statistics                                    │     │   │
│  │     ├── Pipeline State                                         │     │   │
│  │     └── Related Experiments                                    │     │   │
│  │                                                          │     │     │   │
│  │   ont_manuscript.py ◄────────────────────────────────────┘     │     │   │
│  │   (Figure/Table Gen)                                                 │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        ANALYSIS LAYER                                │   │
│  │                    (8 Skill Packages)                                │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │  end-reason  │  │ dorado-bench │  │  ont-align   │              │   │
│  │  │  (σ stage)   │  │  (r stage)   │  │  (r stage)   │              │   │
│  │  │  QC Analysis │  │  Basecalling │  │  Alignment   │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  │                                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │ ont-monitor  │  │ ont-pipeline │  │ experiment-db│              │   │
│  │  │  (σ stage)   │  │  (r,A stage) │  │   (data)     │              │   │
│  │  │  Monitoring  │  │  Workflows   │  │   SQLite     │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  │                                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐                                │   │
│  │  │  manuscript  │  │ont-experiments│                                │   │
│  │  │  (A stage)   │  │    -v2       │                                │   │
│  │  │  Publishing  │  │  Registry    │                                │   │
│  │  └──────────────┘  └──────────────┘                                │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         DATA LAYER                                   │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                      │   │
│  │  Registry (~/.ont-registry/)     │  Textbook (textbook/)            │   │
│  │  ├── experiments.yaml            │  ├── equations.yaml (4087 lines) │   │
│  │  ├── experiments/<id>/           │  ├── variables.yaml (3532 lines) │   │
│  │  │   ├── events.yaml             │  ├── sms.sty                     │   │
│  │  │   ├── tasks.yaml              │  └── src/chapters/*.tex          │   │
│  │  │   └── PROGRESS.md             │                                  │   │
│  │  └── config.yaml                 │  Reference (data/math/)          │   │
│  │                                  │  └── All_Math.pdf                │   │
│  │  Artifacts (~/.ont-manuscript/)  │                                  │   │
│  │  └── artifacts/<exp>/<type>/     │  Schemas (registry/schemas/)     │   │
│  │      └── v1/, v2/, latest/       │  └── *.json (6 schemas)          │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Pipeline Factorization Theorem

The system implements the 9-stage Pipeline Factorization Theorem from Chapter 4:

```
P(h,g,u,d,ℓ,σ,r) = P(h)·P(g|h)·P(u|g)·P(d|u,C)·P(ℓ|d,C)·P(σ|ℓ,A)·P(r|σ,A)

┌─────────────────────────────────────────────────────────────────────────────┐
│                         PIPELINE STAGES                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  BIOLOGICAL                      EXPERIMENTAL                  COMPUTATIONAL│
│  ┌─────┐  ┌─────┐  ┌─────┐     ┌─────┐  ┌─────┐  ┌─────┐     ┌─────┐      │
│  │  h  │─▶│  g  │─▶│  u  │────▶│  d  │─▶│  ℓ  │─▶│  σ  │────▶│  r  │      │
│  │     │  │     │  │     │     │     │  │     │  │     │     │     │      │
│  │Haplo│  │ Std │  │Guide│     │Frag │  │ Lib │  │ Sig │     │Base │      │
│  │type │  │     │  │     │     │     │  │     │  │     │     │call │      │
│  └─────┘  └─────┘  └─────┘     └─────┘  └─────┘  └─────┘     └─────┘      │
│                                   │                 │           │          │
│                                   ▼                 ▼           ▼          │
│                               ┌─────┐           ┌─────┐     ┌─────┐       │
│                               │  C  │           │  A  │     │  A  │       │
│                               │Cas9 │           │Adapt│     │Analy│       │
│                               └─────┘           └─────┘     └─────┘       │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  SKILL MAPPINGS                                                             │
│                                                                             │
│  Stage σ (Signal):     end-reason, ont-monitor                             │
│  Stage r (Basecall):   dorado-bench-v2, ont-align                          │
│  Stage A (Analysis):   ont-pipeline, manuscript                            │
│  Multi-stage:          ont-experiments-v2 (orchestration)                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Pattern B Orchestration (Provenance)

All analyses flow through `ont_experiments.py` for automatic tracking:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PATTERN B FLOW                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  User Request                                                               │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ont_experiments.py run <skill> <experiment_id> [options]           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ├── 1. Validate experiment exists in registry                        │
│       │                                                                     │
│       ├── 2. Create event record                                           │
│       │      {                                                              │
│       │        "id": "evt-xxx",                                            │
│       │        "type": "analysis",                                         │
│       │        "skill": "end-reason",                                      │
│       │        "started": "2025-01-01T12:00:00Z",                         │
│       │        "slurm_job_id": "12345",  // if on HPC                     │
│       │        "gpu_count": 4            // if applicable                  │
│       │      }                                                              │
│       │                                                                     │
│       ├── 3. Dispatch to skill                                             │
│       │      ┌──────────────────────────────────────────────────────┐      │
│       │      │  end_reason.py <data_path> --json results.json       │      │
│       │      └──────────────────────────────────────────────────────┘      │
│       │                                                                     │
│       ├── 4. Capture results                                               │
│       │      - Exit code                                                   │
│       │      - Output files                                                │
│       │      - Metrics                                                     │
│       │                                                                     │
│       ├── 5. Update event record                                           │
│       │      {                                                              │
│       │        "completed": "2025-01-01T12:05:00Z",                       │
│       │        "status": "success",                                        │
│       │        "results": { ... }                                          │
│       │      }                                                              │
│       │                                                                     │
│       └── 6. Sync to database (if experiment_db enabled)                   │
│                                                                             │
│  Result: Full audit trail of all operations                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Manuscript Integration System

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MANUSCRIPT INTEGRATION                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ont-ecosystem (Hub)                    Manuscript Repos (Spokes)          │
│  ════════════════════                   ═════════════════════════          │
│                                                                             │
│  ┌─────────────────────┐                ┌─────────────────────┐            │
│  │  textbook/          │                │  my-cyp2d6-paper/   │            │
│  │  ├── equations.yaml │◄──submodule────│  ├── ont-ecosystem/ │            │
│  │  ├── variables.yaml │                │  ├── figures/       │            │
│  │  └── sms.sty        │                │  ├── tables/        │            │
│  │                     │                │  ├── main.tex       │            │
│  │  manuscripts/       │                │  └── .manuscript.yaml│           │
│  │  └── templates/     │                └─────────────────────┘            │
│  │      ├── paper/     │                           │                       │
│  │      ├── chapter/   │──create─────────────────▶│                       │
│  │      └── supplement/│                           │                       │
│  │                     │                           │                       │
│  │  ~/.ont-manuscript/ │                           │                       │
│  │  └── artifacts/     │──sync────────────────────▶│                       │
│  │      └── exp-xxx/   │  (figures, tables)        │                       │
│  │          ├── figures│                           │                       │
│  │          └── tables │                           │                       │
│  └─────────────────────┘                           │                       │
│                                                     │                       │
│  Commands:                                          │                       │
│  ┌─────────────────────────────────────────────────┴───────────────────┐   │
│  │ ont_integrate.py create-manuscript my-paper --template paper        │   │
│  │ ont_integrate.py connect /path/to/existing-manuscript               │   │
│  │ ont_integrate.py sync /path/to/manuscript --experiments exp-abc     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA FLOW                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Sequencing Run                                                             │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────┐     ont_experiments.py register                       │
│  │  POD5/FAST5     │────────────────────────────────▶ experiments.yaml     │
│  │  Raw Signals    │                                                        │
│  └─────────────────┘                                                        │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────┐     ont_experiments.py run end-reason                 │
│  │  end_reason.py  │────────────────────────────────▶ Event Logged         │
│  │  QC Analysis    │                                   │                    │
│  └─────────────────┘                                   │                    │
│       │                                                │                    │
│       ├── signal_positive_pct                         │                    │
│       ├── unblock_mux_pct                             │                    │
│       └── quality_grade                               ▼                    │
│                                                  ┌──────────┐              │
│  ┌─────────────────┐                            │ Context  │              │
│  │ dorado_basecall │                            │ (unified)│              │
│  │  GPU Basecalling│                            └──────────┘              │
│  └─────────────────┘                                   │                    │
│       │                                                │                    │
│       ├── mean_qscore                                 │                    │
│       ├── n50                                         ▼                    │
│       └── pass_reads                            ┌──────────┐              │
│                                                 │Manuscript│              │
│  ┌─────────────────┐                            │  Studio  │              │
│  │  ont_align.py   │                            └──────────┘              │
│  │  Alignment      │                                   │                    │
│  └─────────────────┘                                   │                    │
│       │                                                ▼                    │
│       ├── mapping_rate                          ┌──────────┐              │
│       ├── mean_coverage                         │ Figures  │              │
│       └── error_rate                            │ Tables   │              │
│                                                 │ (PDF/PNG)│              │
│                                                 └──────────┘              │
│                                                        │                    │
│                                                        ▼                    │
│                                                 ┌──────────┐              │
│                                                 │Manuscript│              │
│                                                 │  Repo    │              │
│                                                 └──────────┘              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
ont-ecosystem/
├── bin/                          # Executable scripts (17 Python)
│   ├── ont_experiments.py        # Core orchestration (2947 lines)
│   ├── ont_manuscript.py         # Figure/table generation (1027 lines)
│   ├── ont_context.py            # Unified experiment view (757 lines)
│   ├── ont_integrate.py          # Manuscript scaffolding (772 lines)
│   ├── ont_pipeline.py           # Multi-step workflows (1029 lines)
│   ├── ont_monitor.py            # Run monitoring (1243 lines)
│   ├── ont_align.py              # Alignment toolkit (1061 lines)
│   ├── end_reason.py             # End reason analysis (581 lines)
│   ├── dorado_basecall.py        # GPU basecalling (834 lines)
│   └── ...
│
├── skills/                       # Skill packages (8)
│   ├── end-reason/
│   │   ├── SKILL.md              # Frontmatter + docs
│   │   └── scripts/              # Skill implementation
│   ├── dorado-bench-v2/
│   ├── ont-align/
│   ├── ont-monitor/
│   ├── ont-pipeline/
│   ├── ont-experiments-v2/
│   ├── experiment-db/
│   └── manuscript/
│
├── textbook/                     # SMS Haplotype Framework
│   ├── equations.yaml            # 4087 lines - equation database
│   ├── variables.yaml            # 3532 lines - variable database
│   ├── database_schema.yaml      # Schema documentation
│   ├── sms.sty                   # LaTeX style package
│   ├── references.bib            # BibTeX references
│   ├── CLAUDE.md                 # AI guidance
│   ├── scripts/
│   │   ├── validate_database.py
│   │   ├── equation_database.py
│   │   └── compile.sh
│   └── src/
│       ├── chapters/             # 48 .tex files
│       └── appendices/           # 11 .tex files
│
├── data/
│   ├── math/
│   │   └── All_Math.pdf          # Authoritative reference (306KB)
│   └── experiment_registry.json
│
├── registry/
│   ├── INDEX.yaml                # Master index (v2.0.0)
│   ├── experiments.yaml          # 145 experiments
│   ├── pipeline/
│   │   └── stages.yaml           # 9 pipeline stages
│   └── schemas/                  # JSON Schema (6 files)
│       ├── experiment.json
│       ├── equation.json
│       ├── pipeline_stage.json
│       ├── task.json
│       ├── task_list.json
│       └── manuscript.json
│
├── manuscripts/
│   └── templates/                # Manuscript templates
│       ├── paper/
│       ├── chapter/
│       └── supplement/
│
├── dashboards/                   # React JSX (4 components)
│   ├── ont_dashboard.jsx
│   ├── ont-experiments-dashboard.jsx
│   ├── ont-align-dashboard.jsx
│   └── ont-workflow-dashboard.jsx
│
├── examples/
│   ├── pipelines/                # Workflow definitions
│   │   ├── qc-fast.yaml
│   │   ├── research-full.yaml
│   │   └── pharmaco-clinical.yaml
│   └── configs/                  # HPC configurations
│       ├── greatlakes.yaml
│       ├── armis2.yaml
│       └── local.yaml
│
├── tests/                        # pytest tests
├── docs/                         # Documentation
├── lib/                          # Shared Python modules
├── .github/workflows/            # CI/CD
├── CLAUDE.md                     # AI guidance
├── README.md                     # Project overview
├── pyproject.toml                # Python project config
├── Makefile                      # Build commands
└── install.sh                    # Installation script
```

## Key Equations Reference

| ID | Name | Formula | Used By |
|----|------|---------|---------|
| 1.1.1 | Phred Score | `p = 10^(-Q/10)` | dorado-bench, ont-align |
| 1.1.2 | Levenshtein | `d(s,r) ∈ ℕ₀` | ont-align |
| 5.2 | Purity Ceiling | `TPR ≤ π` | Classification analysis |
| 6.6 | Bayesian Posterior | `P(h|r) = P(r|h)P(h) / ΣP(r|h')P(h')` | ont-pipeline |
| CE.1 | Pipeline Factorization | See above | All stages |

## Runtime Paths

| Path | Purpose |
|------|---------|
| `~/.ont-registry/` | Event-sourced experiment registry |
| `~/.ont-manuscript/` | Versioned figure/table artifacts |
| `~/.ont-ecosystem/` | User configuration |

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `ONT_REGISTRY_DIR` | `~/.ont-registry` | Registry location |
| `ONT_MANUSCRIPT_DIR` | `~/.ont-manuscript` | Artifacts location |
| `ONT_ECOSYSTEM_HOME` | Auto-detect | Repository root |
| `ONT_GITHUB_SYNC` | `false` | Enable GitHub sync |
| `SLURM_JOB_ID` | (auto) | HPC job tracking |
