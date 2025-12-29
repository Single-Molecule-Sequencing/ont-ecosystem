# ONT Ecosystem Skills Reference

This document provides Claude with automatic context about available skills in the ONT Ecosystem. Skills are invoked using slash commands (e.g., `/end-reason`) or through the Skill tool.

## Available Skills

### /end-reason
**Purpose**: Oxford Nanopore read end reason QC analysis
**When to use**: Analyzing nanopore sequencing quality, checking adaptive sampling efficiency, investigating read termination patterns, diagnosing sequencing issues, running QC on POD5/Fast5 data
**Key commands**:
```bash
ont_experiments.py run end_reasons <exp_id> --json results.json --plot qc.png
python3 end_reason.py /path/to/data --json results.json
```

### /end-reason-v2
**Purpose**: Advanced end reason analysis with recursive search, parallel processing, and intelligent sampling
**When to use**: Large-scale analysis, multi-directory searches, performance-optimized QC
**Key commands**:
```bash
python3 end_reason.py /path/to/data --recursive --parallel --sample 100000
```

### /ont-experiments
**Purpose**: Experiment registry and provenance tracking hub
**When to use**: Creating experiments, running analyses with tracking, viewing experiment history, managing the experiment lifecycle
**Key commands**:
```bash
ont_experiments.py create <exp_id> --sample <sample> --flowcell <fc_id>
ont_experiments.py run <skill> <exp_id> [options]
ont_experiments.py list --status active
ont_experiments.py show <exp_id>
```

### /ont-align
**Purpose**: ONT read alignment workflows
**When to use**: Aligning nanopore reads to reference, generating BAM files, running minimap2
**Key commands**:
```bash
ont_experiments.py run alignment <exp_id> --ref GRCh38.fa
python3 ont_align.py --input reads.bam --ref reference.fa --output aligned.bam
```

### /ont-pipeline
**Purpose**: Multi-step pipeline execution
**When to use**: Running complete analysis pipelines, chaining multiple skills, batch processing
**Key commands**:
```bash
ont_pipeline.py run qc-fast <exp_id>
ont_pipeline.py run research-full <exp_id>
ont_pipeline.py list
```

### /ont-monitor
**Purpose**: Real-time sequencing run monitoring
**When to use**: Monitoring active runs, checking flowcell health, tracking yield
**Key commands**:
```bash
ont_monitor.py /path/to/run --interval 60
ont_monitor.py /path/to/run --metrics pore_count,yield,n50
```

### /dorado-bench
**Purpose**: Dorado basecalling benchmarking and optimization
**When to use**: Comparing basecalling models, estimating resources, optimizing GPU usage
**Key commands**:
```bash
python3 dorado_basecall.py benchmark --models fast,hac,sup
python3 calculate_resources.py --data-size 100 --model sup
```

### /experiment-db
**Purpose**: SQLite experiment database operations
**When to use**: Querying experiment data, generating reports, database maintenance
**Key commands**:
```bash
python3 experiment_db.py query --sample HG002
python3 experiment_db.py export --format csv
```

### /manuscript
**Purpose**: Publication-quality figure and table generation
**When to use**: Creating figures for papers, generating LaTeX tables, exporting artifacts
**Key commands**:
```bash
ont_manuscript.py figure fig_end_reason_kde <exp_id> --format pdf
ont_manuscript.py table tbl_qc_summary <exp_id> --format tex
ont_manuscript.py export <exp_id> ./paper --target latex
```

### /comprehensive-analysis
**Purpose**: Full analysis pipeline with visualization
**When to use**: Running complete analysis workflows, generating comprehensive reports
**Key commands**:
```bash
python3 comprehensive_analysis.py /path/to/data --output report/
```

## Skill Invocation

Skills can be invoked in three ways:

1. **Slash command**: `/end-reason` - Direct invocation
2. **Through ont_experiments**: `ont_experiments.py run end_reasons <exp_id>` - With provenance tracking
3. **Direct script**: `python3 skills/end-reason/scripts/end_reason.py` - Standalone

## Pattern B Orchestration

For full provenance tracking, always prefer running through `ont_experiments.py`:

```bash
# Preferred (full provenance)
ont_experiments.py run <skill_name> <experiment_id> [options]

# Direct (no provenance)
<skill_script>.py /path/to/data [options]
```

## Common Workflows

### QC Workflow
```bash
ont_experiments.py create exp-001 --sample HG002 --flowcell PAM12345
ont_experiments.py run end_reasons exp-001 --json qc.json --plot qc.png
ont_experiments.py run basecalling exp-001 --model sup
```

### Analysis Workflow
```bash
ont_experiments.py run alignment exp-001 --ref GRCh38.fa
ont_experiments.py run variant_calling exp-001 --caller clair3
ont_experiments.py run methylation exp-001
```

### Manuscript Workflow
```bash
ont_manuscript.py figure fig_end_reason_kde exp-001 --format pdf
ont_manuscript.py table tbl_qc_summary exp-001 --format tex
ont_manuscript.py export exp-001 ./paper --target latex
```
