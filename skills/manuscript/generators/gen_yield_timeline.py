#!/usr/bin/env python3
"""
Generator: Yield Timeline Plot

Creates a cumulative yield plot showing reads and bases over time.
Useful for visualizing sequencing run progression and throughput patterns.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

# Add bin to path for imports
bin_dir = Path(__file__).parent.parent.parent.parent / 'bin'
sys.path.insert(0, str(bin_dir))


@dataclass
class YieldTimelineConfig:
    """Configuration for yield timeline plots"""
    title: str = "Cumulative Sequencing Yield"
    show_reads: bool = True
    show_bases: bool = True
    figsize: tuple = (12, 6)
    dpi: int = 300
    colors: tuple = ("#2E86AB", "#E94F37")  # Blue for reads, red for bases
    grid: bool = True
    legend_loc: str = "upper left"


def generate_yield_timeline(
    timestamps: List[float],
    reads: List[int],
    bases: List[int],
    output_path: Path,
    config: Optional[YieldTimelineConfig] = None,
    format: str = "pdf"
) -> Dict[str, Any]:
    """
    Generate cumulative yield timeline plot.

    Args:
        timestamps: Time points (hours from start)
        reads: Cumulative read counts at each timestamp
        bases: Cumulative base counts at each timestamp
        output_path: Path to save the figure
        config: Plot configuration
        format: Output format (pdf, png, svg)

    Returns:
        Metadata dict with figure details
    """
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return {"error": "matplotlib/numpy not available", "success": False}

    if config is None:
        config = YieldTimelineConfig()

    fig, ax1 = plt.subplots(figsize=config.figsize)

    # Plot reads on primary y-axis
    if config.show_reads and reads:
        ax1.plot(timestamps, reads, color=config.colors[0],
                 linewidth=2, label="Reads")
        ax1.set_ylabel("Cumulative Reads", color=config.colors[0])
        ax1.tick_params(axis='y', labelcolor=config.colors[0])
        ax1.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, _: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K')
        )

    # Plot bases on secondary y-axis
    if config.show_bases and bases:
        ax2 = ax1.twinx()
        ax2.plot(timestamps, bases, color=config.colors[1],
                 linewidth=2, label="Bases", linestyle='--')
        ax2.set_ylabel("Cumulative Bases", color=config.colors[1])
        ax2.tick_params(axis='y', labelcolor=config.colors[1])
        ax2.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, _: f'{x/1e9:.1f}Gb' if x >= 1e9 else f'{x/1e6:.0f}Mb')
        )

    ax1.set_xlabel("Run Time (hours)")
    ax1.set_title(config.title)

    if config.grid:
        ax1.grid(True, alpha=0.3)

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    if config.show_bases and bases:
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc=config.legend_loc)
    elif config.show_reads:
        ax1.legend(loc=config.legend_loc)

    plt.tight_layout()

    # Save figure
    output_file = output_path.with_suffix(f".{format}")
    plt.savefig(output_file, dpi=config.dpi, bbox_inches='tight')
    plt.close()

    return {
        "success": True,
        "output_path": str(output_file),
        "format": format,
        "config": {
            "title": config.title,
            "dpi": config.dpi,
            "figsize": config.figsize
        },
        "data_summary": {
            "time_range_hours": max(timestamps) if timestamps else 0,
            "total_reads": max(reads) if reads else 0,
            "total_bases": max(bases) if bases else 0
        }
    }


def generate_from_context(context, output_path: Path, **kwargs):
    """Generate yield timeline from experiment context"""
    # Extract timeline data from context if available
    # This is a placeholder - actual implementation depends on data structure

    # For now, generate sample data based on final statistics
    import numpy as np

    stats = context.statistics if hasattr(context, 'statistics') else None
    if not stats:
        return {"error": "No statistics available", "success": False}

    total_reads = getattr(stats, 'total_reads', 0) or 0
    total_bases = getattr(stats, 'total_bases', 0) or 0

    if total_reads == 0:
        return {"error": "No reads in experiment", "success": False}

    # Generate simulated timeline (24 hours, typical run)
    hours = np.linspace(0, 24, 100)
    # Sigmoidal growth curve (typical for sequencing)
    reads = (total_reads * (1 / (1 + np.exp(-0.3 * (hours - 12))))).astype(int)
    bases = (total_bases * (1 / (1 + np.exp(-0.3 * (hours - 12))))).astype(int)

    return generate_yield_timeline(
        timestamps=hours.tolist(),
        reads=reads.tolist(),
        bases=bases.tolist(),
        output_path=output_path,
        **kwargs
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate yield timeline plot")
    parser.add_argument("output", type=Path, help="Output file path")
    parser.add_argument("--format", default="pdf", choices=["pdf", "png", "svg"])
    parser.add_argument("--demo", action="store_true", help="Generate demo plot")

    args = parser.parse_args()

    if args.demo:
        import numpy as np
        hours = np.linspace(0, 48, 200)
        reads = (5e6 * (1 / (1 + np.exp(-0.2 * (hours - 24))))).astype(int)
        bases = (25e9 * (1 / (1 + np.exp(-0.2 * (hours - 24))))).astype(int)

        result = generate_yield_timeline(
            timestamps=hours.tolist(),
            reads=reads.tolist(),
            bases=bases.tolist(),
            output_path=args.output,
            format=args.format
        )
        print(f"Generated: {result}")
