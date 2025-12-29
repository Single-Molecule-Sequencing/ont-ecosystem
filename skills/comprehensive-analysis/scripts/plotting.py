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
except (ImportError, AttributeError):  # AttributeError for numpy compatibility
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


def mean_qscore(qscores):
    """
    Calculate mean Q-score correctly via probability space.

    Q-scores are logarithmic (Phred scale), so we must:
    1. Convert each Q to error probability: P = 10^(-Q/10)
    2. Average the probabilities
    3. Convert back to Q-score: Q = -10 * log10(P_avg)
    """
    if len(qscores) == 0:
        return 0.0
    probs = np.power(10, -np.asarray(qscores) / 10)
    mean_prob = np.mean(probs)
    if mean_prob <= 0:
        return 60.0  # Cap at Q60
    return -10 * np.log10(mean_prob)


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
    bp = ax5.boxplot(er_data, labels=er_labels, patch_artist=True, showfliers=False)
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
            stats_text += f"  Mean Q: {mean_qscore(er_qscores):.1f}\n"
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
    bp = ax4.boxplot(er_data, labels=er_labels, patch_artist=True, showfliers=False)
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
            mean_q.append(mean_qscore(er_qscores))
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
    mean_q = mean_qscore(qscores)
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
            mean_q_data.append(mean_qscore(er_qscores))
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


def plot_temporal_evolution(df, output_path, length_col, qscore_col, end_reason_col,
                            time_col, dpi=300):
    """Generate temporal evolution analysis by end reason."""
    if not HAS_MATPLOTLIB:
        return None

    times = df[time_col].values / 3600  # Convert to hours
    end_reasons = sorted(df[end_reason_col].unique())
    max_time = times.max()

    fig = plt.figure(figsize=(18, 14))
    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)

    # Panel 1: Stacked area of proportions over time
    ax1 = fig.add_subplot(gs[0, :2])
    time_bins = np.linspace(0, max_time, 50)
    proportions = {er: [] for er in end_reasons}

    for i in range(len(time_bins) - 1):
        mask = (times >= time_bins[i]) & (times < time_bins[i+1])
        total = mask.sum()
        for er in end_reasons:
            er_mask = mask & (df[end_reason_col].values == er)
            proportions[er].append(er_mask.sum() / max(total, 1) * 100)

    bin_centers = (time_bins[:-1] + time_bins[1:]) / 2
    bottom = np.zeros(len(bin_centers))

    for er in end_reasons:
        color = END_REASON_COLORS.get(er, COLORS['primary'])
        ax1.fill_between(bin_centers, bottom, bottom + proportions[er],
                        alpha=0.7, color=color, label=er)
        bottom = bottom + np.array(proportions[er])

    ax1.set_xlabel('Time (hours)', fontsize=11)
    ax1.set_ylabel('Proportion (%)', fontsize=11)
    ax1.set_title('End Reason Proportions Over Time', fontsize=12, fontweight='bold')
    ax1.legend(loc='upper right', fontsize=9)
    ax1.set_xlim(0, max_time)
    ax1.set_ylim(0, 100)

    # Panel 2: Read rate over time by end reason
    ax2 = fig.add_subplot(gs[0, 2])
    for er in end_reasons:
        er_times = times[df[end_reason_col].values == er]
        if len(er_times) > 10:
            hist, edges = np.histogram(er_times, bins=30)
            bin_width = edges[1] - edges[0]
            rates = hist / bin_width / 60  # reads per minute
            centers = (edges[:-1] + edges[1:]) / 2
            color = END_REASON_COLORS.get(er, COLORS['primary'])
            ax2.plot(centers, rates, color=color, linewidth=1.5, label=er)

    ax2.set_xlabel('Time (hours)', fontsize=11)
    ax2.set_ylabel('Reads/minute', fontsize=11)
    ax2.set_title('Read Rate by End Reason', fontsize=12, fontweight='bold')
    ax2.legend(fontsize=8)

    # Panel 3: Cumulative reads over time
    ax3 = fig.add_subplot(gs[1, 0])
    sort_idx = np.argsort(times)
    for er in end_reasons:
        er_mask = df[end_reason_col].values == er
        er_times = times[er_mask]
        if len(er_times) > 10:
            er_sort = np.argsort(er_times)
            cumsum = np.arange(1, len(er_times) + 1)
            color = END_REASON_COLORS.get(er, COLORS['primary'])
            ax3.plot(er_times[er_sort], cumsum, color=color, linewidth=2, label=er)

    ax3.set_xlabel('Time (hours)', fontsize=11)
    ax3.set_ylabel('Cumulative Reads', fontsize=11)
    ax3.set_title('Cumulative Reads by End Reason', fontsize=12, fontweight='bold')
    ax3.legend(fontsize=8)

    # Panel 4: Cumulative yield over time by end reason
    ax4 = fig.add_subplot(gs[1, 1])
    lengths = df[length_col].values
    for er in end_reasons:
        er_mask = df[end_reason_col].values == er
        er_times = times[er_mask]
        er_lengths = lengths[er_mask]
        if len(er_times) > 10:
            sort_idx = np.argsort(er_times)
            cumsum = np.cumsum(er_lengths[sort_idx]) / 1e9
            color = END_REASON_COLORS.get(er, COLORS['primary'])
            ax4.plot(er_times[sort_idx], cumsum, color=color, linewidth=2, label=er)

    ax4.set_xlabel('Time (hours)', fontsize=11)
    ax4.set_ylabel('Cumulative Yield (Gb)', fontsize=11)
    ax4.set_title('Cumulative Yield by End Reason', fontsize=12, fontweight='bold')
    ax4.legend(fontsize=8)

    # Panel 5: Rolling mean quality over time
    ax5 = fig.add_subplot(gs[1, 2])
    qscores = df[qscore_col].values
    window_size = max(100, len(df) // 100)

    for er in end_reasons:
        er_mask = df[end_reason_col].values == er
        er_times = times[er_mask]
        er_qscores = qscores[er_mask]
        if len(er_times) > window_size:
            sort_idx = np.argsort(er_times)
            er_times_sorted = er_times[sort_idx]
            er_qscores_sorted = er_qscores[sort_idx]
            # Rolling mean
            rolling_q = np.convolve(er_qscores_sorted,
                                   np.ones(window_size)/window_size, mode='valid')
            rolling_t = er_times_sorted[window_size//2:window_size//2+len(rolling_q)]
            color = END_REASON_COLORS.get(er, COLORS['primary'])
            ax5.plot(rolling_t, rolling_q, color=color, linewidth=1.5, label=er)

    ax5.set_xlabel('Time (hours)', fontsize=11)
    ax5.set_ylabel('Mean Q-Score (rolling)', fontsize=11)
    ax5.set_title('Quality Over Time', fontsize=12, fontweight='bold')
    ax5.legend(fontsize=8)

    # Panel 6: Rolling mean length over time
    ax6 = fig.add_subplot(gs[2, 0])
    for er in end_reasons:
        er_mask = df[end_reason_col].values == er
        er_times = times[er_mask]
        er_lengths = lengths[er_mask]
        if len(er_times) > window_size:
            sort_idx = np.argsort(er_times)
            er_times_sorted = er_times[sort_idx]
            er_lengths_sorted = er_lengths[sort_idx]
            rolling_len = np.convolve(er_lengths_sorted,
                                     np.ones(window_size)/window_size, mode='valid')
            rolling_t = er_times_sorted[window_size//2:window_size//2+len(rolling_len)]
            color = END_REASON_COLORS.get(er, COLORS['primary'])
            ax6.plot(rolling_t, rolling_len, color=color, linewidth=1.5, label=er)

    ax6.set_xlabel('Time (hours)', fontsize=11)
    ax6.set_ylabel('Mean Length (rolling)', fontsize=11)
    ax6.set_title('Read Length Over Time', fontsize=12, fontweight='bold')
    ax6.legend(fontsize=8)

    # Panel 7: Hourly read counts
    ax7 = fig.add_subplot(gs[2, 1])
    hours = np.floor(times).astype(int)
    max_hour = int(max_time) + 1
    width = 0.8 / len(end_reasons)

    for i, er in enumerate(end_reasons):
        er_hours = hours[df[end_reason_col].values == er]
        counts = [np.sum(er_hours == h) for h in range(max_hour)]
        x_pos = np.arange(max_hour) + i * width - 0.4 + width/2
        color = END_REASON_COLORS.get(er, COLORS['primary'])
        ax7.bar(x_pos, counts, width=width, color=color, alpha=0.7, label=er)

    ax7.set_xlabel('Hour', fontsize=11)
    ax7.set_ylabel('Read Count', fontsize=11)
    ax7.set_title('Hourly Read Counts', fontsize=12, fontweight='bold')
    ax7.legend(fontsize=8)

    # Panel 8: Signal positive percentage over time
    ax8 = fig.add_subplot(gs[2, 2])
    sp_pct = []
    for i in range(len(time_bins) - 1):
        mask = (times >= time_bins[i]) & (times < time_bins[i+1])
        total = mask.sum()
        sp_mask = mask & (df[end_reason_col].values == 'signal_positive')
        sp_pct.append(sp_mask.sum() / max(total, 1) * 100)

    ax8.fill_between(bin_centers, sp_pct, alpha=0.3, color=END_REASON_COLORS['signal_positive'])
    ax8.plot(bin_centers, sp_pct, color=END_REASON_COLORS['signal_positive'], linewidth=2)
    ax8.axhline(np.mean(sp_pct), color='red', linestyle='--', alpha=0.7,
               label=f'Mean: {np.mean(sp_pct):.1f}%')
    ax8.set_xlabel('Time (hours)', fontsize=11)
    ax8.set_ylabel('signal_positive %', fontsize=11)
    ax8.set_title('Signal Positive Rate Over Time', fontsize=12, fontweight='bold')
    ax8.legend(fontsize=9)
    ax8.set_ylim(0, 100)

    fig.suptitle('Temporal Evolution by End Reason', fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()
    return output_path


def plot_channel_analysis(df, output_path, length_col, qscore_col, end_reason_col,
                          channel_col, dpi=300):
    """Generate channel-based analysis by end reason."""
    if not HAS_MATPLOTLIB:
        return None

    channels = df[channel_col].values
    end_reasons = sorted(df[end_reason_col].unique())
    n_channels = int(channels.max())

    fig = plt.figure(figsize=(18, 14))
    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)

    # Panel 1: End reason proportions by channel group
    ax1 = fig.add_subplot(gs[0, 0])
    channel_groups = [(1, 128), (129, 256), (257, 384), (385, 512)]
    group_labels = ['Ch 1-128', 'Ch 129-256', 'Ch 257-384', 'Ch 385-512']

    proportions = {er: [] for er in end_reasons}
    for start, end in channel_groups:
        mask = (channels >= start) & (channels <= end)
        total = mask.sum()
        for er in end_reasons:
            er_mask = mask & (df[end_reason_col].values == er)
            proportions[er].append(er_mask.sum() / max(total, 1) * 100)

    x_pos = np.arange(len(group_labels))
    width = 0.8 / len(end_reasons)

    for i, er in enumerate(end_reasons):
        color = END_REASON_COLORS.get(er, COLORS['primary'])
        ax1.bar(x_pos + i * width - 0.4 + width/2, proportions[er],
               width=width, color=color, alpha=0.7, label=er)

    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(group_labels, fontsize=9)
    ax1.set_ylabel('Proportion (%)', fontsize=11)
    ax1.set_title('End Reason by Channel Group', fontsize=12, fontweight='bold')
    ax1.legend(fontsize=8)

    # Panel 2: Signal positive rate heatmap by channel
    ax2 = fig.add_subplot(gs[0, 1:])
    # Create 2D grid for MinION layout (assuming 512 channels in 4x128 grid)
    grid_size = (4, 128)
    sp_grid = np.zeros(grid_size)

    for ch in range(1, min(n_channels + 1, 513)):
        ch_mask = channels == ch
        total = ch_mask.sum()
        sp_mask = ch_mask & (df[end_reason_col].values == 'signal_positive')
        sp_rate = sp_mask.sum() / max(total, 1) * 100

        row = (ch - 1) // 128
        col = (ch - 1) % 128
        if row < 4:
            sp_grid[row, col] = sp_rate

    im = ax2.imshow(sp_grid, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)
    plt.colorbar(im, ax=ax2, label='signal_positive %')
    ax2.set_xlabel('Channel (within row)', fontsize=11)
    ax2.set_ylabel('Row', fontsize=11)
    ax2.set_title('Signal Positive Rate by Channel', fontsize=12, fontweight='bold')

    # Panel 3: Channel distribution by end reason (violin)
    ax3 = fig.add_subplot(gs[1, 0])
    for i, er in enumerate(end_reasons):
        er_channels = channels[df[end_reason_col].values == er]
        if len(er_channels) > 100:
            if len(er_channels) > 5000:
                er_channels = np.random.choice(er_channels, 5000, replace=False)
            color = END_REASON_COLORS.get(er, COLORS['primary'])
            parts = ax3.violinplot([er_channels], positions=[i], showmeans=True)
            for pc in parts['bodies']:
                pc.set_facecolor(color)
                pc.set_alpha(0.6)

    ax3.set_xticks(range(len(end_reasons)))
    ax3.set_xticklabels([er.replace('_', '\n') for er in end_reasons], fontsize=8)
    ax3.set_ylabel('Channel', fontsize=11)
    ax3.set_title('Channel Distribution by End Reason', fontsize=12, fontweight='bold')

    # Panel 4: Mean quality by channel group
    ax4 = fig.add_subplot(gs[1, 1])
    qscores = df[qscore_col].values
    mean_q = {er: [] for er in end_reasons}

    for start, end in channel_groups:
        mask = (channels >= start) & (channels <= end)
        for er in end_reasons:
            er_mask = mask & (df[end_reason_col].values == er)
            er_qscores = qscores[er_mask]
            mean_q[er].append(mean_qscore(er_qscores) if len(er_qscores) > 0 else 0)

    for i, er in enumerate(end_reasons):
        color = END_REASON_COLORS.get(er, COLORS['primary'])
        ax4.bar(x_pos + i * width - 0.4 + width/2, mean_q[er],
               width=width, color=color, alpha=0.7, label=er)

    ax4.set_xticks(x_pos)
    ax4.set_xticklabels(group_labels, fontsize=9)
    ax4.set_ylabel('Mean Q-Score', fontsize=11)
    ax4.set_title('Quality by Channel Group', fontsize=12, fontweight='bold')
    ax4.legend(fontsize=8)

    # Panel 5: Mean length by channel group
    ax5 = fig.add_subplot(gs[1, 2])
    lengths = df[length_col].values
    mean_len = {er: [] for er in end_reasons}

    for start, end in channel_groups:
        mask = (channels >= start) & (channels <= end)
        for er in end_reasons:
            er_mask = mask & (df[end_reason_col].values == er)
            er_lengths = lengths[er_mask]
            mean_len[er].append(np.mean(er_lengths) if len(er_lengths) > 0 else 0)

    for i, er in enumerate(end_reasons):
        color = END_REASON_COLORS.get(er, COLORS['primary'])
        ax5.bar(x_pos + i * width - 0.4 + width/2, mean_len[er],
               width=width, color=color, alpha=0.7, label=er)

    ax5.set_xticks(x_pos)
    ax5.set_xticklabels(group_labels, fontsize=9)
    ax5.set_ylabel('Mean Length (bp)', fontsize=11)
    ax5.set_title('Read Length by Channel Group', fontsize=12, fontweight='bold')
    ax5.legend(fontsize=8)

    # Panel 6: Active channels over time (if time available)
    ax6 = fig.add_subplot(gs[2, 0])
    if 'start_time' in df.columns:
        times = df['start_time'].values / 3600
        time_bins = np.linspace(0, times.max(), 30)
        active_channels = []

        for i in range(len(time_bins) - 1):
            mask = (times >= time_bins[i]) & (times < time_bins[i+1])
            active = len(np.unique(channels[mask]))
            active_channels.append(active)

        bin_centers = (time_bins[:-1] + time_bins[1:]) / 2
        ax6.fill_between(bin_centers, active_channels, alpha=0.3, color=COLORS['primary'])
        ax6.plot(bin_centers, active_channels, color=COLORS['primary'], linewidth=2)
        ax6.set_xlabel('Time (hours)', fontsize=11)
        ax6.set_ylabel('Active Channels', fontsize=11)
        ax6.set_title('Active Channels Over Time', fontsize=12, fontweight='bold')

    # Panel 7: Reads per channel distribution
    ax7 = fig.add_subplot(gs[2, 1])
    reads_per_channel = []
    for ch in range(1, min(n_channels + 1, 513)):
        reads_per_channel.append(np.sum(channels == ch))

    ax7.hist(reads_per_channel, bins=50, color=COLORS['primary'], alpha=0.7, edgecolor='white')
    ax7.axvline(np.mean(reads_per_channel), color='red', linestyle='--',
               label=f'Mean: {np.mean(reads_per_channel):.0f}')
    ax7.axvline(np.median(reads_per_channel), color='orange', linestyle=':',
               label=f'Median: {np.median(reads_per_channel):.0f}')
    ax7.set_xlabel('Reads per Channel', fontsize=11)
    ax7.set_ylabel('Count', fontsize=11)
    ax7.set_title('Reads per Channel Distribution', fontsize=12, fontweight='bold')
    ax7.legend(fontsize=9)

    # Panel 8: Channel performance summary
    ax8 = fig.add_subplot(gs[2, 2])
    ax8.axis('off')

    total_channels = len(np.unique(channels))
    mean_reads = np.mean(reads_per_channel)
    std_reads = np.std(reads_per_channel)
    low_perf = np.sum(np.array(reads_per_channel) < mean_reads / 2)
    high_perf = np.sum(np.array(reads_per_channel) > mean_reads * 1.5)

    summary_text = f"""Channel Performance Summary
{'='*40}

Active Channels: {total_channels}
Mean Reads/Channel: {mean_reads:.0f}
Std Reads/Channel: {std_reads:.0f}

Low Performers (<50% mean): {low_perf} ({low_perf/total_channels*100:.1f}%)
High Performers (>150% mean): {high_perf} ({high_perf/total_channels*100:.1f}%)

Channel Efficiency: {total_channels/512*100:.1f}%
"""
    ax8.text(0.05, 0.95, summary_text, transform=ax8.transAxes, fontsize=10,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    fig.suptitle('Channel Analysis by End Reason', fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()
    return output_path


def plot_quality_length_correlation(df, output_path, length_col, qscore_col,
                                    end_reason_col, dpi=300):
    """Generate quality-length correlation analysis."""
    if not HAS_MATPLOTLIB:
        return None

    lengths = df[length_col].values
    qscores = df[qscore_col].values
    end_reasons = sorted(df[end_reason_col].unique())

    fig = plt.figure(figsize=(18, 14))
    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)

    # Panel 1: Scatter plot with regression by end reason
    ax1 = fig.add_subplot(gs[0, :2])

    for er in end_reasons:
        mask = df[end_reason_col].values == er
        er_lengths = lengths[mask]
        er_qscores = qscores[mask]

        if len(er_lengths) > 100:
            # Subsample for plotting
            if len(er_lengths) > 2000:
                idx = np.random.choice(len(er_lengths), 2000, replace=False)
                plot_len = er_lengths[idx]
                plot_q = er_qscores[idx]
            else:
                plot_len = er_lengths
                plot_q = er_qscores

            color = END_REASON_COLORS.get(er, COLORS['primary'])
            ax1.scatter(plot_len, plot_q, alpha=0.3, s=10, c=color, label=er)

            # Add regression line
            z = np.polyfit(er_lengths, er_qscores, 1)
            p = np.poly1d(z)
            x_line = np.linspace(0, np.percentile(er_lengths, 99), 100)
            ax1.plot(x_line, p(x_line), color=color, linewidth=2, linestyle='--')

    ax1.set_xlabel('Read Length (bp)', fontsize=11)
    ax1.set_ylabel('Quality Score', fontsize=11)
    ax1.set_title('Quality vs Length by End Reason', fontsize=12, fontweight='bold')
    ax1.legend(fontsize=9)
    ax1.set_xlim(0, np.percentile(lengths, 99))

    # Panel 2: Correlation coefficients
    ax2 = fig.add_subplot(gs[0, 2])
    correlations = []
    labels = []
    colors_bar = []

    for er in end_reasons:
        mask = df[end_reason_col].values == er
        er_lengths = lengths[mask]
        er_qscores = qscores[mask]
        if len(er_lengths) > 100:
            corr = np.corrcoef(er_lengths, er_qscores)[0, 1]
            correlations.append(corr)
            labels.append(er.replace('_', '\n'))
            colors_bar.append(END_REASON_COLORS.get(er, COLORS['primary']))

    bars = ax2.bar(range(len(correlations)), correlations, color=colors_bar, alpha=0.7)
    ax2.set_xticks(range(len(labels)))
    ax2.set_xticklabels(labels, fontsize=8)
    ax2.set_ylabel('Correlation (r)', fontsize=11)
    ax2.set_title('Length-Quality Correlation', fontsize=12, fontweight='bold')
    ax2.axhline(0, color='gray', linestyle='-', alpha=0.5)
    for bar, val in zip(bars, correlations):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{val:.3f}', ha='center', fontsize=9)

    # Panel 3: 2D KDE contours by end reason
    ax3 = fig.add_subplot(gs[1, 0])
    for er in end_reasons:
        mask = df[end_reason_col].values == er
        er_lengths = lengths[mask]
        er_qscores = qscores[mask]

        if len(er_lengths) > 500:
            # Subsample for KDE
            if len(er_lengths) > 5000:
                idx = np.random.choice(len(er_lengths), 5000, replace=False)
                er_lengths = er_lengths[idx]
                er_qscores = er_qscores[idx]

            try:
                kde = stats.gaussian_kde([er_lengths, er_qscores])
                x_grid = np.linspace(0, np.percentile(lengths, 95), 50)
                y_grid = np.linspace(0, 35, 50)
                X, Y = np.meshgrid(x_grid, y_grid)
                Z = kde([X.ravel(), Y.ravel()]).reshape(X.shape)
                color = END_REASON_COLORS.get(er, COLORS['primary'])
                ax3.contour(X, Y, Z, levels=5, colors=[color], alpha=0.7)
            except Exception:
                pass

    ax3.set_xlabel('Read Length (bp)', fontsize=11)
    ax3.set_ylabel('Quality Score', fontsize=11)
    ax3.set_title('2D KDE Contours', fontsize=12, fontweight='bold')

    # Panel 4: Binned quality by length
    ax4 = fig.add_subplot(gs[1, 1])
    length_bins = np.percentile(lengths, np.linspace(0, 100, 11))

    for er in end_reasons:
        mask = df[end_reason_col].values == er
        er_lengths = lengths[mask]
        er_qscores = qscores[mask]

        if len(er_lengths) > 100:
            binned_q = []
            bin_centers = []
            for i in range(len(length_bins) - 1):
                bin_mask = (er_lengths >= length_bins[i]) & (er_lengths < length_bins[i+1])
                if bin_mask.sum() > 10:
                    binned_q.append(mean_qscore(er_qscores[bin_mask]))
                    bin_centers.append((length_bins[i] + length_bins[i+1]) / 2)

            color = END_REASON_COLORS.get(er, COLORS['primary'])
            ax4.plot(bin_centers, binned_q, 'o-', color=color, linewidth=2,
                    markersize=6, label=er)

    ax4.set_xlabel('Read Length (bp)', fontsize=11)
    ax4.set_ylabel('Mean Quality', fontsize=11)
    ax4.set_title('Binned Quality by Length', fontsize=12, fontweight='bold')
    ax4.legend(fontsize=8)

    # Panel 5: Length distribution by quality bins
    ax5 = fig.add_subplot(gs[1, 2])
    q_bins = [(0, 10), (10, 15), (15, 20), (20, 40)]
    q_labels = ['Q0-10', 'Q10-15', 'Q15-20', 'Q20+']

    for i, (q_min, q_max) in enumerate(q_bins):
        q_mask = (qscores >= q_min) & (qscores < q_max)
        q_lengths = lengths[q_mask]
        if len(q_lengths) > 100:
            kde = stats.gaussian_kde(q_lengths, bw_method=0.1)
            x = np.linspace(0, np.percentile(lengths, 99), 300)
            ax5.plot(x, kde(x), linewidth=2, label=f'{q_labels[i]} (n={len(q_lengths):,})')

    ax5.set_xlabel('Read Length (bp)', fontsize=11)
    ax5.set_ylabel('Density', fontsize=11)
    ax5.set_title('Length by Quality Bins', fontsize=12, fontweight='bold')
    ax5.legend(fontsize=8)

    # Panel 6: Hexbin density plot
    ax6 = fig.add_subplot(gs[2, 0])
    hb = ax6.hexbin(lengths, qscores, gridsize=40, cmap='viridis',
                   extent=[0, np.percentile(lengths, 99), 0, 35], mincnt=1)
    plt.colorbar(hb, ax=ax6, label='Count')
    ax6.set_xlabel('Read Length (bp)', fontsize=11)
    ax6.set_ylabel('Quality Score', fontsize=11)
    ax6.set_title('Density (All Reads)', fontsize=12, fontweight='bold')

    # Panel 7: Quality percentiles by length bins
    ax7 = fig.add_subplot(gs[2, 1])
    percentiles = [25, 50, 75, 90]
    colors_pct = ['#3498db', '#27ae60', '#f39c12', '#e74c3c']

    for pct, color in zip(percentiles, colors_pct):
        pct_values = []
        bin_centers = []
        for i in range(len(length_bins) - 1):
            bin_mask = (lengths >= length_bins[i]) & (lengths < length_bins[i+1])
            if bin_mask.sum() > 10:
                pct_values.append(np.percentile(qscores[bin_mask], pct))
                bin_centers.append((length_bins[i] + length_bins[i+1]) / 2)
        ax7.plot(bin_centers, pct_values, 'o-', color=color, linewidth=2,
                label=f'{pct}th percentile')

    ax7.set_xlabel('Read Length (bp)', fontsize=11)
    ax7.set_ylabel('Quality Score', fontsize=11)
    ax7.set_title('Quality Percentiles by Length', fontsize=12, fontweight='bold')
    ax7.legend(fontsize=9)

    # Panel 8: Summary statistics
    ax8 = fig.add_subplot(gs[2, 2])
    ax8.axis('off')

    overall_corr = np.corrcoef(lengths, qscores)[0, 1]
    summary_text = f"""Quality-Length Correlation Summary
{'='*40}

Overall Correlation: {overall_corr:.4f}

By End Reason:
"""
    for er in end_reasons:
        mask = df[end_reason_col].values == er
        er_lengths = lengths[mask]
        er_qscores = qscores[mask]
        if len(er_lengths) > 100:
            corr = np.corrcoef(er_lengths, er_qscores)[0, 1]
            summary_text += f"  {er}: r = {corr:.4f}\n"

    ax8.text(0.05, 0.95, summary_text, transform=ax8.transAxes, fontsize=10,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    fig.suptitle('Quality-Length Correlation Analysis', fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()
    return output_path


def plot_hourly_evolution(df, output_path, length_col, qscore_col, end_reason_col,
                          time_col, dpi=300):
    """Generate hourly evolution analysis."""
    if not HAS_MATPLOTLIB:
        return None

    times = df[time_col].values / 3600
    lengths = df[length_col].values
    qscores = df[qscore_col].values
    end_reasons = sorted(df[end_reason_col].unique())

    hours = np.floor(times).astype(int)
    max_hour = int(times.max()) + 1

    fig = plt.figure(figsize=(18, 14))
    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)

    # Panel 1: Mean quality by hour and end reason
    ax1 = fig.add_subplot(gs[0, 0])
    for er in end_reasons:
        er_mask = df[end_reason_col].values == er
        er_hours = hours[er_mask]
        er_qscores = qscores[er_mask]

        hourly_q = []
        valid_hours = []
        for h in range(max_hour):
            h_mask = er_hours == h
            if h_mask.sum() > 10:
                hourly_q.append(mean_qscore(er_qscores[h_mask]))
                valid_hours.append(h)

        if valid_hours:
            color = END_REASON_COLORS.get(er, COLORS['primary'])
            ax1.plot(valid_hours, hourly_q, 'o-', color=color, linewidth=2,
                    markersize=5, label=er)

    ax1.set_xlabel('Hour', fontsize=11)
    ax1.set_ylabel('Mean Quality', fontsize=11)
    ax1.set_title('Hourly Mean Quality', fontsize=12, fontweight='bold')
    ax1.legend(fontsize=8)

    # Panel 2: Mean length by hour and end reason
    ax2 = fig.add_subplot(gs[0, 1])
    for er in end_reasons:
        er_mask = df[end_reason_col].values == er
        er_hours = hours[er_mask]
        er_lengths = lengths[er_mask]

        hourly_len = []
        valid_hours = []
        for h in range(max_hour):
            h_mask = er_hours == h
            if h_mask.sum() > 10:
                hourly_len.append(np.mean(er_lengths[h_mask]))
                valid_hours.append(h)

        if valid_hours:
            color = END_REASON_COLORS.get(er, COLORS['primary'])
            ax2.plot(valid_hours, hourly_len, 'o-', color=color, linewidth=2,
                    markersize=5, label=er)

    ax2.set_xlabel('Hour', fontsize=11)
    ax2.set_ylabel('Mean Length (bp)', fontsize=11)
    ax2.set_title('Hourly Mean Length', fontsize=12, fontweight='bold')
    ax2.legend(fontsize=8)

    # Panel 3: Hourly yield by end reason
    ax3 = fig.add_subplot(gs[0, 2])
    for er in end_reasons:
        er_mask = df[end_reason_col].values == er
        er_hours = hours[er_mask]
        er_lengths = lengths[er_mask]

        hourly_yield = []
        for h in range(max_hour):
            h_mask = er_hours == h
            hourly_yield.append(er_lengths[h_mask].sum() / 1e9)

        color = END_REASON_COLORS.get(er, COLORS['primary'])
        ax3.bar(np.arange(max_hour) + list(end_reasons).index(er) * 0.2 - 0.3,
               hourly_yield, width=0.2, color=color, alpha=0.7, label=er)

    ax3.set_xlabel('Hour', fontsize=11)
    ax3.set_ylabel('Yield (Gb)', fontsize=11)
    ax3.set_title('Hourly Yield', fontsize=12, fontweight='bold')
    ax3.legend(fontsize=8)

    # Panel 4: Hourly read count by end reason
    ax4 = fig.add_subplot(gs[1, 0])
    width = 0.8 / len(end_reasons)

    for i, er in enumerate(end_reasons):
        er_hours = hours[df[end_reason_col].values == er]
        counts = [np.sum(er_hours == h) for h in range(max_hour)]
        x_pos = np.arange(max_hour) + i * width - 0.4 + width/2
        color = END_REASON_COLORS.get(er, COLORS['primary'])
        ax4.bar(x_pos, counts, width=width, color=color, alpha=0.7, label=er)

    ax4.set_xlabel('Hour', fontsize=11)
    ax4.set_ylabel('Read Count', fontsize=11)
    ax4.set_title('Hourly Read Count', fontsize=12, fontweight='bold')
    ax4.legend(fontsize=8)

    # Panel 5: Hourly N50 by end reason
    ax5 = fig.add_subplot(gs[1, 1])
    for er in end_reasons:
        er_mask = df[end_reason_col].values == er
        er_hours = hours[er_mask]
        er_lengths = lengths[er_mask]

        hourly_n50 = []
        valid_hours = []
        for h in range(max_hour):
            h_mask = er_hours == h
            h_lengths = er_lengths[h_mask]
            if len(h_lengths) > 50:
                hourly_n50.append(calculate_n50(h_lengths))
                valid_hours.append(h)

        if valid_hours:
            color = END_REASON_COLORS.get(er, COLORS['primary'])
            ax5.plot(valid_hours, hourly_n50, 'o-', color=color, linewidth=2,
                    markersize=5, label=er)

    ax5.set_xlabel('Hour', fontsize=11)
    ax5.set_ylabel('N50 (bp)', fontsize=11)
    ax5.set_title('Hourly N50', fontsize=12, fontweight='bold')
    ax5.legend(fontsize=8)

    # Panel 6: Quality threshold pass rates by hour
    ax6 = fig.add_subplot(gs[1, 2])
    q10_hourly = []
    q15_hourly = []
    q20_hourly = []

    for h in range(max_hour):
        h_mask = hours == h
        h_qscores = qscores[h_mask]
        if len(h_qscores) > 0:
            q10_hourly.append(np.sum(h_qscores >= 10) / len(h_qscores) * 100)
            q15_hourly.append(np.sum(h_qscores >= 15) / len(h_qscores) * 100)
            q20_hourly.append(np.sum(h_qscores >= 20) / len(h_qscores) * 100)
        else:
            q10_hourly.append(0)
            q15_hourly.append(0)
            q20_hourly.append(0)

    ax6.plot(range(max_hour), q10_hourly, 'o-', color='#e74c3c', label='≥Q10', linewidth=2)
    ax6.plot(range(max_hour), q15_hourly, 's-', color='#f39c12', label='≥Q15', linewidth=2)
    ax6.plot(range(max_hour), q20_hourly, '^-', color='#27ae60', label='≥Q20', linewidth=2)
    ax6.set_xlabel('Hour', fontsize=11)
    ax6.set_ylabel('Pass Rate (%)', fontsize=11)
    ax6.set_title('Hourly Quality Thresholds', fontsize=12, fontweight='bold')
    ax6.legend(fontsize=9)
    ax6.set_ylim(0, 105)

    # Panel 7: Signal positive rate by hour
    ax7 = fig.add_subplot(gs[2, 0])
    sp_hourly = []
    for h in range(max_hour):
        h_mask = hours == h
        total = h_mask.sum()
        sp_mask = h_mask & (df[end_reason_col].values == 'signal_positive')
        sp_hourly.append(sp_mask.sum() / max(total, 1) * 100)

    ax7.fill_between(range(max_hour), sp_hourly, alpha=0.3,
                    color=END_REASON_COLORS['signal_positive'])
    ax7.plot(range(max_hour), sp_hourly, 'o-',
            color=END_REASON_COLORS['signal_positive'], linewidth=2)
    ax7.axhline(np.mean(sp_hourly), color='red', linestyle='--',
               label=f'Mean: {np.mean(sp_hourly):.1f}%')
    ax7.set_xlabel('Hour', fontsize=11)
    ax7.set_ylabel('signal_positive %', fontsize=11)
    ax7.set_title('Hourly Signal Positive Rate', fontsize=12, fontweight='bold')
    ax7.legend(fontsize=9)

    # Panel 8: Cumulative metrics by hour
    ax8 = fig.add_subplot(gs[2, 1])
    cumulative_reads = np.cumsum([np.sum(hours == h) for h in range(max_hour)])
    cumulative_bases = np.cumsum([lengths[hours == h].sum() for h in range(max_hour)]) / 1e9

    ax8_twin = ax8.twinx()
    ax8.plot(range(max_hour), cumulative_reads, 'o-', color=COLORS['primary'],
            linewidth=2, label='Cumulative Reads')
    ax8_twin.plot(range(max_hour), cumulative_bases, 's-', color=COLORS['secondary'],
                 linewidth=2, label='Cumulative Bases')

    ax8.set_xlabel('Hour', fontsize=11)
    ax8.set_ylabel('Cumulative Reads', fontsize=11, color=COLORS['primary'])
    ax8_twin.set_ylabel('Cumulative Bases (Gb)', fontsize=11, color=COLORS['secondary'])
    ax8.set_title('Cumulative Progress', fontsize=12, fontweight='bold')

    # Panel 9: Hourly statistics summary
    ax9 = fig.add_subplot(gs[2, 2])
    ax9.axis('off')

    best_hour_q = np.argmax([mean_qscore(qscores[hours == h]) if np.sum(hours == h) > 0 else 0
                            for h in range(max_hour)])
    best_hour_yield = np.argmax([lengths[hours == h].sum() for h in range(max_hour)])

    summary_text = f"""Hourly Evolution Summary
{'='*40}

Duration: {max_hour} hours
Total Reads: {len(df):,}
Total Yield: {lengths.sum()/1e9:.2f} Gb

Best Quality Hour: Hour {best_hour_q}
  Mean Q: {mean_qscore(qscores[hours == best_hour_q]):.1f}

Best Yield Hour: Hour {best_hour_yield}
  Yield: {lengths[hours == best_hour_yield].sum()/1e9:.3f} Gb

Peak Read Rate: {max([np.sum(hours == h) for h in range(max_hour)]):,}/hour
"""
    ax9.text(0.05, 0.95, summary_text, transform=ax9.transAxes, fontsize=10,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    fig.suptitle('Hourly Evolution Analysis', fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()
    return output_path


def plot_overview_summary(df, output_path, length_col, qscore_col, end_reason_col,
                          time_col=None, channel_col=None, title="Experiment Overview",
                          dpi=300):
    """Generate quick overview summary figure."""
    if not HAS_MATPLOTLIB:
        return None

    lengths = df[length_col].values
    qscores = df[qscore_col].values
    end_reasons = df[end_reason_col].value_counts()

    n50 = calculate_n50(lengths)
    total_bases = np.sum(lengths)
    mean_q = mean_qscore(qscores)
    sp_pct = end_reasons.get('signal_positive', 0) / len(df) * 100

    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(2, 4, hspace=0.3, wspace=0.3)

    # Panel 1: Key metrics
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.axis('off')

    metrics_text = f"""
    EXPERIMENT METRICS
    {'─'*30}

    Total Reads:    {len(df):>12,}
    Total Bases:    {format_bp(total_bases):>12}b
    N50:            {format_bp(n50):>12}

    Mean Quality:   Q{mean_q:>11.1f}
    Mean Length:    {np.mean(lengths):>10,.0f} bp

    signal_positive: {sp_pct:>10.1f}%
    """
    ax1.text(0.1, 0.9, metrics_text, transform=ax1.transAxes, fontsize=11,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='#f0f0f0', alpha=0.8))

    # Panel 2: End reason pie
    ax2 = fig.add_subplot(gs[0, 1])
    colors_pie = [END_REASON_COLORS.get(er, COLORS['primary']) for er in end_reasons.index]
    ax2.pie(end_reasons.values, labels=None, colors=colors_pie,
           autopct=lambda p: f'{p:.0f}%' if p > 5 else '', startangle=90)
    ax2.legend([er.replace('_', ' ') for er in end_reasons.index],
              fontsize=8, loc='center left', bbox_to_anchor=(1, 0.5))
    ax2.set_title('End Reasons', fontsize=12, fontweight='bold')

    # Panel 3: Length KDE
    ax3 = fig.add_subplot(gs[0, 2])
    x = np.linspace(0, np.percentile(lengths, 99), 300)
    kde = stats.gaussian_kde(lengths, bw_method=0.05)
    ax3.fill_between(x, kde(x), alpha=0.3, color=COLORS['primary'])
    ax3.plot(x, kde(x), color=COLORS['primary'], linewidth=2)
    ax3.axvline(n50, color='red', linestyle='--', label=f'N50: {format_bp(n50)}')
    ax3.set_xlabel('Read Length (bp)', fontsize=10)
    ax3.set_ylabel('Density', fontsize=10)
    ax3.set_title('Read Length', fontsize=12, fontweight='bold')
    ax3.legend(fontsize=9)

    # Panel 4: Quality KDE
    ax4 = fig.add_subplot(gs[0, 3])
    x_q = np.linspace(0, 35, 200)
    kde_q = stats.gaussian_kde(qscores, bw_method=0.1)
    ax4.fill_between(x_q, kde_q(x_q), alpha=0.3, color=COLORS['secondary'])
    ax4.plot(x_q, kde_q(x_q), color=COLORS['secondary'], linewidth=2)
    ax4.axvline(mean_q, color='red', linestyle='--', label=f'Mean: Q{mean_q:.1f}')
    for q in [10, 15, 20]:
        ax4.axvline(q, color='gray', linestyle=':', alpha=0.5)
    ax4.set_xlabel('Quality Score', fontsize=10)
    ax4.set_ylabel('Density', fontsize=10)
    ax4.set_title('Quality Score', fontsize=12, fontweight='bold')
    ax4.legend(fontsize=9)

    # Panel 5: Yield over time
    ax5 = fig.add_subplot(gs[1, :2])
    if time_col and time_col in df.columns:
        times = df[time_col].values / 3600
        sort_idx = np.argsort(times)
        cumsum = np.cumsum(lengths[sort_idx]) / 1e9
        ax5.fill_between(times[sort_idx], cumsum, alpha=0.3, color=COLORS['primary'])
        ax5.plot(times[sort_idx], cumsum, color=COLORS['primary'], linewidth=2)
        ax5.set_xlabel('Time (hours)', fontsize=10)
        ax5.set_ylabel('Cumulative Yield (Gb)', fontsize=10)
        ax5.set_title('Yield Over Time', fontsize=12, fontweight='bold')

    # Panel 6: Quality thresholds
    ax6 = fig.add_subplot(gs[1, 2])
    thresholds = [('≥Q10', np.sum(qscores >= 10) / len(qscores) * 100),
                  ('≥Q15', np.sum(qscores >= 15) / len(qscores) * 100),
                  ('≥Q20', np.sum(qscores >= 20) / len(qscores) * 100),
                  ('≥Q25', np.sum(qscores >= 25) / len(qscores) * 100)]
    labels, values = zip(*thresholds)
    colors_bar = ['#e74c3c', '#f39c12', '#27ae60', '#2ecc71']
    bars = ax6.bar(labels, values, color=colors_bar, alpha=0.7)
    for bar, val in zip(bars, values):
        ax6.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f'{val:.1f}%', ha='center', fontsize=10)
    ax6.set_ylabel('Percentage', fontsize=10)
    ax6.set_title('Quality Thresholds', fontsize=12, fontweight='bold')
    ax6.set_ylim(0, 105)

    # Panel 7: N50 by end reason
    ax7 = fig.add_subplot(gs[1, 3])
    n50_by_er = []
    er_labels = []
    er_colors = []
    for er in end_reasons.index:
        er_lengths = lengths[df[end_reason_col].values == er]
        if len(er_lengths) > 100:
            n50_by_er.append(calculate_n50(er_lengths))
            er_labels.append(er.replace('_', '\n'))
            er_colors.append(END_REASON_COLORS.get(er, COLORS['primary']))

    if n50_by_er:
        bars = ax7.bar(range(len(n50_by_er)), n50_by_er, color=er_colors, alpha=0.7)
        ax7.set_xticks(range(len(er_labels)))
        ax7.set_xticklabels(er_labels, fontsize=8)
        for bar, val in zip(bars, n50_by_er):
            ax7.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50,
                    format_bp(val), ha='center', fontsize=9)
    ax7.set_ylabel('N50 (bp)', fontsize=10)
    ax7.set_title('N50 by End Reason', fontsize=12, fontweight='bold')

    fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()
    return output_path


def plot_2d_density_by_end_reason(df, output_path, length_col, qscore_col,
                                   end_reason_col, dpi=300):
    """Generate 2D density plots for each end reason."""
    if not HAS_MATPLOTLIB:
        return None

    lengths = df[length_col].values
    qscores = df[qscore_col].values
    end_reasons = sorted(df[end_reason_col].unique())

    n_reasons = len(end_reasons)
    n_cols = min(3, n_reasons)
    n_rows = (n_reasons + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(6*n_cols, 5*n_rows))
    if n_reasons == 1:
        axes = np.array([[axes]])
    elif n_rows == 1:
        axes = axes.reshape(1, -1)

    for idx, er in enumerate(end_reasons):
        row = idx // n_cols
        col = idx % n_cols
        ax = axes[row, col]

        mask = df[end_reason_col].values == er
        er_lengths = lengths[mask]
        er_qscores = qscores[mask]

        if len(er_lengths) > 100:
            # Subsample if needed
            if len(er_lengths) > 10000:
                sample_idx = np.random.choice(len(er_lengths), 10000, replace=False)
                er_lengths = er_lengths[sample_idx]
                er_qscores = er_qscores[sample_idx]

            hb = ax.hexbin(er_lengths, er_qscores, gridsize=30,
                          cmap='viridis', mincnt=1,
                          extent=[0, np.percentile(lengths, 99), 0, 35])
            plt.colorbar(hb, ax=ax, label='Count')

        color = END_REASON_COLORS.get(er, COLORS['primary'])
        ax.set_title(f'{er}\n(n={mask.sum():,})', fontsize=11, fontweight='bold',
                    color=color)
        ax.set_xlabel('Read Length (bp)', fontsize=10)
        ax.set_ylabel('Quality Score', fontsize=10)

    # Hide unused subplots
    for idx in range(n_reasons, n_rows * n_cols):
        row = idx // n_cols
        col = idx % n_cols
        axes[row, col].axis('off')

    fig.suptitle('2D Density by End Reason', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close()
    return output_path
