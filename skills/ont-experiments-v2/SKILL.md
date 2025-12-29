---
name: ont-experiments-v2
description: Enhanced Oxford Nanopore experiment management with event-sourced registry, pipeline orchestration, unified QC aggregation, and GitHub-synced storage.
---

# ONT Experiments v2 - Enhanced Registry

Foundational tool for discovering, tracking, and orchestrating Oxford Nanopore sequencing experiments with improved pipeline integration.

## Dual-Mode Operation

This tool operates in two modes:

### HPC Mode (Full Features)
When running on HPC with local filesystem access:
- Full read/write to local registry (`~/.ont-registry/experiments.yaml`)
- Experiment discovery and registration
- Pipeline execution with provenance tracking
- QC and batch operations

### GitHub Mode (Read-Only)
When running remotely without HPC access:
- Fetches registry from GitHub automatically
- List, search, and view experiment details
- Always available - works anywhere with internet

```bash
# Force GitHub mode (useful for remote access)
ont_experiments.py list --github
ont_experiments.py info exp-abc123 --github

# Automatic fallback: if local registry doesn't exist, uses GitHub
ont_experiments.py list
```

## GitHub Registry

The canonical registry is synced to GitHub:
```
https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/registry/experiments.yaml
```

### Syncing Local Changes to GitHub
```bash
# On HPC after discovering/modifying experiments
cd ~/.ont-registry
git add experiments.yaml
git commit -m "Update experiments"
git push
```

## What's New in v2

### 1. Pipeline Integration
```bash
# Run multi-step pipelines with provenance tracking
ont_experiments.py pipeline run pharmaco-clinical exp-abc123

# Resume failed pipelines
ont_experiments.py pipeline resume exp-abc123

# View pipeline status
ont_experiments.py pipeline status exp-abc123
```

### 2. Unified QC Dashboard
```bash
# Generate comprehensive QC report
ont_experiments.py qc exp-abc123 --format html --output report.html

# Aggregate metrics from all analyses
ont_experiments.py qc exp-abc123 --summary
```

### 3. Batch Operations
```bash
# Run analysis on multiple experiments
ont_experiments.py batch end_reasons --tag clinical --parallel 4

# Generate batch report
ont_experiments.py batch-report --tag clinical --output batch_2025Q4.html
```

### 4. Enhanced History Queries
```bash
# Filter by analysis type
ont_experiments.py history exp-abc123 --filter analysis=basecalling

# Filter by date range
ont_experiments.py history exp-abc123 --since 2025-01-01 --until 2025-01-31

# Filter by HPC job
ont_experiments.py history exp-abc123 --job-id 48392571
```

### 5. Improved Data Discovery
```bash
# Recursive discovery with metadata enrichment
ont_experiments.py discover /data/sequencing --recursive --enrich

# Watch for new experiments
ont_experiments.py watch /data/sequencing --interval 60 --register
```

## Registry Location

**Local (HPC):** `~/.ont-registry/experiments.yaml` (git-initializable for sync)

**GitHub (Remote):** `https://github.com/Single-Molecule-Sequencing/ont-ecosystem/blob/main/registry/experiments.yaml`

The tool automatically uses GitHub as a fallback when local registry is unavailable.

## Quick Start

```bash
# Initialize registry with git and pipelines
ont_experiments.py init --git --pipelines

# Discover and register experiments
ont_experiments.py discover /path/to/sequencing/data --register

# Run full pipeline with provenance tracking
ont_experiments.py pipeline run pharmaco-clinical exp-abc123

# Generate comprehensive QC report
ont_experiments.py qc exp-abc123 --format html
```

## Commands

### Core Commands

| Command | Description |
|---------|-------------|
| `init [--git] [--pipelines]` | Initialize registry |
| `discover <dir> [--register]` | Scan for experiments |
| `register <dir>` | Add single experiment |
| `list [--tag] [--status] [--github]` | List experiments |
| `info <id> [--github]` | Show details |
| `run <analysis> <id> [args]` | Run analysis with logging |
| `history <id>` | Show event history |
| `export <id>` | Export commands as script |

### Pipeline Commands

| Command | Description |
|---------|-------------|
| `pipeline list` | List available pipelines |
| `pipeline show <name>` | Show pipeline definition |
| `pipeline run <name> <id>` | Execute pipeline |
| `pipeline resume <id>` | Resume from checkpoint |
| `pipeline status <id>` | Show execution status |

### QC Commands

| Command | Description |
|---------|-------------|
| `qc <id>` | Generate QC report |
| `qc <id> --summary` | Show metrics summary |
| `qc <id> --compare <id2>` | Compare two experiments |

### Batch Commands

| Command | Description |
|---------|-------------|
| `batch <analysis> --tag <tag>` | Run on tagged experiments |
| `batch-report --tag <tag>` | Generate batch summary |

## Event Schema (Enhanced)

```yaml
events:
  - timestamp: "2024-01-15T12:00:00Z"
    type: "analysis"
    analysis: "basecalling"
    
    # Pipeline context (NEW)
    pipeline:
      name: "pharmaco-clinical"
      version: "1.0"
      step: 2
      step_name: "basecalling"
    
    command: "dorado basecaller sup@v5.0.0 /path/to/pod5"
    parameters:
      model: "dna_r10.4.1_e8.2_400bps_sup@v5.0.0"
      model_path: "/nfs/turbo/umms-bleu-secure/programs/dorado_models/sup"
    
    outputs:
      - path: "/path/to/calls.bam"
        size_bytes: 48530000000
        checksum: "sha256:abc123"
    
    results:
      total_reads: 15000000
      mean_qscore: 18.5
      pass_criteria_met: true  # NEW
    
    duration_seconds: 3600
    exit_code: 0
    
    # Enhanced agent tracking
    agent: "claude-web"
    agent_session: "chat-abc123"  # NEW
    
    machine: "gl-login1.arc-ts.umich.edu"
    
    hpc:
      scheduler: "slurm"
      job_id: "12345678"
      partition: "sigbio-a40"
      nodes: ["arm003"]
      gpus: ["NVIDIA A40"]
      memory_gb: 100
      walltime_used: "02:15:33"
```

## Public Datasets (Enhanced)

35+ ONT Open Data datasets with improved categorization:

| Category | Count | Examples |
|----------|-------|----------|
| Human Reference | 5 | gm24385_2023.12, lc2024_t2t |
| GIAB Benchmarks | 4 | giab_2025.01, giab_2023.05 |
| Cancer/Clinical | 6 | hereditary_cancer_2025.09, colo829_2024.03 |
| Microbial | 8 | zymo_16s_2025.09, zymo_fecal_2025.05 |
| Pathogen | 5 | pathogen_surveillance_2025.09 |
| Methylation | 4 | methylation_standards_2025.03 |
| RNA | 3 | direct_rna_2024.06 |

```bash
# List by category
ont_experiments.py public --category cancer

# Search datasets
ont_experiments.py public --search "HG002"

# Fetch with auto-register
ont_experiments.py fetch giab_2025.01 /dest --register --verify
```

## HPC Integration (Enhanced)

### SLURM Auto-Detection
```yaml
hpc:
  scheduler: "slurm"
  job_id: "12345678"
  job_name: "ont-basecall-exp123"
  partition: "sigbio-a40"
  account: "bleu1"
  nodes: ["arm003"]
  gpus: ["NVIDIA A40"]
  cpus_allocated: 16
  memory_allocated_gb: 100
  walltime_requested: "72:00:00"
  walltime_used: "02:15:33"
  exit_state: "COMPLETED"
```

### Job Correlation
```bash
# Find experiment by SLURM job ID
ont_experiments.py find --job-id 12345678

# Cross-reference with sacct
ont_experiments.py history exp-abc123 --sacct
```

## Integration Patterns

### Pattern A: Direct Execution
Analysis skills write directly to output files.
```bash
python3 end_reason.py /path/to/data --json results.json
```

### Pattern B: Orchestrated Execution (Recommended)
ont-experiments wraps analysis skills, capturing provenance.
```bash
ont_experiments.py run end_reasons exp-abc123 --json qc.json
```

### Pattern C: Pipeline Execution (NEW)
Multi-step workflows with unified tracking.
```bash
ont_experiments.py pipeline run pharmaco-clinical exp-abc123
```

## Configuration

Registry configuration in `~/.ont-registry/config.yaml`:

```yaml
# Default paths
paths:
  dorado: /nfs/turbo/umms-bleu-secure/programs/dorado-1.1.1-linux-x64/bin/dorado
  models: /nfs/turbo/umms-bleu-secure/programs/dorado_models
  references: /nfs/turbo/umms-bleu-secure/references

# HPC defaults
hpc:
  default_cluster: armis2
  account: bleu1
  
# Agent tracking
agent:
  name: claude-web
  track_sessions: true
  
# Notifications (optional)
notifications:
  slack_webhook: null
  email: null
```

## Migration from v1

```bash
# Backup existing registry
cp ~/.ont-registry/experiments.yaml ~/.ont-registry/experiments.yaml.bak

# Migrate to v2 format
ont_experiments.py migrate --from-v1

# Verify migration
ont_experiments.py list
```

## Dependencies

```
pyyaml>=6.0          # Registry format
pod5>=0.3.0          # POD5 support (recommended)
h5py>=3.0.0          # Fast5 support (optional)
gitpython>=3.1       # Git integration (optional)
jinja2>=3.0          # Report templating (optional)
pandas>=1.5          # Metrics aggregation (optional)
```
