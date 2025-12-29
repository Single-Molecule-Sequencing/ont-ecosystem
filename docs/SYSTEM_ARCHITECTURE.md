# ONT Ecosystem System Architecture

## Overview

The ONT Ecosystem is a comprehensive toolkit for Oxford Nanopore sequencing experiment management with **full provenance tracking**, **event-sourced registry**, **domain memory**, and **integrated analysis workflows**.

```
                    +----------------------------------------------------+
                    |           ONT ECOSYSTEM ARCHITECTURE               |
                    +----------------------------------------------------+
                                          |
          +-------------------------------+-------------------------------+
          |                               |                               |
    +-----------+                  +-----------+                  +-----------+
    | Registry  |                  |  Domain   |                  | Textbook  |
    | System    |                  |  Memory   |                  | Registry  |
    +-----------+                  +-----------+                  +-----------+
    | experiments.yaml             | tasks.yaml                   | equations |
    | events tracking              | PROGRESS.md                  | variables |
    | schema validation            | bootup ritual                | stages    |
    +-----------+                  +-----------+                  +-----------+
          |                               |                               |
          +-------------------------------+-------------------------------+
                                          |
                    +----------------------------------------------------+
                    |        ont_experiments.py (Core Orchestration)      |
                    |        Pattern B: All analysis goes through here    |
                    +----------------------------------------------------+
                                          |
    +----------+----------+----------+----------+----------+----------+
    |          |          |          |          |          |          |
+-------+ +-------+ +-------+ +-------+ +-------+ +-------+ +-------+
|end-   | |dorado-| |ont-   | |ont-   | |ont-   | |experi-| |experi-|
|reason | |bench  | |align  | |monitor| |pipeline| |ment-db| |ment-  |
|(QC)   | |(call) | |(align)| |(watch)| |(flow) | |(DB)   | |montage|
+-------+ +-------+ +-------+ +-------+ +-------+ +-------+ +-------+
    |          |          |          |          |          |
    v          v          v          v          v          v
+----------------------------------------------------------------+
|              Pipeline Factorization Theorem Stages              |
+----------------------------------------------------------------+
|  h    |  g    |  u    |  d    |  l    |  σ    |  r    |  C  | A |
+----------------------------------------------------------------+
```

## Complete Skill Inventory

| Skill | Stage | Script | Description | Input Mode |
|-------|-------|--------|-------------|------------|
| **ont-experiments-v2** | Core | `ont_experiments.py` | Event-sourced registry & orchestration | - |
| **end-reason** | σ | `end_reason.py` | Read end reason QC analysis | location |
| **dorado-bench-v2** | r | `dorado_basecall.py` | GPU basecalling with model management | location |
| **ont-align** | r | `ont_align.py` | Alignment + Levenshtein edit distance | explicit |
| **ont-monitor** | σ | `ont_monitor.py` | Real-time/retrospective run monitoring | location |
| **ont-pipeline** | r,A | `ont_pipeline.py` | Multi-step workflow orchestration | - |
| **experiment-db** | - | `experiment_db.py` | SQLite database builder | path |

## Analysis Skills Integration

The `ANALYSIS_SKILLS` dictionary in `ont_experiments.py:92-152` maps each analysis type to its implementation:

```python
ANALYSIS_SKILLS = {
    # Signal Stage (σ)
    "end_reasons":   {"script": "end_reason.py",      "pipeline_stage": "σ", "skill_dir": "end-reason"},
    "endreason_qc":  {"script": "ont_endreason_qc.py", "pipeline_stage": "σ", "skill_dir": "end-reason"},
    "monitoring":    {"script": "ont_monitor.py",     "pipeline_stage": "σ", "skill_dir": "ont-monitor"},

    # Basecalling Stage (r)
    "basecalling":   {"script": "dorado_basecall.py", "pipeline_stage": "r", "skill_dir": "dorado-bench-v2"},
    "alignment":     {"script": "ont_align.py",       "pipeline_stage": "r", "skill_dir": "ont-align"},
    "align_qc":      {"script": "ont_align.py",       "pipeline_stage": "r", "skill_dir": "ont-align"},
}
```

## Pipeline Factorization Theorem

The core mathematical framework from the SMS Haplotype Framework Textbook:

```
P(h,g,u,d,l,σ,r) = P(h)·P(g|h)·P(u|g)·P(d|u)·P(l|d)·P(σ|l)·P(r|σ)
```

### Pipeline Stages

| Symbol | Name | Probability | Team | Skills |
|--------|------|-------------|------|--------|
| h | Haplotype Selection | P(h) | PGx | - |
| g | Standard Construction | P(g\|h) | Golden Gate | - |
| u | Guide Design | P(u\|g) | Cas9 Enrichment | - |
| d | Post-Cas9 Fragmentation | P(d\|u,C) | Cas9 Enrichment | - |
| ℓ | Library Loading | P(ℓ\|d,C) | HTC | - |
| σ | Signal Acquisition | P(σ\|ℓ,A) | ONT Adaptive | end-reason, ont-monitor |
| r | Basecalling | P(r\|σ,A) | AI/Basecaller | dorado-bench, ont-align |
| C | Cas9 Toggle | P(C) | Cas9 Enrichment | - |
| A | Adaptive Sampling Toggle | P(A) | ONT Adaptive | ont-pipeline |

## Event-Sourced Registry

### Directory Structure

```
~/.ont-registry/
├── experiments.yaml              # Main registry (YAML)
├── experiments/                  # Per-experiment domain memory
│   └── exp-abc123/
│       ├── tasks.yaml            # Machine-readable task backlog
│       ├── PROGRESS.md           # Human-readable progress log
│       └── CLAUDE.md             # Experiment-specific AI context
└── schemas/                      # JSON Schema validation
```

### Event Types

| Type | Description | Example |
|------|-------------|---------|
| `created` | Experiment registered | Initial discovery |
| `discovered` | Found during scan | Auto-discovery |
| `registered` | User registration | Manual add |
| `analysis` | Analysis executed | `run end_reasons exp-123` |
| `status_change` | Status update | `pending` → `running` |
| `tag_added` | Tag added | `--tags cyp2d6` |
| `error` | Error recorded | Analysis failure |
| `note` | User note | Free-form annotation |

### Event Object Structure

```yaml
events:
  - timestamp: "2024-01-15T14:30:00Z"
    type: "analysis"
    tool: "end_reason.py"
    description: "End reason QC analysis"
    results:
      total_reads: 125000
      quality_grade: "A"
      signal_positive_pct: 92.5
    exit_code: 0
    duration_seconds: 45.2
```

## Domain Memory System

Based on Anthropic's agent memory patterns for stateful AI workflows:

### Task Lifecycle

```
     ○ pending
         |
         v
     ◐ in_progress
        /   \
       v     v
    ✓ passing  ✗ failing
                  |
                  v
               − skipped
```

### Task v2.0 Features

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Task identifier (e.g., "end_reasons") |
| `status` | enum | pending, in_progress, passing, failing, skipped |
| `pipeline_stage` | str | Pipeline stage (σ, r, A) |
| `skill` | str | Associated skill name |
| `dependencies` | list | Task names that must complete first |
| `priority` | int | Execution priority (1-10) |
| `attempts` | int | Number of execution attempts |
| `error` | str | Error message if failing |

### Bootup Ritual Pattern

```python
# Agent bootup sequence
ctx = bootup_check("exp-abc123")

if ctx is None:
    print("Experiment not found")
elif ctx.failing_tasks:
    print(f"Fix first: {ctx.failing_tasks[0].name}")
    print(f"Error: {ctx.failing_tasks[0].error}")
elif ctx.pending_tasks:
    next_task = ctx.tasks.get_next_task()
    print(f"Next: {next_task.name}")
else:
    print("All tasks complete!")
```

## Schema Validation

JSON Schema validation ensures data integrity:

### Available Schemas

```
registry/schemas/
├── experiment.json      # Experiment metadata
├── equation.json        # Math equations
├── pipeline_stage.json  # Pipeline stages
├── task.json            # Individual tasks
└── task_list.json       # Task backlog
```

### Validation Commands

```bash
# Validate all registry files
ont_experiments.py validate

# Validate specific file
ont_experiments.py validate registry/textbook/equations.yaml
```

## Pattern B Orchestration

All analysis should route through `ont_experiments.py` for provenance:

```
+------------------+          +------------------+
|   Direct Call    |          | Pattern B Call   |
| (No Provenance)  |          | (Full Tracking)  |
+------------------+          +------------------+
| end_reason.py    |    vs    | ont_experiments  |
| /data/exp        |          | run end_reasons  |
| --json out.json  |          | exp-123 --json   |
+------------------+          +------------------+
| Output: JSON     |          | Output: JSON     |
| No tracking      |          | + Event logged   |
| No history       |          | + Checksums      |
|                  |          | + HPC metadata   |
|                  |          | + Duration       |
+------------------+          +------------------+
```

## Textbook Registry

Mathematical knowledge from SMS Haplotype Framework Textbook:

```
registry/textbook/
├── equations_full.yaml    # 4087 lines - all equations
├── variables_full.yaml    # 3532 lines - all variables
├── database_schema.yaml   # Schema documentation
├── chapters.yaml          # Chapter index
├── frameworks.yaml        # SMA-SEER, Pipeline Factorization
└── qc_gates.yaml          # QC thresholds
```

### Key Equations

| ID | Name | LaTeX | Stage |
|----|------|-------|-------|
| eq_6_6 | Bayesian Posterior | `P(h|r) = P(r|h)P(h) / ΣP(r|h')P(h')` | A |
| eq_phred | Phred Score | `Q = -10 log₁₀(P_error)` | r |
| eq_identity | Sequence Identity | `I = M / (M + X + I + D)` | r |
| eq_5_2 | Purity Ceiling | `TPR ≤ π` | g, A |

### Query Commands

```bash
# List all equations
ont_experiments.py math list

# Get equation details
ont_experiments.py math get eq_6_6

# Search equations
ont_experiments.py math search "bayesian"

# List pipeline stages
ont_experiments.py stages

# Get stage details
ont_experiments.py stage σ
```

## Testing

All tests are in `tests/` and run with pytest:

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_core.py -v

# Run specific test
pytest tests/test_core.py::test_edit_distance_basic -v
```

### Test Coverage

| Test | Description |
|------|-------------|
| `test_skill_files_exist` | SKILL.md exists for each skill |
| `test_skill_frontmatter` | Valid YAML frontmatter |
| `test_bin_scripts_exist` | All bin/*.py scripts exist |
| `test_bin_scripts_syntax` | Python syntax valid |
| `test_edit_distance_basic` | edlib integration |
| `test_task_dataclass` | Domain memory tasks |
| `test_tasklist_dataclass` | Task list operations |
| `test_validate_equation` | Schema validation |
| `test_validate_pipeline_stage` | Stage schema |

## HPC Integration

### SLURM Metadata Capture

When running on HPC clusters, automatic capture of:
- Job ID (`SLURM_JOB_ID`)
- Node list (`SLURM_NODELIST`)
- GPU allocation (`CUDA_VISIBLE_DEVICES`)
- Partition name
- Walltime

### Example HPC Workflow

```bash
# Generate SLURM job script
dorado_basecall.py /path/to/pod5 \
  --model sup@v5.0.0 \
  --slurm job.sh \
  --partition spgpu \
  --gpu-type a100

# Submit to SLURM
sbatch job.sh

# Analysis automatically captures HPC metadata
ont_experiments.py run basecalling exp-123 --model sup@v5.0.0
# → Event includes: job_id, nodes, gpus, partition, walltime
```

## File Structure

```
ont-ecosystem/
├── bin/                          # Executable scripts
│   ├── ont_experiments.py        # Core orchestration (2100+ lines)
│   ├── ont_align.py              # Alignment + edit distance
│   ├── ont_pipeline.py           # Pipeline orchestration
│   ├── end_reason.py             # End reason QC
│   ├── ont_endreason_qc.py       # Enhanced QC with KDE
│   ├── ont_monitor.py            # Run monitoring
│   ├── dorado_basecall.py        # GPU basecalling
│   └── calculate_resources.py    # Resource estimation
├── skills/                       # Skill packages
│   ├── ont-experiments-v2/       # Core skill
│   ├── end-reason/               # QC skill
│   ├── dorado-bench-v2/          # Basecalling skill
│   ├── ont-align/                # Alignment skill
│   ├── ont-monitor/              # Monitoring skill
│   ├── ont-pipeline/             # Pipeline skill
│   └── experiment-db/            # Database skill
├── registry/                     # Data registries
│   ├── textbook/                 # Math from textbook
│   └── schemas/                  # JSON Schema validation
├── dashboards/                   # React components
├── examples/                     # Config examples
│   ├── pipelines/                # Workflow definitions
│   └── configs/                  # HPC configs
├── tests/                        # pytest tests
└── docs/                         # Documentation
```

## Quick Reference

### Common Commands

```bash
# Registry Operations
ont_experiments.py init --git                    # Initialize
ont_experiments.py discover /data --register    # Discover
ont_experiments.py list                          # List experiments
ont_experiments.py info exp-123                  # Details
ont_experiments.py history exp-123               # Event history

# Analysis (Pattern B)
ont_experiments.py run end_reasons exp-123       # QC
ont_experiments.py run basecalling exp-123       # Basecall
ont_experiments.py run alignment exp-123         # Align

# Domain Memory
ont_experiments.py init-tasks exp-123            # Initialize
ont_experiments.py tasks exp-123                 # View tasks
ont_experiments.py next exp-123 --json           # Get next

# Math Registry
ont_experiments.py math list                     # Equations
ont_experiments.py stages                        # Pipeline stages
ont_experiments.py validate                      # Validate schemas
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ONT_REGISTRY_DIR` | Registry location | `~/.ont-registry` |
| `ONT_NO_GITHUB_SYNC` | Disable GitHub sync | `0` |
| `SLURM_JOB_ID` | HPC job ID | (auto) |
| `CUDA_VISIBLE_DEVICES` | GPU allocation | (auto) |
