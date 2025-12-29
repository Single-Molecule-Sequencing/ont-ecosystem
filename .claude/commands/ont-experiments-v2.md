---
description: Oxford Nanopore experiment management with event-sourced registry and provenance tracking. Use when discovering experiments, registering runs, tracking analysis history, or orchestrating multi-step pipelines with full audit trails.
---

# /ont-experiments-v2

Enhanced Oxford Nanopore experiment management with event-sourced registry and pipeline orchestration.

## Usage

Manage experiments with full provenance tracking:

$ARGUMENTS

## Quick Start

```bash
# Initialize registry
ont_experiments.py init --git --pipelines

# Discover experiments
ont_experiments.py discover /path/to/data --register

# Run analysis with provenance
ont_experiments.py run end_reasons exp-abc123 --json qc.json --plot qc.png

# View experiment history
ont_experiments.py history exp-abc123

# List experiments
ont_experiments.py list --tag clinical --status active
```

## Core Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize registry |
| `discover <dir>` | Scan for experiments |
| `register <dir>` | Add single experiment |
| `list` | List experiments |
| `info <id>` | Show details |
| `run <analysis> <id>` | Run analysis |
| `history <id>` | Show event history |

## Pipeline Commands

| Command | Description |
|---------|-------------|
| `pipeline list` | List pipelines |
| `pipeline run <name> <id>` | Execute pipeline |
| `pipeline resume <id>` | Resume from checkpoint |
| `pipeline status <id>` | Show status |

## Analysis Skills

Run any skill with provenance:
```bash
ont_experiments.py run end_reasons exp-abc123 --json qc.json
ont_experiments.py run basecalling exp-abc123 --model sup --output calls.bam
ont_experiments.py run alignment exp-abc123 --reference GRCh38
ont_experiments.py run variant_calling exp-abc123 --caller clair3
```

## Dual-Mode Operation

### HPC Mode (Full Features)
- Full read/write to local registry
- Experiment discovery and registration
- Pipeline execution

### GitHub Mode (Read-Only)
```bash
# Force GitHub mode
ont_experiments.py list --github
ont_experiments.py info exp-abc123 --github
```

## Event Tracking

All operations are logged:
```yaml
events:
  - timestamp: "2024-01-15T12:00:00Z"
    type: "analysis"
    analysis: "basecalling"
    command: "dorado basecaller..."
    results:
      total_reads: 15000000
      mean_qscore: 18.5
    hpc:
      job_id: "12345678"
      partition: "sigbio-a40"
```

## Dependencies

- pyyaml
- pod5
- h5py (optional)
- gitpython (optional)
