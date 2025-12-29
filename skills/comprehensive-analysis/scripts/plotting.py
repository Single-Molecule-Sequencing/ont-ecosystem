#!/usr/bin/env python3
"""
Plotting library for comprehensive ONT sequencing analysis.

Provides KDE-based distributions, end-reason comparisons, and publication-quality figures.
All plots use consistent color schemes and semi-transparent overlays.
"""

import numpy as np
from pathlib import Path

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec
    from scipy import stats
    from scipy.signal import find_peaks, savgol_filter
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# Consistent color scheme for end reasons
END_REASON_COLORS = {
    'signal_positive': '#27ae60',      # Green - normal completion
    'unblock_mux_change': '#3498db',   # Blue - unblock
    'data_service_unblock_mux_change': '#9b59b6',  # Purple
    'signal_negative': '#e74c3c',      # Red - signal lost
    'mux_change': '#f39c12',           # Orange - mux change
}

# General colors
COLORS = {
    'all_reads': '#2c3e50',            # Dark gray for all reads
    'primary': '#2E86AB',
    'secondary': '#A23B72',
    'accent': '#F18F01',
    'success': '#27ae60',
    'warning': '#f39c12',
    'danger': '#e74c3c',
}


def format_bp(bp):
    """Format base pairs with K/M suffix."""
    if bp >= 1_000_000:
        return f"{bp/1_000_000:.1f}M"
    elif bp >= 1_000:
        return f"{bp/1_000:.1f}K"
    return f"{bp:.0f}"


def calculate_n50(lengths):
    """Calculate N50 from array of lengths."""
    sorted_lengths = np.sort(lengths)[::-1]
    cumsum = np.cumsum(sorted_lengths)
    total = cumsum[-1]
    idx = np.searchsorted(cumsum, total / 2)
    return sorted_lengths[min(idx, len(sorted_lengths) - 1)]


def q_to_accuracy(q):
    """Convert Q-score to accuracy percentage."""
    return (1 - 10 ** (-q / 10)) * 100


def detect_peaks(y, height_threshold=0.05, distance=50):
    """Detect peaks in array with smoothing."""
    try:
        window = min(51, max(5, len(y)//4*2+1))
        y_smooth = savgol_filter(y, window_length=window, polyorder=3)
        peaks, props = find_peaks(
            y_smooth, height=max(y_smooth) * height_threshold,
            distance=distance, prominence=max(y_smooth) * 0.02
        )
        return peaks, props
    except Exception:
        return [], {}


def plot_length_kde_by_end_reason(df, output_path, length_col, end_reason_col, dpi=300):
    """Generate read length KDE with end-reason breakdown."""
    if not HAS_MATPLOTLIB:
        return None

    lengths = df[length_col].values
    end_reasons = df[end_reason_col].unique()
    x_max = np.percentile(lengths, 99.5)
    x = np.linspace(0, x_max, 1000)

    fig = plt.figure(figsize=(18, 14))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    # Panel 1: All reads with end-reason overlay
    ax1 = fig.add_subplot(gs[0, :2])
    kde_all = stats.gaussian_kde(lengths, bw_method=0.05)
    y_all = kde_all(x)
    ax1.fill_between(x, y_all, alpha=0.2, color=COLORS['all_reads'],
                    label=f'All reads (n={len(lengths):,})')
    ax1.plot(x, y_all, color=COLORS['all_reads'], linewidth=2.5, linestyle='--')

    for end_reason in sorted(end_reasons):
        mask = df[end_reason_col] == end_reason
        er_lengths = df.loc[mask, length_col].values
        if len(er_lengths) > 100:
            kde_er = stats.gaussian_kde(er_lengths, bw_method=0.05)
            y_er = kde_er(x)
            scale = len(er_lengths) / len(lengths)
            y_scaled = y_er * scale
            color = END_REASON_COLORS.get(end_reason, COLORS['primary'])
            ax1.fill_between(x, y_scaled, alpha=0.3, color=color,
                           label=f'{end_reason} (n={len(er_lengths):,}, {scale*100:.1f}%)')
            ax1.plot(x, y_scaled, color=color, linewidth=1.5)

    ax1.set_xlabel('Read Length (bp)', fontsize=12)
    ax1.set_ylabel('Density (scaled by proportion)', fontsize=12)
    ax1.set_title('Read Length Distribution by End Reason', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper right', fontsize=9)
    ax1.set_xlim(0, x_max)

    # Panel 2: Statistics
    ax2 = fig.add_subplot(gs[0, 2])
    ax2.axis('off')
    stats_text = "End Reason Statistics\n" + "="*40 + "\n\n"
    for end_reason in sorted(end_reasons):
        mask = df[end_reason_col] == end_reason
        er_lengths = df.loc[mask, length_col].values
        if len(er_lengths) > 0:
            n50 = calculate_n50(er_lengths)
            stats_text += f"{end_reason}:\n"
            stats_text += f"  N: {len(er_lengths):,} ({len(er_lengths)/len(lengths)*100:.1f}%)\n"
            stats_text += f"  Mean: {np.mean(er_lengths):,.0f} bp\n"
            stats_text += f"  N50: {n50:,} bp\n\n"
    ax2.text(0.05, 0.95, stats_text, transform=ax2.transAxes, fontsize=9,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # Panel 3: Normalized comparison
    ax3 = fig.add_subplot(gs[1, 0])
    for end_reason in sorted(end_reasons):
        mask = df[end_reason_col] == end_reason
        er_lengths = df.loc[mask, length_col].values
        if len(er_lengths) > 100:
            kde_er = stats.gaussian_kde(er_lengths, bw_method=0.05)
            y_er = kde_er(x)
            color = END_REASON_COLORS.get(end_reason, COLORS['primary'])
            ax3.fill_between(x, y_er, alpha=0.25, color=color)
            ax3.plot(x, y_er, color=color, linewidth=1.5, label=end_reason)
    ax3.set_xlabel('Read Length (bp)', fontsize=11)
    ax3.set_ylabel('Density (normalized)', fontsize=11)
    ax3.set_title('Normalized Distributions', fontsize=12, fontweight='bold')
    ax3.legend(fontsize=8)
    ax3.set_xlim(0, x_max)

    # Panel 4: Log scale
    ax4 = fig.add_subplot(gs[1, 1])
    log_lengths = np.log10(lengths[lengths > 0])
    x_log = np.linspace(log_lengths.min(), log_lengths.max(), 500)
    for end_reason in sorted(end_reasons):
        mask = df[end_reason_col] == end_reason
        er_lengths = df.loc[mask, length_col].values
        er_lengths = er_lengths[er_lengths > 0]
        if len(er_lengths) > 100:
            log_er = np.log10(er_lengths)
            kde_er = stats.gaussian_kde(log_er, bw_method=0.05)
            y_er = kde_er(x_log)
            color = END_REASON_COLORS.get(end_reason, COLORS['primary'])
            ax4.fill_between(10**x_log, y_er, alpha=0.25, color=color)
            ax4.plot(10**x_log, y_er, color=color, linewidth=1.5)
    ax4.set_xscale('log')
    ax4.set_xlabel('Read Length (bp, log scale)', fontsize=11)
    ax4.set_ylabel('Density', fontsize=11)
    ax4.set_title('Log Scale Comparison', fontsize=12, fontweight='bold')

    # Panel 5: Box plots
    ax5 = fig.add_subplot(gs[1, 2])
    er_data = []
    er_labels = []
    er_colors = []
    for end_reason in sorted(end_reasons):
        mask = df[end_reason_col] == end_reason
        er_lengths = df.loc[mask, length_col].values
        if len(er_lengths) > 10:
            er_data.append(er_lengths)
            er_labels.append(end_reason.replace('_', '\n'))
            er_colors.append(END_REASON_COLORS.get(end_reason, COLORS['primary']))
    bp = ax5.boxplot(er_data, tick_labels=er_labels, patch_artist=True, showfliers=False)
    for patch, color in zip(bp['boxes'], er_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    ax5.set_ylabel('Read Length (bp)', fontsize=11)
    ax5.set_title('Length Distribution by End Reason', fontsize=12, fontweight='bold')
    ax5.tick_params(axis='x', labelsize=8)

    # Panel 6: CDF comparison
    ax6 = fig.add_subplot(gs[2, 0])
    for end_reason in sorted(end_reasons):
        mask = df[end_reason_col] == end_reason
        er_lengths = df.loc[mask, length_col].values
        if len(er_lengths) > 100:
            sorted_len = np.sort(er_lengths)
            cdf = np.arange(1, len(sorted_len) + 1) / len(sorted_len) * 100
            color = END_REASON_COLORS.get(end_reason, COLORS['primary'])
            ax6.plot(sorted_len, cdf, color=color, linewidth=2, label=end_reason)
    ax6.set_xscale('log')
    ax6.set_xlabel('Read Length (bp)', fontsize=11)
    ax6.set_ylabel('Cumulative %', fontsize=11)
    ax6.set_title('Cumulative Distribution', fontsize=12, fontweight='bold')
    ax6.legend(fontsize=8)
    ax6.set_ylim(0, 100)
    ax6.grid(True, alpha=0.3)

    # Panel 7: N50 bar chart
    ax7 = fig.add_subplot(gs[2, 1])
    n50_data = []
    n50_labels = []
    n50_colors = []
    for end_reason in sorted(end_reasons):
        mask = df[end_reason_col] == end_reason
        er_lengths = df.loc[mask, length_col].values
        if len(er_lengths) > 100:
            n50 = calculate_n50(er_lengths)
            n50_data.append(n50)
            n50_labels.append(end_reason.replace('_', '\n'))
            n50_colors.append(END_REASON_COLORS.get(end_reason, COLORS['primary']))
    bars = ax7.bar(range(len(n50_data)), n50_data, color=n50_colors, alpha=0.7)
    ax7.set_xticks(range(len(n50_data)))
    ax7.set_xticklabels(n50_labels, fontsize=8)
    ax7.set_ylabel('N50 (bp)', fontsize=11)
    ax7.set_title('N50 by End Reason', fontsize=12, fontweight='bold')
    for bar, val in zip(bars, n50_data):
        ax7.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50,
                format_bp(val), ha='center', fontsize=9)

    # Panel 8: Violin plots
    ax8 = fig.add_subplot(gs[2, 2])
    for i, end_reason in enumerate(sorted(end_reasons)):
        mask = df[end_reason_col] == end_reason
        er_lengths = df.loc[mask, length_col].values
        if len(er_lengths) > 100:
            if len(er_lengths) > 5000:
                er_lengths = np.random.choice(er_lengths, 5000, replace=False)
            color = END_REASON_COLORS.get(end_reason, COLORS['primary'])
            parts = ax8.violinplot([er_lengths], positions=[i], showmeans=True, showmedians=True)
            for pc in parts['bodies']:
                pc.set_facecolor(color)
                pc.set_alpha(0.6)
    ax8.set_xticks(range(len(end_reasons)))
    ax8.set_xticklabels([er.replace('_', '\n') for er in sorted(end_reasons)], fontsize=8)
    ax8.set_ylabel('Read Length (bp)', fontsize=11)
    ax8.set_title('Violin Plot Comparison', fontsize=12, fontweight='bold')

    fig.suptitle('Read Length Analysis by End Reason', fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()
    return output_path


def plot_quality_kde_by_end_reason(df, output_path, qscore_col, end_reason_col, dpi=300):
    """Generate quality score KDE with end-reason breakdown."""
    if not HAS_MATPLOTLIB:
        return None

    qscores = df[qscore_col].values
    end_reasons = df[end_reason_col].unique()
    x = np.linspace(0, 40, 500)

    fig = plt.figure(figsize=(18, 14))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    # Panel 1: All reads with end-reason overlay
    ax1 = fig.add_subplot(gs[0, :2])
    kde_all = stats.gaussian_kde(qscores, bw_method=0.1)
    y_all = kde_all(x)
    ax1.fill_between(x, y_all, alpha=0.2, color=COLORS['all_reads'],
                    label=f'All reads (n={len(qscores):,})')
    ax1.plot(x, y_all, color=COLORS['all_reads'], linewidth=2.5, linestyle='--')

    for end_reason in sorted(end_reasons):
        mask = df[end_reason_col] == end_reason
        er_qscores = df.loc[mask, qscore_col].values
        if len(er_qscores) > 100:
            kde_er = stats.gaussian_kde(er_qscores, bw_method=0.1)
            y_er = kde_er(x)
            scale = len(er_qscores) / len(qscores)
            y_scaled = y_er * scale
            color = END_REASON_COLORS.get(end_reason, COLORS['primary'])
            ax1.fill_between(x, y_scaled, alpha=0.3, color=color,
                           label=f'{end_reason} (n={len(er_qscores):,}, {scale*100:.1f}%)')
            ax1.plot(x, y_scaled, color=color, linewidth=1.5)

    for q, ls in [(10, ':'), (15, '--'), (20, '-.')]:
        ax1.axvline(q, color='gray', linestyle=ls, alpha=0.5, linewidth=1)

    ax1.set_xlabel('Quality Score (Q)', fontsize=12)
    ax1.set_ylabel('Density (scaled by proportion)', fontsize=12)
    ax1.set_title('Quality Score Distribution by End Reason', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper right', fontsize=9)
    ax1.set_xlim(0, 40)

    # Panel 2: Statistics
    ax2 = fig.add_subplot(gs[0, 2])
    ax2.axis('off')
    stats_text = "End Reason Quality Stats\n" + "="*40 + "\n\n"
    for end_reason in sorted(end_reasons):
        mask = df[end_reason_col] == end_reason
        er_qscores = df.loc[mask, qscore_col].values
        if len(er_qscores) > 0:
            q10_pct = np.sum(er_qscores >= 10) / len(er_qscores) * 100
            q15_pct = np.sum(er_qscores >= 15) / len(er_qscores) * 100
            q20_pct = np.sum(er_qscores >= 20) / len(er_qscores) * 100
            stats_text += f"{end_reason}:\n"
            stats_text += f"  Mean Q: {np.mean(er_qscores):.1f}\n"
            stats_text += f"  ≥Q10: {q10_pct:.1f}%\n"
            stats_text += f"  ≥Q15: {q15_pct:.1f}%\n"
            stats_text += f"  ≥Q20: {q20_pct:.1f}%\n\n"
    ax2.text(0.05, 0.95, stats_text, transform=ax2.transAxes, fontsize=9,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # Panel 3: Normalized comparison
    ax3 = fig.add_subplot(gs[1, 0])
    for end_reason in sorted(end_reasons):
        mask = df[end_reason_col] == end_reason
        er_qscores = df.loc[mask, qscore_col].values
        if len(er_qscores) > 100:
            kde_er = stats.gaussian_kde(er_qscores, bw_method=0.1)
            y_er = kde_er(x)
            color = END_REASON_COLORS.get(end_reason, COLORS['primary'])
            ax3.fill_between(x, y_er, alpha=0.25, color=color)
            ax3.plot(x, y_er, color=color, linewidth=1.5, label=end_reason)
    ax3.set_xlabel('Quality Score (Q)', fontsize=11)
    ax3.set_ylabel('Density (normalized)', fontsize=11)
    ax3.set_title('Normalized Distributions', fontsize=12, fontweight='bold')
    ax3.legend(fontsize=8)
    ax3.set_xlim(0, 40)

    # Panel 4: Box plots
    ax4 = fig.add_subplot(gs[1, 1])
    er_data = []
    er_labels = []
    er_colors = []
    for end_reason in sorted(end_reasons):
        mask = df[end_reason_col] == end_reason
        er_qscores = df.loc[mask, qscore_col].values
        if len(er_qscores) > 10:
            er_data.append(er_qscores)
            er_labels.append(end_reason.replace('_', '\n'))
            er_colors.append(END_REASON_COLORS.get(end_reason, COLORS['primary']))
    bp = ax4.boxplot(er_data, tick_labels=er_labels, patch_artist=True, showfliers=False)
    for patch, color in zip(bp['boxes'], er_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    for q in [10, 15, 20]:
        ax4.axhline(q, color='gray', linestyle='--', alpha=0.5)
    ax4.set_ylabel('Quality Score (Q)', fontsize=11)
    ax4.set_title('Quality by End Reason', fontsize=12, fontweight='bold')
    ax4.tick_params(axis='x', labelsize=8)

    # Panel 5: Threshold pass rates
    ax5 = fig.add_subplot(gs[1, 2])
    width = 0.25
    q10_rates = []
    q15_rates = []
    q20_rates = []
    labels = []
    for end_reason in sorted(end_reasons):
        mask = df[end_reason_col] == end_reason
        er_qscores = df.loc[mask, qscore_col].values
        if len(er_qscores) > 10:
            q10_rates.append(np.sum(er_qscores >= 10) / len(er_qscores) * 100)
            q15_rates.append(np.sum(er_qscores >= 15) / len(er_qscores) * 100)
            q20_rates.append(np.sum(er_qscores >= 20) / len(er_qscores) * 100)
            labels.append(end_reason.replace('_', '\n'))
    x_pos = np.arange(len(labels))
    ax5.bar(x_pos - width, q10_rates, width, label='≥Q10', color='#e74c3c', alpha=0.7)
    ax5.bar(x_pos, q15_rates, width, label='≥Q15', color='#f39c12', alpha=0.7)
    ax5.bar(x_pos + width, q20_rates, width, label='≥Q20', color='#27ae60', alpha=0.7)
    ax5.set_xticks(x_pos)
    ax5.set_xticklabels(labels, fontsize=8)
    ax5.set_ylabel('Pass Rate (%)', fontsize=11)
    ax5.set_title('Quality Threshold Pass Rates', fontsize=12, fontweight='bold')
    ax5.legend(fontsize=9)
    ax5.set_ylim(0, 105)

    # Panel 6: CDF
    ax6 = fig.add_subplot(gs[2, 0])
    for end_reason in sorted(end_reasons):
        mask = df[end_reason_col] == end_reason
        er_qscores = df.loc[mask, qscore_col].values
        if len(er_qscores) > 100:
            sorted_q = np.sort(er_qscores)
            cdf = np.arange(1, len(sorted_q) + 1) / len(sorted_q) * 100
            color = END_REASON_COLORS.get(end_reason, COLORS['primary'])
            ax6.plot(sorted_q, cdf, color=color, linewidth=2, label=end_reason)
    ax6.set_xlabel('Quality Score (Q)', fontsize=11)
    ax6.set_ylabel('Cumulative %', fontsize=11)
    ax6.set_title('Cumulative Distribution', fontsize=12, fontweight='bold')
    ax6.legend(fontsize=8)
    ax6.set_xlim(0, 40)
    ax6.set_ylim(0, 100)
    ax6.grid(True, alpha=0.3)

    # Panel 7: Mean quality bar chart
    ax7 = fig.add_subplot(gs[2, 1])
    mean_q = []
    colors_bar = []
    labels = []
    for end_reason in sorted(end_reasons):
        mask = df[end_reason_col] == end_reason
        er_qscores = df.loc[mask, qscore_col].values
        if len(er_qscores) > 10:
            mean_q.append(np.mean(er_qscores))
            colors_bar.append(END_REASON_COLORS.get(end_reason, COLORS['primary']))
            labels.append(end_reason.replace('_', '\n'))
    bars = ax7.bar(range(len(mean_q)), mean_q, color=colors_bar, alpha=0.7)
    ax7.set_xticks(range(len(mean_q)))
    ax7.set_xticklabels(labels, fontsize=8)
    ax7.set_ylabel('Mean Quality Score', fontsize=11)
    ax7.set_title('Mean Q-Score by End Reason', fontsize=12, fontweight='bold')
    for bar, val in zip(bars, mean_q):
        ax7.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                f'Q{val:.1f}', ha='center', fontsize=9)

    # Panel 8: Accuracy distribution
    ax8 = fig.add_subplot(gs[2, 2])
    for end_reason in sorted(end_reasons):
        mask = df[end_reason_col] == end_reason
        er_qscores = df.loc[mask, qscore_col].values
        if len(er_qscores) > 100:
            accuracies = q_to_accuracy(er_qscores)
            kde_er = stats.gaussian_kde(accuracies, bw_method=0.1)
            x_acc = np.linspace(80, 100, 300)
            y_er = kde_er(x_acc)
            color = END_REASON_COLORS.get(end_reason, COLORS['primary'])
            ax8.fill_between(x_acc, y_er, alpha=0.25, color=color)
            ax8.plot(x_acc, y_er, color=color, linewidth=1.5, label=end_reason)
    ax8.set_xlabel('Accuracy (%)', fontsize=11)
    ax8.set_ylabel('Density', fontsize=11)
    ax8.set_title('Accuracy Distribution', fontsize=12, fontweight='bold')
    ax8.legend(fontsize=8)
    ax8.set_xlim(85, 100)

    fig.suptitle('Quality Score Analysis by End Reason', fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()
    return output_path


def plot_publication_summary(df, output_path, length_col, qscore_col, end_reason_col,
                             time_col=None, title="Sequencing Analysis", dpi=600):
    """Generate publication-quality summary figure."""
    if not HAS_MATPLOTLIB:
        return None

    lengths = df[length_col].values
    qscores = df[qscore_col].values
    end_reasons = df[end_reason_col].unique()

    n50 = calculate_n50(lengths)
    mean_len = np.mean(lengths)
    mean_q = np.mean(qscores)
    median_q = np.median(qscores)
    total_bases = np.sum(lengths)
    q10_pct = np.sum(qscores >= 10) / len(qscores) * 100
    q15_pct = np.sum(qscores >= 15) / len(qscores) * 100
    q20_pct = np.sum(qscores >= 20) / len(qscores) * 100

    fig = plt.figure(figsize=(16, 12))
    gs = GridSpec(3, 4, figure=fig, hspace=0.35, wspace=0.35, height_ratios=[1.2, 1, 0.8])

    # Panel A: Read Length KDE
    ax_a = fig.add_subplot(gs[0, 0:2])
    x_len = np.linspace(0, np.percentile(lengths, 99), 500)
    kde_all = stats.gaussian_kde(lengths, bw_method=0.05)
    ax_a.fill_between(x_len, kde_all(x_len), alpha=0.15, color=COLORS['all_reads'])
    ax_a.plot(x_len, kde_all(x_len), color=COLORS['all_reads'], linewidth=2,
             linestyle='--', label=f'All (n={len(lengths):,})')

    for er in sorted(end_reasons):
        mask = df[end_reason_col] == er
        er_lengths = df.loc[mask, length_col].values
        if len(er_lengths) > 100:
            kde = stats.gaussian_kde(er_lengths, bw_method=0.05)
            color = END_REASON_COLORS.get(er, COLORS['primary'])
            ax_a.fill_between(x_len, kde(x_len), alpha=0.25, color=color)
            ax_a.plot(x_len, kde(x_len), color=color, linewidth=1.5,
                     label=f'{er} ({len(er_lengths)/len(lengths)*100:.1f}%)')

    ax_a.axvline(n50, color='#c0392b', linestyle='--', linewidth=2, alpha=0.8)
    ax_a.annotate(f'N50\n{format_bp(n50)}', xy=(n50, ax_a.get_ylim()[1]*0.9),
                 fontsize=9, ha='center', color='#c0392b', fontweight='bold')
    ax_a.set_xlabel('Read Length (bp)', fontsize=11)
    ax_a.set_ylabel('Density', fontsize=11)
    ax_a.set_title('A. Read Length Distribution', fontsize=12, fontweight='bold', loc='left')
    ax_a.legend(fontsize=8, loc='upper right')
    ax_a.set_xlim(0, np.percentile(lengths, 99))
    ax_a.spines['top'].set_visible(False)
    ax_a.spines['right'].set_visible(False)

    # Panel B: Quality Score KDE
    ax_b = fig.add_subplot(gs[0, 2:4])
    x_q = np.linspace(0, 35, 300)
    kde_all_q = stats.gaussian_kde(qscores, bw_method=0.1)
    ax_b.fill_between(x_q, kde_all_q(x_q), alpha=0.15, color=COLORS['all_reads'])
    ax_b.plot(x_q, kde_all_q(x_q), color=COLORS['all_reads'], linewidth=2,
             linestyle='--', label=f'All (n={len(qscores):,})')

    for er in sorted(end_reasons):
        mask = df[end_reason_col] == er
        er_qscores = df.loc[mask, qscore_col].values
        if len(er_qscores) > 100:
            kde = stats.gaussian_kde(er_qscores, bw_method=0.1)
            color = END_REASON_COLORS.get(er, COLORS['primary'])
            ax_b.fill_between(x_q, kde(x_q), alpha=0.25, color=color)
            ax_b.plot(x_q, kde(x_q), color=color, linewidth=1.5, label=er)

    for q, label in [(10, 'Q10'), (15, 'Q15'), (20, 'Q20')]:
        ax_b.axvline(q, color='gray', linestyle=':', alpha=0.5)
    ax_b.axvline(mean_q, color='#c0392b', linestyle='--', linewidth=2, alpha=0.8)
    ax_b.set_xlabel('Quality Score (Q)', fontsize=11)
    ax_b.set_ylabel('Density', fontsize=11)
    ax_b.set_title('B. Quality Score Distribution', fontsize=12, fontweight='bold', loc='left')
    ax_b.legend(fontsize=8, loc='upper right')
    ax_b.set_xlim(0, 35)
    ax_b.spines['top'].set_visible(False)
    ax_b.spines['right'].set_visible(False)

    # Panel C: End reason pie
    ax_c = fig.add_subplot(gs[1, 0])
    counts = df[end_reason_col].value_counts()
    colors_pie = [END_REASON_COLORS.get(er, COLORS['primary']) for er in counts.index]
    ax_c.pie(counts.values, labels=None, colors=colors_pie,
            autopct=lambda p: f'{p:.0f}%' if p > 3 else '', explode=[0.02]*len(counts))
    ax_c.legend(counts.index, fontsize=8, loc='center left', bbox_to_anchor=(1, 0.5))
    ax_c.set_title('C. End Reason', fontsize=12, fontweight='bold', loc='left')

    # Panel D: N50 by end reason
    ax_d = fig.add_subplot(gs[1, 1])
    n50_data = []
    labels = []
    colors_bar = []
    for er in sorted(end_reasons):
        mask = df[end_reason_col] == er
        er_lengths = df.loc[mask, length_col].values
        if len(er_lengths) > 100:
            n50_data.append(calculate_n50(er_lengths))
            labels.append(er.replace('_', '\n'))
            colors_bar.append(END_REASON_COLORS.get(er, COLORS['primary']))
    bars = ax_d.bar(range(len(n50_data)), n50_data, color=colors_bar, alpha=0.8)
    ax_d.set_xticks(range(len(labels)))
    ax_d.set_xticklabels(labels, fontsize=8)
    ax_d.set_ylabel('N50 (bp)', fontsize=10)
    ax_d.set_title('D. N50 by End Reason', fontsize=12, fontweight='bold', loc='left')
    ax_d.spines['top'].set_visible(False)
    ax_d.spines['right'].set_visible(False)

    # Panel E: Mean quality by end reason
    ax_e = fig.add_subplot(gs[1, 2])
    mean_q_data = []
    labels = []
    colors_bar = []
    for er in sorted(end_reasons):
        mask = df[end_reason_col] == er
        er_qscores = df.loc[mask, qscore_col].values
        if len(er_qscores) > 100:
            mean_q_data.append(np.mean(er_qscores))
            labels.append(er.replace('_', '\n'))
            colors_bar.append(END_REASON_COLORS.get(er, COLORS['primary']))
    bars = ax_e.bar(range(len(mean_q_data)), mean_q_data, color=colors_bar, alpha=0.8)
    ax_e.set_xticks(range(len(labels)))
    ax_e.set_xticklabels(labels, fontsize=8)
    ax_e.set_ylabel('Mean Q-Score', fontsize=10)
    ax_e.set_title('E. Quality by End Reason', fontsize=12, fontweight='bold', loc='left')
    ax_e.spines['top'].set_visible(False)
    ax_e.spines['right'].set_visible(False)

    # Panel F: Yield over time
    ax_f = fig.add_subplot(gs[1, 3])
    if time_col and time_col in df.columns:
        times = df[time_col].values / 3600
        sort_idx = np.argsort(times)
        times_sorted = times[sort_idx]
        lengths_sorted = lengths[sort_idx]
        cumsum = np.cumsum(lengths_sorted) / 1e9
        ax_f.fill_between(times_sorted, cumsum, alpha=0.3, color=COLORS['primary'])
        ax_f.plot(times_sorted, cumsum, color=COLORS['primary'], linewidth=2)
        ax_f.set_xlabel('Time (hours)', fontsize=10)
        ax_f.set_ylabel('Cumulative Yield (Gb)', fontsize=10)
        ax_f.set_title('F. Yield Over Time', fontsize=12, fontweight='bold', loc='left')
        ax_f.spines['top'].set_visible(False)
        ax_f.spines['right'].set_visible(False)

    # Panel G: Summary table
    ax_g = fig.add_subplot(gs[2, :])
    ax_g.axis('off')
    sp_count = np.sum(df[end_reason_col] == 'signal_positive')
    sp_pct = sp_count / len(df) * 100
    summary_data = [
        ['Metric', 'Value', 'Metric', 'Value', 'Metric', 'Value'],
        ['Total Reads', f'{len(df):,}', 'Mean Length', f'{mean_len:,.0f} bp', 'signal_positive', f'{sp_pct:.1f}%'],
        ['Total Bases', f'{format_bp(total_bases)}b', 'Median Length', f'{np.median(lengths):,.0f} bp', '≥Q10', f'{q10_pct:.1f}%'],
        ['N50', f'{n50:,} bp', 'Mean Q-Score', f'{mean_q:.2f}', '≥Q15', f'{q15_pct:.1f}%'],
        ['Max Length', f'{format_bp(lengths.max())}', 'Median Q-Score', f'{median_q:.2f}', '≥Q20', f'{q20_pct:.1f}%'],
    ]
    table = ax_g.table(cellText=summary_data[1:], colLabels=summary_data[0],
                      loc='center', cellLoc='center', colColours=['#f0f0f0']*6)
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.0, 1.8)
    for i in range(6):
        table[(0, i)].set_facecolor('#2E86AB')
        table[(0, i)].set_text_props(color='white', fontweight='bold')
    ax_g.set_title('G. Summary Statistics', fontsize=12, fontweight='bold', loc='left', y=0.95)

    fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()
    return output_path
