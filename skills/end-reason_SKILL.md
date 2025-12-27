---
name: end-reason
description: Oxford Nanopore read end reason QC analysis with high-resolution KDE visualization. Use when analyzing nanopore sequencing quality, checking for adaptive sampling efficiency, investigating read termination patterns (signal_positive, unblock_mux_change, data_service_unblock), diagnosing sequencing issues, running QC on POD5/Fast5 data, detecting concatemers, or comparing library prep quality across experiments. Integrates with ont-experiments for provenance tracking via Pattern B orchestration. Triggers on queries about end reason distributions, pore unblocking events, adaptive sampling rejection rates, or sequencing termination causes.
---

# ONT End Reason QC Analysis v2.0

High-resolution KDE visualization with multi-zoom analysis, concatemer detection, and publication-quality plots for Oxford Nanopore read termination patterns.

## Quick Start

```bash
# Basic KDE analysis
python3 scripts/ont_endreason_qc.py /path/to/run --plot-kde qc.png

# Multi-zoom analysis (short reads + peak + concatemers)
python3 scripts/ont_endreason_qc.py /path/to/run --plot-multizoom zoom.png

# Full analysis suite
python3 scripts/ont_endreason_qc.py /path/to/run \
  --plot-kde kde.png \
  --plot-multizoom zoom.png \
  --plot-summary summary.png \
  --json stats.json
```

## Plot Types

### 1. KDE Distribution (`--plot-kde`)
High-resolution kernel density estimation (10bp resolution):
- **Signal positive** (green) - normal sequencing completion
- **Unblock** (red) - pore unblocking events
- Semi-transparent fills with solid line overlays
- Automatic target size detection and marking

### 2. Multi-Zoom Analysis (`--plot-multizoom`)
Four-panel analysis at different scales:
- **Short reads (0-500bp)**: Adapter dimer detection
- **Target peak (1.5-3.5kb)**: Size selection efficiency
- **Concatemers (4-8kb)**: 2x target detection
- **Long reads (8-15kb)**: 3x+ fragments

### 3. Summary Statistics (`--plot-summary`)
Cross-experiment comparison with quality thresholds.

## End Reason Categories

| End Reason | Description | Expected % |
|------------|-------------|------------|
| `signal_positive` | Normal completion | 85-98% |
| `unblock_mux_change` | Pore unblocking | 1-10% |
| `data_service_unblock` | Basecall rejection | 0-5% |

## Quality Thresholds

| Metric | Excellent | Good | Warning | Poor |
|--------|-----------|------|---------|------|
| Signal positive % | ≥95% | 85-95% | 75-85% | <75% |
| Unblock % | <2% | 2-5% | 5-10% | >10% |
| Short read % (<200bp) | <1% | 1-5% | 5-15% | >15% |

## Diagnostic Patterns

- **Median << N50**: Contamination masked by long tail
- **Unblock N50 > signal_positive N50**: Concatemer enrichment
- **Bimodal at ~150bp**: Adapter dimer contamination

## CLI Reference

```
ont_endreason_qc.py [inputs...] [options]

Plot Options:
  --plot-kde, -k FILE         KDE distributions by end reason
  --plot-multizoom, -m FILE   4-panel multi-zoom analysis
  --plot-summary, -s FILE     Summary statistics panels

Output Options:
  --json, -j FILE       Full statistics JSON

Analysis Options:
  --max-reads INT       Sample limit for quick analysis
  --dpi INT             Plot resolution (default: 300)
```

## Pattern B Integration

```bash
# Register with ont-experiments provenance
ont_experiments.py run endreason_qc exp-abc123 --plot-kde qc.png --json stats.json
```

## Dependencies

- numpy>=1.20
- scipy>=1.7  
- matplotlib>=3.5
