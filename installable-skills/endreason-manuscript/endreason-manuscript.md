# End-Reason Manuscript Data Hub

Generate publication-quality figures and tables for end-reason analysis manuscript.

## Usage

```bash
# Initialize manuscript directory
/endreason-manuscript init

# Fetch data from all sources
/endreason-manuscript fetch --internal --public

# Generate all outputs
/endreason-manuscript generate --figures --tables

# Run full pipeline
/endreason-manuscript pipeline
```

## Available Figures

- **fig_adaptive_efficiency** - Adaptive vs non-adaptive sampling comparison
- **fig_endreason_breakdown** - Detailed per-end-reason breakdown
- **fig_channel_analysis** - Channel-level heatmaps
- **fig_library_quality** - Library quality assessment

## Available Tables

- **tbl_endreason_summary** - Per-end-reason statistics
- **tbl_adaptive_metrics** - Adaptive sampling efficiency metrics

## Quick Start

Run the full pipeline to generate all manuscript outputs:

```bash
endreason_manuscript.py pipeline --output manuscript/endreason/
```

This will:
1. Initialize the manuscript directory structure
2. Fetch internal experiments from registry
3. Fetch public ONT datasets
4. Analyze all experiments
5. Generate all figures and tables

## Output Directory

```
manuscript/endreason/
├── data/           # Source data
├── figures/        # PDF/PNG figures
├── tables/         # LaTeX/CSV/JSON tables
├── text/           # Manuscript sections
└── submission/     # Final outputs
```
