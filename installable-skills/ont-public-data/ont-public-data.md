---
name: ont-public-data
version: 1.0.0
description: Discover, stream, and analyze public ONT datasets from S3 without full downloads
author: Single Molecule Sequencing Lab
user_invocable: true
---

# ONT Public Data Analysis

Stream and analyze public Oxford Nanopore datasets from ONT Open Data (s3://ont-open-data/) without downloading full files.

## Commands

When the user invokes this skill, execute the appropriate command:

### List datasets
```bash
python ~/repos/ont-ecosystem/skills/ont-public-data/scripts/ont_public_data.py list
```

### Discover experiments
```bash
python ~/repos/ont-ecosystem/skills/ont-public-data/scripts/ont_public_data.py discover <dataset_name>
```

### Analyze a dataset
```bash
python ~/repos/ont-ecosystem/skills/ont-public-data/scripts/ont_public_data.py analyze <dataset_name> \
  --max-reads 50000 \
  --max-experiments 10 \
  --output ~/ont_public_analysis
```

### Generate report
```bash
python ~/repos/ont-ecosystem/skills/ont-public-data/scripts/ont_public_data.py report ~/ont_public_analysis
```

## Usage Examples

```
/ont-public-data list
/ont-public-data discover giab_2025.01
/ont-public-data analyze pgx_as_2025.07 --max-experiments 5
/ont-public-data report ~/ont_public_analysis
```

## Available Datasets

Key datasets in ONT Open Data:
- **giab_2025.01** - GIAB reference samples (HG001-HG007), long reads
- **pgx_as_2025.07** - Pharmacogenomics with adaptive sampling
- **hereditary_cancer_2025.09** - Hereditary cancer panel (amplicons)
- **zymo_16s_2025.09** - Zymo mock communities for 16S
- **chrom_acc_2025.06** - Chromatin accessibility
- **visium_hd_2025.06** - Visium HD spatial transcriptomics

## Output

For each experiment:
- `summaries/<experiment>_summary.json` - Statistics (N50, Q-score, end reasons, etc.)
- `plots/<experiment>_summary.png` - 6-panel visualization

Aggregate:
- `all_experiments_summary.json` - Combined results
- `analysis_report.md` - Markdown report

## Streaming Approach

Uses byte-range HTTP requests and samtools streaming to analyze 50,000 reads per experiment without downloading multi-GB files.
