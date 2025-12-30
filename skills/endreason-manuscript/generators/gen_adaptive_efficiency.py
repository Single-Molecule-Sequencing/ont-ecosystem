#!/usr/bin/env python3
"""
Generate adaptive sampling efficiency comparison figure.

Creates a 2x2 panel figure comparing adaptive vs non-adaptive experiments:
(A) Signal positive % grouped bar chart
(B) Unblock % violin/box plot
(C) Scatter of signal_positive vs total_reads
(D) Stacked bar of end-reason breakdown

Usage:
    gen_adaptive_efficiency.py --input merged_data.json --output fig.pdf
"""

import argparse
import json
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# Optional imports
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    HAS_MATPLOTLIB = True
except (ImportError, AttributeError):
    HAS_MATPLOTLIB = False


# =============================================================================
# Configuration
# =============================================================================

# Color schemes
COLORS = {
    "adaptive": "#E74C3C",      # Red
    "non_adaptive": "#3498DB",  # Blue
    "signal_positive": "#27AE60",  # Green
    "unblock_mux_change": "#E74C3C",  # Red
    "data_service_unblock": "#F39C12",  # Orange
    "mux_change": "#9B59B6",   # Purple
    "signal_negative": "#7F8C8D",  # Gray
    "other": "#BDC3C7",        # Light gray
}

# End-reason display names
END_REASON_LABELS = {
    "signal_positive": "Signal Positive",
    "unblock_mux_change": "Unblock (MUX)",
    "data_service_unblock_mux_change": "Unblock (Data Svc)",
    "mux_change": "MUX Change",
    "signal_negative": "Signal Negative",
    "other": "Other",
}


# =============================================================================
# Data Loading
# =============================================================================

@dataclass
class ExperimentData:
    """Simplified experiment data for plotting."""
    experiment_id: str
    name: str
    source: str
    is_adaptive: bool
    total_reads: int
    signal_positive_pct: float
    unblock_pct: float
    data_service_pct: float
    rejection_rate: float
    quality_grade: str
    # Per-category percentages for stacked bar
    end_reason_pcts: Dict[str, float]


def load_merged_data(input_path: Path) -> List[ExperimentData]:
    """Load merged experiment data from JSON."""
    with open(input_path) as f:
        data = json.load(f)

    experiments = []
    for exp in data.get("experiments", []):
        end_reasons = exp.get("end_reasons")
        if not end_reasons:
            continue

        total = end_reasons.get("total_reads", 0)
        if total == 0:
            continue

        # Calculate percentages
        def pct(key):
            return end_reasons.get(key, 0) / total * 100 if total > 0 else 0

        experiments.append(ExperimentData(
            experiment_id=end_reasons.get("experiment_id", ""),
            name=exp.get("metadata", {}).get("name", "")[:20],
            source=end_reasons.get("source", "unknown"),
            is_adaptive=end_reasons.get("is_adaptive", False),
            total_reads=total,
            signal_positive_pct=end_reasons.get("signal_positive_pct", 0),
            unblock_pct=end_reasons.get("unblock_pct", 0),
            data_service_pct=end_reasons.get("data_service_pct", 0),
            rejection_rate=end_reasons.get("rejection_rate", 0),
            quality_grade=end_reasons.get("quality_grade", "D"),
            end_reason_pcts={
                "signal_positive": pct("signal_positive"),
                "unblock_mux_change": pct("unblock_mux_change"),
                "data_service_unblock_mux_change": pct("data_service_unblock_mux_change"),
                "mux_change": pct("mux_change"),
                "signal_negative": pct("signal_negative"),
                "other": pct("other") + pct("unknown"),
            },
        ))

    return experiments


# =============================================================================
# Figure Generation
# =============================================================================

def generate_adaptive_efficiency(
    experiments: List[ExperimentData],
    output_path: Path,
    format: str = "pdf",
    dpi: int = 150,
    figsize: tuple = (14, 10),
) -> Optional[Path]:
    """
    Generate adaptive efficiency comparison figure.

    Args:
        experiments: List of ExperimentData objects
        output_path: Output file path
        format: Output format (pdf, png)
        dpi: DPI for raster formats
        figsize: Figure size in inches

    Returns:
        Path to generated file or None on failure
    """
    if not HAS_MATPLOTLIB:
        print("Error: matplotlib required for figure generation")
        return None

    if not experiments:
        print("Error: No experiment data provided")
        return None

    # Separate adaptive vs non-adaptive
    adaptive = [e for e in experiments if e.is_adaptive]
    non_adaptive = [e for e in experiments if not e.is_adaptive]

    print(f"  Adaptive experiments: {len(adaptive)}")
    print(f"  Non-adaptive experiments: {len(non_adaptive)}")

    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=figsize)

    # ==========================================================================
    # Panel A: Signal Positive % grouped bar chart
    # ==========================================================================
    ax1 = axes[0, 0]

    # Calculate means
    adaptive_sp = [e.signal_positive_pct for e in adaptive] if adaptive else [0]
    non_adaptive_sp = [e.signal_positive_pct for e in non_adaptive] if non_adaptive else [0]

    categories = ["Adaptive", "Non-Adaptive"]
    means = [np.mean(adaptive_sp) if adaptive_sp else 0,
             np.mean(non_adaptive_sp) if non_adaptive_sp else 0]
    stds = [np.std(adaptive_sp) if len(adaptive_sp) > 1 else 0,
            np.std(non_adaptive_sp) if len(non_adaptive_sp) > 1 else 0]

    x = np.arange(len(categories))
    bars = ax1.bar(x, means, yerr=stds, capsize=5,
                   color=[COLORS["adaptive"], COLORS["non_adaptive"]],
                   edgecolor='black', linewidth=0.5)

    ax1.set_ylabel("Signal Positive (%)", fontsize=11)
    ax1.set_title("A. Signal Positive Rate", fontsize=12, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories)
    ax1.set_ylim(0, 100)

    # Add threshold lines
    ax1.axhline(y=75, color='orange', linestyle='--', alpha=0.5, label='QC Threshold (75%)')
    ax1.axhline(y=95, color='green', linestyle='--', alpha=0.5, label='Excellent (95%)')
    ax1.legend(fontsize=8, loc='lower right')

    # Add value labels
    for bar, mean, std in zip(bars, means, stds):
        if mean > 0:
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + std + 1,
                    f'{mean:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Add sample size
    ax1.text(0, -10, f'n={len(adaptive)}', ha='center', fontsize=9)
    ax1.text(1, -10, f'n={len(non_adaptive)}', ha='center', fontsize=9)

    # ==========================================================================
    # Panel B: Unblock % box plot
    # ==========================================================================
    ax2 = axes[0, 1]

    data_to_plot = []
    labels = []
    colors_box = []

    if adaptive:
        data_to_plot.append([e.unblock_pct for e in adaptive])
        labels.append("Adaptive")
        colors_box.append(COLORS["adaptive"])

    if non_adaptive:
        data_to_plot.append([e.unblock_pct for e in non_adaptive])
        labels.append("Non-Adaptive")
        colors_box.append(COLORS["non_adaptive"])

    if data_to_plot:
        bp = ax2.boxplot(data_to_plot, labels=labels, patch_artist=True)
        for patch, color in zip(bp['boxes'], colors_box):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

    ax2.set_ylabel("Unblock Rate (%)", fontsize=11)
    ax2.set_title("B. Unblock Rate Distribution", fontsize=12, fontweight='bold')

    # Add threshold lines
    ax2.axhline(y=5, color='green', linestyle='--', alpha=0.5, label='Grade B (≤5%)')
    ax2.axhline(y=10, color='orange', linestyle='--', alpha=0.5, label='Grade C (≤10%)')
    ax2.legend(fontsize=8, loc='upper right')

    # ==========================================================================
    # Panel C: Scatter of signal_positive vs total_reads
    # ==========================================================================
    ax3 = axes[1, 0]

    if adaptive:
        reads_a = [e.total_reads / 1e6 for e in adaptive]  # Convert to millions
        sp_a = [e.signal_positive_pct for e in adaptive]
        ax3.scatter(reads_a, sp_a, c=COLORS["adaptive"], s=80, alpha=0.7,
                   edgecolors='black', linewidth=0.5, label='Adaptive')

    if non_adaptive:
        reads_na = [e.total_reads / 1e6 for e in non_adaptive]
        sp_na = [e.signal_positive_pct for e in non_adaptive]
        ax3.scatter(reads_na, sp_na, c=COLORS["non_adaptive"], s=80, alpha=0.7,
                   edgecolors='black', linewidth=0.5, label='Non-Adaptive')

    ax3.set_xlabel("Total Reads (millions)", fontsize=11)
    ax3.set_ylabel("Signal Positive (%)", fontsize=11)
    ax3.set_title("C. Signal Positive vs. Throughput", fontsize=12, fontweight='bold')
    ax3.set_ylim(0, 100)
    ax3.legend(fontsize=9)

    # Add quality threshold
    ax3.axhline(y=75, color='orange', linestyle='--', alpha=0.5)

    # ==========================================================================
    # Panel D: Stacked bar of end-reason breakdown (top N experiments)
    # ==========================================================================
    ax4 = axes[1, 1]

    # Select top experiments (by total reads) for visualization
    sorted_exps = sorted(experiments, key=lambda x: x.total_reads, reverse=True)
    top_exps = sorted_exps[:min(10, len(sorted_exps))]

    if top_exps:
        names = [e.name for e in top_exps]
        x = np.arange(len(names))
        width = 0.7

        # Stack categories
        bottom = np.zeros(len(top_exps))
        categories_order = ["signal_positive", "unblock_mux_change",
                           "data_service_unblock_mux_change", "mux_change",
                           "signal_negative", "other"]

        for category in categories_order:
            values = [e.end_reason_pcts.get(category, 0) for e in top_exps]
            color = COLORS.get(category.replace("_unblock_mux_change", "_unblock"),
                              COLORS.get("other", "#BDC3C7"))
            label = END_REASON_LABELS.get(category, category)
            ax4.bar(x, values, width, bottom=bottom, label=label, color=color,
                   edgecolor='white', linewidth=0.5)
            bottom += values

        ax4.set_ylabel("Percentage (%)", fontsize=11)
        ax4.set_title("D. End-Reason Breakdown (Top 10 by reads)", fontsize=12, fontweight='bold')
        ax4.set_xticks(x)
        ax4.set_xticklabels(names, rotation=45, ha='right', fontsize=8)
        ax4.set_ylim(0, 100)
        ax4.legend(fontsize=7, loc='upper right', ncol=2)

        # Mark adaptive experiments
        for i, exp in enumerate(top_exps):
            if exp.is_adaptive:
                ax4.annotate('A', (i, 2), ha='center', fontsize=8,
                           color='white', fontweight='bold')

    # ==========================================================================
    # Final touches
    # ==========================================================================
    fig.suptitle("Adaptive Sampling Efficiency Analysis",
                 fontsize=14, fontweight='bold', y=1.02)

    plt.tight_layout()

    # Save
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', format=format)
    plt.close()

    print(f"  Generated: {output_path}")
    return output_path


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate adaptive sampling efficiency comparison figure"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Input JSON file with merged experiment data",
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output file path",
    )
    parser.add_argument(
        "--format", "-f",
        default="pdf",
        choices=["pdf", "png", "svg"],
        help="Output format (default: pdf)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="DPI for raster formats (default: 150)",
    )

    args = parser.parse_args()

    if not HAS_MATPLOTLIB:
        print("Error: matplotlib is required for figure generation")
        print("Install with: pip install matplotlib numpy")
        sys.exit(1)

    # Load data
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    experiments = load_merged_data(input_path)
    if not experiments:
        print("Error: No valid experiment data found")
        sys.exit(1)

    print(f"Loaded {len(experiments)} experiments")

    # Generate figure
    output_path = generate_adaptive_efficiency(
        experiments,
        Path(args.output),
        format=args.format,
        dpi=args.dpi,
    )

    if output_path:
        print(f"Success: {output_path}")
        sys.exit(0)
    else:
        print("Error: Figure generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
