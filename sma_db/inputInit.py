#!/usr/bin/env python3
"""
inputInit.py - Input Standardization Script

Standardizes input file paths, creates symlinks, and extracts metadata
from input filenames for the SMA pipeline.

Usage:
    python inputInit.py --bam <path> --pod5 <path> --ref <path> [--exp-id <id>]

Creates:
    Input/
        {exp_id}.bam -> source BAM
        {exp_id}_pod5/ -> source POD5 directory
        {exp_id}.fa -> source reference FASTA
"""

import argparse
import json
import re
from pathlib import Path


def parse_bam_filename(bam_path: Path) -> dict:
    """
    Parse BAM filename to extract metadata.

    Expected naming convention:
        {exp_id}_{bc_model_type}_v{bc_model_version}_{trim}_{modifications}.bam

    Or for raw files:
        FBD69411_pass_V04_2_2_34fa833d_5920c4dc_0.bam

    Returns dict with extracted metadata.
    """
    metadata = {
        'exp_id': None,
        'model_tier': None,
        'model_ver': None,
        'trim': None,
        'mod_bitflag': 0,
        'original_filename': bam_path.name
    }

    stem = bam_path.stem

    # Try standard naming convention first
    # Pattern: {exp_id}_{tier}_v{version}_{trim}_{mods}
    standard_pattern = r'^(.+?)_([shf])_v([\d.]+)_(\d)_(.+)$'
    match = re.match(standard_pattern, stem)

    if match:
        metadata['exp_id'] = match.group(1)
        metadata['model_tier'] = match.group(2)
        metadata['model_ver'] = match.group(3)
        metadata['trim'] = int(match.group(4))
        mods_str = match.group(5)
        metadata['mod_bitflag'] = parse_modifications(mods_str)
    else:
        # For raw MinKNOW output, extract what we can
        # Pattern: FBD69411_pass_V04_2_2_34fa833d_5920c4dc_0
        parts = stem.split('_')
        if len(parts) >= 3:
            metadata['exp_id'] = parts[0]  # Flow cell ID

    return metadata


def parse_modifications(mods_str: str) -> int:
    """Convert modification string to bitflag integer."""

    MOD_BITS = {
        'non': 0,
        '6mA': 1,
        '5mCG_5hmCG': 2,
        '5mC_5hmC': 4,
        '4mC_5mC': 8,
        '5mC': 16,
    }

    if mods_str == 'non' or mods_str == '0':
        return 0

    bitflag = 0

    # Handle combined modifications (e.g., "6mA+5mCG_5hmCG")
    for mod in mods_str.split('+'):
        mod = mod.strip()
        if mod in MOD_BITS:
            bitflag |= MOD_BITS[mod]

    return bitflag


def create_symlinks(
    bam_path: Path,
    pod5_path: Path,
    ref_path: Path,
    exp_id: str,
    input_dir: Path
) -> dict:
    """Create standardized symlinks in Input directory."""

    input_dir.mkdir(parents=True, exist_ok=True)

    links = {}

    # BAM symlink
    bam_link = input_dir / f"{exp_id}.bam"
    if bam_link.exists() or bam_link.is_symlink():
        bam_link.unlink()
    bam_link.symlink_to(bam_path.resolve())
    links['bam'] = str(bam_link)

    # Also link BAM index if exists
    bai_path = bam_path.with_suffix('.bam.bai')
    if bai_path.exists():
        bai_link = input_dir / f"{exp_id}.bam.bai"
        if bai_link.exists() or bai_link.is_symlink():
            bai_link.unlink()
        bai_link.symlink_to(bai_path.resolve())
        links['bai'] = str(bai_link)

    # POD5 directory symlink
    pod5_link = input_dir / f"{exp_id}_pod5"
    if pod5_link.exists() or pod5_link.is_symlink():
        pod5_link.unlink()
    pod5_link.symlink_to(pod5_path.resolve())
    links['pod5'] = str(pod5_link)

    # Reference FASTA symlink
    ref_link = input_dir / f"{exp_id}.fa"
    if ref_link.exists() or ref_link.is_symlink():
        ref_link.unlink()
    ref_link.symlink_to(ref_path.resolve())
    links['ref'] = str(ref_link)

    return links


def main():
    parser = argparse.ArgumentParser(
        description="Standardize input files for SMA pipeline"
    )
    parser.add_argument(
        "--bam", "-b",
        type=Path,
        required=True,
        help="Path to input BAM file or directory containing BAM files"
    )
    parser.add_argument(
        "--pod5", "-p",
        type=Path,
        required=True,
        help="Path to POD5 directory"
    )
    parser.add_argument(
        "--ref", "-r",
        type=Path,
        required=True,
        help="Path to reference FASTA file"
    )
    parser.add_argument(
        "--exp-id", "-e",
        type=str,
        help="Experiment ID (auto-detected from BAM filename if not provided)"
    )
    parser.add_argument(
        "--input-dir", "-i",
        type=Path,
        default=Path("Input"),
        help="Input directory for symlinks (default: ./Input)"
    )
    parser.add_argument(
        "--output-json", "-o",
        type=Path,
        help="Output JSON file for metadata (optional)"
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.bam.exists():
        raise FileNotFoundError(f"BAM not found: {args.bam}")
    if not args.pod5.exists():
        raise FileNotFoundError(f"POD5 directory not found: {args.pod5}")
    if not args.ref.exists():
        raise FileNotFoundError(f"Reference FASTA not found: {args.ref}")

    # Handle BAM directory (merge multiple BAMs conceptually)
    if args.bam.is_dir():
        bam_files = list(args.bam.glob("*.bam"))
        if not bam_files:
            raise FileNotFoundError(f"No BAM files found in: {args.bam}")
        # Use first BAM for metadata, store directory for processing
        bam_path = bam_files[0]
        is_bam_dir = True
        bam_dir = args.bam
    else:
        bam_path = args.bam
        is_bam_dir = False
        bam_dir = None

    # Parse metadata from filename
    metadata = parse_bam_filename(bam_path)

    # Override exp_id if provided
    if args.exp_id:
        metadata['exp_id'] = args.exp_id

    if not metadata['exp_id']:
        # Generate from reference filename
        metadata['exp_id'] = args.ref.stem

    print(f"Experiment ID: {metadata['exp_id']}")
    print(f"Parsed metadata: {metadata}")

    # Create symlinks
    if is_bam_dir:
        # For directories, link the directory
        links = {}
        bam_link = args.input_dir / f"{metadata['exp_id']}_bam"
        args.input_dir.mkdir(parents=True, exist_ok=True)
        if bam_link.exists() or bam_link.is_symlink():
            bam_link.unlink()
        bam_link.symlink_to(bam_dir.resolve())
        links['bam_dir'] = str(bam_link)

        # POD5 and ref
        pod5_link = args.input_dir / f"{metadata['exp_id']}_pod5"
        if pod5_link.exists() or pod5_link.is_symlink():
            pod5_link.unlink()
        pod5_link.symlink_to(args.pod5.resolve())
        links['pod5'] = str(pod5_link)

        ref_link = args.input_dir / f"{metadata['exp_id']}.fa"
        if ref_link.exists() or ref_link.is_symlink():
            ref_link.unlink()
        ref_link.symlink_to(args.ref.resolve())
        links['ref'] = str(ref_link)
    else:
        links = create_symlinks(
            bam_path, args.pod5, args.ref,
            metadata['exp_id'], args.input_dir
        )

    metadata['links'] = links
    metadata['bam_is_dir'] = is_bam_dir
    if is_bam_dir:
        metadata['bam_file_count'] = len(bam_files)

    print(f"\nCreated symlinks in {args.input_dir}/:")
    for name, path in links.items():
        print(f"  {name}: {path}")

    # Save metadata
    if args.output_json:
        with open(args.output_json, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"\nMetadata saved to: {args.output_json}")

    # Also save default metadata file
    metadata_file = args.input_dir / f"{metadata['exp_id']}_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Metadata saved to: {metadata_file}")

    return metadata


if __name__ == "__main__":
    main()
