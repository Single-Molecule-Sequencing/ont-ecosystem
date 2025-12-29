---
name: registry-browser
version: 1.0.0
description: Interactive registry browser and metadata management for ONT experiments. Visualize, search, and update experiment metadata with analysis results and artifact tracking.
author: Single Molecule Sequencing Lab
user_invocable: true
---

# Registry Browser

Interactive browser and metadata manager for the ONT experiment registry.

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

### Add public experiment
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

- **Visual Browser**: Interactive HTML interface with search
- **Metadata Enrichment**: Extract and track comprehensive metadata
- **Artifact Tracking**: Track plots, summaries, and result files
- **Duplicate Detection**: Check before adding experiments
- **Public Data Integration**: Register ONT Open Data experiments
