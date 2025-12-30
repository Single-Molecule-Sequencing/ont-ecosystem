#!/usr/bin/env python3
"""
SMA-seq Reference Builder

Generates reference sequences and configuration files for SMA-seq experiments.

Library Structure (all barcodes):
  5'- PREFIX + ADAPTER + FLANK_F + BARCODE + FLANK_R + TARGET -3'

Usage:
  python sma_seq_reference_builder.py --output-dir new_experiment/ --targets targets.yaml

Example targets.yaml:
  targets:
    CYP2D6_region1:
      forward_sequence: "AGGATTTGCATA..."
      forward_barcode: BC02
      reverse_barcode: BC07
      size_range: [200, 260]
    CYP2D6_region2:
      forward_sequence: "TGGTGTAGGTGC..."
      forward_barcode: BC09
      reverse_barcode: BC04
      size_range: [195, 255]
"""

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("ERROR: pyyaml required - pip install pyyaml")


# =============================================================================
# LIBRARY STRUCTURE CONSTANTS
# =============================================================================

LIBRARY_ELEMENTS = {
    'PREFIX': {
        'sequence': 'CCTGTACTTCGTT',
        'length': 13,
        'description': '13bp prefix before adapter'
    },
    'ADAPTER': {
        'sequence': 'CAGTTACGTATTGCT',
        'length': 15,
        'description': '15bp Native Adapter end sequence'
    },
    'FLANK_F': {
        'sequence': 'AAGGTTAA',
        'length': 8,
        'description': '8bp front flank (between adapter and barcode)'
    },
    'FLANK_R': {
        'sequence': 'CAGCACCT',
        'length': 8,
        'description': '8bp rear flank (between barcode and target)'
    },
}

# Standard SMA-seq barcode sequences
BARCODE_SEQUENCES = {
    'BC02': 'ACAGACGACTACAAACGGAATCGA',  # 24bp
    'BC04': 'TAGCAAACACGATAGAATCCGAA',   # 23bp
    'BC07': 'GGATTCATTCCCACGGTAACAC',    # 22bp
    'BC09': 'AACCAAGACTCGCTGTGCCTAGTT',  # 24bp
}


def reverse_complement(seq):
    """Return reverse complement of a DNA sequence."""
    comp = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G', 'N': 'N'}
    return ''.join(comp.get(b, b) for b in reversed(seq.upper()))


def build_reference(bc_seq, target_seq):
    """Build full reference sequence."""
    return (LIBRARY_ELEMENTS['PREFIX']['sequence'] +
            LIBRARY_ELEMENTS['ADAPTER']['sequence'] +
            LIBRARY_ELEMENTS['FLANK_F']['sequence'] +
            bc_seq +
            LIBRARY_ELEMENTS['FLANK_R']['sequence'] +
            target_seq)


def generate_config(targets, experiment_name="SMA-seq"):
    """Generate full configuration dictionary."""

    config = {
        'experiment': experiment_name,
        'library_structure': {
            'description': "5'- PREFIX + ADAPTER + FLANK_F + BARCODE + FLANK_R + TARGET -3'",
            'elements': LIBRARY_ELEMENTS,
        },
        'barcodes': {},
        'targets': {},
        'full_references': {},
    }

    for target_name, target_info in targets.items():
        fwd_seq = target_info['forward_sequence'].upper()
        rev_seq = reverse_complement(fwd_seq)
        fwd_bc = target_info['forward_barcode']
        rev_bc = target_info['reverse_barcode']
        size_range = target_info.get('size_range', [190, 270])

        # Add target sequences
        config['targets'][f'{target_name}_forward'] = {
            'description': f'{target_name} forward strand',
            'length': len(fwd_seq),
            'sequence': fwd_seq,
        }
        config['targets'][f'{target_name}_reverse'] = {
            'description': f'{target_name} reverse complement',
            'length': len(rev_seq),
            'sequence': rev_seq,
        }

        # Add barcode configs
        config['barcodes'][fwd_bc] = {
            'sequence': BARCODE_SEQUENCES[fwd_bc],
            'length': len(BARCODE_SEQUENCES[fwd_bc]),
            'target': f'{target_name}_forward',
            'target_description': f'{target_name} (forward orientation)',
            'size_range': size_range,
        }
        config['barcodes'][rev_bc] = {
            'sequence': BARCODE_SEQUENCES[rev_bc],
            'length': len(BARCODE_SEQUENCES[rev_bc]),
            'target': f'{target_name}_reverse',
            'target_description': f'RC({target_name}) (reverse complement)',
            'size_range': size_range,
        }

        # Build full references
        fwd_ref = build_reference(BARCODE_SEQUENCES[fwd_bc], fwd_seq)
        rev_ref = build_reference(BARCODE_SEQUENCES[rev_bc], rev_seq)

        config['full_references'][fwd_bc] = {
            'length': len(fwd_ref),
            'sequence': fwd_ref,
        }
        config['full_references'][rev_bc] = {
            'length': len(rev_ref),
            'sequence': rev_ref,
        }

    return config


def generate_reference_fasta(config):
    """Generate FASTA content for reference sequences."""
    lines = []
    for target_name, target_info in config['targets'].items():
        lines.append(f">{target_name}  {target_info['description']} ({target_info['length']}bp)")
        lines.append(target_info['sequence'])
    return '\n'.join(lines) + '\n'


def generate_dorado_toml(barcode_name, bc_seq):
    """Generate Dorado demux TOML content."""
    bc_len = len(bc_seq)
    bc_num = int(barcode_name[2:])

    # Mask patterns for Dorado
    mask_front = LIBRARY_ELEMENTS['ADAPTER']['sequence'][-6:] + LIBRARY_ELEMENTS['FLANK_F']['sequence']
    mask_rear = LIBRARY_ELEMENTS['FLANK_R']['sequence']

    return f'''[arrangement]
name = "SMA_{bc_len}bp"
kit = "SQK-NBD114-24"

mask1_front = "{mask_front}"
mask1_rear = "{mask_rear}"

barcode1_pattern = "SMA_{bc_len}bp_NB%02i"

first_index = {bc_num}
last_index = {bc_num + 2}

[scoring]
max_barcode_penalty = 11
min_barcode_penalty_dist = 3
min_separation_only_dist = 6
barcode_end_proximity = 75
flank_left_pad = 5
flank_right_pad = 10
front_barcode_window = 175
'''


def generate_barcode_fasta(barcode_name, bc_seq):
    """Generate barcode sequences FASTA for Dorado."""
    bc_len = len(bc_seq)
    bc_num = int(barcode_name[2:])

    lines = [f">SMA_{bc_len}bp_NB{bc_num:02d}", bc_seq]

    # Add dummy barcodes for adjacent indices (Dorado requirement)
    for i in range(bc_num + 1, bc_num + 3):
        dummy = 'AT' * (bc_len // 2) + ('A' if bc_len % 2 else '')
        lines.append(f">SMA_{bc_len}bp_NB{i:02d}")
        lines.append(dummy[:bc_len])

    return '\n'.join(lines) + '\n'


def print_reference_summary(config):
    """Print annotated reference assembly summary."""
    print("=" * 90)
    print("REFERENCE ASSEMBLY SUMMARY")
    print("=" * 90)
    print()
    print("Library Structure: PREFIX + ADAPTER + FLANK_F + BARCODE + FLANK_R + TARGET")
    print()

    for elem_name in ['PREFIX', 'ADAPTER', 'FLANK_F', 'FLANK_R']:
        elem = LIBRARY_ELEMENTS[elem_name]
        print(f"  {elem_name:8} = {elem['sequence']} ({elem['length']}bp)")
    print()

    for bc_name in sorted(config['barcodes'].keys()):
        bc = config['barcodes'][bc_name]
        ref = config['full_references'][bc_name]

        print("=" * 90)
        print(f"{bc_name}: {bc['target_description']}")
        print("=" * 90)
        print()
        print(f"  BARCODE = {bc['sequence']} ({bc['length']}bp)")
        print(f"  TARGET  = {bc['target']} ({config['targets'][bc['target']]['length']}bp)")
        print(f"  SIZE RANGE = {bc['size_range'][0]}-{bc['size_range'][1]}bp")
        print()
        print(f"  FULL REFERENCE ({ref['length']}bp):")

        # Print in 80-char lines
        seq = ref['sequence']
        for i in range(0, len(seq), 80):
            print(f"    {i:3}: {seq[i:i+80]}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='Generate SMA-seq reference sequences and configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Example targets.yaml:
  targets:
    CYP2D6_region1:
      forward_sequence: "AGGATTTGCATAGATGGGTTTGGG..."
      forward_barcode: BC02
      reverse_barcode: BC07
      size_range: [200, 260]
'''
    )
    parser.add_argument('--output-dir', '-o', required=True, help='Output directory')
    parser.add_argument('--targets', '-t', required=True, help='Targets YAML file')
    parser.add_argument('--name', '-n', default='SMA-seq', help='Experiment name')
    parser.add_argument('--print-only', action='store_true', help='Print summary only, no file output')
    args = parser.parse_args()

    # Load targets
    with open(args.targets) as f:
        targets_data = yaml.safe_load(f)

    targets = targets_data.get('targets', targets_data)

    # Generate config
    config = generate_config(targets, args.name)

    # Print summary
    print_reference_summary(config)

    if args.print_only:
        return

    # Create output directory
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    config_dir = out_dir / 'config'
    config_dir.mkdir(exist_ok=True)

    # Write main config
    config_file = out_dir / 'sma_seq_config.yaml'
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    print(f"Wrote: {config_file}")

    # Write reference FASTA
    ref_fasta = out_dir / 'reference.fa'
    with open(ref_fasta, 'w') as f:
        f.write(generate_reference_fasta(config))
    print(f"Wrote: {ref_fasta}")

    # Write Dorado configs per barcode length
    bc_by_length = {}
    for bc_name, bc_info in config['barcodes'].items():
        bc_len = bc_info['length']
        if bc_len not in bc_by_length:
            bc_by_length[bc_len] = []
        bc_by_length[bc_len].append((bc_name, bc_info['sequence']))

    for bc_len, barcodes in bc_by_length.items():
        for bc_name, bc_seq in barcodes:
            # TOML
            toml_file = config_dir / f'SMA_{bc_len}bp.toml'
            with open(toml_file, 'w') as f:
                f.write(generate_dorado_toml(bc_name, bc_seq))

            # Barcode sequences FASTA
            fasta_file = config_dir / f'SMA_{bc_len}bp_sequences.fasta'
            with open(fasta_file, 'w') as f:
                f.write(generate_barcode_fasta(bc_name, bc_seq))

    print(f"Wrote: {len(bc_by_length)} Dorado config sets to {config_dir}/")

    print()
    print("=" * 90)
    print("NEXT STEPS")
    print("=" * 90)
    print(f"1. Review generated files in {out_dir}/")
    print(f"2. Run demux: dorado demux --kit-name SMA_XXbp --barcode-arrangement config/SMA_XXbp.toml ...")
    print(f"3. Tag reads: python tag_demuxed_reads.py --config {config_file}")


if __name__ == '__main__':
    main()
