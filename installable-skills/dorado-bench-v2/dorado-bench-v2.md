---
description: Run Dorado basecalling on University of Michigan HPC clusters (ARMIS2, Great Lakes). Use when basecalling ONT data, generating SLURM jobs, benchmarking models, or processing POD5 files with GPU optimization.
---

# /dorado-bench-v2

Oxford Nanopore basecalling with Dorado on University of Michigan HPC clusters (ARMIS2 and Great Lakes).

## Usage

Run Dorado basecalling with GPU optimization:

$ARGUMENTS

## Cluster Configurations

### ARMIS2 (sigbio-a40)
- Partition: sigbio-a40
- Account: bleu1
- GPU: NVIDIA A40

### Great Lakes (gpu_mig40)
- Partition: gpu_mig40
- Account: bleu99
- GPU: NVIDIA A100 80GB

## Model Tiers

| Tier | Accuracy | Resources |
|------|----------|-----------|
| fast | ~95% | batch=4096, mem=50G |
| hac | ~98% | batch=2048, mem=75G |
| sup | ~99% | batch=1024, mem=100G |

## Examples

```bash
# Run basecalling through ont-experiments (with provenance)
ont_experiments.py run basecalling exp-abc123 --model sup --output calls.bam

# Direct basecalling
python3 dorado_basecall.py /path/to/pod5 --model sup --cluster armis2 --output calls.bam

# Generate SLURM job
python3 dorado_basecall.py /path/to/pod5 --model sup@v5.0.0 --cluster armis2 --slurm job.sbatch
sbatch job.sbatch

# With methylation calling
ont_experiments.py run basecalling exp-abc123 --model sup --modifications 5mCG_5hmCG --output calls_5mc.bam
```

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
| `--modifications` | Enable 5mCG_5hmCG methylation |

## Dependencies

- dorado (system)
- pod5
- pysam
