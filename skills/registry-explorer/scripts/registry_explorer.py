#!/usr/bin/env python3
"""
Registry Explorer - Deep source data inspection for ONT experiments.

Explores local paths and remote URLs to extract metadata from:
- BAM headers (@RG, @PG tags)
- POD5 files (run metadata)
- final_summary.txt (chemistry, model, yield)
- sequencing_summary.txt (per-read stats)

Usage:
    python registry_explorer.py explore <exp_id> [--verbose]
    python registry_explorer.py scan [--local | --public] [--missing-chemistry] [--apply]
    python registry_explorer.py check <exp_id>
    python registry_explorer.py ls <exp_id> [--recursive]
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# =============================================================================
# CONFIGURATION
# =============================================================================

REGISTRY_PATH = Path.home() / ".ont-registry" / "experiments.yaml"
AUDIT_LOG_PATH = Path.home() / ".ont-registry" / "audit_log.yaml"

# File patterns to look for
FILE_PATTERNS = {
    'bam': ['*.bam', '*/*.bam', 'pass/*.bam', 'fail/*.bam'],
    'pod5': ['*.pod5', 'pod5_pass/*.pod5', 'pod5_fail/*.pod5', '*/*.pod5'],
    'final_summary': ['final_summary*.txt', '**/final_summary*.txt'],
    'sequencing_summary': ['sequencing_summary*.txt', '**/sequencing_summary*.txt'],
    'report': ['report_*.html', '**/report_*.html'],
}

# Chemistry patterns from final_summary
CHEMISTRY_MAP = {
    'FLO-PRO114M': 'R10.4.1',
    'FLO-PRO114': 'R10.4.1',
    'FLO-PRO002': 'R9.4.1',
    'FLO-MIN114': 'R10.4.1',
    'FLO-MIN106': 'R9.4.1',
    'FLO-FLG114': 'R10.4.1',
    'FLO-FLG001': 'R9.4.1',
}

# Model patterns
MODEL_PATTERNS = [
    (r'dna_r10\.4\.1_e8\.2_\d+bps_sup', 'sup'),
    (r'dna_r10\.4\.1_e8\.2_\d+bps_hac', 'hac'),
    (r'dna_r10\.4\.1_e8\.2_\d+bps_fast', 'fast'),
    (r'dna_r9\.4\.1_\d+bps_sup', 'sup'),
    (r'dna_r9\.4\.1_\d+bps_hac', 'hac'),
    (r'dna_r9\.4\.1_\d+bps_fast', 'fast'),
    (r'sup@v\d+', 'sup'),
    (r'hac@v\d+', 'hac'),
    (r'fast@v\d+', 'fast'),
    (r'\bsup\b', 'sup'),
    (r'\bhac\b', 'hac'),
    (r'\bfast\b', 'fast'),
]


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def load_registry() -> Dict:
    """Load the experiment registry."""
    if not REGISTRY_PATH.exists():
        return {"version": "3.0", "experiments": []}
    with open(REGISTRY_PATH) as f:
        return yaml.safe_load(f) or {"version": "3.0", "experiments": []}


def save_registry(data: Dict):
    """Save the experiment registry."""
    data["updated"] = datetime.now().isoformat()
    with open(REGISTRY_PATH, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def log_audit(action: str, exp_id: str, changes: Dict):
    """Log audit entry."""
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    if AUDIT_LOG_PATH.exists():
        with open(AUDIT_LOG_PATH) as f:
            log = yaml.safe_load(f) or {"entries": []}
    else:
        log = {"entries": []}

    log["entries"].append({
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "experiment_id": exp_id,
        "changes": changes,
    })

    log["entries"] = log["entries"][-2000:]

    with open(AUDIT_LOG_PATH, 'w') as f:
        yaml.dump(log, f, default_flow_style=False)


def find_files(base_path: str, patterns: List[str]) -> List[Path]:
    """Find files matching patterns in base path."""
    base = Path(base_path)
    if not base.exists():
        return []

    found = []
    for pattern in patterns:
        if '**' in pattern:
            found.extend(base.rglob(pattern.replace('**/', '')))
        else:
            found.extend(base.glob(pattern))

    return sorted(set(found))


# =============================================================================
# METADATA EXTRACTION
# =============================================================================

def extract_from_bam_header(bam_path: str) -> Dict[str, Any]:
    """Extract metadata from BAM header."""
    metadata = {}

    try:
        cmd = f"samtools view -H {bam_path} 2>/dev/null | head -200"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            return metadata

        header = result.stdout

        for line in header.split('\n'):
            if line.startswith('@RG'):
                parts = line.split('\t')
                for part in parts[1:]:
                    if part.startswith('SM:'):
                        metadata['sample'] = part[3:]
                    elif part.startswith('PL:'):
                        metadata['platform'] = part[3:]
                    elif part.startswith('PM:'):
                        metadata['platform_model'] = part[3:]
                    elif part.startswith('DS:'):
                        desc = part[3:]
                        # Extract basecaller info
                        if 'dorado' in desc.lower():
                            metadata['basecaller'] = 'dorado'
                            ver = re.search(r'dorado[_\s]*([\d\.]+)', desc, re.I)
                            if ver:
                                metadata['basecaller_version'] = ver.group(1)
                        # Extract model
                        for pattern, model in MODEL_PATTERNS:
                            if re.search(pattern, desc, re.I):
                                metadata['basecall_model'] = model
                                break

            elif line.startswith('@PG'):
                parts = line.split('\t')
                for part in parts[1:]:
                    if part.startswith('PN:'):
                        program = part[3:]
                        if 'dorado' in program.lower():
                            metadata['basecaller'] = 'dorado'
                        elif 'guppy' in program.lower():
                            metadata['basecaller'] = 'guppy'
                    elif part.startswith('VN:'):
                        if 'basecaller_version' not in metadata:
                            metadata['basecaller_version'] = part[3:]
                    elif part.startswith('CL:'):
                        cmdline = part[3:]
                        for pattern, model in MODEL_PATTERNS:
                            if re.search(pattern, cmdline, re.I):
                                metadata['basecall_model'] = model
                                break

        return metadata

    except Exception as e:
        print(f"    Error reading BAM header: {e}")
        return metadata


def extract_from_final_summary(summary_path: str) -> Dict[str, Any]:
    """Extract metadata from final_summary.txt."""
    metadata = {}

    try:
        with open(summary_path) as f:
            content = f.read()

        lines = content.split('\n')
        for line in lines:
            if '=' in line:
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip()

                if key == 'flow_cell_product_code':
                    metadata['flowcell_product'] = value
                    if value in CHEMISTRY_MAP:
                        metadata['chemistry'] = CHEMISTRY_MAP[value]

                elif key == 'flow_cell_id':
                    metadata['flowcell_id'] = value
                    # Determine flowcell type from ID
                    if value.startswith('P'):
                        metadata['flowcell_type'] = 'PromethION'
                    elif value.startswith('F'):
                        metadata['flowcell_type'] = 'MinION'
                    elif value.startswith('A'):
                        metadata['flowcell_type'] = 'Flongle'

                elif key == 'device_id':
                    metadata['device_id'] = value

                elif key == 'device_type':
                    metadata['device_type'] = value

                elif key == 'sample_id':
                    if value and value != 'no_sample_id':
                        metadata['sample'] = value

                elif key == 'experiment_id':
                    metadata['experiment_name'] = value

                elif key == 'protocol_group_id':
                    metadata['protocol_group'] = value

                elif key == 'run_id':
                    metadata['run_id'] = value[:8] if len(value) >= 8 else value

                elif key == 'basecalling_model':
                    metadata['basecall_model_full'] = value
                    for pattern, model in MODEL_PATTERNS:
                        if re.search(pattern, value, re.I):
                            metadata['basecall_model'] = model
                            break

                elif key == 'yield':
                    try:
                        metadata['yield_bases'] = int(value)
                    except ValueError:
                        pass

                elif key == 'n50':
                    try:
                        metadata['n50'] = int(value)
                    except ValueError:
                        pass

                elif key == 'mean_read_quality':
                    try:
                        metadata['mean_qscore'] = float(value)
                    except ValueError:
                        pass

        return metadata

    except Exception as e:
        print(f"    Error reading final_summary: {e}")
        return metadata


def extract_from_pod5(pod5_path: str) -> Dict[str, Any]:
    """Extract metadata from POD5 file."""
    metadata = {}

    try:
        import pod5

        with pod5.Reader(pod5_path) as reader:
            # Get run info from first read
            for read in reader.reads():
                run_info = read.run_info

                metadata['run_id'] = run_info.acquisition_id[:8] if run_info.acquisition_id else None
                metadata['experiment_name'] = run_info.experiment_name
                metadata['sample_id'] = run_info.sample_id if run_info.sample_id != 'no_sample_id' else None
                metadata['flowcell_id'] = run_info.flow_cell_id
                metadata['device_id'] = run_info.device_id
                metadata['device_type'] = run_info.device_type
                metadata['protocol_group'] = run_info.protocol_group_id

                # Try to get flow cell product code
                if hasattr(run_info, 'flow_cell_product_code'):
                    fc_product = run_info.flow_cell_product_code
                    if fc_product in CHEMISTRY_MAP:
                        metadata['chemistry'] = CHEMISTRY_MAP[fc_product]

                break  # Only need first read for run info

        return {k: v for k, v in metadata.items() if v}

    except ImportError:
        print("    pod5 library not installed, skipping POD5 extraction")
        return metadata
    except Exception as e:
        print(f"    Error reading POD5: {e}")
        return metadata


# =============================================================================
# EXPLORATION FUNCTIONS
# =============================================================================

def explore_experiment(exp: Dict, verbose: bool = False) -> Dict[str, Any]:
    """Fully explore an experiment's source data."""
    exp_id = exp.get('id', 'unknown')
    location = exp.get('location', '')

    print(f"\nExploring: {exp.get('name', exp_id)}")
    print(f"  ID: {exp_id}")
    print(f"  Location: {location[:70]}...")

    all_metadata = {}
    artifacts = []

    if not location:
        print("  No location set, cannot explore")
        return all_metadata

    base_path = Path(location)

    # Check if path exists
    if not base_path.exists():
        print(f"  Path does not exist: {location[:50]}...")
        # Try parent directories
        for parent in [base_path.parent, base_path.parent.parent]:
            if parent.exists():
                print(f"  Trying parent: {parent}")
                base_path = parent
                break
        else:
            return all_metadata

    # Find and process BAM files
    bam_files = find_files(str(base_path), FILE_PATTERNS['bam'])
    if bam_files:
        print(f"  Found {len(bam_files)} BAM file(s)")
        for bam in bam_files[:3]:  # Process first 3
            if verbose:
                print(f"    Processing: {bam.name}")
            bam_meta = extract_from_bam_header(str(bam))
            if bam_meta:
                all_metadata.update(bam_meta)
                artifacts.append({'type': 'bam', 'path': str(bam)})
                if verbose:
                    for k, v in bam_meta.items():
                        print(f"      {k}: {v}")
                break  # Usually one BAM is enough

    # Find and process final_summary files
    summary_files = find_files(str(base_path), FILE_PATTERNS['final_summary'])
    if summary_files:
        print(f"  Found {len(summary_files)} final_summary file(s)")
        for summary in summary_files[:1]:
            if verbose:
                print(f"    Processing: {summary.name}")
            summary_meta = extract_from_final_summary(str(summary))
            if summary_meta:
                # Update without overwriting existing values
                for k, v in summary_meta.items():
                    if k not in all_metadata:
                        all_metadata[k] = v
                artifacts.append({'type': 'summary', 'path': str(summary)})
                if verbose:
                    for k, v in summary_meta.items():
                        print(f"      {k}: {v}")

    # Find and process POD5 files
    pod5_files = find_files(str(base_path), FILE_PATTERNS['pod5'])
    if pod5_files:
        print(f"  Found {len(pod5_files)} POD5 file(s)")
        for pod5 in pod5_files[:1]:
            if verbose:
                print(f"    Processing: {pod5.name}")
            pod5_meta = extract_from_pod5(str(pod5))
            if pod5_meta:
                for k, v in pod5_meta.items():
                    if k not in all_metadata:
                        all_metadata[k] = v
                artifacts.append({'type': 'pod5', 'path': str(pod5)})

    # Add artifacts to metadata
    if artifacts:
        all_metadata['_artifacts'] = artifacts

    if all_metadata:
        print(f"  Extracted {len(all_metadata)} metadata fields")
    else:
        print("  No metadata extracted")

    return all_metadata


def check_experiment_files(exp: Dict) -> Dict[str, Any]:
    """Check what files exist for an experiment."""
    location = exp.get('location', '')
    result = {
        'exists': False,
        'bam_count': 0,
        'pod5_count': 0,
        'summary_count': 0,
        'total_size_gb': 0,
    }

    if not location:
        return result

    base_path = Path(location)
    if not base_path.exists():
        return result

    result['exists'] = True

    # Count files
    result['bam_count'] = len(find_files(str(base_path), FILE_PATTERNS['bam']))
    result['pod5_count'] = len(find_files(str(base_path), FILE_PATTERNS['pod5']))
    result['summary_count'] = len(find_files(str(base_path), FILE_PATTERNS['final_summary']))

    # Calculate total size
    try:
        total_bytes = sum(f.stat().st_size for f in base_path.rglob('*') if f.is_file())
        result['total_size_gb'] = round(total_bytes / (1024**3), 2)
    except Exception:
        pass

    return result


def list_experiment_files(exp: Dict, recursive: bool = False) -> List[Dict]:
    """List files in experiment directory."""
    location = exp.get('location', '')
    files = []

    if not location:
        return files

    base_path = Path(location)
    if not base_path.exists():
        return files

    pattern = '**/*' if recursive else '*'
    for f in base_path.glob(pattern):
        if f.is_file():
            try:
                size = f.stat().st_size
                files.append({
                    'name': f.name,
                    'path': str(f),
                    'size_mb': round(size / (1024**2), 2),
                    'type': f.suffix.lstrip('.'),
                })
            except Exception:
                pass

    return sorted(files, key=lambda x: x['name'])


# =============================================================================
# UPDATE FUNCTIONS
# =============================================================================

def update_experiment_from_exploration(exp: Dict, extracted: Dict, apply: bool = False) -> Dict:
    """Update experiment with extracted metadata."""
    changes = {}

    if not extracted:
        return changes

    # Ensure metadata dict exists
    if 'metadata' not in exp:
        exp['metadata'] = {}
    metadata = exp['metadata']

    # Fields to update
    field_mapping = {
        'chemistry': 'chemistry',
        'basecall_model': 'basecall_model',
        'basecaller': 'basecaller',
        'basecaller_version': 'basecaller_version',
        'flowcell_type': 'flowcell_type',
        'flowcell_id': 'flowcell_id',
        'device_type': 'device_type',
        'device_id': 'device_id',
        'sample': 'sample',
        'run_id': 'run_id',
        'n50': 'n50',
        'mean_qscore': 'mean_qscore',
    }

    for src_field, dest_field in field_mapping.items():
        if src_field in extracted and not metadata.get(dest_field):
            metadata[dest_field] = extracted[src_field]
            changes[f'explored_{dest_field}'] = extracted[src_field]

    # Handle artifacts
    if '_artifacts' in extracted and not exp.get('artifacts'):
        exp['artifacts'] = []
        for artifact in extracted['_artifacts']:
            exp['artifacts'].append({
                'path': artifact['path'],
                'type': artifact['type'],
                'discovered': datetime.now().isoformat(),
            })
        changes['added_artifacts'] = len(extracted['_artifacts'])

    # Update provenance
    if changes:
        if 'provenance' not in exp:
            exp['provenance'] = {}
        exp['provenance']['last_explored'] = datetime.now().isoformat()
        exp['provenance']['schema_version'] = '2.0'

    return changes


# =============================================================================
# MAIN COMMANDS
# =============================================================================

def cmd_explore(args):
    """Explore a single experiment."""
    data = load_registry()
    exp = next((e for e in data['experiments'] if e.get('id') == args.exp_id), None)

    if not exp:
        print(f"Experiment not found: {args.exp_id}")
        return 1

    extracted = explore_experiment(exp, verbose=args.verbose)

    if extracted:
        print(f"\nExtracted metadata:")
        for k, v in extracted.items():
            if not k.startswith('_'):
                print(f"  {k}: {v}")

        changes = update_experiment_from_exploration(exp, extracted, apply=args.apply)

        if changes:
            print(f"\nChanges to apply:")
            for k, v in changes.items():
                print(f"  {k}: {v}")

            if args.apply:
                for i, e in enumerate(data['experiments']):
                    if e.get('id') == args.exp_id:
                        data['experiments'][i] = exp
                        break
                save_registry(data)
                log_audit('explore', args.exp_id, changes)
                print("\nSaved to registry")
            else:
                print("\n(use --apply to save changes)")

    return 0


def cmd_scan(args):
    """Scan multiple experiments."""
    data = load_registry()
    experiments = data.get('experiments', [])

    # Filter experiments
    filtered = []
    for exp in experiments:
        if args.local and exp.get('source') != 'local':
            continue
        if args.public and exp.get('source') != 'ont-open-data':
            continue
        if args.missing_chemistry:
            if exp.get('metadata', {}).get('chemistry'):
                continue
        if args.missing_model:
            if exp.get('metadata', {}).get('basecall_model'):
                continue
        filtered.append(exp)

    if args.limit:
        filtered = filtered[:args.limit]

    print(f"Scanning {len(filtered)} experiments...")
    stats = {'processed': 0, 'updated': 0, 'failed': 0}

    for i, exp in enumerate(filtered):
        print(f"\n[{i+1}/{len(filtered)}] {exp.get('name', exp.get('id'))[:40]}")

        try:
            extracted = explore_experiment(exp, verbose=False)
            changes = update_experiment_from_exploration(exp, extracted, apply=args.apply)

            if changes:
                stats['updated'] += 1
                print(f"  Extracted: {', '.join(changes.keys())}")

                if args.apply:
                    for j, e in enumerate(data['experiments']):
                        if e.get('id') == exp.get('id'):
                            data['experiments'][j] = exp
                            break
                    log_audit('explore_scan', exp.get('id'), changes)
            else:
                print("  No new metadata extracted")

        except Exception as e:
            stats['failed'] += 1
            print(f"  Error: {e}")

        stats['processed'] += 1

    if args.apply and stats['updated'] > 0:
        save_registry(data)
        print(f"\nSaved {stats['updated']} updates to registry")

    print(f"\nScan complete:")
    print(f"  Processed: {stats['processed']}")
    print(f"  Updated: {stats['updated']}")
    print(f"  Failed: {stats['failed']}")

    return 0


def cmd_check(args):
    """Check files for an experiment."""
    data = load_registry()
    exp = next((e for e in data['experiments'] if e.get('id') == args.exp_id), None)

    if not exp:
        print(f"Experiment not found: {args.exp_id}")
        return 1

    print(f"Checking: {exp.get('name', args.exp_id)}")
    print(f"Location: {exp.get('location', 'not set')}")

    result = check_experiment_files(exp)

    print(f"\nFile check results:")
    print(f"  Path exists: {result['exists']}")
    print(f"  BAM files: {result['bam_count']}")
    print(f"  POD5 files: {result['pod5_count']}")
    print(f"  Summary files: {result['summary_count']}")
    print(f"  Total size: {result['total_size_gb']} GB")

    return 0


def cmd_ls(args):
    """List files in experiment directory."""
    data = load_registry()
    exp = next((e for e in data['experiments'] if e.get('id') == args.exp_id), None)

    if not exp:
        print(f"Experiment not found: {args.exp_id}")
        return 1

    files = list_experiment_files(exp, recursive=args.recursive)

    print(f"Files in: {exp.get('location', 'not set')}")
    print(f"Total: {len(files)} files\n")

    for f in files[:50]:
        print(f"  {f['size_mb']:8.2f} MB  {f['name']}")

    if len(files) > 50:
        print(f"  ... and {len(files) - 50} more")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Registry Explorer - Deep source data inspection")
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Explore command
    explore_parser = subparsers.add_parser('explore', help='Explore single experiment')
    explore_parser.add_argument('exp_id', help='Experiment ID')
    explore_parser.add_argument('-v', '--verbose', action='store_true')
    explore_parser.add_argument('--apply', action='store_true', help='Apply changes to registry')

    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan multiple experiments')
    scan_parser.add_argument('--local', action='store_true', help='Only local experiments')
    scan_parser.add_argument('--public', action='store_true', help='Only public experiments')
    scan_parser.add_argument('--missing-chemistry', action='store_true')
    scan_parser.add_argument('--missing-model', action='store_true')
    scan_parser.add_argument('--limit', type=int)
    scan_parser.add_argument('--apply', action='store_true', help='Apply changes to registry')

    # Check command
    check_parser = subparsers.add_parser('check', help='Check experiment files')
    check_parser.add_argument('exp_id', help='Experiment ID')

    # List command
    ls_parser = subparsers.add_parser('ls', help='List experiment files')
    ls_parser.add_argument('exp_id', help='Experiment ID')
    ls_parser.add_argument('-r', '--recursive', action='store_true')

    args = parser.parse_args()

    if args.command == 'explore':
        return cmd_explore(args)
    elif args.command == 'scan':
        return cmd_scan(args)
    elif args.command == 'check':
        return cmd_check(args)
    elif args.command == 'ls':
        return cmd_ls(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
