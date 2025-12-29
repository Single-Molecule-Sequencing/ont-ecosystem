# ONT Ecosystem Installable Skills

This directory contains installable skill files for Claude Code, Claude Desktop, and Claude Web.

## Quick Install (All Skills)

```bash
./install-all.sh
```

This installs all skills to `~/.claude/commands/` and checks for required dependencies.

## Manual Installation

Copy individual skill command files to your Claude commands directory:

```bash
# Create Claude commands directory
mkdir -p ~/.claude/commands

# Install specific skills
cp comprehensive-analysis/comprehensive-analysis.md ~/.claude/commands/
cp end-reason/end-reason.md ~/.claude/commands/
```

## Available Skills

### /comprehensive-analysis

Complete ONT experiment analysis with 9 publication-quality figures, KDE distributions, end-reason overlays, and intelligent data sampling.

**Features:**
- 9 publication-quality figures with consistent end-reason color coding
- Data sampling (50K default) with runtime estimation
- Stratified sampling by end_reason
- Interactive HTML dashboard

**Usage:**
```bash
# Quick analysis (sampled, ~30s)
/comprehensive-analysis /path/to/experiment -o output/

# Full analysis (all reads)
/comprehensive-analysis /path/to/experiment -o output/ --full --dpi 600
```

**Dependencies:** numpy, pandas, matplotlib, scipy

### /end-reason

Oxford Nanopore read end reason QC analysis for adaptive sampling efficiency.

**Features:**
- End reason classification (signal_positive, unblock_mux_change, etc.)
- Quality assessment (OK/CHECK/FAIL)
- Support for POD5, Fast5, and sequencing_summary.txt

**Usage:**
```bash
# Analyze POD5 directory
/end-reason /path/to/pod5 --json results.json

# Quick analysis
/end-reason /path/to/data --quick --plot qc.png
```

**Dependencies:** pod5, pysam, numpy

## Directory Structure

```
installable-skills/
├── README.md                          # This file
├── install-all.sh                     # Install all skills
├── comprehensive-analysis/
│   ├── comprehensive-analysis.md      # Skill command file
│   ├── manifest.json                  # Skill metadata
│   └── install.sh                     # Individual installer
└── end-reason/
    ├── end-reason.md                  # Skill command file
    └── manifest.json                  # Skill metadata
```

## Dependencies

Install all dependencies:

```bash
pip install numpy pandas matplotlib scipy pod5 pysam
```

## For Claude Desktop/Web

Skills are automatically available when:
1. The skill command files are in `~/.claude/commands/`
2. Claude has access to the ont-ecosystem repository

## For Claude Code (CLI)

Skills are automatically loaded from the repository's `.claude/skills/` directory when working in the ont-ecosystem project.

## Updating Skills

To update skills, pull the latest changes and re-run the installer:

```bash
git pull origin main
./installable-skills/install-all.sh
```
