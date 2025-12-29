# ONT Ecosystem Quick Start Guide

## Installation

### One-line Install

```bash
curl -sSL https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/install.sh | bash
source ~/.ont-ecosystem/env.sh
```

### HPC Installation

```bash
module load python/3.10
./install.sh --hpc
source ~/.ont-ecosystem/env.sh
```

## First Steps

### 1. Initialize the Registry

```bash
ont_experiments.py init --git
```

This creates `~/.ont-registry/` with git tracking.

### 2. Discover Experiments

```bash
ont_experiments.py discover /path/to/sequencing/runs --register
```

### 3. List Experiments

```bash
ont_experiments.py list
ont_experiments.py list --tags cyp2d6
```

### 4. Run Analysis

```bash
# QC analysis
ont_experiments.py run end_reasons exp-abc123 --json qc.json

# Basecalling
ont_experiments.py run basecalling exp-abc123 --model sup@v5.0.0 --output calls.bam

# Alignment
ont_experiments.py run alignment exp-abc123 --reference GRCh38 --output aligned.bam
```

### 5. View History

```bash
ont_experiments.py history exp-abc123
```

## Key Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize registry |
| `discover` | Find experiments |
| `register` | Manually register |
| `list` | List experiments |
| `info` | Show experiment details |
| `run` | Run analysis skill |
| `history` | View event history |
| `pipeline` | Run multi-step workflow |
| `public` | List public datasets |

## Getting Help

```bash
ont_experiments.py --help
ont_experiments.py run --help
ont_align.py --help
```
