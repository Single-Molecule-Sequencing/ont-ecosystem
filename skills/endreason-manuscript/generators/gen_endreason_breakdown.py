#!/usr/bin/env python3
"""
Generate detailed end-reason breakdown figure.

Creates a 6-panel figure showing comprehensive end-reason analysis:
(A) Horizontal bar chart of all end reasons with percentages
(B) Pie/donut chart of major categories
(C) Quality grade annotation panel
(D) Expected range highlighting (green/yellow/red bands)
(E) Read count summary by category
(F) Adaptive vs non-adaptive comparison

Usage:
    gen_endreason_breakdown.py --input merged_data.json --output fig.pdf
"""

import argparse
import json
import sys
from pathlib import Path
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

# Color scheme for end reasons
COLORS = {
    "signal_positive": "#27AE60",  # Green
    "unblock_mux_change": "#E74C3C",  # Red
    "data_service_unblock_mux_change": "#F39C12",  # Orange
    "mux_change": "#9B59B6",   # Purple
    "signal_negative": "#7F8C8D",  # Gray
    "unknown": "#BDC3C7",      # Light gray
    "other": "#95A5A6",        # Medium gray
}

# Display names
END_REASON_LABELS = {
    "signal_positive": "Signal Positive",
    "unblock_mux_change": "Unblock (MUX)",
    "data_service_unblock_mux_change": "Unblock (Data Service)",
    "mux_change": "MUX Change",
    "signal_negative": "Signal Negative",
    "unknown": "Unknown",
    "other": "Other",
}

# Expected ranges (min, max) for quality assessment
EXPECTED_RANGES = {
    "signal_positive": (75, 95),
    "unblock_mux_change": (0, 20),
    "data_service_unblock_mux_change": (0, 15),
    "mux_change": (0, 10),
    "signal_negative": (0, 5),
}

# Quality grade thresholds
GRADE_THRESHOLDS = {
    "A": {"signal_positive": 95, "unblock": 2, "color": "#27AE60"},
    "B": {"signal_positive": 85, "unblock": 5, "color": "#3498DB"},
    "C": {"signal_positive": 75, "unblock": 10, "color": "#F39C12"},
    "D": {"signal_positive": 0, "unblock": 100, "color": "#E74C3C"},
}


# =============================================================================
# Data Aggregation
# =============================================================================

def aggregate_end_reasons(experiments: List[Dict]) -> Dict[str, Any]:
    """Aggregate end-reason data across all experiments."""
    totals = {
        "signal_positive": 0,
        "unblock_mux_change": 0,
        "data_service_unblock_mux_change": 0,
        "mux_change": 0,
        "signal_negative": 0,
        "unknown": 0,
        "other": 0,
        "total_reads": 0,
    }

    adaptive_count = 0
    non_adaptive_count = 0
    grades = {"A": 0, "B": 0, "C": 0, "D": 0}

    for exp in experiments:
        er = exp.get("end_reasons")
        if not er:
            continue

        total = er.get("total_reads", 0)
        if total == 0:
            continue

        totals["total_reads"] += total
        totals["signal_positive"] += er.get("signal_positive", 0)
        totals["unblock_mux_change"] += er.get("unblock_mux_change", 0)
        totals["data_service_unblock_mux_change"] += er.get("data_service_unblock_mux_change", 0)
        totals["mux_change"] += er.get("mux_change", 0)
        totals["signal_negative"] += er.get("signal_negative", 0)
        totals["unknown"] += er.get("unknown", 0)
        totals["other"] += er.get("other", 0)

        if er.get("is_adaptive", False):
            adaptive_count += 1
        else:
            non_adaptive_count += 1

        grade = er.get("quality_grade", "D")
        if grade in grades:
            grades[grade] += 1

    # Calculate percentages
    total_reads = totals["total_reads"]
    percentages = {}
    for key in ["signal_positive", "unblock_mux_change", "data_service_unblock_mux_change",
                "mux_change", "signal_negative", "unknown", "other"]:
        percentages[key] = (totals[key] / total_reads * 100) if total_reads > 0 else 0

    return {
        "totals": totals,
        "percentages": percentages,
        "n_experiments": len(experiments),
        "adaptive_count": adaptive_count,
        "non_adaptive_count": non_adaptive_count,
        "grades": grades,
    }


# =============================================================================
# Figure Generation
# =============================================================================

def generate_endreason_breakdown(
    experiments: List[Dict],
    output_path: Path,
    format: str = "pdf",
    dpi: int = 150,
    figsize: tuple = (16, 12),
) -> Optional[Path]:
    """
    Generate end-reason breakdown figure.

    Args:
        experiments: List of experiment dicts with end_reasons
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

    # Aggregate data
    agg = aggregate_end_reasons(experiments)
    pcts = agg["percentages"]
    totals = agg["totals"]

    # Create figure with 6 panels
    fig = plt.figure(figsize=figsize)

    # Custom layout: 3 rows, varying columns
    ax1 = plt.subplot2grid((3, 3), (0, 0), colspan=2, rowspan=1)  # Horizontal bar
    ax2 = plt.subplot2grid((3, 3), (0, 2), rowspan=1)  # Pie chart
    ax3 = plt.subplot2grid((3, 3), (1, 0), colspan=1)  # Quality grade
    ax4 = plt.subplot2grid((3, 3), (1, 1), colspan=2)  # Expected ranges
    ax5 = plt.subplot2grid((3, 3), (2, 0), colspan=2)  # Read counts
    ax6 = plt.subplot2grid((3, 3), (2, 2), colspan=1)  # Adaptive comparison

    # ==========================================================================
    # Panel A: Horizontal bar chart of all end reasons
    # ==========================================================================
    categories = ["signal_positive", "unblock_mux_change", "data_service_unblock_mux_change",
                  "mux_change", "signal_negative", "unknown"]
    values = [pcts.get(cat, 0) for cat in categories]
    labels = [END_REASON_LABELS.get(cat, cat) for cat in categories]
    colors = [COLORS.get(cat, "#BDC3C7") for cat in categories]

    y_pos = np.arange(len(categories))
    bars = ax1.barh(y_pos, values, color=colors, edgecolor='black', linewidth=0.5)

    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(labels, fontsize=10)
    ax1.set_xlabel("Percentage (%)", fontsize=11)
    ax1.set_title("A. End-Reason Distribution", fontsize=12, fontweight='bold')
    ax1.set_xlim(0, 100)

    # Add value labels
    for bar, val in zip(bars, values):
        ax1.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                f'{val:.1f}%', va='center', fontsize=9)

    # ==========================================================================
    # Panel B: Pie/donut chart
    # ==========================================================================
    # Consolidate small categories
    pie_data = {}
    for cat in categories:
        val = pcts.get(cat, 0)
        if val >= 1:  # Only show categories >= 1%
            pie_data[END_REASON_LABELS.get(cat, cat)] = val
        else:
            pie_data["Other"] = pie_data.get("Other", 0) + val

    pie_labels = list(pie_data.keys())
    pie_values = list(pie_data.values())
    pie_colors = [COLORS.get(k.lower().replace(" ", "_").replace("(", "").replace(")", ""),
                            COLORS.get("other")) for k in pie_labels]

    wedges, texts, autotexts = ax2.pie(
        pie_values,
        labels=pie_labels,
        colors=pie_colors,
        autopct='%1.1f%%',
        startangle=90,
        wedgeprops=dict(width=0.6, edgecolor='white'),  # Donut style
        textprops={'fontsize': 8},
    )
    ax2.set_title("B. Category Distribution", fontsize=12, fontweight='bold')

    # ==========================================================================
    # Panel C: Quality grade summary
    # ==========================================================================
    grades = agg["grades"]
    grade_labels = ["A", "B", "C", "D"]
    grade_counts = [grades.get(g, 0) for g in grade_labels]
    grade_colors = [GRADE_THRESHOLDS[g]["color"] for g in grade_labels]

    bars = ax3.bar(grade_labels, grade_counts, color=grade_colors,
                   edgecolor='black', linewidth=0.5)
    ax3.set_ylabel("Number of Experiments", fontsize=11)
    ax3.set_title("C. Quality Grades", fontsize=12, fontweight='bold')

    # Add value labels
    for bar, val in zip(bars, grade_counts):
        if val > 0:
            ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                    str(val), ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Add grade criteria
    ax3.text(0.5, -0.15, "A: SP≥95%, UB≤2%  B: SP≥85%, UB≤5%",
             transform=ax3.transAxes, ha='center', fontsize=8, style='italic')

    # ==========================================================================
    # Panel D: Expected ranges visualization
    # ==========================================================================
    range_cats = ["signal_positive", "unblock_mux_change", "data_service_unblock_mux_change"]
    range_labels = [END_REASON_LABELS.get(cat, cat)[:15] for cat in range_cats]
    actual_values = [pcts.get(cat, 0) for cat in range_cats]

    x_pos = np.arange(len(range_cats))
    width = 0.5

    # Draw expected range bands
    for i, cat in enumerate(range_cats):
        expected = EXPECTED_RANGES.get(cat, (0, 100))
        # Green band (good)
        ax4.barh(i, expected[1] - expected[0], left=expected[0], height=0.3,
                color='#27AE60', alpha=0.3)

    # Draw actual values
    bars = ax4.barh(x_pos, actual_values, height=0.5, color='#3498DB',
                   edgecolor='black', linewidth=0.5)

    ax4.set_yticks(x_pos)
    ax4.set_yticklabels(range_labels, fontsize=10)
    ax4.set_xlabel("Percentage (%)", fontsize=11)
    ax4.set_title("D. Actual vs Expected Ranges", fontsize=12, fontweight='bold')
    ax4.set_xlim(0, 100)

    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#27AE60', alpha=0.3, label='Expected Range'),
        Patch(facecolor='#3498DB', label='Actual Value'),
    ]
    ax4.legend(handles=legend_elements, loc='upper right', fontsize=8)

    # ==========================================================================
    # Panel E: Read counts by category
    # ==========================================================================
    count_cats = ["signal_positive", "unblock_mux_change", "mux_change", "other"]
    count_labels = [END_REASON_LABELS.get(cat, cat) for cat in count_cats]
    count_values = [totals.get(cat, 0) / 1e6 for cat in count_cats]  # Millions
    count_colors = [COLORS.get(cat, "#BDC3C7") for cat in count_cats]

    x_pos = np.arange(len(count_cats))
    bars = ax5.bar(x_pos, count_values, color=count_colors, edgecolor='black', linewidth=0.5)

    ax5.set_xticks(x_pos)
    ax5.set_xticklabels(count_labels, rotation=15, ha='right', fontsize=9)
    ax5.set_ylabel("Reads (millions)", fontsize=11)
    ax5.set_title("E. Total Read Counts by Category", fontsize=12, fontweight='bold')

    # Add value labels
    for bar, val in zip(bars, count_values):
        if val > 0:
            ax5.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                    f'{val:.1f}M', ha='center', va='bottom', fontsize=9)

    # Add total
    total_m = totals["total_reads"] / 1e6
    ax5.text(0.95, 0.95, f'Total: {total_m:.1f}M reads\nn={agg["n_experiments"]} experiments',
             transform=ax5.transAxes, ha='right', va='top', fontsize=9,
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # ==========================================================================
    # Panel F: Adaptive vs Non-Adaptive comparison
    # ==========================================================================
    adaptive_n = agg["adaptive_count"]
    non_adaptive_n = agg["non_adaptive_count"]

    categories = ["Adaptive\nSampling", "Standard\nSequencing"]
    values = [adaptive_n, non_adaptive_n]
    colors = ["#E74C3C", "#3498DB"]

    bars = ax6.bar(categories, values, color=colors, edgecolor='black', linewidth=0.5)
    ax6.set_ylabel("Number of Experiments", fontsize=11)
    ax6.set_title("F. Sequencing Mode", fontsize=12, fontweight='bold')

    for bar, val in zip(bars, values):
        if val > 0:
            ax6.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                    str(val), ha='center', va='bottom', fontsize=10, fontweight='bold')

    # ==========================================================================
    # Final touches
    # ==========================================================================
    fig.suptitle("End-Reason Analysis Summary",
                 fontsize=14, fontweight='bold', y=1.01)

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
        description="Generate end-reason breakdown figure"
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

    with open(input_path) as f:
        data = json.load(f)

    experiments = data.get("experiments", [])
    if not experiments:
        print("Error: No experiments found in input file")
        sys.exit(1)

    print(f"Loaded {len(experiments)} experiments")

    # Generate figure
    output_path = generate_endreason_breakdown(
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
