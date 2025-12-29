"""Discovery Report Module for ONT Experiment Analysis

Generates terminal, JSON, and HTML reports from QuickSummary data.
"""

import json
import html
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Import QuickSummary - handle both package and direct import cases
try:
    from .quick_analysis import QuickSummary, aggregate_summaries
except ImportError:
    from quick_analysis import QuickSummary, aggregate_summaries


# =============================================================================
# Number Formatting Utilities
# =============================================================================

def format_number(n: Optional[int], suffix: str = "") -> str:
    """Format large numbers with K/M/G suffixes."""
    if n is None:
        return "?"
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.1f}G{suffix}"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M{suffix}"
    if n >= 1_000:
        return f"{n/1_000:.1f}K{suffix}"
    return f"{n}{suffix}"


def format_size(gb: float) -> str:
    """Format size in GB."""
    if gb >= 1000:
        return f"{gb/1000:.2f}TB"
    return f"{gb:.1f}GB"


def format_float(f: Optional[float], decimals: int = 1) -> str:
    """Format float with specified decimals."""
    if f is None:
        return "?"
    return f"{f:.{decimals}f}"


def format_pct(pct: Optional[float]) -> str:
    """Format percentage."""
    if pct is None:
        return "?"
    return f"{pct:.1f}%"


# =============================================================================
# Terminal Output
# =============================================================================

# ANSI color codes
COLORS = {
    'reset': '\033[0m',
    'bold': '\033[1m',
    'dim': '\033[2m',
    'red': '\033[31m',
    'green': '\033[32m',
    'yellow': '\033[33m',
    'blue': '\033[34m',
    'magenta': '\033[35m',
    'cyan': '\033[36m',
    'white': '\033[37m',
    'bg_green': '\033[42m',
    'bg_yellow': '\033[43m',
    'bg_red': '\033[41m',
}

GRADE_COLORS = {
    'A': 'green',
    'B': 'cyan',
    'C': 'yellow',
    'D': 'magenta',
    'F': 'red',
    'S': 'blue',  # Signal-only (pod5/fast5 without basecalling)
    '?': 'dim',
}


def colorize(text: str, color: str) -> str:
    """Apply ANSI color to text."""
    if color in COLORS:
        return f"{COLORS[color]}{text}{COLORS['reset']}"
    return text


def grade_colored(grade: str) -> str:
    """Return grade with appropriate color."""
    color = GRADE_COLORS.get(grade, 'white')
    return colorize(grade, color)


def truncate(s: str, max_len: int) -> str:
    """Truncate string with ellipsis."""
    if len(s) <= max_len:
        return s
    return s[:max_len-2] + ".."


def format_duration(hours: Optional[float]) -> str:
    """Format duration in hours to human readable string."""
    if hours is None:
        return "?"
    if hours < 1:
        return f"{int(hours * 60)}m"
    if hours < 24:
        return f"{hours:.1f}h"
    days = hours / 24
    return f"{days:.1f}d"


def display_terminal_summary(
    summaries: List[QuickSummary],
    source_dir: str = "",
    elapsed_time: float = 0.0,
    use_colors: bool = True
) -> None:
    """Display quick analysis results as a colored terminal table.

    Args:
        summaries: List of QuickSummary objects
        source_dir: Source directory that was scanned
        elapsed_time: Time taken for analysis
        use_colors: Whether to use ANSI colors
    """
    if not use_colors:
        # Disable colors
        global COLORS
        COLORS = {k: '' for k in COLORS}

    agg = aggregate_summaries(summaries)

    # Calculate total reads and bases
    total_reads = sum(s.total_reads or 0 for s in summaries)
    total_bases = sum(s.total_bases or 0 for s in summaries)

    # Header
    print()
    print(colorize("=" * 120, 'dim'))
    print(colorize(f"  Discovery Analysis: {source_dir}", 'bold'))
    print(colorize(f"  Found: {len(summaries)} experiments | "
                   f"Total: {format_size(agg['total_size_gb'])} | "
                   f"{format_number(total_reads)} reads | "
                   f"{format_number(total_bases)} bases | "
                   f"Analyzed in {elapsed_time:.1f}s", 'dim'))
    print(colorize("=" * 120, 'dim'))
    print()

    # Table header - expanded with new columns
    headers = ["Name", "Started", "Duration", "Reads", "Bases", "Q", "N50", "Device", "Grade"]
    widths = [28, 16, 8, 10, 10, 5, 8, 12, 5]

    header_line = "  "
    for h, w in zip(headers, widths):
        header_line += h.ljust(w) + " "
    print(colorize(header_line, 'bold'))

    # Separator
    sep_line = "  "
    for w in widths:
        sep_line += "-" * w + " "
    print(colorize(sep_line, 'dim'))

    # Table rows
    for s in summaries:
        row = "  "
        row += truncate(s.name, 28).ljust(28) + " "

        # Started date/time
        if s.start_date and s.start_time:
            # Show just month-day and time
            date_short = s.start_date[5:] if s.start_date else "?"  # MM-DD
            started_str = f"{date_short} {s.start_time}"
        else:
            started_str = "?"
        row += started_str.ljust(16) + " "

        # Duration
        row += format_duration(s.duration_hours).rjust(8) + " "

        # Reads and bases
        row += format_number(s.total_reads).rjust(10) + " "
        row += format_number(s.total_bases).rjust(10) + " "

        # Q-score
        row += format_float(s.mean_qscore).rjust(5) + " "

        # N50
        row += format_number(s.n50).rjust(8) + " "

        # Device/Flow cell
        device_str = s.device_id or s.flow_cell_id or "?"
        row += truncate(device_str, 12).ljust(12) + " "

        # Print row (without grade color)
        print(row, end="")
        # Print grade with color
        print(grade_colored(s.quality_grade).center(5))

    print()

    # Summary line
    grade_summary = []
    for grade in ['A', 'B', 'C', 'D', 'F', 'S']:
        count = agg.get(f'grade_{grade.lower()}_count', 0)
        if count > 0:
            grade_summary.append(f"{count} Grade {grade_colored(grade)}")

    issues_count = agg.get('issues_count', 0)
    issues_text = f"{issues_count} Issues" if issues_count > 0 else colorize("0 Issues", 'green')

    print(f"  Summary: {' | '.join(grade_summary)} | {issues_text}")
    print()


# =============================================================================
# JSON Report
# =============================================================================

def generate_json_report(
    summaries: List[QuickSummary],
    output_path: Path,
    source_dir: str = "",
    elapsed_time: float = 0.0
) -> Path:
    """Generate comprehensive JSON report.

    Args:
        summaries: List of QuickSummary objects
        output_path: Path for output JSON file
        source_dir: Source directory that was scanned
        elapsed_time: Time taken for analysis

    Returns:
        Path to generated JSON file
    """
    agg = aggregate_summaries(summaries)

    report = {
        "generated_at": datetime.now().isoformat(),
        "source_directory": str(source_dir),
        "analysis_time_seconds": elapsed_time,
        "experiment_count": len(summaries),
        "summary": agg,
        "experiments": [s.to_dict() for s in summaries],
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)

    return output_path


# =============================================================================
# HTML Dashboard
# =============================================================================

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ONT Discovery Report</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            line-height: 1.6;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        header {
            background: linear-gradient(135deg, #1e293b, #334155);
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 24px;
        }
        h1 { font-size: 1.8rem; margin-bottom: 8px; }
        .subtitle { color: #94a3b8; font-size: 0.9rem; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .stat-card {
            background: #1e293b;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #10b981;
        }
        .stat-value { font-size: 2rem; font-weight: bold; color: #10b981; }
        .stat-label { color: #94a3b8; font-size: 0.85rem; text-transform: uppercase; }
        .grade-dist {
            display: flex;
            gap: 12px;
            margin-top: 12px;
        }
        .grade-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.85rem;
        }
        .grade-A { background: #065f46; color: #6ee7b7; }
        .grade-B { background: #0e7490; color: #67e8f9; }
        .grade-C { background: #a16207; color: #fde047; }
        .grade-D { background: #7e22ce; color: #d8b4fe; }
        .grade-F { background: #991b1b; color: #fca5a5; }
        .grade-S { background: #1e40af; color: #93c5fd; }  /* Signal-only */
        table {
            width: 100%;
            border-collapse: collapse;
            background: #1e293b;
            border-radius: 8px;
            overflow: hidden;
        }
        th {
            background: #334155;
            padding: 12px 16px;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.75rem;
            color: #94a3b8;
            cursor: pointer;
        }
        th:hover { background: #475569; }
        td {
            padding: 12px 16px;
            border-bottom: 1px solid #334155;
        }
        tr:hover { background: #334155; }
        .search-box {
            width: 100%;
            padding: 12px 16px;
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            color: #e2e8f0;
            font-size: 1rem;
            margin-bottom: 16px;
        }
        .search-box:focus { outline: none; border-color: #10b981; }
        .issues { color: #f87171; font-size: 0.85rem; }
        .no-issues { color: #6ee7b7; }
        .completeness {
            display: flex;
            gap: 4px;
        }
        .check { color: #6ee7b7; }
        .missing { color: #475569; }
        footer {
            text-align: center;
            padding: 20px;
            color: #64748b;
            font-size: 0.85rem;
        }
        @media (max-width: 768px) {
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            table { font-size: 0.85rem; }
            td, th { padding: 8px 10px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>ONT Discovery Report</h1>
            <div class="subtitle">
                Source: {{source_dir}} | Generated: {{generated_at}} | Analysis time: {{elapsed_time}}s
            </div>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{{experiment_count}}</div>
                <div class="stat-label">Experiments</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{total_reads}}</div>
                <div class="stat-label">Total Reads</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{total_bases}}</div>
                <div class="stat-label">Total Bases</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{total_size}}</div>
                <div class="stat-label">Total Size</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{avg_qscore}}</div>
                <div class="stat-label">Avg Q-Score</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{avg_n50}}</div>
                <div class="stat-label">Avg N50</div>
            </div>
        </div>

        <div class="stat-card" style="margin-bottom: 24px;">
            <div class="stat-label" style="margin-bottom: 8px;">Quality Grade Distribution</div>
            <div class="grade-dist">
                {{grade_badges}}
            </div>
        </div>

        <input type="text" class="search-box" placeholder="Search experiments..." id="searchBox">

        <table id="experimentTable">
            <thead>
                <tr>
                    <th onclick="sortTable(0)">Name</th>
                    <th onclick="sortTable(1)">Started</th>
                    <th onclick="sortTable(2)">Duration</th>
                    <th onclick="sortTable(3)">Reads</th>
                    <th onclick="sortTable(4)">Bases</th>
                    <th onclick="sortTable(5)">Q-Score</th>
                    <th onclick="sortTable(6)">N50</th>
                    <th onclick="sortTable(7)">Device</th>
                    <th onclick="sortTable(8)">Grade</th>
                    <th>Completeness</th>
                    <th>Issues</th>
                </tr>
            </thead>
            <tbody>
                {{table_rows}}
            </tbody>
        </table>

        <footer>
            ONT Ecosystem v3.0 | Discovery Report
        </footer>
    </div>

    <script>
        // Search functionality
        document.getElementById('searchBox').addEventListener('input', function() {
            const filter = this.value.toLowerCase();
            const rows = document.querySelectorAll('#experimentTable tbody tr');
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(filter) ? '' : 'none';
            });
        });

        // Sort functionality
        let sortDir = {};
        function sortTable(col) {
            const table = document.getElementById('experimentTable');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));

            sortDir[col] = !sortDir[col];
            const dir = sortDir[col] ? 1 : -1;

            rows.sort((a, b) => {
                let aVal = a.cells[col].textContent.trim();
                let bVal = b.cells[col].textContent.trim();

                // Try numeric sort
                const aNum = parseFloat(aVal.replace(/[^0-9.-]/g, ''));
                const bNum = parseFloat(bVal.replace(/[^0-9.-]/g, ''));

                if (!isNaN(aNum) && !isNaN(bNum)) {
                    return (aNum - bNum) * dir;
                }
                return aVal.localeCompare(bVal) * dir;
            });

            rows.forEach(row => tbody.appendChild(row));
        }
    </script>
</body>
</html>'''


def generate_html_dashboard(
    summaries: List[QuickSummary],
    output_path: Path,
    source_dir: str = "",
    elapsed_time: float = 0.0
) -> Path:
    """Generate standalone HTML dashboard.

    Args:
        summaries: List of QuickSummary objects
        output_path: Path for output HTML file
        source_dir: Source directory that was scanned
        elapsed_time: Time taken for analysis

    Returns:
        Path to generated HTML file
    """
    agg = aggregate_summaries(summaries)

    # Generate grade badges
    grade_badges = []
    for grade in ['A', 'B', 'C', 'D', 'F']:
        count = agg.get(f'grade_{grade.lower()}_count', 0)
        if count > 0:
            grade_badges.append(f'<span class="grade-badge grade-{grade}">{count} {grade}</span>')
    grade_badges_html = ' '.join(grade_badges) if grade_badges else '<span class="no-issues">All experiments pending</span>'

    # Generate table rows
    table_rows = []
    for s in summaries:
        # Completeness icons
        checks = []
        for label, has in [('FS', s.has_final_summary), ('SS', s.has_sequencing_summary),
                           ('P5', s.has_pod5), ('F5', s.has_fast5), ('FQ', s.has_fastq)]:
            if has:
                checks.append(f'<span class="check" title="{label}">{label}</span>')
            else:
                checks.append(f'<span class="missing" title="{label}">{label}</span>')
        completeness = '<div class="completeness">' + ' '.join(checks) + '</div>'

        # Issues
        if s.issues:
            issues_html = '<span class="issues">' + html.escape('; '.join(s.issues[:2])) + '</span>'
        else:
            issues_html = '<span class="no-issues">-</span>'

        # Format started time
        if s.start_date and s.start_time:
            started = f"{s.start_date[5:]} {s.start_time}"  # MM-DD HH:MM
        else:
            started = "?"

        # Format duration
        duration = format_duration(s.duration_hours)

        # Device ID
        device = s.device_id or "?"

        row = f'''<tr>
            <td>{html.escape(s.name[:35])}</td>
            <td>{html.escape(started)}</td>
            <td>{duration}</td>
            <td>{format_number(s.total_reads)}</td>
            <td>{format_number(s.total_bases)}</td>
            <td>{format_float(s.mean_qscore)}</td>
            <td>{format_number(s.n50)}</td>
            <td>{html.escape(device)}</td>
            <td><span class="grade-badge grade-{s.quality_grade}">{s.quality_grade}</span></td>
            <td>{completeness}</td>
            <td>{issues_html}</td>
        </tr>'''
        table_rows.append(row)

    # Fill template
    html_content = HTML_TEMPLATE
    replacements = {
        '{{source_dir}}': html.escape(str(source_dir)),
        '{{generated_at}}': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        '{{elapsed_time}}': f'{elapsed_time:.1f}',
        '{{experiment_count}}': str(len(summaries)),
        '{{total_reads}}': format_number(agg.get('total_reads', 0)),
        '{{total_bases}}': format_number(agg.get('total_bases', 0)),
        '{{total_size}}': format_size(agg.get('total_size_gb', 0)),
        '{{avg_qscore}}': format_float(agg.get('avg_qscore')),
        '{{avg_n50}}': format_number(agg.get('avg_n50')),
        '{{grade_badges}}': grade_badges_html,
        '{{table_rows}}': '\n'.join(table_rows),
    }

    for key, value in replacements.items():
        html_content = html_content.replace(key, value)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        f.write(html_content)

    return output_path


# =============================================================================
# Comparison Table
# =============================================================================

def generate_comparison_table(
    summaries: List[QuickSummary],
    output_path: Path,
    format: str = 'csv'
) -> Path:
    """Generate comparison table across experiments.

    Args:
        summaries: List of QuickSummary objects
        output_path: Path for output file
        format: Output format ('csv', 'tsv', 'json')

    Returns:
        Path to generated file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if format == 'json':
        data = []
        for s in summaries:
            data.append({
                'id': s.experiment_id,
                'name': s.name,
                'start_date': s.start_date,
                'start_time': s.start_time,
                'duration_hours': s.duration_hours,
                'reads': s.total_reads,
                'bases': s.total_bases,
                'qscore': s.mean_qscore,
                'n50': s.n50,
                'pass_rate': s.pass_rate,
                'device_id': s.device_id,
                'grade': s.quality_grade,
            })
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
    else:
        sep = '\t' if format == 'tsv' else ','
        with open(output_path, 'w') as f:
            f.write(sep.join(['ID', 'Name', 'Started', 'Duration', 'Reads', 'Bases', 'Q-Score', 'N50', 'Pass Rate', 'Device', 'Grade']) + '\n')
            for s in summaries:
                # Format started
                if s.start_date and s.start_time:
                    started = f"{s.start_date} {s.start_time}"
                else:
                    started = ''
                # Format duration
                duration = format_duration(s.duration_hours) if s.duration_hours else ''

                row = [
                    s.experiment_id,
                    s.name,
                    started,
                    duration,
                    str(s.total_reads or ''),
                    str(s.total_bases or ''),
                    format_float(s.mean_qscore) if s.mean_qscore else '',
                    str(s.n50 or ''),
                    format_pct(s.pass_rate) if s.pass_rate else '',
                    s.device_id or '',
                    s.quality_grade,
                ]
                f.write(sep.join(row) + '\n')

    return output_path


# =============================================================================
# Report Generation Entry Point
# =============================================================================

def generate_all_reports(
    summaries: List[QuickSummary],
    output_dir: Path,
    source_dir: str = "",
    elapsed_time: float = 0.0,
    display_terminal: bool = True
) -> Dict[str, Path]:
    """Generate all report formats.

    Args:
        summaries: List of QuickSummary objects
        output_dir: Directory for output files
        source_dir: Source directory that was scanned
        elapsed_time: Time taken for analysis
        display_terminal: Whether to display terminal output

    Returns:
        Dictionary mapping report type to file path
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    reports = {}

    # Terminal display
    if display_terminal:
        display_terminal_summary(summaries, source_dir, elapsed_time)

    # JSON report
    json_path = output_dir / 'discovery_report.json'
    reports['json'] = generate_json_report(summaries, json_path, source_dir, elapsed_time)

    # HTML dashboard
    html_path = output_dir / 'discovery_dashboard.html'
    reports['html'] = generate_html_dashboard(summaries, html_path, source_dir, elapsed_time)

    # Comparison CSV
    csv_path = output_dir / 'comparison_table.csv'
    reports['csv'] = generate_comparison_table(summaries, csv_path, format='csv')

    return reports
