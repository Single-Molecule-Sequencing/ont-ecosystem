#!/usr/bin/env python3
"""
HPC POD5 Audit Script
=====================
Run this on Great Lakes to check which experiments have POD5 files.

Usage:
    python3 hpc_pod5_audit.py

Output:
    ./pod5_audit_results.json - Full audit results

Copy results back to WSL:
    scp greatlakes:~/pod5_audit_results.json /tmp/
"""

import json
import os
from pathlib import Path
from datetime import datetime

# Embedded experiment data (116 HPC experiments)
HPC_EXPERIMENTS = [
    {"id": "exp-9f9f4bc1", "location": "/nfs/turbo/umms-atheylab/sequencing_data/data_from_linux_desktop_lab/Fall2025/11182025_IF_NewBCPart4_SMA_Seq"},
    {"id": "exp-cf3ed5a3", "location": "/nfs/turbo/umms-atheylab/sequencing_data/data_from_linux_desktop_lab/10092025_IF_SMA_Seq"},
    {"id": "exp-4ff11072", "location": "/nfs/turbo/umms-atheylab/sequencing_data/data_from_linux_desktop_lab/IF_SMAseq_9302025"},
    {"id": "exp-1788022b", "location": "/nfs/turbo/umms-atheylab/sequencing_data/data_from_linux_desktop_lab/Fall2025/IF_SMA_Seq_12042025"},
    {"id": "exp-36c525f6", "location": "/nfs/turbo/umms-atheylab/sequencing_data/data_from_linux_desktop_lab/Fall2025/September_30_IF"},
    {"id": "exp-46553b7d", "location": "/nfs/turbo/umms-atheylab/sequencing_data/data_from_linux_desktop_lab/Fall2025/GF_SMAseq_10_16_2025"},
    {"id": "exp-1c9262b1", "location": "/nfs/turbo/umms-atheylab/sequencing_data/data_from_linux_desktop_lab/Fall2025/GF_SMAseq_11_13_2025"},
    {"id": "exp-10355be5", "location": "/nfs/turbo/umms-atheylab/sequencing_data/data_from_linux_desktop_lab/Fall2025/GF_SMAseq_10072025"},
    {"id": "exp-6c9e3477", "location": "/nfs/turbo/umms-atheylab/sequencing_data/data_from_linux_desktop_lab/Fall2025/09_25_IF"},
]
# Note: Full list will be loaded from experiments file

def load_full_experiment_list():
    """Load full experiment list from registry if available."""
    # Try to load from file
    for path in [
        '/tmp/hpc_experiments.json',
        os.path.expanduser('~/hpc_experiments.json'),
        './hpc_experiments.json'
    ]:
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    return None

def check_experiment(exp):
    """Check if experiment directory has POD5 files."""
    location = exp.get('location', '')
    result = {
        'id': exp.get('id', 'unknown'),
        'name': exp.get('name', ''),
        'location': location,
        'exists': False,
        'status': 'unknown',
        'pod5_count': 0,
        'pod5_dir': None,
        'fast5_count': 0,
        'bam_count': 0,
        'subdirs': []
    }

    if not location:
        result['status'] = 'no_location'
        return result

    path = Path(location)
    if not path.exists():
        result['status'] = 'missing'
        return result

    result['exists'] = True

    # List subdirectories
    try:
        result['subdirs'] = [d.name for d in path.iterdir() if d.is_dir()][:20]
    except PermissionError:
        result['status'] = 'permission_denied'
        return result

    # Look for POD5 files in common locations
    pod5_locations = ['pod5', 'pod5_pass', 'pod5_fail', 'pass', 'fail', '.']

    for subdir in pod5_locations:
        check_path = path / subdir if subdir != '.' else path
        if check_path.exists():
            try:
                pod5_files = list(check_path.glob('*.pod5'))
                if pod5_files:
                    result['pod5_count'] += len(pod5_files)
                    if not result['pod5_dir']:
                        result['pod5_dir'] = str(check_path)
            except PermissionError:
                pass

    # Check for fast5 if no pod5
    if result['pod5_count'] == 0:
        try:
            fast5_count = sum(1 for _ in path.rglob('*.fast5'))
            result['fast5_count'] = min(fast5_count, 10000)  # Cap for performance
        except:
            pass

    # Check for BAM files
    try:
        bam_count = sum(1 for _ in path.rglob('*.bam'))
        result['bam_count'] = min(bam_count, 100)
    except:
        pass

    # Determine status
    if result['pod5_count'] > 0:
        result['status'] = 'ready'
    elif result['fast5_count'] > 0:
        result['status'] = 'fast5_only'
    elif result['bam_count'] > 0:
        result['status'] = 'bam_only'
    else:
        result['status'] = 'no_raw_data'

    return result

def main():
    print("=" * 60)
    print("HPC POD5 AUDIT")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    # Load experiments
    experiments = load_full_experiment_list()
    if experiments:
        print(f"\nLoaded {len(experiments)} experiments from file")
    else:
        print("\nNo experiment file found, using embedded sample (9 experiments)")
        print("To audit all experiments, copy hpc_experiments.json to HPC first:")
        print("  scp /tmp/hpc_experiments.json greatlakes:~/")
        experiments = HPC_EXPERIMENTS

    # Run audit
    results = {
        'ready': [],
        'missing': [],
        'fast5_only': [],
        'bam_only': [],
        'no_raw_data': [],
        'permission_denied': [],
        'no_location': []
    }

    print(f"\nAuditing {len(experiments)} experiments...")

    for i, exp in enumerate(experiments):
        if (i + 1) % 20 == 0:
            print(f"  Progress: {i + 1}/{len(experiments)}")

        check = check_experiment(exp)
        status = check['status']
        if status in results:
            results[status].append(check)
        else:
            results['no_raw_data'].append(check)

    # Summary
    print("\n" + "=" * 60)
    print("AUDIT RESULTS")
    print("=" * 60)

    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_experiments': len(experiments),
        'ready': len(results['ready']),
        'missing': len(results['missing']),
        'fast5_only': len(results['fast5_only']),
        'bam_only': len(results['bam_only']),
        'no_raw_data': len(results['no_raw_data']),
        'permission_denied': len(results['permission_denied'])
    }

    print(f"\nReady for end_reason analysis: {summary['ready']}")
    print(f"Directory missing:             {summary['missing']}")
    print(f"Fast5 only (needs conversion): {summary['fast5_only']}")
    print(f"BAM only (no raw signal):      {summary['bam_only']}")
    print(f"No raw data found:             {summary['no_raw_data']}")
    print(f"Permission denied:             {summary['permission_denied']}")

    # Save results
    output = {
        'summary': summary,
        'experiments': results
    }

    output_path = os.path.expanduser('~/pod5_audit_results.json')
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to: {output_path}")
    print("\nTo copy results back to WSL:")
    print(f"  scp greatlakes:{output_path} /tmp/")

    # Also print ready experiments for quick reference
    if results['ready']:
        print(f"\n=== READY EXPERIMENTS ({len(results['ready'])}) ===")
        for exp in results['ready'][:10]:
            print(f"  {exp['id']}: {exp['pod5_count']} POD5 files")
            print(f"    {exp['pod5_dir']}")
        if len(results['ready']) > 10:
            print(f"  ... and {len(results['ready']) - 10} more")

if __name__ == '__main__':
    main()
