#!/usr/bin/env python3
"""
End Reason Analysis - ONT QC Skill

Analyze Oxford Nanopore read end reasons for quality assessment,
adaptive sampling efficiency, and sequencing diagnostics.

Designed for Pattern B integration with ont-experiments:
  ont_experiments.py run end_reasons <exp_id> --json results.json

Can also run standalone:
  python3 end_reason.py /path/to/data --json results.json

Output fields (captured by ont-experiments):
  - total_reads
  - quality_status (OK, CHECK, FAIL)
  - signal_positive_pct
  - unblock_mux_pct
  - data_service_pct
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import time

# Optional imports
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

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except (ImportError, AttributeError):
    # AttributeError catches numpy version incompatibility (_ARRAY_API not found)
    HAS_MATPLOTLIB = False

try:
    import pandas as pd
    HAS_PANDAS = True
except (ImportError, AttributeError):
    # AttributeError catches numpy version incompatibility
    HAS_PANDAS = False


# =============================================================================
# End Reason Definitions
# =============================================================================

END_REASON_CATEGORIES = {
    # Normal completion
    'signal_positive': {
        'description': 'Normal read completion with good signal',
        'expected_range': (75, 95),
        'severity': 'good',
    },
    # Adaptive sampling rejections
    'unblock_mux_change': {
        'description': 'Rejected by adaptive sampling (hardware)',
        'expected_range': (0, 20),
        'severity': 'info',
    },
    'data_service_unblock_mux_change': {
        'description': 'Rejected by adaptive sampling (basecall)',
        'expected_range': (0, 15),
        'severity': 'info',
    },
    # Pore management
    'mux_change': {
        'description': 'Pore multiplexer change',
        'expected_range': (0, 10),
        'severity': 'neutral',
    },
    # Signal issues
    'signal_negative': {
        'description': 'Signal lost or degraded',
        'expected_range': (0, 5),
        'severity': 'warning',
    },
    # Unknown
    'unknown': {
        'description': 'Unknown or unclassified end reason',
        'expected_range': (0, 5),
        'severity': 'warning',
    },
}

# Mapping from various formats to canonical names
END_REASON_ALIASES = {
    # POD5 end reasons
    0: 'unknown',
    1: 'signal_positive',
    2: 'signal_negative', 
    3: 'mux_change',
    4: 'unblock_mux_change',
    5: 'data_service_unblock_mux_change',
    
    # String variants
    'signal_positive': 'signal_positive',
    'signal_negative': 'signal_negative',
    'mux_change': 'mux_change',
    'unblock_mux_change': 'unblock_mux_change',
    'data_service_unblock_mux_change': 'data_service_unblock_mux_change',
    'unknown': 'unknown',
    
    # Fast5/sequencing_summary variants
    'data_service': 'data_service_unblock_mux_change',
    'adaptive_sampling': 'unblock_mux_change',
}


# =============================================================================
# Data Extraction
# =============================================================================

def normalize_end_reason(reason: Any) -> str:
    """Normalize end reason to canonical name"""
    if reason in END_REASON_ALIASES:
        return END_REASON_ALIASES[reason]
    
    if isinstance(reason, str):
        reason_lower = reason.lower().replace(' ', '_')
        if reason_lower in END_REASON_ALIASES:
            return END_REASON_ALIASES[reason_lower]
    
    return 'unknown'


def extract_from_pod5(path: Path, quick: bool = False, max_reads: int = 10000) -> List[Dict]:
    """Extract end reasons from POD5 file(s)"""
    if not HAS_POD5:
        raise ImportError("pod5 not installed: pip install pod5")
    
    reads = []
    
    pod5_files = [path] if path.suffix == '.pod5' else list(path.rglob('*.pod5'))
    
    for pod5_file in pod5_files:
        try:
            with pod5.Reader(pod5_file) as reader:
                for read in reader.reads():
                    reads.append({
                        'read_id': str(read.read_id),
                        'channel': read.pore.channel,
                        'end_reason': normalize_end_reason(read.end_reason.value),
                        'duration': read.num_samples / read.run_info.sample_rate if read.run_info.sample_rate else 0,
                    })
                    
                    if quick and len(reads) >= max_reads:
                        return reads
        except Exception as e:
            print(f"  Warning: Error reading {pod5_file}: {e}", file=sys.stderr)
    
    return reads


def extract_from_fast5(path: Path, quick: bool = False, max_reads: int = 10000) -> List[Dict]:
    """Extract end reasons from Fast5 file(s)"""
    if not HAS_H5PY:
        raise ImportError("h5py not installed: pip install h5py")
    
    reads = []
    
    fast5_files = [path] if path.suffix == '.fast5' else list(path.rglob('*.fast5'))
    
    for fast5_file in fast5_files:
        try:
            with h5py.File(fast5_file, 'r') as f:
                # Handle multi-read fast5
                read_groups = [k for k in f.keys() if k.startswith('read_')]
                if not read_groups:
                    read_groups = ['']
                
                for read_group in read_groups:
                    base = f[read_group] if read_group else f
                    
                    # Try to find end_reason
                    end_reason = 'unknown'
                    channel = 0
                    read_id = ''
                    duration = 0
                    
                    # Check various locations
                    for path_prefix in ['', 'Raw/', 'Analyses/']:
                        try:
                            if f'{path_prefix}channel_id' in base:
                                channel = int(base[f'{path_prefix}channel_id'].attrs.get('channel_number', 0))
                        except:
                            pass
                        
                        try:
                            if f'{path_prefix}tracking_id' in base:
                                tracking = base[f'{path_prefix}tracking_id']
                                read_id = tracking.attrs.get('read_id', b'').decode() if isinstance(tracking.attrs.get('read_id'), bytes) else str(tracking.attrs.get('read_id', ''))
                        except:
                            pass
                    
                    reads.append({
                        'read_id': read_id or read_group,
                        'channel': channel,
                        'end_reason': end_reason,
                        'duration': duration,
                    })
                    
                    if quick and len(reads) >= max_reads:
                        return reads
        except Exception as e:
            print(f"  Warning: Error reading {fast5_file}: {e}", file=sys.stderr)
    
    return reads


def extract_from_summary(path: Path, quick: bool = False, max_reads: int = 10000) -> List[Dict]:
    """Extract end reasons from sequencing_summary.txt"""
    reads = []
    
    summary_files = [path] if path.suffix == '.txt' else list(path.rglob('*sequencing_summary*.txt'))
    
    for summary_file in summary_files:
        try:
            with open(summary_file, 'r') as f:
                header = f.readline().strip().split('\t')
                
                # Find relevant columns
                cols = {}
                for i, col in enumerate(header):
                    col_lower = col.lower()
                    if 'read_id' in col_lower:
                        cols['read_id'] = i
                    elif 'channel' in col_lower:
                        cols['channel'] = i
                    elif 'end_reason' in col_lower:
                        cols['end_reason'] = i
                    elif 'duration' in col_lower:
                        cols['duration'] = i
                
                if 'end_reason' not in cols:
                    continue
                
                for line in f:
                    parts = line.strip().split('\t')
                    
                    read_id = parts[cols.get('read_id', 0)] if 'read_id' in cols else ''
                    channel = int(parts[cols['channel']]) if 'channel' in cols and cols['channel'] < len(parts) else 0
                    end_reason = normalize_end_reason(parts[cols['end_reason']]) if cols['end_reason'] < len(parts) else 'unknown'
                    duration = float(parts[cols['duration']]) if 'duration' in cols and cols['duration'] < len(parts) else 0
                    
                    reads.append({
                        'read_id': read_id,
                        'channel': channel,
                        'end_reason': end_reason,
                        'duration': duration,
                    })
                    
                    if quick and len(reads) >= max_reads:
                        return reads
        except Exception as e:
            print(f"  Warning: Error reading {summary_file}: {e}", file=sys.stderr)
    
    return reads


def detect_format(path: Path) -> str:
    """Detect data format in path.

    Prefers summary files (always available) over pod5/fast5 which require
    optional dependencies.
    """
    if path.suffix == '.pod5':
        return 'pod5'
    if path.suffix == '.fast5':
        return 'fast5'
    if path.suffix == '.txt' and 'sequencing_summary' in path.name:
        return 'summary'

    if path.is_dir():
        # Prefer summary (always works) > POD5 (if installed) > Fast5 (if installed)
        if list(path.rglob('*sequencing_summary*.txt')):
            return 'summary'
        if HAS_POD5 and list(path.rglob('*.pod5')):
            return 'pod5'
        if HAS_H5PY and list(path.rglob('*.fast5')):
            return 'fast5'
        # Fall back to pod5/fast5 even if not installed (will error with helpful message)
        if list(path.rglob('*.pod5')):
            return 'pod5'
        if list(path.rglob('*.fast5')):
            return 'fast5'

    return 'unknown'


# =============================================================================
# Analysis
# =============================================================================

def analyze_end_reasons(reads: List[Dict]) -> Dict[str, Any]:
    """Analyze end reason distribution and quality"""
    if not reads:
        return {
            'total_reads': 0,
            'quality_status': 'FAIL',
            'error': 'No reads found',
        }
    
    # Count end reasons
    counter = Counter(r['end_reason'] for r in reads)
    total = len(reads)
    
    # Build distribution
    distribution = {}
    for reason, count in counter.most_common():
        pct = (count / total) * 100
        distribution[reason] = {
            'count': count,
            'pct': round(pct, 2),
        }
    
    # Extract key percentages
    signal_positive_pct = distribution.get('signal_positive', {}).get('pct', 0)
    unblock_mux_pct = distribution.get('unblock_mux_change', {}).get('pct', 0)
    data_service_pct = distribution.get('data_service_unblock_mux_change', {}).get('pct', 0)
    signal_negative_pct = distribution.get('signal_negative', {}).get('pct', 0)
    
    # Determine quality status
    quality_status = 'OK'
    quality_issues = []
    
    # Check signal_positive threshold
    if signal_positive_pct < 50:
        quality_status = 'FAIL'
        quality_issues.append(f'signal_positive too low ({signal_positive_pct:.1f}% < 50%)')
    elif signal_positive_pct < 75:
        if quality_status != 'FAIL':
            quality_status = 'CHECK'
        quality_issues.append(f'signal_positive below optimal ({signal_positive_pct:.1f}% < 75%)')
    
    # Check signal_negative
    if signal_negative_pct > 20:
        if quality_status != 'FAIL':
            quality_status = 'CHECK'
        quality_issues.append(f'high signal_negative ({signal_negative_pct:.1f}% > 20%)')
    
    # Note adaptive sampling
    adaptive_pct = unblock_mux_pct + data_service_pct
    adaptive_note = None
    if adaptive_pct > 5:
        adaptive_note = f'Adaptive sampling detected ({adaptive_pct:.1f}% rejections)'
    
    return {
        'total_reads': total,
        'end_reasons': distribution,
        'signal_positive_pct': round(signal_positive_pct, 2),
        'unblock_mux_pct': round(unblock_mux_pct, 2),
        'data_service_pct': round(data_service_pct, 2),
        'quality_status': quality_status,
        'quality_issues': quality_issues if quality_issues else None,
        'adaptive_note': adaptive_note,
    }


# =============================================================================
# Output
# =============================================================================

def print_summary(analysis: Dict[str, Any], verbose: bool = False):
    """Print analysis summary to console"""
    status_symbols = {'OK': '✓', 'CHECK': '⚠', 'FAIL': '✗'}
    
    print(f"\n  End Reason Analysis")
    print(f"  {'═' * 50}")
    
    print(f"\n  Total Reads: {analysis['total_reads']:,}")
    
    status = analysis['quality_status']
    symbol = status_symbols.get(status, '?')
    print(f"  Quality: {symbol} {status}")
    
    if analysis.get('quality_issues'):
        for issue in analysis['quality_issues']:
            print(f"    - {issue}")
    
    if analysis.get('adaptive_note'):
        print(f"  Note: {analysis['adaptive_note']}")
    
    print(f"\n  End Reason Distribution")
    print(f"  {'─' * 40}")
    
    for reason, data in analysis.get('end_reasons', {}).items():
        count = data['count']
        pct = data['pct']
        bar_len = int(pct / 5)
        bar = '█' * bar_len + '░' * (20 - bar_len)
        print(f"  {reason:<35} {pct:5.1f}% {bar} ({count:,})")
    
    print()


def write_json(analysis: Dict[str, Any], filepath: Path):
    """Write analysis to JSON file"""
    with open(filepath, 'w') as f:
        json.dump(analysis, f, indent=2)
    print(f"  JSON written: {filepath}")


def write_csv(reads: List[Dict], filepath: Path):
    """Write per-read data to CSV"""
    if HAS_PANDAS:
        df = pd.DataFrame(reads)
        df.to_csv(filepath, index=False)
    else:
        # Manual CSV writing
        with open(filepath, 'w') as f:
            if reads:
                headers = list(reads[0].keys())
                f.write(','.join(headers) + '\n')
                for read in reads:
                    f.write(','.join(str(read.get(h, '')) for h in headers) + '\n')
    
    print(f"  CSV written: {filepath} ({len(reads)} reads)")


def write_plot(analysis: Dict[str, Any], filepath: Path):
    """Create end reason distribution plot"""
    if not HAS_MATPLOTLIB:
        print("  Warning: matplotlib not installed, skipping plot", file=sys.stderr)
        return
    
    reasons = list(analysis.get('end_reasons', {}).keys())
    percentages = [analysis['end_reasons'][r]['pct'] for r in reasons]
    
    # Color scheme
    colors = []
    for reason in reasons:
        if reason == 'signal_positive':
            colors.append('#2ecc71')  # Green
        elif reason in ('unblock_mux_change', 'data_service_unblock_mux_change'):
            colors.append('#3498db')  # Blue
        elif reason == 'signal_negative':
            colors.append('#e74c3c')  # Red
        else:
            colors.append('#95a5a6')  # Gray
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    bars = ax.barh(reasons, percentages, color=colors)
    
    # Add percentage labels
    for bar, pct in zip(bars, percentages):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                f'{pct:.1f}%', va='center', fontsize=10)
    
    ax.set_xlabel('Percentage of Reads')
    ax.set_title(f'End Reason Distribution (n={analysis["total_reads"]:,})')
    ax.set_xlim(0, 105)
    
    # Add quality status
    status = analysis['quality_status']
    status_color = {'OK': 'green', 'CHECK': 'orange', 'FAIL': 'red'}.get(status, 'gray')
    ax.text(0.98, 0.98, f'Status: {status}', transform=ax.transAxes,
            ha='right', va='top', fontsize=12, fontweight='bold', color=status_color)
    
    plt.tight_layout()
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  Plot written: {filepath}")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='ONT End Reason Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s /path/to/experiment
  %(prog)s /path/to/data --json results.json --plot qc.png
  %(prog)s /path/to/data --quick --csv reads.csv

Integration with ont-experiments:
  ont_experiments.py run end_reasons exp-abc123 --json results.json
'''
    )
    
    parser.add_argument('path', help='Experiment directory or data file')
    parser.add_argument('--json', metavar='FILE', help='Output JSON summary')
    parser.add_argument('--csv', metavar='FILE', help='Output per-read CSV')
    parser.add_argument('--plot', metavar='FILE', help='Output distribution plot')
    parser.add_argument('--format', choices=['pod5', 'fast5', 'summary', 'auto'],
                        default='auto', help='Data format (default: auto-detect)')
    parser.add_argument('--quick', action='store_true', help='Quick mode (sample 10k reads)')
    parser.add_argument('--max-reads', type=int, default=10000, help='Max reads in quick mode')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    path = Path(args.path).resolve()
    
    if not path.exists():
        print(f"Error: Path not found: {path}", file=sys.stderr)
        return 1
    
    # Detect format
    data_format = args.format if args.format != 'auto' else detect_format(path)
    
    if data_format == 'unknown':
        print(f"Error: No supported data found in: {path}", file=sys.stderr)
        print(f"       Supported: POD5, Fast5, sequencing_summary.txt", file=sys.stderr)
        return 1
    
    print(f"\n  Path: {path}")
    print(f"  Format: {data_format}")
    print(f"  Mode: {'quick' if args.quick else 'full'}")
    
    # Extract data
    start_time = time.time()
    
    try:
        if data_format == 'pod5':
            reads = extract_from_pod5(path, quick=args.quick, max_reads=args.max_reads)
        elif data_format == 'fast5':
            reads = extract_from_fast5(path, quick=args.quick, max_reads=args.max_reads)
        elif data_format == 'summary':
            reads = extract_from_summary(path, quick=args.quick, max_reads=args.max_reads)
        else:
            print(f"Error: Unsupported format: {data_format}", file=sys.stderr)
            return 1
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error extracting data: {e}", file=sys.stderr)
        return 1
    
    extraction_time = time.time() - start_time
    
    if not reads:
        print(f"Error: No reads extracted", file=sys.stderr)
        return 1
    
    print(f"  Extracted: {len(reads):,} reads ({extraction_time:.1f}s)")
    
    # Analyze
    analysis = analyze_end_reasons(reads)
    analysis['experiment_path'] = str(path)
    analysis['data_format'] = data_format
    analysis['analysis_duration_seconds'] = round(time.time() - start_time, 2)
    
    # Output
    print_summary(analysis, verbose=args.verbose)
    
    if args.json:
        write_json(analysis, Path(args.json))
    
    if args.csv:
        write_csv(reads, Path(args.csv))
    
    if args.plot:
        write_plot(analysis, Path(args.plot))
    
    # Exit code based on quality
    if analysis['quality_status'] == 'FAIL':
        return 2
    elif analysis['quality_status'] == 'CHECK':
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
