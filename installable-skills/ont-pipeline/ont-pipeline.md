---
description: "Oxford Nanopore multi-step workflow orchestration with unified QC aggregation.\
  \ Use when running complete analysis pipelines (QC \u2192 basecalling \u2192 alignment\
  \ \u2192 variants \u2192 pharmacogenomics), generating unified reports, batch processing\
  \ experiments, or coordinating complex multi-step workflows. Integrates with ont-experiments\
  \ registry for full provenance tracking."
name: ont-pipeline
---

# /ont-pipeline

Oxford Nanopore multi-step workflow orchestration with unified QC aggregation.

## Usage

$ARGUMENTS

## Quick Start

```bash
# Basic usage
python skills/ont-pipeline/scripts/ont_pipeline.py [input]

# With provenance tracking
ont_experiments.py run ont_pipeline exp-001 [options]
```

## Options

See `/ont-pipeline --help` for all available options.

## Installation

```bash
# Clone repository
git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git

# Install to Claude commands
cp ont-ecosystem/installable-skills/ont-pipeline/ont-pipeline.md ~/.claude/commands/
```
