# End Reason Manuscript Design

**Date:** 2025-12-30
**Target:** bioRxiv preprint
**Approach:** Sequential pipeline with AI agents, hybrid collaboration

## Overview

Complete the End Reason paper using an automated pipeline with checkpoints for user review. The paper analyzes end_reason metadata from Oxford Nanopore sequencing to characterize read termination events.

## Pipeline Architecture

```
STAGE 0: HPC Data Discovery
├── 0a. Audit 166 experiments → find POD5 locations
├── 0b. Submit SLURM batch → /end-reason analysis
├── 0c. Collect results → update registry with QC metrics
└── 0d. Export master dataset → consolidated_end_reasons.csv
        ↓
   [CHECKPOINT: Review data completeness]
        ↓
STAGE 1: Curation & Analysis
├── 1a. Quality filter → exclude failed/incomplete runs
├── 1b. Define cohorts → internal vs external, device types
├── 1c. Statistical analysis → distributions, correlations
└── 1d. Select final N experiments for paper
        ↓
   [CHECKPOINT: Approve curated dataset]
        ↓
STAGE 2: Figure Generation
├── Fig 1: End reason taxonomy (signal diagrams)
├── Fig 2: Distribution across experiments
├── Fig 3: Read length by end reason
├── Fig 4: Q-score by end reason (bimodality)
└── Supplementary figures
        ↓
   [CHECKPOINT: Approve figures]
        ↓
STAGE 3: Writing
├── 3a. Methods → analysis pipeline, statistical approach
├── 3b. Results → data-driven narrative from figures
└── 3c. Polish → integrate with existing intro/discussion
        ↓
   [CHECKPOINT: Review complete draft]
        ↓
STAGE 4: bioRxiv Package
└── Export PDF, source files, data availability statement
```

## Data Sources

### HPC (Great Lakes)
- Location: `/nfs/turbo/umms-atheylab/`
- Content: POD5 files, BAM files, sequencing runs
- Access: SSH from WSL

### Local Registry
- Location: `~/.ont-registry/experiments.yaml`
- Content: 166 experiments (metadata only, no end_reason QC yet)

### Existing Paper Materials
- Location: `/mnt/d/Google_Drive_umich/Athey Lab Sequencing Project/Papers in Process/End Reason/`
- Content: V3 draft (docx), figures (AI/PNG), data tables (xlsx)

## Stage 0: HPC Data Discovery (Detail)

### 0a. Audit Registry
Extract all 166 experiments with their HPC paths. Identify:
- Experiments with POD5 files (required)
- Experiments with BAM files (optional, for tagging)
- Missing/inaccessible data

Output: `experiment_audit.json`

### 0b. SLURM Batch Submission
```bash
#SBATCH --array=1-N
#SBATCH --time=00:30:00
#SBATCH --mem=8G
#SBATCH --account=bleu99

python end_reason.py /path/to/pod5 --json output.json
```

### 0c. Result Collection
Collect JSON outputs, update registry with:
- Per-experiment end_reason percentages
- Read counts by category
- Analysis timestamps

### 0d. Export Master Dataset
Columns: `experiment_id, device, flowcell, total_reads, signal_positive_pct, unblock_mux_change_pct, signal_negative_pct, mux_change_pct, mean_qscore, n50, ...`

## Sections Needing Work

Priority sections (from user):
1. **Methods** - Analysis pipeline, statistical approach
2. **Results** - Data presentation, figures, statistical claims

Existing content (needs integration):
- Introduction - Partial draft exists
- Discussion - Partial draft exists

## Success Criteria

- [ ] All experiments audited and categorized
- [ ] End_reason analysis complete for 100+ experiments
- [ ] 4+ main figures generated
- [ ] Methods section complete and accurate
- [ ] Results section data-driven and coherent
- [ ] bioRxiv-ready PDF exported

## Tools & Skills

- `/end-reason` - End reason QC analysis
- `/comprehensive-analysis` - Full analysis with figures
- `/manuscript` - Figure/table generation
- `/ont-experiments-v2` - Registry management
- `/greatlakes-sync` - HPC data sync
