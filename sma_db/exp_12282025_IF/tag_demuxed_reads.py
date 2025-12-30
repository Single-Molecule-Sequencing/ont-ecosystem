#!/usr/bin/env python3
"""
Tag Dorado-demuxed SMA-seq reads with QC metrics.

Reads demuxed BAM files from Dorado output and adds:
  eq:f  - Mean Q-score (probability-space average)
  ed:i  - Edit distance to full reference sequence
  sz:Z  - Size status (in_range/short/long)

Configuration loaded from sma_seq_config.yaml

Usage:
  python tag_demuxed_reads.py --input-dir sample_demux --output-dir tagged_reads
"""

import argparse
import math
import os
import sys
from pathlib import Path
from collections import defaultdict

try:
    import yaml
except ImportError:
    sys.exit("ERROR: pyyaml required - pip install pyyaml")

try:
    import pysam
except ImportError:
    sys.exit("ERROR: pysam required - pip install pysam")

try:
    import edlib
except ImportError:
    sys.exit("ERROR: edlib required - pip install edlib")


def load_config(config_path='sma_seq_config.yaml'):
    """Load SMA-seq configuration from YAML file."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_library_elements(config):
    """Extract library structure elements from config."""
    lib = config['library_structure']['elements']
    return {
        'PREFIX': lib['PREFIX']['sequence'],
        'ADAPTER': lib['ADAPTER']['sequence'],
        'FLANK_F': lib['FLANK_F']['sequence'],
        'FLANK_R': lib['FLANK_R']['sequence'],
    }


def get_barcode_config(config):
    """Extract barcode configurations from config."""
    bc_config = {}
    for bc_name, bc_data in config['barcodes'].items():
        bc_config[bc_name] = {
            'bc_seq': bc_data['sequence'],
            'target': bc_data['target'],
            'size_range': tuple(bc_data['size_range']),
        }
    return bc_config


def get_target_sequences(config):
    """Extract target sequences from config."""
    return {name: data['sequence'] for name, data in config['targets'].items()}


# Map file patterns to barcode names
BARCODE_PATTERNS = {
    'barcode02': 'BC02', '24bp_barcode02': 'BC02',
    'barcode04': 'BC04', '23bp_barcode04': 'BC04',
    'barcode07': 'BC07', '22bp_barcode07': 'BC07',
    'barcode09': 'BC09', '24bp_barcode09': 'BC09',
}


def build_reference(lib_elements, bc_seq, target_seq):
    """Build full reference: 5'- PREFIX + ADAPTER + FLANK_F + BC + FLANK_R + TARGET -3'"""
    return (lib_elements['PREFIX'] +
            lib_elements['ADAPTER'] +
            lib_elements['FLANK_F'] +
            bc_seq +
            lib_elements['FLANK_R'] +
            target_seq)


def mean_qscore(quals):
    """Calculate mean Q-score in probability space (correct method)."""
    if not quals:
        return 0.0
    probs = [10 ** (-q / 10) for q in quals]
    mean_p = sum(probs) / len(probs)
    if mean_p <= 0:
        return 60.0
    if mean_p >= 1:
        return 0.0
    return -10 * math.log10(mean_p)


def calculate_edit_distance(seq, ref):
    """Calculate edit distance with proper handling for different lengths."""
    if not seq:
        return len(ref) if ref else 0

    rlen = len(seq)
    ref_len = len(ref)

    # Use appropriate alignment mode based on length ratio
    if rlen <= ref_len * 1.5:
        aln = edlib.align(seq, ref, mode='NW', task='path')
    else:
        aln = edlib.align(ref, seq, mode='HW', task='path')

    return min(aln['editDistance'], max(rlen, ref_len))


def get_barcode_from_filename(filename):
    """Extract barcode name from filename."""
    for pattern, bc in BARCODE_PATTERNS.items():
        if pattern in filename.lower():
            return bc
    return None


def main():
    parser = argparse.ArgumentParser(description='Tag demuxed SMA-seq reads')
    parser.add_argument('--input-dir', default='sample_demux', help='Dorado demux output directory')
    parser.add_argument('--output-dir', default='tagged_reads', help='Output directory')
    parser.add_argument('--config', default='sma_seq_config.yaml', help='Configuration YAML file')
    parser.add_argument('--sample', type=int, default=0, help='Sample N reads per barcode (0=all)')
    args = parser.parse_args()

    print("=" * 60)
    print("SMA-seq Read Tagger")
    print("=" * 60)

    # Load configuration
    print(f"\nLoading configuration from {args.config}...")
    config = load_config(args.config)
    lib_elements = get_library_elements(config)
    barcode_config = get_barcode_config(config)
    targets = get_target_sequences(config)

    print(f"  Library elements: PREFIX({len(lib_elements['PREFIX'])}bp) + "
          f"ADAPTER({len(lib_elements['ADAPTER'])}bp) + "
          f"FLANK_F({len(lib_elements['FLANK_F'])}bp) + BC + "
          f"FLANK_R({len(lib_elements['FLANK_R'])}bp) + TARGET")

    # Build full references for each barcode
    full_refs = {}
    for bc, cfg in barcode_config.items():
        target_name = cfg['target']
        if target_name not in targets:
            print(f"  WARNING: {target_name} not found in config")
            continue

        full_ref = build_reference(lib_elements, cfg['bc_seq'], targets[target_name])
        full_refs[bc] = full_ref
        print(f"  {bc}: {len(full_ref)}bp reference (target={target_name})")

    # Create output directory
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Find all demuxed BAM files
    input_dir = Path(args.input_dir)
    bam_files = list(input_dir.glob('**/*.bam'))
    bam_files = [f for f in bam_files if 'unclassified' not in f.name]

    print(f"\nFound {len(bam_files)} classified BAM files")

    # Process each BAM file
    all_stats = {}
    for bam_file in bam_files:
        bc = get_barcode_from_filename(bam_file.name)
        if not bc or bc not in full_refs:
            print(f"\nSkipping {bam_file.name} - unknown barcode")
            continue

        cfg = barcode_config[bc]
        ref_seq = full_refs[bc]
        min_sz, max_sz = cfg['size_range']

        print(f"\n{bc} ({bam_file.name}):")

        stats = {'n': 0, 'in_range': 0, 'short': 0, 'long': 0, 'eds': [], 'eqs': []}
        out_bam = str(out_dir / f"{bc}_tagged.bam")

        # Get header
        with pysam.AlignmentFile(str(bam_file), 'rb', check_sq=False) as inp:
            header = inp.header.to_dict()

        with pysam.AlignmentFile(str(bam_file), 'rb', check_sq=False) as inp:
            with pysam.AlignmentFile(out_bam, 'wb', header=header) as out:
                for read in inp:
                    if args.sample > 0 and stats['n'] >= args.sample:
                        break

                    seq = read.query_sequence
                    quals = read.query_qualities
                    rlen = len(seq) if seq else 0

                    # Mean Q-score
                    eq = mean_qscore(list(quals)) if quals else 0.0

                    # Size classification
                    if rlen < min_sz:
                        sz = 'short'
                        stats['short'] += 1
                    elif rlen > max_sz:
                        sz = 'long'
                        stats['long'] += 1
                    else:
                        sz = 'in_range'
                        stats['in_range'] += 1

                    # Edit distance to full reference
                    ed = calculate_edit_distance(seq, ref_seq) if seq else 0

                    # Set tags
                    read.set_tag('eq', round(eq, 2), 'f')
                    read.set_tag('ed', ed, 'i')
                    read.set_tag('sz', sz, 'Z')
                    read.set_tag('bc', bc, 'Z')

                    out.write(read)
                    stats['n'] += 1
                    stats['eds'].append(ed)
                    stats['eqs'].append(eq)

        # Sort and index
        sorted_bam = out_bam.replace('.bam', '_sorted.bam')
        pysam.sort('-o', sorted_bam, out_bam)
        os.rename(sorted_bam, out_bam)
        pysam.index(out_bam)

        # Print stats
        n = stats['n']
        print(f"  Reads: {n}")
        print(f"  Size: in_range={stats['in_range']} ({100*stats['in_range']/n:.1f}%), short={stats['short']}, long={stats['long']}")
        if stats['eds']:
            avg_ed = sum(stats['eds']) / len(stats['eds'])
            low_ed = sum(1 for e in stats['eds'] if e < 30)
            print(f"  Edit distance: mean={avg_ed:.1f}, <30bp={low_ed}/{n} ({100*low_ed/n:.1f}%)")
        if stats['eqs']:
            avg_eq = sum(stats['eqs']) / len(stats['eqs'])
            print(f"  Q-score: mean={avg_eq:.1f}")

        all_stats[bc] = stats

    print("\n" + "=" * 60)
    print("Output files:")
    for f in sorted(out_dir.glob('*.bam')):
        if not str(f).endswith('.bai'):
            size_kb = f.stat().st_size / 1024
            print(f"  {f.name}: {size_kb:.1f} KB")

    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    total_reads = sum(s['n'] for s in all_stats.values())
    for bc in ['BC02', 'BC04', 'BC07', 'BC09']:
        if bc in all_stats:
            s = all_stats[bc]
            pct_in_range = 100 * s['in_range'] / s['n'] if s['n'] > 0 else 0
            avg_ed = sum(s['eds']) / len(s['eds']) if s['eds'] else 0
            avg_eq = sum(s['eqs']) / len(s['eqs']) if s['eqs'] else 0
            print(f"  {bc}: {s['n']:5d} reads, {pct_in_range:5.1f}% in-range, ED={avg_ed:5.1f}, Q={avg_eq:4.1f}")
    print(f"  Total: {total_reads} reads")


if __name__ == '__main__':
    main()
