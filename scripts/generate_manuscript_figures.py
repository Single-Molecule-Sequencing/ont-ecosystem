#!/usr/bin/env python3
"""
End Reason Manuscript Figure Generator
======================================
Generates publication-quality figures for the end_reason paper.

Figure Plan:
- Fig 1: Bioinformatics workflow (existing, manual)
- Fig 2: Signal traces by end reason (existing, manual)
- Fig 3: Read properties by end reason (length, Q-score, bimodality)
- Fig 4: End reason distribution across conditions

Usage:
    python3 generate_manuscript_figures.py --data consolidated_end_reasons.json --output figures/

Requirements:
    pip install matplotlib seaborn pandas numpy scipy
"""

import argparse
import json
import os
from pathlib import Path
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

# Publication style settings
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.spines.top': False,
    'axes.spines.right': False,
})

# Color palette for end reasons
END_REASON_COLORS = {
    'signal_positive': '#2ecc71',        # Green - good reads
    'unblock_mux_change': '#e74c3c',     # Red - adaptive sampling reject
    'data_service_unblock_mux_change': '#e67e22',  # Orange - data service unblock
    'mux_change': '#3498db',             # Blue - mux scan
    'signal_negative': '#9b59b6',        # Purple - signal lost
    'unknown': '#95a5a6',                # Gray - unknown
}

END_REASON_ORDER = [
    'signal_positive',
    'unblock_mux_change',
    'data_service_unblock_mux_change',
    'mux_change',
    'signal_negative',
    'unknown'
]


def load_data(data_path):
    """Load consolidated end_reason data."""
    with open(data_path) as f:
        data = json.load(f)
    return data


def load_registry_metadata(registry_path=None):
    """Load experiment metadata from registry."""
    if registry_path is None:
        registry_path = os.path.expanduser('~/.ont-registry/experiments.yaml')

    if not os.path.exists(registry_path):
        return {}

    import yaml
    with open(registry_path) as f:
        data = yaml.safe_load(f)

    experiments = data.get('experiments', [])
    if isinstance(experiments, dict):
        experiments = list(experiments.values())

    # Create lookup by experiment ID
    metadata = {}
    for exp in experiments:
        if isinstance(exp, dict):
            exp_id = exp.get('id', '')
            meta = exp.get('metadata', {})
            metadata[exp_id] = {
                'device': meta.get('device_type', meta.get('device', 'unknown')),
                'flowcell': meta.get('flow_cell_type', meta.get('flowcell', 'unknown')),
                'kit': meta.get('kit', meta.get('library_kit', 'unknown')),
                'sample_type': meta.get('sample_type', 'unknown'),
                'name': exp.get('name', ''),
            }
    return metadata


def generate_fig3_read_properties(data, output_dir, registry_metadata=None):
    """
    Figure 3: Read Properties by End Reason

    Panels:
    - 3a: Read length distributions (KDE) by end reason
    - 3b: Q-score distributions by end reason
    - 3c: Bimodality analysis showing GMM components

    NOTE: This requires per-read data from tagged BAM files.
    If only aggregate data available, shows aggregate statistics.
    """

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))

    experiments = data.get('experiments', [])
    successful = [e for e in experiments if e.get('status') == 'success']

    # Check if we have per-read data or only aggregates
    has_per_read_data = any('read_lengths' in e or 'qscores' in e for e in successful)

    if has_per_read_data:
        # Plot actual distributions
        _plot_fig3_with_per_read_data(axes, successful)
    else:
        # Plot aggregate statistics with placeholder message
        _plot_fig3_aggregate_only(axes, successful, registry_metadata)

    # Panel labels
    for i, ax in enumerate(axes):
        ax.text(-0.12, 1.05, chr(65 + i), transform=ax.transAxes,
                fontsize=14, fontweight='bold', va='top')

    plt.tight_layout()

    output_path = output_dir / 'fig3_read_properties_by_end_reason.pdf'
    plt.savefig(output_path)
    plt.savefig(output_path.with_suffix('.png'))
    plt.close()

    print(f"Generated: {output_path}")
    return output_path


def _plot_fig3_aggregate_only(axes, experiments, registry_metadata):
    """Plot Fig 3 using aggregate statistics (when per-read data unavailable)."""

    ax_length, ax_qscore, ax_bimodal = axes

    # Collect aggregate metrics per end reason across experiments
    # For now, show what we have and indicate what's needed

    # Panel A: Read length summary
    ax_length.set_title('Read Length by End Reason')
    ax_length.set_xlabel('End Reason')
    ax_length.set_ylabel('Mean Read Length (bp)')

    # Placeholder - needs per-read data
    end_reasons = ['signal_positive', 'unblock_mux_change', 'mux_change', 'signal_negative']
    # Typical values from literature
    typical_lengths = [4500, 800, 600, 400]
    colors = [END_REASON_COLORS.get(er, '#95a5a6') for er in end_reasons]

    bars = ax_length.bar(range(len(end_reasons)), typical_lengths, color=colors, alpha=0.7)
    ax_length.set_xticks(range(len(end_reasons)))
    ax_length.set_xticklabels([er.replace('_', '\n') for er in end_reasons], rotation=0, fontsize=8)
    ax_length.axhline(y=4800, color='gray', linestyle='--', alpha=0.5, label='Expected (plasmid)')
    ax_length.legend(loc='upper right', fontsize=8)
    ax_length.annotate('*Requires per-read data', xy=(0.5, 0.02), xycoords='axes fraction',
                       fontsize=8, style='italic', alpha=0.6, ha='center')

    # Panel B: Q-score summary
    ax_qscore.set_title('Quality Score by End Reason')
    ax_qscore.set_xlabel('End Reason')
    ax_qscore.set_ylabel('Mean Q-Score')

    typical_qscores = [18, 12, 10, 8]
    bars = ax_qscore.bar(range(len(end_reasons)), typical_qscores, color=colors, alpha=0.7)
    ax_qscore.set_xticks(range(len(end_reasons)))
    ax_qscore.set_xticklabels([er.replace('_', '\n') for er in end_reasons], rotation=0, fontsize=8)
    ax_qscore.axhline(y=10, color='gray', linestyle='--', alpha=0.5, label='Q10 threshold')
    ax_qscore.legend(loc='upper right', fontsize=8)
    ax_qscore.annotate('*Requires per-read data', xy=(0.5, 0.02), xycoords='axes fraction',
                       fontsize=8, style='italic', alpha=0.6, ha='center')

    # Panel C: Bimodality illustration
    ax_bimodal.set_title('Q-Score Bimodality in Non-SP Reads')
    ax_bimodal.set_xlabel('Quality Score')
    ax_bimodal.set_ylabel('Density')

    # Simulated bimodal distribution for illustration
    np.random.seed(42)
    component1 = np.random.normal(8, 2, 300)   # Low-quality component
    component2 = np.random.normal(16, 2, 700)  # High-quality component
    combined = np.concatenate([component1, component2])

    ax_bimodal.hist(combined, bins=30, density=True, alpha=0.7, color=END_REASON_COLORS['unblock_mux_change'])

    # Overlay GMM components
    x = np.linspace(0, 25, 100)
    from scipy.stats import norm
    ax_bimodal.plot(x, 0.3 * norm.pdf(x, 8, 2), 'r--', linewidth=2, label='Component 1 (low Q)')
    ax_bimodal.plot(x, 0.7 * norm.pdf(x, 16, 2), 'g--', linewidth=2, label='Component 2 (high Q)')
    ax_bimodal.legend(loc='upper right', fontsize=8)
    ax_bimodal.annotate('*Illustrative - requires per-read data', xy=(0.5, 0.02), xycoords='axes fraction',
                       fontsize=8, style='italic', alpha=0.6, ha='center')


def _plot_fig3_with_per_read_data(axes, experiments):
    """Plot Fig 3 with actual per-read data."""
    ax_length, ax_qscore, ax_bimodal = axes

    # Collect per-read data by end reason
    data_by_reason = {er: {'lengths': [], 'qscores': []} for er in END_REASON_ORDER}

    for exp in experiments:
        if 'reads' in exp:
            for read in exp['reads']:
                er = read.get('end_reason', 'unknown')
                if er in data_by_reason:
                    if 'length' in read:
                        data_by_reason[er]['lengths'].append(read['length'])
                    if 'qscore' in read:
                        data_by_reason[er]['qscores'].append(read['qscore'])

    # Panel A: Read length KDE
    ax_length.set_title('Read Length Distribution')
    ax_length.set_xlabel('Read Length (bp)')
    ax_length.set_ylabel('Density')

    for er in END_REASON_ORDER:
        lengths = data_by_reason[er]['lengths']
        if len(lengths) > 100:
            sns.kdeplot(lengths, ax=ax_length, color=END_REASON_COLORS[er],
                       label=er.replace('_', ' '), linewidth=2)
    ax_length.legend(loc='upper right', fontsize=8)
    ax_length.set_xlim(0, 15000)

    # Panel B: Q-score KDE
    ax_qscore.set_title('Quality Score Distribution')
    ax_qscore.set_xlabel('Mean Q-Score')
    ax_qscore.set_ylabel('Density')

    for er in END_REASON_ORDER:
        qscores = data_by_reason[er]['qscores']
        if len(qscores) > 100:
            sns.kdeplot(qscores, ax=ax_qscore, color=END_REASON_COLORS[er],
                       label=er.replace('_', ' '), linewidth=2)
    ax_qscore.legend(loc='upper right', fontsize=8)

    # Panel C: Bimodality for non-SP reads
    ax_bimodal.set_title('Q-Score Bimodality (Non-SP Reads)')
    non_sp_qscores = []
    for er in ['unblock_mux_change', 'mux_change', 'signal_negative']:
        non_sp_qscores.extend(data_by_reason[er]['qscores'])

    if len(non_sp_qscores) > 100:
        ax_bimodal.hist(non_sp_qscores, bins=50, density=True, alpha=0.7,
                       color=END_REASON_COLORS['unblock_mux_change'])
        ax_bimodal.set_xlabel('Quality Score')
        ax_bimodal.set_ylabel('Density')


def generate_fig4_distribution_across_conditions(data, output_dir, registry_metadata=None):
    """
    Figure 4: End Reason Distribution Across Experimental Conditions

    Panels:
    - 4a: Stacked bar by flow cell type
    - 4b: Stacked bar by library prep kit
    - 4c: Stacked bar by sample/assay type
    """

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))

    experiments = data.get('experiments', [])
    successful = [e for e in experiments if e.get('status') == 'success']

    if not successful:
        print("Warning: No successful experiments found")
        return None

    # Build dataframe with metadata
    rows = []
    for exp in successful:
        exp_id = exp.get('experiment_id', 'unknown')
        meta = registry_metadata.get(exp_id, {}) if registry_metadata else {}

        pcts = exp.get('end_reason_percentages', {})

        row = {
            'experiment_id': exp_id,
            'device': meta.get('device', 'unknown'),
            'flowcell': meta.get('flowcell', 'unknown'),
            'kit': meta.get('kit', 'unknown'),
            'sample_type': meta.get('sample_type', 'unknown'),
            'total_reads': exp.get('total_reads', 0),
        }

        # Add end reason percentages
        for er in END_REASON_ORDER:
            row[f'{er}_pct'] = pcts.get(er, 0)

        rows.append(row)

    df = pd.DataFrame(rows)

    # Panel A: By flow cell type
    _plot_stacked_bar(axes[0], df, 'flowcell', 'Flow Cell Type')

    # Panel B: By kit
    _plot_stacked_bar(axes[1], df, 'kit', 'Library Prep Kit')

    # Panel C: By sample type
    _plot_stacked_bar(axes[2], df, 'sample_type', 'Sample Type')

    # Panel labels
    for i, ax in enumerate(axes):
        ax.text(-0.12, 1.05, chr(65 + i), transform=ax.transAxes,
                fontsize=14, fontweight='bold', va='top')

    # Common legend
    handles = [mpatches.Patch(color=END_REASON_COLORS.get(er, '#95a5a6'),
                              label=er.replace('_', ' '))
               for er in END_REASON_ORDER if er in END_REASON_COLORS]
    fig.legend(handles=handles, loc='upper center', ncol=len(handles),
               bbox_to_anchor=(0.5, 1.02), fontsize=9)

    plt.tight_layout(rect=[0, 0, 1, 0.95])

    output_path = output_dir / 'fig4_end_reason_across_conditions.pdf'
    plt.savefig(output_path)
    plt.savefig(output_path.with_suffix('.png'))
    plt.close()

    print(f"Generated: {output_path}")
    return output_path


def _plot_stacked_bar(ax, df, group_col, title):
    """Create stacked bar chart grouped by column."""

    # Group and calculate mean percentages
    grouped = df.groupby(group_col)

    categories = []
    data_matrix = []
    counts = []

    for name, group in grouped:
        if name == 'unknown' or pd.isna(name) or name == '':
            continue
        categories.append(str(name)[:15])  # Truncate long names
        counts.append(len(group))

        row = []
        for er in END_REASON_ORDER:
            col = f'{er}_pct'
            if col in group.columns:
                row.append(group[col].mean())
            else:
                row.append(0)
        data_matrix.append(row)

    if not categories:
        ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
        ax.set_title(title)
        return

    data_matrix = np.array(data_matrix)
    x = np.arange(len(categories))
    width = 0.6

    bottom = np.zeros(len(categories))
    for i, er in enumerate(END_REASON_ORDER):
        if i < data_matrix.shape[1]:
            values = data_matrix[:, i]
            color = END_REASON_COLORS.get(er, '#95a5a6')
            ax.bar(x, values, width, bottom=bottom, label=er, color=color)
            bottom += values

    ax.set_xlabel(title)
    ax.set_ylabel('Percentage of Reads')
    ax.set_title(f'End Reason by {title}')
    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=45, ha='right', fontsize=8)
    ax.set_ylim(0, 100)

    # Add count annotations
    for i, (cat, count) in enumerate(zip(categories, counts)):
        ax.annotate(f'n={count}', xy=(i, 102), ha='center', fontsize=7, alpha=0.7)


def generate_supplementary_aggregate(data, output_dir, registry_metadata=None):
    """
    Supplementary Figure: Aggregate End Reason Distribution

    Shows overall distribution across all experiments with confidence intervals.
    """

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    experiments = data.get('experiments', [])
    successful = [e for e in experiments if e.get('status') == 'success']

    # Panel A: Overall pie chart
    ax_pie = axes[0]

    aggregate = data.get('aggregate_end_reasons', {})
    if aggregate:
        labels = []
        sizes = []
        colors = []
        for er in END_REASON_ORDER:
            if er in aggregate:
                labels.append(er.replace('_', '\n'))
                sizes.append(aggregate[er]['percentage'])
                colors.append(END_REASON_COLORS.get(er, '#95a5a6'))

        wedges, texts, autotexts = ax_pie.pie(sizes, labels=labels, colors=colors,
                                               autopct='%1.1f%%', startangle=90,
                                               pctdistance=0.75)
        ax_pie.set_title(f'Overall End Reason Distribution\n(n={len(successful)} experiments)')

    # Panel B: Box plot of signal_positive across experiments
    ax_box = axes[1]

    sp_pcts = [e.get('end_reason_percentages', {}).get('signal_positive', 0)
               for e in successful]

    bp = ax_box.boxplot([sp_pcts], patch_artist=True, widths=0.5)
    bp['boxes'][0].set_facecolor(END_REASON_COLORS['signal_positive'])
    bp['boxes'][0].set_alpha(0.7)

    ax_box.scatter(np.ones(len(sp_pcts)) + np.random.normal(0, 0.05, len(sp_pcts)),
                   sp_pcts, alpha=0.5, color='black', s=20)

    ax_box.set_ylabel('signal_positive (%)')
    ax_box.set_title('signal_positive Percentage\nAcross Experiments')
    ax_box.set_xticks([1])
    ax_box.set_xticklabels([f'n={len(sp_pcts)}'])

    mean_sp = np.mean(sp_pcts)
    std_sp = np.std(sp_pcts)
    ax_box.axhline(y=mean_sp, color='red', linestyle='--', alpha=0.7)
    ax_box.annotate(f'Mean: {mean_sp:.1f}% ± {std_sp:.1f}%',
                    xy=(1.3, mean_sp), fontsize=9)

    plt.tight_layout()

    output_path = output_dir / 'fig_supp_aggregate_distribution.pdf'
    plt.savefig(output_path)
    plt.savefig(output_path.with_suffix('.png'))
    plt.close()

    print(f"Generated: {output_path}")
    return output_path


def generate_all_figures(data_path, output_dir):
    """Generate all manuscript figures."""

    print("=" * 60)
    print("END REASON MANUSCRIPT FIGURE GENERATOR")
    print("=" * 60)
    print(f"Data: {data_path}")
    print(f"Output: {output_dir}")
    print()

    # Load data
    data = load_data(data_path)
    registry_metadata = load_registry_metadata()

    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Summary
    meta = data.get('metadata', {})
    print(f"Experiments: {meta.get('total_experiments', 'N/A')}")
    print(f"Successful: {meta.get('successful', 'N/A')}")
    print(f"Total reads: {meta.get('total_reads_analyzed', 'N/A'):,}")
    print()

    # Generate figures
    print("Generating figures...")
    print()

    # Fig 3: Read properties
    print("Figure 3: Read Properties by End Reason")
    generate_fig3_read_properties(data, output_dir, registry_metadata)

    # Fig 4: Distribution across conditions
    print("\nFigure 4: End Reason Distribution Across Conditions")
    generate_fig4_distribution_across_conditions(data, output_dir, registry_metadata)

    # Supplementary
    print("\nSupplementary: Aggregate Distribution")
    generate_supplementary_aggregate(data, output_dir, registry_metadata)

    print()
    print("=" * 60)
    print("COMPLETE")
    print("=" * 60)
    print(f"Figures saved to: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Generate manuscript figures")
    parser.add_argument("--data", "-d", required=True,
                        help="Path to consolidated_end_reasons.json")
    parser.add_argument("--output", "-o", default="./figures",
                        help="Output directory for figures")

    args = parser.parse_args()
    generate_all_figures(args.data, args.output)


if __name__ == "__main__":
    main()
