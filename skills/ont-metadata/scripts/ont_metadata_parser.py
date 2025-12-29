#!/usr/bin/env python3
"""
ont_metadata_parser.py - Extract Run Metadata from ONT Raw Data Files

Efficiently extracts experiment metadata from POD5 and Fast5 files without
requiring final_summary.txt files. This enables discovery of experiments
that have raw data but incomplete summary outputs.

Key metadata extracted:
- flow_cell_id
- sample_id
- acquisition_id
- protocol
- instrument
- experiment_start_time
- sequencing_kit
- basecall_model

Usage:
    # Parse single file
    from ont_metadata_parser import parse_pod5_metadata, parse_fast5_metadata
    metadata = parse_pod5_metadata('/path/to/file.pod5')

    # Auto-detect format
    from ont_metadata_parser import extract_metadata_from_dir
    metadata = extract_metadata_from_dir('/path/to/experiment')

References:
- POD5: https://github.com/nanoporetech/pod5-file-format
- Fast5: https://github.com/nanoporetech/ont_fast5_api
- POD5 API: https://pod5-file-format.readthedocs.io/

Part of: https://github.com/Single-Molecule-Sequencing/ont-ecosystem
"""

import os
import sys
import json
import glob
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

# Optional imports - handle gracefully
try:
    import pod5
    HAS_POD5 = True
except ImportError:
    HAS_POD5 = False

try:
    import h5py
    HAS_H5PY = True
except ImportError:
    HAS_H5PY = False

# Prefer ont_fast5_api for Fast5 files (uses h5py internally)
try:
    from ont_fast5_api.fast5_interface import get_fast5_file, is_multi_read
    from ont_fast5_api.fast5_info import Fast5Info
    HAS_ONT_FAST5_API = True
except ImportError:
    HAS_ONT_FAST5_API = False

# Fast5 file type constants (from ont_fast5_api)
FAST5_MULTI_READ = "multi-read"
FAST5_SINGLE_READ = "single-read"
FAST5_BULK = "bulk"

logger = logging.getLogger(__name__)


# =============================================================================
# POD5 Metadata Extraction
# =============================================================================

def parse_pod5_metadata(filepath: Path, sample_size: int = 1) -> Dict[str, Any]:
    """
    Extract run-level metadata from a POD5 file.

    POD5 files store run_info containing acquisition metadata.
    We only need to read one read to get the run-level info.

    Args:
        filepath: Path to POD5 file
        sample_size: Number of reads to sample for metadata (1 is usually enough)

    Returns:
        Dict with extracted metadata fields

    POD5 RunInfo attributes (from pod5 library):
        - acquisition_id: UUID for the acquisition
        - acquisition_start_time: datetime when acquisition started
        - adc_max, adc_min: ADC value range
        - context_tags: dict with protocol/kit/etc info
        - experiment_name: name of experiment
        - flow_cell_id: flow cell identifier
        - flow_cell_product_code: product code (e.g., FLO-MIN114)
        - protocol_name: protocol name
        - protocol_run_id: unique run identifier
        - sample_id: sample name
        - sample_rate: sampling rate in Hz
        - sequencing_kit: kit identifier (e.g., SQK-LSK114)
        - system_name: instrument name/type
        - system_type: instrument type
        - tracking_id: additional tracking metadata
    """
    if not HAS_POD5:
        raise ImportError("pod5 not installed: pip install pod5")

    metadata = {
        'source_file': str(filepath),
        'file_type': 'pod5',
        'parse_error': None,
    }

    try:
        with pod5.Reader(filepath) as reader:
            # Get first read's run_info
            for read in reader.reads():
                run_info = read.run_info

                # Core identifiers
                metadata['acquisition_id'] = run_info.acquisition_id
                metadata['flow_cell_id'] = run_info.flow_cell_id
                metadata['sample_id'] = run_info.sample_id
                metadata['experiment_name'] = run_info.experiment_name
                metadata['protocol_run_id'] = run_info.protocol_run_id

                # Instrument info
                metadata['instrument'] = run_info.system_name
                metadata['system_type'] = run_info.system_type

                # Protocol/kit info
                metadata['protocol'] = run_info.protocol_name
                metadata['sequencing_kit'] = run_info.sequencing_kit
                metadata['flow_cell_product_code'] = run_info.flow_cell_product_code

                # Timing
                if run_info.acquisition_start_time:
                    metadata['started'] = run_info.acquisition_start_time.isoformat()

                # Sample rate
                metadata['sample_rate'] = run_info.sample_rate

                # Context tags (contains additional protocol details)
                if hasattr(run_info, 'context_tags') and run_info.context_tags:
                    ctx = run_info.context_tags
                    metadata['context_tags'] = dict(ctx) if ctx else {}
                    # Extract common context fields
                    if 'experiment_type' in ctx:
                        metadata['experiment_type'] = ctx['experiment_type']
                    if 'basecall_model' in ctx:
                        metadata['basecall_model'] = ctx['basecall_model']

                # Tracking ID (contains run-level metadata)
                if hasattr(run_info, 'tracking_id') and run_info.tracking_id:
                    tracking = run_info.tracking_id
                    metadata['tracking_id'] = dict(tracking) if tracking else {}
                    # Extract common tracking fields
                    if 'device_id' in tracking:
                        metadata['device_id'] = tracking['device_id']
                    if 'run_id' in tracking:
                        metadata['run_id'] = tracking['run_id']
                    if 'protocol_group_id' in tracking:
                        metadata['protocol_group_id'] = tracking['protocol_group_id']

                # Only need one read for run-level metadata
                break

    except Exception as e:
        metadata['parse_error'] = str(e)
        logger.warning(f"Error parsing POD5 {filepath}: {e}")

    return metadata


def scan_pod5_directory(directory: Path, max_files: int = 3) -> Dict[str, Any]:
    """
    Scan directory for POD5 files and extract metadata.

    Args:
        directory: Directory to scan
        max_files: Max files to parse (1 is usually enough for run-level info)

    Returns:
        Aggregated metadata from POD5 files
    """
    if not HAS_POD5:
        return {'file_type': 'pod5', 'error': 'pod5 library not installed'}

    pod5_files = list(directory.rglob('*.pod5'))
    if not pod5_files:
        return {'file_type': 'pod5', 'error': 'No POD5 files found'}

    # Parse first few files to get metadata
    metadata = None
    for pod5_file in pod5_files[:max_files]:
        try:
            metadata = parse_pod5_metadata(pod5_file)
            if metadata and not metadata.get('parse_error'):
                break
        except Exception as e:
            logger.warning(f"Error scanning {pod5_file}: {e}")
            continue

    if not metadata:
        metadata = {'file_type': 'pod5', 'error': 'Failed to parse any POD5 files'}

    metadata['pod5_count'] = len(pod5_files)
    return metadata


# =============================================================================
# Fast5 Metadata Extraction (using ont_fast5_api)
# =============================================================================

def detect_fast5_type(filepath: Path) -> str:
    """
    Detect Fast5 file type: single-read, multi-read, or bulk.

    Uses ont_fast5_api if available, falls back to h5py inspection.

    Args:
        filepath: Path to Fast5 file

    Returns:
        One of: 'single-read', 'multi-read', 'bulk', or 'unknown'
    """
    if HAS_ONT_FAST5_API:
        try:
            if is_multi_read(str(filepath)):
                return FAST5_MULTI_READ
            else:
                return FAST5_SINGLE_READ
        except Exception:
            pass

    # Fallback to h5py inspection
    if HAS_H5PY:
        try:
            with h5py.File(filepath, 'r') as f:
                # Check for file_type attribute (multi-read v2.2+)
                if 'file_type' in f.attrs:
                    file_type = f.attrs['file_type']
                    if isinstance(file_type, bytes):
                        file_type = file_type.decode()
                    return file_type

                # Check structure to determine type
                keys = list(f.keys())

                # Bulk files have IntermediateData, StateData, etc.
                if 'IntermediateData' in keys or 'StateData' in keys:
                    return FAST5_BULK

                # Multi-read files have read_* groups at root
                if any(k.startswith('read_') for k in keys):
                    return FAST5_MULTI_READ

                # Single-read files have UniqueGlobalKey
                if 'UniqueGlobalKey' in keys:
                    return FAST5_SINGLE_READ

        except Exception:
            pass

    return 'unknown'


def parse_fast5_metadata(filepath: Path) -> Dict[str, Any]:
    """
    Extract run-level metadata from a Fast5 (HDF5) file.

    Uses ont_fast5_api if available for proper API access, with h5py fallback.

    Fast5 file types:
    - single-read: One read per file (legacy format, deprecated)
    - multi-read: Multiple reads per file (4000 typical, current standard)
    - bulk: Raw channel data stream (special use case)

    Metadata sources:
    - tracking_id: run_id, flow_cell_id, sample_id, device info, timestamps
    - context_tags: experiment_type, sequencing_kit, basecall settings
    - channel_id: channel configuration and calibration

    Args:
        filepath: Path to Fast5 file

    Returns:
        Dict with extracted metadata fields

    References:
        https://github.com/nanoporetech/ont_fast5_api
    """
    metadata = {
        'source_file': str(filepath),
        'file_type': 'fast5',
        'fast5_format': 'unknown',
        'parse_error': None,
    }

    # Detect file type first
    metadata['fast5_format'] = detect_fast5_type(filepath)

    if metadata['fast5_format'] == FAST5_BULK:
        metadata['parse_error'] = 'Bulk Fast5 files not supported for metadata extraction'
        return metadata

    # Try ont_fast5_api first (preferred)
    if HAS_ONT_FAST5_API:
        try:
            return _parse_fast5_with_api(filepath, metadata)
        except Exception as e:
            logger.warning(f"ont_fast5_api failed for {filepath}, trying h5py fallback: {e}")

    # Fallback to raw h5py
    if HAS_H5PY:
        try:
            return _parse_fast5_with_h5py(filepath, metadata)
        except Exception as e:
            metadata['parse_error'] = str(e)
            logger.warning(f"Error parsing Fast5 {filepath}: {e}")

    if not HAS_ONT_FAST5_API and not HAS_H5PY:
        metadata['parse_error'] = 'Neither ont_fast5_api nor h5py installed'

    return metadata


def _parse_fast5_with_api(filepath: Path, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse Fast5 using ont_fast5_api (preferred method).

    Uses the official ONT API for proper metadata access:
    - get_tracking_id(): run metadata dict
    - get_context_tags(): experiment context dict
    - get_channel_info(): channel calibration dict
    """
    with get_fast5_file(str(filepath), mode='r') as f5:
        # Get first read for run-level metadata
        for read in f5.get_reads():
            # Tracking ID contains run-level metadata
            tracking = read.get_tracking_id()
            if tracking:
                metadata['tracking_id'] = tracking
                metadata['run_id'] = tracking.get('run_id', '')
                metadata['flow_cell_id'] = tracking.get('flow_cell_id', '')
                metadata['flow_cell_product_code'] = tracking.get('flow_cell_product_code', '')
                metadata['sample_id'] = tracking.get('sample_id', '')
                metadata['protocol_group_id'] = tracking.get('protocol_group_id', '')
                metadata['protocol_run_id'] = tracking.get('protocol_run_id', '')
                metadata['device_id'] = tracking.get('device_id', '')
                metadata['device_type'] = tracking.get('device_type', '')
                metadata['instrument'] = tracking.get('device_type', '') or tracking.get('hostname', '')
                metadata['exp_start_time'] = tracking.get('exp_start_time', '')
                metadata['started'] = tracking.get('exp_start_time', '')
                metadata['acquisition_id'] = tracking.get('acquisition_id', '')
                metadata['experiment_duration_set'] = tracking.get('experiment_duration_set', '')
                metadata['guppy_version'] = tracking.get('guppy_version', '')
                metadata['hostname'] = tracking.get('hostname', '')
                metadata['operating_system'] = tracking.get('operating_system', '')
                metadata['protocol'] = tracking.get('protocols_version_name', '')

            # Context tags contain experiment settings
            if read.has_context_tags:
                context = read.get_context_tags()
                if context:
                    metadata['context_tags'] = context
                    metadata['experiment_type'] = context.get('experiment_type', '')
                    metadata['experiment_kit'] = context.get('experiment_kit', '')
                    metadata['sequencing_kit'] = context.get('sequencing_kit', '')
                    metadata['basecall_model'] = context.get('basecall_model_version_id', '')
                    metadata['local_basecalling'] = context.get('local_basecalling', '')
                    metadata['barcoding_enabled'] = context.get('barcoding_enabled', '')
                    metadata['selected_speed_bases_per_second'] = context.get('selected_speed_bases_per_second', '')
                    metadata['package'] = context.get('package', '')
                    metadata['package_version'] = context.get('package_version', '')

            # Channel info for calibration data
            try:
                channel_info = read.get_channel_info()
                if channel_info:
                    metadata['channel_info'] = channel_info
                    metadata['sample_rate'] = channel_info.get('sampling_rate', '')
            except Exception:
                pass

            # Only need first read for run-level metadata
            break

        # Count reads in file
        try:
            read_ids = f5.get_read_ids()
            metadata['read_count'] = len(read_ids)
        except Exception:
            metadata['read_count'] = 1 if metadata['fast5_format'] == FAST5_SINGLE_READ else 'unknown'

    return metadata


def _parse_fast5_with_h5py(filepath: Path, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse Fast5 using raw h5py (fallback method).

    Used when ont_fast5_api is not available.
    """
    def decode_attr(attr):
        """Decode HDF5 attribute value (handles bytes and numpy types)."""
        if attr is None:
            return None
        if isinstance(attr, bytes):
            return attr.decode('utf-8', errors='replace')
        if hasattr(attr, 'item'):  # numpy types
            return attr.item()
        return str(attr)

    with h5py.File(filepath, 'r') as f:
        is_multi = metadata['fast5_format'] == FAST5_MULTI_READ
        tracking_group = None
        context_group = None

        if is_multi:
            # Multi-read fast5: look in first read_* group
            read_groups = [k for k in f.keys() if k.startswith('read_')]
            if read_groups:
                read_key = sorted(read_groups)[0]
                base = f[read_key]
                if 'tracking_id' in base:
                    tracking_group = base['tracking_id']
                if 'context_tags' in base:
                    context_group = base['context_tags']
            metadata['read_count'] = len(read_groups)
        else:
            # Single-read fast5: look in UniqueGlobalKey
            if 'UniqueGlobalKey' in f:
                ugk = f['UniqueGlobalKey']
                if 'tracking_id' in ugk:
                    tracking_group = ugk['tracking_id']
                if 'context_tags' in ugk:
                    context_group = ugk['context_tags']
            # Also check root level
            if tracking_group is None and 'tracking_id' in f:
                tracking_group = f['tracking_id']
            if context_group is None and 'context_tags' in f:
                context_group = f['context_tags']
            metadata['read_count'] = 1

        # Extract tracking_id attributes
        if tracking_group is not None:
            attrs = tracking_group.attrs
            tracking = {k: decode_attr(v) for k, v in attrs.items()}
            metadata['tracking_id'] = tracking
            metadata['run_id'] = tracking.get('run_id', '')
            metadata['flow_cell_id'] = tracking.get('flow_cell_id', '')
            metadata['flow_cell_product_code'] = tracking.get('flow_cell_product_code', '')
            metadata['sample_id'] = tracking.get('sample_id', '')
            metadata['protocol_group_id'] = tracking.get('protocol_group_id', '')
            metadata['protocol_run_id'] = tracking.get('protocol_run_id', '')
            metadata['device_id'] = tracking.get('device_id', '')
            metadata['device_type'] = tracking.get('device_type', '')
            metadata['instrument'] = tracking.get('device_type', '') or tracking.get('hostname', '')
            metadata['exp_start_time'] = tracking.get('exp_start_time', '')
            metadata['started'] = tracking.get('exp_start_time', '')
            metadata['acquisition_id'] = tracking.get('acquisition_id', '')

        # Extract context_tags attributes
        if context_group is not None:
            attrs = context_group.attrs
            context = {k: decode_attr(v) for k, v in attrs.items()}
            metadata['context_tags'] = context
            metadata['experiment_type'] = context.get('experiment_type', '')
            metadata['experiment_kit'] = context.get('experiment_kit', '')
            metadata['sequencing_kit'] = context.get('sequencing_kit', '')
            metadata['basecall_model'] = context.get('basecall_model_version_id', '')
            metadata['local_basecalling'] = context.get('local_basecalling', '')
            metadata['barcoding_enabled'] = context.get('barcoding_enabled', '')

    return metadata


def scan_fast5_directory(directory: Path, max_files: int = 3) -> Dict[str, Any]:
    """
    Scan directory for Fast5 files and extract metadata.

    Detects file types (single-read, multi-read, bulk) and extracts
    run-level metadata using ont_fast5_api or h5py.

    Args:
        directory: Directory to scan
        max_files: Max files to parse

    Returns:
        Aggregated metadata from Fast5 files
    """
    if not HAS_H5PY and not HAS_ONT_FAST5_API:
        return {'file_type': 'fast5', 'error': 'Neither ont_fast5_api nor h5py library installed'}

    fast5_files = list(directory.rglob('*.fast5'))
    if not fast5_files:
        return {'file_type': 'fast5', 'error': 'No Fast5 files found'}

    # Detect file types in directory
    file_types = {}
    for f5_file in fast5_files[:min(10, len(fast5_files))]:
        ftype = detect_fast5_type(f5_file)
        file_types[ftype] = file_types.get(ftype, 0) + 1

    # Parse first few files to get metadata
    metadata = None
    for fast5_file in fast5_files[:max_files]:
        try:
            metadata = parse_fast5_metadata(fast5_file)
            if metadata and not metadata.get('parse_error'):
                break
        except Exception as e:
            logger.warning(f"Error scanning {fast5_file}: {e}")
            continue

    if not metadata:
        metadata = {'file_type': 'fast5', 'error': 'Failed to parse any Fast5 files'}

    metadata['fast5_count'] = len(fast5_files)
    metadata['fast5_types_found'] = file_types
    metadata['parser_used'] = 'ont_fast5_api' if HAS_ONT_FAST5_API else 'h5py'
    return metadata


# =============================================================================
# Unified Interface
# =============================================================================

def detect_raw_data_type(directory: Path) -> Optional[str]:
    """
    Detect what type of raw data is in a directory.

    Returns:
        'pod5', 'fast5', 'both', or None
    """
    has_pod5 = bool(list(directory.rglob('*.pod5')))
    has_fast5 = bool(list(directory.rglob('*.fast5')))

    if has_pod5 and has_fast5:
        return 'both'
    elif has_pod5:
        return 'pod5'
    elif has_fast5:
        return 'fast5'
    return None


def extract_metadata_from_dir(directory: Path) -> Dict[str, Any]:
    """
    Extract metadata from a directory containing raw ONT data.

    Auto-detects file format (POD5 vs Fast5) and extracts run-level metadata.
    Prefers POD5 if both are present (newer format with better metadata).

    Args:
        directory: Path to experiment directory

    Returns:
        Dict with extracted metadata
    """
    directory = Path(directory)

    if not directory.exists():
        return {'error': f'Directory not found: {directory}'}

    data_type = detect_raw_data_type(directory)

    if data_type is None:
        return {'error': 'No POD5 or Fast5 files found'}

    # Count files
    pod5_count = len(list(directory.rglob('*.pod5')))
    fast5_count = len(list(directory.rglob('*.fast5')))

    # Prefer POD5 (newer format, better metadata structure)
    if data_type in ('pod5', 'both') and HAS_POD5:
        metadata = scan_pod5_directory(directory)
    elif data_type in ('fast5', 'both') and HAS_H5PY:
        metadata = scan_fast5_directory(directory)
    elif data_type == 'pod5':
        return {'file_type': 'pod5', 'error': 'pod5 library not installed', 'pod5_count': pod5_count}
    elif data_type == 'fast5':
        return {'file_type': 'fast5', 'error': 'h5py library not installed', 'fast5_count': fast5_count}
    else:
        return {'error': 'Required libraries not installed'}

    # Add file counts
    metadata['pod5_count'] = pod5_count
    metadata['fast5_count'] = fast5_count
    metadata['data_type'] = data_type
    metadata['directory'] = str(directory)

    return metadata


def find_experiment_directories(scan_dir: Path) -> List[Path]:
    """
    Find potential experiment directories containing raw ONT data.

    An experiment directory is identified by containing:
    - POD5 files, or
    - Fast5 files, or
    - final_summary*.txt files

    Args:
        scan_dir: Root directory to scan

    Returns:
        List of experiment directory paths
    """
    experiment_dirs = set()

    # Method 1: Find directories with final_summary files
    for summary in scan_dir.rglob('final_summary*.txt'):
        experiment_dirs.add(summary.parent)

    # Method 2: Find directories with POD5 files
    for pod5_file in scan_dir.rglob('*.pod5'):
        # Walk up to find the experiment root
        # Usually: experiment_dir/pod5_pass/*.pod5 or experiment_dir/pod5/*.pod5
        parent = pod5_file.parent
        # Check if parent is a pod5 subdirectory
        if parent.name in ('pod5', 'pod5_pass', 'pod5_fail', 'pod5_skip'):
            experiment_dirs.add(parent.parent)
        else:
            experiment_dirs.add(parent)

    # Method 3: Find directories with Fast5 files
    for fast5_file in scan_dir.rglob('*.fast5'):
        parent = fast5_file.parent
        # Check if parent is a fast5 subdirectory
        if parent.name in ('fast5', 'fast5_pass', 'fast5_fail', 'fast5_skip'):
            experiment_dirs.add(parent.parent)
        else:
            experiment_dirs.add(parent)

    return list(experiment_dirs)


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """CLI for testing metadata extraction."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Extract metadata from ONT raw data files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('path', help='File or directory to parse')
    parser.add_argument('--format', choices=['pod5', 'fast5', 'auto'],
                       default='auto', help='File format (default: auto-detect)')
    parser.add_argument('--json', metavar='FILE', help='Output metadata to JSON file')
    parser.add_argument('--find-experiments', action='store_true',
                       help='Find all experiment directories in path')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')

    args = parser.parse_args()
    path = Path(args.path)

    if args.find_experiments:
        print(f"Scanning for experiments in: {path}")
        exp_dirs = find_experiment_directories(path)
        print(f"\nFound {len(exp_dirs)} experiment directories:")
        for exp_dir in sorted(exp_dirs):
            print(f"  {exp_dir}")
        return 0

    if not path.exists():
        print(f"Error: Path not found: {path}", file=sys.stderr)
        return 1

    print(f"Extracting metadata from: {path}")
    print(f"POD5 library: {'available' if HAS_POD5 else 'not installed'}")
    print(f"ont_fast5_api: {'available' if HAS_ONT_FAST5_API else 'not installed'}")
    print(f"h5py library: {'available' if HAS_H5PY else 'not installed'}")
    print()

    if path.is_file():
        if path.suffix == '.pod5':
            if not HAS_POD5:
                print("Error: pod5 library not installed", file=sys.stderr)
                return 1
            metadata = parse_pod5_metadata(path)
        elif path.suffix == '.fast5':
            if not HAS_H5PY:
                print("Error: h5py library not installed", file=sys.stderr)
                return 1
            metadata = parse_fast5_metadata(path)
        else:
            print(f"Error: Unsupported file type: {path.suffix}", file=sys.stderr)
            return 1
    else:
        metadata = extract_metadata_from_dir(path)

    # Print metadata
    print("Extracted Metadata:")
    print("-" * 50)

    # Key fields to show
    key_fields = [
        'flow_cell_id', 'sample_id', 'acquisition_id', 'protocol',
        'instrument', 'started', 'sequencing_kit', 'experiment_name',
        'protocol_group_id', 'pod5_count', 'fast5_count',
        'fast5_format', 'read_count', 'fast5_types_found', 'parser_used'
    ]

    for field in key_fields:
        if field in metadata and metadata[field]:
            print(f"  {field}: {metadata[field]}")

    if args.verbose:
        print("\nFull metadata:")
        for k, v in sorted(metadata.items()):
            if k not in key_fields:
                print(f"  {k}: {v}")

    if metadata.get('parse_error'):
        print(f"\nWarning: {metadata['parse_error']}")

    # Write JSON
    if args.json:
        with open(args.json, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        print(f"\nMetadata written to: {args.json}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
