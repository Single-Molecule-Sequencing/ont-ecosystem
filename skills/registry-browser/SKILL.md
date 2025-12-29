---
name: registry-browser
version: 1.0.0
description: Interactive registry browser and metadata management for ONT experiments. Visualize, search, and update experiment metadata with analysis results and artifact tracking.
author: Single Molecule Sequencing Lab
slash_command: registry-browser
user_invocable: true
tags:
  - ont
  - registry
  - visualization
  - metadata
  - browser
dependencies:
  - pyyaml
  - jinja2 (optional, for HTML reports)
---

# Registry Browser Skill

Interactive browser and metadata manager for the ONT experiment registry. Provides visualization, search, metadata enrichment, and artifact tracking.

## Features

- **Visual Registry Browser**: Interactive HTML interface to explore experiments
- **Metadata Enrichment**: Extract and store comprehensive metadata from experiments
- **Artifact Tracking**: Track analysis outputs, plots, and result files
- **Search & Filter**: Full-text search across all experiment metadata
- **Public Data Integration**: Register public ONT experiments with full metadata
- **Duplicate Detection**: Check if experiments exist before adding

## Quick Start

```bash
# Launch interactive browser
/registry-browser view

# Search experiments
/registry-browser search "GIAB HG002"

# Add public experiment with metadata
/registry-browser add-public giab_2025.01 HG001_PAW79146

# Update experiment with analysis results
/registry-browser update exp-abc123 --analysis qc --results results.json

# Export registry to HTML
/registry-browser export --format html --output registry.html
```

## Commands

### view
Launch interactive HTML browser for the registry.

```bash
/registry-browser view [--output browser.html]
```

### search
Search experiments by name, ID, metadata, or tags.

```bash
/registry-browser search <query> [--field name|id|all]
```

### add-public
Add a public ONT experiment to the registry with full metadata extraction.

```bash
/registry-browser add-public <dataset> <experiment> [--analyze]
```

### update
Update experiment with analysis results and artifact locations.

```bash
/registry-browser update <id> --analysis <type> --results <file>
/registry-browser update <id> --artifact <path> --type <plot|summary|report>
```

### check
Check if an experiment exists and show its metadata status.

```bash
/registry-browser check <id|name>
```

### export
Export registry to various formats.

```bash
/registry-browser export --format html|json|csv --output <file>
```

## Metadata Schema

Experiments can have the following metadata:

```yaml
experiment:
  id: "exp-abc123"
  name: "HG001_PAW79146"
  source: "ont-open-data"  # or "local"

  # Core metrics
  total_reads: 50000
  total_bases: 747200000
  mean_quality: 12.0
  n50: 27241

  # Extended metadata
  metadata:
    dataset: "giab_2025.01"
    sample: "HG001"
    flowcell: "PAW79146"
    chemistry: "R10.4.1"
    basecaller: "dorado sup"
    reference: "GRCh38"

  # Analysis results
  analyses:
    - type: "streaming_qc"
      timestamp: "2025-12-29T10:00:00Z"
      results:
        mean_qscore: 12.0
        median_qscore: 11.8
        pass_rate: 85.95
        mapping_rate: 98.2

  # Artifact tracking
  artifacts:
    - path: "/path/to/summary.json"
      type: "summary"
      created: "2025-12-29T10:00:00Z"
    - path: "/path/to/plot.png"
      type: "plot"
      created: "2025-12-29T10:00:00Z"
```

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
