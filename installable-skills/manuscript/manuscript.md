---
description: Generate publication-quality figures and tables from ONT experiments. Use when creating manuscript figures, exporting KDE plots, generating QC summary tables, or preparing LaTeX/HTML outputs for papers.
---

# /manuscript

Generate publication-quality figures and tables from ONT sequencing experiments.

## Usage

Create manuscript-ready artifacts:

$ARGUMENTS

## Commands

```bash
# List available pipelines
ont_manuscript.py list-pipelines

# Run QC report pipeline
ont_manuscript.py pipeline qc-report <experiment_id>

# Generate specific figure
ont_manuscript.py figure fig_end_reason_kde <experiment_id> --format pdf

# Generate specific table
ont_manuscript.py table tbl_qc_summary <experiment_id> --format tex

# Export for manuscript
ont_manuscript.py export <experiment_id> ./manuscript --target latex

# Compare experiments
ont_manuscript.py compare exp1 exp2 exp3
```

## Figure Generators

| ID | Description | Formats |
|----|-------------|---------|
| fig_end_reason_kde | KDE plot by end reason | pdf, png |
| fig_end_reason_pie | End reason pie chart | pdf, png |
| fig_quality_dist | Q-score distribution | pdf, png |
| fig_read_length | Read length distribution | pdf, png |
| fig_yield_timeline | Cumulative yield | pdf, png |
| fig_n50_barplot | N50 comparison | pdf, png |
| fig_coverage | Coverage depth | pdf, png |
| fig_comparison | Multi-experiment | pdf, png |

## Table Generators

| ID | Description | Formats |
|----|-------------|---------|
| tbl_qc_summary | QC metrics | tex, csv, json, html |
| tbl_basecalling | Basecalling stats | tex, csv, json, html |
| tbl_alignment | Alignment stats | tex, csv, json, html |
| tbl_comparison | Multi-experiment | tex, csv, json, html |

## Pipelines

| Pipeline | Description |
|----------|-------------|
| qc-report | QC figures and summary |
| full-analysis | Complete analysis |
| comparison | Multi-experiment |
| summary-only | Tables only |

## Export Formats

### LaTeX
- Figures as PDF
- Tables as .tex files
- Ready for `\includegraphics{}`

### HTML
- Figures as PNG
- Tables as HTML fragments

## Dependencies

- matplotlib
- pandas
- numpy
- jinja2
