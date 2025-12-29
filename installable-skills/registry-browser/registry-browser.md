---
name: registry-browser
description: Interactive registry browser with rigorous metadata schema for ONT experiments.
  Features clear read count provenance (sampled/estimated/counted), direct S3/HTTPS
  URLs, comprehensive metadata extraction, and detail modal views.
metadata:
  version: 2.0.0
  author: Single Molecule Sequencing Lab
  user_invocable: true
---

# Registry Browser v2.0

Interactive browser and metadata manager with rigorous schema, provenance tracking, and direct data access URLs.

## Key Features in v2.0

- **Read Count Provenance**: Clear distinction between sampled, estimated, and counted reads
- **Data Access URLs**: Direct S3/HTTPS links to public ONT data
- **Detail Modal**: Click any experiment to see comprehensive metadata
- **Provenance Indicators**: Color-coded display of data source and computation method

## Commands

When the user invokes this skill, execute the appropriate command:

### View registry browser
```bash
python ~/repos/ont-ecosystem/skills/registry-browser/scripts/registry_browser.py view --output ~/ont_public_analysis/registry_browser.html
```

### Search experiments
```bash
python ~/repos/ont-ecosystem/skills/registry-browser/scripts/registry_browser.py search "<query>"
```

### Check if experiment exists
```bash
python ~/repos/ont-ecosystem/skills/registry-browser/scripts/registry_browser.py check "<id_or_name>"
```

### Add public experiment with full metadata extraction
```bash
python ~/repos/ont-ecosystem/skills/registry-browser/scripts/registry_browser.py add-public <dataset> <experiment> --analyze
```

### Update experiment with results
```bash
python ~/repos/ont-ecosystem/skills/registry-browser/scripts/registry_browser.py update <id> --analysis <type> --results <file>
```

### Export registry
```bash
python ~/repos/ont-ecosystem/skills/registry-browser/scripts/registry_browser.py export --format html --output registry.html
```

## Usage Examples

```
/registry-browser view
/registry-browser search "GIAB HG002"
/registry-browser check exp-abc123
/registry-browser add-public giab_2025.01 HG001_PAW79146 --analyze
```

## Features

- **Visual Browser**: Interactive HTML with grid/list/table views
- **Advanced Filtering**: Filter by source, sample, device, chemistry, model
- **Comprehensive Metadata**: Extract from file paths and BAM headers
  - Sample ID (HG001, NA12878, etc.)
  - Device type (PromethION, MinION, Flongle)
  - Chemistry (R10.4.1, R9.4.1)
  - Basecaller and version
  - Reference genome
  - Modifications (5mCG, 5hmCG)
  - Kit, library, replicate info
- **BAM Header Parsing**: Extract @RG, @PG, @SQ metadata
- **Artifact Tracking**: Track plots, summaries, and result files
- **Duplicate Detection**: Check before adding experiments
- **Public Data Integration**: Register ONT Open Data experiments
