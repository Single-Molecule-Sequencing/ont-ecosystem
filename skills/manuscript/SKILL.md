---
name: manuscript
description: Generate publication-quality figures and tables from ONT sequencing experiments. Supports KDE plots, quality distributions, QC summary tables, and multi-format export (PDF, PNG, LaTeX, HTML, JSON). Integrates with SMS_textbook for versioned artifact storage. Use for manuscript preparation, textbook figure generation, or experiment comparison.
---

# Manuscript Skill

Generate publication-quality figures and tables from ONT sequencing experiments.

## Pipeline Stage
- **Stage**: Post-analysis (A)
- **Purpose**: Convert analysis results into manuscript-ready artifacts

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

## Available Pipelines

| Pipeline | Description | Auto-Figures | Auto-Tables |
|----------|-------------|--------------|-------------|
| qc-report | QC figures and summary | fig_end_reason_kde, fig_quality_dist | tbl_qc_summary |
| full-analysis | Complete analysis | All QC + coverage, alignment | All QC + basecalling, alignment |
| comparison | Multi-experiment | Overlay plots, box plots | Comparison table |
| summary-only | Tables only | None | tbl_experiment_summary |

## Figure Generators

| ID | Description | Formats |
|----|-------------|---------|
| fig_end_reason_kde | KDE plot of read lengths by end reason | pdf, png |
| fig_quality_dist | Q-score distribution histogram | pdf, png |
| fig_coverage | Coverage depth plot | pdf, png |
| fig_alignment_stats | Alignment statistics | pdf, png |
| fig_comparison_overlay | Multi-experiment overlay | pdf, png |
| fig_box_comparison | Box plot comparison | pdf, png |

## Table Generators

| ID | Description | Formats |
|----|-------------|---------|
| tbl_qc_summary | QC metrics summary | tex, csv, json, html |
| tbl_basecalling | Basecalling statistics | tex, csv, json, html |
| tbl_alignment | Alignment statistics | tex, csv, json, html |
| tbl_comparison | Multi-experiment comparison | tex, csv, json, html |
| tbl_experiment_summary | Single experiment summary | tex, csv, json, html |

## Artifact Storage

Generated artifacts are stored with versioning:

```
~/.ont-manuscript/artifacts/
├── <experiment_id>/
│   ├── figures/
│   │   ├── fig_end_reason_kde/
│   │   │   ├── v1/
│   │   │   │   ├── fig_end_reason_kde.pdf
│   │   │   │   └── metadata.yaml
│   │   │   ├── v2/
│   │   │   └── latest -> v2
│   │   └── fig_quality_dist/
│   └── tables/
│       └── tbl_qc_summary/
```

## Export Formats

### LaTeX
- Figures exported as PDF
- Tables exported as .tex files
- Ready for `\input{}` or `\includegraphics{}`

### HTML
- Figures exported as PNG
- Tables exported as HTML fragments
- Ready for web embedding

## Integration with SMS_textbook

Use `ont_textbook_export.py` to export artifacts in the textbook's versioned format:

```bash
ont_textbook_export.py <experiment_id> /path/to/SMS_textbook
```

This creates:
```
SMS_textbook/figures/<fig_id>/latest/<fig_id>.pdf
SMS_textbook/tables/<tbl_id>/latest/<tbl_id>.tex
```

## Key Metrics

From **Pipeline Factorization Theorem** (CE.1):
- Signal Positive %: Reads with natural termination
- Unblock %: Reads rejected by adaptive sampling
- Quality Grade: A/B/C/D based on QC thresholds
- N50: Read length at which 50% of bases are in longer reads
- Mean Q-Score: Average Phred quality score
