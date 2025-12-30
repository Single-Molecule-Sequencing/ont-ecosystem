#!/usr/bin/env python3
"""
Detailed SMA-seq read analysis with end reason breakdowns.
Shows: length, ED, Q-score distributions - all reads vs in-range, colored by end reason.
"""

import sys
import json
from pathlib import Path
from collections import defaultdict

try:
    import pysam
except ImportError:
    sys.exit("ERROR: pysam required")

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
except ImportError:
    sys.exit("ERROR: matplotlib required")

try:
    import numpy as np
except ImportError:
    sys.exit("ERROR: numpy required")

# Size ranges for each barcode
SIZE_RANGES = {
    'BC02': (200, 260),
    'BC04': (195, 255),
    'BC07': (200, 260),
    'BC09': (195, 255),
}

# End reason colors
END_REASON_COLORS = {
    'signal_positive': '#2ecc71',  # Green
    'signal_negative': '#e74c3c',  # Red
    'unblock_mux_change': '#f39c12',  # Orange
    'data_service_unblock_mux_change': '#9b59b6',  # Purple
    'unknown': '#95a5a6',  # Gray
}


def load_end_reasons(json_path='end_reasons.json'):
    """Load end reasons from JSON file."""
    if not Path(json_path).exists():
        return {}
    with open(json_path) as f:
        data = json.load(f)
    return data.get('end_reasons', {})


def load_reads(bam_path, end_reasons=None):
    """Load read data from tagged BAM file."""
    if end_reasons is None:
        end_reasons = {}

    reads = []
    with pysam.AlignmentFile(str(bam_path), 'rb', check_sq=False) as bam:
        for read in bam:
            seq = read.query_sequence
            rlen = len(seq) if seq else 0

            try:
                eq = read.get_tag('eq')
            except:
                eq = 0.0
            try:
                ed = read.get_tag('ed')
            except:
                ed = 0
            try:
                st = read.get_tag('st')
            except:
                st = 'fwd'

            end_reason = end_reasons.get(read.query_name, 'unknown')

            reads.append({
                'name': read.query_name,
                'length': rlen,
                'eq': eq,
                'ed': ed,
                'strand': st,
                'end_reason': end_reason,
            })
    return reads


def main():
    input_dir = Path('tagged_reads')
    output_dir = Path('analysis_plots')
    output_dir.mkdir(exist_ok=True)

    bam_files = sorted(input_dir.glob('*_tagged.bam'))
    if not bam_files:
        print("No tagged BAM files found")
        return

    print("=" * 70)
    print("SMA-seq Detailed Read Analysis")
    print("=" * 70)

    # Load end reasons
    print("\nLoading end reasons...")
    end_reasons = load_end_reasons()
    print(f"  {len(end_reasons)} end reasons loaded")

    # Load all data
    all_data = {}
    for bam_file in bam_files:
        bc = bam_file.stem.replace('_tagged', '')
        reads = load_reads(bam_file, end_reasons)
        all_data[bc] = reads
        print(f"  {bc}: {len(reads)} reads")

    barcodes = ['BC02', 'BC04', 'BC07', 'BC09']
    n_barcodes = len([bc for bc in barcodes if bc in all_data])

    # Create figure: 4 rows (barcodes) x 4 columns (length, length by end reason, ED, Q)
    fig, axes = plt.subplots(n_barcodes, 4, figsize=(20, 4*n_barcodes))
    if n_barcodes == 1:
        axes = axes.reshape(1, -1)

    row = 0
    for bc in barcodes:
        if bc not in all_data:
            continue

        reads = all_data[bc]
        min_sz, max_sz = SIZE_RANGES[bc]

        lengths = np.array([r['length'] for r in reads])
        eds = np.array([r['ed'] for r in reads])
        eqs = np.array([r['eq'] for r in reads])
        end_reasons_arr = np.array([r['end_reason'] for r in reads])

        # In-range mask
        in_range_mask = (lengths >= min_sz) & (lengths <= max_sz)
        in_range_lens = lengths[in_range_mask]
        in_range_eds = eds[in_range_mask]
        in_range_eqs = eqs[in_range_mask]

        # Print summary
        print(f"\n{bc}: {len(reads)} reads, {len(in_range_lens)} in-range ({100*len(in_range_lens)/len(reads):.1f}%)")
        print(f"  Length: median={np.median(lengths):.0f}, mean={np.mean(lengths):.0f}")
        print(f"  ED: median={np.median(eds):.0f}, mean={np.mean(eds):.0f}")
        print(f"  Q: median={np.median(eqs):.1f}, mean={np.mean(eqs):.1f}")

        # ===== Plot 1: Length - All vs In-Range =====
        ax1 = axes[row, 0]
        bins = np.linspace(0, min(600, max(500, lengths.max())), 60)

        ax1.hist(lengths, bins=bins, alpha=0.5, color='steelblue', label='All reads', edgecolor='none')
        ax1.hist(in_range_lens, bins=bins, alpha=0.8, color='#2ecc71', label=f'In-range ({min_sz}-{max_sz}bp)', edgecolor='none')

        ax1.axvline(min_sz, color='red', linestyle='--', linewidth=2, alpha=0.8)
        ax1.axvline(max_sz, color='red', linestyle='--', linewidth=2, alpha=0.8)

        ax1.set_xlabel('Read Length (bp)', fontsize=10)
        ax1.set_ylabel('Count', fontsize=10)
        ax1.set_title(f'{bc} Length Distribution\n(n={len(reads)}, {100*len(in_range_lens)/len(reads):.0f}% in-range)', fontsize=11)
        ax1.legend(fontsize=8, loc='upper right')
        ax1.set_xlim(0, 600)

        # ===== Plot 2: Length by End Reason =====
        ax2 = axes[row, 1]

        # Group by end reason
        unique_reasons = sorted(set(end_reasons_arr))
        for reason in unique_reasons:
            mask = end_reasons_arr == reason
            reason_lens = lengths[mask]
            if len(reason_lens) > 0:
                color = END_REASON_COLORS.get(reason, '#3498db')
                label = f'{reason.replace("_", " ")} ({len(reason_lens)})'
                ax2.hist(reason_lens, bins=bins, alpha=0.6, color=color, label=label, edgecolor='none')

        ax2.axvline(min_sz, color='red', linestyle='--', linewidth=2, alpha=0.8)
        ax2.axvline(max_sz, color='red', linestyle='--', linewidth=2, alpha=0.8)

        ax2.set_xlabel('Read Length (bp)', fontsize=10)
        ax2.set_ylabel('Count', fontsize=10)
        sig_pos = sum(1 for r in reads if r['end_reason'] == 'signal_positive')
        ax2.set_title(f'{bc} Length by End Reason\n({100*sig_pos/len(reads):.1f}% signal_positive)', fontsize=11)
        ax2.legend(fontsize=7, loc='upper right')
        ax2.set_xlim(0, 600)

        # ===== Plot 3: Edit Distance - All vs In-Range =====
        ax3 = axes[row, 2]
        ed_bins = np.linspace(0, min(150, eds.max() + 10), 50)

        ax3.hist(eds, bins=ed_bins, alpha=0.5, color='steelblue', label='All reads', edgecolor='none')
        ax3.hist(in_range_eds, bins=ed_bins, alpha=0.8, color='#2ecc71', label='In-range size', edgecolor='none')

        ax3.axvline(20, color='orange', linestyle='--', linewidth=2, alpha=0.8, label='ED=20')
        ax3.axvline(50, color='red', linestyle='--', linewidth=2, alpha=0.8, label='ED=50')

        ax3.set_xlabel('Edit Distance (bp)', fontsize=10)
        ax3.set_ylabel('Count', fontsize=10)
        low_ed_50 = sum(1 for e in eds if e < 50)
        ax3.set_title(f'{bc} Edit Distance\n(median={np.median(eds):.0f}, {100*low_ed_50/len(eds):.0f}% <50)', fontsize=11)
        ax3.legend(fontsize=8, loc='upper right')

        # ===== Plot 4: Q-score - All vs In-Range =====
        ax4 = axes[row, 3]
        q_bins = np.linspace(0, 25, 40)

        ax4.hist(eqs, bins=q_bins, alpha=0.5, color='steelblue', label='All reads', edgecolor='none')
        ax4.hist(in_range_eqs, bins=q_bins, alpha=0.8, color='#2ecc71', label='In-range size', edgecolor='none')

        ax4.axvline(10, color='orange', linestyle='--', linewidth=2, alpha=0.8, label='Q10')
        ax4.axvline(15, color='red', linestyle='--', linewidth=2, alpha=0.8, label='Q15')

        ax4.set_xlabel('Mean Q-score', fontsize=10)
        ax4.set_ylabel('Count', fontsize=10)
        q10_pct = 100 * sum(1 for q in eqs if q >= 10) / len(eqs)
        ax4.set_title(f'{bc} Q-score\n(median={np.median(eqs):.1f}, {q10_pct:.0f}% >=Q10)', fontsize=11)
        ax4.legend(fontsize=8, loc='upper right')

        row += 1

    plt.tight_layout()

    # Save figure
    output_file = output_dir / 'read_distributions_detailed.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"\nPlot saved to: {output_file}")

    # Summary table
    print("\n" + "=" * 80)
    print("Summary Statistics")
    print("=" * 80)
    print(f"{'Barcode':<8} {'Reads':>8} {'In-Range':>10} {'Med Len':>10} {'Med ED':>10} {'Med Q':>8} {'Q>=10':>8} {'sig_pos':>10}")
    print("-" * 80)
    for bc in barcodes:
        if bc not in all_data:
            continue
        reads = all_data[bc]
        min_sz, max_sz = SIZE_RANGES[bc]
        lengths = np.array([r['length'] for r in reads])
        eds = np.array([r['ed'] for r in reads])
        eqs = np.array([r['eq'] for r in reads])
        in_range = sum(1 for r in reads if min_sz <= r['length'] <= max_sz)
        pct = 100 * in_range / len(reads)
        q10_pct = 100 * sum(1 for q in eqs if q >= 10) / len(eqs)
        sig_pos = sum(1 for r in reads if r['end_reason'] == 'signal_positive')
        sig_pos_pct = 100 * sig_pos / len(reads)
        print(f"{bc:<8} {len(reads):>8} {pct:>9.1f}% {np.median(lengths):>10.0f} {np.median(eds):>10.0f} {np.median(eqs):>8.1f} {q10_pct:>7.1f}% {sig_pos_pct:>9.1f}%")


if __name__ == '__main__':
    main()
