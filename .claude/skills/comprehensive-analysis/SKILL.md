---
name: comprehensive-analysis
version: "1.0.0"
description: "Comprehensive ONT sequencing experiment analysis with publication-quality figures"
author: "ONT Ecosystem"
category: analysis
tags:
  - visualization
  - quality-control
  - kde
  - publication
dependencies:
  - numpy
  - pandas
  - matplotlib
  - scipy
inputs:
  - sequencing_summary.txt
  - throughput.csv (optional)
  - pore_activity.csv (optional)
outputs:
  - figures/*.png
  - statistics.json
  - dashboard.html
---

# Comprehensive Analysis Skill

Generates publication-quality visualizations and comprehensive analysis of Oxford Nanopore sequencing experiments.

## Features

- **KDE-based distributions**: Smooth kernel density estimation for read lengths and quality scores
- **Peak detection**: Automatic detection and annotation of distribution peaks
- **Multi-resolution views**: Overview, zoomed, and publication-ready figures
- **Temporal analysis**: Quality and yield over time
- **Channel analysis**: Per-channel statistics
- **End reason breakdown**: Classification of read termination types
- **Interactive dashboard**: HTML dashboard with all figures

## Usage

```bash
# Analyze experiment from sequencing summary
python comprehensive_analysis.py /path/to/experiment --output /path/to/output

# With specific options
python comprehensive_analysis.py /path/to/experiment \
    --output /path/to/output \
    --dpi 600 \
    --title "My Experiment" \
    --open-browser
```

## Output Structure

```
output/
├── figures/
│   ├── 01_read_length_kde.png
│   ├── 01b_read_length_peaks.png
│   ├── 01c_read_length_publication.png
│   ├── 02_quality_kde.png
│   ├── 02b_quality_time.png
│   ├── 02c_quality_channel.png
│   ├── 02d_quality_end_reason.png
│   ├── 02e_quality_publication.png
│   ├── 03_end_reason_pie.png
│   ├── 04_yield_timeline.png
│   ├── 05_channel_heatmap.png
│   └── 06_comprehensive_overview.png
├── statistics.json
└── dashboard.html
```

## Generated Figures

1. **Read Length Analysis**
   - Multi-panel KDE with linear/log scales
   - Peak detection with BP-resolution zooms
   - N50, mean, median markers

2. **Quality Score Analysis**
   - KDE with Q10/Q15/Q20 thresholds
   - Accuracy scale overlay
   - Temporal quality trends
   - Per-channel quality distribution
   - Quality by end reason

3. **End Reason Classification**
   - Pie chart with counts
   - Percentage breakdowns

4. **Yield Timeline**
   - Cumulative bases over time
   - Read rate over time

5. **Channel Activity**
   - Heatmap of reads per channel
   - Quality by channel

6. **Comprehensive Overview**
   - Single publication figure with key metrics
