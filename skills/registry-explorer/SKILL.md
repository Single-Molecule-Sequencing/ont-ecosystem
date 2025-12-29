---
name: registry-explorer
description: Explore and search the ONT experiment registry with advanced filtering and export capabilities.
---

# Registry Explorer Skill

Deep inspection of source data files to extract comprehensive metadata for ONT experiments.

## Purpose

This skill explores experiment source data to extract metadata that can't be inferred from names or paths:
- **BAM headers**: Basecaller, model, sample info from @RG/@PG tags
- **POD5 files**: Run metadata, device info, protocol settings
- **final_summary.txt**: Chemistry, basecall model, yield statistics
- **sequencing_summary.txt**: Per-read statistics

## Quick Start

```bash
# Explore a single experiment
/registry-explorer explore exp-abc123

# Scan all local experiments for metadata
/registry-explorer scan --local

# Extract metadata from specific file types
/registry-explorer extract exp-abc123 --bam --pod5 --summary

# Check if source files exist
/registry-explorer check exp-abc123

# List files in experiment directory
/registry-explorer ls exp-abc123
```

## Commands

### `explore <exp_id>` - Full Exploration

Fully explore an experiment's source data:

```bash
registry_explorer.py explore exp-abc123 [--verbose]

# Checks for and parses:
# - BAM files (header metadata)
# - POD5 files (run metadata)
# - final_summary.txt (chemistry, model, yield)
# - sequencing_summary.txt (per-read stats)
# - report_*.html (MinKNOW reports)
```

### `scan` - Batch Scanning

Scan multiple experiments:

```bash
registry_explorer.py scan [--local | --public | --all]

# Options:
--missing-chemistry   Only experiments missing chemistry
--missing-model       Only experiments missing basecall_model
--limit N             Process at most N experiments
--apply               Apply changes to registry
```

### `extract` - Targeted Extraction

Extract specific metadata types:

```bash
registry_explorer.py extract exp-abc123 [options]

# Options:
--bam          Extract from BAM headers
--pod5         Extract from POD5 metadata
--summary      Extract from summary files
--all          Extract from all available sources
```

### `check` - File Existence Check

Verify source files exist:

```bash
registry_explorer.py check exp-abc123

# Reports:
# - Directory exists
# - BAM files found
# - POD5 files found
# - Summary files found
# - Total size
```

### `ls` - List Files

List files in experiment directory:

```bash
registry_explorer.py ls exp-abc123 [--recursive]
```

## Metadata Extracted

### From BAM Headers

| Tag | Field | Description |
|-----|-------|-------------|
| @RG SM | sample | Sample name |
| @RG PL | platform | Platform (ONT) |
| @RG PM | model | Platform model |
| @RG DS | basecaller | Basecaller info |
| @PG PN | program | Program name |
| @PG VN | version | Program version |
| @PG CL | model | Model from command line |

### From POD5 Files

| Field | Description |
|-------|-------------|
| run_id | Unique run identifier |
| experiment_id | Experiment name |
| sample_id | Sample identifier |
| flow_cell_id | Flowcell ID |
| device_id | Device serial number |
| device_type | Device model |
| protocol_group_id | Protocol group |
| protocol_run_id | Protocol run ID |

### From final_summary.txt

| Field | Description |
|-------|-------------|
| flowcell_type | Chemistry (R10.4.1, R9.4.1) |
| basecaller | Basecaller software |
| model | Basecall model (sup/hac/fast) |
| yield_bases | Total yield in bases |
| n50 | N50 read length |
| mean_qscore | Mean quality score |

### From sequencing_summary.txt

| Field | Description |
|-------|-------------|
| read_count | Total reads |
| pass_count | Passing reads |
| mean_length | Mean read length |
| mean_qscore | Mean Q-score |

## Integration with Registry

Updates to registry include:
- Metadata fields populated
- Artifacts tracked (file paths)
- Provenance updated with extraction timestamp
- Audit log updated

```bash
# Full workflow
/registry-explorer scan --local --missing-chemistry --apply
/registry-scrutinize audit
```

## File Patterns

The explorer looks for files matching:

```
{location}/
├── *.bam                    # Aligned/basecalled BAM
├── pod5_pass/               # POD5 files
├── final_summary*.txt       # Run summary
├── sequencing_summary*.txt  # Per-read summary
├── report_*.html            # MinKNOW reports
└── other_reports/
    └── *.json               # Additional metadata
```

## Examples

### Extract chemistry for all local experiments
```bash
/registry-explorer scan --local --missing-chemistry --apply
```

### Deep exploration of single experiment
```bash
/registry-explorer explore exp-abc123 --verbose
```

### Check what files exist
```bash
/registry-explorer ls exp-abc123 --recursive
```
