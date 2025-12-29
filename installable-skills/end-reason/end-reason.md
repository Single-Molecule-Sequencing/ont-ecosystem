---
description: Oxford Nanopore read end reason QC analysis. Use when analyzing nanopore
  sequencing quality, checking for adaptive sampling efficiency, investigating read
  termination patterns, diagnosing sequencing issues, or running QC on POD5/Fast5
  data. Integrates with ont-experiments for provenance tracking via Pattern B orchestration.
  Supports signal_positive, unblock_mux_change, data_service_unblock_mux_change analysis
  with quality thresholds.
name: end-reason
---

# /end-reason

Oxford Nanopore read end reason QC analysis.

## Usage

$ARGUMENTS

## Quick Start

```bash
# Basic usage
python skills/end-reason/scripts/end_reason.py [input]

# With provenance tracking
ont_experiments.py run end_reason exp-001 [options]
```

## Options

See `/end-reason --help` for all available options.

## Installation

```bash
# Clone repository
git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git

# Install to Claude commands
cp ont-ecosystem/installable-skills/end-reason/end-reason.md ~/.claude/commands/
```
