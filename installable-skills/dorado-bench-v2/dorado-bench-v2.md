---
description: Oxford Nanopore basecalling with Dorado on University of Michigan HPC
  clusters (ARMIS2 and Great Lakes). Use when running dorado basecalling, generating
  SLURM jobs for basecalling, benchmarking models, optimizing GPU resources, or processing
  POD5 data. Captures model paths, GPU allocations, and job metadata. Integrates with
  ont-experiments for provenance tracking. Supports fast/hac/sup models, methylation
  calling, and automatic resource calculation.
name: dorado-bench-v2
---

# /dorado-bench-v2

Oxford Nanopore basecalling with Dorado on University of Michigan HPC clusters (ARMIS2 and Great Lakes).

## Usage

$ARGUMENTS

## Quick Start

```bash
# Basic usage
python skills/dorado-bench-v2/scripts/dorado_bench_v2.py [input]

# With provenance tracking
ont_experiments.py run dorado_bench_v2 exp-001 [options]
```

## Options

See `/dorado-bench-v2 --help` for all available options.

## Installation

```bash
# Clone repository
git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git

# Install to Claude commands
cp ont-ecosystem/installable-skills/dorado-bench-v2/dorado-bench-v2.md ~/.claude/commands/
```
