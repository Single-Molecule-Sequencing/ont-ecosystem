---
name: dorado-bench-v2
description: Oxford Nanopore basecalling with Dorado on University of Michigan HPC clusters (ARMIS2 and Great Lakes). Use when running dorado basecalling, generating SLURM jobs for basecalling, benchmarking models, optimizing GPU resources, or processing POD5 data. Captures model paths, GPU allocations, and job metadata. Integrates with ont-experiments for provenance tracking. Supports fast/hac/sup models, methylation calling, and automatic resource calculation.
---

# Dorado-Bench v2 - ONT Basecalling

Basecalling toolkit for UM HPC clusters with provenance tracking.

## Integration

Run through ont-experiments for provenance tracking:

```bash
ont_experiments.py run basecalling exp-abc123 --model sup --output calls.bam --json stats.json
```

Or standalone:

```bash
python3 dorado_basecall.py /path/to/pod5 --model sup --cluster armis2 --output calls.bam
```

## Cluster Configurations

### ARMIS2 (sigbio-a40)

```yaml
partition: sigbio-a40
account: bleu1
gres: gpu:a40:1
dorado: /nfs/turbo/umms-bleu-secure/programs/dorado-1.1.1-linux-x64/bin/dorado
models: /nfs/turbo/umms-bleu-secure/programs/dorado_models
```

### Great Lakes (gpu_mig40)

```yaml
partition: gpu_mig40
account: bleu99
gres: gpu:nvidia_a100_80gb_pcie_3g.40gb:1
dorado: /nfs/turbo/umms-atheylab/dorado-bench/dorado-1.1.1-linux-x64/bin/dorado
models: /nfs/turbo/umms-atheylab/dorado-bench/Models
```

**Athey Lab Turbo Drive Paths:**
- Base: `/nfs/turbo/umms-atheylab/`
- Dorado: `/nfs/turbo/umms-atheylab/dorado-bench/dorado-1.1.1-linux-x64/bin/dorado`
- Models: `/nfs/turbo/umms-atheylab/dorado-bench/Models/Simplex/`
- Input: `/nfs/turbo/umms-atheylab/dorado-bench/Input/`
- Output: `/nfs/turbo/umms-atheylab/dorado-bench/Output/`
- Sequencing data: `/nfs/turbo/umms-atheylab/sequencing_data/`

## Model Tiers

| Tier | Accuracy | ARMIS2 Resources | Great Lakes Resources |
|------|----------|------------------|----------------------|
| fast | ~95% | batch=4096, mem=50G, 24h | batch=2048, mem=32G, 24h |
| hac | ~98% | batch=2048, mem=75G, 72h | batch=1024, mem=64G, 72h |
| sup | ~99% | batch=1024, mem=100G, 144h | batch=512, mem=64G, 144h |

## Options

| Option | Description |
|--------|-------------|
| `--model TIER` | fast, hac, sup (default: hac) |
| `--version VER` | Model version (default: v5.0.0) |
| `--cluster` | armis2 or greatlakes |
| `--output FILE` | Output BAM file |
| `--json FILE` | Output JSON statistics |
| `--slurm FILE` | Generate SLURM script |
| `--emit-moves` | Include move table |
| `--modifications MOD` | Enable 5mCG_5hmCG methylation |

## SLURM Generation

```bash
python3 dorado_basecall.py /path/to/pod5 \
  --model sup@v5.0.0 \
  --cluster armis2 \
  --slurm job.sbatch

sbatch job.sbatch
```

## Event Tracking

When run through ont-experiments, captures:
- Model name and full path
- Model tier/version/chemistry
- Batch size and device
- BAM statistics (reads, qscore, N50)
- SLURM job ID, nodes, GPUs

## Methylation Calling

```bash
ont_experiments.py run basecalling exp-abc123 \
  --model sup \
  --modifications 5mCG_5hmCG \
  --output calls_5mc.bam
```

Resources adjusted: memory +50%, batch size -30%

## Great Lakes Quick Start

### Using greatlakes_submit.py (Simplified)

```bash
# Generate and submit a SUP basecalling job
python3 greatlakes_submit.py \
  /nfs/turbo/umms-atheylab/dorado-bench/Input/sample1 \
  --model sup@v5.0.0 \
  --output /nfs/turbo/umms-atheylab/dorado-bench/Output/sample1_sup.bam \
  --email user@umich.edu

# Dry run (generate script only)
python3 greatlakes_submit.py \
  /nfs/turbo/umms-atheylab/sequencing_data/my_sample/pod5 \
  --model hac \
  --output /nfs/turbo/umms-atheylab/dorado-bench/Output/my_sample_hac.bam \
  --dry-run
```

### Using dorado_basecall.py

```bash
# Generate SLURM script for Great Lakes
python3 dorado_basecall.py \
  /nfs/turbo/umms-atheylab/dorado-bench/Input/sample1 \
  --model sup@v5.0.0 \
  --cluster greatlakes \
  --output /nfs/turbo/umms-atheylab/dorado-bench/Output/sample1_sup.bam \
  --slurm job.sbatch

sbatch job.sbatch
```

### Batch Job Submission

```bash
# Generate sbatch files from command list
python3 make_sbatch_from_cmdtxt.py \
  -i dorado_basecaller_sup_cmd.txt \
  -o Sbatch/sup \
  --account bleu99 \
  --partition gpu_mig40 \
  --gres "gpu:nvidia_a100_80gb_pcie_3g.40gb:1" \
  --time "16:00:00" \
  --email user@umich.edu

# Submit all jobs
bash sbatch_all.sh
```

### Monitoring Jobs

```bash
squeue -u $USER                    # Check your jobs
squeue -p gpu_mig40                # Check partition queue
seff <job_id>                      # Job efficiency (after completion)
sacct -j <job_id> --format=JobID,JobName,State,ExitCode,Elapsed
```
