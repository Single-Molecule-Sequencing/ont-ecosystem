---
name: comprehensive-analysis
description: Comprehensive ONT sequencing analysis with KDE distributions, end-reason
  overlays, runtime estimation, and publication-quality figures. Supports data sampling
  for quick previews with estimated full runtime.
metadata:
  version: 2.0.0
  author: ONT Ecosystem
  category: analysis
  command: /comprehensive-analysis
  tags:
  - visualization
  - quality-control
  - kde
  - publication
  - end-reason
  - sampling
  dependencies:
  - numpy
  - pandas
  - matplotlib
  - scipy
  inputs:
  - sequencing_summary.txt
  outputs:
  - figures/*.png (9 publication-quality figures)
  - statistics.json
  - dashboard.html
---

# Comprehensive Analysis Skill

Generates publication-quality visualizations and comprehensive analysis of Oxford Nanopore sequencing experiments with consistent end-reason color coding and intelligent data sampling.

## Features

- **KDE-based distributions**: Smooth kernel density estimation with semi-transparent end-reason overlays
- **Consistent color scheme**: End-reason colors maintained across all 9 figures
- **Data sampling**: Default 50K reads (stratified by end_reason) for quick analysis
- **Runtime estimation**: Estimates full analysis time based on sampled execution
- **Publication-ready**: Up to 600 DPI output with proper annotations
- **Interactive dashboard**: HTML dashboard with modal viewing

## Quick Start

```bash
# Quick analysis (default - samples 50K reads)
python comprehensive_analysis.py /path/to/experiment -o output/

# Full analysis (all reads - for publication)
python comprehensive_analysis.py /path/to/experiment -o output/ --full

# Custom sample size
python comprehensive_analysis.py /path/to/experiment -o output/ --sample-size 100000

# From sequencing summary directly
python comprehensive_analysis.py --summary /path/to/sequencing_summary.txt -o output/

# With options
python comprehensive_analysis.py /path/to/experiment \
    --output output/ \
    --dpi 600 \
    --title "My Experiment" \
    --open-browser \
    --full
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output, -o` | Output directory (required) | - |
| `--summary` | Path to sequencing_summary.txt | auto-detect |
| `--title` | Custom title for figures | experiment name |
| `--dpi` | Figure resolution | 300 |
| `--full` | Use all reads (no sampling) | False |
| `--sample-size` | Number of reads to sample | 50,000 |
| `--open-browser` | Open dashboard when done | False |

## Data Sampling

By default, the skill samples up to 50,000 reads for quick visualization:

- **Stratified sampling**: Maintains end_reason proportions
- **Statistics from full data**: All statistics always computed from full dataset
- **Runtime estimation**: Estimates time for full analysis based on sampled execution
- **Annotated figures**: Sampled figures clearly marked with read counts
- **Dashboard banner**: Orange banner shows sampling status and estimated full runtime

## Generated Figures (9 total)

| # | Figure | Description |
|---|--------|-------------|
| 01 | Overview Summary | Quick assessment with key metrics |
| 02 | Length by End Reason | KDE with semi-transparent overlays |
| 03 | Quality by End Reason | Quality distribution per end reason |
| 04 | Quality-Length Correlation | Scatter, regression, binned analysis |
| 05 | 2D Density by End Reason | Hexbin density per end reason |
| 06 | Temporal Evolution | Stacked area, read rates, cumulative |
| 07 | Hourly Evolution | Quality, length, yield by hour |
| 08 | Channel Analysis | Heatmaps, performance by channel |
| 09 | Publication Summary | Combined publication-ready figure |

## End Reason Color Scheme

| End Reason | Color | Hex |
|------------|-------|-----|
| signal_positive | Green | #27ae60 |
| unblock_mux_change | Blue | #3498db |
| data_service_unblock_mux_change | Blue | #3498db |
| signal_negative | Red | #e74c3c |
| mux_change | Orange | #f39c12 |

## Output Structure

```
output/
├── figures/
│   ├── 01_overview_summary.png
│   ├── 02_length_by_end_reason.png
│   ├── 03_quality_by_end_reason.png
│   ├── 04_quality_length_correlation.png
│   ├── 05_2d_density_by_end_reason.png
│   ├── 06_temporal_evolution.png
│   ├── 07_hourly_evolution.png
│   ├── 08_channel_analysis.png
│   └── 09_publication_summary.png
├── statistics.json
└── dashboard.html
```

## Statistics JSON

```json
{
  "total_reads": 45136865,
  "sampled_reads": 50014,
  "is_sampled": true,
  "total_bases": 30479300000,
  "mean_length": 675.2,
  "median_length": 450.0,
  "n50": 675,
  "mean_qscore": 11.5,
  "median_qscore": 12.1,
  "pass_reads": 45136865,
  "fail_reads": 0,
  "pass_rate": 100.0,
  "end_reasons": {
    "data_service_unblock_mux_change": 41251754,
    "signal_positive": 3734572,
    "unblock_mux_change": 103126,
    "signal_negative": 44003,
    "mux_change": 2892
  }
}
```

## Integration with ont-experiments

Run through ont-experiments for provenance tracking:

```bash
ont_experiments.py run comprehensive_analysis exp-abc123 \
    --output results/ \
    --full \
    --dpi 600
```

## Example Output

```
Loading: /path/to/sequencing_summary.txt
  Loaded 45,136,865 reads

  [SAMPLING] Dataset has 45,136,865 reads > 50,000 threshold
  [SAMPLING] Using stratified sampling by end_reason
  [SAMPLING] Using 50,014 sampled reads for visualization
  [SAMPLING] NOTE: Run with --full flag to use all 45,136,865 reads

=== Statistics (from full dataset) ===
Reads: 45,136,865
Bases: 30479.3Mb
N50: 675 bp
Mean Q: 11.5

=== Generating Figures ===
  Generated: 01_overview_summary.png
  ...
  Generated: 09_publication_summary.png

  Figure generation time: 32.4s
  Estimated time for full 45,136,865 reads: ~9.8 hours

=== Analysis Complete ===
```
