#!/usr/bin/env python3
"""
Update all SMA-seq experiment configs with consistent structure.

Adds:
- custom_barcode field to sample mappings (where applicable)
- overhang field to sample mappings
- orientation field
- barcodes_file reference
- Consolidate reference paths
"""
import yaml
import os
from pathlib import Path

# Custom barcode mappings for each experiment type
CUSTOM_BARCODES = {
    # Forward barcodes (NB01-NB05) - for experiments using custom barcodes
    'barcode01': {'custom_barcode': 'NB01', 'overhang': 'TTCG', 'orientation': 'forward'},
    'barcode02': {'custom_barcode': 'NB02', 'overhang': 'AGGA', 'orientation': 'forward'},
    'barcode03': {'custom_barcode': 'NB03', 'overhang': 'AGAG', 'orientation': 'forward'},
    'barcode04': {'custom_barcode': 'NB04', 'overhang': 'TGGT', 'orientation': 'forward'},
    'barcode05': {'custom_barcode': 'NB05', 'overhang': 'CTGA', 'orientation': 'forward'},
}

# Experiments that use custom barcodes
CUSTOM_BC_EXPERIMENTS = [
    '12082025_IF_NewBCPart4_SMA_seq',
    '12182025_IF_NewBCPart4_Ex1_SMA_seq',
    '12182025_IF_NewBCPart4_Ex2_SMA_seq',
    '12182025_IF_NewBCPart4_Ex3_SMA_seq',
]

def update_config(filepath: Path) -> bool:
    """Update a single config file."""
    with open(filepath) as f:
        config = yaml.safe_load(f)

    exp_id = config.get('experiment', {}).get('id', '')
    modified = False

    # Add barcodes_file reference if missing
    if 'reference' in config:
        if 'barcodes_file' not in config['reference']:
            config['reference']['barcodes_file'] = '../targets/sma_barcodes.yaml'
            modified = True

    # Update sample mappings for custom barcode experiments
    if exp_id in CUSTOM_BC_EXPERIMENTS and 'samples' in config:
        for bc_name, bc_data in config['samples'].items():
            if bc_name in CUSTOM_BARCODES:
                for key, value in CUSTOM_BARCODES[bc_name].items():
                    if key not in bc_data:
                        bc_data[key] = value
                        modified = True

    # Ensure reference paths use references/ subdirectory
    if 'reference' in config:
        ref = config['reference']
        for key in ['fasta', 'full_products', 'targets_only', 'artifacts']:
            if key in ref and isinstance(ref[key], str):
                if not ref[key].startswith('references/') and '/' in ref[key]:
                    # Extract just the filename
                    filename = ref[key].split('/')[-1]
                    ref[key] = f'references/{filename}'
                    modified = True

    if modified:
        with open(filepath, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return modified


def main():
    experiments_dir = Path(__file__).parent / 'experiments'

    updated = []
    for config_file in experiments_dir.glob('*.yaml'):
        if update_config(config_file):
            updated.append(config_file.name)
            print(f"  Updated: {config_file.name}")

    print(f"\nUpdated {len(updated)} config files")


if __name__ == '__main__':
    main()
