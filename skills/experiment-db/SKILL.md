---
name: experiment-db
description: SQLite database for tracking nanopore experiments with fast SQL queries and statistics
version: 1.0.0
author: Single Molecule Sequencing Lab
category: data-management
tags:
  - nanopore
  - database
  - sqlite
  - experiments
  - end-reason
---

# Experiment Database Skill

SQLite database for tracking nanopore sequencing experiments. Complements the YAML-based ont-experiments-v2 registry by providing fast SQL-based queries for statistics and end reason distributions.

## When to Use

Use this skill when you need to:
- Build a database of all experiments in a directory
- Query experiment statistics using SQL
- Get end reason distributions across experiments
- Search for experiments by sample name or protocol
- Generate aggregate statistics across many experiments

## Commands

### Build Database

```bash
# Build database from experiment directory
experiment_db.py build --data_dir /data1 --db_path /data1/experiments.db

# Force rebuild (drops existing tables)
experiment_db.py build --data_dir /data1 --db_path experiments.db --rebuild

# Save report to file
experiment_db.py build --data_dir /data1 --db_path experiments.db -o report.txt
```

### Query Database

```bash
# Show summary
experiment_db.py query --db_path experiments.db --summary

# Show end reason distribution
experiment_db.py query --db_path experiments.db --end_reasons

# Search for specific experiment
experiment_db.py query --db_path experiments.db --experiment "sample_name"

# Custom SQL query
experiment_db.py query --db_path experiments.db --sql "SELECT * FROM experiments WHERE sample_id LIKE '%cyp2d6%'"
```

## Database Schema

### Table: experiments
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| experiment_path | TEXT | Full path to experiment |
| instrument | TEXT | Sequencer name |
| flow_cell_id | TEXT | Flow cell identifier |
| sample_id | TEXT | Sample name |
| protocol_group_id | TEXT | Protocol group |
| protocol | TEXT | Protocol name |
| started | TEXT | Start timestamp |
| acquisition_stopped | TEXT | End timestamp |
| pod5_files | INTEGER | Count of POD5 files |
| fastq_files | INTEGER | Count of FASTQ files |
| bam_files | INTEGER | Count of BAM files |

### Table: read_statistics
| Column | Type | Description |
|--------|------|-------------|
| experiment_id | INTEGER | Foreign key to experiments |
| total_reads | INTEGER | Total read count |
| passed_reads | INTEGER | Passed filter count |
| failed_reads | INTEGER | Failed filter count |
| total_bases | INTEGER | Total bases sequenced |
| mean_read_length | REAL | Mean read length |
| n50 | INTEGER | N50 read length |
| mean_qscore | REAL | Mean quality score |

### Table: end_reason_distribution
| Column | Type | Description |
|--------|------|-------------|
| experiment_id | INTEGER | Foreign key to experiments |
| end_reason | TEXT | End reason category |
| count | INTEGER | Read count |
| percentage | REAL | Percentage of total |

## Integration with ont_experiments.py

This skill integrates with Pattern B orchestration:

```bash
# Run through ont_experiments.py for provenance tracking
ont_experiments.py run experiment-db exp-abc123 --action build

# Direct execution (no provenance)
experiment_db.py build --data_dir /path/to/data --db_path experiments.db
```

## Example Queries

```sql
-- Find experiments with high signal_positive percentage
SELECT e.sample_id, erd.percentage
FROM experiments e
JOIN end_reason_distribution erd ON e.id = erd.experiment_id
WHERE erd.end_reason = 'signal_positive'
AND erd.percentage > 70;

-- Get average N50 by protocol
SELECT protocol, AVG(n50) as avg_n50
FROM experiments e
JOIN read_statistics rs ON e.id = rs.experiment_id
GROUP BY protocol;
```

## Great Lakes Discovery & Sync

Discover experiments on Great Lakes HPC turbo drive and sync to GitHub.

### Full Workflow

```bash
# Generate and submit discovery SLURM job
python3 sync_greatlakes.py

# Or step by step:
# 1. Generate discovery job (runs on Great Lakes via SLURM)
python3 sync_greatlakes.py --generate-only
ssh greatlakes "sbatch /nfs/turbo/umms-atheylab/discovery_job.sbatch"

# 2. After job completes, compare and review changes
python3 greatlakes_discovery.py compare \
  --manifest /nfs/turbo/umms-atheylab/experiment_manifest.json

# 3. Sync approved changes to GitHub
python3 greatlakes_discovery.py sync \
  --manifest /nfs/turbo/umms-atheylab/experiment_manifest.json \
  --approved --github
```

### Configuration

Turbo drive paths (in `greatlakes_discovery.py`):
- Base: `/nfs/turbo/umms-atheylab`
- Scan dirs: `sequencing_data`, `miamon`, `backup_from_desktop`
- Manifest: `/nfs/turbo/umms-atheylab/experiment_manifest.json`
- Database: `/nfs/turbo/umms-atheylab/experiments.db`

### GitHub Registry

Discovered experiments are exported to `registry/experiments_snapshot.json` for version control. The workflow:
1. SLURM job scans turbo drive for `final_summary*.txt` files
2. Exports manifest with metadata (sample_id, flow_cell, file counts)
3. Compares against current database
4. User reviews and approves proposed changes
5. Snapshot exported to GitHub repo

## Dependencies

- Python >= 3.7
- sqlite3 (standard library)
- Optional: pandas (for faster parsing)
