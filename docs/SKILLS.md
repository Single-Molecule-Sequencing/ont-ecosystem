# ONT Ecosystem Skills

## Overview

Skills are modular analysis components that integrate with the core registry through Pattern B orchestration.

## Available Skills

### ont-experiments-v2 (Core)

The central orchestration hub. All other skills run through this for provenance tracking.

```bash
ont_experiments.py run <skill> <experiment_id> [options]
```

### ont-align

Alignment and sequence comparison.

- minimap2 and Dorado aligner support
- Reference genome registry
- BAM QC statistics
- **Levenshtein edit distance** using edlib

```bash
# Alignment
ont_experiments.py run alignment exp-abc123 --reference GRCh38

# Edit distance
ont_align.py editdist "ACGT" "ACTT" --cigar
```

### ont-pipeline

Multi-step workflow orchestration.

- YAML-defined pipelines
- Checkpoint/resume
- Unified QC reports

```bash
ont_experiments.py pipeline run pharmaco-clinical exp-abc123
```

### end-reason

Read end reason QC analysis.

- Adaptive sampling efficiency
- Quality thresholds

```bash
ont_experiments.py run end_reasons exp-abc123 --json qc.json
```

### dorado-bench-v2

GPU-accelerated basecalling.

- Model management
- SLURM job generation
- Resource optimization

```bash
ont_experiments.py run basecalling exp-abc123 --model sup@v5.0.0
```

### ont-monitor

Real-time run monitoring.

- Live dashboards
- Time-series analysis
- Alerts

```bash
ont_experiments.py run monitoring exp-abc123 --live
```

## Using Skills with Claude

Upload `.skill` files to Claude Projects:

1. Go to Claude Projects
2. Add skill files from `skills/` directory
3. Claude can now assist with ONT analysis

## Creating Custom Skills

See the skill template in `docs/SKILL_TEMPLATE.md`.
