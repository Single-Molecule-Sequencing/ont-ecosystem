#!/usr/bin/env python3
"""
Generate multi-experiment comparison plots.

Creates bar charts and box plots comparing metrics across experiments.

Usage:
    gen_comparison_plot.py <exp1> <exp2> ... --output <path> --format <pdf|png>
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


def generate_comparison_plot(contexts, output_path: Path, format: str = "pdf",
                              dpi: int = 150, figsize: tuple = (14, 10)):
    """
    Generate comparison plots from multiple experiment contexts.

    Args:
        contexts: List of ExperimentContext objects
        output_path: Output file path
        format: Output format (pdf, png)
        dpi: DPI for raster formats
        figsize: Figure size in inches

    Returns:
        Path to generated file
    """
    if not HAS_MATPLOTLIB:
        print("Error: matplotlib required for figure generation")
        return None

    if len(contexts) < 2:
        print("Error: Need at least 2 experiments to compare")
        return None

    fig, axes = plt.subplots(2, 2, figsize=figsize)

    names = [ctx.name[:15] for ctx in contexts]
    colors = plt.cm.Set2(np.linspace(0, 1, len(contexts)))

    # 1. Total Reads comparison
    ax1 = axes[0, 0]
    reads = [ctx.statistics.total_reads if ctx.statistics else 0 for ctx in contexts]
    bars = ax1.bar(names, reads, color=colors, edgecolor='black', linewidth=0.5)
    ax1.set_ylabel("Total Reads", fontsize=11)
    ax1.set_title("Read Count Comparison", fontsize=12, fontweight='bold')
    ax1.tick_params(axis='x', rotation=45)
    # Add value labels
    for bar, val in zip(bars, reads):
        if val > 0:
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                    f'{val/1e6:.1f}M', ha='center', va='bottom', fontsize=9)

    # 2. N50 comparison
    ax2 = axes[0, 1]
    n50s = [ctx.statistics.n50 if ctx.statistics else 0 for ctx in contexts]
    bars = ax2.bar(names, n50s, color=colors, edgecolor='black', linewidth=0.5)
    ax2.set_ylabel("N50 (bp)", fontsize=11)
    ax2.set_title("N50 Comparison", fontsize=12, fontweight='bold')
    ax2.tick_params(axis='x', rotation=45)
    for bar, val in zip(bars, n50s):
        if val > 0:
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                    f'{val:,}', ha='center', va='bottom', fontsize=9)

    # 3. Quality Score comparison
    ax3 = axes[1, 0]
    qscores = [ctx.statistics.mean_qscore if ctx.statistics else 0 for ctx in contexts]
    bars = ax3.bar(names, qscores, color=colors, edgecolor='black', linewidth=0.5)
    ax3.set_ylabel("Mean Q-Score", fontsize=11)
    ax3.set_title("Quality Score Comparison", fontsize=12, fontweight='bold')
    ax3.tick_params(axis='x', rotation=45)
    ax3.axhline(y=10, color='orange', linestyle='--', alpha=0.5, label='Q10')
    ax3.axhline(y=20, color='green', linestyle='--', alpha=0.5, label='Q20')
    ax3.legend(fontsize=8, loc='upper right')
    for bar, val in zip(bars, qscores):
        if val > 0:
            ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                    f'{val:.1f}', ha='center', va='bottom', fontsize=9)

    # 4. Signal Positive % comparison
    ax4 = axes[1, 1]
    sp_pcts = [ctx.end_reasons.signal_positive_pct if ctx.end_reasons else 0 for ctx in contexts]
    bars = ax4.bar(names, sp_pcts, color=colors, edgecolor='black', linewidth=0.5)
    ax4.set_ylabel("Signal Positive (%)", fontsize=11)
    ax4.set_title("End Reason Comparison", fontsize=12, fontweight='bold')
    ax4.tick_params(axis='x', rotation=45)
    ax4.set_ylim(0, 100)
    ax4.axhline(y=50, color='gray', linestyle=':', alpha=0.5)
    for bar, val in zip(bars, sp_pcts):
        if val > 0:
            ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                    f'{val:.1f}%', ha='center', va='bottom', fontsize=9)

    fig.suptitle(f"Experiment Comparison ({len(contexts)} experiments)",
                 fontsize=14, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    plt.close()

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate experiment comparison plots")
    parser.add_argument("experiment_ids", nargs="+", help="Experiment IDs to compare")
    parser.add_argument("--output", "-o", required=True, help="Output path")
    parser.add_argument("--format", default="pdf", choices=["pdf", "png"], help="Output format")
    parser.add_argument("--dpi", type=int, default=150, help="DPI for PNG output")

    args = parser.parse_args()

    if not HAS_CONTEXT:
        print("Error: ont_context module required")
        sys.exit(1)

    contexts = []
    for exp_id in args.experiment_ids:
        ctx = load_experiment_context(exp_id)
        if ctx is None:
            print(f"Warning: Experiment not found: {exp_id}")
            continue
        contexts.append(ctx)

    if len(contexts) < 2:
        print("Error: Need at least 2 experiments to compare")
        sys.exit(1)

    output_path = Path(args.output)
    result = generate_comparison_plot(
        contexts, output_path, args.format,
        dpi=args.dpi
    )

    if result:
        print(f"Generated: {result}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
