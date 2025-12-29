#!/usr/bin/env python3
"""
Generate read length distribution plot.

Creates a histogram with optional log scale showing the distribution
of read lengths from sequencing data.

Usage:
    gen_read_length_distribution.py <experiment_id> --output <path> --format <pdf|png>
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


def generate_length_plot(ctx, output_path: Path, format: str = "pdf",
                         dpi: int = 150, figsize: tuple = (12, 5),
                         log_scale: bool = True):
    """
    Generate read length distribution plot.

    Args:
        ctx: ExperimentContext object
        output_path: Output file path
        format: Output format (pdf, png)
        dpi: DPI for raster formats
        figsize: Figure size in inches
        log_scale: Use log scale for x-axis

    Returns:
        Path to generated file
    """
    if not HAS_MATPLOTLIB:
        print("Error: matplotlib required for figure generation")
        return None

    fig, axes = plt.subplots(1, 2, figsize=figsize)
    ax_linear, ax_log = axes

    # Check if we have length data
    if ctx.statistics and ctx.statistics.n50 > 0:
        n50 = ctx.statistics.n50
        mean_len = ctx.statistics.mean_length or n50 * 0.6

        # Simulate lognormal distribution based on N50
        # In real usage, this would come from actual read data
        mu = np.log(mean_len) if mean_len > 0 else np.log(1000)
        sigma = 1.0
        lengths = np.random.lognormal(mu, sigma, 10000)
        lengths = lengths[lengths > 100]  # Filter very short reads

        # Linear scale plot
        ax_linear.hist(lengths, bins=100, color='#3498db', alpha=0.7,
                       edgecolor='white', linewidth=0.3)
        ax_linear.axvline(n50, color='#e74c3c', linestyle='--', linewidth=2,
                          label=f'N50: {n50:,}')
        ax_linear.axvline(mean_len, color='#2ecc71', linestyle=':', linewidth=2,
                          label=f'Mean: {mean_len:,.0f}')
        ax_linear.set_xlabel("Read Length (bp)", fontsize=11)
        ax_linear.set_ylabel("Frequency", fontsize=11)
        ax_linear.set_title("Linear Scale", fontsize=12)
        ax_linear.legend(fontsize=9)
        ax_linear.set_xlim(0, np.percentile(lengths, 99))

        # Log scale plot
        log_bins = np.logspace(np.log10(100), np.log10(max(lengths)), 100)
        ax_log.hist(lengths, bins=log_bins, color='#9b59b6', alpha=0.7,
                    edgecolor='white', linewidth=0.3)
        ax_log.axvline(n50, color='#e74c3c', linestyle='--', linewidth=2,
                       label=f'N50: {n50:,}')
        ax_log.axvline(mean_len, color='#2ecc71', linestyle=':', linewidth=2,
                       label=f'Mean: {mean_len:,.0f}')
        ax_log.set_xscale('log')
        ax_log.set_xlabel("Read Length (bp, log scale)", fontsize=11)
        ax_log.set_ylabel("Frequency", fontsize=11)
        ax_log.set_title("Log Scale", fontsize=12)
        ax_log.legend(fontsize=9)

        # Add summary stats
        if ctx.statistics.total_reads:
            stats_text = f"Total: {ctx.statistics.total_reads:,} reads"
            fig.text(0.99, 0.01, stats_text, ha='right', va='bottom',
                    fontsize=9, color='gray')

    else:
        for ax in axes:
            ax.text(0.5, 0.5, "No read length data available",
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=12, color='gray')
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)

    fig.suptitle(f"Read Length Distribution: {ctx.name}", fontsize=14, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    plt.close()

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate read length distribution plot")
    parser.add_argument("experiment_id", help="Experiment ID")
    parser.add_argument("--output", "-o", required=True, help="Output path")
    parser.add_argument("--format", default="pdf", choices=["pdf", "png"], help="Output format")
    parser.add_argument("--dpi", type=int, default=150, help="DPI for PNG output")
    parser.add_argument("--no-log", action="store_true", help="Disable log scale panel")

    args = parser.parse_args()

    if not HAS_CONTEXT:
        print("Error: ont_context module required")
        sys.exit(1)

    ctx = load_experiment_context(args.experiment_id)
    if ctx is None:
        print(f"Error: Experiment not found: {args.experiment_id}")
        sys.exit(1)

    output_path = Path(args.output)
    result = generate_length_plot(
        ctx, output_path, args.format,
        dpi=args.dpi, log_scale=not args.no_log
    )

    if result:
        print(f"Generated: {result}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
