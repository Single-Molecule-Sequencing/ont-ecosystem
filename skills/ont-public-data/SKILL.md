---
name: ont-public-data
description: Discover, stream, and analyze public ONT datasets from S3 without full downloads. Analyzes reads via byte-range requests, generates statistics and publication plots.
---

# ONT Public Data Skill

Discover, stream, and analyze public Oxford Nanopore datasets from the ONT Open Data S3 bucket without downloading full files.

## Features

- **Dataset Discovery**: Browse and catalog experiments from `s3://ont-open-data/`
- **Streaming Analysis**: Use byte-range requests to analyze data without full downloads
- **50K Read Sampling**: Analyze first 50,000 reads per experiment for quick insights
- **Statistics Generation**: Compute N50, Q-scores, read lengths, end reasons, etc.
- **Publication Plots**: Generate 6-panel summary figures per experiment
- **Database Integration**: Add analyzed experiments to ont-ecosystem registry

## Quick Start

```bash
# List available datasets
/ont-public-data list

# Analyze a specific dataset
/ont-public-data analyze giab_2025.01 --max-experiments 5

# Full analysis with all datasets
/ont-public-data analyze-all --output ~/analysis_results

# Generate comparison report
/ont-public-data report ~/analysis_results
```

## Commands

### list
List available datasets in the ONT Open Data S3 bucket.

```bash
/ont-public-data list
/ont-public-data list --filter 2025  # Filter by year
```

### discover
Discover experiments within a specific dataset.

```bash
/ont-public-data discover giab_2025.01
/ont-public-data discover pgx_as_2025.07 --json experiments.json
```

### analyze
Stream and analyze experiments from a dataset.

```bash
/ont-public-data analyze giab_2025.01 --max-reads 50000 --output ~/results
/ont-public-data analyze hereditary_cancer_2025.09 --max-experiments 10
```

### analyze-all
Analyze multiple datasets in one run.

```bash
/ont-public-data analyze-all --datasets giab_2025.01,pgx_as_2025.07
/ont-public-data analyze-all --output ~/full_analysis
```

### report
Generate comprehensive comparison reports.

```bash
/ont-public-data report ~/analysis_results --format markdown
/ont-public-data report ~/analysis_results --format html
```

## Output Files

For each analyzed experiment:
- `summaries/<experiment>_summary.json` - Statistics and metrics
- `plots/<experiment>_summary.png` - 6-panel visualization

Aggregate outputs:
- `all_experiments_summary.json` - Combined results
- `analysis_report.md` - Comprehensive report
- `plots/dataset_comparison.png` - Cross-dataset comparison figure

## Streaming Approach

The skill uses two streaming methods to avoid downloading large files:

1. **Sequencing Summary Streaming**: HTTP byte-range requests to get first ~30MB of `.txt` files
2. **BAM Streaming**: `samtools view <url> | head -n 50000` for direct BAM access

This allows analyzing terabytes of public data with minimal bandwidth.

## Available Datasets

| Dataset | Description | Data Type |
|---------|-------------|-----------|
| giab_2025.01 | GIAB reference samples (HG001-HG007) | POD5 + sequencing_summary |
| pgx_as_2025.07 | Pharmacogenomics adaptive sampling | BAM |
| hereditary_cancer_2025.09 | Hereditary cancer panel | BAM |
| zymo_16s_2025.09 | Zymo 16S mock communities | BAM |
| chrom_acc_2025.06 | Chromatin accessibility | BAM |
| visium_hd_2025.06 | Visium HD spatial | BAM |
| And 30+ more... | | |

## Integration with ont-ecosystem

Analyzed experiments can be added to the experiment registry:

```bash
/ont-public-data analyze giab_2025.01 --add-to-registry
```

This integrates with Pattern B orchestration for full provenance tracking.

## Example Output

```
=== giab_2025.01_HG001_PAW79146 ===
Reads sampled: 50,000
Total bases: 747.2 Mb
Mean read length: 14,944 bp
N50: 27,241 bp
Mean Q-score: 12.0
Pass rate: 85.95%
End reasons:
  - signal_positive: 88.4%
  - mux_change: 7.1%
  - unblock_mux_change: 4.0%
```

## Requirements

- Python 3.9+
- matplotlib, numpy
- AWS CLI (`~/.local/bin/aws`)
- samtools (for BAM streaming)
- Internet connection (S3 public access)
