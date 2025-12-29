# ONT Ecosystem Installable Skills

This directory contains installable skill files for Claude Code, Claude Desktop, and Claude Web.

## Quick Install (All Skills)

```bash
./install-all.sh
```

This installs all 9 skills to `~/.claude/commands/` and checks for required dependencies.

## Available Skills

| Skill | Purpose |
|-------|---------|
| `/comprehensive-analysis` | 9 publication figures, KDE, sampling, runtime estimation |
| `/dorado-bench-v2` | Dorado basecalling on UM HPC (ARMIS2/Great Lakes) |
| `/end-reason` | End reason QC for adaptive sampling |
| `/experiment-db` | SQLite database for experiment tracking |
| `/manuscript` | Publication-quality figures and tables |
| `/ont-align` | Alignment, reference management, edit distance |
| `/ont-experiments-v2` | Experiment registry with provenance tracking |
| `/ont-monitor` | Real-time sequencing run monitoring |
| `/ont-pipeline` | Multi-step workflow orchestration |

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
python3 dorado_basecall.py /path/to/pod5 --model sup --cluster armis2 --slurm job.sbatch
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

## Directory Structure

```
installable-skills/
├── README.md                          # This file
├── install-all.sh                     # Install all skills
├── comprehensive-analysis/
│   └── comprehensive-analysis.md      # Skill command file
├── dorado-bench-v2/
│   └── dorado-bench-v2.md
├── end-reason/
│   └── end-reason.md
├── experiment-db/
│   └── experiment-db.md
├── manuscript/
│   └── manuscript.md
├── ont-align/
│   └── ont-align.md
├── ont-experiments-v2/
│   └── ont-experiments-v2.md
├── ont-monitor/
│   └── ont-monitor.md
└── ont-pipeline/
    └── ont-pipeline.md
```

## Dependencies

Install all dependencies:

```bash
pip install numpy pandas matplotlib scipy pod5 pysam edlib pyyaml jinja2
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
