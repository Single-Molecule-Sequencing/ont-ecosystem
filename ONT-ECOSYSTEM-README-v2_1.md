# ONT Experiment Ecosystem v2.1

A comprehensive skill ecosystem for Oxford Nanopore sequencing experiment management with **full provenance tracking** and **event-sourced registry**.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     ont-experiments (CORE)                       │
│  • Event-sourced registry (~/.ont-registry/)                     │
│  • Experiment discovery & metadata extraction                    │
│  • Pattern B orchestration (wraps analysis skills)               │
│  • Public dataset access (30+ datasets)                          │
│  • HPC/SLURM metadata capture                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
    ┌─────────────┬───────────┼───────────┬─────────────┐
    ▼             ▼           ▼           ▼             ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│end-reason│ │dorado-  │ │ont-align│ │ont-     │ │ future  │
│(QC)     │ │bench    │ │(align)  │ │monitor  │ │(variant)│
│         │ │(basecall)│ │         │ │         │ │         │
└─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
```

## Skills Overview

| Skill | Description | Key Features |
|-------|-------------|--------------|
| **ont-experiments** | Core registry & orchestration | Event sourcing, Pattern B, HPC metadata |
| **end-reason** | Read end reason QC | Adaptive sampling analysis, quality status |
| **dorado-bench** | Basecalling workflows | Model management, SLURM generation |
| **ont-align** | Alignment & reference mgmt | minimap2/dorado, coverage metrics |
| **ont-monitor** | Run monitoring | Live dashboard, time-series, alerts |

## Quick Start

```bash
# 1. Initialize registries
ont_experiments.py init --git
ont_align.py refs init

# 2. Discover and register experiments
ont_experiments.py discover /nfs/turbo/athey-lab/runs --register

# 3. Add reference genomes
ont_align.py refs add /path/to/hs1.fa --name hs1

# 4. Monitor active run
ont_experiments.py run monitoring exp-abc123 --live

# 5. Run QC analysis
ont_experiments.py run end_reasons exp-abc123 --json qc.json

# 6. Basecall with SUP model
ont_experiments.py run basecalling exp-abc123 \
  --model sup@v5.0.0 --output calls.bam

# 7. Align to reference
ont_experiments.py run alignment exp-abc123 \
  --ref hs1 --output aligned.bam --coverage cov.bed

# 8. View complete history
ont_experiments.py history exp-abc123
```

## Pattern B: Centralized Orchestration

All analysis skills integrate through `ont-experiments`:

```bash
# ✗ Old way (no provenance)
end_reason.py /data/exp --json results.json
ont_monitor.py /data/exp --json metrics.json
ont_align.py align reads.bam --ref hg38 --output aligned.bam

# ✓ New way (full provenance)
ont_experiments.py run end_reasons exp-abc123 --json results.json
ont_experiments.py run monitoring exp-abc123 --json metrics.json
ont_experiments.py run alignment exp-abc123 --ref hg38 --output aligned.bam
```

This captures automatically:
- Full command with parameters
- Output file checksums
- Duration and exit code
- HPC metadata (SLURM job ID, nodes, GPUs)
- Results summary in registry
- Agent tracking (claude-web, claude-code, manual)

## Analysis Skills Configuration

Add to `ANALYSIS_SKILLS` in `ont_experiments.py`:

```python
ANALYSIS_SKILLS = {
    "end_reasons": {
        "script": "end_reason.py",
        "description": "Read end reason QC analysis",
        "result_fields": ["total_reads", "quality_status", "signal_positive_pct"],
        "input_mode": "location",
    },
    "basecalling": {
        "script": "dorado_basecall.py",
        "description": "Dorado basecalling",
        "result_fields": ["total_reads", "pass_reads", "mean_qscore", "n50"],
        "input_mode": "location",
        "capture_model_path": True,
    },
    "alignment": {
        "script": "ont_align.py align",
        "description": "Alignment to reference",
        "result_fields": ["total_reads", "mapped_reads", "mapping_rate", "mean_mapq"],
        "input_mode": "explicit",
    },
    "monitoring": {
        "script": "ont_monitor.py",
        "description": "Run monitoring and metrics",
        "result_fields": ["total_reads", "total_bases", "mean_qscore", "n50", "is_active"],
        "input_mode": "location",
    },
}
```

## Registries

### Experiment Registry (`~/.ont-registry/`)

Tracks experiments with full event history:
- Discovery and registration events
- Analysis runs with parameters and results
- Tags, status changes, notes
- Git-friendly for sync across machines

### Reference Registry (`~/.ont-references/`)

Tracks reference genomes:
- Path and checksum verification
- Index status (minimap2 .mmi)
- Aliases for convenience
- Auto-discovery from common paths

## Skill Files

| File | Description | Size |
|------|-------------|------|
| `ont-experiments.skill` | Core registry + orchestration | ~18KB |
| `end-reason.skill` | End reason QC analysis | ~8KB |
| `dorado-bench.skill` | Basecalling with model tracking | ~54KB |
| `ont-align.skill` | Alignment + reference management | ~50KB |
| `ont-monitor.skill` | Run monitoring + dashboards | ~55KB |

## Installation

```bash
# Copy .skill files to skills directory
# Install Python dependencies
pip install pyyaml pod5 h5py matplotlib pandas pysam numpy

# Ensure external tools are in PATH
which minimap2 samtools dorado
```

## Complete CYP2D6 Workflow

```bash
# 1. Register new PromethION run
ont_experiments.py register /nfs/turbo/athey-lab/runs/20240115 \
  --tags "cyp2d6,patient_cohort,batch1"

# 2. Monitor during sequencing
ont_experiments.py run monitoring exp-20240115 --live --interval 60

# 3. QC check after completion
ont_experiments.py run end_reasons exp-20240115 \
  --json qc.json --plot qc.png

# 4. Basecall with SUP model on HPC
sbatch --partition=sigbio-a40 --gres=gpu:a40:1 --mem=100G --time=72:00:00 --wrap="\
  ont_experiments.py run basecalling exp-20240115 \
    --model sup@v5.0.0 \
    --output /scratch/basecalled.bam \
    --json basecall_stats.json"

# 5. Align to T2T reference
ont_experiments.py run alignment exp-20240115 \
  --ref hs1 \
  --output /scratch/aligned.bam \
  --coverage coverage.bed \
  --json alignment_stats.json

# 6. Review complete history
ont_experiments.py history exp-20240115

# 7. Export for documentation
ont_experiments.py export exp-20240115 > analysis_commands.sh
```

## Author

Built for the Athey SMS Lab, University of Michigan
