#!/usr/bin/env python3
"""
ONT Read Length Distribution Analysis v2.0

High-resolution, publication-quality read length distribution analysis
for Oxford Nanopore sequencing data.

Key Features:
- BP-level resolution plotting (no binning loss)
- High-resolution PNG output (300+ DPI)
- Zoomable regions for detailed peak analysis
- Multi-experiment comparison
- Customizable styling and color schemes

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
from typing import Dict, List, Optional, Tuple, Any, Iterator, Union
from dataclasses import dataclass, asdict, field
from collections import Counter, defaultdict
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
    from matplotlib.ticker import FuncFormatter, MaxNLocator, AutoMinorLocator
    from matplotlib.colors import LinearSegmentedColormap
    import matplotlib.patches as mpatches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


# ============================================================================
# Publication-Quality Color Schemes
# ============================================================================

COLOR_SCHEMES = {
    'default': ['#2563eb', '#dc2626', '#16a34a', '#9333ea', '#ea580c', '#0891b2'],
    'viridis': ['#440154', '#414487', '#2a788e', '#22a884', '#7ad151', '#fde725'],
    'nature': ['#E64B35', '#4DBBD5', '#00A087', '#3C5488', '#F39B7F', '#8491B4'],
    'science': ['#3B4992', '#EE0000', '#008B45', '#631879', '#008280', '#BB0021'],
    'nejm': ['#BC3C29', '#0072B5', '#E18727', '#20854E', '#7876B1', '#6F99AD'],
    'lancet': ['#00468B', '#ED0000', '#42B540', '#0099B4', '#925E9F', '#FDAF91'],
}


@dataclass
class ReadLengthStats:
    """Statistics for a read length distribution with raw data support"""
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
    q1_length: float
    q3_length: float
    reads_gt_1kb: int
    reads_gt_5kb: int
    reads_gt_10kb: int
    reads_gt_20kb: int
    reads_gt_50kb: int
    reads_gt_100kb: int
    pct_gt_1kb: float
    pct_gt_5kb: float
    pct_gt_10kb: float
    # Raw data for high-res plotting
    length_counts: Dict[int, int] = field(default_factory=dict)  # bp -> count
    histogram_bins: List[int] = field(default_factory=list)
    histogram_counts: List[int] = field(default_factory=list)
    timestamp: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dict, compressing length_counts for JSON"""
        d = asdict(self)
        # Compress length_counts to list of tuples for efficient storage
        if self.length_counts:
            d['length_counts_compressed'] = list(self.length_counts.items())
            del d['length_counts']
        return d
    
    @classmethod
    def from_dict(cls, d: dict) -> 'ReadLengthStats':
        """Reconstruct from dict"""
        if 'length_counts_compressed' in d:
            d['length_counts'] = dict(d.pop('length_counts_compressed'))
        return cls(**d)


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
                  store_raw: bool = True) -> ReadLengthStats:
    """
    Compute comprehensive statistics from read lengths
    
    Args:
        lengths: List of read lengths
        experiment_id: Unique experiment identifier
        experiment_name: Human-readable name
        source_file: Source file path
        store_raw: Whether to store bp-level counts for high-res plotting
    """
    
    if not lengths:
        raise ValueError("No reads found")
    
    # Count frequencies at bp level for high-res plotting
    length_counts = Counter(lengths) if store_raw else {}
    
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
    
    # Build coarse histogram for backwards compatibility
    bin_size = 1000
    max_bin = 100000
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
        length_counts=dict(length_counts),
        histogram_bins=bins,
        histogram_counts=counts,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


# ============================================================================
# Data Source Parsers
# ============================================================================

def parse_sequencing_summary(filepath: Path, max_reads: int = None) -> List[int]:
    """Parse sequencing_summary.txt for read lengths"""
    lengths = []
    
    opener = gzip.open if str(filepath).endswith('.gz') else open
    
    with opener(filepath, 'rt') as f:
        header = f.readline().strip().split('\t')
        
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
            if line_num % 4 == 2:
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
            sample_rate = read.run_info.sample_rate
            signal_len = len(read.signal)
            estimated_bases = int(signal_len / sample_rate * 450)
            lengths.append(estimated_bases)
    
    return lengths


def find_data_source(run_path: Path) -> Tuple[Path, str]:
    """Find the best data source in a run directory"""
    
    for pattern in ['sequencing_summary*.txt', 'sequencing_summary*.txt.gz']:
        matches = list(run_path.glob(pattern))
        if matches:
            return matches[0], 'sequencing_summary'
    
    for subdir in ['', 'basecalling', 'pass', 'fail']:
        check_path = run_path / subdir if subdir else run_path
        for pattern in ['sequencing_summary*.txt', 'sequencing_summary*.txt.gz']:
            matches = list(check_path.glob(pattern))
            if matches:
                return matches[0], 'sequencing_summary'
    
    for pattern in ['*.bam', 'pass/*.bam', 'basecalling/*.bam']:
        matches = list(run_path.glob(pattern))
        if matches:
            return matches[0], 'bam'
    
    for pattern in ['*.fastq', '*.fastq.gz', '*.fq', '*.fq.gz', 
                    'pass/*.fastq.gz', 'fastq_pass/*.fastq.gz']:
        matches = list(run_path.glob(pattern))
        if matches:
            return matches[0], 'fastq'
    
    for pattern in ['*.pod5', 'pod5_pass/*.pod5', 'pod5/*.pod5']:
        matches = list(run_path.glob(pattern))
        if matches:
            return matches[0], 'pod5'
    
    raise FileNotFoundError(f"No suitable data source found in {run_path}")


def extract_lengths(source_path: Path, source_type: str = None, 
                    max_reads: int = None) -> List[int]:
    """Extract read lengths from various file types"""
    
    if source_type is None:
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
                       source_type: str = None, store_raw: bool = True) -> ReadLengthStats:
    """Analyze read lengths for a single experiment"""
    
    run_path = Path(run_path)
    
    if run_path.is_file():
        source_path = run_path
    else:
        source_path, detected_type = find_data_source(run_path)
        if source_type is None:
            source_type = detected_type
    
    if experiment_id is None:
        experiment_id = hashlib.sha256(str(run_path).encode()).hexdigest()[:8]
    
    if experiment_name is None:
        experiment_name = run_path.parent.name if run_path.is_file() else run_path.name
    
    lengths = extract_lengths(source_path, source_type, max_reads)
    stats = compute_stats(lengths, experiment_id, experiment_name, str(source_path), store_raw)
    
    return stats


# ============================================================================
# HIGH-RESOLUTION PLOTTING
# ============================================================================

def format_bp(x, pos):
    """Format bp values for axis labels"""
    if x >= 1e6:
        return f'{x/1e6:.1f}M'
    elif x >= 1e3:
        return f'{x/1e3:.0f}k'
    else:
        return f'{int(x)}'


def plot_high_resolution(
    stats: ReadLengthStats,
    output_path: Path,
    title: str = None,
    dpi: int = 300,
    figsize: Tuple[float, float] = (12, 8),
    xlim: Tuple[int, int] = None,
    log_y: bool = False,
    color_scheme: str = 'default',
    smoothing: int = 0,
    show_stats: bool = True,
    show_markers: bool = True,
    style: str = 'publication',
    transparent: bool = False,
):
    """
    Generate high-resolution, publication-quality read length distribution plot.
    
    Args:
        stats: ReadLengthStats object with bp-level length_counts
        output_path: Output PNG path
        title: Plot title (auto-generated if None)
        dpi: Output resolution (default 300 for publication quality)
        figsize: Figure size in inches
        xlim: X-axis limits as (min_bp, max_bp), None for auto
        log_y: Use logarithmic y-axis
        color_scheme: Color scheme name from COLOR_SCHEMES
        smoothing: Rolling average window (0 for no smoothing, keeps bp resolution)
        show_stats: Show statistics box
        show_markers: Show mean/median/N50 vertical lines
        style: Plot style ('publication', 'presentation', 'minimal')
        transparent: Transparent background
    """
    
    if not HAS_MATPLOTLIB:
        raise ImportError("matplotlib required for plotting: pip install matplotlib")
    
    if not HAS_NUMPY:
        raise ImportError("numpy required for high-res plotting: pip install numpy")
    
    if not stats.length_counts:
        raise ValueError("No bp-level data available. Re-run analysis with store_raw=True")
    
    # Get color scheme
    colors = COLOR_SCHEMES.get(color_scheme, COLOR_SCHEMES['default'])
    main_color = colors[0]
    
    # Apply style settings
    if style == 'publication':
        plt.rcParams.update({
            'font.family': 'sans-serif',
            'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
            'font.size': 10,
            'axes.linewidth': 1.2,
            'axes.labelsize': 12,
            'axes.titlesize': 14,
            'xtick.major.width': 1.2,
            'ytick.major.width': 1.2,
            'xtick.minor.width': 0.8,
            'ytick.minor.width': 0.8,
            'legend.fontsize': 9,
            'figure.dpi': dpi,
        })
    elif style == 'presentation':
        plt.rcParams.update({
            'font.size': 14,
            'axes.linewidth': 2,
            'axes.labelsize': 16,
            'axes.titlesize': 18,
            'xtick.major.width': 2,
            'ytick.major.width': 2,
            'legend.fontsize': 12,
            'figure.dpi': dpi,
        })
    
    # Create figure
    fig, ax = plt.subplots(figsize=figsize)
    
    # Extract bp-level data
    bp_lengths = np.array(sorted(stats.length_counts.keys()))
    bp_counts = np.array([stats.length_counts[bp] for bp in bp_lengths])
    
    # Apply x-axis limits
    if xlim:
        mask = (bp_lengths >= xlim[0]) & (bp_lengths <= xlim[1])
        bp_lengths = bp_lengths[mask]
        bp_counts = bp_counts[mask]
    
    # Apply smoothing if requested (but preserve peaks)
    if smoothing > 0:
        kernel = np.ones(smoothing) / smoothing
        bp_counts_smooth = np.convolve(bp_counts, kernel, mode='same')
    else:
        bp_counts_smooth = bp_counts
    
    # Calculate density for area plot
    # Use fill_between for publication-quality rendering
    ax.fill_between(bp_lengths, bp_counts_smooth, alpha=0.4, color=main_color,
                    linewidth=0, label='_nolegend_')
    ax.plot(bp_lengths, bp_counts_smooth, color=main_color, linewidth=1.0,
            label=f'{stats.experiment_name}')
    
    # Add statistical markers
    if show_markers:
        line_alpha = 0.8
        line_width = 1.5
        
        # N50 (most prominent)
        ax.axvline(stats.n50, color='#dc2626', linestyle='-', linewidth=line_width+0.5, 
                   alpha=line_alpha, label=f'N50: {stats.n50:,} bp', zorder=5)
        
        # Mean
        ax.axvline(stats.mean_length, color='#16a34a', linestyle='--', linewidth=line_width,
                   alpha=line_alpha, label=f'Mean: {stats.mean_length:,.0f} bp', zorder=5)
        
        # Median
        ax.axvline(stats.median_length, color='#9333ea', linestyle=':', linewidth=line_width,
                   alpha=line_alpha, label=f'Median: {stats.median_length:,.0f} bp', zorder=5)
    
    # Y-axis scaling
    if log_y:
        ax.set_yscale('log')
        ax.set_ylabel('Read Count (log scale)', fontweight='bold')
    else:
        ax.set_ylabel('Read Count', fontweight='bold')
    
    # X-axis formatting
    ax.set_xlabel('Read Length (bp)', fontweight='bold')
    ax.xaxis.set_major_formatter(FuncFormatter(format_bp))
    ax.xaxis.set_minor_locator(AutoMinorLocator(5))
    ax.yaxis.set_minor_locator(AutoMinorLocator(5))
    
    # Grid
    ax.grid(True, which='major', alpha=0.3, linestyle='-', linewidth=0.8)
    ax.grid(True, which='minor', alpha=0.15, linestyle='-', linewidth=0.4)
    
    # Title
    if title is None:
        title = f"Read Length Distribution: {stats.experiment_name}"
    ax.set_title(title, fontweight='bold', pad=15)
    
    # Legend
    if show_markers:
        legend = ax.legend(loc='upper right', framealpha=0.95, edgecolor='gray',
                          fancybox=True, shadow=False)
    
    # Statistics box
    if show_stats:
        stats_text = (
            f"Total Reads: {stats.total_reads:,}\n"
            f"Total Bases: {stats.total_bases / 1e9:.2f} Gb\n"
            f"Std Dev: {stats.std_length:,.0f} bp\n"
            f"Min: {stats.min_length:,} bp\n"
            f"Max: {stats.max_length:,} bp\n"
            f"Q1: {stats.q1_length:,.0f} bp\n"
            f"Q3: {stats.q3_length:,.0f} bp\n"
            f">10kb: {stats.pct_gt_10kb:.1f}%"
        )
        
        props = dict(boxstyle='round,pad=0.5', facecolor='white', 
                    edgecolor='gray', alpha=0.9)
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                fontsize=9, verticalalignment='top', horizontalalignment='left',
                bbox=props, family='monospace')
    
    # Tight layout and save
    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', 
                transparent=transparent, facecolor='white' if not transparent else 'none')
    plt.close()
    
    # Reset rcParams
    plt.rcParams.update(plt.rcParamsDefault)


def plot_high_resolution_multi(
    all_stats: List[ReadLengthStats],
    output_path: Path,
    title: str = "Read Length Distribution Comparison",
    dpi: int = 300,
    figsize: Tuple[float, float] = (14, 9),
    xlim: Tuple[int, int] = None,
    log_y: bool = False,
    color_scheme: str = 'default',
    smoothing: int = 0,
    normalize: bool = True,
    show_legend: bool = True,
    style: str = 'publication',
    alpha: float = 0.5,
):
    """
    Generate high-resolution multi-experiment comparison plot.
    
    Args:
        all_stats: List of ReadLengthStats objects
        output_path: Output PNG path
        title: Plot title
        dpi: Output resolution
        figsize: Figure size
        xlim: X-axis limits
        log_y: Logarithmic y-axis
        color_scheme: Color scheme name
        smoothing: Rolling average window
        normalize: Normalize to percentage/density
        show_legend: Show legend
        style: Plot style
        alpha: Fill alpha for overlapping distributions
    """
    
    if not HAS_MATPLOTLIB or not HAS_NUMPY:
        raise ImportError("matplotlib and numpy required")
    
    colors = COLOR_SCHEMES.get(color_scheme, COLOR_SCHEMES['default'])
    
    # Style settings
    if style == 'publication':
        plt.rcParams.update({
            'font.family': 'sans-serif',
            'font.size': 10,
            'axes.linewidth': 1.2,
            'axes.labelsize': 12,
            'axes.titlesize': 14,
        })
    
    fig, ax = plt.subplots(figsize=figsize)
    
    for i, stats in enumerate(all_stats):
        color = colors[i % len(colors)]
        
        if not stats.length_counts:
            # Fall back to histogram bins
            bp_lengths = np.array(stats.histogram_bins)
            bp_counts = np.array(stats.histogram_counts).astype(float)
        else:
            bp_lengths = np.array(sorted(stats.length_counts.keys()))
            bp_counts = np.array([stats.length_counts[bp] for bp in bp_lengths]).astype(float)
        
        # Apply xlim
        if xlim:
            mask = (bp_lengths >= xlim[0]) & (bp_lengths <= xlim[1])
            bp_lengths = bp_lengths[mask]
            bp_counts = bp_counts[mask]
        
        # Normalize
        if normalize and bp_counts.sum() > 0:
            bp_counts = bp_counts / bp_counts.sum() * 100
        
        # Smoothing
        if smoothing > 0:
            kernel = np.ones(smoothing) / smoothing
            bp_counts = np.convolve(bp_counts, kernel, mode='same')
        
        # Plot
        label = f"{stats.experiment_name} (N50={stats.n50:,})"
        ax.fill_between(bp_lengths, bp_counts, alpha=alpha, color=color, linewidth=0)
        ax.plot(bp_lengths, bp_counts, color=color, linewidth=1.5, label=label)
    
    # Formatting
    ylabel = 'Percentage of Reads' if normalize else 'Read Count'
    if log_y:
        ax.set_yscale('log')
        ylabel += ' (log scale)'
    
    ax.set_xlabel('Read Length (bp)', fontweight='bold')
    ax.set_ylabel(ylabel, fontweight='bold')
    ax.set_title(title, fontweight='bold', pad=15)
    ax.xaxis.set_major_formatter(FuncFormatter(format_bp))
    ax.xaxis.set_minor_locator(AutoMinorLocator(5))
    ax.grid(True, which='major', alpha=0.3)
    ax.grid(True, which='minor', alpha=0.15)
    
    if show_legend:
        ax.legend(loc='upper right', framealpha=0.95, fontsize=9)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()
    plt.rcParams.update(plt.rcParamsDefault)


def plot_zoom_region(
    stats: ReadLengthStats,
    output_path: Path,
    center: int,
    window: int = 1000,
    title: str = None,
    dpi: int = 300,
    figsize: Tuple[float, float] = (10, 6),
    show_individual_bp: bool = True,
    color_scheme: str = 'default',
):
    """
    Generate zoomed plot around a specific region at bp resolution.
    
    Args:
        stats: ReadLengthStats with bp-level data
        output_path: Output path
        center: Center of zoom window (bp)
        window: Window size (total width in bp)
        title: Plot title
        dpi: Resolution
        figsize: Figure size
        show_individual_bp: Show individual bp as bars vs line
        color_scheme: Color scheme
    """
    
    if not HAS_MATPLOTLIB or not HAS_NUMPY:
        raise ImportError("matplotlib and numpy required")
    
    if not stats.length_counts:
        raise ValueError("No bp-level data available")
    
    colors = COLOR_SCHEMES.get(color_scheme, COLOR_SCHEMES['default'])
    main_color = colors[0]
    
    # Calculate bounds
    half_window = window // 2
    x_min = center - half_window
    x_max = center + half_window
    
    # Extract data in window
    bp_lengths = []
    bp_counts = []
    for bp in range(x_min, x_max + 1):
        bp_lengths.append(bp)
        bp_counts.append(stats.length_counts.get(bp, 0))
    
    bp_lengths = np.array(bp_lengths)
    bp_counts = np.array(bp_counts)
    
    fig, ax = plt.subplots(figsize=figsize)
    
    if show_individual_bp and window <= 500:
        # Bar plot for true bp resolution
        ax.bar(bp_lengths, bp_counts, width=0.8, color=main_color, 
               edgecolor='darkblue', alpha=0.7, linewidth=0.3)
    else:
        # Line plot for wider windows
        ax.fill_between(bp_lengths, bp_counts, alpha=0.4, color=main_color)
        ax.plot(bp_lengths, bp_counts, color=main_color, linewidth=1.0)
    
    ax.set_xlabel('Read Length (bp)', fontweight='bold')
    ax.set_ylabel('Read Count', fontweight='bold')
    
    if title is None:
        title = f"Zoomed View: {center-half_window:,} - {center+half_window:,} bp"
    ax.set_title(title, fontweight='bold')
    
    ax.set_xlim(x_min, x_max)
    ax.grid(True, alpha=0.3)
    
    # Show actual bp values on x-axis for small windows
    if window <= 100:
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=20))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()


# ============================================================================
# Legacy Plot Functions (for compatibility)
# ============================================================================

def plot_single_distribution(stats: ReadLengthStats, output_path: Path,
                             title: str = None, log_scale: bool = False,
                             max_length: int = None):
    """Generate histogram plot - redirects to high-res version"""
    xlim = (0, max_length) if max_length else None
    plot_high_resolution(stats, output_path, title=title, log_y=log_scale, xlim=xlim)


def plot_multi_comparison(all_stats: List[ReadLengthStats], output_path: Path,
                          title: str = "Read Length Distribution Comparison",
                          plot_type: str = "overlay", max_length: int = None,
                          normalize: bool = True):
    """Generate comparison plot - enhanced version"""
    
    if plot_type == "overlay":
        xlim = (0, max_length) if max_length else None
        plot_high_resolution_multi(all_stats, output_path, title=title, 
                                   xlim=xlim, normalize=normalize)
    elif plot_type == "violin":
        _plot_violin(all_stats, output_path, title)
    elif plot_type == "bar":
        _plot_bar_metrics(all_stats, output_path, title)
    else:
        plot_high_resolution_multi(all_stats, output_path, title=title)


def _plot_violin(all_stats: List[ReadLengthStats], output_path: Path, title: str):
    """Generate violin/box plot comparison"""
    if not HAS_MATPLOTLIB or not HAS_NUMPY:
        raise ImportError("matplotlib and numpy required")
    
    colors = COLOR_SCHEMES['default']
    fig, ax = plt.subplots(figsize=(max(8, len(all_stats) * 1.5), 7))
    
    positions = list(range(len(all_stats)))
    labels = [s.experiment_name for s in all_stats]
    
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
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()


def _plot_bar_metrics(all_stats: List[ReadLengthStats], output_path: Path, title: str):
    """Generate bar chart comparing key metrics"""
    if not HAS_MATPLOTLIB or not HAS_NUMPY:
        raise ImportError("matplotlib and numpy required")
    
    colors = COLOR_SCHEMES['default']
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    names = [s.experiment_name[:20] for s in all_stats]
    x = np.arange(len(names))
    width = 0.6
    
    metrics = [
        (axes[0, 0], [s.n50 for s in all_stats], 'N50 (bp)', 'N50 Read Length'),
        (axes[0, 1], [s.mean_length for s in all_stats], 'Mean Length (bp)', 'Mean Read Length'),
        (axes[1, 0], [s.total_reads / 1e6 for s in all_stats], 'Total Reads (millions)', 'Total Read Count'),
        (axes[1, 1], [s.pct_gt_10kb for s in all_stats], 'Percentage', 'Reads >10kb (%)'),
    ]
    
    for ax, values, ylabel, ax_title in metrics:
        bars = ax.bar(x, values, width, color=[colors[i % len(colors)] for i in range(len(all_stats))])
        ax.set_ylabel(ylabel)
        ax.set_title(ax_title)
        ax.set_xticks(x)
        ax.set_xticklabels(names, rotation=45, ha='right')
        ax.grid(True, alpha=0.3, axis='y')
    
    plt.suptitle(title, fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()


# ============================================================================
# Summary Table
# ============================================================================

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
    
    widths = [max(len(str(row[i])) for row in [headers] + rows) for i in range(len(headers))]
    
    sep = '+' + '+'.join('-' * (w + 2) for w in widths) + '+'
    header_row = '|' + '|'.join(f' {headers[i]:<{widths[i]}} ' for i in range(len(headers))) + '|'
    
    lines = [sep, header_row, sep]
    for row in rows:
        line = '|' + '|'.join(f' {row[i]:<{widths[i]}} ' for i in range(len(row))) + '|'
        lines.append(line)
    lines.append(sep)
    
    return '\n'.join(lines)


# ============================================================================
# Main CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='ONT Read Length Distribution Analysis v2.0 - High Resolution',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single experiment with high-res plot (default)
  ont_readlen.py /path/to/run --plot dist.png
  
  # Specify resolution and figure size
  ont_readlen.py /path/to/run --plot dist.png --dpi 600 --figsize 14 10
  
  # Zoom into a specific region (bp resolution)
  ont_readlen.py /path/to/run --plot zoom.png --xlim 5000 10000
  
  # Generate zoomed plot around a peak
  ont_readlen.py /path/to/run --zoom 8500 --zoom-window 500 --plot peak.png
  
  # Multi-experiment comparison
  ont_readlen.py exp1/ exp2/ exp3/ --plot comparison.png
  
  # Different color schemes
  ont_readlen.py /path/to/run --plot dist.png --colors nature
  
  # Log scale with custom title
  ont_readlen.py /path/to/run --plot dist.png --log-y --title "My Experiment"
  
  # Pattern B integration (via ont-experiments)
  ont_experiments.py run readlen exp-abc123 --plot dist.png --json stats.json
"""
    )
    
    parser.add_argument('inputs', nargs='+', help='Run directories or data files')
    parser.add_argument('--json', '-j', help='Output JSON file')
    parser.add_argument('--plot', '-p', help='Output plot file (PNG)')
    parser.add_argument('--csv', help='Output CSV summary')
    
    # High-resolution options
    parser.add_argument('--dpi', type=int, default=300,
                        help='Output resolution (default: 300 for publication quality)')
    parser.add_argument('--figsize', nargs=2, type=float, default=[12, 8],
                        metavar=('WIDTH', 'HEIGHT'), help='Figure size in inches')
    parser.add_argument('--xlim', nargs=2, type=int, metavar=('MIN', 'MAX'),
                        help='X-axis limits in bp for zoomed view')
    
    # Zoom functionality
    parser.add_argument('--zoom', type=int, metavar='CENTER_BP',
                        help='Generate zoomed plot centered at this bp position')
    parser.add_argument('--zoom-window', type=int, default=1000,
                        help='Zoom window width in bp (default: 1000)')
    
    # Plot styling
    parser.add_argument('--colors', choices=list(COLOR_SCHEMES.keys()), default='default',
                        help='Color scheme')
    parser.add_argument('--style', choices=['publication', 'presentation', 'minimal'],
                        default='publication', help='Plot style preset')
    parser.add_argument('--log-y', action='store_true', help='Logarithmic y-axis')
    parser.add_argument('--smoothing', type=int, default=0,
                        help='Smoothing window (0 for none, preserves bp resolution)')
    parser.add_argument('--no-stats', action='store_true', help='Hide statistics box')
    parser.add_argument('--no-markers', action='store_true', help='Hide mean/median/N50 lines')
    parser.add_argument('--transparent', action='store_true', help='Transparent background')
    
    # Multi-experiment options
    parser.add_argument('--plot-type', choices=['overlay', 'violin', 'bar'],
                        default='overlay', help='Comparison plot type')
    parser.add_argument('--normalize', action='store_true', 
                        help='Normalize distributions to percentage')
    
    # Data options
    parser.add_argument('--max-reads', type=int, help='Maximum reads to process')
    parser.add_argument('--source-type', choices=['sequencing_summary', 'bam', 'fastq', 'pod5'],
                        help='Force specific source type')
    parser.add_argument('--title', help='Custom plot title')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress console output')
    parser.add_argument('--version', action='version', version='ont_readlen.py 2.0')
    
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
                source_type=args.source_type,
                store_raw=True  # Always store raw for high-res plotting
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
            "version": "2.0",
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
            figsize = tuple(args.figsize)
            xlim = tuple(args.xlim) if args.xlim else None
            
            # Handle zoom mode
            if args.zoom:
                if len(all_stats) > 1:
                    print("Warning: --zoom only works with single experiment, using first", 
                          file=sys.stderr)
                plot_zoom_region(
                    all_stats[0], plot_path,
                    center=args.zoom,
                    window=args.zoom_window,
                    title=args.title,
                    dpi=args.dpi,
                    figsize=figsize,
                    color_scheme=args.colors,
                )
            elif len(all_stats) == 1:
                plot_high_resolution(
                    all_stats[0], plot_path,
                    title=args.title,
                    dpi=args.dpi,
                    figsize=figsize,
                    xlim=xlim,
                    log_y=args.log_y,
                    color_scheme=args.colors,
                    smoothing=args.smoothing,
                    show_stats=not args.no_stats,
                    show_markers=not args.no_markers,
                    style=args.style,
                    transparent=args.transparent,
                )
            else:
                if args.plot_type == 'overlay':
                    plot_high_resolution_multi(
                        all_stats, plot_path,
                        title=args.title or "Read Length Distribution Comparison",
                        dpi=args.dpi,
                        figsize=figsize,
                        xlim=xlim,
                        log_y=args.log_y,
                        color_scheme=args.colors,
                        smoothing=args.smoothing,
                        normalize=args.normalize,
                        style=args.style,
                    )
                else:
                    plot_multi_comparison(
                        all_stats, plot_path,
                        title=args.title or "Read Length Distribution Comparison",
                        plot_type=args.plot_type,
                        normalize=args.normalize,
                    )
            
            if not args.quiet:
                print(f"Plot saved: {args.plot} ({args.dpi} DPI)")
    
    # Print single-experiment stats to stdout if no output specified
    if not args.json and not args.csv and not args.plot:
        for stats in all_stats:
            d = stats.to_dict()
            # Remove large data for console output
            d.pop('length_counts_compressed', None)
            d.pop('histogram_bins', None)
            d.pop('histogram_counts', None)
            print(json.dumps(d, indent=2))


if __name__ == '__main__':
    main()
