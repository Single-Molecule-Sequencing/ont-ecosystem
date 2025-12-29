#!/usr/bin/env python3
"""
Generator: End Reason Pie Chart

Creates a pie or donut chart showing the distribution of read end reasons.
Provides clear visualization of signal positive vs unblock ratios.
"""

import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

# Add bin to path for imports
bin_dir = Path(__file__).parent.parent.parent.parent / 'bin'
sys.path.insert(0, str(bin_dir))


@dataclass
class EndReasonPieConfig:
    """Configuration for end reason pie charts"""
    title: str = "Read End Reason Distribution"
    figsize: tuple = (10, 8)
    dpi: int = 300
    style: str = "donut"  # "pie" or "donut"
    donut_ratio: float = 0.6
    colors: Dict[str, str] = field(default_factory=lambda: {
        "signal_positive": "#2E86AB",
        "unblock_mux_change": "#E94F37",
        "data_service_unblock_mux_change": "#F6AE2D",
        "mux_change": "#86BA90",
        "other": "#8B8B8B"
    })
    explode_threshold: float = 0.05  # Explode slices < 5%
    show_percentages: bool = True
    show_counts: bool = True
    legend_loc: str = "lower right"


# Friendly names for end reasons
END_REASON_LABELS = {
    "signal_positive": "Signal Positive\n(Natural End)",
    "unblock_mux_change": "Unblock\n(Adaptive Sampling)",
    "data_service_unblock_mux_change": "Data Service\nUnblock",
    "mux_change": "Mux Change",
    "other": "Other"
}


def generate_end_reason_pie(
    end_reasons: Dict[str, int],
    output_path: Path,
    config: Optional[EndReasonPieConfig] = None,
    format: str = "pdf"
) -> Dict[str, Any]:
    """
    Generate end reason pie/donut chart.

    Args:
        end_reasons: Dict mapping end reason to count
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
        config = EndReasonPieConfig()

    # Filter and sort end reasons
    total = sum(end_reasons.values())
    if total == 0:
        return {"error": "No end reason data", "success": False}

    # Consolidate small categories into "other"
    consolidated = {}
    other_count = 0
    for reason, count in end_reasons.items():
        pct = count / total
        if pct < 0.01:  # Less than 1%
            other_count += count
        else:
            consolidated[reason] = count

    if other_count > 0:
        consolidated["other"] = consolidated.get("other", 0) + other_count

    # Sort by count (descending)
    sorted_reasons = sorted(consolidated.items(), key=lambda x: -x[1])

    labels = []
    sizes = []
    colors = []
    explode = []

    for reason, count in sorted_reasons:
        pct = count / total
        label = END_REASON_LABELS.get(reason, reason.replace("_", " ").title())

        if config.show_counts:
            if count >= 1e6:
                label += f"\n({count/1e6:.1f}M)"
            elif count >= 1e3:
                label += f"\n({count/1e3:.0f}K)"
            else:
                label += f"\n({count})"

        labels.append(label)
        sizes.append(count)
        colors.append(config.colors.get(reason, config.colors.get("other", "#8B8B8B")))
        explode.append(0.05 if pct < config.explode_threshold else 0)

    # Create figure
    fig, ax = plt.subplots(figsize=config.figsize)

    if config.style == "donut":
        # Donut chart
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            colors=colors,
            explode=explode,
            autopct='%1.1f%%' if config.show_percentages else '',
            pctdistance=0.75,
            labeldistance=1.15,
            startangle=90,
            wedgeprops=dict(width=1-config.donut_ratio, edgecolor='white')
        )

        # Add center text
        total_str = f'{total/1e6:.1f}M' if total >= 1e6 else f'{total/1e3:.0f}K'
        ax.text(0, 0, f'Total\n{total_str}\nreads',
                ha='center', va='center', fontsize=14, fontweight='bold')
    else:
        # Standard pie chart
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            colors=colors,
            explode=explode,
            autopct='%1.1f%%' if config.show_percentages else '',
            pctdistance=0.6,
            startangle=90,
            wedgeprops=dict(edgecolor='white')
        )

    # Style text
    for text in texts:
        text.set_fontsize(10)
    for autotext in autotexts:
        autotext.set_fontsize(9)
        autotext.set_fontweight('bold')

    ax.set_title(config.title, fontsize=14, fontweight='bold', pad=20)

    plt.tight_layout()

    # Save figure
    output_file = output_path.with_suffix(f".{format}")
    plt.savefig(output_file, dpi=config.dpi, bbox_inches='tight')
    plt.close()

    # Calculate key metrics
    signal_positive = end_reasons.get("signal_positive", 0)
    unblock = end_reasons.get("unblock_mux_change", 0) + \
              end_reasons.get("data_service_unblock_mux_change", 0)

    return {
        "success": True,
        "output_path": str(output_file),
        "format": format,
        "config": {
            "title": config.title,
            "style": config.style,
            "dpi": config.dpi
        },
        "data_summary": {
            "total_reads": total,
            "num_categories": len(sorted_reasons),
            "signal_positive_pct": signal_positive / total * 100 if total > 0 else 0,
            "unblock_pct": unblock / total * 100 if total > 0 else 0
        }
    }


def generate_from_context(context, output_path: Path, **kwargs):
    """Generate end reason pie chart from experiment context"""
    end_reasons = context.end_reasons if hasattr(context, 'end_reasons') else None

    if end_reasons is None:
        return {"error": "No end reason data available", "success": False}

    # Extract counts from end_reasons object
    reason_counts = {}
    for attr in dir(end_reasons):
        if not attr.startswith('_') and not attr.endswith('_pct'):
            value = getattr(end_reasons, attr, None)
            if isinstance(value, (int, float)) and value > 0:
                reason_counts[attr] = int(value)

    if not reason_counts:
        return {"error": "No end reason counts found", "success": False}

    return generate_end_reason_pie(
        end_reasons=reason_counts,
        output_path=output_path,
        **kwargs
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate end reason pie chart")
    parser.add_argument("output", type=Path, help="Output file path")
    parser.add_argument("--format", default="pdf", choices=["pdf", "png", "svg"])
    parser.add_argument("--style", default="donut", choices=["pie", "donut"])
    parser.add_argument("--demo", action="store_true", help="Generate demo chart")

    args = parser.parse_args()

    if args.demo:
        demo_data = {
            "signal_positive": 2500000,
            "unblock_mux_change": 1800000,
            "data_service_unblock_mux_change": 300000,
            "mux_change": 150000,
            "other": 50000
        }

        config = EndReasonPieConfig(style=args.style)
        result = generate_end_reason_pie(
            end_reasons=demo_data,
            output_path=args.output,
            config=config,
            format=args.format
        )
        print(f"Generated: {result}")
