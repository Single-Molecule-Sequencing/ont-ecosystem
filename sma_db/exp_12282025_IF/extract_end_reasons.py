#!/usr/bin/env python3
"""
Extract end reasons from POD5 files and match to tagged BAM reads.

End reasons indicate why a read ended:
  - signal_positive: Normal end (pore cleared naturally)
  - unblock_mux_change: Mux scan triggered ejection
  - data_service_unblock_mux_change: Adaptive sampling rejection
  - unknown: Unknown reason
"""

import sys
from pathlib import Path
from collections import defaultdict
import json

try:
    import pod5
except ImportError:
    sys.exit("ERROR: pod5 required - pip install pod5")

try:
    import pysam
except ImportError:
    sys.exit("ERROR: pysam required - pip install pysam")


def get_read_ids_from_bam(bam_dir):
    """Get all read IDs from tagged BAM files."""
    read_ids = set()
    bam_to_reads = {}

    for bam_file in Path(bam_dir).glob('*_tagged.bam'):
        bc = bam_file.stem.replace('_tagged', '')
        bam_to_reads[bc] = []

        with pysam.AlignmentFile(str(bam_file), 'rb', check_sq=False) as bam:
            for read in bam:
                read_id = read.query_name
                read_ids.add(read_id)
                bam_to_reads[bc].append(read_id)

    return read_ids, bam_to_reads


def extract_end_reasons_from_pod5(pod5_dir, read_ids):
    """Extract end reasons for specified read IDs from POD5 files."""
    end_reasons = {}

    pod5_files = list(Path(pod5_dir).glob('**/*.pod5'))
    print(f"Found {len(pod5_files)} POD5 files")

    for i, pod5_file in enumerate(pod5_files):
        if i % 5 == 0:
            print(f"  Processing {i+1}/{len(pod5_files)}: {pod5_file.name}...")

        try:
            with pod5.Reader(pod5_file) as reader:
                for read in reader.reads():
                    read_id = str(read.read_id)
                    if read_id in read_ids:
                        # Get end reason from read
                        end_reason = read.end_reason.name if read.end_reason else 'unknown'
                        end_reasons[read_id] = end_reason
        except Exception as e:
            print(f"  Warning: Error reading {pod5_file.name}: {e}")
            continue

    return end_reasons


def main():
    pod5_dir = Path('/data1/12282025_IF_DoubleBC_SMA_seq_no_trim/no_sample_id')
    bam_dir = Path('tagged_reads')
    output_file = Path('end_reasons.json')

    print("=" * 60)
    print("End Reason Extraction")
    print("=" * 60)

    # Get read IDs from BAM files
    print("\nGetting read IDs from tagged BAM files...")
    read_ids, bam_to_reads = get_read_ids_from_bam(bam_dir)
    print(f"  Total reads to look up: {len(read_ids)}")
    for bc, reads in sorted(bam_to_reads.items()):
        print(f"    {bc}: {len(reads)} reads")

    # Extract end reasons from POD5 files
    print(f"\nExtracting end reasons from POD5 files in {pod5_dir}...")
    end_reasons = extract_end_reasons_from_pod5(pod5_dir, read_ids)
    print(f"\n  Found end reasons for {len(end_reasons)}/{len(read_ids)} reads")

    # Count end reasons
    reason_counts = defaultdict(int)
    for reason in end_reasons.values():
        reason_counts[reason] += 1

    print("\n  End reason distribution:")
    for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
        pct = 100 * count / len(end_reasons) if end_reasons else 0
        print(f"    {reason}: {count} ({pct:.1f}%)")

    # Save to JSON
    output_data = {
        'end_reasons': end_reasons,
        'summary': {
            'total_reads': len(read_ids),
            'reads_with_end_reason': len(end_reasons),
            'reason_counts': dict(reason_counts)
        }
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\n  Saved to: {output_file}")

    # Per-barcode breakdown
    print("\n" + "=" * 60)
    print("Per-barcode end reason breakdown:")
    print("=" * 60)

    for bc, reads in sorted(bam_to_reads.items()):
        bc_reasons = defaultdict(int)
        for read_id in reads:
            reason = end_reasons.get(read_id, 'not_found')
            bc_reasons[reason] += 1

        print(f"\n{bc} ({len(reads)} reads):")
        for reason, count in sorted(bc_reasons.items(), key=lambda x: -x[1]):
            pct = 100 * count / len(reads)
            print(f"  {reason}: {count} ({pct:.1f}%)")


if __name__ == '__main__':
    main()
