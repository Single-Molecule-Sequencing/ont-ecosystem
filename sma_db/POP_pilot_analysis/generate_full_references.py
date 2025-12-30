#!/usr/bin/env python3
"""
Generate full Level 0 plasmid reference sequences for POP targets V0-15 to V0-23.

The POP experiment reads are ~2800bp because they contain full Level 0 plasmids:
- Backbone (2299bp) + Target insert (~100bp) + BsaI overhangs (8bp) ≈ 2400bp

The extra ~400bp observed in actual reads likely comes from:
- Native barcoding adapters (SQK-NBD114-24 kit)
- Library prep additions

Structure of Level 0 plasmid:
    5'- [BsaI overhang (4nt)] - [TARGET INSERT] - [BsaI overhang (4nt)] - [BACKBONE] -3'

For circular plasmid linearized by native barcoding adapter ligation:
    [ADAPTER] - [BARCODE] - [OVERHANG] - [TARGET] - [OVERHANG] - [BACKBONE] - [OVERHANG connects back]
"""

import json
from pathlib import Path

# Level 0 backbone sequence (2299bp) - from all_products_reference.fa
# This is the same backbone used for all Level 0 constructs
BACKBONE = """GCTTGAATTCGAGCTCGGTACCCGGGGATCCTCTAGAGTCGACCTGCAGGCATGCAAGCTTGGCGTAATCATGGTCATAG
CTGTTTCCTGTGTGAAATTGTTATCCGCTCACAATTCCACACAACATACGAGCCGGAAGCATAAAGTGTAAAGCCTGGGG
TGCCTAATGAGTGAGCTAACTCACATTAATTGCGTTGCGCTCACTGCCCGCTTTCCAGTCGGGAAACCTGTCGTGCCAGC
TGCATTAATGAATCGGCCAACGCGCGGGGAGAGGCGGTTTGCGTATTGGGCGCTCTTCCGCTTCCTCGCTCACTGACTCG
CTGCGCTCGGTCGTTCGGCTGCGGCGAGCGGTATCAGCTCACTCAAAGGCGGTAATACGGTTATCCACAGAATCAGGGGA
TAACGCAGGAAAGAACATGTGAGCAAAAGGCCAGCAAAAGGCCAGGAACCGTAAAAAGGCCGCGTTGCTGGCGTTTTTCC
ATAGGCTCCGCCCCCCTGACGAGCATCACAAAAATCGACGCTCAAGTCAGAGGTGGCGAAACCCGACAGGACTATAAAGA
TACCAGGCGTTTCCCCCTGGAAGCTCCCTCGTGCGCTCTCCTGTTCCGACCCTGCCGCTTACCGGATACCTGTCCGCCTT
TCTCCCTTCGGGAAGCGTGGCGCTTTCTCATAGCTCACGCTGTAGGTATCTCAGTTCGGTGTAGGTCGTTCGCTCCAAGC
TGGGCTGTGTGCACGAACCCCCCGTTCAGCCCGACCGCTGCGCCTTATCCGGTAACTATCGTCTTGAGTCCAACCCGGTA
AGACACGACTTATCGCCACTGGCAGCAGCCACTGGTAACAGGATTAGCAGAGCGAGGTATGTAGGCGGTGCTACAGAGTT
CTTGAAGTGGTGGCCTAACTACGGCTACACTAGAAGAACAGTATTTGGTATCTGCGCTCTGCTGAAGCCAGTTACCTTCG
GAAAAAGAGTTGGTAGCTCTTGATCCGGCAAACAAACCACCGCTGGTAGCGGTGGTTTTTTTGTTTGCAAGCAGCAGATT
ACGCGCAGAAAAAAAGGATCTCAAGAAGATCCTTTGATCTTTTCTACGGGGTCTGACGCTCAGTGGAACGAAAACTCACG
TTAAGGGATTTTGGTCATGAGATTATCAAAAAGGATCTTCACCTAGATCCTTTTAAATTAAAAATGAAGTTTTAAATCAA
TCTAAAGTATATATGAGTAAACTTGGTCTGACAGTTACCAATGCTTAATCAGTGAGGCACCTATCTCAGCGATCTGTCTA
TTTCGTTCATCCATAGTTGCCTGACTCCCCGTCGTGTAGATAACTACGATACGGGAGGGCTTACCATCTGGCCCCAGTGC
TGCAATGATACCGCGAGACCCACGCTCACCGGCTCCAGATTTATCAGCAATAAACCAGCCAGCCGGAAGGGCCGAGCGCA
GAAGTGGTCCTGCAACTTTATCCGCCTCCATCCAGTCTATTAATTGTTGCCGGGAAGCTAGAGTAAGTAGTTCGCCAGTT
AATAGTTTGCGCAACGTTGTTGCCATTGCTACAGGCATCGTGGTGTCACGCTCGTCGTTTGGTATGGCTTCATTCAGCTC
CGGTTCCCAACGATCAAGGCGAGTTACATGATCCCCCATGTTGTGCAAAAAAGCGGTTAGCTCCTTCGGTCCTCCGATCG
TTGTCAGAAGTAAGTTGGCCGCAGTGTTATCACTCATGGTTATGGCAGCACTGCATAATTCTCTTACTGTCATGCCATCC
GTAAGATGCTTTTCTGTGACTGGTGAGTACTCAACCAAGTCATTCTGAGAATAGTGTATGCGGCGACCGAGTTGCTCTTG
CCCGGCGTCAATACGGGATAATACCGCGCCACATAGCAGAACTTTAAAAGTGCTCATCATTGGAAAACGTTCTTCGGGGC
GAAAACTCTCAAGGATCTTACCGCTGTTGAGATCCAGTTCGATGTAACCCACTCGTGCACCCAACTGATCTTCAGCATCT
TTTACTTTCACCAGCGTTTCTGGGTGAGCAAAAACAGGAAGGCAAAATGCCGCAAAAAAGGGAATAAGGGCGACACGGAA
ATGTTGAATACTCATACTCTTCCTTTTTCAATATTATTGAAGCATTTATCAGGGTTATTGTCTCATGAGCGGATACATAT
TTGAATGTATTTAGAAAAATAAACAAATAGGGGTTCCGCGCACATTTCCCCGAAAAGTGCCACCTGACGTCTAAGAAACC
ATTATTATCATGACATTAACCTATAAAAATAGGCGTATCACGAGGCCCTTTCGTCGGAG""".replace('\n', '')

# Target insert sequences for V0-15 to V0-23
# From sma_targets.yaml and size_sequence_mapping.yaml
TARGETS = {
    'V0-15': {
        'sequence': 'GTCTAAAGAAAAAAAAAATAAAGCAACATATCCTGAACAAAGGATCCTCCATAACGTTCCCACCAGATTTCTAATCAGAAACATGGAGGCCAGAAAGCA',
        'length': 99,
        'cyp2d6_position': '3909-4007'
    },
    'V0-16': {
        'sequence': 'AGCAGTGGAGGAGGACGACCCTCAGGCAGCCCGGGAGGATGTTGTCACAGGCTGGGGCAAGGGCCTTCCGGCTACCAACTGGGAGCTCTGGGAACAGCCCTGTTGCAAACAA',
        'length': 112,
        'cyp2d6_position': '4004-4115'
    },
    'V0-17': {
        'sequence': 'ACAAGAAGCCATAGCCCGGCCAGAGCCCAGGAATGTGGGCTGGGCTGGGAGCAGCCTCTGGACAGGAGTGGTCCCATCCAGGAAACCTCC',
        'length': 90,
        'cyp2d6_position': '4112-4201'
    },
    'V0-18': {
        'sequence': 'CTCCGGCATGGCTGGGAAGTGGGGTACTTGGTGCCGGGTCTGTATGTGTGTGTGACTGGTGTGTGTGAGAGAGAATGTGTGCCCTAAGTGTCAGTGTGAGTCTGTGTATGTGTGA',
        'length': 115,
        'cyp2d6_position': '4198-4312'
    },
    'V0-19': {
        'sequence': 'GTGAATATTGTCTTTGTGTGGGTGATTTTCTGCGTGTGTAATCGTGTCCCTGCAAGTGTGAACAAGTGGACAAGTGTCTGGGAGTGGACAAGAGATCTGTGCACCATCAGGTGTG',
        'length': 115,
        'cyp2d6_position': '4309-4423'
    },
    'V0-20': {
        'sequence': 'TGTGTGCATAGCGTCTGTGCATGTCAAGAGTGCAAGGTGAAGTGAAGGGACCAGGCCCATGATGCCACTCATCATCAGGAGCTCTAAG',
        'length': 88,
        'cyp2d6_position': '4420-4507'
    },
    'V0-21': {
        'sequence': 'TAAGGCCCCAGGTAAGTGCCAGTGACAGATAAGGGTGCTGAAGGTCACTCTGGAGTGGGCAGGTGGGGGTAGGGAAAGGGCAAGGCCATGTTCTGGAGGAGGGGTT',
        'length': 106,
        'cyp2d6_position': '4504-4609'
    },
    'V0-22': {
        'sequence': 'GGTTGTGACTACATTAGGGTGTATGAGCCTAGCTGGGAGGTGGATGGCCGGGTCCACTGAAACCCTGGTTATCCCAGAAGGCTTTGCAGGCTTCAGGAGC',
        'length': 100,
        'cyp2d6_position': '4606-4705'
    },
    'V0-23': {
        'sequence': 'GAGCTTGGAGTGGGGAGAGGGGGTGACTTCTCCGACCAGGCCCCTCCACCGGCCTACCCTGGGTAAGGGCCTGGAGCAGGAAGCAGGGGCAAGAACCTCTG',
        'length': 101,
        'cyp2d6_position': '4702-4802'
    }
}

# BsaI creates 4-nt 5' overhangs
# For POP targets, we need to determine the overhangs used
# Since these are different targets than V0-4.X, they may use different overhangs
# We'll use generic overhangs for now (GGAG...GCTT pattern similar to V0-4.X)

# Standard Level 0 overhang scheme
# The backbone ends with GGAG and expects insert to start with GGAG
# The insert ends with a complementary overhang that matches backbone start

def construct_full_plasmid(target_id, target_seq, overhang_5p='GGAG', overhang_3p='GCTT'):
    """
    Construct full Level 0 plasmid sequence.

    Structure (linearized at BsaI site):
    [5' overhang] + [TARGET] + [3' overhang] + [BACKBONE]

    This represents the sequence as it would be read from the native adapter.
    """
    # Full sequence: overhang + target + overhang + backbone
    full_seq = overhang_5p + target_seq + overhang_3p + BACKBONE
    return full_seq

def main():
    output_dir = Path(__file__).parent

    # Generate full plasmid FASTA
    fasta_content = f"""# Full Level 0 Plasmid References for POP Targets (V0-15 to V0-23)
# Generated for Q-score analysis of 081920205_IF_Pilot_SMA_seq
#
# Structure: [5' BsaI overhang (4nt)] + [TARGET INSERT] + [3' BsaI overhang (4nt)] + [BACKBONE (2299bp)]
# Total length per plasmid: ~2400-2410 bp
#
# Note: Actual reads may be longer (~2800bp) due to:
# - Native barcoding kit adapters (SQK-NBD114-24)
# - Additional library prep sequences

"""

    stats = {}

    for target_id, info in TARGETS.items():
        target_seq = info['sequence']
        full_seq = construct_full_plasmid(target_id, target_seq)

        # Add to FASTA
        fasta_content += f">{target_id}_full_plasmid  Level 0 plasmid with {target_id} insert ({len(full_seq)}bp)\n"
        # Wrap sequence at 80 characters
        for i in range(0, len(full_seq), 80):
            fasta_content += full_seq[i:i+80] + "\n"

        stats[target_id] = {
            'target_length': info['length'],
            'full_plasmid_length': len(full_seq),
            'backbone_length': len(BACKBONE),
            'cyp2d6_position': info['cyp2d6_position']
        }

    # Add backbone-only reference
    fasta_content += f">backbone_only  Level 0 plasmid backbone ({len(BACKBONE)}bp)\n"
    for i in range(0, len(BACKBONE), 80):
        fasta_content += BACKBONE[i:i+80] + "\n"

    # Write FASTA
    fasta_file = output_dir / 'full_plasmid_references.fa'
    with open(fasta_file, 'w') as f:
        f.write(fasta_content)
    print(f"Wrote: {fasta_file}")

    # Write stats
    stats_file = output_dir / 'full_plasmid_stats.json'
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"Wrote: {stats_file}")

    # Print summary
    print("\n=== Full Plasmid Reference Summary ===")
    print(f"Backbone length: {len(BACKBONE)} bp")
    print(f"\nTarget plasmids:")
    for target_id, info in stats.items():
        print(f"  {target_id}: {info['full_plasmid_length']} bp (insert: {info['target_length']} bp)")

    print(f"\n=== Length Analysis ===")
    print(f"Expected plasmid length range: {min(s['full_plasmid_length'] for s in stats.values())}-{max(s['full_plasmid_length'] for s in stats.values())} bp")
    print(f"Observed read length (from analysis): ~2600-3400 bp")
    print(f"Difference (~200-1000 bp) likely due to:")
    print(f"  - Native barcoding adapters (~60-100 bp per end)")
    print(f"  - Barcode sequences (~24 bp per end)")
    print(f"  - Motor protein sequence and other kit additions")

    return stats

if __name__ == '__main__':
    main()
