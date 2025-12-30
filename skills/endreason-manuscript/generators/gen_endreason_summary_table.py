#!/usr/bin/env python3
"""
Generate end-reason summary table.

Creates a publication-ready table showing per-end-reason statistics:
- End reason category
- Total count
- Percentage
- Expected range
- Status (within/outside expected)

Output formats: LaTeX (.tex), CSV, JSON, HTML

Usage:
    gen_endreason_summary_table.py --input merged_data.json --output table.tex --format tex
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


# =============================================================================
# Configuration
# =============================================================================

# Display names for end reasons
END_REASON_LABELS = {
    "signal_positive": "Signal Positive",
    "unblock_mux_change": "Unblock (MUX Change)",
    "data_service_unblock_mux_change": "Unblock (Data Service)",
    "mux_change": "MUX Change",
    "signal_negative": "Signal Negative",
    "unknown": "Unknown",
    "other": "Other",
}

# Expected ranges (min, max) for each end reason
EXPECTED_RANGES = {
    "signal_positive": (75, 95),
    "unblock_mux_change": (0, 20),
    "data_service_unblock_mux_change": (0, 15),
    "mux_change": (0, 10),
    "signal_negative": (0, 5),
    "unknown": (0, 5),
    "other": (0, 5),
}

# Order of categories in table
CATEGORY_ORDER = [
    "signal_positive",
    "unblock_mux_change",
    "data_service_unblock_mux_change",
    "mux_change",
    "signal_negative",
    "unknown",
    "other",
]


# =============================================================================
# Data Aggregation
# =============================================================================

def aggregate_end_reasons(experiments: List[Dict]) -> Dict[str, Any]:
    """Aggregate end-reason data across all experiments."""
    totals = {cat: 0 for cat in CATEGORY_ORDER}
    totals["total_reads"] = 0

    for exp in experiments:
        er = exp.get("end_reasons")
        if not er:
            continue

        total = er.get("total_reads", 0)
        if total == 0:
            continue

        totals["total_reads"] += total
        for cat in CATEGORY_ORDER:
            totals[cat] += er.get(cat, 0)

    # Calculate percentages and status
    total_reads = totals["total_reads"]
    results = []

    for cat in CATEGORY_ORDER:
        count = totals[cat]
        pct = (count / total_reads * 100) if total_reads > 0 else 0
        expected = EXPECTED_RANGES.get(cat, (0, 100))

        # Determine status
        if expected[0] <= pct <= expected[1]:
            status = "OK"
        elif cat == "signal_positive" and pct < expected[0]:
            status = "LOW"
        elif cat != "signal_positive" and pct > expected[1]:
            status = "HIGH"
        else:
            status = "CHECK"

        results.append({
            "category": cat,
            "label": END_REASON_LABELS.get(cat, cat),
            "count": count,
            "percentage": round(pct, 2),
            "expected_range": f"{expected[0]}-{expected[1]}%",
            "expected_min": expected[0],
            "expected_max": expected[1],
            "status": status,
        })

    return {
        "rows": results,
        "total_reads": total_reads,
        "n_experiments": len([e for e in experiments if e.get("end_reasons")]),
        "generated_at": datetime.now().isoformat(),
    }


# =============================================================================
# Format Output
# =============================================================================

def escape_latex(text: str) -> str:
    """Escape special LaTeX characters."""
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def format_number(n: int) -> str:
    """Format number with thousand separators."""
    return f"{n:,}"


def generate_latex(data: Dict[str, Any], caption: str = None) -> str:
    """Generate LaTeX table."""
    rows = data["rows"]

    # Table header
    latex = [
        r"\begin{table}[htbp]",
        r"\centering",
        f"\\caption{{{caption or 'End-Reason Summary'}}}",
        r"\label{tab:endreason_summary}",
        r"\begin{tabular}{llrrrl}",
        r"\toprule",
        r"\textbf{Category} & \textbf{Count} & \textbf{\%} & \textbf{Expected} & \textbf{Status} \\",
        r"\midrule",
    ]

    # Data rows
    for row in rows:
        label = escape_latex(row["label"])
        count = format_number(row["count"])
        pct = f"{row['percentage']:.1f}\\%"
        expected = escape_latex(row["expected_range"])
        status = row["status"]

        # Color status
        if status == "OK":
            status_tex = r"\textcolor{green!60!black}{OK}"
        elif status == "LOW" or status == "HIGH":
            status_tex = f"\\textcolor{{red}}{{{status}}}"
        else:
            status_tex = f"\\textcolor{{orange}}{{{status}}}"

        latex.append(f"{label} & {count} & {pct} & {expected} & {status_tex} \\\\")

    # Footer
    latex.extend([
        r"\midrule",
        f"\\textbf{{Total}} & \\textbf{{{format_number(data['total_reads'])}}} & 100.0\\% & -- & -- \\\\",
        r"\bottomrule",
        r"\end{tabular}",
        "",
        f"\\footnotesize{{Based on {data['n_experiments']} experiments. Generated: {data['generated_at'][:10]}}}",
        r"\end{table}",
    ])

    return "\n".join(latex)


def generate_csv(data: Dict[str, Any]) -> str:
    """Generate CSV table."""
    rows = data["rows"]

    output = []
    output.append("Category,Count,Percentage,Expected Range,Status")

    for row in rows:
        output.append(f"{row['label']},{row['count']},{row['percentage']},{row['expected_range']},{row['status']}")

    output.append(f"Total,{data['total_reads']},100.0,--,--")
    return "\n".join(output)


def generate_json(data: Dict[str, Any]) -> str:
    """Generate JSON output."""
    return json.dumps(data, indent=2)


def generate_html(data: Dict[str, Any], caption: str = None) -> str:
    """Generate HTML table."""
    rows = data["rows"]

    html = [
        '<table class="endreason-summary">',
        f'<caption>{caption or "End-Reason Summary"}</caption>',
        '<thead>',
        '<tr>',
        '<th>Category</th>',
        '<th>Count</th>',
        '<th>%</th>',
        '<th>Expected</th>',
        '<th>Status</th>',
        '</tr>',
        '</thead>',
        '<tbody>',
    ]

    for row in rows:
        status_class = {
            "OK": "status-ok",
            "LOW": "status-low",
            "HIGH": "status-high",
            "CHECK": "status-check",
        }.get(row["status"], "")

        html.append('<tr>')
        html.append(f'<td>{row["label"]}</td>')
        html.append(f'<td>{format_number(row["count"])}</td>')
        html.append(f'<td>{row["percentage"]:.1f}%</td>')
        html.append(f'<td>{row["expected_range"]}</td>')
        html.append(f'<td class="{status_class}">{row["status"]}</td>')
        html.append('</tr>')

    # Total row
    html.extend([
        '<tr class="total-row">',
        '<td><strong>Total</strong></td>',
        f'<td><strong>{format_number(data["total_reads"])}</strong></td>',
        '<td>100.0%</td>',
        '<td>--</td>',
        '<td>--</td>',
        '</tr>',
        '</tbody>',
        '</table>',
        '',
        '<style>',
        '.endreason-summary { border-collapse: collapse; margin: 20px 0; }',
        '.endreason-summary th, .endreason-summary td { padding: 8px 12px; border: 1px solid #ddd; }',
        '.endreason-summary th { background: #f5f5f5; font-weight: bold; }',
        '.endreason-summary .total-row { background: #f9f9f9; }',
        '.status-ok { color: green; font-weight: bold; }',
        '.status-low, .status-high { color: red; font-weight: bold; }',
        '.status-check { color: orange; font-weight: bold; }',
        '</style>',
    ])

    return "\n".join(html)


# =============================================================================
# Main Generation Function
# =============================================================================

def generate_endreason_summary_table(
    experiments: List[Dict],
    output_path: Path,
    format: str = "tex",
    caption: str = None,
) -> Optional[Path]:
    """
    Generate end-reason summary table.

    Args:
        experiments: List of experiment dicts with end_reasons
        output_path: Output file path
        format: Output format (tex, csv, json, html)
        caption: Table caption

    Returns:
        Path to generated file or None on failure
    """
    if not experiments:
        print("Error: No experiment data provided")
        return None

    # Aggregate data
    data = aggregate_end_reasons(experiments)

    if data["total_reads"] == 0:
        print("Error: No reads found in experiments")
        return None

    # Generate output
    if format == "tex":
        content = generate_latex(data, caption)
    elif format == "csv":
        content = generate_csv(data)
    elif format == "json":
        content = generate_json(data)
    elif format == "html":
        content = generate_html(data, caption)
    else:
        print(f"Error: Unknown format: {format}")
        return None

    # Write output
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)

    print(f"  Generated: {output_path}")
    return output_path


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate end-reason summary table"
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
        default="tex",
        choices=["tex", "csv", "json", "html"],
        help="Output format (default: tex)",
    )
    parser.add_argument(
        "--caption", "-c",
        help="Table caption",
    )

    args = parser.parse_args()

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

    # Generate table
    output_path = generate_endreason_summary_table(
        experiments,
        Path(args.output),
        format=args.format,
        caption=args.caption,
    )

    if output_path:
        print(f"Success: {output_path}")
        sys.exit(0)
    else:
        print("Error: Table generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
