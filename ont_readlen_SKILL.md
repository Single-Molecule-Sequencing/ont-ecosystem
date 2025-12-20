---
name: ont-readlen
description: "Oxford Nanopore read length distribution analysis and visualization. Use when analyzing read length distributions, comparing N50/mean/median across experiments, generating histograms and violin plots, assessing library quality, or evaluating size selection. Integrates with ont-experiments for provenance tracking via Pattern B orchestration. Supports sequencing_summary.txt, BAM, FASTQ, and POD5 inputs."
license: MIT
repository: https://github.com/Single-Molecule-Sequencing/ont-ecosystem
---

# ONT Read Length Distribution - Analysis & Visualization

## Overview

Comprehensive read length distribution analysis for Oxford Nanopore sequencing data. Computes statistics (N50, mean, median, percentiles), generates publication-quality visualizations, and supports multi-experiment comparison.

### Key Capabilities

1. **Statistics Computation**: N50, N90, mean, median, std, percentiles, length thresholds
2. **Multi-Experiment Comparison**: Overlay plots, violin plots, bar charts
3. **Multiple Data Sources**: sequencing_summary.txt, BAM, FASTQ, POD5
4. **Quality Assessment**: Evaluate size selection, library prep quality
5. **Pattern B Integration**: Automatic provenance tracking via ont-experiments

## Installation

Part of the ONT Ecosystem:

```bash
curl -sSL https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/install.sh | bash
source ~/.ont-ecosystem/env.sh
```

### Dependencies

```bash
# Required
pip install numpy

# For BAM files
pip install pysam

# For POD5 files (optional)
pip install pod5

# For visualization
pip install matplotlib
```

## Quick Start

```bash
# Single experiment analysis
ont_readlen.py /path/to/run --json stats.json --plot dist.png

# Multi-experiment comparison
ont_readlen.py exp1/ exp2/ exp3/ --plot comparison.png --plot-type overlay

# With provenance tracking (recommended)
ont_experiments.py run readlen exp-abc123 --json stats.json --plot dist.png

# Quick preview (subset of reads)
ont_readlen.py /path/to/run --max-reads 100000 --plot preview.png

# Compare all experiments in registry
ont_experiments.py list --format ids | xargs ont_readlen.py --plot all_comparison.png
```

## Commands Reference

### Basic Analysis

```bash
# Analyze from run directory (auto-detects source)
ont_readlen.py /path/to/run

# Analyze specific file
ont_readlen.py sequencing_summary.txt
ont_readlen.py aligned.bam
ont_readlen.py reads.fastq.gz
ont_readlen.py signal.pod5

# Force specific source type
ont_readlen.py /path/to/data --source-type bam
```

### Output Options

```bash
# JSON output with full statistics
ont_readlen.py /path/to/run --json stats.json

# CSV summary for spreadsheet
ont_readlen.py /path/to/run --csv summary.csv

# Plot visualization
ont_readlen.py /path/to/run --plot dist.png

# All outputs
ont_readlen.py /path/to/run --json stats.json --csv summary.csv --plot dist.png
```

### Multi-Experiment Comparison

```bash
# Compare multiple experiments
ont_readlen.py exp1/ exp2/ exp3/ --json comparison.json --plot comparison.png

# Different plot types
ont_readlen.py exp1/ exp2/ exp3/ --plot comp.png --plot-type overlay   # Overlaid histograms
ont_readlen.py exp1/ exp2/ exp3/ --plot comp.png --plot-type violin    # Violin/box plots
ont_readlen.py exp1/ exp2/ exp3/ --plot comp.png --plot-type bar       # Bar chart metrics

# Normalized comparison (percentage instead of counts)
ont_readlen.py exp1/ exp2/ exp3/ --plot comp.png --normalize
```

### Plot Customization

```bash
# Custom title
ont_readlen.py /path/to/run --plot dist.png --title "CYP2D6 Library Read Lengths"

# Adjust x-axis maximum
ont_readlen.py /path/to/run --plot dist.png --max-length 100000

# Log scale y-axis
ont_readlen.py /path/to/run --plot dist.png --log-scale
```

### Pattern B Integration

```bash
# Run via ont-experiments for provenance tracking
ont_experiments.py run readlen exp-abc123 \
  --json stats.json \
  --plot dist.png

# View in history
ont_experiments.py history exp-abc123
```

## Statistics Computed

### Core Metrics

| Metric | Description |
|--------|-------------|
| `total_reads` | Total number of reads |
| `total_bases` | Sum of all read lengths |
| `mean_length` | Arithmetic mean of read lengths |
| `median_length` | 50th percentile length |
| `std_length` | Standard deviation |
| `min_length` | Shortest read |
| `max_length` | Longest read |

### NX Statistics

| Metric | Description |
|--------|-------------|
| `n50` | Length where 50% of bases are in reads â‰¥ this length |
| `n90` | Length where 90% of bases are in reads â‰¥ this length |
| `l50` | Number of reads needed to reach N50 |

### Percentiles

| Metric | Description |
|--------|-------------|
| `q1_length` | 25th percentile (first quartile) |
| `q3_length` | 75th percentile (third quartile) |

### Threshold Counts

| Metric | Description |
|--------|-------------|
| `reads_gt_1kb` | Reads â‰¥ 1,000 bp |
| `reads_gt_5kb` | Reads â‰¥ 5,000 bp |
| `reads_gt_10kb` | Reads â‰¥ 10,000 bp |
| `reads_gt_20kb` | Reads â‰¥ 20,000 bp |
| `reads_gt_50kb` | Reads â‰¥ 50,000 bp |
| `reads_gt_100kb` | Reads â‰¥ 100,000 bp |
| `pct_gt_*` | Percentage versions of above |

## JSON Output Format

```json
{
  "version": "2.1",
  "timestamp": "2025-01-15T12:00:00Z",
  "experiments_count": 3,
  "experiments": [
    {
      "experiment_id": "exp-001",
      "experiment_name": "CYP2D6_cohort_batch1",
      "source_file": "/path/to/sequencing_summary.txt",
      "total_reads": 15000000,
      "total_bases": 75000000000,
      "mean_length": 5000.0,
      "median_length": 4200.0,
      "std_length": 3500.0,
      "min_length": 200,
      "max_length": 125000,
      "n50": 8500,
      "n90": 2100,
      "l50": 2850000,
      "q1_length": 2100.0,
      "q3_length": 6800.0,
      "reads_gt_1kb": 13500000,
      "reads_gt_5kb": 6000000,
      "reads_gt_10kb": 2250000,
      "reads_gt_20kb": 450000,
      "reads_gt_50kb": 45000,
      "reads_gt_100kb": 1500,
      "pct_gt_1kb": 90.0,
      "pct_gt_5kb": 40.0,
      "pct_gt_10kb": 15.0,
      "histogram_bins": [0, 1000, 2000, ...],
      "histogram_counts": [50000, 450000, 680000, ...],
      "timestamp": "2025-01-15T12:00:00Z"
    }
  ]
}
```

## Dashboard Display

```
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘              Read Length Distribution Analysis                     â•‘
â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£
â•‘ Experiment: CYP2D6_cohort_batch1                                  â•‘
â•‘ Source: sequencing_summary_FAW12345.txt                           â•‘
â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£
â•‘ SUMMARY                                                            â•‘
â•‘ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€  â•‘
â•‘ Total Reads:   15,000,000    â”‚  Mean Length:    5,000 bp          â•‘
â•‘ Total Bases:   75.0 Gb       â”‚  Median Length:  4,200 bp          â•‘
â•‘ N50:           8,500 bp      â”‚  Max Length:     125,000 bp        â•‘
â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£
â•‘ LENGTH DISTRIBUTION                                                â•‘
â•‘ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€  â•‘
â•‘ >1kb:   90.0%  â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆ           â•‘
â•‘ >5kb:   40.0%  â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆ                                   â•‘
â•‘ >10kb:  15.0%  â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆ                                             â•‘
â•‘ >20kb:   3.0%  â–ˆ                                                  â•‘
â•‘ >50kb:   0.3%  â–                                                  â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
```

## Plot Types

### 1. Single Histogram

```bash
ont_readlen.py experiment/ --plot histogram.png
```

- Bar histogram of read length distribution
- Vertical lines for mean, median, N50
- Statistics box with key metrics
- Suitable for single experiment analysis

### 2. Overlay Plot

```bash
ont_readlen.py exp1/ exp2/ exp3/ --plot overlay.png --plot-type overlay
```

- Multiple distributions overlaid
- Each experiment as a different color
- Legend with N50 values
- Good for comparing similar experiments

### 3. Violin/Box Plot

```bash
ont_readlen.py exp1/ exp2/ exp3/ --plot violin.png --plot-type violin
```

- Side-by-side box plots
- Shows quartiles, median, whiskers
- Mean marked with diamond
- Good for comparing distributions visually

### 4. Bar Chart Comparison

```bash
ont_readlen.py exp1/ exp2/ exp3/ --plot bar.png --plot-type bar
```

- 4-panel comparison chart
- Panels: N50, Mean Length, Total Reads, % >10kb
- Color-coded by experiment
- Good for presentations and reports

## Data Sources

### sequencing_summary.txt (Recommended)

- Fastest source (pre-computed)
- Contains `sequence_length_template` column
- Generated by MinKNOW during basecalling
- Supports gzipped files (.txt.gz)

```bash
ont_readlen.py sequencing_summary_FAW12345_abc123.txt
```

### BAM/SAM Files

- From basecalled/aligned reads
- Extracts query_length from each read
- Skips secondary/supplementary alignments
- Requires pysam

```bash
ont_readlen.py aligned.bam --source-type bam
```

### FASTQ Files

- Direct from basecaller output
- Parses sequence length from each record
- Supports gzipped files
- Slower for large files

```bash
ont_readlen.py reads.fastq.gz
```

### POD5 Files

- Raw signal files
- **Estimates** length from signal duration
- Not basecalled - approximation only
- Requires pod5 library

```bash
ont_readlen.py signal.pod5 --source-type pod5
```

## Use Cases

### Library QC

Evaluate library preparation quality:

```bash
ont_readlen.py /path/to/run --json qc.json

# Check N50 and % >10kb
# Good library: N50 >5kb, >10kb% >20%
# Poor library: N50 <2kb, >10kb% <5%
```

### Size Selection Assessment

Compare before/after size selection:

```bash
ont_readlen.py pre_selection/ post_selection/ \
  --plot selection_effect.png \
  --plot-type overlay \
  --title "Size Selection Effect"
```

### Protocol Comparison

Compare different library prep protocols:

```bash
ont_readlen.py rapid_kit/ ligation_kit/ ultra_long/ \
  --plot protocols.png \
  --plot-type bar \
  --json protocol_comparison.json
```

### Batch QC Report

Generate report for all experiments:

```bash
# Get all experiment paths
ont_experiments.py list --canonical --format paths > experiments.txt

# Analyze all
cat experiments.txt | xargs ont_readlen.py \
  --json batch_readlen.json \
  --csv batch_summary.csv \
  --plot batch_comparison.png \
  --plot-type bar
```

### Time-Course Analysis

Track read length over multiple runs:

```bash
ont_readlen.py run_day1/ run_day2/ run_day3/ run_day4/ run_day5/ \
  --plot timecourse.png \
  --plot-type bar \
  --title "Read Length Trend Over Time"
```

## Python API

```python
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/path/to/ont-ecosystem/bin')
from ont_readlen import (
    analyze_experiment, 
    compute_stats,
    plot_multi_comparison,
    generate_summary_table
)

# Analyze single experiment
stats = analyze_experiment('/path/to/run', experiment_id='exp-001')
print(f"N50: {stats.n50:,} bp")
print(f"Mean: {stats.mean_length:,.0f} bp")
print(f">10kb: {stats.pct_gt_10kb:.1f}%")

# Analyze multiple experiments
all_stats = []
for run_path in ['/path/to/exp1', '/path/to/exp2', '/path/to/exp3']:
    stats = analyze_experiment(run_path)
    all_stats.append(stats)

# Print summary table
print(generate_summary_table(all_stats))

# Generate comparison plot
plot_multi_comparison(
    all_stats,
    output_path='comparison.png',
    plot_type='overlay',
    title='Multi-Experiment Comparison'
)

# Export to JSON
import json
output = {
    "experiments": [s.to_dict() for s in all_stats]
}
with open('comparison.json', 'w') as f:
    json.dump(output, f, indent=2)
```

## Integration with ont-experiments

### Add to ANALYSIS_SKILLS

```python
ANALYSIS_SKILLS = {
    # ... existing skills ...
    "readlen": {
        "script": "ont_readlen.py",
        "description": "Read length distribution analysis",
        "result_fields": ["total_reads", "n50", "mean_length", "pct_gt_10kb"],
        "input_mode": "location",
    },
}
```

### Pattern B Usage

```bash
# Run via ont-experiments
ont_experiments.py run readlen exp-abc123 \
  --json readlen.json \
  --plot readlen.png

# Results captured in registry
ont_experiments.py history exp-abc123
```

### Registry Event

```yaml
events:
  - timestamp: "2025-01-15T12:00:00Z"
    type: analysis
    analysis: readlen
    command: "ont_readlen.py /path/to/run --json readlen.json --plot readlen.png"
    parameters:
      output_json: readlen.json
      output_plot: readlen.png
    outputs:
      - path: /path/to/readlen.json
        checksum: sha256:abc123...
      - path: /path/to/readlen.png
        checksum: sha256:def456...
    results:
      total_reads: 15000000
      n50: 8500
      mean_length: 5000.0
      pct_gt_10kb: 15.0
    duration_seconds: 45
    exit_code: 0
```

## Troubleshooting

### No Data Found

```bash
# Check for expected files
ls -la /path/to/run/sequencing_summary*.txt
ls -la /path/to/run/*.bam
ls -la /path/to/run/fastq_pass/*.fastq.gz

# Run in verbose mode
ont_readlen.py /path/to/run 2>&1 | head
```

### Missing Dependencies

```bash
# Check available libraries
python3 -c "import numpy; print('numpy OK')"
python3 -c "import matplotlib; print('matplotlib OK')"
python3 -c "import pysam; print('pysam OK')"
```

### Memory Issues

```bash
# Use max-reads limit for large datasets
ont_readlen.py /path/to/large_run --max-reads 1000000

# Or process specific summary file
ont_readlen.py /path/to/run/sequencing_summary.txt
```

## Quality Thresholds Reference

### Typical Values by Library Type

| Library Type | Expected N50 | Expected >10kb |
|--------------|--------------|----------------|
| Standard ligation | 5-15 kb | 15-40% |
| Rapid kit | 3-8 kb | 10-25% |
| Ultra-long | 20-50 kb | 40-70% |
| PCR-amplicon | 0.5-2 kb | <5% |
| cDNA | 1-3 kb | 5-15% |

### QC Thresholds

| Metric | Good | Acceptable | Poor |
|--------|------|------------|------|
| N50 | >10 kb | 5-10 kb | <5 kb |
| Mean | >5 kb | 2-5 kb | <2 kb |
| >10kb | >30% | 15-30% | <15% |
| Max | >50 kb | 20-50 kb | <20 kb |

## Related Skills

- **ont-experiments**: Core registry (run readlen via Pattern B)
- **ont-monitor**: Run monitoring including read stats
- **end-reason**: Read end reason QC
- **ont-align**: Alignment statistics

## Author

Single Molecule Sequencing Lab, Athey Lab, University of Michigan
