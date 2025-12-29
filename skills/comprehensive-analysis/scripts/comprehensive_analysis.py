#!/usr/bin/env python3
"""
Comprehensive ONT Experiment Analysis

Generates publication-quality visualizations and comprehensive analysis
of Oxford Nanopore sequencing experiments from sequencing summary data.

Features:
- KDE-based distribution analysis with end-reason overlays
- Peak detection and annotation
- Multi-resolution views (linear, log, zoomed)
- Temporal and spatial analysis
- End-reason comparison across all metrics
- Interactive HTML dashboard

Usage:
    comprehensive_analysis.py /path/to/experiment --output /path/to/output
    comprehensive_analysis.py --summary /path/to/sequencing_summary.txt -o output/
"""

import argparse
import json
import sys
import webbrowser
from pathlib import Path
from datetime import datetime

try:
    import numpy as np
    import pandas as pd
    HAS_DEPS = True
except ImportError as e:
    HAS_DEPS = False
    MISSING_DEP = str(e)

# Import plotting functions
try:
    from plotting import (
        plot_length_kde_by_end_reason,
        plot_quality_kde_by_end_reason,
        plot_publication_summary,
        calculate_n50,
        format_bp,
        q_to_accuracy,
        END_REASON_COLORS,
        COLORS,
        HAS_MATPLOTLIB
    )
except ImportError:
    # Fallback for standalone execution
    HAS_MATPLOTLIB = False


class ComprehensiveAnalyzer:
    """Comprehensive experiment analysis generator."""

    def __init__(self, experiment_path: Path, output_path: Path, dpi: int = 300):
        self.experiment_path = Path(experiment_path)
        self.output_path = Path(output_path)
        self.figures_path = self.output_path / 'figures'
        self.dpi = dpi
        self.df = None
        self.stats = {}

        # Column mappings
        self.length_col = None
        self.qscore_col = None
        self.time_col = None
        self.channel_col = None
        self.end_reason_col = None

        # Create output directories
        self.figures_path.mkdir(parents=True, exist_ok=True)

    def find_sequencing_summary(self) -> Path:
        """Find sequencing summary file in experiment directory."""
        patterns = [
            'sequencing_summary*.txt',
            '**/sequencing_summary*.txt',
            'summary*.txt',
        ]
        for pattern in patterns:
            matches = list(self.experiment_path.glob(pattern))
            if matches:
                return matches[0]
        return None

    def load_data(self, summary_path: Path = None) -> bool:
        """Load sequencing summary data."""
        if summary_path is None:
            summary_path = self.find_sequencing_summary()

        if summary_path is None or not summary_path.exists():
            print(f"Error: No sequencing summary found in {self.experiment_path}")
            return False

        print(f"Loading: {summary_path}")
        self.df = pd.read_csv(summary_path, sep='\t')
        print(f"  Loaded {len(self.df):,} reads")

        # Identify columns
        self.length_col = next((c for c in ['sequence_length_template', 'sequence_length', 'read_length']
                                if c in self.df.columns), None)
        self.qscore_col = next((c for c in ['mean_qscore_template', 'mean_qscore', 'qscore']
                                if c in self.df.columns), None)
        self.time_col = next((c for c in ['start_time', 'time']
                              if c in self.df.columns), None)
        self.channel_col = next((c for c in ['channel']
                                 if c in self.df.columns), None)
        self.end_reason_col = next((c for c in ['end_reason']
                                    if c in self.df.columns), None)

        # Report columns found
        print(f"  Columns: length={self.length_col}, qscore={self.qscore_col}, "
              f"time={self.time_col}, channel={self.channel_col}, end_reason={self.end_reason_col}")

        return True

    def calculate_statistics(self):
        """Calculate comprehensive statistics."""
        lengths = self.df[self.length_col].values if self.length_col else np.array([])
        qscores = self.df[self.qscore_col].values if self.qscore_col else np.array([])

        self.stats = {
            'total_reads': len(self.df),
            'total_bases': int(np.sum(lengths)) if len(lengths) > 0 else 0,
            'mean_length': float(np.mean(lengths)) if len(lengths) > 0 else 0,
            'median_length': float(np.median(lengths)) if len(lengths) > 0 else 0,
            'n50': int(calculate_n50(lengths)) if len(lengths) > 0 else 0,
            'mean_qscore': float(np.mean(qscores)) if len(qscores) > 0 else 0,
            'median_qscore': float(np.median(qscores)) if len(qscores) > 0 else 0,
            'pass_reads': len(self.df),
            'fail_reads': 0,
            'pass_rate': 100.0,
        }

        # End reason counts
        if self.end_reason_col and self.end_reason_col in self.df.columns:
            end_reasons = self.df[self.end_reason_col].value_counts().to_dict()
            self.stats['end_reasons'] = {str(k): int(v) for k, v in end_reasons.items()}

        print(f"\n=== Statistics ===")
        print(f"Reads: {self.stats['total_reads']:,}")
        print(f"Bases: {format_bp(self.stats['total_bases'])}b")
        print(f"N50: {format_bp(self.stats['n50'])} bp")
        print(f"Mean Q: {self.stats['mean_qscore']:.1f}")

        if 'end_reasons' in self.stats:
            print(f"End reasons: {self.stats['end_reasons']}")

        return self.stats

    def save_statistics(self):
        """Save statistics to JSON."""
        stats_path = self.output_path / 'statistics.json'
        with open(stats_path, 'w') as f:
            json.dump(self.stats, f, indent=2)
        print(f"\nSaved: {stats_path}")

    def generate_all_figures(self, title: str = None):
        """Generate all analysis figures."""
        print("\n=== Generating Figures ===")

        if not HAS_MATPLOTLIB:
            print("Warning: matplotlib not available, skipping figures")
            return

        # Generate end-reason comparison plots
        if self.end_reason_col and self.length_col:
            output = plot_length_kde_by_end_reason(
                self.df, self.figures_path / 'length_by_end_reason.png',
                self.length_col, self.end_reason_col, dpi=self.dpi
            )
            if output:
                print(f"  Generated: {output.name}")

        if self.end_reason_col and self.qscore_col:
            output = plot_quality_kde_by_end_reason(
                self.df, self.figures_path / 'quality_by_end_reason.png',
                self.qscore_col, self.end_reason_col, dpi=self.dpi
            )
            if output:
                print(f"  Generated: {output.name}")

        # Publication summary
        if self.length_col and self.qscore_col and self.end_reason_col:
            output = plot_publication_summary(
                self.df, self.figures_path / 'publication_summary.png',
                self.length_col, self.qscore_col, self.end_reason_col,
                time_col=self.time_col, title=title or "Sequencing Analysis",
                dpi=min(self.dpi, 600)  # Cap at 600 for publication
            )
            if output:
                print(f"  Generated: {output.name}")

    def generate_dashboard(self, title: str = None):
        """Generate HTML dashboard."""
        figures = list(self.figures_path.glob('*.png'))
        figures.sort()

        # Get stats for display
        total_reads = self.stats.get('total_reads', 0)
        total_bases = self.stats.get('total_bases', 0)
        n50 = self.stats.get('n50', 0)
        mean_q = self.stats.get('mean_qscore', 0)

        sp_pct = 0
        if 'end_reasons' in self.stats and 'signal_positive' in self.stats['end_reasons']:
            sp_pct = self.stats['end_reasons']['signal_positive'] / total_reads * 100

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title or 'Experiment Analysis'}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e4e4e4;
            min-height: 100vh;
            padding: 20px;
        }}
        header {{
            text-align: center;
            padding: 40px 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            margin-bottom: 30px;
        }}
        h1 {{ font-size: 2.5em; margin-bottom: 10px; color: #fff; }}
        .stats {{
            display: flex;
            justify-content: center;
            gap: 30px;
            flex-wrap: wrap;
            margin-top: 20px;
        }}
        .stat {{
            background: rgba(46, 134, 171, 0.3);
            padding: 15px 25px;
            border-radius: 10px;
            text-align: center;
        }}
        .stat-value {{ font-size: 1.8em; font-weight: bold; color: #2E86AB; }}
        .stat-label {{ font-size: 0.9em; color: #aaa; margin-top: 5px; }}
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(600px, 1fr));
            gap: 20px;
            padding: 20px 0;
        }}
        .figure-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            overflow: hidden;
            transition: transform 0.2s;
        }}
        .figure-card:hover {{ transform: scale(1.02); }}
        .figure-card img {{ width: 100%; display: block; cursor: pointer; }}
        .figure-title {{
            padding: 15px;
            font-weight: bold;
            background: rgba(0,0,0,0.2);
        }}
        footer {{
            text-align: center;
            padding: 30px;
            color: #888;
            font-size: 0.9em;
        }}
        .modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.9);
            z-index: 1000;
            cursor: pointer;
        }}
        .modal img {{
            max-width: 95%;
            max-height: 95%;
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
        }}
    </style>
</head>
<body>
    <header>
        <h1>{title or 'Experiment Analysis'}</h1>
        <div class="stats">
            <div class="stat">
                <div class="stat-value">{total_reads:,}</div>
                <div class="stat-label">Total Reads</div>
            </div>
            <div class="stat">
                <div class="stat-value">{format_bp(total_bases)}b</div>
                <div class="stat-label">Total Bases</div>
            </div>
            <div class="stat">
                <div class="stat-value">{format_bp(n50)}</div>
                <div class="stat-label">N50</div>
            </div>
            <div class="stat">
                <div class="stat-value">Q{mean_q:.1f}</div>
                <div class="stat-label">Mean Quality</div>
            </div>
            <div class="stat">
                <div class="stat-value">{sp_pct:.1f}%</div>
                <div class="stat-label">signal_positive</div>
            </div>
        </div>
    </header>

    <div class="gallery">
"""
        for fig_path in figures:
            fig_name = fig_path.stem.replace('_', ' ').title()
            html += f"""        <div class="figure-card">
            <img src="figures/{fig_path.name}" alt="{fig_name}" onclick="openModal(this)">
            <div class="figure-title">{fig_name}</div>
        </div>
"""

        html += f"""    </div>

    <footer>
        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | ONT Ecosystem Comprehensive Analysis
    </footer>

    <div id="modal" class="modal" onclick="closeModal()">
        <img id="modal-img" src="" alt="Full size">
    </div>

    <script>
        function openModal(img) {{
            document.getElementById('modal').style.display = 'block';
            document.getElementById('modal-img').src = img.src;
        }}
        function closeModal() {{
            document.getElementById('modal').style.display = 'none';
        }}
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') closeModal();
        }});
    </script>
</body>
</html>"""

        dashboard_path = self.output_path / 'dashboard.html'
        with open(dashboard_path, 'w') as f:
            f.write(html)
        print(f"\nSaved: {dashboard_path}")
        return dashboard_path

    def run(self, summary_path: Path = None, title: str = None, open_browser: bool = False):
        """Run complete analysis pipeline."""
        if not self.load_data(summary_path):
            return False

        self.calculate_statistics()
        self.save_statistics()
        self.generate_all_figures(title)
        dashboard = self.generate_dashboard(title)

        if open_browser and dashboard:
            webbrowser.open(f'file://{dashboard.absolute()}')

        print(f"\n=== Analysis Complete ===")
        print(f"Output: {self.output_path}")
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive ONT Experiment Analysis with End-Reason Comparisons",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Analyze experiment directory
    comprehensive_analysis.py /path/to/experiment -o output/

    # From sequencing summary directly
    comprehensive_analysis.py --summary /path/to/sequencing_summary.txt -o output/

    # With custom title and open browser
    comprehensive_analysis.py /path/to/exp -o output/ --title "My Experiment" --open-browser

Features:
    - KDE-based distributions with semi-transparent end-reason overlays
    - Consistent color scheme across all figures
    - Publication-quality output (up to 600 DPI)
    - Interactive HTML dashboard
        """
    )
    parser.add_argument("experiment_path", nargs='?', help="Path to experiment directory")
    parser.add_argument("--output", "-o", required=True, help="Output directory")
    parser.add_argument("--summary", help="Path to sequencing_summary.txt (overrides auto-detection)")
    parser.add_argument("--title", help="Custom title for figures and dashboard")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for figures (default: 300)")
    parser.add_argument("--open-browser", action="store_true", help="Open dashboard in browser when done")

    args = parser.parse_args()

    if not HAS_DEPS:
        print(f"Error: Missing dependencies: {MISSING_DEP}")
        print("Install with: pip install numpy pandas matplotlib scipy")
        sys.exit(1)

    experiment_path = Path(args.experiment_path) if args.experiment_path else Path('.')
    if args.summary:
        summary_path = Path(args.summary)
        experiment_path = summary_path.parent
    else:
        summary_path = None

    analyzer = ComprehensiveAnalyzer(
        experiment_path=experiment_path,
        output_path=Path(args.output),
        dpi=args.dpi
    )

    title = args.title or experiment_path.name
    success = analyzer.run(summary_path=summary_path, title=title, open_browser=args.open_browser)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
