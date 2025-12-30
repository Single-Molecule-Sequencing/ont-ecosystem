#!/usr/bin/env python3
"""
SMA-seq Q-score Analysis from Sequencing Summary

Analyzes reads from sequencing_summary.txt files with:
- Pre-computed alignment metrics (identity, accuracy)
- Per-read Q-score analysis
- Per-target statistics
- Sequence frequency analysis (using alignment accuracy as proxy)

Usage:
    python analyze_seqsum_qscore.py --summary sequencing_summary.txt --output output_dir --sample-size 100000
"""

import argparse
import sys
import os
import json
from pathlib import Path
from collections import defaultdict, Counter
import random

import numpy as np

try:
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not available, plots will be skipped")


def load_sequencing_summary(filepath: str, sample_size: int = None) -> list:
    """Load and optionally sample reads from sequencing summary."""
    print(f"Loading: {filepath}")

    reads = []
    with open(filepath, 'r') as f:
        header = f.readline().strip().split('\t')
        col_idx = {col: i for i, col in enumerate(header)}

        # Required columns
        required = ['read_id', 'mean_qscore_template', 'sequence_length_template', 'alias']
        for col in required:
            if col not in col_idx:
                print(f"Error: Missing required column: {col}")
                sys.exit(1)

        # Optional alignment columns
        has_alignment = 'alignment_identity' in col_idx

        for line in f:
            parts = line.strip().split('\t')
            if len(parts) < len(header):
                continue

            try:
                read = {
                    'read_id': parts[col_idx['read_id']],
                    'qscore': float(parts[col_idx['mean_qscore_template']]),
                    'length': int(parts[col_idx['sequence_length_template']]),
                    'alias': parts[col_idx['alias']],
                    'passes': parts[col_idx.get('passes_filtering', 0)] == 'TRUE' if 'passes_filtering' in col_idx else True,
                    'end_reason': parts[col_idx.get('end_reason', '')] if 'end_reason' in col_idx else 'unknown',
                }

                # Add alignment info if available
                if has_alignment:
                    identity = parts[col_idx['alignment_identity']]
                    accuracy = parts[col_idx['alignment_accuracy']]
                    num_correct = parts[col_idx.get('alignment_num_correct', '')]
                    num_aligned = parts[col_idx.get('alignment_num_aligned', '')]
                    genome = parts[col_idx.get('alignment_genome', '')]

                    read['identity'] = float(identity) if identity not in ['', '-1', '-1.000000'] else None
                    read['accuracy'] = float(accuracy) if accuracy not in ['', '-1', '-1.000000'] else None
                    read['num_correct'] = int(num_correct) if num_correct not in ['', '-1'] else None
                    read['num_aligned'] = int(num_aligned) if num_aligned not in ['', '-1'] else None
                    read['genome'] = genome if genome not in ['', '*'] else None
                    read['has_alignment'] = read['identity'] is not None and read['identity'] >= 0
                else:
                    read['has_alignment'] = False

                reads.append(read)
            except (ValueError, IndexError) as e:
                continue

    print(f"  Loaded {len(reads):,} reads")

    if sample_size and len(reads) > sample_size:
        print(f"  Sampling {sample_size:,} reads...")
        reads = random.sample(reads, sample_size)

    return reads


def compute_statistics(reads: list) -> dict:
    """Compute comprehensive statistics."""
    stats = {
        'total_reads': len(reads),
        'passing_reads': sum(1 for r in reads if r['passes']),
        'aligned_reads': sum(1 for r in reads if r.get('has_alignment', False)),
    }

    # Q-score statistics
    qscores = [r['qscore'] for r in reads if r['qscore'] > 0]
    if qscores:
        stats['mean_qscore'] = float(np.mean(qscores))
        stats['median_qscore'] = float(np.median(qscores))
        stats['std_qscore'] = float(np.std(qscores))
        stats['qscore_distribution'] = qscores

    # Length statistics
    lengths = [r['length'] for r in reads]
    if lengths:
        stats['mean_length'] = float(np.mean(lengths))
        stats['median_length'] = float(np.median(lengths))
        stats['total_bases'] = sum(lengths)

    # Alignment statistics
    aligned_reads = [r for r in reads if r.get('has_alignment', False)]
    if aligned_reads:
        identities = [r['identity'] for r in aligned_reads if r['identity'] is not None]
        accuracies = [r['accuracy'] for r in aligned_reads if r['accuracy'] is not None]

        if identities:
            stats['mean_identity'] = float(np.mean(identities))
            stats['median_identity'] = float(np.median(identities))
            stats['perfect_reads'] = sum(1 for i in identities if i >= 0.9999)
            stats['identity_distribution'] = identities

        if accuracies:
            stats['mean_accuracy'] = float(np.mean(accuracies))
            stats['median_accuracy'] = float(np.median(accuracies))
            stats['accuracy_distribution'] = accuracies
    else:
        stats['perfect_reads'] = 0

    # Per-target statistics
    by_target = defaultdict(list)
    for r in reads:
        alias = r['alias']
        if alias and alias not in ['unclassified', 'mixed']:
            by_target[alias].append(r)

    stats['by_target'] = {}
    for target, treads in by_target.items():
        tqs = [r['qscore'] for r in treads if r['qscore'] > 0]
        tids = [r['identity'] for r in treads if r.get('identity') is not None]

        target_stats = {
            'count': len(treads),
            'mean_qscore': float(np.mean(tqs)) if tqs else 0,
            'mean_length': float(np.mean([r['length'] for r in treads])),
        }

        if tids:
            target_stats['mean_identity'] = float(np.mean(tids))
            target_stats['perfect_count'] = sum(1 for i in tids if i >= 0.9999)

        stats['by_target'][target] = target_stats

    # End reason distribution
    end_reasons = Counter(r['end_reason'] for r in reads)
    stats['end_reasons'] = dict(end_reasons)

    # Q-score by alignment quality bins
    if aligned_reads:
        qscore_by_quality = defaultdict(list)
        for r in aligned_reads:
            if r['identity'] is not None:
                if r['identity'] >= 0.99:
                    qscore_by_quality['perfect'].append(r['qscore'])
                elif r['identity'] >= 0.95:
                    qscore_by_quality['high'].append(r['qscore'])
                elif r['identity'] >= 0.90:
                    qscore_by_quality['medium'].append(r['qscore'])
                else:
                    qscore_by_quality['low'].append(r['qscore'])

        stats['qscore_by_quality'] = {
            k: {'mean': float(np.mean(v)), 'count': len(v)}
            for k, v in qscore_by_quality.items() if v
        }

    return stats


def create_visualizations(stats: dict, output_dir: str):
    """Create comprehensive visualizations."""
    if not HAS_MATPLOTLIB:
        print("Matplotlib not available, skipping visualizations")
        return

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Set up style
    plt.rcParams['axes.grid'] = True
    plt.rcParams['grid.alpha'] = 0.3
    plt.rcParams['figure.facecolor'] = 'white'
    plt.rcParams['axes.facecolor'] = 'white'

    # ==================== Figure 1: Overview ====================
    fig = plt.figure(figsize=(16, 12))
    gs = gridspec.GridSpec(3, 3, figure=fig)

    # 1a. Q-score distribution
    ax1 = fig.add_subplot(gs[0, 0])
    qscores = stats.get('qscore_distribution', [])
    if qscores:
        ax1.hist(qscores, bins=50, color='coral', edgecolor='black', alpha=0.7)
        ax1.axvline(stats['mean_qscore'], color='red', linestyle='--',
                   label=f'Mean: {stats["mean_qscore"]:.1f}')
        ax1.axvline(stats['median_qscore'], color='blue', linestyle='--',
                   label=f'Median: {stats["median_qscore"]:.1f}')
        ax1.set_xlabel('Mean Q-score')
        ax1.set_ylabel('Read Count')
        ax1.set_title('Per-Read Q-score Distribution')
        ax1.legend()

    # 1b. Alignment identity distribution
    ax2 = fig.add_subplot(gs[0, 1])
    identities = stats.get('identity_distribution', [])
    if identities:
        ax2.hist(identities, bins=50, color='steelblue', edgecolor='black', alpha=0.7)
        ax2.axvline(stats.get('mean_identity', 0), color='red', linestyle='--',
                   label=f'Mean: {stats.get("mean_identity", 0):.3f}')
        ax2.set_xlabel('Alignment Identity')
        ax2.set_ylabel('Read Count')
        ax2.set_title(f'Alignment Identity Distribution\n(Perfect: {stats.get("perfect_reads", 0):,})')
        ax2.legend()
    else:
        ax2.text(0.5, 0.5, 'No alignment data', ha='center', va='center', transform=ax2.transAxes)
        ax2.set_title('Alignment Identity Distribution')

    # 1c. Per-target read counts
    ax3 = fig.add_subplot(gs[0, 2])
    by_target = stats.get('by_target', {})
    if by_target:
        sorted_targets = sorted(by_target.items(), key=lambda x: x[1]['count'], reverse=True)
        targets = [t[0] for t in sorted_targets[:10]]
        counts = [t[1]['count'] for t in sorted_targets[:10]]
        colors = plt.cm.tab10(np.linspace(0, 1, len(targets)))
        ax3.barh(range(len(targets)), counts, color=colors)
        ax3.set_yticks(range(len(targets)))
        ax3.set_yticklabels(targets, fontsize=8)
        ax3.set_xlabel('Read Count')
        ax3.set_title('Reads per Target (Top 10)')
        ax3.invert_yaxis()

    # 1d. Q-score vs Identity scatter
    ax4 = fig.add_subplot(gs[1, 0])
    qscores = stats.get('qscore_distribution', [])
    identities = stats.get('identity_distribution', [])
    if len(qscores) == len(identities) and qscores:
        # Subsample for plotting
        n_plot = min(10000, len(qscores))
        idx = random.sample(range(len(qscores)), n_plot)
        ax4.scatter([qscores[i] for i in idx], [identities[i] for i in idx],
                   alpha=0.3, s=5, c='steelblue')
        ax4.set_xlabel('Mean Q-score')
        ax4.set_ylabel('Alignment Identity')
        ax4.set_title('Q-score vs Identity')
    else:
        ax4.text(0.5, 0.5, 'Data mismatch', ha='center', va='center', transform=ax4.transAxes)

    # 1e. Per-target Q-score comparison
    ax5 = fig.add_subplot(gs[1, 1])
    if by_target:
        sorted_targets = sorted(by_target.items(), key=lambda x: x[1]['count'], reverse=True)[:10]
        targets = [t[0] for t in sorted_targets]
        qscores_t = [t[1]['mean_qscore'] for t in sorted_targets]
        colors = ['green' if q >= 15 else 'orange' if q >= 10 else 'red' for q in qscores_t]
        ax5.barh(range(len(targets)), qscores_t, color=colors)
        ax5.set_yticks(range(len(targets)))
        ax5.set_yticklabels(targets, fontsize=8)
        ax5.set_xlabel('Mean Q-score')
        ax5.set_title('Mean Q-score by Target')
        ax5.axvline(15, color='green', linestyle='--', alpha=0.5)
        ax5.axvline(10, color='orange', linestyle='--', alpha=0.5)
        ax5.invert_yaxis()

    # 1f. End reason distribution
    ax6 = fig.add_subplot(gs[1, 2])
    end_reasons = stats.get('end_reasons', {})
    if end_reasons:
        sorted_er = sorted(end_reasons.items(), key=lambda x: x[1], reverse=True)
        reasons = [r[0][:20] for r in sorted_er[:8]]
        er_counts = [r[1] for r in sorted_er[:8]]
        ax6.barh(range(len(reasons)), er_counts, color='mediumpurple')
        ax6.set_yticks(range(len(reasons)))
        ax6.set_yticklabels(reasons, fontsize=8)
        ax6.set_xlabel('Read Count')
        ax6.set_title('End Reason Distribution')
        ax6.invert_yaxis()

    # 1g. Q-score by alignment quality
    ax7 = fig.add_subplot(gs[2, 0])
    qscore_by_quality = stats.get('qscore_by_quality', {})
    if qscore_by_quality:
        categories = ['perfect', 'high', 'medium', 'low']
        q_means = [qscore_by_quality.get(c, {}).get('mean', 0) for c in categories]
        q_counts = [qscore_by_quality.get(c, {}).get('count', 0) for c in categories]
        colors = ['green', 'lightgreen', 'orange', 'red']
        bars = ax7.bar(range(len(categories)), q_means, color=colors, edgecolor='black')
        ax7.set_xticks(range(len(categories)))
        ax7.set_xticklabels([f'{c}\n(n={q_counts[i]:,})' for i, c in enumerate(categories)], fontsize=8)
        ax7.set_ylabel('Mean Q-score')
        ax7.set_title('Q-score by Alignment Quality\n(perfect>99%, high>95%, medium>90%)')
        for i, (bar, val) in enumerate(zip(bars, q_means)):
            ax7.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                    f'{val:.1f}', ha='center', fontsize=9)

    # 1h. Summary statistics text
    ax8 = fig.add_subplot(gs[2, 1:])
    ax8.axis('off')

    summary_text = f"""Summary Statistics
==================
Total reads: {stats['total_reads']:,}
Passing reads: {stats.get('passing_reads', 0):,}
Aligned reads: {stats.get('aligned_reads', 0):,}
Perfect reads (identity >= 99.99%): {stats.get('perfect_reads', 0):,}

Q-score Statistics:
  Mean: {stats.get('mean_qscore', 0):.2f}
  Median: {stats.get('median_qscore', 0):.2f}
  Std: {stats.get('std_qscore', 0):.2f}

Alignment Statistics:
  Mean Identity: {stats.get('mean_identity', 0):.4f}
  Median Identity: {stats.get('median_identity', 0):.4f}
  Mean Accuracy: {stats.get('mean_accuracy', 0):.4f}

Length Statistics:
  Mean: {stats.get('mean_length', 0):.1f} bp
  Median: {stats.get('median_length', 0):.1f} bp
  Total Bases: {stats.get('total_bases', 0)/1e6:.2f} Mb
"""
    ax8.text(0.1, 0.95, summary_text, transform=ax8.transAxes, fontsize=10,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    fig.savefig(output_dir / 'overview_analysis.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  Generated: overview_analysis.png")

    # ==================== Figure 2: Q-score Calibration ====================
    fig2, axes = plt.subplots(2, 2, figsize=(14, 12))

    # 2a. Q-score vs empirical error rate
    ax = axes[0, 0]
    identities = stats.get('identity_distribution', [])
    qscores = stats.get('qscore_distribution', [])
    if identities and qscores and len(identities) == len(qscores):
        # Bin by Q-score and compute empirical error rate
        qscore_bins = np.arange(0, 50, 2)
        bin_data = defaultdict(list)
        for q, i in zip(qscores, identities):
            bin_idx = int(q // 2) * 2
            bin_data[bin_idx].append(1 - i)  # error rate

        bin_centers = []
        emp_error = []
        pred_error = []
        for b in sorted(bin_data.keys()):
            if len(bin_data[b]) >= 10:
                bin_centers.append(b + 1)
                emp_error.append(np.mean(bin_data[b]))
                pred_error.append(10 ** (-(b + 1) / 10))

        if bin_centers:
            ax.scatter(pred_error, emp_error, c='steelblue', s=50, alpha=0.7, label='Observed')
            max_val = max(max(pred_error), max(emp_error))
            ax.plot([0, max_val], [0, max_val], 'r--', label='Perfect calibration')
            ax.set_xlabel('Predicted Error Rate (from Q-score)')
            ax.set_ylabel('Empirical Error Rate (1 - identity)')
            ax.set_title('Q-score Calibration')
            ax.legend()
    else:
        ax.text(0.5, 0.5, 'Insufficient data', ha='center', va='center', transform=ax.transAxes)

    # 2b. Q-score distribution by quality category
    ax = axes[0, 1]
    qscore_by_quality = stats.get('qscore_by_quality', {})
    if qscore_by_quality:
        categories = ['perfect', 'high', 'medium', 'low']
        colors = {'perfect': 'green', 'high': 'lightgreen', 'medium': 'orange', 'low': 'red'}
        for cat in categories:
            if cat in qscore_by_quality:
                # We only have mean, so show as bar + annotation
                pass
        ax.text(0.5, 0.5, 'Q-score distributions\nby quality category\n(see overview)',
               ha='center', va='center', transform=ax.transAxes)
    ax.set_title('Q-score by Alignment Quality')

    # 2c. Identity distribution by Q-score bins
    ax = axes[1, 0]
    if identities and qscores and len(identities) == len(qscores):
        q_bins = [(0, 10), (10, 15), (15, 20), (20, 30), (30, 50)]
        colors = ['red', 'orange', 'yellow', 'lightgreen', 'green']
        for (qmin, qmax), color in zip(q_bins, colors):
            ids = [i for q, i in zip(qscores, identities) if qmin <= q < qmax]
            if ids:
                ax.hist(ids, bins=30, alpha=0.5, label=f'Q{qmin}-{qmax} (n={len(ids):,})',
                       color=color, density=True)
        ax.set_xlabel('Alignment Identity')
        ax.set_ylabel('Density')
        ax.set_title('Identity Distribution by Q-score Bin')
        ax.legend(fontsize=8)

    # 2d. Per-target identity
    ax = axes[1, 1]
    by_target = stats.get('by_target', {})
    if by_target:
        sorted_targets = sorted(by_target.items(), key=lambda x: x[1]['count'], reverse=True)[:10]
        targets = [t[0] for t in sorted_targets]
        ids = [t[1].get('mean_identity', 0) for t in sorted_targets]
        perfect = [t[1].get('perfect_count', 0) for t in sorted_targets]

        x = np.arange(len(targets))
        width = 0.4
        bars1 = ax.bar(x - width/2, ids, width, label='Mean Identity', color='steelblue')
        ax.set_ylabel('Mean Identity', color='steelblue')
        ax.tick_params(axis='y', labelcolor='steelblue')

        ax2 = ax.twinx()
        bars2 = ax2.bar(x + width/2, perfect, width, label='Perfect Reads', color='green', alpha=0.7)
        ax2.set_ylabel('Perfect Reads', color='green')
        ax2.tick_params(axis='y', labelcolor='green')

        ax.set_xticks(x)
        ax.set_xticklabels(targets, rotation=45, ha='right', fontsize=8)
        ax.set_title('Alignment Quality by Target')
        ax.legend(loc='upper left')
        ax2.legend(loc='upper right')

    plt.tight_layout()
    fig2.savefig(output_dir / 'qscore_calibration.png', dpi=150, bbox_inches='tight')
    plt.close(fig2)
    print(f"  Generated: qscore_calibration.png")

    # ==================== Figure 3: Per-Target Analysis ====================
    fig3, axes = plt.subplots(2, 2, figsize=(14, 12))

    by_target = stats.get('by_target', {})
    if by_target:
        sorted_targets = sorted(by_target.items(), key=lambda x: x[1]['count'], reverse=True)

        # 3a. Read count by target
        ax = axes[0, 0]
        targets = [t[0] for t in sorted_targets]
        counts = [t[1]['count'] for t in sorted_targets]
        ax.bar(range(len(targets)), counts, color='steelblue')
        ax.set_xticks(range(len(targets)))
        ax.set_xticklabels(targets, rotation=45, ha='right', fontsize=8)
        ax.set_ylabel('Read Count')
        ax.set_title('Read Distribution by Target')

        # 3b. Mean length by target
        ax = axes[0, 1]
        lengths = [t[1]['mean_length'] for t in sorted_targets]
        ax.bar(range(len(targets)), lengths, color='coral')
        ax.set_xticks(range(len(targets)))
        ax.set_xticklabels(targets, rotation=45, ha='right', fontsize=8)
        ax.set_ylabel('Mean Length (bp)')
        ax.set_title('Mean Read Length by Target')

        # 3c. Q-score by target
        ax = axes[1, 0]
        qscores_t = [t[1]['mean_qscore'] for t in sorted_targets]
        colors = ['green' if q >= 15 else 'orange' if q >= 10 else 'red' for q in qscores_t]
        ax.bar(range(len(targets)), qscores_t, color=colors, edgecolor='black')
        ax.set_xticks(range(len(targets)))
        ax.set_xticklabels(targets, rotation=45, ha='right', fontsize=8)
        ax.set_ylabel('Mean Q-score')
        ax.set_title('Mean Q-score by Target')
        ax.axhline(15, color='green', linestyle='--', alpha=0.5)
        ax.axhline(10, color='orange', linestyle='--', alpha=0.5)

        # 3d. Perfect reads percentage by target
        ax = axes[1, 1]
        perfect_pct = []
        for t in sorted_targets:
            total = t[1]['count']
            perfect = t[1].get('perfect_count', 0)
            pct = (perfect / total * 100) if total > 0 else 0
            perfect_pct.append(pct)
        ax.bar(range(len(targets)), perfect_pct, color='green', edgecolor='black')
        ax.set_xticks(range(len(targets)))
        ax.set_xticklabels(targets, rotation=45, ha='right', fontsize=8)
        ax.set_ylabel('Perfect Reads (%)')
        ax.set_title('Perfect Read Percentage by Target')

    plt.tight_layout()
    fig3.savefig(output_dir / 'target_analysis.png', dpi=150, bbox_inches='tight')
    plt.close(fig3)
    print(f"  Generated: target_analysis.png")


def main():
    parser = argparse.ArgumentParser(description='SMA-seq Q-score Analysis from Sequencing Summary')
    parser.add_argument('--summary', required=True, help='Path to sequencing_summary.txt')
    parser.add_argument('--output', '-o', required=True, help='Output directory')
    parser.add_argument('--sample-size', type=int, default=100000, help='Number of reads to sample')
    args = parser.parse_args()

    # Load data
    reads = load_sequencing_summary(args.summary, args.sample_size)

    # Compute statistics
    print("Computing statistics...")
    stats = compute_statistics(reads)

    # Save statistics
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Remove large arrays for JSON serialization
    stats_json = {k: v for k, v in stats.items()
                  if k not in ['qscore_distribution', 'identity_distribution', 'accuracy_distribution']}

    with open(output_dir / 'statistics.json', 'w') as f:
        json.dump(stats_json, f, indent=2)
    print(f"Saved: {output_dir / 'statistics.json'}")

    # Create visualizations
    print("Creating visualizations...")
    create_visualizations(stats, args.output)

    print(f"\nAnalysis complete!")
    print(f"  Total reads: {stats['total_reads']:,}")
    print(f"  Aligned reads: {stats.get('aligned_reads', 0):,}")
    print(f"  Perfect reads: {stats.get('perfect_reads', 0):,}")
    print(f"  Mean Q-score: {stats.get('mean_qscore', 0):.2f}")
    print(f"  Mean Identity: {stats.get('mean_identity', 0):.4f}")


if __name__ == '__main__':
    main()
