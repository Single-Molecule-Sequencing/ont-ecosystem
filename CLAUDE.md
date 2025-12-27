# ONT Ecosystem - Claude Configuration Guide

This document provides comprehensive instructions for configuring Claude to work with the ONT Ecosystem skills, including setup, usage patterns, and best practices.

## Quick Start

### 1. Upload Skills to Claude Projects

Navigate to your Claude Project and upload the `.skill` files from the `skills/` directory:

```bash
# Required core skill (always upload first)
skills/ont-experiments-v2.skill    # Registry & orchestration

# Analysis skills (upload as needed)
skills/end-reason.skill            # QC analysis
skills/ont-align.skill             # Alignment & edit distance
skills/ont-pipeline.skill          # Workflow orchestration
skills/ont-monitor.skill           # Run monitoring
skills/dorado-bench-v2.skill       # GPU basecalling
skills/experiment-db.skill         # SQLite database
```

### 2. Upload This Configuration File

Upload this `CLAUDE.md` file to your Claude Project to give Claude context about the skill system.

### 3. Start Using Skills

```
You: Analyze the end reasons for experiment exp-abc123
Claude: [Uses end-reason skill through ont-experiments orchestration]
```

---

## Skill Directory

| Skill | Purpose | When to Use |
|-------|---------|-------------|
| **ont-experiments-v2** | Core registry & orchestration | Always - required for all workflows |
| **end-reason** | QC analysis of read end reasons | Run QC, check adaptive sampling efficiency |
| **ont-align** | Alignment with edit distance | Map reads, calculate identity metrics |
| **ont-pipeline** | Multi-step workflow orchestration | Run complete analysis pipelines |
| **ont-monitor** | Real-time run monitoring | Monitor active sequencing runs |
| **dorado-bench-v2** | GPU basecalling on HPC | Basecall POD5 files on cluster |
| **experiment-db** | SQLite experiment database | Query experiments, generate reports |

### Skill Dependencies

```
ont-experiments-v2 (CORE)
├── end-reason
├── ont-align
├── ont-pipeline
│   └── (uses end-reason, ont-align, dorado-bench-v2)
├── ont-monitor
├── dorado-bench-v2
└── experiment-db
```

---

## How to Update Claude with New Skills

### Method 1: Claude Projects (Recommended)

1. **Go to Claude Projects**: https://claude.ai/projects
2. **Create or open your ONT Ecosystem project**
3. **Click "Add content" → "Upload files"**
4. **Upload the following files**:
   - `CLAUDE.md` (this file)
   - `skills/*.skill` (all skill files you need)
   - `registry/experiments.yaml` (your experiment registry)
5. **Start a new conversation** in the project

### Method 2: Claude Code CLI

If using Claude Code (CLI), skills are available in the repository:

```bash
# Clone/update the repository
git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git
cd ont-ecosystem

# Skills are in bin/ for direct execution
python3 bin/ont_experiments.py discover /path/to/data
python3 bin/end_reason.py /path/to/experiment --json results.json
```

### Method 3: Direct Script Upload

For quick use without full skill packaging:

1. Upload the specific script from `bin/` directory
2. Upload its corresponding `*_SKILL.md` documentation
3. Ask Claude to use the script

---

## Workflow Patterns

### Pattern A: Direct Execution (Simple)

Run skills directly without provenance tracking:

```bash
# Direct QC analysis
python3 bin/end_reason.py /path/to/experiment --json qc_results.json

# Direct alignment
python3 bin/ont_align.py align reads.bam reference.fa --json align_stats.json
```

**Use when**: Quick one-off analysis, testing, development

### Pattern B: Orchestrated Execution (Recommended)

Run skills through `ont-experiments` for full provenance:

```bash
# Through orchestrator (captures all metadata)
python3 bin/ont_experiments.py run end_reasons exp-abc123 --json qc_results.json
python3 bin/ont_experiments.py run align exp-abc123 --reference ref.fa
```

**Use when**: Production analysis, reproducibility required, multi-experiment studies

### Pattern C: Pipeline Execution (Complex Workflows)

Run multi-step workflows with YAML definitions:

```bash
# Run predefined pipeline
python3 bin/ont_pipeline.py run examples/pipelines/pharmaco-clinical.yaml exp-abc123

# Available pipelines:
#   qc-fast.yaml           - Quick QC (end_reasons → basecalling → monitoring)
#   pharmaco-clinical.yaml - CYP2D6 + PharmCAT workflow
#   research-full.yaml     - Complete research (alignment → variants → methylation)
```

---

## Common Tasks Reference

### Experiment Discovery & Management

```bash
# Discover experiments in a directory
ont_experiments.py discover /path/to/sequencing/data

# List all experiments
ont_experiments.py list

# Show experiment details
ont_experiments.py show exp-abc123

# Search experiments
ont_experiments.py search --name "SMAseq" --after 2025-01-01
```

### Quality Control

```bash
# End reason analysis (adaptive sampling QC)
ont_experiments.py run end_reasons exp-abc123 --json qc.json --plot qc.png

# Read length distributions (SMAseq)
python3 bin/ont_smaseq_readlen.py /path/to/experiment --output-dir ./results

# Run monitoring (active runs)
ont_experiments.py run monitor exp-abc123 --interval 60 --alerts
```

### Alignment & Analysis

```bash
# Align reads with edit distance
ont_experiments.py run align exp-abc123 --reference hg38.fa --json stats.json

# Full research pipeline
ont_pipeline.py run examples/pipelines/research-full.yaml exp-abc123
```

### Database Queries

```bash
# Initialize database from registry
python3 bin/experiment_db.py init --registry registry/experiments.yaml

# Query experiments
python3 bin/experiment_db.py query --platform PromethION --min-reads 1000000

# Export to CSV
python3 bin/experiment_db.py export --format csv --output experiments.csv
```

---

## Claude Conversation Examples

### Example 1: Analyze a New Experiment

**You**: I just finished a sequencing run at /data1/my_new_run. Can you analyze it?

**Claude will**:
1. Use `ont_experiments.py discover` to register the experiment
2. Run `end_reasons` analysis for QC
3. Generate read length distributions if SMAseq
4. Provide summary statistics and quality assessment

### Example 2: Compare Multiple Experiments

**You**: Compare the N50 and quality metrics across all my SMAseq experiments

**Claude will**:
1. Query the registry for SMAseq experiments
2. Extract statistics from each experiment
3. Generate comparison plots and tables
4. Highlight any experiments with quality issues

### Example 3: Run a Clinical Pipeline

**You**: Run the pharmacogenomics pipeline on experiment exp-abc123

**Claude will**:
1. Use `ont_pipeline.py` with `pharmaco-clinical.yaml`
2. Execute: basecalling → alignment → variants → CYP2D6 → PharmCAT
3. Generate clinical-grade reports
4. Track all provenance in the registry

---

## Skill Configuration

### Environment Variables

```bash
# Registry location (default: ~/.ont-registry/experiments.yaml)
export ONT_REGISTRY=/path/to/experiments.yaml

# HPC cluster configuration
export ONT_CLUSTER=greatlakes  # or armis2, local

# Default output directory
export ONT_OUTPUT_DIR=/path/to/outputs
```

### HPC Configuration

For SLURM clusters, configure in `examples/configs/`:

```yaml
# greatlakes.yaml
cluster: greatlakes
partition: standard
account: your_account
gpus_per_node: 1
time: "24:00:00"
```

---

## Updating Skills

### When to Update

Update your Claude Project skills when:
- New skill versions are released
- You've customized skill behavior
- New experiments are added to the registry
- New analysis types are needed

### Update Process

1. **Pull latest changes**:
   ```bash
   git pull origin main
   ```

2. **Rebuild skill packages** (if modified):
   ```bash
   make package
   ```

3. **Re-upload to Claude Projects**:
   - Remove old skill files from project
   - Upload new `.skill` files
   - Upload updated `CLAUDE.md`
   - Upload updated `registry/experiments.yaml`

4. **Verify in conversation**:
   ```
   You: What version of ont-experiments is loaded?
   Claude: [Shows version from skill metadata]
   ```

---

## Troubleshooting

### "Skill not found" Errors

1. Verify the `.skill` file is uploaded to your Claude Project
2. Check that `ont-experiments-v2.skill` (core) is uploaded
3. Re-upload the specific skill file

### "Experiment not found" Errors

1. Run `ont_experiments.py discover /path/to/data` to register
2. Check experiment ID format (exp-XXXXXXXX)
3. Verify the registry path in environment

### Quality Status Issues

| Status | Meaning | Action |
|--------|---------|--------|
| OK | signal_positive ≥75%, HQ ≥50% | Proceed with analysis |
| CHECK | Borderline metrics | Review QC plots, may need filtering |
| FAIL | Poor quality run | Investigate issues, may need re-run |

### HPC Job Failures

1. Check SLURM logs: `cat slurm-*.out`
2. Verify GPU availability: `squeue -u $USER`
3. Check resource configuration in `examples/configs/`

---

## File Locations Reference

```
ont-ecosystem/
├── CLAUDE.md              ← THIS FILE (upload to Claude Projects)
├── bin/                   ← Executable scripts (for CLI use)
├── skills/                ← Skill packages (upload .skill files)
│   ├── *.skill            ← Upload these to Claude Projects
│   └── */SKILL.md         ← Skill documentation
├── registry/
│   └── experiments.yaml   ← Upload for experiment context
├── examples/
│   ├── pipelines/         ← YAML workflow definitions
│   └── configs/           ← HPC configuration templates
└── docs/                  ← Additional documentation
```

---

## Version Information

| Component | Version |
|-----------|---------|
| ont-experiments-v2 | 2.2.0 |
| ont-align | 1.0.0 |
| ont-pipeline | 1.0.0 |
| end-reason | 1.0.0 |
| dorado-bench-v2 | 2.0.0 |
| ont-monitor | 1.0.0 |
| experiment-db | 2.0.0 |
| ont-smaseq-readlen | 1.0.0 |

---

## Getting Help

- **Documentation**: `docs/` directory
- **Skill details**: `skills/*/SKILL.md` files
- **Issues**: https://github.com/Single-Molecule-Sequencing/ont-ecosystem/issues
- **Examples**: `examples/` directory
