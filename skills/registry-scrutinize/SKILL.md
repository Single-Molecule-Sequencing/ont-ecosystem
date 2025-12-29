---
name: registry-scrutinize
description: Deep validation, re-analysis, and enrichment of ONT experiment registry
  entries. Scrutinizes metadata completeness, validates against strict standards,
  re-analyzes from source data, and maintains comprehensive audit logs.
metadata:
  version: 1.0.0
  author: Single Molecule Sequencing Lab
  slash_command: registry-scrutinize
  user_invocable: true
  tags:
  - ont
  - registry
  - validation
  - enrichment
  - audit
  - metadata
  - qc
  dependencies:
  - pyyaml
  - pysam (optional, for BAM parsing)
  - requests (optional, for streaming)
---

# Registry Scrutinize Skill v1.0

Deep validation and enrichment system for ONT experiment registry entries.

## Purpose

This skill provides comprehensive scrutiny of registry entries:
- **Validate** entries against strict metadata standards
- **Enrich** entries by extracting metadata from names, paths, and source data
- **Re-analyze** experiments from source data (local files or S3)
- **Audit** all changes with detailed logging
- **Report** on registry health and completeness

## Quick Start

```bash
# Full audit of registry with report
/registry-scrutinize audit

# Scrutinize and fix a single experiment
/registry-scrutinize fix exp-abc123

# Enrich all experiments with extracted metadata
/registry-scrutinize enrich --all

# Re-analyze experiments from source data
/registry-scrutinize reanalyze exp-abc123

# Generate comprehensive health report
/registry-scrutinize report --output health_report.html

# Batch scrutinize incomplete entries
/registry-scrutinize batch --incomplete --fix
```

## Commands

### `audit` - Registry Health Audit

Comprehensive audit showing all issues and suggestions:

```bash
registry_scrutinize.py audit [--json output.json] [--verbose]

# Output includes:
# - Validation summary (pass/fail/warning counts)
# - Missing fields by category
# - Metadata extraction opportunities
# - Duplicate detection
# - Stale entry detection
```

### `fix` - Fix Single Experiment

Scrutinize and fix a single experiment:

```bash
registry_scrutinize.py fix <exp_id> [--dry-run] [--force-reanalyze]

# Actions:
# - Validate against schema
# - Extract metadata from name/path
# - Migrate legacy fields to new structure
# - Generate URLs for public data
# - Update provenance timestamps
```

### `enrich` - Metadata Enrichment

Extract and populate metadata across all entries:

```bash
registry_scrutinize.py enrich [--all | --incomplete] [--dry-run]

# Extracts:
# - Sample IDs (HG001-HG007, COLO829, NA12878, etc.)
# - Device types from serial numbers
# - Chemistry from flowcell/path patterns
# - Basecall models (sup/hac/fast)
# - Modifications (5mCG, 5hmCG, 6mA)
# - Kit information
# - Run dates
```

### `reanalyze` - Re-analyze from Source

Re-analyze experiment from source data:

```bash
registry_scrutinize.py reanalyze <exp_id> [--max-reads 50000] [--no-stream]

# For public data:
# - Stream BAM header for metadata
# - Sample reads for QC metrics
# - Compute Q-scores via probability space
# - Calculate N50, length distribution

# For local data:
# - Parse POD5/BAM files
# - Extract run metadata
# - Compute full QC statistics
```

### `batch` - Batch Operations

Process multiple experiments:

```bash
registry_scrutinize.py batch [options]

Options:
  --incomplete    Process only entries with <80% completeness
  --unanalyzed    Process only entries without analyses
  --public        Process only public data
  --local         Process only local data
  --fix           Apply fixes (default: dry-run)
  --reanalyze     Re-analyze from source
  --limit N       Process at most N entries
```

### `report` - Health Report

Generate comprehensive HTML report:

```bash
registry_scrutinize.py report [--output report.html]

# Report includes:
# - Registry overview statistics
# - Completeness distribution
# - Field coverage analysis
# - Recent audit history
# - Recommendations
```

## Validation Standards

### Required Fields (Must Pass)

| Field | Description |
|-------|-------------|
| `id` | Unique experiment ID (exp-XXXXXXXX) |
| `name` | Human-readable name |
| `source` | Data source (local, ont-open-data) |

### Important Fields (Should Have)

| Field | Weight | Description |
|-------|--------|-------------|
| `metadata.sample` | 15 | Sample identifier |
| `metadata.device_type` | 10 | Device model |
| `metadata.chemistry` | 10 | Flowcell chemistry |
| `metadata.basecall_model` | 10 | Model accuracy tier |
| `metadata.flowcell_id` | 5 | Flowcell ID |

### Metric Fields (For Analysis)

| Field | Weight | Description |
|-------|--------|-------------|
| `read_counts.sampled` | 10 | Reads analyzed |
| `quality_metrics.mean_qscore` | 10 | Mean Q-score |
| `length_metrics.n50` | 10 | N50 value |

### Completeness Thresholds

- **Good (80%+)**: All critical metadata present
- **Warning (50-79%)**: Some metadata missing
- **Poor (<50%)**: Significant gaps, needs attention

## Metadata Extraction Patterns

### Sample Detection
- GIAB: `HG001-HG007`, `NA12878`, `NA24385`, etc.
- Cancer: `COLO829`, `HCC1395`, `HCC1937`
- Reference: `CHM13`
- Cell lines: `Jurkat`, `HEK293T`, `HeLa`

### Device Detection
- PromethION: `PA*`, `PCA*`, device IDs starting with `MD-`
- MinION: `MN*`
- GridION: `GXB*`
- Flongle: `FLO*`

### Chemistry Detection
- `R10.4.1`: Latest chemistry
- `R10.4`: Intermediate
- `R9.4.1`: Legacy

### Model Detection
- `sup`: Super high accuracy
- `hac`: High accuracy
- `fast`: Fast basecalling

## Audit Logging

All changes are logged to `~/.ont-registry/audit_log.yaml`:

```yaml
entries:
  - timestamp: "2025-12-29T10:00:00"
    action: "scrutinize_fix"
    experiment_id: "exp-abc123"
    changes:
      extracted_sample: "HG002"
      extracted_chemistry: "R10.4.1"
      migrated_quality_metrics: true
    user: "claude-code"
```

## Integration with Registry

This skill modifies the registry at `~/.ont-registry/experiments.yaml`:

```bash
# Check before making changes
/registry-scrutinize audit

# Apply fixes with dry-run first
/registry-scrutinize batch --incomplete --fix --dry-run

# Then apply for real
/registry-scrutinize batch --incomplete --fix
```

## Examples

### Fix all incomplete entries
```bash
/registry-scrutinize batch --incomplete --fix
```

### Re-analyze public data with fresh QC
```bash
/registry-scrutinize batch --public --unanalyzed --reanalyze --limit 10
```

### Generate report after changes
```bash
/registry-scrutinize report --output ~/registry_health.html
```
