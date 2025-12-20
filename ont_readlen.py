#!/usr/bin/env python3
"""
ONT Read Length Distribution Analysis

Extracts and visualizes read length distributions from Oxford Nanopore
sequencing data. Supports multi-experiment comparison with statistical
analysis and publication-quality plots.

Data Sources:
- sequencing_summary.txt (fastest)
- BAM/SAM files
- POD5 files (with pod5 library)
- FASTQ files

Integrates with ont-experiments for provenance tracking via Pattern B.
"""

import argparse
import json
import sys
import os
import gzip
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Iterator
from dataclasses import dataclass, asdict
from collections import defaultdict
import hashlib

# Optional imports for different data sources
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import pysam
    HAS_PYSAM = True
except ImportError:
    HAS_PYSAM = False

try:
    import pod5
    HAS_POD5 = True
except ImportError:
    HAS_POD5 = False

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


@dataclass
class ReadLengthStats:
    """Statistics for a read length distribution"""
    experiment_id: str
    experiment_name: str
    source_file: str
    total_reads: int
    total_bases: int
    mean_length: float
    median_length: float
    std_length: float
    min_length: int
    max_length: int
    n50: int
    n90: int
    l50: int
    q1_length: float  # 25th percentile
    q3_length: float  # 75th percentile
    reads_gt_1kb: int
    reads_gt_5kb: int
    reads_gt_10kb: int
    reads_gt_20kb: int
    reads_gt_50kb: int
    reads_gt_100kb: int
    pct_gt_1kb: float
    pct_gt_5kb: float
    pct_gt_10kb: float
    histogram_bins: List[int]
    histogram_counts: List[int]
    timestamp: str
    
    def to_dict(self) -> dict:
        return asdict(self)


def calculate_nx(lengths: List[int], x: float = 50) -> Tuple[int, int]:
    """
    Calculate NX value (e.g., N50) and LX (count to reach NX)
    
    Args:
        lengths: List of read lengths (must be sorted descending)
        x: Percentile (50 for N50, 90 for N90, etc.)
    
    Returns:
        (nx_value, lx_count)
    """
    if not lengths:
        return 0, 0
    
    total = sum(lengths)
    target = total * (x / 100.0)
    cumsum = 0
    
    for i, length in enumerate(lengths):
        cumsum += length
        if cumsum >= target:
            return length, i + 1
    
    return lengths[-1], len(lengths)


def compute_stats(lengths: List[int], experiment_id: str, 
                  experiment_name: str, source_file: str,
                  bin_size: int = 1000, max_bin: int = 100000) -> ReadLengthStats:
    """Compute comprehensive statistics from read lengths"""
    
    if not lengths:
        raise ValueError("No reads found")
    
    if HAS_NUMPY:
        arr = np.array(lengths)
        mean_len = float(np.mean(arr))
        median_len = float(np.median(arr))
        std_len = float(np.std(arr))
        q1 = float(np.percentile(arr, 25))
        q3 = float(np.percentile(arr, 75))
    else:
        sorted_lens = sorted(lengths)
        n = len(sorted_lens)
        mean_len = sum(lengths) / n
        median_len = sorted_lens[n // 2]
        variance = sum((x - mean_len) ** 2 for x in lengths) / n
        std_len = variance ** 0.5
        q1 = sorted_lens[n // 4]
        q3 = sorted_lens[3 * n // 4]
    
    # Sort descending for NX calculations
    sorted_desc = sorted(lengths, reverse=True)
    n50, l50 = calculate_nx(sorted_desc, 50)
    n90, _ = calculate_nx(sorted_desc, 90)
    
    # Count reads above thresholds
    reads_gt_1kb = sum(1 for x in lengths if x >= 1000)
    reads_gt_5kb = sum(1 for x in lengths if x >= 5000)
    reads_gt_10kb = sum(1 for x in lengths if x >= 10000)
    reads_gt_20kb = sum(1 for x in lengths if x >= 20000)
    reads_gt_50kb = sum(1 for x in lengths if x >= 50000)
    reads_gt_100kb = sum(1 for x in lengths if x >= 100000)
    
    total = len(lengths)
    
    # Build histogram
    bins = list(range(0, max_bin + bin_size, bin_size))
    counts = [0] * len(bins)
    for length in lengths:
        bin_idx = min(length // bin_size, len(bins) - 1)
        counts[bin_idx] += 1
    
    return ReadLengthStats(
        experiment_id=experiment_id,
        experiment_name=experiment_name,
        source_file=source_file,
        total_reads=total,
        total_bases=sum(lengths),
        mean_length=round(mean_len, 1),
        median_length=round(median_len, 1),
        std_length=round(std_len, 1),
        min_length=min(lengths),
        max_length=max(lengths),
        n50=n50,
        n90=n90,
        l50=l50,
        q1_length=round(q1, 1),
        q3_length=round(q3, 1),
        reads_gt_1kb=reads_gt_1kb,
        reads_gt_5kb=reads_gt_5kb,
        reads_gt_10kb=reads_gt_10kb,
        reads_gt_20kb=reads_gt_20kb,
        reads_gt_50kb=reads_gt_50kb,
        reads_gt_100kb=reads_gt_100kb,
        pct_gt_1kb=round(100 * reads_gt_1kb / total, 2),
        pct_gt_5kb=round(100 * reads_gt_5kb / total, 2),
        pct_gt_10kb=round(100 * reads_gt_10kb / total, 2),
        histogram_bins=bins,
        histogram_counts=counts,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


def parse_sequencing_summary(filepath: Path, max_reads: int = None) -> List[int]:
    """Parse sequencing_summary.txt for read lengths"""
    lengths = []
    
    opener = gzip.open if str(filepath).endswith('.gz') else open
    
    with opener(filepath, 'rt') as f:
        header = f.readline().strip().split('\t')
        
        # Find the sequence_length_template column
        len_col = None
        for i, col in enumerate(header):
            if col in ('sequence_length_template', 'sequence_length', 'read_length'):
                len_col = i
                break
        
        if len_col is None:
            raise ValueError(f"Could not find length column in {filepath}")
        
        for line in f:
            if max_reads and len(lengths) >= max_reads:
                break
            
            parts = line.strip().split('\t')
            if len(parts) > len_col:
                try:
                    length = int(float(parts[len_col]))
                    if length > 0:
                        lengths.append(length)
                except (ValueError, IndexError):
                    continue
    
    return lengths


def parse_bam(filepath: Path, max_reads: int = None) -> List[int]:
    """Parse BAM/SAM file for read lengths"""
    if not HAS_PYSAM:
        raise ImportError("pysam required for BAM parsing: pip install pysam")
    
    lengths = []
    
    with pysam.AlignmentFile(str(filepath), "rb" if str(filepath).endswith('.bam') else "r") as bam:
        for read in bam:
            if max_reads and len(lengths) >= max_reads:
                break
            
            if not read.is_secondary and not read.is_supplementary:
                lengths.append(read.query_length or read.infer_read_length() or 0)
    
    return [x for x in lengths if x > 0]


def parse_fastq(filepath: Path, max_reads: int = None) -> List[int]:
    """Parse FASTQ file for read lengths"""
    lengths = []
    
    opener = gzip.open if str(filepath).endswith('.gz') else open
    
    with opener(filepath, 'rt') as f:
        line_num = 0
        for line in f:
            line_num += 1
            if line_num % 4 == 2:  # Sequence line
                lengths.append(len(line.strip()))
                if max_reads and len(lengths) >= max_reads:
                    break
    
    return lengths


def parse_pod5(filepath: Path, max_reads: int = None) -> List[int]:
    """Parse POD5 file for estimated read lengths"""
    if not HAS_POD5:
        raise ImportError("pod5 required: pip install pod5")
    
    lengths = []
    
    with pod5.Reader(filepath) as reader:
        for read in reader.reads():
            if max_reads and len(lengths) >= max_reads:
                break
            # Estimate length from signal (rough approximation)
            # Actual length requires basecalling
            sample_rate = read.run_info.sample_rate
            signal_len = len(read.signal)
            # ~450 bases/second for R10.4.1
            estimated_bases = int(signal_len / sample_rate * 450)
            lengths.append(estimated_bases)
    
    return lengths


def find_data_source(run_path: Path) -> Tuple[Path, str]:
    """Find the best data source in a run directory"""
    
    # Priority order: sequencing_summary > BAM > FASTQ > POD5
    
    # Check for sequencing_summary
    for pattern in ['sequencing_summary*.txt', 'sequencing_summary*.txt.gz']:
        matches = list(run_path.glob(pattern))
        if matches:
            return matches[0], 'sequencing_summary'
    
    # Check in standard MinKNOW subdirs
    for subdir in ['', 'basecalling', 'pass', 'fail']:
        check_path = run_path / subdir if subdir else run_path
        for pattern in ['sequencing_summary*.txt', 'sequencing_summary*.txt.gz']:
            matches = list(check_path.glob(pattern))
            if matches:
                return matches[0], 'sequencing_summary'
    
    # Check for BAM files
    for pattern in ['*.bam', 'pass/*.bam', 'basecalling/*.bam']:
        matches = list(run_path.glob(pattern))
        if matches:
            return matches[0], 'bam'
    
    # Check for FASTQ
    for pattern in ['*.fastq', '*.fastq.gz', '*.fq', '*.fq.gz', 
                    'pass/*.fastq.gz', 'fastq_pass/*.fastq.gz']:
        matches = list(run_path.glob(pattern))
        if matches:
            return matches[0], 'fastq'
    
    # Check for POD5
    for pattern in ['*.pod5', 'pod5_pass/*.pod5', 'pod5/*.pod5']:
        matches = list(run_path.glob(pattern))
        if matches:
            return matches[0], 'pod5'
    
    raise FileNotFoundError(f"No suitable data source found in {run_path}")


def extract_lengths(source_path: Path, source_type: str = None, 
                    max_reads: int = None) -> List[int]:
    """Extract read lengths from various file types"""
    
    if source_type is None:
        # Auto-detect from filename
        suffix = source_path.suffix.lower()
        name = source_path.name.lower()
        
        if 'sequencing_summary' in name:
            source_type = 'sequencing_summary'
        elif suffix in ('.bam', '.sam'):
            source_type = 'bam'
        elif suffix in ('.fastq', '.fq') or name.endswith('.fastq.gz') or name.endswith('.fq.gz'):
            source_type = 'fastq'
        elif suffix == '.pod5':
            source_type = 'pod5'
        else:
            raise ValueError(f"Cannot determine file type: {source_path}")
    
    parsers = {
        'sequencing_summary': parse_sequencing_summary,
        'bam': parse_bam,
        'fastq': parse_fastq,
        'pod5': parse_pod5,
    }
    
    parser = parsers.get(source_type)
    if not parser:
        raise ValueError(f"Unknown source type: {source_type}")
    
    return parser(source_path, max_reads)


def analyze_experiment(run_path: Path, experiment_id: str = None,
                       experiment_name: str = None, max_reads: int = None,
                       source_type: str = None) -> ReadLengthStats:
    """Analyze read lengths for a single experiment"""
    
    run_path = Path(run_path)
    
    # Find data source
    if run_path.is_file():
        source_path = run_path
    else:
        source_path, detected_type = find_data_source(run_path)
        if source_type is None:
            source_type = detected_type
    
    # Generate experiment ID if not provided
    if experiment_id is None:
        experiment_id = hashlib.sha256(str(run_path).encode()).hexdigest()[:8]
    
    if experiment_name is None:
        experiment_name = run_path.parent.name if run_path.is_file() else run_path.name
    
    # Extract lengths
    lengths = extract_lengths(source_path, source_type, max_reads)
    
    # Compute statistics
    stats = compute_stats(lengths, experiment_id, experiment_name, str(source_path))
    
    return stats


def plot_single_distribution(stats: ReadLengthStats, output_path: Path,
                             title: str = None, log_scale: bool = False,
                             max_length: int = None):
    """Generate histogram plot for single experiment"""
    
    if not HAS_MATPLOTLIB:
        raise ImportError("matplotlib required for plotting: pip install matplotlib")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    bins = stats.histogram_bins
    counts = stats.histogram_counts
    
    if max_length:
        max_idx = next((i for i, b in enumerate(bins) if b > max_length), len(bins))
        bins = bins[:max_idx]
        counts = counts[:max_idx]
    
    # Plot histogram
    bar_width = bins[1] - bins[0] if len(bins) > 1 else 1000
    ax.bar(bins, counts, width=bar_width * 0.9, color='steelblue', 
           edgecolor='darkblue', alpha=0.7)
    
    # Add vertical lines for key statistics
    ax.axvline(stats.mean_length, color='red', linestyle='--', linewidth=2,
               label=f'Mean: {stats.mean_length:,.0f} bp')
    ax.axvline(stats.median_length, color='green', linestyle='--', linewidth=2,
               label=f'Median: {stats.median_length:,.0f} bp')
    ax.axvline(stats.n50, color='orange', linestyle='--', linewidth=2,
               label=f'N50: {stats.n50:,} bp')
    
    if log_scale:
        ax.set_yscale('log')
    
    ax.set_xlabel('Read Length (bp)', fontsize=12)
    ax.set_ylabel('Count', fontsize=12)
    
    if title is None:
        title = f"Read Length Distribution: {stats.experiment_name}"
    ax.set_title(title, fontsize=14, fontweight='bold')
    
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    # Add stats box
    stats_text = (
        f"Total Reads: {stats.total_reads:,}\n"
        f"Total Bases: {stats.total_bases / 1e9:.2f} Gb\n"
        f"Max Length: {stats.max_length:,} bp\n"
        f">10kb: {stats.pct_gt_10kb:.1f}%"
    )
    ax.text(0.98, 0.98, stats_text, transform=ax.transAxes,
            fontsize=10, verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def plot_multi_comparison(all_stats: List[ReadLengthStats], output_path: Path,
                          title: str = "Read Length Distribution Comparison",
                          plot_type: str = "overlay", max_length: int = None,
                          normalize: bool = True):
    """Generate comparison plot for multiple experiments"""
    
    if not HAS_MATPLOTLIB:
        raise ImportError("matplotlib required for plotting: pip install matplotlib")
    
    if not HAS_NUMPY:
        raise ImportError("numpy required for multi-plot: pip install numpy")
    
    colors = plt.cm.tab10.colors
    
    if plot_type == "overlay":
        fig, ax = plt.subplots(figsize=(12, 7))
        
        for i, stats in enumerate(all_stats):
            bins = np.array(stats.histogram_bins)
            counts = np.array(stats.histogram_counts)
            
            if max_length:
                mask = bins <= max_length
                bins = bins[mask]
                counts = counts[mask]
            
            if normalize:
                counts = counts / counts.sum() * 100  # Convert to percentage
            
            color = colors[i % len(colors)]
            ax.plot(bins, counts, linewidth=2, color=color,
                    label=f"{stats.experiment_name} (N50={stats.n50:,})")
            ax.fill_between(bins, counts, alpha=0.2, color=color)
        
        ax.set_xlabel('Read Length (bp)', fontsize=12)
        ax.set_ylabel('Percentage of Reads' if normalize else 'Count', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(True, alpha=0.3)
        
    elif plot_type == "violin":
        # For violin, we need raw length data - use binned approximation
        fig, ax = plt.subplots(figsize=(max(8, len(all_stats) * 1.5), 7))
        
        # Create violin-like representation from histogram data
        positions = list(range(len(all_stats)))
        labels = [s.experiment_name for s in all_stats]
        
        # Draw box plot approximation
        for i, stats in enumerate(all_stats):
            box_data = {
                'med': stats.median_length,
                'q1': stats.q1_length,
                'q3': stats.q3_length,
                'whislo': stats.min_length,
                'whishi': min(stats.max_length, stats.q3_length + 1.5 * (stats.q3_length - stats.q1_length)),
                'mean': stats.mean_length,
            }
            
            bp = ax.bxp([box_data], positions=[i], widths=0.6, 
                        patch_artist=True, showmeans=True,
                        meanprops=dict(marker='D', markerfacecolor='red', markersize=8))
            bp['boxes'][0].set_facecolor(colors[i % len(colors)])
            bp['boxes'][0].set_alpha(0.6)
        
        ax.set_xticks(positions)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.set_ylabel('Read Length (bp)', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
    elif plot_type == "bar":
        # Bar chart comparing key metrics
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        names = [s.experiment_name[:20] for s in all_stats]
        x = np.arange(len(names))
        width = 0.6
        
        # N50
        ax = axes[0, 0]
        n50s = [s.n50 for s in all_stats]
        bars = ax.bar(x, n50s, width, color=[colors[i % len(colors)] for i in range(len(all_stats))])
        ax.set_ylabel('N50 (bp)')
        ax.set_title('N50 Read Length')
        ax.set_xticks(x)
        ax.set_xticklabels(names, rotation=45, ha='right')
        ax.bar_label(bars, fmt=lambda v: f'{v/1000:.1f}k', fontsize=8)
        
        # Mean length
        ax = axes[0, 1]
        means = [s.mean_length for s in all_stats]
        bars = ax.bar(x, means, width, color=[colors[i % len(colors)] for i in range(len(all_stats))])
        ax.set_ylabel('Mean Length (bp)')
        ax.set_title('Mean Read Length')
        ax.set_xticks(x)
        ax.set_xticklabels(names, rotation=45, ha='right')
        
        # Total reads
        ax = axes[1, 0]
        reads = [s.total_reads / 1e6 for s in all_stats]
        bars = ax.bar(x, reads, width, color=[colors[i % len(colors)] for i in range(len(all_stats))])
        ax.set_ylabel('Total Reads (millions)')
        ax.set_title('Total Read Count')
        ax.set_xticks(x)
        ax.set_xticklabels(names, rotation=45, ha='right')
        
        # Percentage >10kb
        ax = axes[1, 1]
        pct10k = [s.pct_gt_10kb for s in all_stats]
        bars = ax.bar(x, pct10k, width, color=[colors[i % len(colors)] for i in range(len(all_stats))])
        ax.set_ylabel('Percentage')
        ax.set_title('Reads >10kb (%)')
        ax.set_xticks(x)
        ax.set_xticklabels(names, rotation=45, ha='right')
        ax.bar_label(bars, fmt='%.1f%%', fontsize=8)
        
        plt.suptitle(title, fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def generate_summary_table(all_stats: List[ReadLengthStats]) -> str:
    """Generate ASCII summary table"""
    
    headers = ['Experiment', 'Reads', 'Bases (Gb)', 'Mean', 'Median', 'N50', 'Max', '>10kb%']
    
    rows = []
    for s in all_stats:
        rows.append([
            s.experiment_name[:25],
            f"{s.total_reads:,}",
            f"{s.total_bases / 1e9:.2f}",
            f"{s.mean_length:,.0f}",
            f"{s.median_length:,.0f}",
            f"{s.n50:,}",
            f"{s.max_length:,}",
            f"{s.pct_gt_10kb:.1f}"
        ])
    
    # Calculate column widths
    widths = [max(len(str(row[i])) for row in [headers] + rows) for i in range(len(headers))]
    
    # Build table
    sep = '+' + '+'.join('-' * (w + 2) for w in widths) + '+'
    header_row = '|' + '|'.join(f' {headers[i]:<{widths[i]}} ' for i in range(len(headers))) + '|'
    
    lines = [sep, header_row, sep]
    for row in rows:
        line = '|' + '|'.join(f' {row[i]:<{widths[i]}} ' for i in range(len(row))) + '|'
        lines.append(line)
    lines.append(sep)
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='ONT Read Length Distribution Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single experiment analysis
  ont_readlen.py /path/to/run --json stats.json --plot dist.png
  
  # Multiple experiments comparison
  ont_readlen.py /path/to/run1 /path/to/run2 /path/to/run3 \\
    --json comparison.json --plot comparison.png --plot-type overlay
  
  # From specific file
  ont_readlen.py sequencing_summary.txt --json stats.json
  
  # With max reads limit (for quick preview)
  ont_readlen.py /path/to/run --max-reads 100000 --plot preview.png
  
  # Pattern B integration (via ont-experiments)
  ont_experiments.py run readlen exp-abc123 --json stats.json --plot dist.png
"""
    )
    
    parser.add_argument('inputs', nargs='+', help='Run directories or data files')
    parser.add_argument('--json', '-j', help='Output JSON file')
    parser.add_argument('--plot', '-p', help='Output plot file (PNG/PDF)')
    parser.add_argument('--plot-type', choices=['histogram', 'overlay', 'violin', 'bar'],
                        default='histogram', help='Plot type for multi-experiment')
    parser.add_argument('--csv', help='Output CSV summary')
    parser.add_argument('--max-reads', type=int, help='Maximum reads to process')
    parser.add_argument('--max-length', type=int, default=50000,
                        help='Maximum length for histogram x-axis')
    parser.add_argument('--log-scale', action='store_true', help='Use log scale for y-axis')
    parser.add_argument('--normalize', action='store_true', 
                        help='Normalize histogram to percentages')
    parser.add_argument('--source-type', choices=['sequencing_summary', 'bam', 'fastq', 'pod5'],
                        help='Force specific source type')
    parser.add_argument('--title', help='Custom plot title')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress console output')
    parser.add_argument('--version', action='version', version='ont_readlen.py 2.1')
    
    args = parser.parse_args()
    
    all_stats = []
    
    for i, input_path in enumerate(args.inputs):
        path = Path(input_path)
        
        if not path.exists():
            print(f"Warning: {input_path} not found, skipping", file=sys.stderr)
            continue
        
        try:
            if not args.quiet:
                print(f"Processing: {path.name}...", file=sys.stderr)
            
            stats = analyze_experiment(
                path,
                experiment_id=f"exp-{i:03d}",
                max_reads=args.max_reads,
                source_type=args.source_type
            )
            all_stats.append(stats)
            
        except Exception as e:
            print(f"Error processing {input_path}: {e}", file=sys.stderr)
            continue
    
    if not all_stats:
        print("Error: No valid experiments found", file=sys.stderr)
        sys.exit(1)
    
    # Print summary table
    if not args.quiet:
        print("\n" + generate_summary_table(all_stats))
    
    # Output JSON
    if args.json:
        output = {
            "version": "2.1",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "experiments_count": len(all_stats),
            "experiments": [s.to_dict() for s in all_stats]
        }
        with open(args.json, 'w') as f:
            json.dump(output, f, indent=2)
        if not args.quiet:
            print(f"\nJSON saved: {args.json}")
    
    # Output CSV
    if args.csv:
        import csv
        with open(args.csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'experiment_id', 'experiment_name', 'total_reads', 'total_bases',
                'mean_length', 'median_length', 'n50', 'n90', 'max_length',
                'pct_gt_1kb', 'pct_gt_5kb', 'pct_gt_10kb'
            ])
            writer.writeheader()
            for s in all_stats:
                writer.writerow({
                    'experiment_id': s.experiment_id,
                    'experiment_name': s.experiment_name,
                    'total_reads': s.total_reads,
                    'total_bases': s.total_bases,
                    'mean_length': s.mean_length,
                    'median_length': s.median_length,
                    'n50': s.n50,
                    'n90': s.n90,
                    'max_length': s.max_length,
                    'pct_gt_1kb': s.pct_gt_1kb,
                    'pct_gt_5kb': s.pct_gt_5kb,
                    'pct_gt_10kb': s.pct_gt_10kb,
                })
        if not args.quiet:
            print(f"CSV saved: {args.csv}")
    
    # Generate plot
    if args.plot:
        if not HAS_MATPLOTLIB:
            print("Warning: matplotlib not available, skipping plot", file=sys.stderr)
        else:
            plot_path = Path(args.plot)
            
            if len(all_stats) == 1:
                plot_single_distribution(
                    all_stats[0], plot_path,
                    title=args.title,
                    log_scale=args.log_scale,
                    max_length=args.max_length
                )
            else:
                plot_type = args.plot_type if args.plot_type != 'histogram' else 'overlay'
                plot_multi_comparison(
                    all_stats, plot_path,
                    title=args.title or "Read Length Distribution Comparison",
                    plot_type=plot_type,
                    max_length=args.max_length,
                    normalize=args.normalize
                )
            
            if not args.quiet:
                print(f"Plot saved: {args.plot}")
    
    # Print single-experiment stats to stdout if no output specified
    if not args.json and not args.csv and not args.plot:
        for stats in all_stats:
            print(json.dumps(stats.to_dict(), indent=2))


if __name__ == '__main__':
    main()
