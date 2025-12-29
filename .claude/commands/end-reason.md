---
description: Analyze Oxford Nanopore read end reasons for adaptive sampling QC. Use when checking sequencing quality, analyzing end_reason metadata, diagnosing adaptive sampling efficiency, or processing POD5/Fast5 data.
---

# /end-reason

Oxford Nanopore read end reason QC analysis for adaptive sampling efficiency and sequencing quality assessment.

## Usage

Analyze end reasons from ONT sequencing data:

$ARGUMENTS

## End Reason Categories

| End Reason | Description | Expected % |
|------------|-------------|------------|
| `signal_positive` | Normal completion | 80-95% |
| `unblock_mux_change` | Adaptive sampling rejection | 0-15% |
| `data_service_unblock_mux_change` | Basecall-triggered rejection | 0-10% |
| `mux_change` | Pore mux change | 1-5% |
| `signal_negative` | Signal lost | <5% |

## Quality Assessment

| Status | Criteria |
|--------|----------|
| OK | signal_positive >= 75% |
| CHECK | signal_positive < 75% or anomalies |
| FAIL | signal_positive < 50% |

## Examples

```bash
# Basic analysis from POD5 directory
python3 skills/end-reason/scripts/end_reason.py /path/to/pod5 --json results.json

# Quick analysis (sample 10k reads)
python3 skills/end-reason/scripts/end_reason.py /path/to/data --quick

# Generate plot
python3 skills/end-reason/scripts/end_reason.py /path/to/data --plot qc.png

# With provenance tracking
ont_experiments.py run end_reasons exp-001 --json results.json --plot qc.png
```

## Options

| Option | Description |
|--------|-------------|
| `--json FILE` | Output JSON summary |
| `--csv FILE` | Output per-read CSV |
| `--plot FILE` | Output bar chart (PNG/PDF) |
| `--format FORMAT` | Force format (pod5, fast5, summary) |
| `--quick` | Sample 10k reads only |

## Supported Formats

- POD5 (fastest, recommended)
- Fast5 (legacy)
- sequencing_summary.txt

## Output JSON

```json
{
  "total_reads": 15000000,
  "quality_status": "OK",
  "signal_positive_pct": 90.0,
  "unblock_mux_pct": 8.0,
  "data_service_pct": 1.0,
  "end_reasons": {
    "signal_positive": {"count": 13500000, "pct": 90.0},
    "unblock_mux_change": {"count": 1200000, "pct": 8.0}
  }
}
```

## Installation

```bash
# Clone the repository
git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git

# Install dependencies
pip install pod5 pysam numpy

# Copy skill command to Claude
cp ont-ecosystem/installable-skills/end-reason/end-reason.md ~/.claude/commands/
```
