#!/usr/bin/env python3
"""
ONT End Reason QC Analysis v2.0

High-resolution KDE visualization with multi-zoom analysis, concatemer detection,
and publication-quality plots for Oxford Nanopore read termination patterns.

Key improvements over v1:
- 10bp resolution KDE instead of coarse histograms
- Multi-zoom panels (short reads, target peak, concatemers, long reads)
- Automatic concatemer detection with 2x/3x target marking
- Cross-experiment comparison overlays
- Quality grading based on empirical SMA-seq thresholds

Author: Claude (Anthropic) + Human collaboration
"""

import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

try:
    import numpy as np
    from scipy.ndimage import gaussian_filter1d
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    import numpy as np

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# ============================================================================
# Constants and Color Schemes
# ============================================================================

COLORS = {
    'signal_positive': {'fill': '#27ae60', 'line': '#1e8449', 'alpha': 0.35},
    'unblock': {'fill': '#e74c3c', 'line': '#c0392b', 'alpha': 0.35},
    'mux_change': {'fill': '#9b59b6', 'line': '#8e44ad', 'alpha': 0.35},
    'signal_negative': {'fill': '#7f8c8d', 'line': '#5d6d7e', 'alpha': 0.35},
}

# Quality thresholds based on SMA-seq analysis
QUALITY_THRESHOLDS = {
    'signal_positive_pct': {'excellent': 95, 'good': 85, 'warning': 75},
    'unblock_pct': {'excellent': 2, 'good': 5, 'warning': 10},
    'short_read_pct': {'excellent': 1, 'good': 5, 'warning': 15},
}

# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class EndReasonData:
    """Statistics for a single end reason category"""
    name: str
    count: int = 0
    pct: float = 0.0
    lengths: List[int] = field(default_factory=list)
    n50: int = 0
    median: int = 0
    mean: float = 0.0
    peak_center: int = 0
    peak_sigma: float = 0.0
    bins_10bp: Dict[int, int] = field(default_factory=dict)
    
@dataclass
class ExperimentStats:
    """Complete statistics for one experiment"""
    name: str
    source_file: str
    total_reads: int = 0
    quality_grade: str = "?"
    signal_positive: EndReasonData = None
    unblock: EndReasonData = None
    other: EndReasonData = None
    short_read_pct: float = 0.0
    adapter_dimer_pct: float = 0.0
    concatemer_pct: float = 0.0
    detected_target: int = 0

# ============================================================================
# Analysis Functions
# ============================================================================

def calculate_n50(lengths: List[int]) -> int:
    """Calculate N50 from length list"""
    if not lengths:
        return 0
    sorted_desc = sorted(lengths, reverse=True)
    total = sum(sorted_desc)
    target = total / 2
    cumsum = 0
    for length in sorted_desc:
        cumsum += length
        if cumsum >= target:
            return length
    return sorted_desc[-1]

def normalize_end_reason(raw: str) -> str:
    """Map end reason to canonical category"""
    if not raw:
        return 'other'
    r = raw.lower().strip()
    if 'signal_positive' in r:
        return 'signal_positive'
    elif 'unblock' in r:
        return 'unblock'
    elif 'mux_change' in r:
        return 'mux_change'
    elif 'signal_negative' in r:
        return 'signal_negative'
    return 'other'

def lengths_to_kde(lengths: List[int], resolution: int = 10, 
                   max_len: int = 15000, sigma: float = 3.0) -> Tuple[np.ndarray, np.ndarray]:
    """Convert lengths to smoothed KDE density curve"""
    if not lengths:
        x = np.arange(0, max_len, resolution)
        return x, np.zeros_like(x, dtype=float)
    
    # Bin at resolution
    bins = {}
    for length in lengths:
        b = (length // resolution) * resolution
        if b < max_len:
            bins[b] = bins.get(b, 0) + 1
    
    # Create fine grid
    x = np.arange(0, max_len, resolution)
    y = np.zeros_like(x, dtype=float)
    
    for b, c in bins.items():
        idx = b // resolution
        if 0 <= idx < len(y):
            y[idx] = c
    
    # Smooth with Gaussian
    if HAS_SCIPY:
        y = gaussian_filter1d(y, sigma=sigma)
    
    # Normalize to percentage
    if y.sum() > 0:
        y = y / y.max() * 100
    
    return x, y

def detect_peak(x: np.ndarray, y: np.ndarray) -> Tuple[int, float]:
    """Find main peak center and estimate sigma"""
    if y.max() == 0:
        return 0, 0.0
    peak_idx = np.argmax(y)
    peak_center = int(x[peak_idx])
    
    # Estimate sigma from half-max width
    half_max = y.max() / 2
    above_half = y > half_max
    if above_half.any():
        indices = np.where(above_half)[0]
        width_bp = (indices[-1] - indices[0]) * (x[1] - x[0])
        sigma = width_bp / 2.355  # FWHM to sigma
    else:
        sigma = 100.0
    
    return peak_center, float(sigma)

def analyze_experiment(data_file: Path, max_reads: Optional[int] = None) -> ExperimentStats:
    """Analyze a single experiment's sequencing summary"""
    
    stats = ExperimentStats(
        name=data_file.parent.name if data_file.is_file() else data_file.name,
        source_file=str(data_file),
        signal_positive=EndReasonData(name='signal_positive'),
        unblock=EndReasonData(name='unblock'),
        other=EndReasonData(name='other'),
    )
    
    # Find sequencing summary file
    if data_file.is_dir():
        candidates = list(data_file.rglob('sequencing_summary*.txt'))
        if not candidates:
            raise FileNotFoundError(f"No sequencing_summary.txt found in {data_file}")
        data_file = candidates[0]
    
    # Parse file
    sp_lengths = []
    ub_lengths = []
    other_lengths = []
    
    with open(data_file, 'r') as f:
        header = f.readline().strip().split('\t')
        
        # Find column indices
        len_col = None
        er_col = None
        for i, col in enumerate(header):
            if 'sequence_length' in col.lower():
                len_col = i
            if 'end_reason' in col.lower():
                er_col = i
        
        if len_col is None:
            raise ValueError("Could not find sequence_length column")
        
        count = 0
        for line in f:
            if max_reads and count >= max_reads:
                break
            
            fields = line.strip().split('\t')
            if len(fields) <= max(len_col, er_col or 0):
                continue
            
            try:
                length = int(fields[len_col])
                end_reason = normalize_end_reason(fields[er_col] if er_col else '')
                
                if end_reason == 'signal_positive':
                    sp_lengths.append(length)
                elif end_reason == 'unblock':
                    ub_lengths.append(length)
                else:
                    other_lengths.append(length)
                
                count += 1
            except (ValueError, IndexError):
                continue
    
    # Compute statistics
    all_lengths = sp_lengths + ub_lengths + other_lengths
    stats.total_reads = len(all_lengths)
    
    if not all_lengths:
        return stats
    
    # Signal positive stats
    if sp_lengths:
        stats.signal_positive.count = len(sp_lengths)
        stats.signal_positive.pct = len(sp_lengths) / stats.total_reads * 100
        stats.signal_positive.lengths = sp_lengths
        stats.signal_positive.n50 = calculate_n50(sp_lengths)
        stats.signal_positive.median = int(np.median(sp_lengths))
        stats.signal_positive.mean = float(np.mean(sp_lengths))
        x, y = lengths_to_kde(sp_lengths)
        stats.signal_positive.peak_center, stats.signal_positive.peak_sigma = detect_peak(x, y)
    
    # Unblock stats
    if ub_lengths:
        stats.unblock.count = len(ub_lengths)
        stats.unblock.pct = len(ub_lengths) / stats.total_reads * 100
        stats.unblock.lengths = ub_lengths
        stats.unblock.n50 = calculate_n50(ub_lengths)
        stats.unblock.median = int(np.median(ub_lengths))
        stats.unblock.mean = float(np.mean(ub_lengths))
    
    # Quality metrics
    short_reads = sum(1 for l in all_lengths if l < 200)
    stats.short_read_pct = short_reads / stats.total_reads * 100
    
    adapter_dimers = sum(1 for l in all_lengths if l < 100)
    stats.adapter_dimer_pct = adapter_dimers / stats.total_reads * 100
    
    # Detect target size from signal_positive peak
    if stats.signal_positive.peak_center > 0:
        stats.detected_target = stats.signal_positive.peak_center
        target = stats.detected_target
        concatemers = sum(1 for l in all_lengths if l > target * 1.8)
        stats.concatemer_pct = concatemers / stats.total_reads * 100
    
    # Quality grade
    sp_pct = stats.signal_positive.pct
    ub_pct = stats.unblock.pct
    sr_pct = stats.short_read_pct
    
    if sp_pct >= 95 and ub_pct <= 2 and sr_pct <= 1:
        stats.quality_grade = "A"
    elif sp_pct >= 85 and ub_pct <= 5 and sr_pct <= 5:
        stats.quality_grade = "B"
    elif sp_pct >= 75 and ub_pct <= 10 and sr_pct <= 15:
        stats.quality_grade = "C"
    else:
        stats.quality_grade = "D"
    
    return stats

# ============================================================================
# Plotting Functions
# ============================================================================

def plot_kde_comparison(stats: ExperimentStats, output: Path, dpi: int = 300):
    """Main KDE plot: signal_positive vs unblock overlay"""
    
    fig, ax = plt.subplots(figsize=(14, 8), dpi=dpi)
    
    # Signal positive KDE
    x_sp, y_sp = lengths_to_kde(stats.signal_positive.lengths, max_len=12000)
    ax.fill_between(x_sp, y_sp, alpha=COLORS['signal_positive']['alpha'],
                    color=COLORS['signal_positive']['fill'])
    ax.plot(x_sp, y_sp, linewidth=2.5, color=COLORS['signal_positive']['line'],
            label=f"signal_positive (n={stats.signal_positive.count:,}, N50={stats.signal_positive.n50:,})")
    
    # Unblock KDE
    x_ub, y_ub = lengths_to_kde(stats.unblock.lengths, max_len=12000)
    ax.fill_between(x_ub, y_ub, alpha=COLORS['unblock']['alpha'],
                    color=COLORS['unblock']['fill'])
    ax.plot(x_ub, y_ub, linewidth=2.5, color=COLORS['unblock']['line'],
            label=f"unblock (n={stats.unblock.count:,}, N50={stats.unblock.n50:,})")
    
    # Target marker
    if stats.detected_target > 0:
        ax.axvline(x=stats.detected_target, color='black', linestyle='--', 
                   alpha=0.6, linewidth=2, label=f"Target: {stats.detected_target:,} bp")
    
    ax.set_xlim(0, 10000)
    ax.set_xlabel('Read Length (bp)', fontsize=14)
    ax.set_ylabel('Density (%)', fontsize=14)
    ax.set_title(f"End Reason Analysis: {stats.name}\n"
                 f"Quality Grade: {stats.quality_grade} | "
                 f"Signal+: {stats.signal_positive.pct:.1f}% | "
                 f"Unblock: {stats.unblock.pct:.1f}%",
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=11)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()

def plot_multizoom(stats: ExperimentStats, output: Path, dpi: int = 300):
    """4-panel multi-zoom analysis"""
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12), dpi=dpi)
    
    zoom_configs = [
        (0, 500, 'Short Reads (0-500bp)', 'Adapter dimers & contamination'),
        (1500, 3500, 'Target Peak (1.5-3.5kb)', 'Size selection efficiency'),
        (4000, 8000, 'Concatemers (4-8kb)', '2x target region'),
        (8000, 15000, 'Long Reads (8-15kb)', '3x+ fragments'),
    ]
    
    for ax, (xmin, xmax, title, subtitle) in zip(axes.flat, zoom_configs):
        # Signal positive
        x_sp, y_sp = lengths_to_kde(stats.signal_positive.lengths, max_len=xmax+1000)
        ax.fill_between(x_sp, y_sp, alpha=0.4, color=COLORS['signal_positive']['fill'])
        ax.plot(x_sp, y_sp, linewidth=2, color=COLORS['signal_positive']['line'],
                label='signal_positive')
        
        # Unblock
        x_ub, y_ub = lengths_to_kde(stats.unblock.lengths, max_len=xmax+1000)
        ax.fill_between(x_ub, y_ub, alpha=0.4, color=COLORS['unblock']['fill'])
        ax.plot(x_ub, y_ub, linewidth=2, color=COLORS['unblock']['line'],
                label='unblock')
        
        # Target markers
        target = stats.detected_target or 2630
        if xmin <= target <= xmax:
            ax.axvline(x=target, color='black', linestyle='--', alpha=0.6, linewidth=1.5)
        if xmin <= target*2 <= xmax:
            ax.axvline(x=target*2, color='blue', linestyle=':', alpha=0.5, linewidth=1.5,
                      label=f'2x target ({target*2})')
        if xmin <= target*3 <= xmax:
            ax.axvline(x=target*3, color='purple', linestyle=':', alpha=0.5, linewidth=1.5,
                      label=f'3x target ({target*3})')
        
        ax.set_xlim(xmin, xmax)
        ax.set_xlabel('Read Length (bp)', fontsize=11)
        ax.set_ylabel('Density (%)', fontsize=11)
        ax.set_title(f'{title}\n{subtitle}', fontsize=11, fontweight='bold')
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, alpha=0.3)
    
    plt.suptitle(f'Multi-Zoom End Reason Analysis: {stats.name}',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()

def plot_summary(stats_list: List[ExperimentStats], output: Path, dpi: int = 300):
    """Summary statistics bar charts"""
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), dpi=dpi)
    
    names = [s.name for s in stats_list]
    sp_counts = [s.signal_positive.count for s in stats_list]
    ub_counts = [s.unblock.count for s in stats_list]
    
    x = np.arange(len(names))
    width = 0.35
    
    # Panel 1: Read counts
    ax1.bar(x - width/2, sp_counts, width, label='signal_positive',
            color=COLORS['signal_positive']['fill'], 
            edgecolor=COLORS['signal_positive']['line'], linewidth=2)
    ax1.bar(x + width/2, ub_counts, width, label='unblock',
            color=COLORS['unblock']['fill'],
            edgecolor=COLORS['unblock']['line'], linewidth=2)
    
    ax1.set_ylabel('Read Count', fontsize=12)
    ax1.set_title('Read Counts by End Reason', fontsize=12, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels([n[:15] for n in names], rotation=45, ha='right')
    ax1.legend()
    ax1.set_yscale('log')
    ax1.grid(True, alpha=0.3, axis='y')
    
    # Panel 2: Unblock percentage
    ub_pcts = [s.unblock.pct for s in stats_list]
    colors = []
    for pct in ub_pcts:
        if pct <= 2:
            colors.append('#27ae60')  # Green - excellent
        elif pct <= 5:
            colors.append('#f39c12')  # Yellow - good
        elif pct <= 10:
            colors.append('#e67e22')  # Orange - warning
        else:
            colors.append('#e74c3c')  # Red - poor
    
    bars = ax2.bar(x, ub_pcts, width=0.6, color=colors,
                   edgecolor='black', linewidth=1)
    
    ax2.axhline(y=2, color='green', linestyle='--', alpha=0.7, label='Excellent (<2%)')
    ax2.axhline(y=5, color='orange', linestyle='--', alpha=0.7, label='Good (<5%)')
    ax2.axhline(y=10, color='red', linestyle='--', alpha=0.7, label='Warning (<10%)')
    
    ax2.set_ylabel('Unblock Percentage (%)', fontsize=12)
    ax2.set_title('Unblock Rate by Experiment', fontsize=12, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels([n[:15] for n in names], rotation=45, ha='right')
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Add percentage labels
    for bar, pct in zip(bars, ub_pcts):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                f'{pct:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    plt.suptitle('End Reason Summary Statistics', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()

# ============================================================================
# Main CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='ONT End Reason QC Analysis v2.0',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic KDE analysis
  python3 ont_endreason_qc_v2.py /path/to/run --plot-kde qc.png
  
  # Multi-zoom analysis
  python3 ont_endreason_qc_v2.py /path/to/run --plot-multizoom zoom.png
  
  # Full analysis with all outputs
  python3 ont_endreason_qc_v2.py /path/to/run --plot-kde kde.png \\
      --plot-multizoom zoom.png --plot-summary summary.png --json stats.json
"""
    )
    
    parser.add_argument('inputs', nargs='+', help='Run directories or sequencing_summary files')
    parser.add_argument('--plot-kde', '-k', help='Output KDE comparison plot')
    parser.add_argument('--plot-multizoom', '-m', help='Output multi-zoom analysis plot')
    parser.add_argument('--plot-summary', '-s', help='Output summary statistics plot')
    parser.add_argument('--json', '-j', help='Output JSON statistics')
    parser.add_argument('--dpi', type=int, default=300, help='Plot resolution')
    parser.add_argument('--max-reads', type=int, help='Limit reads for quick analysis')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress output')
    
    args = parser.parse_args()
    
    all_stats = []
    
    for input_path in args.inputs:
        path = Path(input_path)
        if not path.exists():
            print(f"Warning: {input_path} not found", file=sys.stderr)
            continue
        
        try:
            if not args.quiet:
                print(f"Processing: {path.name}...", file=sys.stderr)
            stats = analyze_experiment(path, max_reads=args.max_reads)
            all_stats.append(stats)
        except Exception as e:
            print(f"Error: {input_path}: {e}", file=sys.stderr)
    
    if not all_stats:
        print("Error: No valid experiments", file=sys.stderr)
        sys.exit(1)
    
    # Print summary
    if not args.quiet:
        print("\n" + "="*80)
        print("END REASON QC SUMMARY")
        print("="*80)
        for s in all_stats:
            print(f"\n{s.name}:")
            print(f"  Total reads: {s.total_reads:,}")
            print(f"  Quality grade: {s.quality_grade}")
            print(f"  Signal positive: {s.signal_positive.pct:.1f}% (N50={s.signal_positive.n50:,})")
            print(f"  Unblock: {s.unblock.pct:.1f}% (N50={s.unblock.n50:,})")
            print(f"  Short reads (<200bp): {s.short_read_pct:.1f}%")
    
    # Generate plots
    if HAS_MATPLOTLIB:
        for stats in all_stats:
            if args.plot_kde:
                out = Path(args.plot_kde)
                if len(all_stats) > 1:
                    out = out.parent / f"{out.stem}_{stats.name}{out.suffix}"
                plot_kde_comparison(stats, out, dpi=args.dpi)
                if not args.quiet:
                    print(f"Saved: {out}")
            
            if args.plot_multizoom:
                out = Path(args.plot_multizoom)
                if len(all_stats) > 1:
                    out = out.parent / f"{out.stem}_{stats.name}{out.suffix}"
                plot_multizoom(stats, out, dpi=args.dpi)
                if not args.quiet:
                    print(f"Saved: {out}")
        
        if args.plot_summary:
            plot_summary(all_stats, Path(args.plot_summary), dpi=args.dpi)
            if not args.quiet:
                print(f"Saved: {args.plot_summary}")
    
    # Output JSON
    if args.json:
        output = {
            "version": "2.0",
            "analysis_type": "endreason_qc",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "experiments": []
        }
        for s in all_stats:
            exp_data = {
                "name": s.name,
                "source_file": s.source_file,
                "total_reads": s.total_reads,
                "quality_grade": s.quality_grade,
                "signal_positive": {
                    "count": s.signal_positive.count,
                    "pct": round(s.signal_positive.pct, 2),
                    "n50": s.signal_positive.n50,
                    "median": s.signal_positive.median,
                    "peak_center": s.signal_positive.peak_center,
                    "peak_sigma": round(s.signal_positive.peak_sigma, 1),
                },
                "unblock": {
                    "count": s.unblock.count,
                    "pct": round(s.unblock.pct, 2),
                    "n50": s.unblock.n50,
                    "median": s.unblock.median,
                },
                "contamination": {
                    "short_read_pct": round(s.short_read_pct, 2),
                    "adapter_dimer_pct": round(s.adapter_dimer_pct, 2),
                    "concatemer_pct": round(s.concatemer_pct, 2),
                },
                "detected_target": s.detected_target,
            }
            output["experiments"].append(exp_data)
        
        with open(args.json, 'w') as f:
            json.dump(output, f, indent=2)
        if not args.quiet:
            print(f"Saved: {args.json}")

if __name__ == '__main__':
    main()
