---
description: SQLite database for tracking nanopore experiments with fast SQL queries
  and statistics
name: experiment-db
---

# /experiment-db

SQLite database for tracking nanopore experiments with fast SQL queries and statistics.

## Usage

$ARGUMENTS

## Quick Start

```bash
# Basic usage
python skills/experiment-db/scripts/experiment_db.py [input]

# With provenance tracking
ont_experiments.py run experiment_db exp-001 [options]
```

## Options

See `/experiment-db --help` for all available options.

## Installation

```bash
# Clone repository
git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git

# Install to Claude commands
cp ont-ecosystem/installable-skills/experiment-db/experiment-db.md ~/.claude/commands/
```
