# ONT Ecosystem Tutorials

This guide provides step-by-step tutorials for common workflows in the ONT Ecosystem.

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Experiment Discovery & Registration](#2-experiment-discovery--registration)
3. [Running QC Analysis](#3-running-qc-analysis)
4. [Using Domain Memory](#4-using-domain-memory)
5. [Pipeline Workflows](#5-pipeline-workflows)
6. [HPC Integration](#6-hpc-integration)
7. [Math Registry Queries](#7-math-registry-queries)
8. [Agent Workflows](#8-agent-workflows)

---

## 1. Getting Started

### Installation

```bash
# One-line install
curl -sSL https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/install.sh | bash
source ~/.ont-ecosystem/env.sh

# Or clone and install manually
git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git
cd ont-ecosystem
make install
```

### Initialize Registry

```bash
# Create empty registry
ont_experiments.py init

# Create with Git tracking
ont_experiments.py init --git
```

### Verify Installation

```bash
# Check available commands
ont_experiments.py --help

# List pipeline stages
ont_experiments.py stages

# Run tests
pytest tests/ -v
```

---

## 2. Experiment Discovery & Registration

### Auto-Discovery

Scan directories for ONT experiments:

```bash
# Discover experiments in directory
ont_experiments.py discover /path/to/sequencing/data

# Discover and auto-register
ont_experiments.py discover /path/to/data --register

# Discover with tags
ont_experiments.py discover /path/to/data --register --tags "project1,batch1"
```

### Manual Registration

```bash
# Register single experiment
ont_experiments.py register /nfs/turbo/data/run_20240115 \
  --name "CYP2D6 Patient Cohort 1" \
  --tags "cyp2d6,clinical"

# Register with sample info
ont_experiments.py register /data/run_001 \
  --sample-id "HG002" \
  --platform "PromethION" \
  --kit "SQK-LSK114"
```

### Listing & Viewing

```bash
# List all experiments
ont_experiments.py list

# Filter by tag
ont_experiments.py list --tag cyp2d6

# Filter by status
ont_experiments.py list --status running

# View experiment details
ont_experiments.py info exp-abc123

# View full event history
ont_experiments.py history exp-abc123
```

---

## 3. Running QC Analysis

### End Reason Analysis

The end reason analysis examines why reads terminated:

```bash
# Basic QC
ont_experiments.py run end_reasons exp-abc123

# With JSON output
ont_experiments.py run end_reasons exp-abc123 --json results.json

# With visualization
ont_experiments.py run end_reasons exp-abc123 --json results.json --plot qc.png
```

**Quality Grades:**
- **A**: signal_positive > 90%, unblock < 5%
- **B**: signal_positive > 80%, unblock < 10%
- **C**: signal_positive > 70%, unblock < 15%
- **D**: Below grade C thresholds

### Enhanced QC with KDE

```bash
# Enhanced visualization
ont_experiments.py run endreason_qc exp-abc123

# Multi-zoom plot
python bin/ont_endreason_qc.py /path/to/experiment \
  --output kde_plot.png \
  --zoom-panels 3
```

### Run Monitoring

```bash
# Snapshot of current state
ont_experiments.py run monitoring exp-abc123 --snapshot

# Live monitoring during sequencing
ont_experiments.py run monitoring exp-abc123 --live --interval 60

# Historical analysis
ont_experiments.py run monitoring exp-abc123 --history
```

---

## 4. Using Domain Memory

Domain memory provides persistent task tracking for experiments.

### Initialize Domain Memory

```bash
# Create task backlog for experiment
ont_experiments.py init-tasks exp-abc123

# Initialize with experiment-specific CLAUDE.md
ont_experiments.py init-tasks exp-abc123 --claude-md
```

### View Tasks

```bash
# View task backlog with status
ont_experiments.py tasks exp-abc123

# Output:
# Tasks for CYP2D6 Run 1:
# --------------------------------------------------
#   ○ end_reasons: pending
#   ○ endreason_qc: pending (depends: end_reasons)
#   ○ basecalling: pending
#   ○ alignment: pending (depends: basecalling)
#   ○ pipeline: pending (depends: alignment)
#
# Recommendation: Next task: end_reasons
```

### Get Next Task (Agent-Friendly)

```bash
# Human-readable output
ont_experiments.py next exp-abc123

# Machine-readable JSON
ont_experiments.py next exp-abc123 --json
# {"task": "end_reasons", "status": "pending", "runnable": true, "command": "ont_experiments.py run end_reasons exp-abc123"}
```

### View Progress Log

```bash
# View progress log
ont_experiments.py progress exp-abc123

# Output:
# # Progress Log: CYP2D6 Run 1
#
# ## 2024-01-15 14:30 - end_reasons
# - ✓ Ran end_reasons
# - Exit code: 0
# - Duration: 45.2s
# - total_reads: 125000
# - quality_grade: A
```

### Task States

| State | Icon | Meaning |
|-------|------|---------|
| `pending` | ○ | Not yet started |
| `in_progress` | ◐ | Currently running |
| `passing` | ✓ | Completed successfully |
| `failing` | ✗ | Failed - needs attention |
| `skipped` | − | Manually skipped |

---

## 5. Pipeline Workflows

### Available Pipelines

```bash
# List available pipelines
ls examples/pipelines/

# pharmaco-clinical.yaml  - Clinical PGx workflow
# qc-fast.yaml            - Quick QC check
# research-full.yaml      - Full research analysis
```

### Running a Pipeline

```bash
# Run clinical pharmacogenomics pipeline
ont_experiments.py pipeline run pharmaco-clinical exp-abc123

# Run with specific output directory
ont_experiments.py pipeline run pharmaco-clinical exp-abc123 \
  --output /scratch/results

# Dry run to preview steps
ont_experiments.py pipeline run pharmaco-clinical exp-abc123 --dry-run
```

### Pipeline YAML Format

```yaml
# examples/pipelines/pharmaco-clinical.yaml
name: pharmaco-clinical
description: Clinical pharmacogenomics workflow
version: 1.0

steps:
  - name: qc
    skill: end_reasons
    required: true

  - name: basecall
    skill: basecalling
    args:
      - --model
      - sup@v5.0.0
    required: true
    depends_on: [qc]

  - name: align
    skill: alignment
    args:
      - --reference
      - hs1
    required: true
    depends_on: [basecall]
```

### Resume Failed Pipeline

```bash
# Resume from failure point
ont_experiments.py pipeline resume exp-abc123

# Skip failed step and continue
ont_experiments.py pipeline resume exp-abc123 --skip-failed
```

---

## 6. HPC Integration

### SLURM Job Generation

```bash
# Generate SLURM script for basecalling
dorado_basecall.py /path/to/pod5 \
  --model sup@v5.0.0 \
  --output calls.bam \
  --slurm job.sh \
  --partition spgpu \
  --gpu-type a100 \
  --time 24:00:00

# Submit job
sbatch job.sh
```

### HPC Configs

```yaml
# examples/configs/greatlakes.yaml
cluster: greatlakes
partitions:
  gpu: spgpu
  cpu: standard
gpu_types:
  - a40
  - a100
modules:
  - python/3.10
  - cuda/12.1
```

### Using Configs

```bash
# Apply Great Lakes config
dorado_basecall.py /path/to/pod5 \
  --config examples/configs/greatlakes.yaml \
  --model sup@v5.0.0 \
  --slurm job.sh
```

### Automatic HPC Metadata Capture

When running through `ont_experiments.py`, HPC metadata is automatically captured:

```bash
# Run on HPC cluster
sbatch --wrap="ont_experiments.py run basecalling exp-abc123 --model sup@v5.0.0"

# Event automatically includes:
# - job_id: 12345678
# - partition: spgpu
# - nodes: gpu-001
# - gpus: cuda:0,1
```

---

## 7. Math Registry Queries

### List Equations

```bash
# List all equations
ont_experiments.py math list

# List equations by stage
ont_experiments.py math list --stage r

# Search equations
ont_experiments.py math search "bayesian"
```

### Get Equation Details

```bash
# Get specific equation
ont_experiments.py math get eq_6_6

# Output:
# Equation: eq_6_6
# Name: Bayesian Posterior
# LaTeX: P(h|r) = \frac{P(r|h)P(h)}{\sum_{h'} P(r|h')P(h')}
# Stage: A
# Importance: critical
```

### Get LaTeX

```bash
# Get just the LaTeX
ont_experiments.py math latex eq_6_6
# P(h|r) = \frac{P(r|h)P(h)}{\sum_{h'} P(r|h')P(h')}
```

### Pipeline Stages

```bash
# List all stages
ont_experiments.py stages

# Get stage details
ont_experiments.py stage σ

# Output:
# Stage: σ (Signal Acquisition)
# Probability: P(σ|ℓ,A)
# Team: ONT Adaptive
# Skills: end-reason, ont-monitor
```

### Variable Lookup

```bash
# List variables
ont_experiments.py math variables list

# Get variable details
ont_experiments.py math variables get Q

# Output:
# Variable: Q
# Name: Phred Quality Score
# Domain: [0, 93]
# Description: -10 log₁₀(P_error)
```

---

## 8. Agent Workflows

For AI agents working with ONT Ecosystem:

### Bootup Ritual

Always start by reading current state:

```bash
# Get grounded context
ont_experiments.py next exp-abc123 --json

# Returns:
{
  "experiment_id": "exp-abc123",
  "experiment_name": "CYP2D6 Run 1",
  "pending_tasks": ["end_reasons", "basecalling"],
  "failing_tasks": [],
  "next_task": {
    "name": "end_reasons",
    "command": "ont_experiments.py run end_reasons exp-abc123",
    "runnable": true
  },
  "recommendation": "Run end_reasons analysis first"
}
```

### Execute Recommended Task

```bash
# Run the recommended task
ont_experiments.py run end_reasons exp-abc123 --json results.json

# Task status auto-updates
# Progress log auto-appends
```

### Handle Failures

```bash
# Check for failing tasks
ont_experiments.py tasks exp-abc123

# If failing:
#   ✗ end_reasons: failing
#       Error: No sequencing_summary.txt found

# Fix and retry
ont_experiments.py run end_reasons exp-abc123 --summary /alt/path/summary.txt
```

### Progress Tracking

```bash
# Append note to progress log
ont_experiments.py note exp-abc123 "Identified missing summary file, using alternate path"

# View full progress
ont_experiments.py progress exp-abc123
```

### Complete Workflow Example

```python
# Agent pseudocode
import subprocess
import json

def process_experiment(exp_id):
    while True:
        # Get next task
        result = subprocess.run(
            ["ont_experiments.py", "next", exp_id, "--json"],
            capture_output=True
        )
        ctx = json.loads(result.stdout)

        if not ctx["pending_tasks"] and not ctx["failing_tasks"]:
            print("All tasks complete!")
            break

        if ctx["failing_tasks"]:
            task = ctx["failing_tasks"][0]
            print(f"Fixing: {task['name']} - {task['error']}")
            # Handle failure...

        elif ctx["pending_tasks"]:
            task = ctx["next_task"]
            if task["runnable"]:
                print(f"Running: {task['command']}")
                subprocess.run(task["command"].split())
            else:
                print(f"Blocked: {task['name']} waiting for dependencies")
```

---

## Next Steps

- Read [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) for complete technical details
- Check [CLAUDE.md](../CLAUDE.md) for AI agent guidance
- Explore [examples/](../examples/) for configuration templates
- Run `pytest tests/ -v` to verify your installation
