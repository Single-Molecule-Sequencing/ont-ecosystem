#!/usr/bin/env python3
"""
Generate reference FASTA files for all SMA-seq experiments.

Creates:
- reference.fa: Clean expected products
- reference_artifacts.fa: Daisy chain artifact sequences
- reference_targets.fa: Target sequences only

Based on expected_products.yaml and sma_targets.yaml
"""

import os
import yaml
from pathlib import Path

# Library structure constants
PREFIX = "CCTGTACTTCGTT"      # 13bp
ADAPTER = "CAGTTACGTATTGCT"   # 15bp
FLANK_F = "AAGGTTAA"          # 8bp
FLANK_R = "CAGCACCT"          # 8bp

# Barcode sequences
BARCODES = {
    "NB01": {"seq": "CACAAAGACACCGACAACTTTCTT", "overhang": "TTCG", "target": "V0-4.1"},
    "NB02": {"seq": "ACAGACGACTACAAACGGAATCGA", "overhang": "AGGA", "target": "V0-4.2"},
    "NB03": {"seq": "CCTGGTAACTGGGACACAAGACTC", "overhang": "AGAG", "target": "V0-4.3"},
    "NB04": {"seq": "TAGCAAACACGATAGAATCCGAA", "overhang": "TGGT", "target": "V0-4.4"},
    "NB05": {"seq": "GGTTACACAAACCCTGGACAAGC", "overhang": "CTGA", "target": "V0-39"},
    "NB06": {"seq": "GACTACTTTCTGCCTTTGCGAGAA", "overhang": "TCCT", "target": "V0-4.2"},
    "NB07": {"seq": "GGATTCATTCCCACGGTAACAC", "overhang": "CTCT", "target": "V0-4.2"},
    "NB08": {"seq": "ACGTAACTTGGTTTGTTCCCTGAA", "overhang": "ACCA", "target": "V0-4.4"},
    "NB09": {"seq": "AACCAAGACTCGCTGTGCCTAGTT", "overhang": "TCAG", "target": "V0-4.4"},
}

# Simulated backbone sequence (~2000bp) for daisy chain artifacts
# This is a placeholder - actual backbone would come from plasmid sequence
BACKBONE_SEQ = "N" * 2000  # Placeholder for backbone


def load_targets(targets_file):
    """Load target sequences from YAML file."""
    with open(targets_file) as f:
        data = yaml.safe_load(f)

    targets = {}
    for target_id, info in data.get('targets', {}).items():
        seq = info.get('designed_sequence') or info.get('sanger_sequence') or info.get('sequence')
        if seq:
            targets[target_id] = seq.upper()

    return targets


def build_clean_product(barcode_id, target_seq, overhang=""):
    """Build full clean product sequence."""
    bc = BARCODES.get(barcode_id, {})
    barcode_seq = bc.get('seq', '')

    return (
        PREFIX +
        ADAPTER +
        FLANK_F +
        barcode_seq +
        FLANK_R +
        overhang +
        target_seq
    )


def write_fasta(sequences, output_file):
    """Write sequences to FASTA file."""
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        for name, seq in sequences.items():
            f.write(f">{name}\n")
            # Write sequence in 80-char lines
            for i in range(0, len(seq), 80):
                f.write(seq[i:i+80] + "\n")

    print(f"  Written: {output_file} ({len(sequences)} sequences)")


def generate_experiment_references(exp_id, targets_used, targets, output_dir):
    """Generate reference files for a specific experiment."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    clean_products = {}
    target_only = {}
    artifacts = {}

    # Build clean products
    for barcode_id, target_id in targets_used.items():
        if target_id in targets:
            target_seq = targets[target_id]
            bc_info = BARCODES.get(barcode_id, {})
            overhang = bc_info.get('overhang', '')

            # Clean product
            product_name = f"{barcode_id}_{target_id}_clean"
            clean_products[product_name] = build_clean_product(barcode_id, target_seq, overhang)

            # Target only
            target_only[target_id] = target_seq

    # Build artifact sequences (daisy chains)
    target_list = list(targets_used.values())
    for i in range(len(target_list) - 1):
        t1, t2 = target_list[i], target_list[i+1]
        if t1 in targets and t2 in targets:
            artifact_name = f"daisy_chain_{t1}_{t2}"
            # Daisy chain: TARGET_A + BACKBONE + TARGET_B
            artifacts[artifact_name] = targets[t1] + BACKBONE_SEQ + targets[t2]

    # Write files
    write_fasta(clean_products, output_dir / "reference.fa")
    write_fasta(target_only, output_dir / "reference_targets.fa")
    if artifacts:
        write_fasta(artifacts, output_dir / "reference_artifacts.fa")


def main():
    """Generate references for all experiments."""

    base_dir = Path(__file__).parent
    targets_file = base_dir / "targets" / "sma_targets.yaml"

    print("Loading target sequences...")
    targets = load_targets(targets_file)
    print(f"  Loaded {len(targets)} targets")

    # Experiment configurations
    experiments = {
        "12282025_IF_DoubleBC_SMA_seq": {
            "NB02": "V0-4.2",
            "NB04": "V0-4.4",
            "NB07": "V0-4.2",
            "NB09": "V0-4.4",
        },
        "12232025_IF_DoubleBC_SMA_seq": {
            "NB01": "V0-4.1",
            "NB02": "V0-4.2",
            "NB03": "V0-4.3",
            "NB04": "V0-4.4",
            "NB05": "V0-39",
        },
        "11242025_IF_Part4_SMA_seq": {
            "NB01": "V0-4.1",
            "NB02": "V0-4.2",
            "NB03": "V0-4.3",
            "NB04": "V0-4.4",
            # Standard ONT barcodes for V0-39 through V0-47
        },
        "12082025_IF_NewBCPart4_SMA_seq": {
            "NB01": "V0-4.1",
            "NB02": "V0-4.2",
            "NB03": "V0-4.3",
            "NB04": "V0-4.4",
            "NB05": "V0-39",
        },
        "12182025_IF_NewBCPart4_Ex1_SMA_seq": {
            "NB01": "V0-4.1",
            "NB02": "V0-4.2",
            "NB03": "V0-4.3",
            "NB04": "V0-4.4",
            "NB05": "V0-39",
        },
        "12182025_IF_NewBCPart4_Ex2_SMA_seq": {
            "NB01": "V0-4.1",
            "NB02": "V0-4.2",
            "NB03": "V0-4.3",
            "NB04": "V0-4.4",
            "NB05": "V0-39",
        },
        "12182025_IF_NewBCPart4_Ex3_SMA_seq": {
            "NB01": "V0-4.1",
            "NB02": "V0-4.2",
            "NB03": "V0-4.3",
            "NB04": "V0-4.4",
            "NB05": "V0-39",
        },
    }

    print("\nGenerating reference files...")
    for exp_id, targets_used in experiments.items():
        print(f"\n{exp_id}:")
        output_dir = base_dir / "experiments" / exp_id / "references"
        generate_experiment_references(exp_id, targets_used, targets, output_dir)

    print("\n=== Reference generation complete ===")


if __name__ == "__main__":
    main()
