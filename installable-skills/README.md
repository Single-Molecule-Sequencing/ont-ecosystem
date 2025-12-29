# ONT Ecosystem Installable Skills

This directory contains installable skill files for Claude Code, Claude Desktop, and Claude Web.

## Installation by Platform

### Claude Code (CLI) - Automatic

Skills load automatically from `.claude/commands/` when working in the ont-ecosystem project.

**Manual installation to user directory:**
```bash
./install-all.sh
```

This copies slash command files to `~/.claude/commands/`.

### Claude Desktop / Claude Web - ZIP Files

1. Download ZIP files from `installable-skills/zip/`
2. In Claude Desktop/Web: **Settings > Features > Custom Skills**
3. Upload each `.zip` file
4. Restart Claude

**Generate fresh ZIP files:**
```bash
./create-zips.sh
```

### Claude API - Programmatic

Upload skills via the Skills API:
```python
import anthropic

client = anthropic.Anthropic()

with open("installable-skills/zip/end-reason.zip", "rb") as f:
    skill = client.beta.skills.create(
        name="end-reason",
        zip_file=f,
        betas=["skills-2025-10-02"]
    )
```

## Available Skills

| Skill | Purpose | ZIP Size |
|-------|---------|----------|
| `comprehensive-analysis` | 9 publication figures, KDE, sampling, runtime estimation | 22KB |
| `dorado-bench-v2` | Dorado basecalling on UM HPC (ARMIS2/Great Lakes) | 13KB |
| `end-reason` | End reason QC for adaptive sampling | 7KB |
| `experiment-db` | SQLite database for experiment tracking | 14KB |
| `manuscript` | Publication-quality figures and tables | 2KB |
| `ont-align` | Alignment, reference management, edit distance | 11KB |
| `ont-experiments-v2` | Experiment registry with provenance tracking | 32KB |
| `ont-monitor` | Real-time sequencing run monitoring | 14KB |
| `ont-pipeline` | Multi-step workflow orchestration | 13KB |

## Directory Structure

```
installable-skills/
├── README.md                          # This file
├── install-all.sh                     # Install slash commands (~/.claude/commands/)
├── create-zips.sh                     # Generate ZIP files for Desktop/Web
├── zip/                               # ZIP files for Claude Desktop/Web
│   ├── comprehensive-analysis.zip
│   ├── dorado-bench-v2.zip
│   ├── end-reason.zip
│   ├── experiment-db.zip
│   ├── manuscript.zip
│   ├── ont-align.zip
│   ├── ont-experiments-v2.zip
│   ├── ont-monitor.zip
│   └── ont-pipeline.zip
└── */                                 # Slash command files (*.md)
    └── *.md                           # For Claude Code ~/.claude/commands/
```

## File Formats

### Slash Commands (`*.md`)
Simple markdown files with YAML frontmatter for Claude Code slash commands:
```yaml
---
description: What this command does. Use when...
---

# /command-name

Instructions for Claude...
```

### Agent Skills (`SKILL.md` in ZIP)
Full skills with YAML frontmatter for Claude Desktop/Web/API:
```yaml
---
name: skill-name
description: What this skill does. Use when...
---

# Skill Name

## Instructions
[Detailed guidance for Claude]

## Examples
[Usage examples]
```

## Platform Differences

| Feature | Claude Code | Claude Desktop/Web | Claude API |
|---------|-------------|-------------------|------------|
| Format | Directory or `.md` | ZIP file | ZIP file |
| Location | `.claude/commands/` | Settings upload | API upload |
| Sharing | Project-local | Per-user | Organization-wide |
| Tool restrictions | `allowed-tools` supported | No restrictions | Depends on API |
| Network access | Full | Varies | No network |

## Dependencies

Most skills require Python packages. Install all:
```bash
pip install numpy pandas matplotlib scipy pod5 pysam edlib pyyaml jinja2
```

## Skill Details

### /comprehensive-analysis
Complete ONT experiment analysis with 9 publication-quality figures, KDE distributions, end-reason overlays, and intelligent data sampling.
```bash
/comprehensive-analysis /path/to/experiment -o output/
/comprehensive-analysis /path/to/experiment -o output/ --full --dpi 600
```

### /dorado-bench-v2
Oxford Nanopore basecalling with Dorado on UM HPC clusters with GPU optimization.
```bash
ont_experiments.py run basecalling exp-abc123 --model sup --output calls.bam
```

### /end-reason
End reason QC analysis for adaptive sampling efficiency.
```bash
/end-reason /path/to/pod5 --json results.json --plot qc.png
```

### /experiment-db
SQLite database for fast SQL queries on experiment data.
```bash
experiment_db.py build --data_dir /data1 --db_path experiments.db
experiment_db.py query --db_path experiments.db --summary
```

### /manuscript
Generate publication-quality figures and tables.
```bash
ont_manuscript.py figure fig_end_reason_kde exp-001 --format pdf
ont_manuscript.py table tbl_qc_summary exp-001 --format tex
```

### /ont-align
Alignment with minimap2/dorado, reference management, edit distance.
```bash
ont_align.py align reads.bam --reference GRCh38 --output aligned.bam
ont_align.py editdist "ACGT" "ACTT" --cigar
```

### /ont-experiments-v2
Core experiment registry with event-sourced provenance tracking.
```bash
ont_experiments.py init --git
ont_experiments.py discover /path/to/data --register
ont_experiments.py run end_reasons exp-001 --json qc.json
```

### /ont-monitor
Real-time and retrospective sequencing run monitoring.
```bash
ont_monitor.py /path/to/run --live
ont_monitor.py /path/to/run --json metrics.json --plot run.png
```

### /ont-pipeline
Multi-step workflow orchestration with unified QC.
```bash
ont_pipeline.py run pharmaco-clinical exp-001
ont_pipeline.py report exp-001 --format html
```

## Updating Skills

To update skills after pulling new changes:

```bash
# Pull latest
git pull origin main

# Regenerate ZIP files
./installable-skills/create-zips.sh

# Reinstall slash commands
./installable-skills/install-all.sh
```

For Claude Desktop/Web, re-upload the updated ZIP files.
