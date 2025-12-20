---
name: ont-readlen-endreason
description: Combined Oxford Nanopore read length + end reason analysis with semi-transparent overlaid distributions, cross-experiment correlation plots, and comprehensive QC statistics. Use when analyzing nanopore sequencing quality, comparing library preparations with adaptive sampling, investigating read termination patterns vs read length, or generating publication-quality combined QC figures. Integrates with ont-experiments for provenance tracking via Pattern B orchestration.
---

# Combined Read Length + End Reason Analysis

Publication-quality analysis combining read length distributions with end reason classification for Oxford Nanopore sequencing data.

## Quick Start

```bash
# Single experiment - semi-transparent distributions by end reason
python3 ont_readlen_endreason.py /path/to/run --plot-by-endreason dist.png

# Multi-experiment comparison (end reason freq vs mean size)
python3 ont_readlen_endreason.py exp1/ exp2/ exp3/ --plot-summary summary.png

# Detailed 4-panel analysis
python3 ont_readlen_endreason.py /path/to/run --plot-detailed detailed.png

# Full analysis with all outputs
python3 ont_readlen_endreason.py /path/to/run \
    --json stats.json \
    --plot-by-endreason dist.png \
    --plot-detailed detailed.png
```

## Key Features

- **Semi-transparent overlays**: See how read length distributions differ by end reason class
- **Cross-experiment correlations**: Plot end reason frequency vs mean read size across experiments  
- **Combined statistics**: N50, mean, median computed per end reason class
- **Adaptive sampling QC**: Visualize signal_positive vs unblock reads
- **Publication quality**: 300 DPI default, customizable colors and styling

## Visualizations

### 1. Semi-Transparent Distribution Plot (`--plot-by-endreason`)

Overlays read length histograms for each end reason class with transparency:
- **Blue (signal_positive)**: Normal completion - typically shows full size distribution
- **Red (unblock_mux_change)**: Adaptive sampling rejections - typically shorter reads
- **Orange (data_service_unblock)**: Basecall-triggered rejections
- **Purple (mux_change)**: Pore mux changes
- **Gray (signal_negative)**: Signal lost

### 2. Cross-Experiment Summary (`--plot-summary`)

4-panel comparison across multiple experiments:
- **Top-left**: Stacked bar chart of end reason percentages
- **Top-right**: Mean read length colored by QC status (OK/CHECK/FAIL)
- **Bottom-left**: Scatter plot of Signal Positive % vs Mean Length
- **Bottom-right**: N50 comparison by end reason class (grouped bars)

### 3. Detailed 4-Panel (`--plot-detailed`)

Single-experiment deep-dive:
- **Top-left**: Linear-scale overlaid distributions
- **Top-right**: Log-scale overlaid distributions (see rare events)
- **Bottom-left**: End reason pie chart
- **Bottom-right**: N50 horizontal bar by end reason

## CLI Reference

```
ont_readlen_endreason.py [paths...] [options]

Plotting Options:
  --plot-by-endreason, -p FILE   Semi-transparent distributions by end reason
  --plot-summary, -s FILE        Cross-experiment summary (4-panel)
  --plot-detailed, -d FILE       Detailed single-experiment analysis

Output Options:
  --json, -j FILE                JSON output with all statistics
  --csv FILE                     CSV summary table

Display Options:
  --dpi INT                      Resolution (default: 300)
  --alpha FLOAT                  Transparency 0-1 (default: 0.4)
  --log-y                        Log y-axis for distributions
  --title TEXT                   Custom plot title

Data Options:
  --max-reads INT                Limit reads for quick preview
  --source-type TYPE             Force: sequencing_summary|pod5
  --quiet, -q                    Suppress console output
```

## Statistics Output

### Per-Experiment Statistics

| Metric | Description |
|--------|-------------|
| total_reads | Total reads analyzed |
| mean_length | Overall mean read length |
| n50, n90 | Assembly-style metrics |
| signal_positive_pct | Percentage of normal completions |
| quality_status | OK (>=75%), CHECK (50-75%), FAIL (<50%) |

### Per End-Reason Statistics

| Metric | Description |
|--------|-------------|
| count | Number of reads in class |
| pct | Percentage of total reads |
| mean_length | Mean length for this class |
| median_length | Median length for this class |
| n50 | N50 for reads in this class |
| length_counts | BP-level frequency data |

## End Reason Categories

| End Reason | Description | Expected % | Typical Read Size |
|------------|-------------|------------|-------------------|
| signal_positive | Normal completion | 80-95% | Full distribution |
| unblock_mux_change | Adaptive sampling rejection | 0-15% | Short (rejected early) |
| data_service_unblock | Basecall-triggered rejection | 0-10% | Short-medium |
| mux_change | Pore mux change | 1-5% | Variable |
| signal_negative | Signal lost | <5% | Variable |

## Quality Assessment

| Status | Criteria | Action |
|--------|----------|--------|
| OK | signal_positive >=75% | Normal operation |
| CHECK | signal_positive 50-75% | Review adaptive sampling settings |
| FAIL | signal_positive <50% | Investigate run problems |

## Interpretation Guide

### Normal Library (No Adaptive Sampling)
- **Expected**: >90% signal_positive
- **Read lengths**: All end reasons should have similar distributions
- **N50 pattern**: Similar across all classes

### Adaptive Sampling Run
- **Expected**: 20-30% unblock reads (depending on target/non-target ratio)
- **Read lengths**: unblock reads should be SHORT (rejected early)
- **N50 pattern**: signal_positive >> unblock_mux_change N50

### Troubleshooting Patterns

| Pattern | Likely Cause |
|---------|--------------|
| Low signal_positive, high unblock | Aggressive adaptive sampling |
| Similar N50 across all classes | Adaptive sampling not working effectively |
| High mux_change | Pore health issues |
| High signal_negative | Flow cell problems |

## Python API

```python
from ont_readlen_endreason import (
    analyze_experiment, 
    plot_by_end_reason,
    plot_multi_experiment_summary,
    plot_detailed_4panel
)

# Analyze single experiment
stats = analyze_experiment("/path/to/run")
print(f"Signal Positive: {stats.signal_positive_pct:.1f}%")
print(f"Quality Status: {stats.quality_status}")

# Per-class statistics
for er_name, er_stats in stats.end_reason_stats.items():
    print(f"  {er_name}: {er_stats.count:,} reads, N50={er_stats.n50:,} bp")

# Generate plots
plot_by_end_reason(stats, "dist.png", alpha=0.4)
plot_detailed_4panel(stats, "detailed.png")
```

## Pattern B Integration

For ont-experiments orchestration:

```bash
ont_experiments.py run readlen_endreason exp-abc123 \
    --json stats.json \
    --plot-by-endreason dist.png
```
