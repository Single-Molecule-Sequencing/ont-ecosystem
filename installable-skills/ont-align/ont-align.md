---
description: Oxford Nanopore alignment with minimap2/dorado, reference genome management,
  BAM QC, and Levenshtein edit distance computation using edlib. Use when aligning
  ONT reads to reference genomes, managing reference genome registries, computing
  alignment statistics, generating coverage metrics, performing BAM quality control,
  or computing edit distances between sequences. Integrates with ont-experiments for
  provenance tracking via Pattern B orchestration.
name: ont-align
---

# /ont-align

Oxford Nanopore alignment with minimap2/dorado, reference genome management, BAM QC, and Levenshtein edit distance computation using edlib.

## Usage

$ARGUMENTS

## Quick Start

```bash
# Basic usage
python skills/ont-align/scripts/ont_align.py [input]

# With provenance tracking
ont_experiments.py run ont_align exp-001 [options]
```

## Options

See `/ont-align --help` for all available options.

## Installation

```bash
# Clone repository
git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git

# Install to Claude commands
cp ont-ecosystem/installable-skills/ont-align/ont-align.md ~/.claude/commands/
```
