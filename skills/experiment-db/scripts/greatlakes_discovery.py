#!/usr/bin/env python3
"""
greatlakes_discovery.py - Experiment Discovery and Database Sync for Great Lakes HPC

Discovers nanopore experiments on the Athey Lab turbo drive, compares against
the current database, proposes updates for user approval, and syncs to GitHub.

Workflow:
1. Scan turbo drive for experiments (runs as SLURM job on Great Lakes)
2. Export findings to JSON manifest
3. Compare against current database
4. Generate diff showing proposed changes
5. User approves changes
6. Update local database and sync to GitHub

Usage:
    # Generate discovery SLURM job and submit
    python3 greatlakes_discovery.py scan --submit

    # Compare discovered experiments to current database
    python3 greatlakes_discovery.py compare --manifest discovered.json

    # Apply approved changes and sync to GitHub
    python3 greatlakes_discovery.py sync --manifest discovered.json --approved

Part of: https://github.com/Single-Molecule-Sequencing/ont-ecosystem
"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib

# Great Lakes Configuration
GREATLAKES_CONFIG = {
    'partition': 'standard',  # Use standard partition for discovery (no GPU needed)
    'account': 'bleu99',
    'turbo_base': '/nfs/turbo/umms-atheylab',
    'scan_dirs': [
        '/nfs/turbo/umms-atheylab/sequencing_data',
        '/nfs/turbo/umms-atheylab/miamon',
        '/nfs/turbo/umms-atheylab/backup_from_desktop',
    ],
    'db_path': '/nfs/turbo/umms-atheylab/experiments.db',
    'manifest_path': '/nfs/turbo/umms-atheylab/experiment_manifest.json',
    'registry_path': '/nfs/turbo/umms-atheylab/experiments_registry.yaml',
}

# GitHub Configuration
GITHUB_CONFIG = {
    'repo': 'Single-Molecule-Sequencing/ont-ecosystem',
    'branch': 'main',
    'registry_path': 'registry/experiments.yaml',
    'db_snapshot_path': 'registry/experiments_snapshot.json',
}

SLURM_SCAN_TEMPLATE = """#!/bin/bash
#SBATCH --job-name=ont_discovery
#SBATCH --account={account}
#SBATCH --partition={partition}
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output={logs_dir}/discovery_%j.out
#SBATCH --error={logs_dir}/discovery_%j.err

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

# Load Python if needed
module load python/3.10 2>/dev/null || true

# Run discovery script
cd {script_dir}
python3 {script_path} scan-local \\
    --output {manifest_path} \\
    --db-path {db_path} \\
    {scan_dirs}

echo ""
echo "======================================"
echo "Discovery Complete"
echo "======================================"
echo "End Time: $(date)"
echo "Manifest: {manifest_path}"
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
    except Exception as e:
        pass
    return data


def find_experiments_local(scan_dirs: List[str]) -> List[Dict[str, Any]]:
    """
    Find all nanopore experiment directories by looking for final_summary files.

    Args:
        scan_dirs: List of directories to scan

    Returns:
        List of experiment metadata dicts
    """
    import glob

    experiments = []
    seen_paths = set()

    for scan_dir in scan_dirs:
        if not os.path.isdir(scan_dir):
            print(f"Skipping non-existent directory: {scan_dir}")
            continue

        print(f"Scanning: {scan_dir}")

        # Find all final_summary files
        pattern = os.path.join(scan_dir, '**', 'final_summary*.txt')
        summary_files = glob.glob(pattern, recursive=True)

        for summary_path in summary_files:
            exp_dir = os.path.dirname(summary_path)

            # Skip duplicates
            if exp_dir in seen_paths:
                continue
            seen_paths.add(exp_dir)

            # Parse metadata
            metadata = parse_final_summary(Path(summary_path))

            # Count data files
            pod5_count = len(glob.glob(os.path.join(exp_dir, '**', '*.pod5'), recursive=True))
            fast5_count = len(glob.glob(os.path.join(exp_dir, '**', '*.fast5'), recursive=True))
            fastq_count = len(glob.glob(os.path.join(exp_dir, '**', '*.fastq*'), recursive=True))
            bam_count = len(glob.glob(os.path.join(exp_dir, '**', '*.bam'), recursive=True))

            # Generate experiment ID from path
            exp_id = hashlib.md5(exp_dir.encode()).hexdigest()[:12]

            experiment = {
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
            }

            experiments.append(experiment)
            print(f"  Found: {metadata.get('sample_id', 'unknown')} ({exp_dir})")

    return experiments


def load_current_database(db_path: str) -> Dict[str, Dict]:
    """
    Load current experiments from SQLite database.

    Returns:
        Dict mapping experiment path to metadata
    """
    if not os.path.exists(db_path):
        return {}

    experiments = {}
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT experiment_path, sample_id, flow_cell_id, protocol_group_id,
                   started, pod5_files, fastq_files, bam_files
            FROM experiments
        """)

        for row in cursor.fetchall():
            experiments[row[0]] = {
                'path': row[0],
                'sample_id': row[1],
                'flow_cell_id': row[2],
                'protocol_group_id': row[3],
                'started': row[4],
                'pod5_files': row[5],
                'fastq_files': row[6],
                'bam_files': row[7],
            }
    except sqlite3.OperationalError:
        pass

    conn.close()
    return experiments


def compare_experiments(discovered: List[Dict], current: Dict[str, Dict]) -> Dict[str, Any]:
    """
    Compare discovered experiments against current database.

    Returns:
        Dict with 'new', 'updated', 'unchanged' lists
    """
    result = {
        'new': [],
        'updated': [],
        'unchanged': [],
        'summary': {
            'total_discovered': len(discovered),
            'total_current': len(current),
            'new_count': 0,
            'updated_count': 0,
            'unchanged_count': 0,
        }
    }

    for exp in discovered:
        path = exp['path']

        if path not in current:
            result['new'].append(exp)
            result['summary']['new_count'] += 1
        else:
            # Check if metadata changed
            curr = current[path]
            changed = False
            changes = []

            for field in ['pod5_files', 'fastq_files', 'bam_files']:
                if exp.get(field, 0) != curr.get(field, 0):
                    changed = True
                    changes.append(f"{field}: {curr.get(field, 0)} -> {exp.get(field, 0)}")

            if changed:
                exp['changes'] = changes
                result['updated'].append(exp)
                result['summary']['updated_count'] += 1
            else:
                result['unchanged'].append(exp)
                result['summary']['unchanged_count'] += 1

    return result


def format_diff_report(comparison: Dict[str, Any]) -> str:
    """Format comparison result as a readable diff report."""
    lines = []
    lines.append("=" * 70)
    lines.append("EXPERIMENT DISCOVERY REPORT")
    lines.append("=" * 70)
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")

    summary = comparison['summary']
    lines.append("SUMMARY")
    lines.append("-" * 40)
    lines.append(f"  Total discovered: {summary['total_discovered']}")
    lines.append(f"  Currently in DB:  {summary['total_current']}")
    lines.append(f"  New experiments:  {summary['new_count']}")
    lines.append(f"  Updated:          {summary['updated_count']}")
    lines.append(f"  Unchanged:        {summary['unchanged_count']}")
    lines.append("")

    if comparison['new']:
        lines.append("NEW EXPERIMENTS")
        lines.append("-" * 40)
        for exp in comparison['new']:
            lines.append(f"  + {exp['sample_id'] or 'unknown'}")
            lines.append(f"    Path: {exp['path']}")
            lines.append(f"    Flow Cell: {exp['flow_cell_id']}")
            lines.append(f"    POD5: {exp['pod5_files']}, FASTQ: {exp['fastq_files']}, BAM: {exp['bam_files']}")
            lines.append("")

    if comparison['updated']:
        lines.append("UPDATED EXPERIMENTS")
        lines.append("-" * 40)
        for exp in comparison['updated']:
            lines.append(f"  ~ {exp['sample_id'] or 'unknown'}")
            lines.append(f"    Path: {exp['path']}")
            for change in exp.get('changes', []):
                lines.append(f"    {change}")
            lines.append("")

    return "\n".join(lines)


def generate_slurm_script(output_path: str) -> str:
    """Generate SLURM script for discovery job."""

    script_dir = Path(__file__).parent
    script_path = Path(__file__).name
    logs_dir = Path(GREATLAKES_CONFIG['turbo_base']) / 'logs'

    script = SLURM_SCAN_TEMPLATE.format(
        account=GREATLAKES_CONFIG['account'],
        partition=GREATLAKES_CONFIG['partition'],
        logs_dir=logs_dir,
        timestamp=datetime.now(timezone.utc).isoformat(),
        script_dir=script_dir,
        script_path=script_path,
        manifest_path=GREATLAKES_CONFIG['manifest_path'],
        db_path=GREATLAKES_CONFIG['db_path'],
        scan_dirs=' \\\n    '.join(GREATLAKES_CONFIG['scan_dirs']),
    )

    with open(output_path, 'w') as f:
        f.write(script)

    os.chmod(output_path, 0o755)
    return output_path


def export_manifest(experiments: List[Dict], output_path: str):
    """Export discovered experiments to JSON manifest."""
    manifest = {
        'version': '1.0',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'scan_dirs': GREATLAKES_CONFIG['scan_dirs'],
        'total_experiments': len(experiments),
        'experiments': experiments,
    }

    with open(output_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"Exported {len(experiments)} experiments to {output_path}")


def export_for_github(comparison: Dict[str, Any], output_path: str):
    """
    Export database snapshot for GitHub sync.

    Creates a JSON file that can be committed to the repo.
    """
    # Create a simplified snapshot for GitHub
    snapshot = {
        'version': '1.0',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'source': 'greatlakes',
        'turbo_base': GREATLAKES_CONFIG['turbo_base'],
        'summary': comparison['summary'],
        'experiments': [],
    }

    # Include all discovered experiments
    for exp in comparison['new'] + comparison['updated'] + comparison['unchanged']:
        snapshot['experiments'].append({
            'id': exp.get('id', ''),
            'sample_id': exp.get('sample_id', ''),
            'flow_cell_id': exp.get('flow_cell_id', ''),
            'protocol_group_id': exp.get('protocol_group_id', ''),
            'started': exp.get('started', ''),
            'path': exp.get('path', ''),
            'pod5_files': exp.get('pod5_files', 0),
            'fastq_files': exp.get('fastq_files', 0),
            'bam_files': exp.get('bam_files', 0),
        })

    with open(output_path, 'w') as f:
        json.dump(snapshot, f, indent=2)

    print(f"Exported GitHub snapshot to {output_path}")
    return output_path


def cmd_scan(args):
    """Generate and optionally submit SLURM discovery job."""
    script_path = Path(GREATLAKES_CONFIG['turbo_base']) / 'discovery_job.sbatch'

    # Create logs directory
    logs_dir = Path(GREATLAKES_CONFIG['turbo_base']) / 'logs'
    logs_dir.mkdir(exist_ok=True)

    generate_slurm_script(str(script_path))
    print(f"Generated SLURM script: {script_path}")

    if args.submit:
        print("Submitting job to Great Lakes...")
        # This would be run via SSH or locally on Great Lakes
        print(f"Run: sbatch {script_path}")

    return 0


def cmd_scan_local(args):
    """Run discovery locally (called from SLURM job)."""
    print("Starting local experiment discovery...")

    experiments = find_experiments_local(args.scan_dirs)
    print(f"\nFound {len(experiments)} experiments")

    # Export manifest
    export_manifest(experiments, args.output)

    # Compare against database if it exists
    if args.db_path and os.path.exists(args.db_path):
        current = load_current_database(args.db_path)
        comparison = compare_experiments(experiments, current)

        report = format_diff_report(comparison)
        print(report)

        # Save comparison report
        report_path = args.output.replace('.json', '_diff.txt')
        with open(report_path, 'w') as f:
            f.write(report)
        print(f"Diff report saved to: {report_path}")

        # Export for GitHub
        github_path = args.output.replace('.json', '_github.json')
        export_for_github(comparison, github_path)

    return 0


def cmd_compare(args):
    """Compare manifest against current database."""
    if not os.path.exists(args.manifest):
        print(f"Error: Manifest not found: {args.manifest}")
        return 1

    with open(args.manifest, 'r') as f:
        manifest = json.load(f)

    discovered = manifest.get('experiments', [])
    current = load_current_database(args.db_path)

    comparison = compare_experiments(discovered, current)
    report = format_diff_report(comparison)
    print(report)

    # Save comparison
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"Report saved to: {args.output}")

    return 0


def cmd_sync(args):
    """Sync approved changes to database and GitHub."""
    if not os.path.exists(args.manifest):
        print(f"Error: Manifest not found: {args.manifest}")
        return 1

    with open(args.manifest, 'r') as f:
        manifest = json.load(f)

    discovered = manifest.get('experiments', [])

    if not args.approved:
        print("Changes not approved. Use --approved to apply changes.")
        print("Review the diff report first.")
        return 1

    # Update local database
    print(f"Updating database: {args.db_path}")
    # Here we would call the experiment_db.py build function
    # For now, just print what would happen
    print(f"  Would add {len(discovered)} experiments to database")

    # Export for GitHub
    if args.github:
        github_snapshot = Path(args.manifest).parent / 'experiments_snapshot.json'
        current = load_current_database(args.db_path) if os.path.exists(args.db_path) else {}
        comparison = compare_experiments(discovered, current)
        export_for_github(comparison, str(github_snapshot))

        print(f"\nGitHub snapshot exported to: {github_snapshot}")
        print("To sync to GitHub:")
        print(f"  1. Copy {github_snapshot} to registry/experiments_snapshot.json")
        print("  2. git add registry/experiments_snapshot.json")
        print("  3. git commit -m 'Update experiment registry from Great Lakes'")
        print("  4. git push")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Great Lakes Experiment Discovery and Sync',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest='command', help='Command')

    # scan command - generate SLURM job
    scan_parser = subparsers.add_parser('scan', help='Generate discovery SLURM job')
    scan_parser.add_argument('--submit', action='store_true',
                            help='Submit job after generating')

    # scan-local command - run discovery locally
    local_parser = subparsers.add_parser('scan-local', help='Run discovery locally')
    local_parser.add_argument('scan_dirs', nargs='+', help='Directories to scan')
    local_parser.add_argument('--output', '-o', required=True,
                             help='Output manifest JSON path')
    local_parser.add_argument('--db-path', help='Current database path for comparison')

    # compare command
    compare_parser = subparsers.add_parser('compare', help='Compare manifest to database')
    compare_parser.add_argument('--manifest', '-m', required=True,
                               help='Discovered experiments manifest')
    compare_parser.add_argument('--db-path', default=GREATLAKES_CONFIG['db_path'],
                               help='Database path')
    compare_parser.add_argument('--output', '-o', help='Save report to file')

    # sync command
    sync_parser = subparsers.add_parser('sync', help='Sync approved changes')
    sync_parser.add_argument('--manifest', '-m', required=True,
                            help='Discovered experiments manifest')
    sync_parser.add_argument('--db-path', default=GREATLAKES_CONFIG['db_path'],
                            help='Database path')
    sync_parser.add_argument('--approved', action='store_true',
                            help='Confirm approval of changes')
    sync_parser.add_argument('--github', action='store_true',
                            help='Export snapshot for GitHub sync')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    if args.command == 'scan':
        return cmd_scan(args)
    elif args.command == 'scan-local':
        return cmd_scan_local(args)
    elif args.command == 'compare':
        return cmd_compare(args)
    elif args.command == 'sync':
        return cmd_sync(args)

    return 0


if __name__ == '__main__':
    sys.exit(main())
