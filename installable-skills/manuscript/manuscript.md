---
description: Generate publication-quality figures and tables from ONT sequencing experiments.
  Supports KDE plots, quality distributions, QC summary tables, and multi-format export
  (PDF, PNG, LaTeX, HTML, JSON). Integrates with SMS_textbook for versioned artifact
  storage. Use for manuscript preparation, textbook figure generation, or experiment
  comparison.
name: manuscript
---

# /manuscript

Generate publication-quality figures and tables from ONT sequencing experiments. Supports KDE plots, quality distributions, QC summary tables, and multi-format export (PDF, PNG, LaTeX, HTML, JSON). Integrates with SMS_textbook for versioned artifact storage. Use for manuscript preparation, textbook figure generation, or experiment comparison..

## Usage

$ARGUMENTS

## Quick Start

```bash
# Basic usage
python skills/manuscript/scripts/manuscript.py [input]

# With provenance tracking
ont_experiments.py run manuscript exp-001 [options]
```

## Options

See `/manuscript --help` for all available options.

## Installation

```bash
# Clone repository
git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git

# Install to Claude commands
cp ont-ecosystem/installable-skills/manuscript/manuscript.md ~/.claude/commands/
```
