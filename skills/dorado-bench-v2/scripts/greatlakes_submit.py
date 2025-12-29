#!/usr/bin/env python3
"""
Great Lakes SLURM Job Submission Helper

Simplified interface for submitting dorado basecalling jobs to Great Lakes HPC.

Usage:
    # Generate and optionally submit a single job
    python3 greatlakes_submit.py /path/to/pod5 --model sup --output output.bam

    # Generate SLURM script only (don't submit)
    python3 greatlakes_submit.py /path/to/pod5 --model sup --output output.bam --dry-run

    # Submit with email notifications
    python3 greatlakes_submit.py /path/to/pod5 --model sup --output output.bam --email user@umich.edu

Examples:
    # Basecall with SUP model
    python3 greatlakes_submit.py /nfs/turbo/umms-atheylab/sequencing_data/sample1/pod5 \\
        --model sup@v5.0.0 \\
        --output /nfs/turbo/umms-atheylab/dorado-bench/Output/sample1_sup.bam

    # Quick test with FAST model
    python3 greatlakes_submit.py ./Input/test_sample \\
        --model fast \\
        --output ./Output/test_fast.bam \\
        --dry-run
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Great Lakes Configuration
GREATLAKES_CONFIG = {
    'partition': 'gpu_mig40',
    'account': 'bleu99',
    'gres': 'gpu:nvidia_a100_80gb_pcie_3g.40gb:1',
    'dorado_path': '/nfs/turbo/umms-atheylab/dorado-bench/dorado-1.1.1-linux-x64/bin/dorado',
    'model_dir': '/nfs/turbo/umms-atheylab/dorado-bench/Models/Simplex',
}

# Model tier configurations
MODEL_TIERS = {
    'fast': {
        'cpus': 8,
        'memory': '32G',
        'time': '24:00:00',
        'batch_size': 2048,
    },
    'hac': {
        'cpus': 16,
        'memory': '64G',
        'time': '72:00:00',
        'batch_size': 1024,
    },
    'sup': {
        'cpus': 16,
        'memory': '64G',
        'time': '144:00:00',
        'batch_size': 512,
    },
}

SLURM_TEMPLATE = """#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --account={account}
#SBATCH --partition={partition}
#SBATCH --gres={gres}
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task={cpus}
#SBATCH --mem={memory}
#SBATCH --time={time}
#SBATCH --output={logs_dir}/%x_%j.out
#SBATCH --error={logs_dir}/%x_%j.err
{mail_directives}

# ============================================
# Dorado Basecalling Job - Great Lakes HPC
# Generated: {timestamp}
# ============================================

set -euo pipefail

echo "======================================"
echo "SLURM Job Information"
echo "======================================"
echo "Job ID: $SLURM_JOB_ID"
echo "Job Name: $SLURM_JOB_NAME"
echo "Node: $SLURM_NODELIST"
echo "Partition: $SLURM_JOB_PARTITION"
echo "Start Time: $(date)"
echo "Working Directory: $(pwd)"
echo ""

# GPU Information
echo "GPU Information:"
nvidia-smi
echo ""
echo "CUDA_VISIBLE_DEVICES: ${{CUDA_VISIBLE_DEVICES:-not set}}"
echo ""

# Create log file
mkdir -p {logs_dir}
LOG_FILE="{logs_dir}/dorado_${{SLURM_JOB_ID}}.log"

log_msg() {{
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${{LOG_FILE}}"
}}

log_msg "Starting dorado basecalling"
log_msg "Model: {model}"
log_msg "Input: {input_path}"
log_msg "Output: {output_path}"

# Ensure output directory exists
mkdir -p "$(dirname {output_path})"

# Run dorado basecaller
log_msg "Executing: {dorado_cmd}"

{dorado_cmd} 2>&1 | tee -a "${{LOG_FILE}}"
EXIT_CODE=${{PIPESTATUS[0]}}

if [ $EXIT_CODE -eq 0 ]; then
    log_msg "Basecalling completed successfully"

    # Generate BAM statistics if samtools available
    if command -v samtools &> /dev/null && [[ "{output_path}" == *.bam ]]; then
        log_msg "Generating BAM statistics..."
        samtools index "{output_path}" 2>/dev/null || true
        samtools flagstat "{output_path}" > "{output_path_stem}_flagstat.txt" 2>/dev/null || true
        samtools stats "{output_path}" > "{output_path_stem}_stats.txt" 2>/dev/null || true
        log_msg "Statistics generated"
    fi

    # Report output size
    OUTPUT_SIZE=$(ls -lh "{output_path}" 2>/dev/null | awk '{{print $5}}' || echo "unknown")
    log_msg "Output file size: $OUTPUT_SIZE"
else
    log_msg "ERROR: Basecalling failed with exit code $EXIT_CODE"
fi

echo ""
echo "======================================"
echo "Job Summary"
echo "======================================"
echo "End Time: $(date)"
echo "Total Runtime: $SECONDS seconds"
echo "Exit Code: $EXIT_CODE"
echo "Log File: ${{LOG_FILE}}"
echo "Output: {output_path}"

exit $EXIT_CODE
"""


def parse_model_string(model_str: str) -> dict:
    """Parse model string into components"""
    result = {
        'tier': 'hac',
        'version': 'v5.0.0',
        'full_name': model_str,
    }

    # Simple tier name
    if model_str.lower() in MODEL_TIERS:
        result['tier'] = model_str.lower()
        return result

    # tier@version format
    if '@' in model_str:
        parts = model_str.split('@')
        if parts[0].lower() in MODEL_TIERS:
            result['tier'] = parts[0].lower()
            result['version'] = parts[1] if parts[1].startswith('v') else f'v{parts[1]}'
            return result

    # Extract tier from full model name
    model_lower = model_str.lower()
    for tier in ['sup', 'hac', 'fast']:
        if f'_{tier}' in model_lower:
            result['tier'] = tier
            break

    return result


def find_model_path(model_str: str) -> str:
    """Find the model path on disk"""
    model_info = parse_model_string(model_str)
    model_dir = Path(GREATLAKES_CONFIG['model_dir'])

    # Build expected model name
    base = 'dna_r10.4.1_e8.2_400bps'
    tier = model_info['tier']
    version = model_info['version']

    expected_name = f"{base}_{tier}@{version}"
    model_path = model_dir / expected_name

    if model_path.exists():
        return str(model_path)

    # Try without version
    for p in model_dir.glob(f"{base}_{tier}*"):
        if p.is_dir():
            return str(p)

    # Return full name for dorado to download
    return expected_name


def generate_slurm_script(
    input_path: Path,
    output_path: Path,
    model: str,
    email: str = None,
    job_name: str = None,
    logs_dir: str = None,
) -> str:
    """Generate SLURM batch script"""

    model_info = parse_model_string(model)
    tier = model_info['tier']
    resources = MODEL_TIERS[tier]

    model_path = find_model_path(model)

    if not job_name:
        sample_name = input_path.name if input_path.is_dir() else input_path.stem
        job_name = f"dorado_{sample_name}_{tier}"[:40]

    if not logs_dir:
        logs_dir = str(output_path.parent / 'Logs')

    # Build dorado command
    dorado_cmd = (
        f"{GREATLAKES_CONFIG['dorado_path']} basecaller "
        f"{model_path} "
        f"{input_path} "
        f"--device cuda:0 "
        f"--batchsize {resources['batch_size']} "
        f"> {output_path}"
    )

    # Mail directives
    mail_directives = ""
    if email:
        mail_directives = f"#SBATCH --mail-user={email}\n#SBATCH --mail-type=BEGIN,END,FAIL"

    # Get stem for stats files
    output_path_stem = str(output_path).replace('.bam', '')

    script = SLURM_TEMPLATE.format(
        job_name=job_name,
        account=GREATLAKES_CONFIG['account'],
        partition=GREATLAKES_CONFIG['partition'],
        gres=GREATLAKES_CONFIG['gres'],
        cpus=resources['cpus'],
        memory=resources['memory'],
        time=resources['time'],
        logs_dir=logs_dir,
        mail_directives=mail_directives,
        timestamp=datetime.now(timezone.utc).isoformat(),
        model=model_path,
        input_path=input_path,
        output_path=output_path,
        output_path_stem=output_path_stem,
        dorado_cmd=dorado_cmd,
    )

    return script


def main():
    parser = argparse.ArgumentParser(
        description='Great Lakes SLURM Job Submission Helper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s /path/to/pod5 --model sup --output output.bam
  %(prog)s /path/to/pod5 --model hac@v5.0.0 --output output.bam --dry-run
  %(prog)s /path/to/pod5 --model sup --output output.bam --email user@umich.edu
'''
    )

    parser.add_argument('input', help='POD5 directory or file')
    parser.add_argument('--model', '-m', default='hac',
                       help='Model: fast, hac, sup, or tier@version (default: hac)')
    parser.add_argument('--output', '-o', required=True,
                       help='Output BAM file path')
    parser.add_argument('--email', '-e',
                       help='Email for SLURM notifications')
    parser.add_argument('--job-name', '-j',
                       help='Custom job name')
    parser.add_argument('--logs-dir', '-l',
                       help='Directory for log files')
    parser.add_argument('--dry-run', '-n', action='store_true',
                       help='Generate script but do not submit')
    parser.add_argument('--save-script', '-s',
                       help='Save SLURM script to file')

    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    if not input_path.exists():
        print(f"Error: Input not found: {input_path}", file=sys.stderr)
        return 1

    # Generate script
    script = generate_slurm_script(
        input_path=input_path,
        output_path=output_path,
        model=args.model,
        email=args.email,
        job_name=args.job_name,
        logs_dir=args.logs_dir,
    )

    # Determine script path
    if args.save_script:
        script_path = Path(args.save_script)
    else:
        script_path = output_path.parent / f"{output_path.stem}.sbatch"

    # Write script
    script_path.parent.mkdir(parents=True, exist_ok=True)
    with open(script_path, 'w') as f:
        f.write(script)
    script_path.chmod(0o755)

    print(f"Generated SLURM script: {script_path}")

    model_info = parse_model_string(args.model)
    tier = model_info['tier']
    resources = MODEL_TIERS[tier]

    print(f"\nJob Configuration:")
    print(f"  Partition: {GREATLAKES_CONFIG['partition']}")
    print(f"  Account: {GREATLAKES_CONFIG['account']}")
    print(f"  GPU: {GREATLAKES_CONFIG['gres']}")
    print(f"  CPUs: {resources['cpus']}")
    print(f"  Memory: {resources['memory']}")
    print(f"  Time: {resources['time']}")
    print(f"  Model: {args.model} (tier: {tier})")

    if args.dry_run:
        print(f"\nDry run - script saved but not submitted")
        print(f"To submit manually: sbatch {script_path}")
        return 0

    # Submit job
    print(f"\nSubmitting job...")
    try:
        result = subprocess.run(
            ['sbatch', str(script_path)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"Job submitted: {result.stdout.strip()}")
            print(f"\nMonitor with: squeue -u $USER")
            return 0
        else:
            print(f"Submission failed: {result.stderr}", file=sys.stderr)
            print(f"Script saved to: {script_path}")
            print(f"Submit manually: sbatch {script_path}")
            return 1

    except FileNotFoundError:
        print("Note: sbatch not found (not on cluster?)")
        print(f"Script saved to: {script_path}")
        print(f"Transfer to Great Lakes and run: sbatch {script_path}")
        return 0


if __name__ == '__main__':
    sys.exit(main())
