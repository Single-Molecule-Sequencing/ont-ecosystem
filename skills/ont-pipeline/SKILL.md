---
name: ont-pipeline
description: Oxford Nanopore multi-step workflow orchestration with unified QC aggregation. Use when running complete analysis pipelines (QC → basecalling → alignment → variants → pharmacogenomics), generating unified reports, batch processing experiments, or coordinating complex multi-step workflows. Integrates with ont-experiments registry for full provenance tracking.
---

# ONT Pipeline - Workflow Orchestration

Multi-step analysis pipeline orchestrator with unified QC aggregation and pharmacogenomics support.

## Core Concept

Defines and executes reproducible analysis workflows:

```yaml
# ~/.ont-registry/pipelines/pharmaco-clinical.yaml
name: pharmaco-clinical
description: Clinical pharmacogenomics workflow
version: "1.0"

steps:
  - name: end_reasons
    analysis: end_reasons
    required: true
    pass_criteria:
      signal_positive_pct: ">=75"
    outputs: [json, plot]
    
  - name: basecalling
    analysis: basecalling
    depends_on: [end_reasons]
    parameters:
      model: sup
      modifications: 5mCG_5hmCG
    outputs: [bam, json]
    
  - name: alignment
    analysis: alignment
    depends_on: [basecalling]
    parameters:
      reference: GRCh38
      preset: map-ont
    outputs: [bam, stats]
    
  - name: variants
    analysis: variant_calling
    depends_on: [alignment]
    parameters:
      caller: clair3
      model: r1041_e82_400bps_sup_v500
    outputs: [vcf, json]
    
  - name: cyp2d6
    analysis: cyp2d6_calling
    depends_on: [variants]
    parameters:
      caller: cyrius
      reference: GRCh38
    outputs: [json, tsv]
    
  - name: pharmcat
    analysis: pharmcat
    depends_on: [variants, cyp2d6]
    parameters:
      reporter: true
      sources: [CPIC, DPWG, FDA]
    outputs: [json, html]

aggregation:
  metrics:
    - source: end_reasons
      fields: [quality_status, signal_positive_pct]
    - source: basecalling  
      fields: [mean_qscore, median_qscore, n50, total_reads]
    - source: alignment
      fields: [mapped_pct, mean_coverage, target_coverage]
    - source: variants
      fields: [total_variants, pass_variants, ti_tv_ratio]
    - source: cyp2d6
      fields: [diplotype, phenotype, activity_score]
    - source: pharmcat
      fields: [drug_count, actionable_count]
```

## Quick Start

```bash
# Initialize registry with pipeline support
ont_experiments.py init --git

# List available pipelines
ont_pipeline.py list

# Run a pipeline on an experiment
ont_pipeline.py run pharmaco-clinical exp-abc123

# Run with custom parameters
ont_pipeline.py run pharmaco-clinical exp-abc123 \
  --param basecalling.model=hac \
  --param alignment.reference=/path/to/custom.fa

# Resume failed pipeline
ont_pipeline.py resume exp-abc123

# Generate unified report
ont_pipeline.py report exp-abc123 --format html --output report.html
```

## Commands

| Command | Description |
|---------|-------------|
| `list` | List available pipelines |
| `show <pipeline>` | Show pipeline definition |
| `validate <pipeline>` | Validate pipeline YAML |
| `run <pipeline> <exp>` | Execute pipeline on experiment |
| `resume <exp>` | Resume from last successful step |
| `status <exp>` | Show pipeline execution status |
| `report <exp>` | Generate unified QC report |
| `batch <pipeline> <exp...>` | Run on multiple experiments |
| `create <name>` | Create new pipeline template |

## Built-in Pipelines

### pharmaco-clinical

Full pharmacogenomics workflow with PharmCAT reporting:
```
end_reasons → basecalling(sup) → alignment → variants → cyp2d6 → pharmcat
```

### qc-fast

Quick QC assessment:
```
end_reasons → basecalling(fast) → basic_stats
```

### research-full

Complete research workflow with methylation:
```
end_reasons → basecalling(sup+5mC) → alignment → variants → sv_calling → methylation
```

### validation

Validation against known truth set:
```
end_reasons → basecalling → alignment → variants → truth_comparison
```

## Pipeline Execution

### Dependency Resolution

Steps execute in dependency order with automatic parallelization:

```
end_reasons ─────────────────────────────┐
                                         ├─→ report
basecalling → alignment → variants → cyp2d6
                      └→ coverage_stats ─┘
```

### State Tracking

Pipeline state stored in registry events:

```yaml
events:
  - timestamp: "2025-01-15T10:00:00Z"
    type: pipeline_start
    pipeline: pharmaco-clinical
    version: "1.0"
    
  - timestamp: "2025-01-15T10:05:00Z"
    type: analysis
    analysis: end_reasons
    pipeline_step: 1
    exit_code: 0
    
  - timestamp: "2025-01-15T12:00:00Z"
    type: pipeline_complete
    pipeline: pharmaco-clinical
    duration_seconds: 7200
    steps_completed: 6
    steps_failed: 0
```

### Failure Handling

```bash
# Pipeline fails at step 3
ont_pipeline.py run pharmaco-clinical exp-abc123
# Error: Step 'alignment' failed (exit code 1)
# Run 'ont_pipeline.py resume exp-abc123' to retry

# Resume from failed step
ont_pipeline.py resume exp-abc123
# Skipping completed: end_reasons, basecalling
# Retrying: alignment...
```

## Unified QC Report

Aggregates metrics from all pipeline steps:

```bash
ont_pipeline.py report exp-abc123 --format html --output qc_report.html
```

### Report Sections

1. **Summary Dashboard**
   - Overall status (PASS/WARN/FAIL)
   - Key metrics at a glance
   - Pipeline execution timeline

2. **Sequencing QC**
   - End reason distribution
   - Quality scores
   - Read length distribution

3. **Basecalling**
   - Model and parameters
   - Pass/fail rates
   - Q-score distribution

4. **Alignment**
   - Mapping statistics
   - Coverage distribution
   - Target region performance

5. **Variant Calling**
   - Variant counts by type
   - Quality metrics
   - Ti/Tv ratio

6. **Pharmacogenomics** (if applicable)
   - CYP2D6 diplotype and phenotype
   - Drug-gene interactions
   - Clinical recommendations

### Report Formats

| Format | Description |
|--------|-------------|
| `html` | Interactive HTML dashboard |
| `pdf` | Print-ready PDF report |
| `json` | Machine-readable metrics |
| `markdown` | Documentation-friendly |

## Batch Processing

```bash
# Run pipeline on all experiments with a tag
ont_pipeline.py batch pharmaco-clinical \
  --tag cyp2d6 \
  --parallel 4 \
  --output-dir /results/batch_2025Q4

# Run on specific experiments
ont_pipeline.py batch pharmaco-clinical \
  exp-abc123 exp-def456 exp-ghi789 \
  --parallel 2

# Generate batch summary
ont_pipeline.py batch-report /results/batch_2025Q4
```

## Custom Pipelines

### Create from Template

```bash
ont_pipeline.py create my-workflow
# Creates ~/.ont-registry/pipelines/my-workflow.yaml
```

### YAML Structure

```yaml
name: my-workflow
description: Custom analysis workflow
version: "1.0"
author: your-name

# Parameters with defaults (overridable at runtime)
parameters:
  reference: GRCh38
  model_tier: sup

steps:
  - name: step_name
    analysis: analysis_type  # Maps to ANALYSIS_SKILLS in ont-experiments
    depends_on: []           # List of step names
    required: true           # Fail pipeline if step fails
    parameters:              # Step-specific parameters
      key: value
    pass_criteria:           # Conditions to continue
      metric: ">=threshold"
    outputs: [json, bam]     # Output types to generate
    
aggregation:
  metrics:
    - source: step_name
      fields: [metric1, metric2]
      
  thresholds:
    quality_status: PASS
    mean_qscore: ">=15"
    mapped_pct: ">=90"
```

## HPC Integration

Pipelines automatically use HPC resources:

```bash
# Generate SLURM array job for batch
ont_pipeline.py batch pharmaco-clinical \
  --tag batch1 \
  --slurm batch_job.sbatch

# Submit
sbatch batch_job.sbatch
```

SLURM script adapts resources per step:
- Basecalling: GPU partition (sigbio-a40)
- Alignment: High-memory nodes
- Variant calling: Multi-core CPU

## Integration with ont-experiments

Pipeline events logged to experiment registry:

```bash
# View pipeline history
ont_experiments.py history exp-abc123

# Filter by pipeline
ont_experiments.py history exp-abc123 --filter pipeline=pharmaco-clinical

# Export pipeline commands
ont_experiments.py export exp-abc123 --pipeline
```

## CLI Reference

```
ont_pipeline.py <command> [options]

Commands:
  list                    List available pipelines
  show <pipeline>         Show pipeline definition
  validate <pipeline>     Validate pipeline YAML
  run <pipeline> <exp>    Execute pipeline
  resume <exp>            Resume from last checkpoint
  status <exp>            Show execution status
  report <exp>            Generate unified report
  batch <pipeline> ...    Batch execution
  batch-report <dir>      Generate batch summary
  create <name>           Create pipeline template

Run options:
  --param KEY=VALUE       Override parameter
  --skip-step STEP        Skip specific step
  --from-step STEP        Start from step
  --dry-run               Show execution plan

Report options:
  --format FORMAT         Output format (html, pdf, json, markdown)
  --output FILE           Output file path
  --include-plots         Embed visualization plots

Batch options:
  --parallel N            Concurrent experiments
  --tag TAG               Filter by experiment tag
  --output-dir DIR        Results directory
  --slurm FILE            Generate SLURM array job
```

## Dependencies

```
pyyaml>=6.0          # Pipeline definitions
jinja2>=3.0          # Report templating
pandas>=1.5          # Metrics aggregation
plotly>=5.0          # Interactive plots (optional)
weasyprint>=60       # PDF generation (optional)
```
