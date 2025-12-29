---
description: Real-time and retrospective Oxford Nanopore sequencing run monitoring. Use when tracking active sequencing runs, analyzing completed run performance, checking throughput/quality/pore activity metrics, generating run reports, or diagnosing sequencing issues. Integrates with ont-experiments for provenance tracking via Pattern B orchestration.
---

# /ont-monitor

Real-time and retrospective Oxford Nanopore sequencing run monitoring.

## Usage

$ARGUMENTS

## Quick Start

```bash
# Basic usage
python skills/ont-monitor/scripts/ont_monitor.py [input]

# With provenance tracking
ont_experiments.py run ont_monitor exp-001 [options]
```

## Options

See `/ont-monitor --help` for all available options.

## Installation

```bash
# Clone repository
git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git

# Install to Claude commands
cp ont-ecosystem/installable-skills/ont-monitor/ont-monitor.md ~/.claude/commands/
```
