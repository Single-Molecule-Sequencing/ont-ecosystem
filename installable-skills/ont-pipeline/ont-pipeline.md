---
description: Oxford Nanopore multi-step workflow orchestration with unified QC aggregation. Use when running complete analysis pipelines (QC→basecalling→alignment→variants→pharmaco), generating unified reports, or batch processing experiments.
---

# /ont-pipeline

Oxford Nanopore multi-step workflow orchestration with unified QC aggregation.

## Usage

Run complete analysis pipelines:

$ARGUMENTS

## Quick Start

```bash
# List available pipelines
ont_pipeline.py list

# Run a pipeline
ont_pipeline.py run pharmaco-clinical exp-abc123

# Run with custom parameters
ont_pipeline.py run pharmaco-clinical exp-abc123 --param basecalling.model=hac

# Resume failed pipeline
ont_pipeline.py resume exp-abc123

# Generate unified report
ont_pipeline.py report exp-abc123 --format html --output report.html
```

## Built-in Pipelines

### pharmaco-clinical
Full pharmacogenomics workflow:
```
end_reasons → basecalling(sup) → alignment → variants → cyp2d6 → pharmcat
```

### qc-fast
Quick QC assessment:
```
end_reasons → basecalling(fast) → basic_stats
```

### research-full
Complete research workflow:
```
end_reasons → basecalling(sup+5mC) → alignment → variants → sv_calling → methylation
```

### validation
Validation against truth set:
```
end_reasons → basecalling → alignment → variants → truth_comparison
```

## Commands

| Command | Description |
|---------|-------------|
| `list` | List pipelines |
| `show <pipeline>` | Show definition |
| `run <pipeline> <exp>` | Execute pipeline |
| `resume <exp>` | Resume from checkpoint |
| `status <exp>` | Show status |
| `report <exp>` | Generate QC report |
| `batch <pipeline> ...` | Batch execution |

## Report Sections

1. **Summary Dashboard** - Overall status, key metrics
2. **Sequencing QC** - End reasons, quality, length
3. **Basecalling** - Model, pass/fail rates
4. **Alignment** - Mapping stats, coverage
5. **Variant Calling** - Counts, Ti/Tv ratio
6. **Pharmacogenomics** - CYP2D6, drug interactions

## Report Formats

| Format | Description |
|--------|-------------|
| html | Interactive dashboard |
| pdf | Print-ready report |
| json | Machine-readable |
| markdown | Documentation |

## Batch Processing

```bash
# Run on tagged experiments
ont_pipeline.py batch pharmaco-clinical --tag cyp2d6 --parallel 4

# Generate batch summary
ont_pipeline.py batch-report /results/batch_2025Q4
```

## CLI Reference

```
ont_pipeline.py <command> [options]

Run options:
  --param KEY=VALUE    Override parameter
  --skip-step STEP     Skip specific step
  --dry-run            Show execution plan

Report options:
  --format FORMAT      html, pdf, json, markdown
  --output FILE        Output path
  --include-plots      Embed plots

Batch options:
  --parallel N         Concurrent experiments
  --tag TAG            Filter by tag
  --slurm FILE         Generate SLURM job
```

## Dependencies

- pyyaml
- jinja2
- pandas
- plotly (optional)
- weasyprint (optional)
