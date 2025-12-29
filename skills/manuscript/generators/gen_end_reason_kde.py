#!/usr/bin/env python3
"""
Generate KDE plot of read lengths by end reason.

This generator creates a kernel density estimate plot showing the distribution
of read lengths, colored by end reason category (signal_positive, unblock, etc.).

Usage:
    gen_end_reason_kde.py <experiment_id> --output <path> --format <pdf|png>
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "bin"))

try:
    from ont_context import load_experiment_context
    HAS_CONTEXT = True
except ImportError:
    HAS_CONTEXT = False

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def generate_kde_plot(ctx, output_path: Path, format: str = "pdf",
                      dpi: int = 150, figsize: tuple = (10, 6),
                      zoom_panels: int = 0):
    """
    Generate KDE plot from experiment context.

    Args:
        ctx: ExperimentContext object
        output_path: Output file path
        format: Output format (pdf, png)
        dpi: DPI for raster formats
        figsize: Figure size in inches
        zoom_panels: Number of zoom panels (0 = none)

    Returns:
        Path to generated file
    """
    if not HAS_MATPLOTLIB:
        print("Error: matplotlib required for figure generation")
        return None

    # Create figure
    if zoom_panels > 0:
        fig, axes = plt.subplots(1, zoom_panels + 1, figsize=(figsize[0] * (zoom_panels + 1) / 2, figsize[1]))
        ax_main = axes[0]
    else:
        fig, ax_main = plt.subplots(figsize=figsize)

    # Color scheme
    colors = {
        'signal_positive': '#2ecc71',  # Green
        'unblock_mux_change': '#e74c3c',  # Red
        'data_service': '#f39c12',  # Orange
        'other': '#95a5a6',  # Gray
    }

    # Check if we have end reason data
    if ctx.end_reasons:
        # Create bar chart of end reason percentages
        categories = ['Signal\nPositive', 'Unblock/\nMUX Change']
        values = [ctx.end_reasons.signal_positive_pct, ctx.end_reasons.unblock_pct]
        bar_colors = [colors['signal_positive'], colors['unblock_mux_change']]

        bars = ax_main.bar(categories, values, color=bar_colors, edgecolor='black', linewidth=0.5)

        # Add value labels on bars
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax_main.annotate(f'{val:.1f}%',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),
                           textcoords="offset points",
                           ha='center', va='bottom', fontsize=12, fontweight='bold')

        ax_main.set_ylabel("Percentage (%)", fontsize=12)
        ax_main.set_ylim(0, 100)

        # Add quality grade annotation
        if ctx.quality_grade:
            ax_main.annotate(f"Grade: {ctx.quality_grade}",
                           xy=(0.95, 0.95), xycoords='axes fraction',
                           ha='right', va='top', fontsize=14, fontweight='bold',
                           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    else:
        # No data - show placeholder
        ax_main.text(0.5, 0.5, "No end reason data available\n\nRun: ont_experiments.py run end_reasons",
                    ha='center', va='center', transform=ax_main.transAxes,
                    fontsize=14, color='gray')
        ax_main.set_xlim(0, 1)
        ax_main.set_ylim(0, 1)

    # Set title
    ax_main.set_title(f"End Reason Distribution\n{ctx.name}", fontsize=14, fontweight='bold')

    # Add zoom panels if requested
    if zoom_panels > 0 and ctx.statistics:
        # Placeholder for zoom panels
        for i, ax in enumerate(axes[1:], 1):
            ax.text(0.5, 0.5, f"Zoom Panel {i}\n(Requires raw data)",
                   ha='center', va='center', transform=ax.transAxes,
                   fontsize=10, color='gray')
            ax.set_title(f"Detail View {i}")

    # Add metadata annotation
    if ctx.statistics:
        meta_text = f"Total Reads: {ctx.statistics.total_reads:,}"
        fig.text(0.99, 0.01, meta_text, ha='right', va='bottom',
                fontsize=9, color='gray', transform=fig.transFigure)

    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    plt.close()

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate KDE plot of end reasons")
    parser.add_argument("experiment_id", help="Experiment ID")
    parser.add_argument("--output", "-o", required=True, help="Output path")
    parser.add_argument("--format", default="pdf", choices=["pdf", "png"], help="Output format")
    parser.add_argument("--dpi", type=int, default=150, help="DPI for PNG output")
    parser.add_argument("--zoom-panels", type=int, default=0, help="Number of zoom panels")

    args = parser.parse_args()

    if not HAS_CONTEXT:
        print("Error: ont_context module required")
        sys.exit(1)

    ctx = load_experiment_context(args.experiment_id)
    if ctx is None:
        print(f"Error: Experiment not found: {args.experiment_id}")
        sys.exit(1)

    output_path = Path(args.output)
    result = generate_kde_plot(
        ctx, output_path, args.format,
        dpi=args.dpi, zoom_panels=args.zoom_panels
    )

    if result:
        print(f"Generated: {result}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
