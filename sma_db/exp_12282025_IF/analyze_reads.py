#!/usr/bin/env python3
"""
Analyze tagged SMA-seq reads - distributions of length, edit distance, Q-score, end reason.
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

            # Get tags
            try:
                eq = read.get_tag('eq')
            except:
                eq = 0.0
            try:
                ed = read.get_tag('ed')
            except:
                ed = 0
            try:
                sz = read.get_tag('sz')
            except:
                sz = 'unknown'
            try:
                st = read.get_tag('st')
            except:
                st = 'fwd'

            # Get end reason from preloaded data
            end_reason = end_reasons.get(read.query_name, 'unknown')

            reads.append({
                'name': read.query_name,
                'length': rlen,
                'eq': eq,
                'ed': ed,
                'sz': sz,
                'strand': st,
                'end_reason': end_reason,
            })
    return reads

def main():
    input_dir = Path('tagged_reads')
    output_dir = Path('analysis_plots')
    output_dir.mkdir(exist_ok=True)

    # Find all tagged BAM files
    bam_files = sorted(input_dir.glob('*_tagged.bam'))

    if not bam_files:
        print("No tagged BAM files found in tagged_reads/")
        return

    print("=" * 70)
    print("SMA-seq Read Analysis")
    print("=" * 70)

    # Load end reasons from JSON
    print("\nLoading end reasons...")
    end_reasons = load_end_reasons()
    print(f"  {len(end_reasons)} end reasons loaded")

    # Load all data
    all_data = {}
    for bam_file in bam_files:
        bc = bam_file.stem.replace('_tagged', '')
        print(f"\nLoading {bc}...")
        reads = load_reads(bam_file, end_reasons)
        all_data[bc] = reads
        print(f"  {len(reads)} reads loaded")

    # Create figure with subplots (4 columns: length, ED, Q-score, end reason)
    fig = plt.figure(figsize=(20, 16))

    barcodes = ['BC02', 'BC04', 'BC07', 'BC09']
    n_barcodes = len([bc for bc in barcodes if bc in all_data])

    plot_idx = 1

    for bc in barcodes:
        if bc not in all_data:
            continue

        reads = all_data[bc]
        min_sz, max_sz = SIZE_RANGES[bc]

        lengths = np.array([r['length'] for r in reads])
        eds = np.array([r['ed'] for r in reads])
        eqs = np.array([r['eq'] for r in reads])
        strands = np.array([r['strand'] for r in reads])

        # Masks for in-range and strand
        in_range_mask = (lengths >= min_sz) & (lengths <= max_sz)
        fwd_mask = strands == 'fwd'
        rev_mask = strands == 'rev'

        in_range_lens = lengths[in_range_mask]
        in_range_eds = eds[in_range_mask]
        in_range_eqs = eqs[in_range_mask]

        # Strand-specific data
        fwd_lens = lengths[fwd_mask]
        rev_lens = lengths[rev_mask]
        fwd_eds = eds[fwd_mask]
        rev_eds = eds[rev_mask]

        print(f"\n{'='*50}")
        print(f"{bc} Analysis")
        print(f"{'='*50}")
        print(f"  Total reads: {len(reads)}")
        print(f"  In-range ({min_sz}-{max_sz}bp): {len(in_range_lens)} ({100*len(in_range_lens)/len(reads):.1f}%)")
        print(f"  Length: min={lengths.min()}, max={lengths.max()}, median={np.median(lengths):.0f}, mean={np.mean(lengths):.0f}")
        print(f"  Edit dist: min={eds.min()}, max={eds.max()}, median={np.median(eds):.0f}, mean={np.mean(eds):.0f}")
        print(f"  Q-score: min={eqs.min():.1f}, max={eqs.max():.1f}, median={np.median(eqs):.1f}, mean={np.mean(eqs):.1f}")

        # Strand breakdown
        n_fwd = len(fwd_lens)
        n_rev = len(rev_lens)
        if n_rev > 0:
            print(f"  Strand: fwd={n_fwd} ({100*n_fwd/len(reads):.1f}%), rev={n_rev} ({100*n_rev/len(reads):.1f}%)")
            if len(fwd_eds) > 0:
                print(f"    Fwd ED: median={np.median(fwd_eds):.0f}, mean={np.mean(fwd_eds):.0f}")
            if len(rev_eds) > 0:
                print(f"    Rev ED: median={np.median(rev_eds):.0f}, mean={np.mean(rev_eds):.0f}")

        # Size breakdown
        short = sum(1 for r in reads if r['length'] < min_sz)
        long = sum(1 for r in reads if r['length'] > max_sz)
        print(f"  Size breakdown: short={short}, in_range={len(in_range_lens)}, long={long}")

        # End reason breakdown
        end_reason_counts = defaultdict(int)
        for r in reads:
            end_reason_counts[r['end_reason']] += 1
        print(f"  End reasons: " + ", ".join(f"{k}={v}" for k, v in sorted(end_reason_counts.items(), key=lambda x: -x[1])))

        # ===== Plot 1: Length distribution =====
        ax1 = fig.add_subplot(n_barcodes, 4, plot_idx)

        bins = np.linspace(0, max(500, lengths.max()), 60)

        # For dual-strand barcodes, show by strand; otherwise show all/in-range
        if n_rev > 0 and n_fwd > 0:
            # Dual-strand: show fwd vs rev
            ax1.hist(fwd_lens, bins=bins, alpha=0.6, color='#3498db', label=f'Forward ({n_fwd})', edgecolor='none')
            ax1.hist(rev_lens, bins=bins, alpha=0.6, color='#e74c3c', label=f'Reverse ({n_rev})', edgecolor='none')
        else:
            # Single-strand: show all/in-range
            ax1.hist(lengths, bins=bins, alpha=0.5, color='steelblue', label='All reads', edgecolor='none')
            ax1.hist(in_range_lens, bins=bins, alpha=0.8, color='#2ecc71', label=f'In-range ({min_sz}-{max_sz}bp)', edgecolor='none')

        # Add vertical lines for size range
        ax1.axvline(min_sz, color='red', linestyle='--', linewidth=2, alpha=0.8)
        ax1.axvline(max_sz, color='red', linestyle='--', linewidth=2, alpha=0.8)

        ax1.set_xlabel('Read Length (bp)', fontsize=10)
        ax1.set_ylabel('Count', fontsize=10)
        if n_rev > 0:
            ax1.set_title(f'{bc} Length by Strand\n(n={len(reads)}, {100*n_fwd/len(reads):.0f}% fwd, {100*n_rev/len(reads):.0f}% rev)', fontsize=11)
        else:
            ax1.set_title(f'{bc} Read Length Distribution\n(n={len(reads)}, {100*len(in_range_lens)/len(reads):.0f}% in-range)', fontsize=11)
        ax1.legend(fontsize=9, loc='upper right')
        ax1.set_xlim(0, 500)

        plot_idx += 1

        # ===== Plot 2: Edit distance distribution =====
        ax2 = fig.add_subplot(n_barcodes, 4, plot_idx)

        ed_bins = np.linspace(0, min(200, eds.max() + 10), 50)

        # For dual-strand barcodes, show by strand
        if n_rev > 0 and n_fwd > 0 and len(fwd_eds) > 0 and len(rev_eds) > 0:
            ax2.hist(fwd_eds, bins=ed_bins, alpha=0.6, color='#3498db', label=f'Fwd (med={np.median(fwd_eds):.0f})', edgecolor='none')
            ax2.hist(rev_eds, bins=ed_bins, alpha=0.6, color='#e74c3c', label=f'Rev (med={np.median(rev_eds):.0f})', edgecolor='none')
        else:
            ax2.hist(eds, bins=ed_bins, alpha=0.5, color='steelblue', label='All reads', edgecolor='none')
            ax2.hist(in_range_eds, bins=ed_bins, alpha=0.8, color='#2ecc71', label='In-range size', edgecolor='none')

        # Threshold lines
        ax2.axvline(20, color='orange', linestyle='--', linewidth=2, alpha=0.8, label='ED=20')
        ax2.axvline(50, color='red', linestyle='--', linewidth=2, alpha=0.8, label='ED=50')

        ax2.set_xlabel('Edit Distance (bp)', fontsize=10)
        ax2.set_ylabel('Count', fontsize=10)
        low_ed_20 = sum(1 for e in eds if e < 20)
        low_ed_50 = sum(1 for e in eds if e < 50)
        ax2.set_title(f'{bc} Edit Distance\n(median={np.median(eds):.0f}, {100*low_ed_20/len(eds):.0f}%<20, {100*low_ed_50/len(eds):.0f}%<50)', fontsize=11)
        ax2.legend(fontsize=9, loc='upper right')

        plot_idx += 1

        # ===== Plot 3: Q-score distribution =====
        ax3 = fig.add_subplot(n_barcodes, 4, plot_idx)

        # All reads
        q_bins = np.linspace(0, 25, 40)
        ax3.hist(eqs, bins=q_bins, alpha=0.5, color='steelblue', label='All reads', edgecolor='none')

        # In-range only
        ax3.hist(in_range_eqs, bins=q_bins, alpha=0.8, color='#2ecc71', label='In-range size', edgecolor='none')

        # Threshold lines
        ax3.axvline(10, color='orange', linestyle='--', linewidth=2, alpha=0.8, label='Q10 (10% error)')
        ax3.axvline(15, color='red', linestyle='--', linewidth=2, alpha=0.8, label='Q15 (3% error)')

        ax3.set_xlabel('Mean Q-score', fontsize=10)
        ax3.set_ylabel('Count', fontsize=10)
        q10_pct = 100 * sum(1 for q in eqs if q >= 10) / len(eqs)
        ax3.set_title(f'{bc} Q-score\n(median={np.median(eqs):.1f}, {q10_pct:.0f}% ≥Q10)', fontsize=11)
        ax3.legend(fontsize=9, loc='upper right')

        plot_idx += 1

        # ===== Plot 4: End Reason distribution =====
        ax4 = fig.add_subplot(n_barcodes, 4, plot_idx)

        # Count end reasons
        reasons = sorted(end_reason_counts.keys())
        counts = [end_reason_counts[r] for r in reasons]

        # Define colors for different end reasons
        reason_colors = {
            'signal_positive': '#2ecc71',  # Green - normal completion
            'signal_negative': '#e74c3c',  # Red - abnormal
            'unblock_mux_change': '#f39c12',  # Orange - mux ejection
            'data_service_unblock_mux_change': '#9b59b6',  # Purple - adaptive sampling
            'unknown': '#95a5a6',  # Gray
        }
        colors = [reason_colors.get(r, '#3498db') for r in reasons]

        # Create bar chart
        bars = ax4.bar(range(len(reasons)), counts, color=colors, edgecolor='none', alpha=0.8)

        ax4.set_xticks(range(len(reasons)))
        ax4.set_xticklabels([r.replace('_', '\n') for r in reasons], fontsize=8, rotation=0)
        ax4.set_ylabel('Count', fontsize=10)

        # Calculate signal_positive percentage
        sig_pos = end_reason_counts.get('signal_positive', 0)
        sig_pos_pct = 100 * sig_pos / len(reads) if reads else 0
        ax4.set_title(f'{bc} End Reason\n({sig_pos_pct:.1f}% signal_positive)', fontsize=11)

        # Add count labels on bars
        for bar, count in zip(bars, counts):
            if count > 0:
                ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                        str(count), ha='center', va='bottom', fontsize=8)

        plot_idx += 1

    plt.tight_layout()

    # Save figure
    output_file = output_dir / 'read_distributions.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"\n{'='*70}")
    print(f"Plot saved to: {output_file}")

    # Create summary table
    print(f"\n{'='*70}")
    print("Summary Statistics")
    print("=" * 70)
    print(f"{'Barcode':<8} {'Reads':>8} {'In-Range':>10} {'Med Len':>10} {'Med ED':>10} {'Med Q':>10} {'Q≥10':>10}")
    print("-" * 70)
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
        print(f"{bc:<8} {len(reads):>8} {pct:>9.1f}% {np.median(lengths):>10.0f} {np.median(eds):>10.0f} {np.median(eqs):>10.1f} {q10_pct:>9.1f}%")

    print("\n" + "=" * 70)
    print("Note: Edit distance calculated against full expected reference:")
    print("      Adapter + Flank + Barcode + Flank + GG_junction + Target")
    print("=" * 70)

if __name__ == '__main__':
    main()
