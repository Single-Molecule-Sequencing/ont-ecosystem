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
import time
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


def mean_qscore_from_array(qscores: 'np.ndarray') -> float:
    """
    Calculate mean Q-score correctly via probability space.

    Q-scores are logarithmic (Phred scale), so we must:
    1. Convert each Q to error probability: P = 10^(-Q/10)
    2. Average the probabilities
    3. Convert back to Q-score: Q = -10 * log10(P_avg)
    """
    if len(qscores) == 0:
        return 0.0
    probs = np.power(10, -qscores / 10)
    mean_prob = np.mean(probs)
    if mean_prob <= 0:
        return 60.0  # Cap at Q60
    return -10 * np.log10(mean_prob)

# Import plotting functions
try:
    from plotting import (
        plot_length_kde_by_end_reason,
        plot_quality_kde_by_end_reason,
        plot_publication_summary,
        plot_temporal_evolution,
        plot_channel_analysis,
        plot_quality_length_correlation,
        plot_hourly_evolution,
        plot_overview_summary,
        plot_2d_density_by_end_reason,
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


# Default sample size for quick analysis
DEFAULT_SAMPLE_SIZE = 50000


class ComprehensiveAnalyzer:
    """Comprehensive experiment analysis generator."""

    def __init__(self, experiment_path: Path, output_path: Path, dpi: int = 300,
                 full_data: bool = False, sample_size: int = DEFAULT_SAMPLE_SIZE):
        self.experiment_path = Path(experiment_path)
        self.output_path = Path(output_path)
        self.figures_path = self.output_path / 'figures'
        self.dpi = dpi
        self.full_data = full_data
        self.sample_size = sample_size
        self.df = None
        self.df_full = None  # Keep full data for statistics
        self.stats = {}
        self.is_sampled = False
        self.total_reads = 0
        self.figure_generation_time = 0  # seconds
        self.estimated_full_time = None  # seconds

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
        """Load sequencing summary data with optional stratified sampling."""
        if summary_path is None:
            summary_path = self.find_sequencing_summary()

        if summary_path is None or not summary_path.exists():
            print(f"Error: No sequencing summary found in {self.experiment_path}")
            return False

        print(f"Loading: {summary_path}")
        self.df_full = pd.read_csv(summary_path, sep='\t')
        self.total_reads = len(self.df_full)
        print(f"  Loaded {self.total_reads:,} reads")

        # Identify columns first (needed for stratified sampling)
        self.length_col = next((c for c in ['sequence_length_template', 'sequence_length', 'read_length']
                                if c in self.df_full.columns), None)
        self.qscore_col = next((c for c in ['mean_qscore_template', 'mean_qscore', 'qscore']
                                if c in self.df_full.columns), None)
        self.time_col = next((c for c in ['start_time', 'time']
                              if c in self.df_full.columns), None)
        self.channel_col = next((c for c in ['channel']
                                 if c in self.df_full.columns), None)
        self.end_reason_col = next((c for c in ['end_reason']
                                    if c in self.df_full.columns), None)

        # Apply sampling if not using full data and dataset is large enough
        if not self.full_data and self.total_reads > self.sample_size:
            self.is_sampled = True
            print(f"\n  [SAMPLING] Dataset has {self.total_reads:,} reads > {self.sample_size:,} threshold")

            # Stratified sampling by end_reason to maintain proportions
            if self.end_reason_col and self.end_reason_col in self.df_full.columns:
                print(f"  [SAMPLING] Using stratified sampling by end_reason")
                sampled_dfs = []
                for er in self.df_full[self.end_reason_col].unique():
                    er_df = self.df_full[self.df_full[self.end_reason_col] == er]
                    proportion = len(er_df) / self.total_reads
                    n_sample = max(10, int(self.sample_size * proportion))
                    if len(er_df) > n_sample:
                        sampled_dfs.append(er_df.sample(n=n_sample, random_state=42))
                    else:
                        sampled_dfs.append(er_df)
                self.df = pd.concat(sampled_dfs, ignore_index=True)
            else:
                # Random sampling if no end_reason column
                self.df = self.df_full.sample(n=self.sample_size, random_state=42)

            print(f"  [SAMPLING] Using {len(self.df):,} sampled reads for visualization")
            print(f"  [SAMPLING] NOTE: Run with --full flag to use all {self.total_reads:,} reads")
        else:
            self.df = self.df_full
            if self.full_data and self.total_reads > self.sample_size:
                print(f"  [FULL DATA] Using all {self.total_reads:,} reads (--full flag enabled)")

        # Report columns found
        print(f"  Columns: length={self.length_col}, qscore={self.qscore_col}, "
              f"time={self.time_col}, channel={self.channel_col}, end_reason={self.end_reason_col}")

        return True

    def calculate_statistics(self):
        """Calculate comprehensive statistics from FULL data (not sampled)."""
        # Always use full data for statistics
        df_stats = self.df_full if self.df_full is not None else self.df
        lengths = df_stats[self.length_col].values if self.length_col else np.array([])
        qscores = df_stats[self.qscore_col].values if self.qscore_col else np.array([])

        self.stats = {
            'total_reads': self.total_reads,  # Always report full count
            'sampled_reads': len(self.df) if self.is_sampled else None,
            'is_sampled': self.is_sampled,
            'total_bases': int(np.sum(lengths)) if len(lengths) > 0 else 0,
            'mean_length': float(np.mean(lengths)) if len(lengths) > 0 else 0,
            'median_length': float(np.median(lengths)) if len(lengths) > 0 else 0,
            'n50': int(calculate_n50(lengths)) if len(lengths) > 0 else 0,
            'mean_qscore': float(mean_qscore_from_array(qscores)) if len(qscores) > 0 else 0,
            'median_qscore': float(np.median(qscores)) if len(qscores) > 0 else 0,
            'pass_reads': len(self.df),
            'fail_reads': 0,
            'pass_rate': 100.0,
        }

        # End reason counts (from full data)
        if self.end_reason_col and self.end_reason_col in df_stats.columns:
            end_reasons = df_stats[self.end_reason_col].value_counts().to_dict()
            self.stats['end_reasons'] = {str(k): int(v) for k, v in end_reasons.items()}

        print(f"\n=== Statistics (from full dataset) ===")
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
        """Generate all analysis figures with timing for runtime estimation."""
        print("\n=== Generating Figures ===")

        if not HAS_MATPLOTLIB:
            print("Warning: matplotlib not available, skipping figures")
            return

        # Build title with sampling annotation
        base_title = title or "Experiment Analysis"
        if self.is_sampled:
            sample_note = f" [SAMPLED: {len(self.df):,} of {self.total_reads:,} reads]"
            print(f"  NOTE: Figures use {len(self.df):,} sampled reads (stratified by end_reason)")
            print(f"  NOTE: Run with --full flag for final publication figures\n")
        else:
            sample_note = f" [{self.total_reads:,} reads]"

        # Start timing
        start_time = time.time()

        # 1. Quick overview summary (first for immediate viewing)
        if self.length_col and self.qscore_col and self.end_reason_col:
            output = plot_overview_summary(
                self.df, self.figures_path / '01_overview_summary.png',
                self.length_col, self.qscore_col, self.end_reason_col,
                time_col=self.time_col, channel_col=self.channel_col,
                title=base_title + sample_note, dpi=self.dpi
            )
            if output:
                print(f"  Generated: {output.name}")

        # 2. Read length KDE by end reason
        if self.end_reason_col and self.length_col:
            output = plot_length_kde_by_end_reason(
                self.df, self.figures_path / '02_length_by_end_reason.png',
                self.length_col, self.end_reason_col, dpi=self.dpi
            )
            if output:
                print(f"  Generated: {output.name}")

        # 3. Quality KDE by end reason
        if self.end_reason_col and self.qscore_col:
            output = plot_quality_kde_by_end_reason(
                self.df, self.figures_path / '03_quality_by_end_reason.png',
                self.qscore_col, self.end_reason_col, dpi=self.dpi
            )
            if output:
                print(f"  Generated: {output.name}")

        # 4. Quality-length correlation analysis
        if self.length_col and self.qscore_col and self.end_reason_col:
            output = plot_quality_length_correlation(
                self.df, self.figures_path / '04_quality_length_correlation.png',
                self.length_col, self.qscore_col, self.end_reason_col, dpi=self.dpi
            )
            if output:
                print(f"  Generated: {output.name}")

        # 5. 2D density by end reason
        if self.length_col and self.qscore_col and self.end_reason_col:
            output = plot_2d_density_by_end_reason(
                self.df, self.figures_path / '05_2d_density_by_end_reason.png',
                self.length_col, self.qscore_col, self.end_reason_col, dpi=self.dpi
            )
            if output:
                print(f"  Generated: {output.name}")

        # 6. Temporal evolution (if time data available)
        if self.time_col and self.length_col and self.qscore_col and self.end_reason_col:
            output = plot_temporal_evolution(
                self.df, self.figures_path / '06_temporal_evolution.png',
                self.length_col, self.qscore_col, self.end_reason_col,
                self.time_col, dpi=self.dpi
            )
            if output:
                print(f"  Generated: {output.name}")

        # 7. Hourly evolution (if time data available)
        if self.time_col and self.length_col and self.qscore_col and self.end_reason_col:
            output = plot_hourly_evolution(
                self.df, self.figures_path / '07_hourly_evolution.png',
                self.length_col, self.qscore_col, self.end_reason_col,
                self.time_col, dpi=self.dpi
            )
            if output:
                print(f"  Generated: {output.name}")

        # 8. Channel analysis (if channel data available)
        if self.channel_col and self.length_col and self.qscore_col and self.end_reason_col:
            output = plot_channel_analysis(
                self.df, self.figures_path / '08_channel_analysis.png',
                self.length_col, self.qscore_col, self.end_reason_col,
                self.channel_col, dpi=self.dpi
            )
            if output:
                print(f"  Generated: {output.name}")

        # 9. Publication-ready summary (high DPI)
        if self.length_col and self.qscore_col and self.end_reason_col:
            pub_title = base_title + sample_note
            output = plot_publication_summary(
                self.df, self.figures_path / '09_publication_summary.png',
                self.length_col, self.qscore_col, self.end_reason_col,
                time_col=self.time_col, title=pub_title,
                dpi=min(self.dpi, 600)  # Cap at 600 for publication
            )
            if output:
                print(f"  Generated: {output.name}")

        # Calculate timing and estimate
        self.figure_generation_time = time.time() - start_time
        print(f"\n  Figure generation time: {self.figure_generation_time:.1f}s")

        if self.is_sampled:
            # Estimate full runtime based on linear scaling with some overhead
            # Actual scaling may vary based on complexity, but linear is a reasonable estimate
            scaling_factor = self.total_reads / len(self.df)
            # Add 20% overhead for larger datasets (memory, disk I/O)
            overhead_factor = 1.2
            self.estimated_full_time = self.figure_generation_time * scaling_factor * overhead_factor
            # Format for display
            if self.estimated_full_time < 60:
                time_str = f"{self.estimated_full_time:.0f} seconds"
            elif self.estimated_full_time < 3600:
                time_str = f"{self.estimated_full_time/60:.1f} minutes"
            else:
                time_str = f"{self.estimated_full_time/3600:.1f} hours"
            print(f"  Estimated time for full {self.total_reads:,} reads: ~{time_str}")

    def generate_dashboard(self, title: str = None):
        """Generate HTML dashboard."""
        figures = list(self.figures_path.glob('*.png'))
        figures.sort()

        # Get stats for display
        total_reads = self.stats.get('total_reads', 0)
        sampled_reads = self.stats.get('sampled_reads', None)
        total_bases = self.stats.get('total_bases', 0)
        n50 = self.stats.get('n50', 0)
        mean_q = self.stats.get('mean_qscore', 0)

        sp_pct = 0
        if 'end_reasons' in self.stats and 'signal_positive' in self.stats['end_reasons']:
            sp_pct = self.stats['end_reasons']['signal_positive'] / total_reads * 100

        # Sampling banner with runtime estimate
        if self.is_sampled:
            # Format estimated time
            if self.estimated_full_time and self.estimated_full_time > 0:
                if self.estimated_full_time < 60:
                    est_str = f"{self.estimated_full_time:.0f} seconds"
                elif self.estimated_full_time < 3600:
                    est_str = f"{self.estimated_full_time/60:.1f} minutes"
                else:
                    est_str = f"{self.estimated_full_time/3600:.1f} hours"
                time_note = f"<br><em>Estimated time for full analysis: ~{est_str}</em>"
            else:
                time_note = ""
            sampling_banner = f"""
        <div class="sampling-banner">
            <strong>SAMPLED DATA:</strong> Figures generated from {sampled_reads:,} randomly sampled reads
            (stratified by end_reason) out of {total_reads:,} total reads.
            <br>Run with <code>--full</code> flag to generate final publication figures using all data.{time_note}
        </div>"""
        else:
            sampling_banner = ""

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
        .sampling-banner {{
            background: rgba(243, 156, 18, 0.3);
            border: 2px solid #f39c12;
            border-radius: 10px;
            padding: 15px 20px;
            margin-bottom: 20px;
            text-align: center;
            color: #fff;
        }}
        .sampling-banner code {{
            background: rgba(0,0,0,0.3);
            padding: 2px 8px;
            border-radius: 4px;
            font-family: monospace;
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
{sampling_banner}
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
    # Quick analysis (sampled, <=50K reads)
    comprehensive_analysis.py /path/to/experiment -o output/

    # Full analysis (all reads - for publication)
    comprehensive_analysis.py /path/to/experiment -o output/ --full

    # Custom sample size
    comprehensive_analysis.py /path/to/experiment -o output/ --sample-size 100000

    # From sequencing summary directly
    comprehensive_analysis.py --summary /path/to/sequencing_summary.txt -o output/

    # With custom title and open browser
    comprehensive_analysis.py /path/to/exp -o output/ --title "My Experiment" --open-browser

Features:
    - KDE-based distributions with semi-transparent end-reason overlays
    - Consistent color scheme across all figures
    - Stratified sampling by end_reason (maintains proportions)
    - Statistics always computed from full data
    - Publication-quality output (up to 600 DPI)
    - Interactive HTML dashboard
        """
    )
    parser.add_argument("experiment_path", nargs='?', help="Path to experiment directory")
    parser.add_argument("--output", "-o", required=True, help="Output directory")
    parser.add_argument("--summary", help="Path to sequencing_summary.txt (overrides auto-detection)")
    parser.add_argument("--title", help="Custom title for figures and dashboard")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for figures (default: 300)")
    parser.add_argument("--full", action="store_true",
                        help="Use all reads (default: sample <=50,000 for quick analysis)")
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE,
                        help=f"Number of reads to sample (default: {DEFAULT_SAMPLE_SIZE:,})")
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
        dpi=args.dpi,
        full_data=args.full,
        sample_size=args.sample_size
    )

    title = args.title or experiment_path.name
    success = analyzer.run(summary_path=summary_path, title=title, open_browser=args.open_browser)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
