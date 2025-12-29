---
name: registry-browser
version: 3.0.0
description: Interactive registry browser with validation, re-analysis, and completeness tracking for ONT experiments. Features 42basepairs.com integration, audit logging, metadata validation, and publication-ready data access.
author: Single Molecule Sequencing Lab
slash_command: registry-browser
user_invocable: true
tags:
  - ont
  - registry
  - visualization
  - metadata
  - browser
  - validation
  - audit
  - bam-header
  - filtering
  - provenance
dependencies:
  - pyyaml
  - jinja2 (optional, for HTML reports)
---

# Registry Browser Skill v3.0

Comprehensive registry management with validation, re-analysis capabilities, and completeness tracking. Integrates with 42basepairs.com for visual S3 browsing.

## Key Features in v3.0

### Data Completeness Tracking
Visual indicators showing metadata completeness:
- **Good (80%+)**: Green indicator - most metadata present
- **Partial (50-79%)**: Yellow indicator - some metadata missing
- **Incomplete (<50%)**: Red indicator - significant gaps

### Validation & Audit
- `registry_validator.py`: Validate and fix registry entries
- `registry_reanalyze.py`: Re-analyze experiments from source data
- Audit log at `~/.ont-registry/audit_log.yaml`
- Automated metadata extraction from names/paths

### 42basepairs.com Integration
Direct links to visual S3 browser for public experiments:
- Browse experiment files interactively
- Preview BAM/POD5 contents
- Download individual files

### Enhanced Metadata Extraction
Automatic extraction of:
- Sample IDs (HG001-HG007, COLO829, etc.)
- Device types (PromethION, MinION, Mk1D, Flongle)
- Chemistry (R10.4.1, R9.4.1, E8.2)
- Basecall models (sup, hac, fast)
- Modifications (5mCG, 5hmCG, 6mA)
- Run dates from experiment names

## Features

- **Visual Registry Browser**: Interactive HTML with grid/list/table/detail views
- **Provenance Tracking**: Clear indication of data source and computation method
- **Advanced Filtering**: Filter by source, sample, device, chemistry, basecall model
- **Comprehensive Metadata Extraction**:
  - Sample ID (HG001, NA12878, COLO829, etc.)
  - Device type (PromethION, MinION, Flongle)
  - Chemistry (R10.4.1, R9.4.1, E8.2)
  - Basecaller and version (dorado, guppy)
  - Reference genome (GRCh38, CHM13-T2T)
  - Modifications (5mCG, 5hmCG, 6mA)
  - Kit, library, replicate info
- **BAM Header Parsing**: Extract @RG, @PG, @SQ metadata
- **Artifact Tracking**: Track analysis outputs, plots, and result files
- **Search & Filter**: Full-text search across all experiment metadata
- **Public Data Integration**: Register public ONT experiments with URLs
- **Duplicate Detection**: Check if experiments exist before adding

## Quick Start

```bash
# Launch interactive browser v3
python registry-browser/scripts/generate_browser_v3.py

# Audit registry for issues
python registry-browser/scripts/registry_validator.py audit

# Fix all registry issues
python registry-browser/scripts/registry_validator.py fix

# Update metadata for all experiments
python registry-browser/scripts/registry_reanalyze.py --update-metadata

# Re-analyze a single experiment
python registry-browser/scripts/registry_reanalyze.py exp-abc123
```

## Commands

### Validation Commands

```bash
# Audit - Show registry issues and suggestions
registry_validator.py audit [--json output.json] [-v]

# Fix - Automatically fix common issues
registry_validator.py fix [--dry-run] [-v]

# Validate - Check single experiment
registry_validator.py validate <exp_id>
```

### Re-analysis Commands

```bash
# Update metadata from names/paths
registry_reanalyze.py --update-metadata [--dry-run]

# Re-analyze single experiment (streams data)
registry_reanalyze.py <exp_id> [--no-stats]

# Re-analyze all public experiments
registry_reanalyze.py --public-all [--no-stats]
```

### Browser Commands

```bash
# Generate v3 browser with completeness tracking
generate_browser_v3.py

# Legacy v2 browser
registry_browser.py view [--output browser.html]

# Search experiments
registry_browser.py search <query>

# Check experiment
registry_browser.py check <id|name>
```

## Metadata Schema v2.0

The v2 schema provides rigorous field definitions with clear provenance tracking.
See `scripts/metadata_schema.py` for complete field definitions.

```yaml
experiment:
  id: "exp-abc123"
  name: "HG001_PAW79146"
  source: "ont-open-data"  # or "local"
  status: "analyzed"       # discovered, registered, analyzing, analyzed, complete

  # Data Access URLs (for public data)
  urls:
    s3: "s3://ont-open-data/giab_2025.01/..."
    https: "https://ont-open-data.s3.amazonaws.com/giab_2025.01/..."
    landing_page: "https://labs.epi2me.io/giab-2025.01/"

  # Read Counts with Clear Provenance
  read_counts:
    sampled: 50000              # Exact count of reads processed in analysis
    estimated_total: 5000000    # Extrapolated from file size (marked with ~)
    counted_total: null         # Only if full enumeration was performed
    count_source: "sampled"     # Which count is primary
    description: "Sampled reads from streaming analysis (not total reads)"

  # Base Counts
  base_counts:
    sampled_bases: 747200000
    estimated_total_bases: 74720000000

  # Quality Metrics (computed via probability space)
  quality_metrics:
    mean_qscore: 18.5           # -10*log10(mean(10^(-Q/10))), NOT arithmetic mean
    median_qscore: 19.2
    q10_percent: 95.2
    q20_percent: 72.8
    q30_percent: 15.3
    computed_from_n_reads: 50000
    note: "Q-scores computed via probability space averaging"

  # Length Metrics
  length_metrics:
    n50: 28500                  # 50% of bases in reads >= this length
    n90: 8200
    mean_length: 14943
    median_length: 12500
    max_length: 245678
    min_length: 200

  # Alignment Metrics
  alignment_metrics:
    mapping_rate: 99.2
    mapped_reads: 49600
    unmapped_reads: 400

  # Sequencing Metadata
  metadata:
    sample: "HG002"
    dataset: "giab_2025.01"
    device_type: "PromethION"
    flowcell_id: "PAW79146"
    chemistry: "R10.4.1"
    basecall_model: "sup"
    basecaller: "dorado"
    basecaller_version: "0.5.3"
    reference: "GRCh38"
    modifications: ["5mCG", "5hmCG"]
    kit: "SQK-LSK114"

  # Provenance
  provenance:
    schema_version: "2.0"
    registered: "2025-12-29T10:00:00Z"
    updated: "2025-12-29T12:00:00Z"
    analysis_tool: "registry-browser v2.0.0"

  # Artifacts
  artifacts:
    - path: "/path/to/summary.json"
      type: "summary"
      created: "2025-12-29T10:00:00Z"
```

### Read Count Interpretation Guide

| Display | Meaning | Provenance |
|---------|---------|------------|
| `50,000` (purple) | Sampled reads | Exact count from streaming analysis |
| `~5,000,000` (orange) | Estimated total | Extrapolated from file size |
| `4,987,234` (green) | Counted total | Full file enumeration |
| `50,000` (gray italic) | Legacy format | Provenance unknown |

## Integration with ont-experiments

This skill integrates with the core registry at `~/.ont-registry/experiments.yaml`:

```bash
# Check experiment before analysis
/registry-browser check exp-abc123

# Run analysis if needed, then update
ont_experiments.py run end_reasons exp-abc123 --json qc.json
/registry-browser update exp-abc123 --analysis end_reasons --results qc.json
```

## Public Data Registration

When adding public experiments, the skill:

1. Checks if experiment already exists in registry
2. Extracts comprehensive metadata from S3
3. Streams sample reads for QC metrics
4. Registers with full provenance
5. Tracks all generated artifacts

```bash
# Full workflow for public data
/registry-browser add-public giab_2025.01 HG001_PAW79146 --analyze --artifacts ~/analysis/
```
