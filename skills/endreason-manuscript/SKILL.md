---
name: endreason-manuscript
description: Local data processing hub for end-reason manuscript. Integrates HPC experiments, public ONT data, and physical size distributions. Generates publication-quality adaptive sampling figures and end-reason analysis tables for bioRxiv preprint.
---

# End-Reason Manuscript Skill

Data processing hub for generating publication-quality end-reason analysis figures and tables.

## Pipeline Stage
- **Stage**: Post-analysis (A)
- **Purpose**: Aggregate end-reason data from multiple sources and generate manuscript artifacts

## Commands

```bash
# Initialize manuscript directory structure
endreason_manuscript.py init --output manuscript/endreason/

# Fetch data from all sources
endreason_manuscript.py fetch --internal --public

# Run analysis on all experiments
endreason_manuscript.py analyze --all

# Generate all figures and tables
endreason_manuscript.py generate --figures --tables

# Generate specific figure
endreason_manuscript.py generate --figure adaptive_efficiency

# Build LaTeX manuscript
endreason_manuscript.py build --latex

# Full pipeline (fetch + analyze + generate)
endreason_manuscript.py pipeline --output manuscript/endreason/
```

## Data Sources

### Internal (HPC)
- Experiments from `~/.ont-registry/experiments.yaml`
- QC results from Pattern B orchestration
- Filter: DNA, native, R10.4.1 chemistry

### Public (ONT Open Data)
- `giab_2025.01` - GIAB reference samples (non-adaptive)
- `pgx_as_2025.07` - Pharmacogenomics (adaptive sampling)
- Streamed via `ont_public_data.py --max-reads 50000`

### Physical (Deferred)
- TapeStation 4150 CSV exports
- Bioanalyzer 2100 CSV exports
- Parsed to `size_distributions.yaml`

## Figure Generators

| ID | Description | Panels | Script |
|----|-------------|--------|--------|
| fig_adaptive_efficiency | Adaptive vs non-adaptive comparison | 4 | gen_adaptive_efficiency.py |
| fig_endreason_breakdown | Per-end-reason detailed breakdown | 6 | gen_endreason_breakdown.py |
| fig_channel_analysis | Channel-level heatmaps | 4 | gen_channel_analysis.py |
| fig_library_quality | Library quality assessment | 4 | gen_library_quality.py |
| fig_read_vs_physical | Read vs physical size (deferred) | 3 | gen_read_vs_physical.py |
| fig_multi_experiment | Multi-experiment comparison grid | 8 | gen_multi_experiment.py |

## Table Generators

| ID | Description | Formats | Script |
|----|-------------|---------|--------|
| tbl_endreason_summary | Per-end-reason statistics | tex, csv, json, html | gen_endreason_summary_table.py |
| tbl_adaptive_metrics | Adaptive sampling efficiency | tex, csv, json, html | gen_adaptive_metrics_table.py |
| tbl_physical_comparison | Physical vs read length (deferred) | tex, csv, json, html | gen_physical_comparison_table.py |

## Output Directory Structure

```
manuscript/endreason/
├── data/
│   ├── internal/          # HPC experiments QC results
│   ├── public/            # ONT Open Data summaries
│   ├── physical/          # TapeStation/Bioanalyzer (when available)
│   └── merged/            # Combined comparison matrix
├── figures/               # Generated PDFs/PNGs
├── tables/                # Generated LaTeX/CSV/HTML
├── text/                  # Manuscript sections
├── supplementary/         # Supplementary materials
├── submission/            # Final compiled outputs
└── scripts/               # Build scripts
```

## Key Metrics

### End-Reason Categories
| Category | Expected Range | Meaning |
|----------|---------------|---------|
| signal_positive | 75-95% | Normal read completion |
| unblock_mux_change | 0-20% | Hardware adaptive rejection |
| data_service_unblock_mux_change | 0-15% | Basecall-triggered rejection |
| mux_change | 0-10% | Pore multiplexer change |
| signal_negative | 0-5% | Signal loss/degradation |
| unknown | 0-5% | Unclassified |

### Quality Grades
- **Grade A**: signal_positive ≥95%, unblock ≤2%
- **Grade B**: signal_positive ≥85%, unblock ≤5%
- **Grade C**: signal_positive ≥75%, unblock ≤10%
- **Grade D**: Below Grade C thresholds

### Adaptive Sampling Metrics
- **Rejection Rate**: (unblock + data_service) / total
- **Efficiency**: Proportion of target regions enriched
- **Unblock Latency**: Time to rejection decision

## Integration

### With ont-experiments-v2
```bash
# Run with provenance tracking
ont_experiments.py run endreason_manuscript <exp_id> --output manuscript/endreason/
```

### With ont_manuscript.py
Uses the `endreason-preprint` pipeline:
```bash
ont_manuscript.py pipeline endreason-preprint <exp_id>
```

## Example Workflow

```bash
# 1. Initialize
endreason_manuscript.py init --output manuscript/endreason/

# 2. Fetch internal experiments
endreason_manuscript.py fetch --internal

# 3. Fetch public datasets for comparison
endreason_manuscript.py fetch --public --datasets giab_2025.01,pgx_as_2025.07

# 4. Generate all artifacts
endreason_manuscript.py generate --figures --tables

# 5. Build manuscript
endreason_manuscript.py build --latex --output manuscript/endreason/submission/

# Or run full pipeline
endreason_manuscript.py pipeline --output manuscript/endreason/
```
