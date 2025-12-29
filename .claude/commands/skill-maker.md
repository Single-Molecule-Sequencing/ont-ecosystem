---
description: Create, update, and manage Claude skills automatically. Use when developing new analysis functions, fixing skill bugs, improving existing skills, or packaging skills for distribution. Handles SKILL.md creation, slash commands, ZIP packaging, and ecosystem integration.
---

# /skill-maker

Create, update, and manage Claude skills automatically.

## Usage

$ARGUMENTS

## Quick Start

```bash
# Basic usage
python skills/skill-maker/scripts/skill_maker.py [input]

# With provenance tracking
ont_experiments.py run skill_maker exp-001 [options]
```

## Options

See `/skill-maker --help` for all available options.

## Installation

```bash
# Clone repository
git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git

# Install to Claude commands
cp ont-ecosystem/installable-skills/skill-maker/skill-maker.md ~/.claude/commands/
```
