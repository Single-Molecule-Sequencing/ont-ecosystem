#!/usr/bin/env python3
"""
Generator: N50 Bar Plot

Creates a bar chart comparing N50 values across experiments.
Essential for comparing read length distributions in long-read sequencing.
"""

import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple

# Add bin to path for imports
bin_dir = Path(__file__).parent.parent.parent.parent / 'bin'
sys.path.insert(0, str(bin_dir))


@dataclass
class N50BarPlotConfig:
    """Configuration for N50 bar plots"""
    title: str = "Read Length N50 Comparison"
    figsize: tuple = (12, 6)
    dpi: int = 300
    color: str = "#2E86AB"
    highlight_color: str = "#E94F37"
    show_values: bool = True
    show_mean_line: bool = True
    show_thresholds: bool = True
    threshold_lines: Dict[str, Tuple[int, str]] = field(default_factory=lambda: {
        "Short reads": (1000, "#FF6B6B"),
        "Standard": (5000, "#FFE66D"),
        "Ultra-long": (10000, "#4ECDC4")
    })
    sort_by: str = "value"  # "value", "name", or "none"
    horizontal: bool = False
    error_bars: bool = False


def generate_n50_barplot(
    experiments: List[Dict[str, Any]],
    output_path: Path,
    config: Optional[N50BarPlotConfig] = None,
    format: str = "pdf"
) -> Dict[str, Any]:
    """
    Generate N50 bar plot across experiments.

    Args:
        experiments: List of dicts with 'id' and 'n50' keys
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
        config = N50BarPlotConfig()

    # Filter experiments with valid N50
    valid_exps = [exp for exp in experiments if exp.get('n50') is not None]

    if not valid_exps:
        return {"error": "No experiments with N50 data", "success": False}

    # Sort experiments
    if config.sort_by == "value":
        valid_exps = sorted(valid_exps, key=lambda x: x['n50'], reverse=True)
    elif config.sort_by == "name":
        valid_exps = sorted(valid_exps, key=lambda x: x.get('id', ''))

    # Extract data
    labels = [exp.get('id', f'exp_{i}')[:15] for i, exp in enumerate(valid_exps)]
    n50_values = [exp['n50'] for exp in valid_exps]
    mean_n50 = np.mean(n50_values)

    # Create figure
    fig, ax = plt.subplots(figsize=config.figsize)

    # Create bars
    x = np.arange(len(labels))
    bar_width = 0.7

    if config.horizontal:
        bars = ax.barh(x, n50_values, height=bar_width, color=config.color,
                       edgecolor='white', linewidth=0.5)
        ax.set_yticks(x)
        ax.set_yticklabels(labels)
        ax.set_xlabel('N50 (bp)')
        ax.invert_yaxis()
    else:
        bars = ax.bar(x, n50_values, width=bar_width, color=config.color,
                      edgecolor='white', linewidth=0.5)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.set_ylabel('N50 (bp)')

    # Highlight best N50
    best_idx = np.argmax(n50_values)
    if config.horizontal:
        bars[best_idx].set_color(config.highlight_color)
    else:
        bars[best_idx].set_color(config.highlight_color)

    # Add value labels
    if config.show_values:
        for i, (bar, val) in enumerate(zip(bars, n50_values)):
            if val >= 1000:
                text = f'{val/1000:.1f}kb'
            else:
                text = f'{val:.0f}'

            if config.horizontal:
                ax.text(bar.get_width() + max(n50_values) * 0.02, bar.get_y() + bar.get_height()/2,
                        text, va='center', fontsize=9)
            else:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(n50_values) * 0.02,
                        text, ha='center', va='bottom', fontsize=9)

    # Add mean line
    if config.show_mean_line:
        if config.horizontal:
            ax.axvline(x=mean_n50, color='gray', linestyle='--', linewidth=1.5,
                       label=f'Mean: {mean_n50/1000:.1f}kb')
        else:
            ax.axhline(y=mean_n50, color='gray', linestyle='--', linewidth=1.5,
                       label=f'Mean: {mean_n50/1000:.1f}kb')

    # Add threshold lines
    if config.show_thresholds:
        max_val = max(n50_values)
        for label, (threshold, color) in config.threshold_lines.items():
            if threshold <= max_val * 1.5:  # Only show if within range
                if config.horizontal:
                    ax.axvline(x=threshold, color=color, linestyle=':', alpha=0.7,
                               linewidth=1)
                    ax.text(threshold, -0.3, f'{label}\n({threshold/1000:.0f}kb)',
                            ha='center', va='top', fontsize=8, color=color)
                else:
                    ax.axhline(y=threshold, color=color, linestyle=':', alpha=0.7,
                               linewidth=1)
                    ax.text(len(labels) - 0.5, threshold, f'  {label} ({threshold/1000:.0f}kb)',
                            ha='left', va='center', fontsize=8, color=color)

    ax.set_title(config.title, fontsize=14, fontweight='bold', pad=15)

    if config.show_mean_line:
        ax.legend(loc='upper right' if not config.horizontal else 'lower right')

    # Add grid
    if config.horizontal:
        ax.xaxis.grid(True, alpha=0.3)
    else:
        ax.yaxis.grid(True, alpha=0.3)

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
            "sort_by": config.sort_by
        },
        "data_summary": {
            "num_experiments": len(valid_exps),
            "mean_n50": mean_n50,
            "max_n50": max(n50_values),
            "min_n50": min(n50_values),
            "best_experiment": valid_exps[best_idx].get('id')
        }
    }


def generate_from_contexts(contexts: List, output_path: Path, **kwargs):
    """Generate N50 bar plot from list of experiment contexts"""
    experiments = []

    for ctx in contexts:
        exp_data = {'id': getattr(ctx, 'id', 'unknown')}

        stats = getattr(ctx, 'statistics', None)
        if stats:
            n50 = getattr(stats, 'n50', None)
            if n50 is not None:
                exp_data['n50'] = n50
                experiments.append(exp_data)

    return generate_n50_barplot(
        experiments=experiments,
        output_path=output_path,
        **kwargs
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate N50 bar plot")
    parser.add_argument("output", type=Path, help="Output file path")
    parser.add_argument("--format", default="pdf", choices=["pdf", "png", "svg"])
    parser.add_argument("--horizontal", action="store_true", help="Horizontal bars")
    parser.add_argument("--demo", action="store_true", help="Generate demo plot")

    args = parser.parse_args()

    if args.demo:
        import numpy as np
        np.random.seed(42)

        demo_experiments = [
            {'id': 'GIAB-HG002', 'n50': 8500},
            {'id': 'CYP2D6-001', 'n50': 5200},
            {'id': 'CYP2D6-002', 'n50': 5800},
            {'id': 'AS-Capture', 'n50': 3200},
            {'id': 'UltraLong-1', 'n50': 12500},
            {'id': 'FastMode-1', 'n50': 2100},
            {'id': 'PromethION', 'n50': 9800},
            {'id': 'MinION-Std', 'n50': 4800}
        ]

        config = N50BarPlotConfig(horizontal=args.horizontal)
        result = generate_n50_barplot(
            experiments=demo_experiments,
            output_path=args.output,
            config=config,
            format=args.format
        )
        print(f"Generated: {result}")
