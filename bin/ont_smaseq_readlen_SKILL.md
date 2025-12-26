# ONT SMAseq Read Length Distribution Analysis

Fine-grained, high-quality read length distributions for SMA-seq experiments with LED (Length-End-Distribution) analysis.

## Overview

This tool provides publication-quality read length distribution analysis specifically designed for SMA-seq (Single Molecule Analysis sequencing) experiments. It includes:

- **High-quality read filtering** (passes_filtering, Q-score thresholds)
- **Fine-grained BP-level resolution** (no binning loss for peak detection)
- **Publication-quality 300+ DPI output** with customizable styling
- **SMAseq-specific fragment analysis** (adapter dimers, target fragments, ultra-long)
- **Multi-experiment comparison** with statistical annotations
- **End reason stratification** for quality assessment
- **Peak detection** using KDE smoothing

## Installation

The tool is part of the ONT Ecosystem and requires:

```bash
# Required
pip install numpy matplotlib

# Optional (enhanced features)
pip install scipy pyyaml pod5
```

## Usage

### Single Experiment Analysis

```bash
# Basic analysis
python3 ont_smaseq_readlen.py /path/to/experiment --output-dir ./results

# With quality filtering
python3 ont_smaseq_readlen.py /path/to/data \
    --min-qscore 15 \
    --min-length 500 \
    --output-dir ./results

# Publication-quality plots
python3 ont_smaseq_readlen.py /path/to/data \
    --dpi 600 \
    --output-dir ./figures \
    --json stats.json
```

### Registry-Based Batch Analysis

```bash
# Analyze all SMAseq experiments from registry
python3 ont_smaseq_readlen.py \
    --registry /path/to/experiments.yaml \
    --smaseq-only \
    --output-dir ./smaseq_analysis

# Quick test with limited reads
python3 ont_smaseq_readlen.py \
    --registry experiments.yaml \
    --smaseq-only \
    --max-reads 100000 \
    --output-dir ./test_output
```

### Pattern B Integration

```bash
# Through ont-experiments orchestrator
ont_experiments.py run smaseq_readlen <exp_id> --json results.json
```

## Command-Line Options

### Input Options
| Option | Description |
|--------|-------------|
| `path` | Experiment path or sequencing_summary.txt |
| `--registry, -r` | Path to experiments.yaml registry |
| `--smaseq-only` | Only analyze SMAseq experiments from registry |

### Quality Filters
| Option | Default | Description |
|--------|---------|-------------|
| `--min-qscore` | 10.0 | Minimum Q-score for HQ reads |
| `--no-pass-filter` | False | Don't require passes_filtering=True |
| `--min-length` | 100 | Minimum read length (bp) |
| `--max-reads` | None | Maximum reads to process |

### Plot Options
| Option | Default | Description |
|--------|---------|-------------|
| `--dpi` | 300 | Plot resolution |
| `--no-plots` | False | Skip plot generation |
| `--xlim MIN MAX` | Auto | X-axis limits for plots |

### Output Options
| Option | Description |
|--------|-------------|
| `--output-dir, -o` | Output directory for plots and JSON |
| `--json` | Output JSON file for statistics |
| `--quiet, -q` | Suppress progress output |

## Output Files

For each experiment analyzed, the following files are generated:

| File | Description |
|------|-------------|
| `*_readlen_distribution.png` | Main read length histogram with N50/median markers |
| `*_readlen_by_endreason.png` | Overlaid distributions by end reason class |
| `*_hq_vs_lq.png` | Side-by-side HQ vs LQ comparison |
| `*_zoom_analysis.png` | Multi-panel zoom views of peak regions |
| `*_cumulative.png` | Cumulative distribution with NX markers |
| `smaseq_comparison.png` | Multi-experiment comparison (batch mode) |

## Statistics Output

The JSON output includes:

```json
{
  "experiment_id": "abc12345",
  "experiment_name": "IF_SMAseq_09112025",
  "total_reads": 13987594,
  "hq_reads": 12500000,
  "hq_pct": 89.4,
  "n50": 2639,
  "n90": 1205,
  "mean_length": 2443.5,
  "median_length": 2150.0,
  "mean_qscore": 21.9,
  "quality_status": "OK",
  "signal_positive_pct": 78.5,
  "fragment_bins": {
    "adapter_dimer": {"count": 1234, "pct_of_total": 0.01},
    "short_fragment": {"count": 125000, "pct_of_total": 1.0},
    "target_fragment": {"count": 10000000, "pct_of_total": 80.0},
    "long_fragment": {"count": 2000000, "pct_of_total": 16.0},
    "ultra_long": {"count": 373766, "pct_of_total": 2.99}
  },
  "detected_peaks": [2450, 4800, 7200],
  "end_reason_counts": {
    "signal_positive": 9812500,
    "data_service_unblock_mux_change": 1500000,
    "unblock_mux_change": 1000000,
    "mux_change": 187500
  }
}
```

## Fragment Size Classification

The tool classifies reads into SMAseq-specific fragment bins:

| Category | Size Range | Expected |
|----------|------------|----------|
| Adapter Dimer | 0-200 bp | <1% |
| Short Fragment | 200-1000 bp | <5% |
| Target Fragment | 1000-5000 bp | 60-80% |
| Long Fragment | 5000-15000 bp | 10-30% |
| Ultra Long | >15000 bp | <10% |

## Quality Assessment

The tool assigns quality status based on:

| Status | Criteria |
|--------|----------|
| **OK** | Signal positive ≥75% AND HQ reads ≥50% |
| **CHECK** | Signal positive ≥50% OR HQ reads ≥30% |
| **FAIL** | Below CHECK thresholds |

## End Reason Classes

| End Reason | Color | Interpretation |
|------------|-------|----------------|
| Signal Positive | Green | Normal read completion |
| Data Service Unblock | Red | Basecall-based rejection |
| Unblock (Adaptive) | Amber | Hardware adaptive sampling |
| MUX Change | Purple | Pore multiplexer switch |
| Signal Negative | Gray | Signal loss/degradation |

## Example Workflow

```bash
# 1. Analyze all SMAseq experiments
python3 ont_smaseq_readlen.py \
    --registry registry/experiments.yaml \
    --smaseq-only \
    --output-dir ./smaseq_led_analysis \
    --json smaseq_results.json

# 2. Generate high-resolution figures for publication
python3 ont_smaseq_readlen.py \
    /path/to/best_experiment \
    --dpi 600 \
    --min-qscore 15 \
    --output-dir ./publication_figures

# 3. Quick QC check
python3 ont_smaseq_readlen.py \
    /path/to/new_run \
    --max-reads 50000 \
    --quiet
```

## Integration with ONT Ecosystem

This tool integrates with the broader ONT Ecosystem:

- **Pattern B Orchestration**: Register with `ont_experiments.py` for automatic provenance tracking
- **Registry**: Automatically discovers SMAseq experiments from experiments.yaml
- **End Reason Analysis**: Complements `end_reason.py` with length stratification
- **Database**: Results can be stored in experiment-db for longitudinal analysis

## Version History

- **v1.0.0** (2025-12): Initial release with fine-grained LED analysis
  - High-quality read filtering
  - Publication-quality plotting (5 plot types)
  - SMAseq fragment bin analysis
  - Peak detection with KDE
  - Multi-experiment comparison
  - Registry integration
