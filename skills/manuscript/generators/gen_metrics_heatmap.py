#!/usr/bin/env python3
"""
Generator: Metrics Heatmap

Creates a heatmap comparing QC metrics across multiple experiments.
Useful for visualizing patterns and outliers in multi-experiment datasets.
"""

import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

# Add bin to path for imports
bin_dir = Path(__file__).parent.parent.parent.parent / 'bin'
sys.path.insert(0, str(bin_dir))


@dataclass
class MetricsHeatmapConfig:
    """Configuration for metrics heatmap"""
    title: str = "QC Metrics Comparison"
    figsize: tuple = (14, 10)
    dpi: int = 300
    cmap: str = "RdYlGn"  # Red (bad) -> Yellow -> Green (good)
    annotate: bool = True
    annotation_format: str = ".2f"
    normalize: bool = True  # Normalize each metric to 0-1
    cluster_rows: bool = False
    cluster_cols: bool = False
    metric_labels: Dict[str, str] = field(default_factory=lambda: {
        "mean_qscore": "Mean Q-Score",
        "median_qscore": "Median Q-Score",
        "n50": "N50 (bp)",
        "mean_length": "Mean Length (bp)",
        "total_reads": "Total Reads",
        "total_bases": "Total Bases",
        "signal_positive_pct": "Signal Positive %",
        "unblock_pct": "Unblock %",
        "pass_rate": "Pass Rate %"
    })
    # Metrics where higher is better (for color scaling)
    higher_is_better: List[str] = field(default_factory=lambda: [
        "mean_qscore", "median_qscore", "n50", "mean_length",
        "total_reads", "total_bases", "signal_positive_pct", "pass_rate"
    ])


def generate_metrics_heatmap(
    experiments: List[Dict[str, Any]],
    output_path: Path,
    metrics: Optional[List[str]] = None,
    config: Optional[MetricsHeatmapConfig] = None,
    format: str = "pdf"
) -> Dict[str, Any]:
    """
    Generate metrics heatmap across experiments.

    Args:
        experiments: List of experiment dicts with 'id' and metric values
        output_path: Path to save the figure
        metrics: List of metric names to include (default: all available)
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
        config = MetricsHeatmapConfig()

    if len(experiments) < 2:
        return {"error": "Need at least 2 experiments for heatmap", "success": False}

    # Determine metrics to show
    if metrics is None:
        # Auto-detect metrics present in experiments
        all_metrics = set()
        for exp in experiments:
            for key in exp.keys():
                if key not in ['id', 'name', 'path', 'unique_id']:
                    all_metrics.add(key)
        metrics = sorted(all_metrics)

    if not metrics:
        return {"error": "No metrics found in experiments", "success": False}

    # Build data matrix
    exp_ids = [exp.get('id', f'exp_{i}')[:20] for i, exp in enumerate(experiments)]
    data = []

    for metric in metrics:
        row = []
        for exp in experiments:
            value = exp.get(metric)
            if value is None:
                row.append(np.nan)
            elif isinstance(value, (int, float)):
                row.append(float(value))
            else:
                row.append(np.nan)
        data.append(row)

    data = np.array(data)

    # Normalize if requested
    if config.normalize:
        normalized = np.zeros_like(data)
        for i, metric in enumerate(metrics):
            row = data[i]
            valid_mask = ~np.isnan(row)
            if np.any(valid_mask):
                min_val = np.nanmin(row)
                max_val = np.nanmax(row)
                if max_val > min_val:
                    normalized[i] = (row - min_val) / (max_val - min_val)
                    # Invert if lower is better
                    if metric not in config.higher_is_better:
                        normalized[i] = 1 - normalized[i]
                else:
                    normalized[i] = 0.5
            else:
                normalized[i] = np.nan
        plot_data = normalized
    else:
        plot_data = data

    # Create figure
    fig, ax = plt.subplots(figsize=config.figsize)

    # Create heatmap
    im = ax.imshow(plot_data, cmap=config.cmap, aspect='auto', vmin=0, vmax=1)

    # Set ticks
    ax.set_xticks(np.arange(len(exp_ids)))
    ax.set_yticks(np.arange(len(metrics)))
    ax.set_xticklabels(exp_ids, rotation=45, ha='right')
    ax.set_yticklabels([config.metric_labels.get(m, m) for m in metrics])

    # Annotate with actual values
    if config.annotate:
        for i in range(len(metrics)):
            for j in range(len(experiments)):
                value = data[i, j]
                if not np.isnan(value):
                    # Format based on magnitude
                    if value >= 1e9:
                        text = f'{value/1e9:.1f}G'
                    elif value >= 1e6:
                        text = f'{value/1e6:.1f}M'
                    elif value >= 1e3:
                        text = f'{value/1e3:.1f}K'
                    elif value >= 100:
                        text = f'{value:.0f}'
                    elif value >= 1:
                        text = f'{value:.1f}'
                    else:
                        text = f'{value:.3f}'

                    # Determine text color based on background
                    bg_val = plot_data[i, j]
                    text_color = 'white' if 0.3 < bg_val < 0.7 else 'black'

                    ax.text(j, i, text, ha='center', va='center',
                            color=text_color, fontsize=8)

    ax.set_title(config.title, fontsize=14, fontweight='bold', pad=15)

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label('Relative Performance (normalized)' if config.normalize else 'Value',
                   fontsize=10)

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
            "normalized": config.normalize,
            "dpi": config.dpi
        },
        "data_summary": {
            "num_experiments": len(experiments),
            "num_metrics": len(metrics),
            "metrics": metrics
        }
    }


def generate_from_contexts(contexts: List, output_path: Path, **kwargs):
    """Generate metrics heatmap from list of experiment contexts"""
    experiments = []

    for ctx in contexts:
        exp_data = {'id': getattr(ctx, 'id', 'unknown')}

        stats = getattr(ctx, 'statistics', None)
        if stats:
            for attr in ['total_reads', 'total_bases', 'mean_qscore',
                         'median_qscore', 'n50', 'mean_length', 'pass_reads', 'fail_reads']:
                value = getattr(stats, attr, None)
                if value is not None:
                    exp_data[attr] = value

            # Calculate derived metrics
            if exp_data.get('pass_reads') and exp_data.get('total_reads'):
                exp_data['pass_rate'] = exp_data['pass_reads'] / exp_data['total_reads'] * 100

        end_reasons = getattr(ctx, 'end_reasons', None)
        if end_reasons:
            for attr in ['signal_positive_pct', 'unblock_pct']:
                value = getattr(end_reasons, attr, None)
                if value is not None:
                    exp_data[attr] = value

        experiments.append(exp_data)

    return generate_metrics_heatmap(
        experiments=experiments,
        output_path=output_path,
        **kwargs
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate metrics heatmap")
    parser.add_argument("output", type=Path, help="Output file path")
    parser.add_argument("--format", default="pdf", choices=["pdf", "png", "svg"])
    parser.add_argument("--demo", action="store_true", help="Generate demo heatmap")

    args = parser.parse_args()

    if args.demo:
        import numpy as np
        np.random.seed(42)

        demo_experiments = []
        for i in range(8):
            demo_experiments.append({
                'id': f'EXP-{i+1:03d}',
                'mean_qscore': 18 + np.random.normal(0, 2),
                'median_qscore': 19 + np.random.normal(0, 2),
                'n50': 5000 + np.random.normal(0, 1000),
                'mean_length': 4500 + np.random.normal(0, 800),
                'total_reads': int(4e6 + np.random.normal(0, 1e6)),
                'total_bases': int(18e9 + np.random.normal(0, 5e9)),
                'signal_positive_pct': 50 + np.random.normal(0, 10),
                'unblock_pct': 45 + np.random.normal(0, 8),
                'pass_rate': 90 + np.random.normal(0, 5)
            })

        result = generate_metrics_heatmap(
            experiments=demo_experiments,
            output_path=args.output,
            format=args.format
        )
        print(f"Generated: {result}")
