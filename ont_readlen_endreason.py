#!/usr/bin/env python3
"""
ONT Read Length + End Reason Combined Analysis v1.0

Publication-quality analysis combining read length distributions with end reason
classification. Generates overlaid semi-transparent histograms by end reason class
and cross-experiment summary plots.

Key Features:
- Semi-transparent size distributions colored by end reason class
- Cross-experiment: end reason frequency vs mean read size
- Combined statistics (N50 by end reason, size distribution per class)
- Pattern B integration with ont-experiments

Data Sources:
- sequencing_summary.txt (has both length and end_reason columns)
- POD5 files (metadata contains both)

Author: Claude (Anthropic) + Human collaboration
"""

import argparse
import json
import sys
import os
import gzip
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, NamedTuple
from dataclasses import dataclass, asdict, field
from collections import Counter, defaultdict
import hashlib

# Optional imports
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import pod5
    HAS_POD5 = True
except ImportError:
    HAS_POD5 = False

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter, AutoMinorLocator
    import matplotlib.patches as mpatches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


# ============================================================================
# Color Schemes for End Reason Classes
# ============================================================================

END_REASON_COLORS = {
    'signal_positive': '#2563eb',           # Blue - normal completion
    'unblock_mux_change': '#dc2626',        # Red - adaptive sampling rejection
    'data_service_unblock_mux_change': '#ea580c',  # Orange - basecall rejection
    'mux_change': '#9333ea',                # Purple - pore mux change
    'signal_negative': '#6b7280',           # Gray - signal lost
    'unknown': '#94a3b8',                   # Slate - unknown/other
}

END_REASON_LABELS = {
    'signal_positive': 'Signal Positive (Normal)',
    'unblock_mux_change': 'Unblock MUX (Adaptive)',
    'data_service_unblock_mux_change': 'Data Service Unblock',
    'mux_change': 'MUX Change',
    'signal_negative': 'Signal Negative',
    'unknown': 'Unknown/Other',
}

# Canonical ordering for legends
END_REASON_ORDER = [
    'signal_positive',
    'unblock_mux_change', 
    'data_service_unblock_mux_change',
    'mux_change',
    'signal_negative',
    'unknown',
]


# ============================================================================
# Data Structures
# ============================================================================

class ReadInfo(NamedTuple):
    """Single read with length and end reason"""
    length: int
    end_reason: str


@dataclass
class EndReasonStats:
    """Statistics for a single end reason class"""
    end_reason: str
    count: int
    pct: float
    total_bases: int
    mean_length: float
    median_length: float
    n50: int
    min_length: int
    max_length: int
    length_counts: Dict[int, int] = field(default_factory=dict)


@dataclass
class CombinedStats:
    """Combined read length + end reason statistics"""
    experiment_id: str
    experiment_name: str
    source_file: str
    total_reads: int
    total_bases: int
    
    # Overall length stats
    mean_length: float
    median_length: float
    n50: int
    n90: int
    max_length: int
    
    # End reason breakdown
    end_reason_stats: Dict[str, EndReasonStats] = field(default_factory=dict)
    
    # Quality assessment
    quality_status: str = "OK"
    signal_positive_pct: float = 0.0
    
    timestamp: str = ""
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict"""
        d = asdict(self)
        # Convert nested dataclass
        d['end_reason_stats'] = {
            k: asdict(v) for k, v in self.end_reason_stats.items()
        }
        # Compress length_counts in each end_reason_stats
        for er_name, er_data in d['end_reason_stats'].items():
            if 'length_counts' in er_data and er_data['length_counts']:
                er_data['length_counts_compressed'] = list(er_data['length_counts'].items())
                del er_data['length_counts']
        return d


# ============================================================================
# Helper Functions
# ============================================================================

def calculate_nx(lengths: List[int], x: float = 50) -> Tuple[int, int]:
    """Calculate NX value (e.g., N50) and LX count"""
    if not lengths:
        return 0, 0
    sorted_desc = sorted(lengths, reverse=True)
    total = sum(sorted_desc)
    target = total * (x / 100.0)
    cumsum = 0
    for i, length in enumerate(sorted_desc):
        cumsum += length
        if cumsum >= target:
            return length, i + 1
    return sorted_desc[-1], len(sorted_desc)


def normalize_end_reason(raw_reason: str) -> str:
    """Normalize end reason strings to canonical form"""
    if not raw_reason:
        return 'unknown'
    
    reason = raw_reason.lower().strip()
    
    # Map variants to canonical names
    if 'signal_positive' in reason or reason == 'normal':
        return 'signal_positive'
    elif 'data_service_unblock' in reason:
        return 'data_service_unblock_mux_change'
    elif 'unblock_mux' in reason or 'unblock' in reason:
        return 'unblock_mux_change'
    elif 'mux_change' in reason:
        return 'mux_change'
    elif 'signal_negative' in reason:
        return 'signal_negative'
    else:
        return 'unknown'


def compute_end_reason_stats(reads: List[ReadInfo], end_reason: str) -> EndReasonStats:
    """Compute statistics for reads of a specific end reason"""
    lengths = [r.length for r in reads if r.end_reason == end_reason]
    
    if not lengths:
        return EndReasonStats(
            end_reason=end_reason,
            count=0, pct=0.0, total_bases=0,
            mean_length=0.0, median_length=0.0, n50=0,
            min_length=0, max_length=0,
            length_counts={}
        )
    
    length_counts = Counter(lengths)
    total_bases = sum(lengths)
    
    if HAS_NUMPY:
        arr = np.array(lengths)
        mean_len = float(np.mean(arr))
        median_len = float(np.median(arr))
    else:
        sorted_lens = sorted(lengths)
        n = len(sorted_lens)
        mean_len = sum(lengths) / n
        median_len = sorted_lens[n // 2]
    
    n50, _ = calculate_nx(lengths, 50)
    
    return EndReasonStats(
        end_reason=end_reason,
        count=len(lengths),
        pct=0.0,  # Will be computed later with total
        total_bases=total_bases,
        mean_length=round(mean_len, 1),
        median_length=round(median_len, 1),
        n50=n50,
        min_length=min(lengths),
        max_length=max(lengths),
        length_counts=dict(length_counts)
    )


def compute_combined_stats(reads: List[ReadInfo], experiment_id: str,
                          experiment_name: str, source_file: str) -> CombinedStats:
    """Compute comprehensive combined statistics"""
    
    if not reads:
        raise ValueError("No reads found")
    
    total_reads = len(reads)
    all_lengths = [r.length for r in reads]
    total_bases = sum(all_lengths)
    
    # Overall stats
    if HAS_NUMPY:
        arr = np.array(all_lengths)
        mean_len = float(np.mean(arr))
        median_len = float(np.median(arr))
    else:
        sorted_lens = sorted(all_lengths)
        n = len(sorted_lens)
        mean_len = sum(all_lengths) / n
        median_len = sorted_lens[n // 2]
    
    n50, _ = calculate_nx(all_lengths, 50)
    n90, _ = calculate_nx(all_lengths, 90)
    
    # Per end-reason stats
    end_reasons_found = set(r.end_reason for r in reads)
    end_reason_stats = {}
    
    for er in end_reasons_found:
        er_stats = compute_end_reason_stats(reads, er)
        er_stats.pct = round(100 * er_stats.count / total_reads, 2)
        end_reason_stats[er] = er_stats
    
    # Quality assessment
    signal_positive_pct = end_reason_stats.get('signal_positive', EndReasonStats(
        'signal_positive', 0, 0.0, 0, 0.0, 0.0, 0, 0, 0, {}
    )).pct
    
    if signal_positive_pct >= 75:
        quality_status = "OK"
    elif signal_positive_pct >= 50:
        quality_status = "CHECK"
    else:
        quality_status = "FAIL"
    
    return CombinedStats(
        experiment_id=experiment_id,
        experiment_name=experiment_name,
        source_file=source_file,
        total_reads=total_reads,
        total_bases=total_bases,
        mean_length=round(mean_len, 1),
        median_length=round(median_len, 1),
        n50=n50,
        n90=n90,
        max_length=max(all_lengths),
        end_reason_stats=end_reason_stats,
        quality_status=quality_status,
        signal_positive_pct=signal_positive_pct,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


# ============================================================================
# Data Source Parsers
# ============================================================================

def parse_sequencing_summary(filepath: Path, max_reads: int = None) -> List[ReadInfo]:
    """Parse sequencing_summary.txt for both length and end_reason"""
    reads = []
    
    opener = gzip.open if str(filepath).endswith('.gz') else open
    
    with opener(filepath, 'rt') as f:
        header = f.readline().strip().split('\t')
        
        # Find columns
        len_col = None
        er_col = None
        
        for i, col in enumerate(header):
            col_lower = col.lower()
            if col_lower in ('sequence_length_template', 'sequence_length', 'read_length'):
                len_col = i
            if col_lower in ('end_reason', 'end_reason_tag'):
                er_col = i
        
        if len_col is None:
            raise ValueError(f"Could not find length column in {filepath}")
        
        # end_reason column is optional - default to signal_positive if missing
        has_end_reason = er_col is not None
        
        for line in f:
            if max_reads and len(reads) >= max_reads:
                break
            
            parts = line.strip().split('\t')
            if len(parts) <= len_col:
                continue
            
            try:
                length = int(float(parts[len_col]))
                if length <= 0:
                    continue
                
                if has_end_reason and len(parts) > er_col:
                    end_reason = normalize_end_reason(parts[er_col])
                else:
                    end_reason = 'signal_positive'
                
                reads.append(ReadInfo(length=length, end_reason=end_reason))
                
            except (ValueError, IndexError):
                continue
    
    return reads


def parse_pod5(filepath: Path, max_reads: int = None) -> List[ReadInfo]:
    """Parse POD5 file for estimated lengths and end reasons"""
    if not HAS_POD5:
        raise ImportError("pod5 required: pip install pod5")
    
    reads = []
    
    with pod5.Reader(filepath) as reader:
        for read in reader.reads():
            if max_reads and len(reads) >= max_reads:
                break
            
            # Estimate bases from signal
            sample_rate = read.run_info.sample_rate
            signal_len = len(read.signal)
            estimated_bases = int(signal_len / sample_rate * 450)
            
            # Get end reason from read metadata
            try:
                end_reason_raw = read.end_reason.name if hasattr(read, 'end_reason') else 'unknown'
            except:
                end_reason_raw = 'unknown'
            
            end_reason = normalize_end_reason(end_reason_raw)
            reads.append(ReadInfo(length=estimated_bases, end_reason=end_reason))
    
    return reads


def find_data_source(run_path: Path) -> Tuple[Path, str]:
    """Find the best data source in a run directory"""
    
    # Prefer sequencing_summary (has both columns reliably)
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
    
    # POD5 as fallback
    for pattern in ['*.pod5', 'pod5_pass/*.pod5', 'pod5/*.pod5']:
        matches = list(run_path.glob(pattern))
        if matches:
            return matches[0], 'pod5'
    
    raise FileNotFoundError(f"No suitable data source found in {run_path}")


def extract_reads(source_path: Path, source_type: str = None,
                  max_reads: int = None) -> List[ReadInfo]:
    """Extract read info from various file types"""
    
    if source_type is None:
        suffix = source_path.suffix.lower()
        name = source_path.name.lower()
        
        if 'sequencing_summary' in name:
            source_type = 'sequencing_summary'
        elif suffix == '.pod5':
            source_type = 'pod5'
        else:
            raise ValueError(f"Cannot determine file type: {source_path}")
    
    parsers = {
        'sequencing_summary': parse_sequencing_summary,
        'pod5': parse_pod5,
    }
    
    parser = parsers.get(source_type)
    if not parser:
        raise ValueError(f"Unknown source type: {source_type}")
    
    return parser(source_path, max_reads)


def analyze_experiment(run_path: Path, experiment_id: str = None,
                      experiment_name: str = None, max_reads: int = None,
                      source_type: str = None) -> CombinedStats:
    """Analyze a single experiment for combined stats"""
    
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
    
    reads = extract_reads(source_path, source_type, max_reads)
    stats = compute_combined_stats(reads, experiment_id, experiment_name, str(source_path))
    
    return stats


# ============================================================================
# PLOTTING - Semi-Transparent End Reason Distributions
# ============================================================================

def format_bp(x, pos):
    """Format bp values for axis labels"""
    if x >= 1e6:
        return f'{x/1e6:.1f}M'
    elif x >= 1e3:
        return f'{x/1e3:.0f}k'
    else:
        return f'{int(x)}'


def plot_by_end_reason(
    stats: CombinedStats,
    output_path: Path,
    title: str = None,
    dpi: int = 300,
    figsize: Tuple[float, float] = (14, 10),
    xlim: Tuple[int, int] = None,
    log_y: bool = False,
    alpha: float = 0.4,
    normalize: bool = True,
    show_legend: bool = True,
    show_stats_box: bool = True,
):
    """
    Plot semi-transparent read length distributions colored by end reason.
    
    Args:
        stats: CombinedStats object with end_reason_stats
        output_path: Output PNG path  
        title: Plot title
        dpi: Resolution (300 for publication)
        figsize: Figure size in inches
        xlim: X-axis limits
        log_y: Logarithmic y-axis
        alpha: Transparency (0.4 default for good overlap visibility)
        normalize: Normalize to percentage (allows comparison across classes)
        show_legend: Show legend
        show_stats_box: Show summary statistics box
    """
    
    if not HAS_MATPLOTLIB or not HAS_NUMPY:
        raise ImportError("matplotlib and numpy required for plotting")
    
    # Publication style
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
        'font.size': 10,
        'axes.linewidth': 1.2,
        'axes.labelsize': 12,
        'axes.titlesize': 14,
        'xtick.major.width': 1.2,
        'ytick.major.width': 1.2,
        'legend.fontsize': 9,
        'figure.dpi': dpi,
    })
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Determine global x-range
    all_lengths = []
    for er_stats in stats.end_reason_stats.values():
        all_lengths.extend(er_stats.length_counts.keys())
    
    if not all_lengths:
        raise ValueError("No length data available for plotting")
    
    if xlim:
        x_min, x_max = xlim
    else:
        x_min = 0
        x_max = min(max(all_lengths), 50000)  # Cap at 50kb for visibility
    
    # Create histogram bins
    bin_width = max(100, (x_max - x_min) // 200)  # ~200 bins
    bins = np.arange(x_min, x_max + bin_width, bin_width)
    
    legend_handles = []
    
    # Plot each end reason in canonical order
    for er_name in END_REASON_ORDER:
        if er_name not in stats.end_reason_stats:
            continue
        
        er_stats = stats.end_reason_stats[er_name]
        if er_stats.count == 0:
            continue
        
        # Expand length_counts to array
        lengths = []
        for length, count in er_stats.length_counts.items():
            lengths.extend([length] * count)
        
        if not lengths:
            continue
        
        color = END_REASON_COLORS.get(er_name, '#94a3b8')
        label = END_REASON_LABELS.get(er_name, er_name)
        
        # Compute histogram
        weights = None
        if normalize:
            weights = np.ones_like(lengths) * 100.0 / len(lengths)
        
        counts, bin_edges, patches = ax.hist(
            lengths, bins=bins,
            alpha=alpha, color=color, 
            edgecolor=color, linewidth=0.5,
            weights=weights,
            label=f"{label} (n={er_stats.count:,}, {er_stats.pct:.1f}%)"
        )
        
        # Add to legend
        legend_handles.append(mpatches.Patch(
            color=color, alpha=alpha,
            label=f"{label} (n={er_stats.count:,}, {er_stats.pct:.1f}%)"
        ))
    
    # Axis formatting
    ax.set_xlabel('Read Length (bp)', fontweight='bold')
    ylabel = 'Percentage of Reads in Class (%)' if normalize else 'Read Count'
    ax.set_ylabel(ylabel, fontweight='bold')
    ax.xaxis.set_major_formatter(FuncFormatter(format_bp))
    ax.xaxis.set_minor_locator(AutoMinorLocator(5))
    
    if log_y:
        ax.set_yscale('log')
    
    # Grid
    ax.grid(True, which='major', alpha=0.3, linestyle='-')
    ax.grid(True, which='minor', alpha=0.15, linestyle='-')
    
    # Title
    if title is None:
        title = f"Read Length Distribution by End Reason: {stats.experiment_name}"
    ax.set_title(title, fontweight='bold', pad=15)
    
    # Legend
    if show_legend:
        ax.legend(handles=legend_handles, loc='upper right', 
                 framealpha=0.95, edgecolor='gray')
    
    # Stats box
    if show_stats_box:
        stats_text = (
            f"Total Reads: {stats.total_reads:,}\n"
            f"Signal Positive: {stats.signal_positive_pct:.1f}%\n"
            f"Quality: {stats.quality_status}\n"
            f"Overall N50: {stats.n50:,} bp\n"
            f"Overall Mean: {stats.mean_length:,.0f} bp"
        )
        props = dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='gray')
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=9,
               verticalalignment='top', fontfamily='monospace', bbox=props)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()


def plot_multi_experiment_summary(
    all_stats: List[CombinedStats],
    output_path: Path,
    title: str = None,
    dpi: int = 300,
    figsize: Tuple[float, float] = (16, 12),
):
    """
    Generate cross-experiment summary showing end reason frequency vs mean read size.
    
    Creates a 2x2 panel:
    - Top left: End reason frequency by experiment (stacked bar)
    - Top right: Mean read length by experiment (colored by quality status)
    - Bottom left: End reason frequency vs mean length (scatter)
    - Bottom right: N50 by end reason class (grouped bar)
    """
    
    if not HAS_MATPLOTLIB or not HAS_NUMPY:
        raise ImportError("matplotlib and numpy required for plotting")
    
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.size': 10,
        'axes.labelsize': 11,
        'axes.titlesize': 12,
        'figure.dpi': dpi,
    })
    
    fig, axes = plt.subplots(2, 2, figsize=figsize)
    
    exp_names = [s.experiment_name for s in all_stats]
    n_exp = len(all_stats)
    
    # ===== Top Left: End Reason Frequency Stacked Bar =====
    ax1 = axes[0, 0]
    
    bottom = np.zeros(n_exp)
    for er_name in END_REASON_ORDER:
        pcts = []
        for stats in all_stats:
            er_stats = stats.end_reason_stats.get(er_name)
            pcts.append(er_stats.pct if er_stats else 0.0)
        
        if sum(pcts) > 0:
            color = END_REASON_COLORS.get(er_name, '#94a3b8')
            label = END_REASON_LABELS.get(er_name, er_name)
            ax1.bar(range(n_exp), pcts, bottom=bottom, color=color, 
                   label=label, edgecolor='white', linewidth=0.5)
            bottom += np.array(pcts)
    
    ax1.set_xticks(range(n_exp))
    ax1.set_xticklabels(exp_names, rotation=45, ha='right')
    ax1.set_ylabel('Percentage (%)')
    ax1.set_title('End Reason Breakdown by Experiment', fontweight='bold')
    ax1.legend(loc='upper right', fontsize=8)
    ax1.set_ylim(0, 100)
    
    # ===== Top Right: Mean Read Length by Experiment =====
    ax2 = axes[0, 1]
    
    mean_lengths = [s.mean_length for s in all_stats]
    quality_colors = []
    for s in all_stats:
        if s.quality_status == "OK":
            quality_colors.append('#16a34a')  # Green
        elif s.quality_status == "CHECK":
            quality_colors.append('#eab308')  # Yellow
        else:
            quality_colors.append('#dc2626')  # Red
    
    bars = ax2.bar(range(n_exp), mean_lengths, color=quality_colors, edgecolor='black')
    ax2.set_xticks(range(n_exp))
    ax2.set_xticklabels(exp_names, rotation=45, ha='right')
    ax2.set_ylabel('Mean Read Length (bp)')
    ax2.set_title('Mean Read Length by Experiment\n(color = QC status)', fontweight='bold')
    ax2.yaxis.set_major_formatter(FuncFormatter(format_bp))
    
    # Add value labels
    for i, (bar, val) in enumerate(zip(bars, mean_lengths)):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 100,
                f'{val:,.0f}', ha='center', va='bottom', fontsize=8)
    
    # ===== Bottom Left: Signal Positive % vs Mean Length (Scatter) =====
    ax3 = axes[1, 0]
    
    sp_pcts = [s.signal_positive_pct for s in all_stats]
    
    scatter = ax3.scatter(mean_lengths, sp_pcts, c=quality_colors, 
                         s=100, edgecolors='black', linewidth=1)
    
    # Add experiment labels
    for i, (x, y, name) in enumerate(zip(mean_lengths, sp_pcts, exp_names)):
        ax3.annotate(name, (x, y), textcoords="offset points", 
                    xytext=(5, 5), fontsize=8)
    
    ax3.set_xlabel('Mean Read Length (bp)')
    ax3.set_ylabel('Signal Positive (%)')
    ax3.set_title('End Reason Quality vs Read Length', fontweight='bold')
    ax3.xaxis.set_major_formatter(FuncFormatter(format_bp))
    
    # Add quality threshold lines
    ax3.axhline(y=75, color='green', linestyle='--', alpha=0.5, label='OK threshold')
    ax3.axhline(y=50, color='red', linestyle='--', alpha=0.5, label='FAIL threshold')
    ax3.legend(loc='lower right', fontsize=8)
    
    # ===== Bottom Right: N50 by End Reason (Grouped Bar) =====
    ax4 = axes[1, 1]
    
    x = np.arange(n_exp)
    width = 0.15
    offset = 0
    
    for er_name in END_REASON_ORDER:
        n50s = []
        for stats in all_stats:
            er_stats = stats.end_reason_stats.get(er_name)
            n50s.append(er_stats.n50 if er_stats and er_stats.count > 0 else 0)
        
        if sum(n50s) > 0:
            color = END_REASON_COLORS.get(er_name, '#94a3b8')
            label = END_REASON_LABELS.get(er_name, er_name)
            ax4.bar(x + offset * width, n50s, width, color=color, label=label)
            offset += 1
    
    ax4.set_xticks(x + width * (offset - 1) / 2)
    ax4.set_xticklabels(exp_names, rotation=45, ha='right')
    ax4.set_ylabel('N50 (bp)')
    ax4.set_title('N50 by End Reason Class', fontweight='bold')
    ax4.yaxis.set_major_formatter(FuncFormatter(format_bp))
    ax4.legend(loc='upper right', fontsize=7)
    
    # Overall title
    if title is None:
        title = "Cross-Experiment End Reason + Read Length Summary"
    fig.suptitle(title, fontsize=14, fontweight='bold', y=1.02)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()


def plot_detailed_4panel(
    stats: CombinedStats,
    output_path: Path,
    title: str = None,
    dpi: int = 300,
    figsize: Tuple[float, float] = (16, 12),
):
    """
    Generate detailed 4-panel analysis for single experiment.
    
    Panels:
    - Top left: Overlaid distributions (linear scale)
    - Top right: Overlaid distributions (log scale)
    - Bottom left: End reason pie chart
    - Bottom right: N50 comparison bar chart
    """
    
    if not HAS_MATPLOTLIB or not HAS_NUMPY:
        raise ImportError("matplotlib and numpy required")
    
    fig, axes = plt.subplots(2, 2, figsize=figsize)
    
    # ===== Top Left: Linear Scale Distributions =====
    ax1 = axes[0, 0]
    
    x_max = min(stats.max_length, 50000)
    bins = np.arange(0, x_max, 250)
    
    for er_name in END_REASON_ORDER:
        if er_name not in stats.end_reason_stats:
            continue
        er_stats = stats.end_reason_stats[er_name]
        if er_stats.count == 0:
            continue
        
        lengths = []
        for length, count in er_stats.length_counts.items():
            lengths.extend([length] * count)
        
        if not lengths:
            continue
        
        color = END_REASON_COLORS.get(er_name, '#94a3b8')
        label = END_REASON_LABELS.get(er_name, er_name)
        
        ax1.hist(lengths, bins=bins, alpha=0.4, color=color, 
                label=f"{label} ({er_stats.pct:.1f}%)")
    
    ax1.set_xlabel('Read Length (bp)')
    ax1.set_ylabel('Read Count')
    ax1.set_title('Read Length by End Reason (Linear)', fontweight='bold')
    ax1.xaxis.set_major_formatter(FuncFormatter(format_bp))
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)
    
    # ===== Top Right: Log Scale =====
    ax2 = axes[0, 1]
    
    for er_name in END_REASON_ORDER:
        if er_name not in stats.end_reason_stats:
            continue
        er_stats = stats.end_reason_stats[er_name]
        if er_stats.count == 0:
            continue
        
        lengths = []
        for length, count in er_stats.length_counts.items():
            lengths.extend([length] * count)
        
        if not lengths:
            continue
        
        color = END_REASON_COLORS.get(er_name, '#94a3b8')
        label = END_REASON_LABELS.get(er_name, er_name)
        
        ax2.hist(lengths, bins=bins, alpha=0.4, color=color,
                label=f"{label} ({er_stats.pct:.1f}%)")
    
    ax2.set_yscale('log')
    ax2.set_xlabel('Read Length (bp)')
    ax2.set_ylabel('Read Count (log)')
    ax2.set_title('Read Length by End Reason (Log Scale)', fontweight='bold')
    ax2.xaxis.set_major_formatter(FuncFormatter(format_bp))
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)
    
    # ===== Bottom Left: Pie Chart =====
    ax3 = axes[1, 0]
    
    labels = []
    sizes = []
    colors = []
    
    for er_name in END_REASON_ORDER:
        if er_name not in stats.end_reason_stats:
            continue
        er_stats = stats.end_reason_stats[er_name]
        if er_stats.count == 0:
            continue
        
        labels.append(END_REASON_LABELS.get(er_name, er_name))
        sizes.append(er_stats.pct)
        colors.append(END_REASON_COLORS.get(er_name, '#94a3b8'))
    
    wedges, texts, autotexts = ax3.pie(
        sizes, labels=labels, colors=colors, autopct='%1.1f%%',
        startangle=90, pctdistance=0.75,
        wedgeprops=dict(width=0.5, edgecolor='white')
    )
    ax3.set_title('End Reason Distribution', fontweight='bold')
    
    # ===== Bottom Right: N50 Bar Chart =====
    ax4 = axes[1, 1]
    
    er_names = []
    n50s = []
    bar_colors = []
    
    for er_name in END_REASON_ORDER:
        if er_name not in stats.end_reason_stats:
            continue
        er_stats = stats.end_reason_stats[er_name]
        if er_stats.count == 0:
            continue
        
        er_names.append(END_REASON_LABELS.get(er_name, er_name))
        n50s.append(er_stats.n50)
        bar_colors.append(END_REASON_COLORS.get(er_name, '#94a3b8'))
    
    bars = ax4.barh(range(len(er_names)), n50s, color=bar_colors, edgecolor='black')
    ax4.set_yticks(range(len(er_names)))
    ax4.set_yticklabels(er_names)
    ax4.set_xlabel('N50 (bp)')
    ax4.set_title('N50 by End Reason Class', fontweight='bold')
    ax4.xaxis.set_major_formatter(FuncFormatter(format_bp))
    
    # Add value labels
    for bar, val in zip(bars, n50s):
        ax4.text(val + 100, bar.get_y() + bar.get_height()/2,
                f'{val:,}', va='center', fontsize=9)
    
    ax4.grid(True, alpha=0.3, axis='x')
    
    # Overall title
    if title is None:
        title = f"Detailed Analysis: {stats.experiment_name}"
    fig.suptitle(title, fontsize=14, fontweight='bold', y=1.02)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()


# ============================================================================
# Summary Table Generation
# ============================================================================

def generate_summary_table(all_stats: List[CombinedStats]) -> str:
    """Generate text summary table"""
    
    lines = []
    lines.append("=" * 100)
    lines.append("COMBINED READ LENGTH + END REASON ANALYSIS")
    lines.append("=" * 100)
    
    header = (
        f"{'Experiment':<20} {'Reads':>12} {'Mean':>10} {'N50':>10} "
        f"{'SP%':>8} {'Unblk%':>8} {'Status':>8}"
    )
    lines.append(header)
    lines.append("-" * 100)
    
    for stats in all_stats:
        unblock_pct = stats.end_reason_stats.get('unblock_mux_change', 
            EndReasonStats('', 0, 0.0, 0, 0, 0, 0, 0, 0, {})).pct
        
        row = (
            f"{stats.experiment_name[:20]:<20} "
            f"{stats.total_reads:>12,} "
            f"{stats.mean_length:>10,.0f} "
            f"{stats.n50:>10,} "
            f"{stats.signal_positive_pct:>8.1f} "
            f"{unblock_pct:>8.1f} "
            f"{stats.quality_status:>8}"
        )
        lines.append(row)
    
    lines.append("=" * 100)
    lines.append(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    
    return "\n".join(lines)


# ============================================================================
# Main CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Combined ONT read length + end reason analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single experiment - all plots
  python3 ont_readlen_endreason.py /path/to/run --plot-by-endreason dist.png
  
  # Multi-experiment cross-comparison
  python3 ont_readlen_endreason.py exp1/ exp2/ exp3/ --plot-summary summary.png
  
  # Detailed 4-panel analysis
  python3 ont_readlen_endreason.py /path/to/run --plot-detailed detailed.png
  
  # All outputs
  python3 ont_readlen_endreason.py /path/to/run --json stats.json \\
      --plot-by-endreason dist.png --plot-detailed detailed.png
  
  # Pattern B integration (via ont-experiments)
  ont_experiments.py run readlen_endreason exp-abc123 --json stats.json
"""
    )
    
    parser.add_argument('inputs', nargs='+', help='Run directories or data files')
    parser.add_argument('--json', '-j', help='Output JSON file')
    parser.add_argument('--csv', help='Output CSV summary')
    
    # Plotting options
    parser.add_argument('--plot-by-endreason', '-p', 
                       help='Output plot: distributions by end reason (PNG)')
    parser.add_argument('--plot-summary', '-s',
                       help='Output plot: multi-experiment summary (PNG)')
    parser.add_argument('--plot-detailed', '-d',
                       help='Output plot: detailed 4-panel analysis (PNG)')
    
    # Options
    parser.add_argument('--dpi', type=int, default=300,
                       help='Plot resolution (default: 300)')
    parser.add_argument('--max-reads', type=int, help='Limit reads for quick preview')
    parser.add_argument('--source-type', choices=['sequencing_summary', 'pod5'],
                       help='Force specific source type')
    parser.add_argument('--title', help='Custom plot title')
    parser.add_argument('--alpha', type=float, default=0.4,
                       help='Transparency for overlaid histograms (0-1)')
    parser.add_argument('--log-y', action='store_true', help='Log y-axis')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress output')
    parser.add_argument('--version', action='version', 
                       version='ont_readlen_endreason.py 1.0')
    
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
            "version": "1.0",
            "analysis_type": "readlen_endreason_combined",
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
                'experiment_id', 'experiment_name', 'total_reads', 
                'mean_length', 'n50', 'signal_positive_pct', 
                'unblock_mux_pct', 'quality_status'
            ])
            writer.writeheader()
            for s in all_stats:
                unblock_pct = s.end_reason_stats.get('unblock_mux_change',
                    EndReasonStats('', 0, 0.0, 0, 0, 0, 0, 0, 0, {})).pct
                writer.writerow({
                    'experiment_id': s.experiment_id,
                    'experiment_name': s.experiment_name,
                    'total_reads': s.total_reads,
                    'mean_length': s.mean_length,
                    'n50': s.n50,
                    'signal_positive_pct': s.signal_positive_pct,
                    'unblock_mux_pct': unblock_pct,
                    'quality_status': s.quality_status,
                })
        if not args.quiet:
            print(f"CSV saved: {args.csv}")
    
    # Generate plots
    if HAS_MATPLOTLIB:
        # By end reason distribution plot
        if args.plot_by_endreason:
            for stats in all_stats:
                if len(all_stats) > 1:
                    out_path = Path(args.plot_by_endreason)
                    out_path = out_path.parent / f"{out_path.stem}_{stats.experiment_id}{out_path.suffix}"
                else:
                    out_path = Path(args.plot_by_endreason)
                
                plot_by_end_reason(
                    stats, out_path,
                    title=args.title,
                    dpi=args.dpi,
                    alpha=args.alpha,
                    log_y=args.log_y,
                )
                if not args.quiet:
                    print(f"Plot saved: {out_path}")
        
        # Multi-experiment summary
        if args.plot_summary and len(all_stats) >= 1:
            plot_multi_experiment_summary(
                all_stats, Path(args.plot_summary),
                title=args.title,
                dpi=args.dpi,
            )
            if not args.quiet:
                print(f"Summary plot saved: {args.plot_summary}")
        
        # Detailed 4-panel
        if args.plot_detailed:
            for stats in all_stats:
                if len(all_stats) > 1:
                    out_path = Path(args.plot_detailed)
                    out_path = out_path.parent / f"{out_path.stem}_{stats.experiment_id}{out_path.suffix}"
                else:
                    out_path = Path(args.plot_detailed)
                
                plot_detailed_4panel(
                    stats, out_path,
                    title=args.title,
                    dpi=args.dpi,
                )
                if not args.quiet:
                    print(f"Detailed plot saved: {out_path}")
    else:
        if args.plot_by_endreason or args.plot_summary or args.plot_detailed:
            print("Warning: matplotlib not available, skipping plots", file=sys.stderr)
    
    # Print stats to stdout if no outputs specified
    if not args.json and not args.csv and not args.plot_by_endreason \
       and not args.plot_summary and not args.plot_detailed:
        for stats in all_stats:
            d = stats.to_dict()
            # Remove large data
            for er_data in d.get('end_reason_stats', {}).values():
                er_data.pop('length_counts_compressed', None)
            print(json.dumps(d, indent=2))


if __name__ == '__main__':
    main()
