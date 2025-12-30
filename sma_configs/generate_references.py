#!/usr/bin/env python3
"""
Generate SMA-seq reference files for all experiments.

Outputs:
1. Full product references (PREFIX+ADAPTER+FLANK+BARCODE+FLANK+TARGET)
2. Target-only references (just CYP2D6 sequence)
3. Artifact references (daisy chain products for QC)
"""

import yaml
import os
from pathlib import Path

# =============================================================================
# LIBRARY ELEMENTS
# =============================================================================
PREFIX = "CCTGTACTTCGTT"      # 13bp
ADAPTER = "CAGTTACGTATTGCT"   # 15bp
FLANK_F = "AAGGTTAA"          # 8bp
FLANK_R = "CAGCACCT"          # 8bp

# =============================================================================
# CUSTOM BARCODES
# =============================================================================
# Forward barcodes (ligate to 5' end of target)
FORWARD_BARCODES = {
    'NB01': {'seq': 'CACAAAGACACCGACAACTTTCTT', 'overhang': 'TTCG', 'target': 'V0-4.1', 'len': 24},
    'NB02': {'seq': 'ACAGACGACTACAAACGGAATCGA', 'overhang': 'AGGA', 'target': 'V0-4.2', 'len': 24},
    'NB03': {'seq': 'CCTGGTAACTGGGACACAAGACTC', 'overhang': 'AGAG', 'target': 'V0-4.3', 'len': 24},
    'NB04': {'seq': 'TAGCAAACACGATAGAATCCGAA', 'overhang': 'TGGT', 'target': 'V0-4.4', 'len': 23},
    'NB05': {'seq': 'GGTTACACAAACCCTGGACAAGC', 'overhang': 'CTGA', 'target': 'V0-39', 'len': 23},
}

# Reverse barcodes (ligate to 3' end of target, captures RC strand)
REVERSE_BARCODES = {
    'NB06': {'seq': 'GACTACTTTCTGCCTTTGCGAGAA', 'overhang': 'TCCT', 'target': 'V0-4.2', 'len': 24},
    'NB07': {'seq': 'GGATTCATTCCCACGGTAACAC', 'overhang': 'CTCT', 'target': 'V0-4.2', 'len': 22},
    'NB08': {'seq': 'ACGTAACTTGGTTTGTTCCCTGAA', 'overhang': 'ACCA', 'target': 'V0-4.4', 'len': 24},
    'NB09': {'seq': 'AACCAAGACTCGCTGTGCCTAGTT', 'overhang': 'TCAG', 'target': 'V0-4.4', 'len': 24},
    'NB10': {'seq': 'GAGAGGACAAAGGTTTCAACGCTT', 'overhang': 'TTTG', 'target': 'unknown', 'len': 24},
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def reverse_complement(seq):
    """Return reverse complement of DNA sequence."""
    comp = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G',
            'a': 't', 't': 'a', 'g': 'c', 'c': 'g', 'N': 'N', 'n': 'n'}
    return ''.join(comp.get(b, b) for b in reversed(seq))

def get_core_sequence(seq):
    """Extract uppercase (CYP2D6) portion from sequence with lowercase flanks."""
    if seq is None:
        return None
    return ''.join(c for c in seq if c.isupper())

def build_full_product(barcode_seq, target_seq):
    """Build full sequencable product."""
    return PREFIX + ADAPTER + FLANK_F + barcode_seq + FLANK_R + target_seq

def write_fasta(filepath, sequences):
    """Write sequences to FASTA file."""
    with open(filepath, 'w') as f:
        for name, seq in sequences.items():
            f.write(f">{name}\n{seq}\n")
    print(f"  Written: {filepath} ({len(sequences)} sequences)")

# =============================================================================
# MAIN GENERATOR
# =============================================================================

def load_targets(targets_file):
    """Load target sequences from YAML file."""
    with open(targets_file, 'r') as f:
        data = yaml.safe_load(f)

    targets = {}
    for target_id, info in data.get('targets', {}).items():
        seq = info.get('designed_sequence') or info.get('sequence')
        if seq:
            targets[target_id] = {
                'full': seq,
                'core': get_core_sequence(seq),
                'positions': info.get('cyp2d6_positions', ''),
                'length': info.get('expected_length', len(seq) if seq else 0)
            }
    return targets

def generate_experiment_references(exp_id, exp_type, targets, output_dir):
    """Generate all reference files for an experiment."""

    os.makedirs(output_dir, exist_ok=True)

    full_refs = {}
    target_refs = {}
    artifact_refs = {}

    print(f"\n{'='*60}")
    print(f"Experiment: {exp_id}")
    print(f"Type: {exp_type}")
    print(f"{'='*60}")

    if exp_type == 'standard_ont':
        # Standard ONT barcoding - just need target sequences
        target_list = ['V0-4.1', 'V0-4.2', 'V0-4.3', 'V0-4.4',
                       'V0-39', 'V0-40', 'V0-41', 'V0-42', 'V0-43',
                       'V0-44', 'V0-45', 'V0-46', 'V0-47',
                       'V0-4.14', 'V0-4.15', 'V0-4.16', 'V0-4.17']

        for tid in target_list:
            if tid in targets and targets[tid]['core']:
                target_refs[f"{tid}"] = targets[tid]['core']

    elif exp_type == 'single_barcode':
        # Custom single-end barcoding (Dec 8, Dec 18 Ex1)
        for bc_name, bc_info in FORWARD_BARCODES.items():
            tid = bc_info['target']
            if tid in targets and targets[tid]['core']:
                core_seq = targets[tid]['core']

                # Full product
                full_seq = build_full_product(bc_info['seq'], core_seq)
                full_refs[f"{bc_name}_{tid}_forward"] = full_seq

                # Target only
                target_refs[f"{tid}"] = core_seq

    elif exp_type == 'double_barcode':
        # Double-end barcoding (Dec 18 Ex2/Ex3, Dec 23, Dec 28)

        # Forward products
        for bc_name, bc_info in FORWARD_BARCODES.items():
            tid = bc_info['target']
            if tid in targets and targets[tid]['core']:
                core_seq = targets[tid]['core']
                full_seq = build_full_product(bc_info['seq'], core_seq)
                full_refs[f"{bc_name}_{tid}_forward"] = full_seq
                target_refs[f"{tid}_forward"] = core_seq

        # Reverse products
        for bc_name, bc_info in REVERSE_BARCODES.items():
            tid = bc_info['target']
            if tid != 'unknown' and tid in targets and targets[tid]['core']:
                core_seq = targets[tid]['core']
                rc_seq = reverse_complement(core_seq)
                full_seq = build_full_product(bc_info['seq'], rc_seq)
                full_refs[f"{bc_name}_{tid}_reverse"] = full_seq
                target_refs[f"{tid}_reverse"] = rc_seq

        # Artifact sequences (daisy chains)
        # These occur when adjacent plasmid backbones ligate to targets
        artifact_refs["artifact_backbone_fragment"] = "NNNNNNNNNNNNNNNNNNNN"  # Placeholder

    elif exp_type == 'dec28_custom':
        # Dec 28 specific (only V0-4.2 and V0-4.4)
        dec28_barcodes = {
            'BC02': {'seq': 'ACAGACGACTACAAACGGAATCGA', 'target': 'V0-4.2', 'orient': 'forward'},
            'BC04': {'seq': 'TAGCAAACACGATAGAATCCGAA', 'target': 'V0-4.4', 'orient': 'reverse'},
            'BC07': {'seq': 'GGATTCATTCCCACGGTAACAC', 'target': 'V0-4.2', 'orient': 'reverse'},
            'BC09': {'seq': 'AACCAAGACTCGCTGTGCCTAGTT', 'target': 'V0-4.4', 'orient': 'forward'},
        }

        for bc_name, bc_info in dec28_barcodes.items():
            tid = bc_info['target']
            if tid in targets and targets[tid]['core']:
                core_seq = targets[tid]['core']
                if bc_info['orient'] == 'reverse':
                    core_seq = reverse_complement(core_seq)

                full_seq = build_full_product(bc_info['seq'], core_seq)
                full_refs[f"{bc_name}_{tid}_{bc_info['orient']}"] = full_seq
                target_refs[f"{tid}_{bc_info['orient']}"] = core_seq

    # Write output files
    if full_refs:
        write_fasta(os.path.join(output_dir, 'reference_full.fa'), full_refs)
    if target_refs:
        write_fasta(os.path.join(output_dir, 'reference_targets.fa'), target_refs)
    if artifact_refs:
        write_fasta(os.path.join(output_dir, 'reference_artifacts.fa'), artifact_refs)

    # Also write combined reference.fa (full products)
    combined = {**full_refs} if full_refs else {**target_refs}
    write_fasta(os.path.join(output_dir, 'reference.fa'), combined)

    return len(full_refs), len(target_refs)

# =============================================================================
# EXPERIMENT CONFIGURATIONS
# =============================================================================

EXPERIMENTS = {
    # Nov 24: Standard ONT barcoding
    '11242025_IF_Part4_SMA_seq': 'standard_ont',
    '11242025_IF_Part4_CIP_Treated_SMA_seq': 'standard_ont',

    # Dec 8: Custom single-end barcoding
    '12082025_IF_NewBCPart4_SMA_seq': 'single_barcode',

    # Dec 18: Mixed (Ex1=single, Ex2/Ex3=double)
    '12182025_IF_NewBCPart4_Ex1_SMA_seq': 'single_barcode',
    '12182025_IF_NewBCPart4_Ex2_SMA_seq': 'double_barcode',
    '12182025_IF_NewBCPart4_Ex3_SMA_seq': 'double_barcode',

    # Dec 23: Double barcode
    '12232025_IF_DoubleBC_SMA_seq': 'double_barcode',

    # Dec 28: Custom double barcode (V0-4.2 and V0-4.4 only)
    '12282025_IF_DoubleBC_SMA_seq': 'dec28_custom',
    '12282025_IF_DoubleBC_SMA_seq_no_trim': 'dec28_custom',
}

def main():
    script_dir = Path(__file__).parent
    targets_file = script_dir / 'targets' / 'sma_targets.yaml'
    experiments_dir = script_dir / 'experiments'

    print("Loading target sequences...")
    targets = load_targets(targets_file)
    print(f"Loaded {len(targets)} targets")

    total_full = 0
    total_target = 0

    for exp_id, exp_type in EXPERIMENTS.items():
        output_dir = experiments_dir / exp_id
        n_full, n_target = generate_experiment_references(exp_id, exp_type, targets, output_dir)
        total_full += n_full
        total_target += n_target

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Experiments processed: {len(EXPERIMENTS)}")
    print(f"Full product references: {total_full}")
    print(f"Target-only references: {total_target}")

if __name__ == '__main__':
    main()
