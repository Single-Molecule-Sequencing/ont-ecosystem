#!/usr/bin/env python3
"""
sync_greatlakes.py - Full Experiment Discovery and Sync Workflow

Orchestrates the complete workflow for discovering experiments on Great Lakes,
comparing against the database, getting user approval, and syncing to GitHub.

Usage:
    # Run full discovery and sync workflow
    python3 sync_greatlakes.py

    # Just generate the discovery job without submitting
    python3 sync_greatlakes.py --generate-only

    # Skip discovery and just compare existing manifest
    python3 sync_greatlakes.py --manifest /path/to/manifest.json

Part of: https://github.com/Single-Molecule-Sequencing/ont-ecosystem
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Import from local module
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from greatlakes_discovery import (
    GREATLAKES_CONFIG,
    find_experiments_local,
    load_current_database,
    compare_experiments,
    format_diff_report,
    export_for_github,
    export_manifest,
)


def run_ssh_command(cmd: str, timeout: int = 300) -> tuple:
    """Run command on Great Lakes via SSH."""
    ssh_cmd = f'ssh greatlakes "{cmd}"'
    try:
        result = subprocess.run(
            ssh_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"


def submit_slurm_job(script_path: str) -> str:
    """Submit SLURM job and return job ID."""
    code, stdout, stderr = run_ssh_command(f"sbatch {script_path}")
    if code == 0 and "Submitted batch job" in stdout:
        # Extract job ID
        job_id = stdout.strip().split()[-1]
        return job_id
    raise RuntimeError(f"Failed to submit job: {stderr}")


def wait_for_job(job_id: str, timeout: int = 3600) -> bool:
    """Wait for SLURM job to complete."""
    import time
    start = time.time()

    while time.time() - start < timeout:
        code, stdout, _ = run_ssh_command(f"squeue -j {job_id} -h")
        if code != 0 or not stdout.strip():
            # Job completed
            return True
        time.sleep(30)

    return False


def check_job_status(job_id: str) -> dict:
    """Get final job status from sacct."""
    code, stdout, _ = run_ssh_command(
        f"sacct -j {job_id} --format=JobID,State,ExitCode -n -P"
    )
    if code == 0 and stdout.strip():
        parts = stdout.strip().split('\n')[0].split('|')
        return {
            'job_id': parts[0] if len(parts) > 0 else '',
            'state': parts[1] if len(parts) > 1 else '',
            'exit_code': parts[2] if len(parts) > 2 else '',
        }
    return {'state': 'UNKNOWN'}


def generate_slurm_discovery_script() -> str:
    """Generate SLURM script for discovery job."""
    timestamp = datetime.now(timezone.utc).isoformat()
    logs_dir = f"{GREATLAKES_CONFIG['turbo_base']}/logs"
    manifest_path = GREATLAKES_CONFIG['manifest_path']
    db_path = GREATLAKES_CONFIG['db_path']
    scan_dirs = GREATLAKES_CONFIG['scan_dirs']

    script = f"""#!/bin/bash
#SBATCH --job-name=ont_discovery
#SBATCH --account={GREATLAKES_CONFIG['account']}
#SBATCH --partition=standard
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output={logs_dir}/discovery_%j.out
#SBATCH --error={logs_dir}/discovery_%j.err

# ONT Experiment Discovery Job
# Generated: {timestamp}

set -euo pipefail

echo "======================================"
echo "Experiment Discovery Job"
echo "======================================"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "Start: $(date)"

# Load Python
module load python/3.10 2>/dev/null || true

# Create logs directory
mkdir -p {logs_dir}

# Run discovery
cd /nfs/turbo/umms-atheylab

# Use Python to scan directories
python3 << 'PYTHON_SCRIPT'
import json
import os
import glob
import hashlib
from datetime import datetime, timezone
from pathlib import Path

SCAN_DIRS = {json.dumps(scan_dirs)}
OUTPUT = "{manifest_path}"

def parse_final_summary(filepath):
    data = {{}}
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line:
                    key, value = line.split('=', 1)
                    data[key] = value
    except Exception:
        pass
    return data

experiments = []
seen = set()

for scan_dir in SCAN_DIRS:
    if not os.path.isdir(scan_dir):
        print(f"Skipping: {{scan_dir}}")
        continue

    print(f"Scanning: {{scan_dir}}")
    pattern = os.path.join(scan_dir, '**', 'final_summary*.txt')

    for summary_path in glob.glob(pattern, recursive=True):
        exp_dir = os.path.dirname(summary_path)
        if exp_dir in seen:
            continue
        seen.add(exp_dir)

        metadata = parse_final_summary(Path(summary_path))

        pod5_count = len(glob.glob(os.path.join(exp_dir, '**', '*.pod5'), recursive=True))
        fast5_count = len(glob.glob(os.path.join(exp_dir, '**', '*.fast5'), recursive=True))
        fastq_count = len(glob.glob(os.path.join(exp_dir, '**', '*.fastq*'), recursive=True))
        bam_count = len(glob.glob(os.path.join(exp_dir, '**', '*.bam'), recursive=True))

        exp_id = hashlib.md5(exp_dir.encode()).hexdigest()[:12]

        experiments.append({{
            'id': exp_id,
            'path': exp_dir,
            'summary_file': summary_path,
            'instrument': metadata.get('instrument', ''),
            'flow_cell_id': metadata.get('flow_cell_id', ''),
            'sample_id': metadata.get('sample_id', ''),
            'protocol_group_id': metadata.get('protocol_group_id', ''),
            'protocol': metadata.get('protocol', ''),
            'started': metadata.get('started', ''),
            'acquisition_stopped': metadata.get('acquisition_stopped', ''),
            'pod5_files': pod5_count,
            'fast5_files': fast5_count,
            'fastq_files': fastq_count,
            'bam_files': bam_count,
            'discovered_at': datetime.now(timezone.utc).isoformat(),
        }})

        sample = metadata.get('sample_id', 'unknown')
        print(f"  Found: {{sample}} ({{exp_dir}})")

manifest = {{
    'version': '1.0',
    'generated_at': datetime.now(timezone.utc).isoformat(),
    'scan_dirs': SCAN_DIRS,
    'total_experiments': len(experiments),
    'experiments': experiments,
}}

with open(OUTPUT, 'w') as f:
    json.dump(manifest, f, indent=2)

print(f"\\nExported {{len(experiments)}} experiments to {{OUTPUT}}")
PYTHON_SCRIPT

echo ""
echo "======================================"
echo "Discovery Complete"
echo "======================================"
echo "End: $(date)"
echo "Manifest: {manifest_path}"
"""

    return script


def run_discovery_workflow(args):
    """Run the full discovery workflow."""
    print("=" * 60)
    print("ONT Experiment Discovery and Sync Workflow")
    print("=" * 60)
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print()

    manifest_path = args.manifest or GREATLAKES_CONFIG['manifest_path']
    db_path = args.db_path or GREATLAKES_CONFIG['db_path']

    # Step 1: Discovery
    if not args.manifest:
        print("STEP 1: Discovering experiments on Great Lakes")
        print("-" * 40)

        # Generate SLURM script
        script_content = generate_slurm_discovery_script()
        script_path = f"{GREATLAKES_CONFIG['turbo_base']}/discovery_job.sbatch"

        # Write script to turbo drive (accessible from both local and HPC)
        with open(script_path, 'w') as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        print(f"Generated SLURM script: {script_path}")

        if args.generate_only:
            print("\n--generate-only specified, stopping here.")
            print(f"Submit manually: sbatch {script_path}")
            return 0

        # Submit job
        print("Submitting discovery job...")
        try:
            job_id = submit_slurm_job(script_path)
            print(f"Submitted job: {job_id}")
        except RuntimeError as e:
            print(f"Error: {e}")
            print(f"\nSubmit manually: ssh greatlakes 'sbatch {script_path}'")
            return 1

        # Wait for completion
        print("Waiting for job to complete...")
        if not wait_for_job(job_id, timeout=3600):
            print("Job timed out. Check status manually.")
            return 1

        status = check_job_status(job_id)
        print(f"Job completed: {status['state']}")

        if status['state'] != 'COMPLETED':
            print(f"Job failed with state: {status['state']}")
            return 1

    # Step 2: Load and compare
    print("\nSTEP 2: Comparing discoveries to database")
    print("-" * 40)

    if not os.path.exists(manifest_path):
        print(f"Error: Manifest not found: {manifest_path}")
        return 1

    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    discovered = manifest.get('experiments', [])
    print(f"Loaded {len(discovered)} discovered experiments")

    current = {}
    if os.path.exists(db_path):
        current = load_current_database(db_path)
        print(f"Loaded {len(current)} experiments from database")
    else:
        print("No existing database found")

    comparison = compare_experiments(discovered, current)

    # Step 3: Show diff and ask for approval
    print("\nSTEP 3: Proposed Changes")
    print("-" * 40)

    report = format_diff_report(comparison)
    print(report)

    summary = comparison['summary']
    if summary['new_count'] == 0 and summary['updated_count'] == 0:
        print("\nNo changes to apply.")
        return 0

    # Save report
    report_path = manifest_path.replace('.json', '_diff.txt')
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"\nDiff report saved to: {report_path}")

    # Step 4: User approval
    print("\nSTEP 4: Approval Required")
    print("-" * 40)
    print(f"New experiments: {summary['new_count']}")
    print(f"Updated experiments: {summary['updated_count']}")
    print()

    if not args.auto_approve:
        response = input("Apply these changes? [y/N]: ").strip().lower()
        if response != 'y':
            print("Changes not approved. Exiting.")
            return 0

    # Step 5: Apply changes
    print("\nSTEP 5: Applying Changes")
    print("-" * 40)

    # Export GitHub snapshot
    github_snapshot = manifest_path.replace('.json', '_github.json')
    export_for_github(comparison, github_snapshot)
    print(f"GitHub snapshot: {github_snapshot}")

    # Copy to repo registry
    repo_registry = Path(__file__).parent.parent.parent.parent / 'registry' / 'experiments_snapshot.json'
    if repo_registry.parent.exists():
        import shutil
        shutil.copy(github_snapshot, repo_registry)
        print(f"Updated repo: {repo_registry}")

    print("\nSTEP 6: GitHub Sync Instructions")
    print("-" * 40)
    print("To sync to GitHub, run:")
    print("  cd /data2/repos/ont-ecosystem")
    print("  git add registry/experiments_snapshot.json")
    print('  git commit -m "Update experiment registry from Great Lakes discovery"')
    print("  git push")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Full experiment discovery and sync workflow',
    )
    parser.add_argument('--manifest', '-m',
                       help='Use existing manifest (skip discovery)')
    parser.add_argument('--db-path',
                       help='Database path for comparison')
    parser.add_argument('--generate-only', action='store_true',
                       help='Generate SLURM script only, do not submit')
    parser.add_argument('--auto-approve', action='store_true',
                       help='Auto-approve changes without prompting')

    args = parser.parse_args()
    return run_discovery_workflow(args)


if __name__ == '__main__':
    sys.exit(main())
