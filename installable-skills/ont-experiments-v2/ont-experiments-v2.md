---
description: Enhanced Oxford Nanopore experiment management with event-sourced registry,
  pipeline orchestration, unified QC aggregation, and GitHub-synced storage. Discover,
  track, and orchestrate nanopore sequencing experiments with full provenance tracking.
  Works both on HPC (full read/write) and remotely via GitHub (read-only fallback).
  This is the core skill that other ONT analysis skills integrate with via Pattern
  B orchestration.
name: ont-experiments-v2
---

# /ont-experiments-v2

Enhanced Oxford Nanopore experiment management with event-sourced registry, pipeline orchestration, unified QC aggregation, and GitHub-synced storage. Discover, track, and orchestrate nanopore sequencing experiments with full provenance tracking. Works both on HPC (full read/write) and remotely via GitHub (read-only fallback). This is the core skill that other ONT analysis skills integrate with via Pattern B orchestration..

## Usage

$ARGUMENTS

## Quick Start

```bash
# Basic usage
python skills/ont-experiments-v2/scripts/ont_experiments_v2.py [input]

# With provenance tracking
ont_experiments.py run ont_experiments_v2 exp-001 [options]
```

## Options

See `/ont-experiments-v2 --help` for all available options.

## Installation

```bash
# Clone repository
git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git

# Install to Claude commands
cp ont-ecosystem/installable-skills/ont-experiments-v2/ont-experiments-v2.md ~/.claude/commands/
```
