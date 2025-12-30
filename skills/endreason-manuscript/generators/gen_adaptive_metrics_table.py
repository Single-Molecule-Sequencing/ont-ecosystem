#!/usr/bin/env python3
"""
Generate adaptive sampling metrics table.

Creates a publication-ready table showing adaptive sampling efficiency:
- Experiment ID
- Sampling Mode (Adaptive/Standard)
- Signal Positive %
- Unblock %
- Data Service Unblock %
- Rejection Rate
- Efficiency Grade

Output formats: LaTeX (.tex), CSV, JSON, HTML

Usage:
    gen_adaptive_metrics_table.py --input merged_data.json --output table.tex --format tex
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


# =============================================================================
# Configuration
# =============================================================================

# Grade thresholds for adaptive sampling efficiency
EFFICIENCY_GRADES = {
    "A": {"signal_positive_min": 95, "rejection_max": 2},
    "B": {"signal_positive_min": 85, "rejection_max": 5},
    "C": {"signal_positive_min": 75, "rejection_max": 15},
    "D": {"signal_positive_min": 0, "rejection_max": 100},
}


# =============================================================================
# Data Processing
# =============================================================================

def extract_adaptive_metrics(experiments: List[Dict]) -> List[Dict[str, Any]]:
    """Extract adaptive sampling metrics from experiments."""
    rows = []

    for exp in experiments:
        er = exp.get("end_reasons")
        if not er:
            continue

        total = er.get("total_reads", 0)
        if total == 0:
            continue

        exp_id = er.get("experiment_id", exp.get("metadata", {}).get("experiment_id", "unknown"))
        name = exp.get("metadata", {}).get("name", exp_id)[:20]

        signal_positive_pct = er.get("signal_positive_pct", 0)
        unblock_pct = er.get("unblock_pct", 0)
        data_service_pct = er.get("data_service_pct", 0)
        rejection_rate = er.get("rejection_rate", unblock_pct + data_service_pct)

        is_adaptive = er.get("is_adaptive", rejection_rate > 1.0)
        mode = "Adaptive" if is_adaptive else "Standard"

        # Determine efficiency grade
        grade = "D"
        for g, thresholds in EFFICIENCY_GRADES.items():
            if (signal_positive_pct >= thresholds["signal_positive_min"] and
                rejection_rate <= thresholds["rejection_max"]):
                grade = g
                break

        rows.append({
            "experiment_id": exp_id,
            "name": name,
            "mode": mode,
            "is_adaptive": is_adaptive,
            "total_reads": total,
            "signal_positive_pct": round(signal_positive_pct, 1),
            "unblock_pct": round(unblock_pct, 1),
            "data_service_pct": round(data_service_pct, 1),
            "rejection_rate": round(rejection_rate, 1),
            "efficiency_grade": grade,
        })

    # Sort by mode (Adaptive first), then by signal_positive descending
    rows.sort(key=lambda x: (0 if x["is_adaptive"] else 1, -x["signal_positive_pct"]))

    return rows


def compute_summary(rows: List[Dict]) -> Dict[str, Any]:
    """Compute summary statistics."""
    if not rows:
        return {}

    adaptive = [r for r in rows if r["is_adaptive"]]
    standard = [r for r in rows if not r["is_adaptive"]]

    def avg(lst, key):
        vals = [r[key] for r in lst]
        return sum(vals) / len(vals) if vals else 0

    return {
        "n_total": len(rows),
        "n_adaptive": len(adaptive),
        "n_standard": len(standard),
        "adaptive_mean_signal_positive": round(avg(adaptive, "signal_positive_pct"), 1),
        "adaptive_mean_rejection": round(avg(adaptive, "rejection_rate"), 1),
        "standard_mean_signal_positive": round(avg(standard, "signal_positive_pct"), 1),
        "standard_mean_rejection": round(avg(standard, "rejection_rate"), 1),
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
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def format_number(n: int) -> str:
    """Format number with thousand separators."""
    return f"{n:,}"


def generate_latex(rows: List[Dict], summary: Dict, caption: str = None) -> str:
    """Generate LaTeX table."""
    latex = [
        r"\begin{table}[htbp]",
        r"\centering",
        f"\\caption{{{caption or 'Adaptive Sampling Efficiency Metrics'}}}",
        r"\label{tab:adaptive_metrics}",
        r"\begin{tabular}{llrrrrl}",
        r"\toprule",
        r"\textbf{Experiment} & \textbf{Mode} & \textbf{SP\%} & \textbf{UB\%} & \textbf{DS\%} & \textbf{Rej\%} & \textbf{Grade} \\",
        r"\midrule",
    ]

    # Data rows
    for row in rows:
        name = escape_latex(row["name"])
        mode = row["mode"]
        sp = f"{row['signal_positive_pct']:.1f}"
        ub = f"{row['unblock_pct']:.1f}"
        ds = f"{row['data_service_pct']:.1f}"
        rej = f"{row['rejection_rate']:.1f}"
        grade = row["efficiency_grade"]

        # Color grade
        if grade == "A":
            grade_tex = r"\textcolor{green!60!black}{A}"
        elif grade == "B":
            grade_tex = r"\textcolor{blue}{B}"
        elif grade == "C":
            grade_tex = r"\textcolor{orange}{C}"
        else:
            grade_tex = r"\textcolor{red}{D}"

        # Highlight adaptive rows
        if row["is_adaptive"]:
            mode_tex = r"\textbf{Adaptive}"
        else:
            mode_tex = "Standard"

        latex.append(f"{name} & {mode_tex} & {sp} & {ub} & {ds} & {rej} & {grade_tex} \\\\")

    # Summary section
    latex.extend([
        r"\midrule",
        r"\multicolumn{7}{l}{\textit{Summary Statistics}} \\",
        r"\midrule",
    ])

    if summary.get("n_adaptive", 0) > 0:
        latex.append(
            f"Adaptive (n={summary['n_adaptive']}) & -- & "
            f"{summary['adaptive_mean_signal_positive']:.1f} & -- & -- & "
            f"{summary['adaptive_mean_rejection']:.1f} & -- \\\\"
        )

    if summary.get("n_standard", 0) > 0:
        latex.append(
            f"Standard (n={summary['n_standard']}) & -- & "
            f"{summary['standard_mean_signal_positive']:.1f} & -- & -- & "
            f"{summary['standard_mean_rejection']:.1f} & -- \\\\"
        )

    # Footer
    latex.extend([
        r"\bottomrule",
        r"\end{tabular}",
        "",
        r"\footnotesize{SP = Signal Positive, UB = Unblock (MUX), DS = Data Service Unblock, Rej = Rejection Rate}",
        r"\end{table}",
    ])

    return "\n".join(latex)


def generate_csv(rows: List[Dict], summary: Dict) -> str:
    """Generate CSV table."""
    output = []
    output.append("Experiment,Mode,Signal Positive %,Unblock %,Data Service %,Rejection Rate %,Grade")

    for row in rows:
        output.append(
            f"{row['name']},{row['mode']},{row['signal_positive_pct']},"
            f"{row['unblock_pct']},{row['data_service_pct']},{row['rejection_rate']},"
            f"{row['efficiency_grade']}"
        )

    return "\n".join(output)


def generate_json_output(rows: List[Dict], summary: Dict) -> str:
    """Generate JSON output."""
    return json.dumps({
        "rows": rows,
        "summary": summary,
        "generated_at": datetime.now().isoformat(),
    }, indent=2)


def generate_html(rows: List[Dict], summary: Dict, caption: str = None) -> str:
    """Generate HTML table."""
    html = [
        '<table class="adaptive-metrics">',
        f'<caption>{caption or "Adaptive Sampling Efficiency Metrics"}</caption>',
        '<thead>',
        '<tr>',
        '<th>Experiment</th>',
        '<th>Mode</th>',
        '<th>SP%</th>',
        '<th>UB%</th>',
        '<th>DS%</th>',
        '<th>Rej%</th>',
        '<th>Grade</th>',
        '</tr>',
        '</thead>',
        '<tbody>',
    ]

    for row in rows:
        mode_class = "adaptive" if row["is_adaptive"] else "standard"
        grade_class = f"grade-{row['efficiency_grade'].lower()}"

        html.append(f'<tr class="{mode_class}">')
        html.append(f'<td>{row["name"]}</td>')
        html.append(f'<td class="{mode_class}">{row["mode"]}</td>')
        html.append(f'<td>{row["signal_positive_pct"]:.1f}</td>')
        html.append(f'<td>{row["unblock_pct"]:.1f}</td>')
        html.append(f'<td>{row["data_service_pct"]:.1f}</td>')
        html.append(f'<td>{row["rejection_rate"]:.1f}</td>')
        html.append(f'<td class="{grade_class}">{row["efficiency_grade"]}</td>')
        html.append('</tr>')

    html.extend([
        '</tbody>',
        '<tfoot>',
        '<tr>',
        f'<td colspan="7"><em>Total: {summary["n_total"]} experiments '
        f'({summary["n_adaptive"]} adaptive, {summary["n_standard"]} standard)</em></td>',
        '</tr>',
        '</tfoot>',
        '</table>',
        '',
        '<style>',
        '.adaptive-metrics { border-collapse: collapse; margin: 20px 0; width: 100%; }',
        '.adaptive-metrics th, .adaptive-metrics td { padding: 8px 12px; border: 1px solid #ddd; text-align: left; }',
        '.adaptive-metrics th { background: #f5f5f5; font-weight: bold; }',
        '.adaptive-metrics .adaptive { font-weight: bold; }',
        '.adaptive-metrics .grade-a { color: green; font-weight: bold; }',
        '.adaptive-metrics .grade-b { color: blue; }',
        '.adaptive-metrics .grade-c { color: orange; }',
        '.adaptive-metrics .grade-d { color: red; }',
        '</style>',
    ])

    return "\n".join(html)


# =============================================================================
# Main Generation Function
# =============================================================================

def generate_adaptive_metrics_table(
    experiments: List[Dict],
    output_path: Path,
    format: str = "tex",
    caption: str = None,
) -> Optional[Path]:
    """
    Generate adaptive sampling metrics table.

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

    # Extract metrics
    rows = extract_adaptive_metrics(experiments)

    if not rows:
        print("Error: No valid metrics found")
        return None

    summary = compute_summary(rows)

    # Generate output
    if format == "tex":
        content = generate_latex(rows, summary, caption)
    elif format == "csv":
        content = generate_csv(rows, summary)
    elif format == "json":
        content = generate_json_output(rows, summary)
    elif format == "html":
        content = generate_html(rows, summary, caption)
    else:
        print(f"Error: Unknown format: {format}")
        return None

    # Write output
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)

    print(f"  Generated: {output_path}")
    print(f"  {len(rows)} experiments ({summary.get('n_adaptive', 0)} adaptive, {summary.get('n_standard', 0)} standard)")
    return output_path


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate adaptive sampling metrics table"
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
    output_path = generate_adaptive_metrics_table(
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
