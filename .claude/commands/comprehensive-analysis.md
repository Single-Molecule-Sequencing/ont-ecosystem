# /comprehensive-analysis

Comprehensive ONT sequencing analysis with 9 publication-quality figures, KDE distributions, end-reason overlays, and intelligent data sampling.

## Usage

Analyze an ONT sequencing experiment:

$ARGUMENTS

## Features

- **9 publication-quality figures** with consistent end-reason color coding
- **Data sampling**: Default 50K reads (stratified by end_reason) for quick ~30s preview
- **Runtime estimation**: Estimates time for full analysis based on sampled execution
- **Interactive HTML dashboard** with modal figure viewing
- **Statistics from full data**: All metrics computed from complete dataset

## Generated Figures

1. Overview Summary - Quick assessment with key metrics
2. Length by End Reason - KDE with semi-transparent overlays
3. Quality by End Reason - Quality distribution per end reason
4. Quality-Length Correlation - Scatter, regression, binned analysis
5. 2D Density by End Reason - Hexbin density per end reason
6. Temporal Evolution - Stacked area, read rates, cumulative
7. Hourly Evolution - Quality, length, yield by hour
8. Channel Analysis - Heatmaps, performance by channel
9. Publication Summary - Combined publication-ready figure

## End Reason Color Scheme

| End Reason | Color |
|------------|-------|
| signal_positive | Green (#27ae60) |
| unblock_mux_change | Blue (#3498db) |
| signal_negative | Red (#e74c3c) |
| mux_change | Orange (#f39c12) |

## Examples

```bash
# Quick analysis (sampled, ~30s)
python3 skills/comprehensive-analysis/scripts/comprehensive_analysis.py \
    /path/to/experiment -o output/

# Full analysis (all reads, for publication)
python3 skills/comprehensive-analysis/scripts/comprehensive_analysis.py \
    /path/to/experiment -o output/ --full --dpi 600

# From sequencing summary directly
python3 skills/comprehensive-analysis/scripts/comprehensive_analysis.py \
    --summary /path/to/sequencing_summary.txt -o output/

# Custom sample size
python3 skills/comprehensive-analysis/scripts/comprehensive_analysis.py \
    /path/to/experiment -o output/ --sample-size 100000

# Open dashboard in browser when done
python3 skills/comprehensive-analysis/scripts/comprehensive_analysis.py \
    /path/to/experiment -o output/ --open-browser
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output, -o` | Output directory (required) | - |
| `--summary` | Path to sequencing_summary.txt | auto-detect |
| `--title` | Custom title for figures | experiment name |
| `--dpi` | Figure resolution | 300 |
| `--full` | Use all reads (no sampling) | False |
| `--sample-size` | Number of reads to sample | 50,000 |
| `--open-browser` | Open dashboard when done | False |

## Output

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

## Dependencies

- numpy
- pandas
- matplotlib
- scipy

## Installation

```bash
# Clone the repository
git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git

# Install dependencies
pip install numpy pandas matplotlib scipy

# Copy skill command to Claude
cp ont-ecosystem/installable-skills/comprehensive-analysis/comprehensive-analysis.md \
   ~/.claude/commands/
```
