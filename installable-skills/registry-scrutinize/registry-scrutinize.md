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
  - pysam (optional)
  - requests (optional)
---

# Registry Scrutinize Skill

Deep validation and enrichment system for ONT experiment registry entries.

## Overview

This skill provides comprehensive scrutiny of registry entries:
- **Validate** entries against strict metadata standards
- **Enrich** entries by extracting metadata from names, paths, and source data
- **Re-analyze** experiments from source data (local files or S3)
- **Audit** all changes with detailed logging

## Installation

```bash
cd installable-skills && ./install-all.sh
```

## Commands

```bash
# Audit registry for issues
/registry-scrutinize audit

# Fix single experiment
/registry-scrutinize fix exp-abc123

# Enrich all experiments with extracted metadata
/registry-scrutinize enrich --all

# Re-analyze from source
/registry-scrutinize reanalyze exp-abc123

# Batch fix incomplete entries
/registry-scrutinize batch --incomplete --fix --apply

# Batch re-analyze public data
/registry-scrutinize batch --public --unanalyzed --reanalyze --limit 10 --apply
```

## Validation Standards

### Required Fields
- `id`: Unique experiment ID (exp-XXXXXXXX format)
- `name`: Human-readable name
- `source`: Data source (local or ont-open-data)

### Important Metadata Fields (weighted scoring)
| Field | Weight |
|-------|--------|
| sample | 15 |
| device_type | 10 |
| chemistry | 10 |
| basecall_model | 10 |
| flowcell_id | 5 |
| read_counts.sampled | 10 |
| quality_metrics.mean_qscore | 10 |
| length_metrics.n50 | 10 |

### Completeness Thresholds
- **Good (80%+)**: Complete metadata
- **Warning (50-79%)**: Some gaps
- **Poor (<50%)**: Needs attention

## Metadata Extraction

Automatically extracts:
- **Samples**: HG001-HG007, COLO829, NA12878, CHM13, etc.
- **Devices**: PromethION, MinION, Mk1D, GridION, Flongle
- **Chemistry**: R10.4.1, R10.4, R9.4.1, E8.2
- **Models**: sup, hac, fast
- **Modifications**: 5mCG, 5hmCG, 6mA
- **Kits**: SQK-LSK114, SQK-NBD114, etc.

## Audit Logging

All changes logged to `~/.ont-registry/audit_log.yaml` with timestamps, experiment IDs, and detailed change descriptions.

## Script Location

`skills/registry-scrutinize/scripts/registry_scrutinize.py`
