#!/usr/bin/env python3
"""
Custom barcode demultiplexer for SMA-seq using edlib.
Handles variable-length custom barcodes that Dorado's strict length requirements don't support.
"""

import argparse
import sys
import os
from pathlib import Path
from collections import defaultdict

try:
    import pysam
except ImportError:
    sys.exit("ERROR: pysam required - pip install pysam")

try:
    import edlib
except ImportError:
    sys.exit("ERROR: edlib required - pip install edlib")


# Custom barcodes (actual sequences used in library prep)
CUSTOM_BARCODES = {
    'BC02': 'ACAGACGACTACAAACGGAATCGA',   # 24bp - matches standard NB02
    'BC04': 'TAGCAAACACGATAGAATCCGAA',    # 23bp - custom
    'BC07': 'GGATTCATTCCCACGGTAACAC',     # 22bp - custom
    'BC09': 'AACCAAGACTCGCTGTGCCTAGTT',   # 24bp - matches standard NB09
}

# Flanking sequences
FLANK_FRONT = 'AAGGTTAA'
FLANK_REAR = 'CAGCACCT'


def find_barcode(seq, max_ed=5):
    """
    Find the best matching barcode in the read.
    Searches for flank + barcode + flank pattern in multiple regions.

    Returns (barcode_name, edit_distance) or ('unclassified', best_ed)
    """
    if not seq or len(seq) < 50:
        return ('unclassified', -1)

    best_bc = 'unclassified'
    best_ed = float('inf')

    # Search in multiple regions (beginning, middle of short reads)
    search_regions = [
        seq[:150],  # First 150bp
        seq[-150:] if len(seq) > 200 else None,  # Last 150bp (for reverse)
    ]

    for region in search_regions:
        if region is None:
            continue

        # Try to find the flank_front pattern
        flank_aln = edlib.align(FLANK_FRONT, region, mode='HW', task='locations')

        if flank_aln['editDistance'] <= 2 and flank_aln['locations']:
            # Found flank, search for barcode right after it
            flank_end = flank_aln['locations'][0][1] + 1
            barcode_region = region[flank_end:flank_end + 30]

            for bc_name, bc_seq in CUSTOM_BARCODES.items():
                aln = edlib.align(bc_seq, barcode_region, mode='HW', task='path')
                if aln['editDistance'] < best_ed:
                    best_ed = aln['editDistance']
                    best_bc = bc_name
        else:
            # Flank not found, try direct barcode search in this region
            for bc_name, bc_seq in CUSTOM_BARCODES.items():
                aln = edlib.align(bc_seq, region, mode='HW', task='path')
                if aln['editDistance'] < best_ed:
                    best_ed = aln['editDistance']
                    best_bc = bc_name

    if best_ed <= max_ed:
        return (best_bc, best_ed)
    return ('unclassified', best_ed)


def main():
    parser = argparse.ArgumentParser(description='Custom barcode demultiplexer')
    parser.add_argument('input', nargs='+', help='Input BAM file(s)')
    parser.add_argument('-o', '--output-dir', default='demux_output', help='Output directory')
    parser.add_argument('--max-ed', type=int, default=5, help='Max edit distance for barcode matching')
    parser.add_argument('--max-reads', type=int, default=0, help='Max reads to process (0=all)')
    parser.add_argument('--emit-summary', action='store_true', help='Emit barcoding summary')
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Collect all reads by barcode assignment
    assignments = defaultdict(list)
    summary_lines = ['filename\tread_id\tbarcode\tedit_distance']
    total_reads = 0

    for bam_path in args.input:
        bam_file = Path(bam_path)
        print(f"Processing: {bam_file.name}")

        try:
            with pysam.AlignmentFile(str(bam_file), 'rb', check_sq=False) as bam:
                for read in bam:
                    if args.max_reads > 0 and total_reads >= args.max_reads:
                        break

                    seq = read.query_sequence
                    bc, ed = find_barcode(seq, args.max_ed)

                    # Store read with its barcode assignment
                    assignments[bc].append(read)
                    summary_lines.append(f"{bam_file.name}\t{read.query_name}\t{bc}\t{ed}")
                    total_reads += 1

                    if total_reads % 5000 == 0:
                        print(f"  Processed {total_reads} reads...")

            if args.max_reads > 0 and total_reads >= args.max_reads:
                break

        except Exception as e:
            print(f"Error processing {bam_file}: {e}")

    # Write output BAMs for each barcode
    print(f"\nWriting output files...")

    # Get header from first input file
    with pysam.AlignmentFile(args.input[0], 'rb', check_sq=False) as bam:
        header = bam.header.to_dict()

    for bc, reads in assignments.items():
        if not reads:
            continue

        out_bam = out_dir / f"{bc}.bam"
        with pysam.AlignmentFile(str(out_bam), 'wb', header=header) as out:
            for read in reads:
                # Add barcode tag
                read.set_tag('BC', bc, 'Z')
                out.write(read)

        print(f"  {bc}: {len(reads)} reads")

    # Write summary
    if args.emit_summary:
        summary_file = out_dir / 'barcoding_summary.txt'
        with open(summary_file, 'w') as f:
            f.write('\n'.join(summary_lines))
        print(f"\nSummary written to: {summary_file}")

    # Print stats
    print(f"\n{'='*50}")
    print(f"Total reads processed: {total_reads}")
    for bc in ['BC02', 'BC04', 'BC07', 'BC09', 'unclassified']:
        n = len(assignments.get(bc, []))
        pct = 100 * n / total_reads if total_reads > 0 else 0
        print(f"  {bc:12s}: {n:8d} ({pct:5.1f}%)")


if __name__ == '__main__':
    main()
