#!/usr/bin/env python3
"""
ONT SMAseq Read Length Distribution Analysis v1.0

Fine-grained, high-quality read length distributions for SMA-seq experiments.
LED = Length-End-Distribution analysis with quality filtering.

Key Features:
- High-quality read filtering (passes_filtering, Q-score thresholds)
- Fine-grained BP-level resolution (no binning loss)
- Publication-quality 300+ DPI output
- SMAseq-specific peak detection and fragment analysis
- Multi-experiment comparison with statistical annotations
- End reason stratification for quality assessment
- Pattern B integration with ont-experiments

Data Sources (priority order):
1. sequencing_summary.txt - Has passes_filtering, qscore, length, end_reason
2. POD5 files - Metadata contains end reason and signal length

Usage:
  # Single experiment
  python3 ont_smaseq_readlen.py /path/to/experiment --json results.json

  # Registry-based (all SMAseq experiments)
  python3 ont_smaseq_readlen.py --registry /path/to/experiments.yaml --smaseq-only

  # Pattern B integration
  ont_experiments.py run smaseq_readlen <exp_id> --json results.json

Author: Claude (Anthropic) + Human collaboration
Version: 1.0.0
"""

import argparse
import gzip
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

# Optional imports with graceful fallback
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
    from matplotlib.ticker import FuncFormatter, AutoMinorLocator, MaxNLocator
    from matplotlib.patches import Rectangle
    import matplotlib.patches as mpatches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    from scipy import signal as scipy_signal
    from scipy.stats import gaussian_kde
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# =============================================================================
# Constants & Configuration
# =============================================================================

VERSION = "1.0.0"

# Quality filtering thresholds
DEFAULT_MIN_QSCORE = 10.0          # Minimum Q-score for HQ reads
DEFAULT_PASSES_FILTERING = True     # Require passes_filtering=True
DEFAULT_MIN_LENGTH = 100            # Minimum read length (bp)
DEFAULT_MAX_LENGTH = 100000         # Maximum read length for plotting

# SMAseq-specific expected fragment sizes (bp)
SMASEQ_EXPECTED_FRAGMENTS = {
    'adapter_dimer': (0, 200),
    'short_fragment': (200, 1000),
    'target_fragment': (1000, 5000),      # Typical SMAseq targets
    'long_fragment': (5000, 15000),
    'ultra_long': (15000, float('inf')),
}

# Color schemes
QUALITY_COLORS = {
    'high_quality': '#2563eb',      # Blue - HQ reads
    'low_quality': '#dc2626',       # Red - LQ reads
    'all': '#6b7280',               # Gray - All reads
}

END_REASON_COLORS = {
    'signal_positive': '#10b981',               # Green - normal completion
    'unblock_mux_change': '#f59e0b',            # Amber - adaptive rejection
    'data_service_unblock_mux_change': '#ef4444',  # Red - basecall rejection
    'mux_change': '#8b5cf6',                    # Purple - pore change
    'signal_negative': '#6b7280',               # Gray - signal lost
    'unknown': '#94a3b8',                       # Slate - unknown
}

END_REASON_LABELS = {
    'signal_positive': 'Signal Positive',
    'unblock_mux_change': 'Unblock (Adaptive)',
    'data_service_unblock_mux_change': 'Data Service Unblock',
    'mux_change': 'MUX Change',
    'signal_negative': 'Signal Negative',
    'unknown': 'Unknown',
}

# Publication color schemes
COLOR_SCHEMES = {
    'default': ['#2563eb', '#dc2626', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'],
    'viridis': ['#440154', '#31688e', '#35b779', '#fde725', '#21918c', '#5ec962'],
    'nature': ['#E64B35', '#4DBBD5', '#00A087', '#3C5488', '#F39B7F', '#8491B4'],
    'science': ['#3B4992', '#EE0000', '#008B45', '#631879', '#008280', '#BB0021'],
}


# =============================================================================
# Data Structures
# =============================================================================

class ReadRecord(NamedTuple):
    """Single read with quality and length information"""
    read_id: str
    length: int
    qscore: float
    passes_filtering: bool
    end_reason: str
    duration: float = 0.0


@dataclass
class FragmentBin:
    """Statistics for a fragment size bin"""
    name: str
    min_bp: int
    max_bp: int
    count: int = 0
    total_bases: int = 0
    mean_qscore: float = 0.0
    pct_of_total: float = 0.0
    pct_of_bases: float = 0.0


@dataclass
class ReadLengthStats:
    """Comprehensive read length statistics"""
    experiment_id: str
    experiment_name: str
    source_file: str

    # Total counts
    total_reads: int = 0
    total_bases: int = 0
    hq_reads: int = 0
    hq_bases: int = 0
    lq_reads: int = 0
    lq_bases: int = 0

    # Length statistics (HQ reads)
    mean_length: float = 0.0
    median_length: float = 0.0
    std_length: float = 0.0
    min_length: int = 0
    max_length: int = 0
    n50: int = 0
    n90: int = 0
    l50: int = 0

    # Quality statistics
    mean_qscore: float = 0.0
    median_qscore: float = 0.0

    # Fragment distribution
    fragment_bins: Dict[str, FragmentBin] = field(default_factory=dict)

    # End reason breakdown (HQ only)
    end_reason_counts: Dict[str, int] = field(default_factory=dict)
    end_reason_mean_lengths: Dict[str, float] = field(default_factory=dict)

    # Fine-grained distribution (bp-level counts for HQ reads)
    length_counts: Dict[int, int] = field(default_factory=dict)

    # Peak detection
    detected_peaks: List[int] = field(default_factory=list)

    # Quality assessment
    quality_status: str = "OK"
    signal_positive_pct: float = 0.0
    hq_pct: float = 0.0

    # Metadata
    timestamp: str = ""
    filters_applied: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict"""
        d = asdict(self)
        # Convert fragment bins
        d['fragment_bins'] = {k: asdict(v) for k, v in self.fragment_bins.items()}
        # Compress length_counts for storage
        if d['length_counts']:
            # Store as list of [length, count] pairs, sorted
            d['length_counts_compressed'] = sorted(d['length_counts'].items())
            del d['length_counts']
        return d


# =============================================================================
# Helper Functions
# =============================================================================

def normalize_end_reason(raw_reason: str) -> str:
    """Normalize end reason strings to canonical form"""
    if not raw_reason:
        return 'unknown'

    reason = str(raw_reason).lower().strip()

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


def calculate_nx(lengths: List[int], x: float = 50) -> Tuple[int, int]:
    """Calculate NX (e.g., N50) and LX values"""
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


def format_bp(x, pos=None):
    """Format bp values for axis labels"""
    if x >= 1e6:
        return f'{x/1e6:.1f}M'
    elif x >= 1e3:
        return f'{x/1e3:.0f}k'
    else:
        return f'{int(x)}'


def format_count(x, pos=None):
    """Format count values for axis labels"""
    if x >= 1e6:
        return f'{x/1e6:.1f}M'
    elif x >= 1e3:
        return f'{x/1e3:.1f}k'
    else:
        return f'{int(x)}'


def detect_peaks(lengths: List[int], prominence: float = 0.1) -> List[int]:
    """Detect peaks in read length distribution using KDE"""
    if not HAS_SCIPY or not HAS_NUMPY or len(lengths) < 100:
        return []

    try:
        # Create KDE
        kde = gaussian_kde(lengths, bw_method='scott')

        # Evaluate on fine grid
        x_grid = np.linspace(min(lengths), min(max(lengths), 50000), 1000)
        density = kde(x_grid)

        # Find peaks
        peaks, properties = scipy_signal.find_peaks(
            density,
            prominence=prominence * max(density),
            distance=20  # Minimum distance between peaks
        )

        # Return peak positions
        peak_positions = [int(x_grid[p]) for p in peaks]
        return sorted(peak_positions)[:10]  # Top 10 peaks

    except Exception:
        return []


# =============================================================================
# Data Source Parsers
# =============================================================================

def parse_sequencing_summary(
    filepath: Path,
    min_qscore: float = DEFAULT_MIN_QSCORE,
    require_pass: bool = DEFAULT_PASSES_FILTERING,
    min_length: int = DEFAULT_MIN_LENGTH,
    max_reads: int = None
) -> Tuple[List[ReadRecord], List[ReadRecord]]:
    """
    Parse sequencing_summary.txt with quality filtering.

    Returns:
        Tuple of (high_quality_reads, low_quality_reads)
    """
    hq_reads = []
    lq_reads = []

    opener = gzip.open if str(filepath).endswith('.gz') else open

    with opener(filepath, 'rt') as f:
        header = f.readline().strip().split('\t')

        # Find column indices
        col_map = {col.lower(): i for i, col in enumerate(header)}

        # Required columns
        len_col = None
        for name in ['sequence_length_template', 'sequence_length', 'read_length']:
            if name in col_map:
                len_col = col_map[name]
                break

        if len_col is None:
            raise ValueError(f"No length column found in {filepath}")

        # Optional columns
        qscore_col = col_map.get('mean_qscore_template', col_map.get('mean_qscore'))
        pass_col = col_map.get('passes_filtering')
        er_col = col_map.get('end_reason', col_map.get('end_reason_tag'))
        dur_col = col_map.get('duration_template', col_map.get('duration'))
        id_col = col_map.get('read_id', 0)

        read_count = 0
        for line in f:
            if max_reads and read_count >= max_reads:
                break

            parts = line.strip().split('\t')
            if len(parts) <= len_col:
                continue

            try:
                length = int(float(parts[len_col]))
                if length < min_length:
                    continue

                # Get quality score
                qscore = 0.0
                if qscore_col is not None and len(parts) > qscore_col:
                    try:
                        qscore = float(parts[qscore_col])
                    except ValueError:
                        qscore = 0.0

                # Get passes_filtering
                passes = True
                if pass_col is not None and len(parts) > pass_col:
                    passes = parts[pass_col].lower() in ('true', '1', 'yes', 't')

                # Get end reason
                end_reason = 'unknown'
                if er_col is not None and len(parts) > er_col:
                    end_reason = normalize_end_reason(parts[er_col])

                # Get duration
                duration = 0.0
                if dur_col is not None and len(parts) > dur_col:
                    try:
                        duration = float(parts[dur_col])
                    except ValueError:
                        duration = 0.0

                # Get read ID
                read_id = parts[id_col] if len(parts) > id_col else f"read_{read_count}"

                record = ReadRecord(
                    read_id=read_id,
                    length=length,
                    qscore=qscore,
                    passes_filtering=passes,
                    end_reason=end_reason,
                    duration=duration
                )

                # Classify as HQ or LQ
                is_hq = (
                    (not require_pass or passes) and
                    qscore >= min_qscore
                )

                if is_hq:
                    hq_reads.append(record)
                else:
                    lq_reads.append(record)

                read_count += 1

            except (ValueError, IndexError):
                continue

    return hq_reads, lq_reads


def parse_pod5(
    filepath: Path,
    min_qscore: float = DEFAULT_MIN_QSCORE,
    max_reads: int = None
) -> Tuple[List[ReadRecord], List[ReadRecord]]:
    """Parse POD5 file for read lengths and end reasons"""
    if not HAS_POD5:
        raise ImportError("pod5 required: pip install pod5")

    hq_reads = []
    lq_reads = []

    with pod5.Reader(filepath) as reader:
        for i, read in enumerate(reader.reads()):
            if max_reads and i >= max_reads:
                break

            # Estimate length from signal
            sample_rate = read.run_info.sample_rate
            signal_len = len(read.signal)
            estimated_bases = int(signal_len / sample_rate * 450)

            if estimated_bases < DEFAULT_MIN_LENGTH:
                continue

            # Get end reason
            try:
                end_reason_raw = read.end_reason.name if hasattr(read, 'end_reason') else 'unknown'
            except:
                end_reason_raw = 'unknown'

            record = ReadRecord(
                read_id=str(read.read_id),
                length=estimated_bases,
                qscore=0.0,  # Not available from POD5 directly
                passes_filtering=True,
                end_reason=normalize_end_reason(end_reason_raw),
                duration=signal_len / sample_rate if sample_rate > 0 else 0.0
            )

            # POD5 doesn't have qscore, so all are treated as HQ
            hq_reads.append(record)

    return hq_reads, lq_reads


def find_data_source(run_path: Path) -> Tuple[Path, str]:
    """Find the best data source in a run directory"""

    # Prefer sequencing_summary (has quality and passes_filtering)
    search_paths = [
        run_path,
        run_path / 'basecalling',
        run_path / 'pass',
        run_path / 'fastq_pass',
    ]

    for search_path in search_paths:
        if not search_path.exists():
            continue
        for pattern in ['sequencing_summary*.txt', 'sequencing_summary*.txt.gz']:
            matches = list(search_path.glob(pattern))
            if matches:
                return matches[0], 'sequencing_summary'

    # POD5 as fallback
    for pattern in ['*.pod5', 'pod5_pass/*.pod5', 'pod5/*.pod5']:
        matches = list(run_path.glob(pattern))
        if matches:
            return matches[0], 'pod5'

    raise FileNotFoundError(f"No suitable data source found in {run_path}")


# =============================================================================
# Statistics Computation
# =============================================================================

def compute_fragment_bins(lengths: List[int]) -> Dict[str, FragmentBin]:
    """Compute fragment size bin statistics"""
    bins = {}
    total_reads = len(lengths)
    total_bases = sum(lengths)

    for name, (min_bp, max_bp) in SMASEQ_EXPECTED_FRAGMENTS.items():
        bin_lengths = [l for l in lengths if min_bp <= l < max_bp]

        bins[name] = FragmentBin(
            name=name,
            min_bp=min_bp,
            max_bp=int(max_bp) if max_bp != float('inf') else 999999,
            count=len(bin_lengths),
            total_bases=sum(bin_lengths),
            mean_qscore=0.0,
            pct_of_total=100 * len(bin_lengths) / total_reads if total_reads > 0 else 0,
            pct_of_bases=100 * sum(bin_lengths) / total_bases if total_bases > 0 else 0,
        )

    return bins


def compute_stats(
    hq_reads: List[ReadRecord],
    lq_reads: List[ReadRecord],
    experiment_id: str,
    experiment_name: str,
    source_file: str,
    filters: Dict[str, Any]
) -> ReadLengthStats:
    """Compute comprehensive read length statistics"""

    all_reads = hq_reads + lq_reads

    if not all_reads:
        raise ValueError("No reads found")

    # Basic counts
    total_reads = len(all_reads)
    total_bases = sum(r.length for r in all_reads)
    hq_count = len(hq_reads)
    hq_bases = sum(r.length for r in hq_reads)
    lq_count = len(lq_reads)
    lq_bases = sum(r.length for r in lq_reads)

    # HQ length statistics
    hq_lengths = [r.length for r in hq_reads]

    if HAS_NUMPY and hq_lengths:
        arr = np.array(hq_lengths)
        mean_len = float(np.mean(arr))
        median_len = float(np.median(arr))
        std_len = float(np.std(arr))
    elif hq_lengths:
        sorted_lens = sorted(hq_lengths)
        n = len(sorted_lens)
        mean_len = sum(hq_lengths) / n
        median_len = sorted_lens[n // 2]
        std_len = 0.0  # Skip without numpy
    else:
        mean_len = median_len = std_len = 0.0

    # N50, N90
    n50, l50 = calculate_nx(hq_lengths, 50)
    n90, _ = calculate_nx(hq_lengths, 90)

    # Quality scores
    hq_qscores = [r.qscore for r in hq_reads if r.qscore > 0]
    if HAS_NUMPY and hq_qscores:
        mean_q = float(np.mean(hq_qscores))
        median_q = float(np.median(hq_qscores))
    elif hq_qscores:
        sorted_q = sorted(hq_qscores)
        mean_q = sum(hq_qscores) / len(hq_qscores)
        median_q = sorted_q[len(sorted_q) // 2]
    else:
        mean_q = median_q = 0.0

    # Fragment bins (HQ only)
    fragment_bins = compute_fragment_bins(hq_lengths)

    # End reason breakdown (HQ only)
    end_reason_counts = Counter(r.end_reason for r in hq_reads)
    end_reason_lengths = defaultdict(list)
    for r in hq_reads:
        end_reason_lengths[r.end_reason].append(r.length)

    end_reason_mean_lengths = {
        er: sum(lens) / len(lens) if lens else 0
        for er, lens in end_reason_lengths.items()
    }

    # Fine-grained length counts (HQ only)
    length_counts = Counter(hq_lengths)

    # Peak detection
    detected_peaks = detect_peaks(hq_lengths) if hq_lengths else []

    # Quality assessment
    signal_positive_pct = 100 * end_reason_counts.get('signal_positive', 0) / hq_count if hq_count > 0 else 0
    hq_pct = 100 * hq_count / total_reads if total_reads > 0 else 0

    if signal_positive_pct >= 75 and hq_pct >= 50:
        quality_status = "OK"
    elif signal_positive_pct >= 50 or hq_pct >= 30:
        quality_status = "CHECK"
    else:
        quality_status = "FAIL"

    return ReadLengthStats(
        experiment_id=experiment_id,
        experiment_name=experiment_name,
        source_file=source_file,
        total_reads=total_reads,
        total_bases=total_bases,
        hq_reads=hq_count,
        hq_bases=hq_bases,
        lq_reads=lq_count,
        lq_bases=lq_bases,
        mean_length=round(mean_len, 1),
        median_length=round(median_len, 1),
        std_length=round(std_len, 1),
        min_length=min(hq_lengths) if hq_lengths else 0,
        max_length=max(hq_lengths) if hq_lengths else 0,
        n50=n50,
        n90=n90,
        l50=l50,
        mean_qscore=round(mean_q, 2),
        median_qscore=round(median_q, 2),
        fragment_bins=fragment_bins,
        end_reason_counts=dict(end_reason_counts),
        end_reason_mean_lengths={k: round(v, 1) for k, v in end_reason_mean_lengths.items()},
        length_counts=dict(length_counts),
        detected_peaks=detected_peaks,
        quality_status=quality_status,
        signal_positive_pct=round(signal_positive_pct, 2),
        hq_pct=round(hq_pct, 2),
        timestamp=datetime.utcnow().isoformat() + "Z",
        filters_applied=filters
    )


# =============================================================================
# Plotting Functions
# =============================================================================

def plot_fine_grained_distribution(
    stats: ReadLengthStats,
    output_path: Path,
    title: str = None,
    dpi: int = 300,
    figsize: Tuple[float, float] = (14, 8),
    xlim: Tuple[int, int] = None,
    log_y: bool = False,
    show_peaks: bool = True,
    show_fragments: bool = True,
    color_scheme: str = 'default',
):
    """
    Plot fine-grained read length distribution with BP-level resolution.

    Creates publication-quality histogram with optional peak annotations
    and fragment size bin markers.
    """
    if not HAS_MATPLOTLIB or not HAS_NUMPY:
        raise ImportError("matplotlib and numpy required for plotting")

    # Expand length counts to array
    lengths = []
    for length, count in stats.length_counts.items():
        lengths.extend([length] * count)

    if not lengths:
        raise ValueError("No length data for plotting")

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

    # Determine x-range
    if xlim:
        x_min, x_max = xlim
    else:
        x_min = 0
        x_max = min(stats.max_length, DEFAULT_MAX_LENGTH)
        # Expand to show N50 if needed
        if stats.n50 > x_max * 0.8:
            x_max = int(stats.n50 * 1.5)

    # Fine-grained bins (100bp for fine resolution)
    bin_width = 100
    bins = np.arange(x_min, x_max + bin_width, bin_width)

    # Main histogram
    color = COLOR_SCHEMES.get(color_scheme, COLOR_SCHEMES['default'])[0]
    counts, bin_edges, patches = ax.hist(
        lengths, bins=bins,
        alpha=0.8, color=color,
        edgecolor='white', linewidth=0.3,
        label=f'HQ Reads (n={stats.hq_reads:,})'
    )

    # Add fragment region shading
    if show_fragments:
        fragment_colors = {
            'adapter_dimer': '#fef3c7',     # Amber light
            'short_fragment': '#dbeafe',     # Blue light
            'target_fragment': '#dcfce7',    # Green light
            'long_fragment': '#fae8ff',      # Purple light
            'ultra_long': '#fee2e2',         # Red light
        }

        y_max = max(counts) if len(counts) > 0 else 1
        for name, (min_bp, max_bp) in SMASEQ_EXPECTED_FRAGMENTS.items():
            if max_bp == float('inf'):
                max_bp = x_max
            if min_bp < x_max:
                rect = Rectangle(
                    (min_bp, 0), min(max_bp, x_max) - min_bp, y_max * 1.1,
                    alpha=0.15, color=fragment_colors.get(name, '#e5e7eb'),
                    zorder=0
                )
                ax.add_patch(rect)

    # Add peak markers
    if show_peaks and stats.detected_peaks:
        for peak in stats.detected_peaks:
            if x_min <= peak <= x_max:
                ax.axvline(peak, color='#dc2626', linestyle='--',
                          linewidth=1.5, alpha=0.7, zorder=5)
                ax.annotate(
                    f'{format_bp(peak)}',
                    xy=(peak, max(counts) * 0.95),
                    fontsize=8, color='#dc2626',
                    ha='center', va='bottom',
                    rotation=90
                )

    # Add N50 marker
    if x_min <= stats.n50 <= x_max:
        ax.axvline(stats.n50, color='#059669', linestyle='-',
                  linewidth=2, alpha=0.8, zorder=5,
                  label=f'N50 = {format_bp(stats.n50)}')

    # Add median marker
    if x_min <= stats.median_length <= x_max:
        ax.axvline(stats.median_length, color='#7c3aed', linestyle=':',
                  linewidth=2, alpha=0.8, zorder=5,
                  label=f'Median = {format_bp(stats.median_length)}')

    # Axis formatting
    ax.set_xlabel('Read Length (bp)', fontweight='bold')
    ax.set_ylabel('Read Count', fontweight='bold')
    ax.xaxis.set_major_formatter(FuncFormatter(format_bp))
    ax.yaxis.set_major_formatter(FuncFormatter(format_count))
    ax.xaxis.set_minor_locator(AutoMinorLocator(5))

    if log_y:
        ax.set_yscale('log')

    ax.set_xlim(x_min, x_max)

    # Grid
    ax.grid(True, which='major', alpha=0.3, linestyle='-')
    ax.grid(True, which='minor', alpha=0.15, linestyle='-')

    # Title
    if title is None:
        title = f"Read Length Distribution: {stats.experiment_name}"
    ax.set_title(title, fontweight='bold', pad=15)

    # Legend
    ax.legend(loc='upper right', framealpha=0.95)

    # Stats box
    stats_text = (
        f"HQ Reads: {stats.hq_reads:,} ({stats.hq_pct:.1f}%)\n"
        f"Total Bases: {stats.hq_bases/1e9:.2f} Gb\n"
        f"N50: {stats.n50:,} bp\n"
        f"Mean: {stats.mean_length:,.0f} bp\n"
        f"Median: {stats.median_length:,.0f} bp\n"
        f"Mean Q: {stats.mean_qscore:.1f}\n"
        f"Quality: {stats.quality_status}"
    )
    props = dict(boxstyle='round', facecolor='white', alpha=0.95, edgecolor='gray')
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=9,
           verticalalignment='top', fontfamily='monospace', bbox=props)

    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()

    return output_path


def plot_end_reason_overlay(
    stats: ReadLengthStats,
    hq_reads: List[ReadRecord],
    output_path: Path,
    title: str = None,
    dpi: int = 300,
    figsize: Tuple[float, float] = (14, 8),
    xlim: Tuple[int, int] = None,
    alpha: float = 0.5,
):
    """
    Plot read length distributions overlaid by end reason.
    Semi-transparent histograms allow comparison across classes.
    """
    if not HAS_MATPLOTLIB or not HAS_NUMPY:
        raise ImportError("matplotlib and numpy required for plotting")

    # Group reads by end reason
    by_end_reason = defaultdict(list)
    for r in hq_reads:
        by_end_reason[r.end_reason].append(r.length)

    if not by_end_reason:
        raise ValueError("No data for end reason overlay plot")

    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.size': 10,
        'axes.linewidth': 1.2,
        'figure.dpi': dpi,
    })

    fig, ax = plt.subplots(figsize=figsize)

    # Determine x-range
    all_lengths = [l for lengths in by_end_reason.values() for l in lengths]
    if xlim:
        x_min, x_max = xlim
    else:
        x_min = 0
        x_max = min(max(all_lengths), DEFAULT_MAX_LENGTH)

    bin_width = 100
    bins = np.arange(x_min, x_max + bin_width, bin_width)

    # Plot order (signal_positive first, then by count)
    order = ['signal_positive', 'data_service_unblock_mux_change',
             'unblock_mux_change', 'mux_change', 'signal_negative', 'unknown']

    legend_handles = []

    for er_name in order:
        if er_name not in by_end_reason:
            continue

        lengths = by_end_reason[er_name]
        if not lengths:
            continue

        color = END_REASON_COLORS.get(er_name, '#94a3b8')
        label = END_REASON_LABELS.get(er_name, er_name)

        count = len(lengths)
        pct = 100 * count / len(all_lengths)

        ax.hist(
            lengths, bins=bins,
            alpha=alpha, color=color,
            edgecolor=color, linewidth=0.5,
            label=f"{label} (n={count:,}, {pct:.1f}%)"
        )

        legend_handles.append(mpatches.Patch(
            color=color, alpha=alpha,
            label=f"{label} (n={count:,}, {pct:.1f}%)"
        ))

    # Axis formatting
    ax.set_xlabel('Read Length (bp)', fontweight='bold')
    ax.set_ylabel('Read Count', fontweight='bold')
    ax.xaxis.set_major_formatter(FuncFormatter(format_bp))
    ax.yaxis.set_major_formatter(FuncFormatter(format_count))

    ax.set_xlim(x_min, x_max)
    ax.grid(True, which='major', alpha=0.3)

    if title is None:
        title = f"Read Length by End Reason: {stats.experiment_name}"
    ax.set_title(title, fontweight='bold', pad=15)

    ax.legend(handles=legend_handles, loc='upper right', framealpha=0.95)

    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()

    return output_path


def plot_zoom_regions(
    stats: ReadLengthStats,
    output_path: Path,
    zoom_regions: List[Tuple[int, int]] = None,
    title: str = None,
    dpi: int = 300,
    figsize: Tuple[float, float] = (16, 10),
    show_kde: bool = True,
):
    """
    Plot zoomed regions of the read length distribution for fine-grained peak analysis.

    Args:
        stats: ReadLengthStats with length_counts
        output_path: Output path for PNG
        zoom_regions: List of (min_bp, max_bp) tuples for zoom regions
                     If None, auto-detect around peaks
        show_kde: Overlay KDE density curve

    Creates a multi-panel figure with zoomed views of key regions.
    """
    if not HAS_MATPLOTLIB or not HAS_NUMPY:
        raise ImportError("matplotlib and numpy required for plotting")

    # Expand length counts
    lengths = []
    for length, count in stats.length_counts.items():
        lengths.extend([length] * count)

    if not lengths:
        raise ValueError("No length data for zoom plot")

    # Auto-detect zoom regions if not provided
    if zoom_regions is None:
        zoom_regions = []

        # Always include short fragment region (adapter dimers, short fragments)
        zoom_regions.append((0, 1000))

        # Add peak regions
        for peak in stats.detected_peaks[:3]:  # Top 3 peaks
            margin = max(500, peak * 0.2)
            zoom_regions.append((max(0, int(peak - margin)), int(peak + margin)))

        # Add target fragment region
        if stats.n50 > 1000:
            zoom_regions.append((1000, min(stats.n50 * 2, 10000)))

    n_regions = len(zoom_regions)
    if n_regions == 0:
        zoom_regions = [(0, 5000)]
        n_regions = 1

    # Layout: up to 2x3 grid
    n_cols = min(3, n_regions)
    n_rows = (n_regions + n_cols - 1) // n_cols

    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.size': 9,
        'figure.dpi': dpi,
    })

    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
    if n_regions == 1:
        axes = np.array([[axes]])
    elif n_rows == 1:
        axes = axes.reshape(1, -1)
    elif n_cols == 1:
        axes = axes.reshape(-1, 1)

    for idx, (x_min, x_max) in enumerate(zoom_regions):
        row = idx // n_cols
        col = idx % n_cols
        ax = axes[row, col]

        # Filter lengths to region
        region_lengths = [l for l in lengths if x_min <= l <= x_max]

        if not region_lengths:
            ax.text(0.5, 0.5, 'No data in region',
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'Region: {format_bp(x_min)}-{format_bp(x_max)}')
            continue

        # Fine-grained bins (25bp for zoom view)
        bin_width = max(10, (x_max - x_min) // 100)
        bins = np.arange(x_min, x_max + bin_width, bin_width)

        # Histogram
        counts, bin_edges, _ = ax.hist(
            region_lengths, bins=bins,
            alpha=0.7, color='#2563eb',
            edgecolor='white', linewidth=0.3,
        )

        # KDE overlay
        if show_kde and HAS_SCIPY and len(region_lengths) > 50:
            try:
                kde = gaussian_kde(region_lengths, bw_method='scott')
                x_kde = np.linspace(x_min, x_max, 200)
                y_kde = kde(x_kde)

                # Scale KDE to histogram
                scale = max(counts) / max(y_kde) if max(y_kde) > 0 else 1
                ax2 = ax.twinx()
                ax2.plot(x_kde, y_kde * scale, color='#dc2626',
                        linewidth=2, alpha=0.8, label='KDE')
                ax2.set_ylim(0, max(counts) * 1.1)
                ax2.set_yticks([])

                # Find local peaks in this region
                peaks, _ = scipy_signal.find_peaks(y_kde, prominence=0.1 * max(y_kde))
                for peak_idx in peaks[:5]:
                    peak_pos = x_kde[peak_idx]
                    ax.axvline(peak_pos, color='#dc2626', linestyle='--',
                              linewidth=1, alpha=0.6)
                    ax.annotate(f'{int(peak_pos):,}',
                               xy=(peak_pos, max(counts) * 0.95),
                               fontsize=7, color='#dc2626',
                               ha='center', rotation=90)
            except Exception:
                pass

        # Formatting
        ax.set_xlabel('Read Length (bp)', fontsize=8)
        ax.set_ylabel('Count', fontsize=8)
        ax.xaxis.set_major_formatter(FuncFormatter(format_bp))
        ax.set_title(f'Region: {format_bp(x_min)} - {format_bp(x_max)} '
                    f'(n={len(region_lengths):,})', fontsize=10)
        ax.grid(True, alpha=0.3)

    # Hide unused subplots
    for idx in range(n_regions, n_rows * n_cols):
        row = idx // n_cols
        col = idx % n_cols
        axes[row, col].set_visible(False)

    # Overall title
    if title is None:
        title = f"Zoom Analysis: {stats.experiment_name}"
    fig.suptitle(title, fontweight='bold', fontsize=12, y=1.02)

    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()

    return output_path


def plot_cumulative_distribution(
    stats: ReadLengthStats,
    output_path: Path,
    title: str = None,
    dpi: int = 300,
    figsize: Tuple[float, float] = (12, 8),
    show_nx_markers: bool = True,
):
    """
    Plot cumulative read length distribution with NX markers.

    Shows percentage of total bases contributed by reads of each length,
    with N50, N90 markers and SMAseq target region highlighting.
    """
    if not HAS_MATPLOTLIB or not HAS_NUMPY:
        raise ImportError("matplotlib and numpy required for plotting")

    # Expand and sort lengths
    lengths = []
    for length, count in stats.length_counts.items():
        lengths.extend([length] * count)

    if not lengths:
        raise ValueError("No length data for cumulative plot")

    sorted_lengths = np.sort(lengths)[::-1]  # Descending
    cumulative_bases = np.cumsum(sorted_lengths)
    total_bases = cumulative_bases[-1]
    cumulative_pct = 100 * cumulative_bases / total_bases

    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.size': 10,
        'figure.dpi': dpi,
    })

    fig, ax = plt.subplots(figsize=figsize)

    # Plot cumulative curve
    ax.plot(sorted_lengths, cumulative_pct, color='#2563eb', linewidth=2)
    ax.fill_between(sorted_lengths, 0, cumulative_pct, alpha=0.3, color='#2563eb')

    # Add NX markers
    if show_nx_markers:
        for nx, color, label in [(50, '#10b981', 'N50'), (90, '#f59e0b', 'N90')]:
            nx_val, _ = calculate_nx(lengths, nx)
            ax.axvline(nx_val, color=color, linestyle='--', linewidth=2,
                      label=f'{label}: {format_bp(nx_val)}')
            ax.axhline(nx, color=color, linestyle=':', linewidth=1, alpha=0.5)

    # Highlight SMAseq target region
    target_min, target_max = SMASEQ_EXPECTED_FRAGMENTS['target_fragment']
    ax.axvspan(target_min, target_max, alpha=0.1, color='#10b981',
              label='Target Region')

    # Formatting
    ax.set_xlabel('Read Length (bp)', fontweight='bold')
    ax.set_ylabel('Cumulative % of Total Bases', fontweight='bold')
    ax.xaxis.set_major_formatter(FuncFormatter(format_bp))
    ax.set_xlim(left=0)
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)

    if title is None:
        title = f"Cumulative Distribution: {stats.experiment_name}"
    ax.set_title(title, fontweight='bold', pad=15)

    ax.legend(loc='lower right', framealpha=0.95)

    # Stats annotation
    stats_text = (
        f"Total HQ Bases: {stats.hq_bases/1e9:.2f} Gb\n"
        f"N50: {stats.n50:,} bp\n"
        f"L50: {stats.l50:,} reads"
    )
    props = dict(boxstyle='round', facecolor='white', alpha=0.95, edgecolor='gray')
    ax.text(0.02, 0.25, stats_text, transform=ax.transAxes, fontsize=9,
           verticalalignment='top', fontfamily='monospace', bbox=props)

    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()

    return output_path


def plot_multi_experiment_comparison(
    all_stats: List[ReadLengthStats],
    output_path: Path,
    title: str = None,
    dpi: int = 300,
    figsize: Tuple[float, float] = (16, 12),
):
    """
    Generate 4-panel comparison across multiple SMAseq experiments.

    Panels:
    - Top left: N50 comparison bar chart
    - Top right: HQ% vs Total reads scatter
    - Bottom left: Fragment bin stacked bars
    - Bottom right: End reason breakdown
    """
    if not HAS_MATPLOTLIB or not HAS_NUMPY:
        raise ImportError("matplotlib and numpy required for plotting")

    if len(all_stats) < 2:
        raise ValueError("Need at least 2 experiments for comparison")

    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.size': 10,
        'figure.dpi': dpi,
    })

    fig, axes = plt.subplots(2, 2, figsize=figsize)

    exp_names = [s.experiment_name[:25] for s in all_stats]  # Truncate long names
    n_exp = len(all_stats)
    x_pos = np.arange(n_exp)

    # ===== Top Left: N50 Comparison =====
    ax1 = axes[0, 0]
    n50_values = [s.n50 for s in all_stats]
    colors = ['#10b981' if s.quality_status == 'OK' else
              '#f59e0b' if s.quality_status == 'CHECK' else '#ef4444'
              for s in all_stats]

    bars = ax1.bar(x_pos, n50_values, color=colors, edgecolor='white')
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(exp_names, rotation=45, ha='right', fontsize=8)
    ax1.set_ylabel('N50 (bp)')
    ax1.set_title('N50 by Experiment', fontweight='bold')
    ax1.yaxis.set_major_formatter(FuncFormatter(format_bp))

    # Add value labels
    for bar, val in zip(bars, n50_values):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50,
                format_bp(val), ha='center', va='bottom', fontsize=8)

    # ===== Top Right: HQ% vs Total Reads =====
    ax2 = axes[0, 1]
    total_reads = [s.total_reads for s in all_stats]
    hq_pcts = [s.hq_pct for s in all_stats]

    scatter = ax2.scatter(total_reads, hq_pcts, c=n50_values,
                         cmap='viridis', s=100, alpha=0.8, edgecolors='white')

    for i, name in enumerate(exp_names):
        ax2.annotate(name[:15], (total_reads[i], hq_pcts[i]),
                    fontsize=7, alpha=0.8,
                    xytext=(5, 5), textcoords='offset points')

    ax2.set_xlabel('Total Reads')
    ax2.set_ylabel('HQ Reads (%)')
    ax2.set_title('Read Quality vs Quantity', fontweight='bold')
    ax2.xaxis.set_major_formatter(FuncFormatter(format_count))

    cbar = plt.colorbar(scatter, ax=ax2)
    cbar.set_label('N50 (bp)')

    # ===== Bottom Left: Fragment Bins =====
    ax3 = axes[1, 0]

    fragment_names = list(SMASEQ_EXPECTED_FRAGMENTS.keys())
    fragment_colors = ['#fbbf24', '#60a5fa', '#34d399', '#a78bfa', '#f87171']

    bottom = np.zeros(n_exp)
    for i, frag_name in enumerate(fragment_names):
        pcts = []
        for stats in all_stats:
            if frag_name in stats.fragment_bins:
                pcts.append(stats.fragment_bins[frag_name].pct_of_total)
            else:
                pcts.append(0)

        ax3.bar(x_pos, pcts, bottom=bottom, color=fragment_colors[i],
               label=frag_name.replace('_', ' ').title(), edgecolor='white')
        bottom += np.array(pcts)

    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(exp_names, rotation=45, ha='right', fontsize=8)
    ax3.set_ylabel('Percentage (%)')
    ax3.set_title('Fragment Size Distribution', fontweight='bold')
    ax3.legend(loc='upper right', fontsize=7)
    ax3.set_ylim(0, 100)

    # ===== Bottom Right: End Reason =====
    ax4 = axes[1, 1]

    end_reasons = ['signal_positive', 'data_service_unblock_mux_change',
                   'unblock_mux_change', 'mux_change', 'signal_negative']

    bottom = np.zeros(n_exp)
    for er_name in end_reasons:
        pcts = []
        for stats in all_stats:
            total = sum(stats.end_reason_counts.values())
            count = stats.end_reason_counts.get(er_name, 0)
            pcts.append(100 * count / total if total > 0 else 0)

        color = END_REASON_COLORS.get(er_name, '#94a3b8')
        label = END_REASON_LABELS.get(er_name, er_name)

        ax4.bar(x_pos, pcts, bottom=bottom, color=color,
               label=label, edgecolor='white')
        bottom += np.array(pcts)

    ax4.set_xticks(x_pos)
    ax4.set_xticklabels(exp_names, rotation=45, ha='right', fontsize=8)
    ax4.set_ylabel('Percentage (%)')
    ax4.set_title('End Reason Breakdown', fontweight='bold')
    ax4.legend(loc='upper right', fontsize=7)
    ax4.set_ylim(0, 100)

    # Overall title
    if title is None:
        title = f"SMAseq Experiment Comparison (n={n_exp})"
    fig.suptitle(title, fontweight='bold', fontsize=14, y=1.02)

    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()

    return output_path


def plot_hq_vs_lq_comparison(
    stats: ReadLengthStats,
    hq_reads: List[ReadRecord],
    lq_reads: List[ReadRecord],
    output_path: Path,
    title: str = None,
    dpi: int = 300,
    figsize: Tuple[float, float] = (14, 6),
):
    """Plot side-by-side comparison of HQ vs LQ read distributions"""
    if not HAS_MATPLOTLIB or not HAS_NUMPY:
        raise ImportError("matplotlib and numpy required for plotting")

    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.size': 10,
        'figure.dpi': dpi,
    })

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize, sharey=True)

    hq_lengths = [r.length for r in hq_reads]
    lq_lengths = [r.length for r in lq_reads]

    all_lengths = hq_lengths + lq_lengths
    x_max = min(max(all_lengths) if all_lengths else 10000, DEFAULT_MAX_LENGTH)

    bins = np.arange(0, x_max + 100, 100)

    # HQ distribution
    ax1.hist(hq_lengths, bins=bins, color=QUALITY_COLORS['high_quality'],
            alpha=0.8, edgecolor='white')
    ax1.set_xlabel('Read Length (bp)', fontweight='bold')
    ax1.set_ylabel('Read Count', fontweight='bold')
    ax1.set_title(f'High Quality (n={len(hq_lengths):,})', fontweight='bold')
    ax1.xaxis.set_major_formatter(FuncFormatter(format_bp))
    ax1.grid(True, alpha=0.3)

    # HQ stats
    if hq_lengths:
        hq_n50, _ = calculate_nx(hq_lengths, 50)
        ax1.axvline(hq_n50, color='#059669', linestyle='--', linewidth=2,
                   label=f'N50: {format_bp(hq_n50)}')
        ax1.legend(loc='upper right')

    # LQ distribution
    ax2.hist(lq_lengths, bins=bins, color=QUALITY_COLORS['low_quality'],
            alpha=0.8, edgecolor='white')
    ax2.set_xlabel('Read Length (bp)', fontweight='bold')
    ax2.set_title(f'Low Quality (n={len(lq_lengths):,})', fontweight='bold')
    ax2.xaxis.set_major_formatter(FuncFormatter(format_bp))
    ax2.grid(True, alpha=0.3)

    # LQ stats
    if lq_lengths:
        lq_n50, _ = calculate_nx(lq_lengths, 50)
        ax2.axvline(lq_n50, color='#dc2626', linestyle='--', linewidth=2,
                   label=f'N50: {format_bp(lq_n50)}')
        ax2.legend(loc='upper right')

    if title is None:
        title = f"HQ vs LQ Read Comparison: {stats.experiment_name}"
    fig.suptitle(title, fontweight='bold', fontsize=12)

    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()

    return output_path


# =============================================================================
# Registry Integration
# =============================================================================

def load_smaseq_experiments(registry_path: Path) -> List[Dict]:
    """Load SMAseq experiments from registry YAML"""
    if not HAS_YAML:
        raise ImportError("PyYAML required: pip install pyyaml")

    with open(registry_path) as f:
        registry = yaml.safe_load(f)

    experiments = registry.get('experiments', [])

    # Filter for SMAseq
    smaseq_exps = []
    for exp in experiments:
        name = exp.get('name', '').lower()
        if 'sma' in name or 'smaseq' in name:
            smaseq_exps.append(exp)

    return smaseq_exps


# =============================================================================
# Main Analysis Functions
# =============================================================================

def analyze_experiment(
    run_path: Path,
    experiment_id: str = None,
    experiment_name: str = None,
    min_qscore: float = DEFAULT_MIN_QSCORE,
    require_pass: bool = DEFAULT_PASSES_FILTERING,
    min_length: int = DEFAULT_MIN_LENGTH,
    max_reads: int = None,
    output_dir: Path = None,
    generate_plots: bool = True,
    dpi: int = 300,
) -> Tuple[ReadLengthStats, List[ReadRecord], List[ReadRecord]]:
    """
    Analyze a single experiment for read length distributions.

    Returns:
        Tuple of (stats, hq_reads, lq_reads)
    """
    run_path = Path(run_path)

    # Find data source
    if run_path.is_file():
        source_path = run_path
        source_type = 'sequencing_summary' if 'summary' in str(run_path).lower() else 'pod5'
    else:
        source_path, source_type = find_data_source(run_path)

    # Generate IDs if not provided
    if experiment_id is None:
        experiment_id = hashlib.sha256(str(run_path).encode()).hexdigest()[:8]

    if experiment_name is None:
        experiment_name = run_path.parent.name if run_path.is_file() else run_path.name

    # Parse data
    filters = {
        'min_qscore': min_qscore,
        'require_pass': require_pass,
        'min_length': min_length,
        'max_reads': max_reads,
    }

    if source_type == 'sequencing_summary':
        hq_reads, lq_reads = parse_sequencing_summary(
            source_path, min_qscore, require_pass, min_length, max_reads
        )
    else:
        hq_reads, lq_reads = parse_pod5(source_path, min_qscore, max_reads)

    # Compute statistics
    stats = compute_stats(
        hq_reads, lq_reads,
        experiment_id, experiment_name,
        str(source_path), filters
    )

    # Generate plots
    if generate_plots and output_dir and HAS_MATPLOTLIB:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        safe_name = experiment_name.replace('/', '_').replace(' ', '_')[:50]

        # Main distribution plot
        plot_fine_grained_distribution(
            stats,
            output_dir / f"{safe_name}_readlen_distribution.png",
            dpi=dpi
        )

        # End reason overlay
        if hq_reads:
            plot_end_reason_overlay(
                stats, hq_reads,
                output_dir / f"{safe_name}_readlen_by_endreason.png",
                dpi=dpi
            )

        # HQ vs LQ comparison
        if lq_reads:
            plot_hq_vs_lq_comparison(
                stats, hq_reads, lq_reads,
                output_dir / f"{safe_name}_hq_vs_lq.png",
                dpi=dpi
            )

        # Zoom regions for fine-grained peak analysis
        if stats.hq_reads > 100:
            plot_zoom_regions(
                stats,
                output_dir / f"{safe_name}_zoom_analysis.png",
                dpi=dpi
            )

        # Cumulative distribution with NX markers
        if stats.hq_reads > 100:
            plot_cumulative_distribution(
                stats,
                output_dir / f"{safe_name}_cumulative.png",
                dpi=dpi
            )

    return stats, hq_reads, lq_reads


def analyze_smaseq_batch(
    registry_path: Path = None,
    experiment_paths: List[Path] = None,
    output_dir: Path = None,
    min_qscore: float = DEFAULT_MIN_QSCORE,
    require_pass: bool = DEFAULT_PASSES_FILTERING,
    min_length: int = DEFAULT_MIN_LENGTH,
    max_reads: int = None,
    dpi: int = 300,
) -> List[ReadLengthStats]:
    """
    Analyze multiple SMAseq experiments and generate comparison plots.

    Args:
        registry_path: Path to experiments.yaml registry
        experiment_paths: List of experiment paths (alternative to registry)
        output_dir: Output directory for plots and JSON

    Returns:
        List of ReadLengthStats for all experiments
    """
    all_stats = []

    # Get experiment list
    if registry_path:
        experiments = load_smaseq_experiments(registry_path)
        paths = [(exp.get('location'), exp.get('id'), exp.get('name'))
                 for exp in experiments]
    elif experiment_paths:
        paths = [(str(p), None, None) for p in experiment_paths]
    else:
        raise ValueError("Must provide registry_path or experiment_paths")

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    # Analyze each experiment
    for exp_path, exp_id, exp_name in paths:
        if not exp_path or not Path(exp_path).exists():
            print(f"  [SKIP] Path not found: {exp_path}", file=sys.stderr)
            continue

        try:
            print(f"  [ANALYZE] {exp_name or exp_path}", file=sys.stderr)

            stats, hq_reads, lq_reads = analyze_experiment(
                Path(exp_path),
                experiment_id=exp_id,
                experiment_name=exp_name,
                min_qscore=min_qscore,
                require_pass=require_pass,
                min_length=min_length,
                max_reads=max_reads,
                output_dir=output_dir,
                generate_plots=True,
                dpi=dpi,
            )

            all_stats.append(stats)

            print(f"    HQ reads: {stats.hq_reads:,} | N50: {stats.n50:,} bp | "
                  f"Quality: {stats.quality_status}", file=sys.stderr)

        except Exception as e:
            print(f"  [ERROR] {exp_name or exp_path}: {e}", file=sys.stderr)
            continue

    # Generate comparison plot if multiple experiments
    if len(all_stats) >= 2 and output_dir and HAS_MATPLOTLIB:
        try:
            plot_multi_experiment_comparison(
                all_stats,
                output_dir / "smaseq_comparison.png",
                dpi=dpi
            )
            print(f"\n  [SAVED] Multi-experiment comparison plot", file=sys.stderr)
        except Exception as e:
            print(f"  [WARN] Could not generate comparison plot: {e}", file=sys.stderr)

    return all_stats


# =============================================================================
# CLI Interface
# =============================================================================

def print_summary(stats: ReadLengthStats):
    """Print human-readable summary"""
    print(f"\n{'='*60}")
    print(f"SMAseq Read Length Analysis: {stats.experiment_name}")
    print(f"{'='*60}")
    print(f"Source: {stats.source_file}")
    print(f"Timestamp: {stats.timestamp}")
    print()

    # Quality status
    status_icon = {'OK': '✓', 'CHECK': '⚠', 'FAIL': '✗'}.get(stats.quality_status, '?')
    print(f"Quality Status: {status_icon} {stats.quality_status}")
    print()

    # Read counts
    print("Read Counts:")
    print(f"  Total reads:     {stats.total_reads:>12,}")
    print(f"  HQ reads:        {stats.hq_reads:>12,} ({stats.hq_pct:.1f}%)")
    print(f"  LQ reads:        {stats.lq_reads:>12,}")
    print()

    # Length statistics
    print("Length Statistics (HQ reads):")
    print(f"  Mean length:     {stats.mean_length:>12,.0f} bp")
    print(f"  Median length:   {stats.median_length:>12,.0f} bp")
    print(f"  Std deviation:   {stats.std_length:>12,.0f} bp")
    print(f"  N50:             {stats.n50:>12,} bp (L50: {stats.l50:,})")
    print(f"  N90:             {stats.n90:>12,} bp")
    print(f"  Max length:      {stats.max_length:>12,} bp")
    print()

    # Quality scores
    if stats.mean_qscore > 0:
        print("Quality Scores:")
        print(f"  Mean Q-score:    {stats.mean_qscore:>12.1f}")
        print(f"  Median Q-score:  {stats.median_qscore:>12.1f}")
        print()

    # Fragment distribution
    print("Fragment Size Distribution:")
    for name, bin_data in stats.fragment_bins.items():
        if bin_data.count > 0:
            max_bp = f"{bin_data.max_bp:,}" if bin_data.max_bp < 999999 else "∞"
            print(f"  {name:25s}: {bin_data.count:>10,} reads "
                  f"({bin_data.pct_of_total:>5.1f}%) "
                  f"[{bin_data.min_bp:,}-{max_bp} bp]")
    print()

    # End reason breakdown
    print("End Reason Breakdown:")
    total_er = sum(stats.end_reason_counts.values())
    for er, count in sorted(stats.end_reason_counts.items(), key=lambda x: -x[1]):
        pct = 100 * count / total_er if total_er > 0 else 0
        mean_len = stats.end_reason_mean_lengths.get(er, 0)
        label = END_REASON_LABELS.get(er, er)
        print(f"  {label:30s}: {count:>10,} ({pct:>5.1f}%) "
              f"mean={mean_len:,.0f} bp")
    print()

    # Detected peaks
    if stats.detected_peaks:
        print(f"Detected Peaks: {', '.join(f'{p:,} bp' for p in stats.detected_peaks[:5])}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="SMAseq Fine-Grained Read Length Distribution Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze single experiment
  %(prog)s /path/to/experiment --output-dir ./results

  # Analyze from registry (SMAseq only)
  %(prog)s --registry experiments.yaml --smaseq-only

  # High-quality filtering with custom thresholds
  %(prog)s /path/to/data --min-qscore 15 --min-length 500

  # Generate publication-quality plots
  %(prog)s /path/to/data --dpi 600 --output-dir ./figures
        """
    )

    parser.add_argument('path', nargs='?',
                       help='Experiment path or sequencing_summary.txt')
    parser.add_argument('--registry', '-r', type=Path,
                       help='Path to experiments.yaml registry')
    parser.add_argument('--smaseq-only', action='store_true',
                       help='Only analyze SMAseq experiments from registry')
    parser.add_argument('--output-dir', '-o', type=Path,
                       help='Output directory for plots and JSON')
    parser.add_argument('--json', type=Path,
                       help='Output JSON file for statistics')

    # Quality filters
    filter_group = parser.add_argument_group('Quality Filters')
    filter_group.add_argument('--min-qscore', type=float, default=DEFAULT_MIN_QSCORE,
                             help=f'Minimum Q-score for HQ reads (default: {DEFAULT_MIN_QSCORE})')
    filter_group.add_argument('--no-pass-filter', action='store_true',
                             help='Do not require passes_filtering=True')
    filter_group.add_argument('--min-length', type=int, default=DEFAULT_MIN_LENGTH,
                             help=f'Minimum read length (default: {DEFAULT_MIN_LENGTH})')
    filter_group.add_argument('--max-reads', type=int,
                             help='Maximum reads to process (for quick testing)')

    # Plot options
    plot_group = parser.add_argument_group('Plot Options')
    plot_group.add_argument('--dpi', type=int, default=300,
                           help='Plot resolution (default: 300)')
    plot_group.add_argument('--no-plots', action='store_true',
                           help='Skip plot generation')
    plot_group.add_argument('--xlim', type=int, nargs=2, metavar=('MIN', 'MAX'),
                           help='X-axis limits for plots')

    # Output options
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress progress output')
    parser.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')

    args = parser.parse_args()

    # Validate arguments
    if not args.path and not args.registry:
        parser.error("Must provide experiment path or --registry")

    require_pass = not args.no_pass_filter
    generate_plots = not args.no_plots

    try:
        if args.registry and args.smaseq_only:
            # Batch analysis of SMAseq experiments
            if not args.quiet:
                print(f"Loading SMAseq experiments from {args.registry}...", file=sys.stderr)

            all_stats = analyze_smaseq_batch(
                registry_path=args.registry,
                output_dir=args.output_dir,
                min_qscore=args.min_qscore,
                require_pass=require_pass,
                min_length=args.min_length,
                max_reads=args.max_reads,
                dpi=args.dpi,
            )

            if not args.quiet:
                print(f"\nAnalyzed {len(all_stats)} SMAseq experiments", file=sys.stderr)

            # Output combined JSON
            if args.json:
                output = {
                    'version': VERSION,
                    'timestamp': datetime.utcnow().isoformat() + "Z",
                    'experiments': [s.to_dict() for s in all_stats],
                    'summary': {
                        'total_experiments': len(all_stats),
                        'total_hq_reads': sum(s.hq_reads for s in all_stats),
                        'mean_n50': sum(s.n50 for s in all_stats) / len(all_stats) if all_stats else 0,
                    }
                }
                with open(args.json, 'w') as f:
                    json.dump(output, f, indent=2)
                if not args.quiet:
                    print(f"Saved results to {args.json}", file=sys.stderr)

        else:
            # Single experiment analysis
            exp_path = Path(args.path) if args.path else None

            if args.registry and not exp_path:
                # Load first SMAseq from registry
                experiments = load_smaseq_experiments(args.registry)
                if experiments:
                    exp_path = Path(experiments[0]['location'])

            if not exp_path:
                parser.error("No experiment path specified")

            stats, hq_reads, lq_reads = analyze_experiment(
                exp_path,
                min_qscore=args.min_qscore,
                require_pass=require_pass,
                min_length=args.min_length,
                max_reads=args.max_reads,
                output_dir=args.output_dir,
                generate_plots=generate_plots,
                dpi=args.dpi,
            )

            # Print summary
            if not args.quiet:
                print_summary(stats)

            # Output JSON
            if args.json:
                with open(args.json, 'w') as f:
                    json.dump(stats.to_dict(), f, indent=2)
                if not args.quiet:
                    print(f"Saved results to {args.json}", file=sys.stderr)

            # Print for Pattern B capture
            print(json.dumps({
                'experiment_id': stats.experiment_id,
                'hq_reads': stats.hq_reads,
                'n50': stats.n50,
                'quality_status': stats.quality_status,
            }))

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ImportError as e:
        print(f"Missing dependency: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
