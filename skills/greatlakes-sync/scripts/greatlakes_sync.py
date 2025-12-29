#!/usr/bin/env python3
"""
greatlakes_sync.py - Great Lakes HPC Experiment Discovery and Database Sync

Two-stage workflow for discovering experiments on Great Lakes, comparing against
the current database, getting user approval, and syncing to GitHub.

Stage 1: Discovery
    - Generate and submit SLURM job
    - Scan turbo drive for experiments
    - Generate proposal YAML + HTML visualization

Stage 2: Apply
    - Load approved proposal
    - Update local SQLite database
    - Update registry/experiments.yaml
    - Git commit and push

Usage:
    # Stage 1: Run discovery
    greatlakes_sync.py discover --submit --notify

    # Review proposal
    greatlakes_sync.py review --latest

    # Stage 2: Apply changes
    greatlakes_sync.py apply --latest --commit --push

    # Scheduling
    greatlakes_sync.py schedule install --weekly

Part of: https://github.com/Single-Molecule-Sequencing/ont-ecosystem
"""

import argparse
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add script directory to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from proposal import (
    Proposal,
    ExperimentEntry,
    compare_experiments,
    format_proposal_report,
    generate_proposal_filename,
    get_latest_proposal,
    load_database_experiments,
    load_registry_experiments,
)

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Great Lakes Configuration
GREATLAKES_CONFIG = {
    'account': 'bleu99',
    'partition': 'standard',  # CPU partition for discovery
    'turbo_base': '/nfs/turbo/umms-atheylab',
    'scan_dirs': [
        '/nfs/turbo/umms-atheylab/sequencing_data',
        '/nfs/turbo/umms-atheylab/miamon',
        '/nfs/turbo/umms-atheylab/backup_from_desktop',
    ],
    'sync_dir': '/nfs/turbo/umms-atheylab/.ont-sync',
    'db_path': '/nfs/turbo/umms-atheylab/experiments.db',
    'logs_dir': '/nfs/turbo/umms-atheylab/logs',
}

# GitHub Configuration
GITHUB_CONFIG = {
    'repo': 'Single-Molecule-Sequencing/ont-ecosystem',
    'branch': 'main',
    'registry_path': 'registry/experiments.yaml',
}

# SLURM template for discovery job
SLURM_DISCOVERY_TEMPLATE = """#!/bin/bash
#SBATCH --job-name=ont_discovery
#SBATCH --account={account}
#SBATCH --partition={partition}
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=08:00:00
#SBATCH --output={logs_dir}/discovery_%j.out
#SBATCH --error={logs_dir}/discovery_%j.err
{mail_directives}

# ============================================
# ONT Experiment Discovery Job - Great Lakes
# Generated: {timestamp}
# ============================================

set -euo pipefail

echo "======================================"
echo "Experiment Discovery Job"
echo "======================================"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "Start Time: $(date)"
echo ""

# Load Python
module load python/3.10 2>/dev/null || true

# Create directories
mkdir -p {sync_dir}/proposals
mkdir -p {logs_dir}

# Track timing
START_TIME=$(date +%s)

# Run discovery
cd {turbo_base}

python3 << 'PYTHON_SCRIPT'
import glob
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SCAN_DIRS = {scan_dirs_json}
PROPOSAL_PATH = "{proposal_path}"
DB_PATH = "{db_path}"

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

def load_database():
    import sqlite3
    if not os.path.exists(DB_PATH):
        return {{}}
    experiments = {{}}
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT experiment_path, sample_id, flow_cell_id, pod5_files, fastq_files, bam_files
            FROM experiments
        ''')
        for row in cursor.fetchall():
            experiments[row[0]] = {{
                'path': row[0],
                'sample_id': row[1] or '',
                'flow_cell_id': row[2] or '',
                'pod5_files': row[3] or 0,
                'fastq_files': row[4] or 0,
                'bam_files': row[5] or 0,
            }}
        conn.close()
    except Exception as e:
        print(f"Warning: Could not load database: {{e}}")
    return experiments

# Discover experiments
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
            'sample_id': metadata.get('sample_id', ''),
            'flow_cell_id': metadata.get('flow_cell_id', ''),
            'protocol_group_id': metadata.get('protocol_group_id', ''),
            'protocol': metadata.get('protocol', ''),
            'instrument': metadata.get('instrument', ''),
            'started': metadata.get('started', ''),
            'acquisition_stopped': metadata.get('acquisition_stopped', ''),
            'metadata_source': 'final_summary',
            'pod5_files': pod5_count,
            'fast5_files': fast5_count,
            'fastq_files': fastq_count,
            'bam_files': bam_count,
            'discovered_at': datetime.now(timezone.utc).isoformat(),
        }})

        sample = metadata.get('sample_id', 'unknown')
        print(f"  Found: {{sample}} ({{exp_dir}})")

print(f"\\nDiscovered {{len(experiments)}} experiments")

# Load current database
current_db = load_database()
print(f"Current database: {{len(current_db)}} experiments")

# Compare and categorize
new_exps = []
updated_exps = []
unchanged_exps = []

for exp in experiments:
    path = exp['path']
    if path not in current_db:
        new_exps.append(exp)
    else:
        curr = current_db[path]
        changes = []
        for field in ['pod5_files', 'fastq_files', 'bam_files']:
            if exp.get(field, 0) != curr.get(field, 0):
                changes.append({{
                    'field': field,
                    'old_value': curr.get(field, 0),
                    'new_value': exp.get(field, 0),
                }})
        if changes:
            exp['changes'] = changes
            updated_exps.append(exp)
        else:
            unchanged_exps.append(exp)

# Check for removed
removed_exps = []
discovered_paths = set(e['path'] for e in experiments)
for path, curr in current_db.items():
    if path not in discovered_paths:
        if not os.path.isdir(path):
            removed_exps.append({{
                'id': curr.get('id', ''),
                'path': path,
                'sample_id': curr.get('sample_id', ''),
                'removal_reason': 'directory_not_found',
            }})

# Create proposal
proposal = {{
    'version': '1.0',
    'generated_at': datetime.now(timezone.utc).isoformat(),
    'slurm_job_id': os.environ.get('SLURM_JOB_ID', ''),
    'slurm_node': os.environ.get('SLURM_NODELIST', ''),
    'scan_paths': SCAN_DIRS,
    'summary': {{
        'total_discovered': len(experiments),
        'current_in_registry': len(current_db),
        'new_count': len(new_exps),
        'updated_count': len(updated_exps),
        'removed_count': len(removed_exps),
        'unchanged_count': len(unchanged_exps),
    }},
    'changes': {{
        'new': new_exps,
        'updated': updated_exps,
        'removed': removed_exps,
    }},
    'unchanged_count': len(unchanged_exps),
    'approval_status': 'pending',
    'approved_at': None,
    'approved_by': None,
    'applied_at': None,
}}

# Save proposal
import yaml
with open(PROPOSAL_PATH, 'w') as f:
    yaml.dump(proposal, f, default_flow_style=False, sort_keys=False)

print(f"\\nProposal saved to: {{PROPOSAL_PATH}}")
print(f"  New: {{len(new_exps)}}")
print(f"  Updated: {{len(updated_exps)}}")
print(f"  Removed: {{len(removed_exps)}}")
print(f"  Unchanged: {{len(unchanged_exps)}}")
PYTHON_SCRIPT

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "======================================"
echo "Discovery Complete"
echo "======================================"
echo "Duration: ${{DURATION}}s"
echo "End Time: $(date)"
echo "Proposal: {proposal_path}"

# Generate HTML visualization
python3 {visualize_script} --proposal {proposal_path} --output {html_path}

echo "HTML Report: {html_path}"
"""


def parse_final_summary(filepath: Path) -> Dict[str, Any]:
    """Parse final_summary.txt file into a dictionary."""
    data = {}
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


def find_experiments_local(scan_dirs: List[str]) -> List[Dict[str, Any]]:
    """Find all nanopore experiment directories by scanning for final_summary files."""
    experiments = []
    seen: set = set()

    for scan_dir in scan_dirs:
        if not os.path.isdir(scan_dir):
            print(f"Skipping non-existent directory: {scan_dir}")
            continue

        print(f"Scanning: {scan_dir}")
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

            experiment = {
                'id': exp_id,
                'path': exp_dir,
                'sample_id': metadata.get('sample_id', ''),
                'flow_cell_id': metadata.get('flow_cell_id', ''),
                'protocol_group_id': metadata.get('protocol_group_id', ''),
                'protocol': metadata.get('protocol', ''),
                'instrument': metadata.get('instrument', ''),
                'started': metadata.get('started', ''),
                'acquisition_stopped': metadata.get('acquisition_stopped', ''),
                'metadata_source': 'final_summary',
                'pod5_files': pod5_count,
                'fast5_files': fast5_count,
                'fastq_files': fastq_count,
                'bam_files': bam_count,
                'discovered_at': datetime.now(timezone.utc).isoformat(),
            }

            experiments.append(experiment)
            print(f"  Found: {metadata.get('sample_id', 'unknown')} ({exp_dir})")

    return experiments


def generate_slurm_script(
    output_path: Path,
    notify_email: Optional[str] = None
) -> Path:
    """Generate SLURM discovery job script."""
    timestamp = datetime.now(timezone.utc).isoformat()
    proposal_name = generate_proposal_filename()
    proposal_path = f"{GREATLAKES_CONFIG['sync_dir']}/proposals/{proposal_name}"
    html_path = proposal_path.replace('.yaml', '.html')

    mail_directives = ""
    if notify_email:
        mail_directives = f"""#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user={notify_email}"""

    script = SLURM_DISCOVERY_TEMPLATE.format(
        account=GREATLAKES_CONFIG['account'],
        partition=GREATLAKES_CONFIG['partition'],
        logs_dir=GREATLAKES_CONFIG['logs_dir'],
        turbo_base=GREATLAKES_CONFIG['turbo_base'],
        sync_dir=GREATLAKES_CONFIG['sync_dir'],
        db_path=GREATLAKES_CONFIG['db_path'],
        scan_dirs_json=json.dumps(GREATLAKES_CONFIG['scan_dirs']),
        proposal_path=proposal_path,
        html_path=html_path,
        visualize_script=SCRIPT_DIR / 'visualize.py',
        timestamp=timestamp,
        mail_directives=mail_directives,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(script)
    os.chmod(output_path, 0o755)

    return output_path


def submit_slurm_job(script_path: Path) -> Optional[str]:
    """Submit SLURM job and return job ID."""
    try:
        result = subprocess.run(
            ['sbatch', str(script_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0 and 'Submitted batch job' in result.stdout:
            job_id = result.stdout.strip().split()[-1]
            return job_id
        print(f"Error submitting job: {result.stderr}")
        return None
    except subprocess.TimeoutExpired:
        print("Error: sbatch command timed out")
        return None
    except FileNotFoundError:
        print("Error: sbatch not found. Are you on Great Lakes?")
        return None


def update_registry(
    proposal: Proposal,
    registry_path: Path,
    repo_path: Optional[Path] = None
) -> bool:
    """
    Update the experiments registry with approved changes.

    Args:
        proposal: Approved proposal
        registry_path: Path to experiments.yaml
        repo_path: Path to git repo root (for commit/push)

    Returns:
        True if successful
    """
    if not HAS_YAML:
        print("Error: PyYAML required for registry updates")
        return False

    # Load current registry
    registry = {'version': '3.0', 'experiments': []}
    if registry_path.exists():
        with open(registry_path, 'r') as f:
            registry = yaml.safe_load(f) or registry

    experiments = registry.get('experiments', [])
    exp_by_path = {e.get('location', e.get('path', '')): e for e in experiments}

    # Apply new experiments
    for exp in proposal.new:
        if exp.path not in exp_by_path:
            experiments.append({
                'id': exp.id,
                'location': exp.path,
                'sample_id': exp.sample_id,
                'flow_cell_id': exp.flow_cell_id,
                'platform': exp.instrument,
                'status': 'discovered',
                'source': 'greatlakes',
                'discovered': exp.discovered_at,
                'pod5_files': exp.pod5_files,
                'fast5_files': exp.fast5_files,
                'fastq_files': exp.fastq_files,
                'bam_files': exp.bam_files,
            })

    # Apply updates
    for exp in proposal.updated:
        if exp.path in exp_by_path:
            entry = exp_by_path[exp.path]
            entry['pod5_files'] = exp.pod5_files
            entry['fast5_files'] = exp.fast5_files
            entry['fastq_files'] = exp.fastq_files
            entry['bam_files'] = exp.bam_files
            entry['updated'] = datetime.now(timezone.utc).isoformat()

    # Mark removed as archived (soft delete)
    for exp in proposal.removed:
        if exp.path in exp_by_path:
            entry = exp_by_path[exp.path]
            entry['status'] = 'archived'
            entry['archived_reason'] = exp.removal_reason
            entry['archived'] = datetime.now(timezone.utc).isoformat()

    # Update registry metadata
    registry['experiments'] = experiments
    registry['updated'] = datetime.now(timezone.utc).isoformat()
    registry['stats'] = {
        'total_experiments': len([e for e in experiments if e.get('status') != 'archived']),
    }

    # Write registry
    with open(registry_path, 'w') as f:
        yaml.dump(registry, f, default_flow_style=False, sort_keys=False)

    print(f"Updated registry: {registry_path}")
    return True


def git_commit_and_push(
    repo_path: Path,
    files: List[str],
    message: str,
    push: bool = False
) -> bool:
    """Commit and optionally push changes to git."""
    try:
        # Add files
        for file in files:
            subprocess.run(
                ['git', 'add', file],
                cwd=repo_path,
                check=True,
                capture_output=True
            )

        # Commit
        full_message = f"""{message}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: greatlakes-sync <noreply@anthropic.com>"""

        subprocess.run(
            ['git', 'commit', '-m', full_message],
            cwd=repo_path,
            check=True,
            capture_output=True
        )
        print("Created commit")

        # Push
        if push:
            subprocess.run(
                ['git', 'push'],
                cwd=repo_path,
                check=True,
                capture_output=True
            )
            print("Pushed to remote")

        return True
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e.stderr.decode() if e.stderr else str(e)}")
        return False


# ============================================================================
# CLI Commands
# ============================================================================

def cmd_discover(args) -> int:
    """Generate and optionally submit SLURM discovery job."""
    print("=" * 60)
    print("Great Lakes Experiment Discovery")
    print("=" * 60)
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print()

    # Generate SLURM script
    script_path = Path(GREATLAKES_CONFIG['sync_dir']) / 'discovery_job.sbatch'
    generate_slurm_script(script_path, notify_email=args.notify)
    print(f"Generated SLURM script: {script_path}")

    if args.dry_run:
        print("\n--dry-run specified. Script not submitted.")
        print(f"To submit: sbatch {script_path}")
        return 0

    if args.submit:
        print("\nSubmitting job...")
        job_id = submit_slurm_job(script_path)
        if job_id:
            print(f"Submitted job: {job_id}")
            print(f"Monitor with: squeue -j {job_id}")
            print(f"Logs: {GREATLAKES_CONFIG['logs_dir']}/discovery_{job_id}.out")
        else:
            print("Failed to submit job")
            return 1
    else:
        print(f"\nTo submit: sbatch {script_path}")

    return 0


def cmd_discover_local(args) -> int:
    """Run discovery locally (for testing or direct execution)."""
    print("Running local discovery...")
    start_time = time.time()

    experiments = find_experiments_local(args.scan_dirs or GREATLAKES_CONFIG['scan_dirs'])
    print(f"\nDiscovered {len(experiments)} experiments")

    # Load current database
    db_path = args.db_path or GREATLAKES_CONFIG['db_path']
    current_db = load_database_experiments(db_path)
    print(f"Current database: {len(current_db)} experiments")

    # Compare
    proposal = compare_experiments(experiments, current_db)
    proposal.scan_duration_seconds = time.time() - start_time
    proposal.scan_paths = args.scan_dirs or GREATLAKES_CONFIG['scan_dirs']

    # Save proposal
    proposals_dir = Path(args.output_dir or f"{GREATLAKES_CONFIG['sync_dir']}/proposals")
    proposals_dir.mkdir(parents=True, exist_ok=True)
    proposal_path = proposals_dir / generate_proposal_filename()
    proposal.save(proposal_path)

    print(f"\nProposal saved: {proposal_path}")
    print(format_proposal_report(proposal))

    # Generate HTML
    html_path = proposal_path.with_suffix('.html')
    try:
        from visualize import generate_proposal_html
        generate_proposal_html(proposal, html_path)
        print(f"HTML report: {html_path}")
    except ImportError:
        print("Warning: visualize.py not available, skipping HTML generation")

    return 0


def cmd_review(args) -> int:
    """Review a discovery proposal."""
    proposals_dir = Path(GREATLAKES_CONFIG['sync_dir']) / 'proposals'

    if args.latest:
        proposal_path = get_latest_proposal(proposals_dir)
        if not proposal_path:
            print("No proposals found")
            return 1
    elif args.proposal:
        proposal_path = Path(args.proposal)
    else:
        print("Specify --latest or --proposal PATH")
        return 1

    if not proposal_path.exists():
        print(f"Proposal not found: {proposal_path}")
        return 1

    proposal = Proposal.load(proposal_path)
    print(format_proposal_report(proposal))

    if args.browser:
        html_path = proposal_path.with_suffix('.html')
        if html_path.exists():
            import webbrowser
            webbrowser.open(f"file://{html_path}")
        else:
            print(f"HTML not found: {html_path}")

    return 0


def cmd_apply(args) -> int:
    """Apply approved changes to database and registry."""
    proposals_dir = Path(GREATLAKES_CONFIG['sync_dir']) / 'proposals'

    if args.latest:
        proposal_path = get_latest_proposal(proposals_dir)
        if not proposal_path:
            print("No proposals found")
            return 1
    elif args.proposal:
        proposal_path = Path(args.proposal)
    else:
        print("Specify --latest or --proposal PATH")
        return 1

    if not proposal_path.exists():
        print(f"Proposal not found: {proposal_path}")
        return 1

    proposal = Proposal.load(proposal_path)

    # Check approval
    if proposal.approval_status != 'approved' and not args.force:
        print("Proposal not approved. Use --force to apply anyway.")
        print(f"Current status: {proposal.approval_status}")

        # Prompt for approval
        response = input("Approve and apply? [y/N]: ").strip().lower()
        if response != 'y':
            print("Aborted")
            return 1
        proposal.approve()

    print("Applying changes...")

    # Find repo path
    repo_path = Path(__file__).parent.parent.parent.parent
    registry_path = repo_path / GITHUB_CONFIG['registry_path']

    # Update registry
    if not update_registry(proposal, registry_path, repo_path):
        print("Failed to update registry")
        return 1

    proposal.mark_applied()
    proposal.save(proposal_path)

    # Git commit
    if args.commit:
        summary = proposal.summary
        message = f"""Update experiment registry from Great Lakes discovery

- Added: {summary.new_count} new experiments
- Updated: {summary.updated_count} experiments
- Removed: {summary.removed_count} experiments

SLURM Job: {proposal.slurm_job_id}
Discovery: {proposal.generated_at}"""

        if git_commit_and_push(
            repo_path,
            [GITHUB_CONFIG['registry_path']],
            message,
            push=args.push
        ):
            print("Changes committed")
        else:
            print("Warning: Git commit failed")

    # Archive proposal
    approved_dir = Path(GREATLAKES_CONFIG['sync_dir']) / 'approved'
    approved_dir.mkdir(parents=True, exist_ok=True)
    archive_path = approved_dir / proposal_path.name
    shutil.copy(proposal_path, archive_path)
    print(f"Archived to: {archive_path}")

    print("\nChanges applied successfully!")
    return 0


def cmd_schedule(args) -> int:
    """Manage scheduled discovery jobs."""
    from schedule import install_cron, remove_cron, show_status

    if args.action == 'install':
        return install_cron(
            weekly=args.weekly,
            day=args.day,
            hour=args.hour,
            notify_email=args.notify
        )
    elif args.action == 'remove':
        return remove_cron()
    elif args.action == 'status':
        return show_status()

    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Great Lakes Experiment Discovery and Sync',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Stage 1: Run discovery on Great Lakes
  greatlakes_sync.py discover --submit --notify user@umich.edu

  # Review the latest proposal
  greatlakes_sync.py review --latest --browser

  # Stage 2: Apply approved changes
  greatlakes_sync.py apply --latest --commit --push

  # Schedule weekly discovery
  greatlakes_sync.py schedule install --weekly --day sunday --hour 2
"""
    )

    subparsers = parser.add_subparsers(dest='command', help='Command')

    # discover command
    discover_parser = subparsers.add_parser('discover', help='Generate/submit discovery job')
    discover_parser.add_argument('--submit', action='store_true',
                                 help='Submit SLURM job after generating')
    discover_parser.add_argument('--notify', metavar='EMAIL',
                                 help='Email for job notifications')
    discover_parser.add_argument('--dry-run', action='store_true',
                                 help='Generate script without submitting')

    # discover-local command (for testing)
    local_parser = subparsers.add_parser('discover-local', help='Run discovery locally')
    local_parser.add_argument('--scan-dirs', nargs='+', help='Directories to scan')
    local_parser.add_argument('--db-path', help='Database path for comparison')
    local_parser.add_argument('--output-dir', help='Output directory for proposal')

    # review command
    review_parser = subparsers.add_parser('review', help='Review a proposal')
    review_parser.add_argument('--proposal', '-p', help='Path to proposal YAML')
    review_parser.add_argument('--latest', action='store_true',
                               help='Review most recent proposal')
    review_parser.add_argument('--browser', action='store_true',
                               help='Open HTML in browser')

    # apply command
    apply_parser = subparsers.add_parser('apply', help='Apply approved changes')
    apply_parser.add_argument('--proposal', '-p', help='Path to proposal YAML')
    apply_parser.add_argument('--latest', action='store_true',
                              help='Apply most recent proposal')
    apply_parser.add_argument('--force', action='store_true',
                              help='Apply without approval check')
    apply_parser.add_argument('--commit', action='store_true',
                              help='Git commit changes')
    apply_parser.add_argument('--push', action='store_true',
                              help='Git push after commit')

    # schedule command
    schedule_parser = subparsers.add_parser('schedule', help='Manage scheduled jobs')
    schedule_parser.add_argument('action', choices=['install', 'remove', 'status'],
                                 help='Schedule action')
    schedule_parser.add_argument('--weekly', action='store_true',
                                 help='Run weekly')
    schedule_parser.add_argument('--day', default='sunday',
                                 help='Day of week (default: sunday)')
    schedule_parser.add_argument('--hour', type=int, default=2,
                                 help='Hour to run (default: 2)')
    schedule_parser.add_argument('--notify', metavar='EMAIL',
                                 help='Email for notifications')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        'discover': cmd_discover,
        'discover-local': cmd_discover_local,
        'review': cmd_review,
        'apply': cmd_apply,
        'schedule': cmd_schedule,
    }

    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
