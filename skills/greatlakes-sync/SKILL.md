---
name: greatlakes-sync
description: Great Lakes HPC experiment discovery, database sync, and GitHub registry
  updates. Two-stage SLURM workflow with proposal review and HTML visualization.
metadata:
  version: 1.0.0
  author: Single Molecule Sequencing Lab
  category: data-management
  tags:
  - greatlakes
  - hpc
  - discovery
  - sync
  - slurm
  - github
  - database
  invocable: true
---

# Great Lakes Sync

Automated experiment discovery on Great Lakes HPC with database synchronization and GitHub registry updates.

## Features

- **Two-stage workflow**: Discovery creates proposal, separate apply step after review
- **SLURM integration**: CPU-only jobs for efficient discovery
- **HTML visualization**: Color-coded change indicators (new/updated/removed)
- **GitHub sync**: Updates `registry/experiments.yaml` with full provenance
- **Scheduling**: Weekly cron job with email notifications

## Quick Start

```bash
# Stage 1: Run discovery on Great Lakes
greatlakes_sync.py discover --submit --notify

# Review the proposal (opens HTML in browser)
greatlakes_sync.py review --latest

# Stage 2: Apply approved changes
greatlakes_sync.py apply --latest --commit --push
```

## Commands

### discover

Generate and submit SLURM discovery job.

```bash
greatlakes_sync.py discover [options]

Options:
  --submit          Submit SLURM job after generating
  --notify          Send email when job completes
  --dry-run         Generate script without submitting
```

### review

Review a discovery proposal.

```bash
greatlakes_sync.py review [options]

Options:
  --proposal PATH   Path to proposal YAML file
  --latest          Review most recent proposal
  --browser         Open HTML visualization in browser
```

### apply

Apply approved changes to database and GitHub.

```bash
greatlakes_sync.py apply [options]

Options:
  --proposal PATH   Path to approved proposal
  --latest          Apply most recent proposal
  --commit          Git commit changes
  --push            Git push after commit
```

### schedule

Manage scheduled discovery jobs.

```bash
greatlakes_sync.py schedule install --weekly --day sunday --hour 2
greatlakes_sync.py schedule status
greatlakes_sync.py schedule remove
```

## Workflow

```
1. Discovery Job (SLURM)
   └── Scans /nfs/turbo/umms-atheylab/
   └── Finds experiments (final_summary.txt, POD5, Fast5)
   └── Generates proposal YAML + HTML

2. User Review
   └── View HTML with change indicators
   └── Approve/reject changes

3. Apply Changes
   └── Update local SQLite database
   └── Update registry/experiments.yaml
   └── Git commit and push
```

## Directory Structure

```
/nfs/turbo/umms-atheylab/
├── .ont-sync/
│   ├── config.yaml           # Configuration
│   ├── run_discovery.sh      # Cron wrapper
│   ├── proposals/            # Proposal files
│   │   ├── proposal_YYYYMMDD_HHMMSS.yaml
│   │   └── proposal_YYYYMMDD_HHMMSS.html
│   └── approved/             # Applied proposals (archive)
├── logs/                     # SLURM logs
├── experiments.db            # SQLite database
└── experiments_registry.yaml # Local registry copy
```

## Configuration

Default configuration in `/nfs/turbo/umms-atheylab/.ont-sync/config.yaml`:

```yaml
account: bleu99
partition: standard
scan_dirs:
  - /nfs/turbo/umms-atheylab/sequencing_data
  - /nfs/turbo/umms-atheylab/miamon
  - /nfs/turbo/umms-atheylab/backup_from_desktop
notify_email: user@umich.edu
github_repo: Single-Molecule-Sequencing/ont-ecosystem
```

## Change Indicators

The HTML visualization uses color-coded indicators:

| Color | Meaning | Description |
|-------|---------|-------------|
| Green | New | Experiment not in current database |
| Orange | Updated | File counts or metadata changed |
| Red | Removed | Directory no longer exists |
| Gray | Unchanged | No changes detected |

## Integration

This skill integrates with:
- `experiment_db.py` - SQLite database operations
- `ont_experiments.py` - Pattern B orchestration
- `registry/experiments.yaml` - Central GitHub registry
