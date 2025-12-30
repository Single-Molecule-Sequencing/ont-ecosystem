#!/usr/bin/env python3
"""
SMA-seq Preparation Tool

Complete workflow for preparing and running SMA-seq experiments:
- Reference file creation
- Sample sheet generation
- Custom barcode configuration
- Size-based sequence classification
- Dorado integration
- Database metadata storage

Usage:
    python3 sma_prep.py wizard                    # Interactive setup
    python3 sma_prep.py target add --name V04 ... # Add target
    python3 sma_prep.py samplesheet --barcodes ...# Create sample sheet
    python3 sma_prep.py dorado --pod5-dir ...     # Run Dorado
"""

import argparse
import csv
import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# =============================================================================
# ONT BARCODE SEQUENCES (V14)
# =============================================================================
ONT_BARCODES = {
    1: "CACAAAGACACCGACAACTTTCTT", 2: "ACAGACGACTACAAACGGAATCGA",
    3: "CCTGGTAACTGGGACACAAGACTC", 4: "TAGGGAAACACGATAGAATCCGAA",
    5: "AAGGTTACACAAACCTCTGACTCT", 6: "AACTGGAGGACACTCAGGAACTTA",
    7: "ATCGCACTGACATCACCAACTTTT", 8: "AGAAGCTTCGCACAGAATGATTTA",
    9: "AACGCACACTCGAGAACTAGACTT", 10: "AGTTACCTCGTGAATGAACCTTCT",
    11: "ACTGCCTATCCTAAGGTATTTCCT", 12: "AGCCGATGACCAAGTTTATTTACT",
    13: "CCTTGGTCTCTGACTGTTTTCGTT", 14: "CTGAGATAGGACTCTGTCCAAATC",
    15: "CCAGATTGTCAATACTGGAACCGT", 16: "CTCCAAGTTTCGACCGTATACCTT",
    17: "GTTCATCGACTCGCGTAGATCCTT", 18: "GTGCTAGGGACACTTATTCCGATT",
    19: "GAAGCACCGAACTTCTCAATTCTC", 20: "GCGACTCTCTTAAGGATTCTGTAG",
    21: "GACCACCTATGAAACAGAACGAAT", 22: "GTAACTTGGACGACGCATCTCATT",
    23: "GTATGACACCATGAACTGTCTCAC", 24: "GAGGGTATAACACGGTTTATATTC",
    25: "TCAACAGCATCCCGTAAGAATAAG", 26: "TGACGACTATGCTATACTTCTCAC",
    27: "TACCGTGGATCACATAGTACTCTT", 28: "TCCAGGTTCACTTCAAAGAACTAG",
    29: "TGTTCTGACCATGTTAAGAATTGC", 30: "TGTATTCGACTGGTGATCAACTCT",
    31: "TAGATCCACTGAACGCATTTCATC", 32: "TCTCTACTCCACAGGAAGTTATAG",
    33: "TCTCAATCTGGACTACGTCAACTT", 34: "TAGAACTCGCTTTCACACGAATAC",
    35: "TCGGACATTTCTGATCGCACTTAC", 36: "TTGGAGGCTTCTCATATGCTTATC",
    37: "CGATACTGGAATGCAACTCTCACT", 38: "CCCAGTGATTGGACTCACTTTCAT",
    39: "CTGTAACACGTATTCGGACACTTT", 40: "CGACATCTCAAGAACCTTAGGACT",
    41: "CTTATGGTAACCTTCGGATCGTAT", 42: "CCGCATGATGATAGTAGGAGATGT",
    43: "CTTACGAAGAGTAACATGTGGACT", 44: "CTGCAAGTTCTGTGCACTCAGTTT",
    45: "CCGTCATCCACTTCATAGATAGGT", 46: "CAGTAGGTGTTCGTAATGCTCTTC",
    47: "CTTTCCTTCGAAGACTGATGTCTT", 48: "CCGCCATATAGATCGTACAGATCT",
    49: "AAGAAGTACCGTTCTTCCTGTAGA", 50: "AGTTAGAGTGAAACATCCGTGTCA",
    51: "ATGTGAATGAACCCTGAAGGTGAT", 52: "AAGCTCCTAGAAAGTGATGTGTAT",
    53: "ATCTGATCGGTATGTGAACACTCA", 54: "ACGGATCTACAAGATCCCTAACTC",
    55: "ACTTTGAGCATCTCTGTCAGTCAT", 56: "AGTGAGCTCGTTCAATGTGTACTT",
    57: "AAGATGTCGAACCGTACATGAGAT", 58: "ACAGTGGATCCGACAGTATAAGTT",
    59: "ATTCCCGTGAGATACTGTACAACT", 60: "AGGATACGTGACAGTATGAACCTT",
    61: "GAGATCCTAATCGTGAATCGATCT", 62: "GGCCGCATTCAACTTAACAAGTAT",
    63: "GATCACCGACCTAATCATACTGTT", 64: "GTATCTGCGGATAGACTCAGTACT",
    65: "GTCCGAACATGTCTCGTAGATCAT", 66: "GCAACTATAGTGACCTCTAACTGT",
    67: "GAGTCATATGAGCACCAATTCTAC", 68: "GACAGCGTTAGACTACTGTGAATT",
    69: "GCTCTTGTTCTCGAATTGATAGAC", 70: "GTAGTACCACGTTCATGACATCAC",
    71: "GTACACCTCGAGAGTATATCGTCA", 72: "GCATAAGATCTGGTTGGCTACTTT",
    73: "TTCGATAGATTCGTTAAGCCTCTG", 74: "TCCTGATGACCGAACTCTCAATTT",
    75: "TACAGTCGAAATCGCGTGTATACT", 76: "TCCGATAGGCTAATACCATTTCGA",
    77: "TGACGATCACTCCTTGAGATAGTT", 78: "TGAGTGAAGAGTTCCTACTTGTCT",
    79: "TTGGATGGACCACTGTGATAGTTA", 80: "TGAACTTAACGTCCGTGTATCTCT",
    81: "TCGATCGCTAGAGTTAGCTGACAT", 82: "TGATAAGACCTGACTGCTCTGTTA",
    83: "TCGCTCCGTTAGATAACGATGTCT", 84: "TAACTGAGCTCATCGTAATGGATC",
    85: "CGTTATATCTGTACGACGCTATGT", 86: "CCAGAGACATGTGTAAGATCGATG",
    87: "CGGTTGGTTATTCTCATGATCACA", 88: "CATATCGATCGAAGTGACTGTAGT",
    89: "CTCCACTATGGTACTGAATGTCTC", 90: "CATGAAGCCGTGATATGTCACTTT",
    91: "CAGTCTTGTAGGTATTCGTGGATT", 92: "CCAGCGATACTCCTATCGAATACA",
    93: "ATAGACTGTTCGTCGATCTCTTGA", 94: "ACTTGAACAATACGGATGTCATCT",
    95: "ATTCCTGACTATCGACATACTCAT", 96: "ACGGCTTCGATCGTAAGTAGTCAT",
}

# =============================================================================
# CLUSTER CONFIGURATIONS
# =============================================================================
CLUSTERS = {
    "armis2": {
        "partition": "sigbio-a40",
        "account": "bleu1",
        "gres": "gpu:a40:1",
        "cpus": 8,
        "mem": "64G",
        "time": "24:00:00",
        "dorado": "/nfs/turbo/umms-bleu-secure/programs/dorado-1.1.1-linux-x64/bin/dorado",
        "models": "/nfs/turbo/umms-bleu-secure/programs/dorado_models",
    },
    "greatlakes": {
        "partition": "gpu_mig40",
        "account": "bleu99",
        "gres": "gpu:nvidia_a100_80gb_pcie_3g.40gb:1",
        "cpus": 8,
        "mem": "64G",
        "time": "24:00:00",
        "dorado": "dorado",
        "models": "",
    },
}

# =============================================================================
# DEFAULT PRESETS
# =============================================================================
DEFAULT_PRESETS = {
    "sma-single-ended": {
        "name": "SMA_single_ended",
        "type": "single-ended",
        "kit": "SMA",
        "mask1_front": "AAGGTTAA",
        "mask1_rear": "CAGCACCT",
        "mask2_front": "",
        "mask2_rear": "",
        "scoring": {
            "max_barcode_penalty": 11,
            "barcode_end_proximity": 75,
            "min_barcode_penalty_dist": 3,
        },
    },
    "sma-double-ended": {
        "name": "SMA_double_ended",
        "type": "double-ended",
        "kit": "SMA",
        "mask1_front": "AAGGTTAA",
        "mask1_rear": "CAGCACCT",
        "mask2_front": "TTAACCTT",
        "mask2_rear": "AGGTGCTG",
        "scoring": {
            "max_barcode_penalty": 11,
            "barcode_end_proximity": 75,
            "min_barcode_penalty_dist": 3,
        },
    },
}


# =============================================================================
# DATABASE FUNCTIONS
# =============================================================================

def get_db_path() -> Path:
    """Get default database path."""
    return Path.home() / ".sma-prep" / "sma_experiments.db"


def init_database(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Initialize SQLite database with schema."""
    if db_path is None:
        db_path = get_db_path()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS targets (
            target_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            sequence TEXT NOT NULL,
            length INTEGER NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        );

        CREATE TABLE IF NOT EXISTS size_mappings (
            target_id TEXT PRIMARY KEY REFERENCES targets(target_id),
            min_length INTEGER NOT NULL,
            max_length INTEGER NOT NULL,
            expected_length INTEGER NOT NULL,
            tolerance_pct REAL DEFAULT 15.0
        );

        CREATE TABLE IF NOT EXISTS experiments (
            exp_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sample_sheet_path TEXT,
            config_dir TEXT,
            targets TEXT,
            barcodes TEXT,
            status TEXT DEFAULT 'initialized',
            metadata TEXT
        );

        CREATE TABLE IF NOT EXISTS samples (
            sample_id TEXT PRIMARY KEY,
            exp_id TEXT REFERENCES experiments(exp_id),
            barcode INTEGER NOT NULL,
            target_id TEXT REFERENCES targets(target_id),
            condition TEXT,
            replicate INTEGER,
            read_count INTEGER,
            mean_qscore REAL,
            metadata TEXT
        );

        CREATE TABLE IF NOT EXISTS barcode_configs (
            config_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            preset TEXT,
            mask1_front TEXT,
            mask1_rear TEXT,
            mask2_front TEXT,
            mask2_rear TEXT,
            barcodes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        );
    """)

    conn.commit()
    return conn


# =============================================================================
# TARGET MANAGEMENT
# =============================================================================

def target_add(args):
    """Add a new target sequence to the registry."""
    conn = init_database(args.db)

    # Validate sequence
    sequence = args.sequence.upper().replace(" ", "").replace("\n", "")
    if not all(c in "ACGTN" for c in sequence):
        print(f"Error: Invalid characters in sequence. Only ACGTN allowed.")
        sys.exit(1)

    length = len(sequence)
    target_id = args.name.lower().replace(" ", "_")

    # Calculate size range if not provided
    tolerance = args.tolerance if args.tolerance else 15.0
    min_length = args.min_length if args.min_length else int(length * (1 - tolerance/100))
    max_length = args.max_length if args.max_length else int(length * (1 + tolerance/100))

    metadata = {
        "description": args.description or "",
        "barcode": args.barcode,
        "source": args.source or "manual",
    }

    try:
        conn.execute("""
            INSERT INTO targets (target_id, name, sequence, length, description, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (target_id, args.name, sequence, length, args.description, json.dumps(metadata)))

        conn.execute("""
            INSERT INTO size_mappings (target_id, min_length, max_length, expected_length, tolerance_pct)
            VALUES (?, ?, ?, ?, ?)
        """, (target_id, min_length, max_length, length, tolerance))

        conn.commit()
        print(f"Added target: {args.name}")
        print(f"  Length: {length} bp")
        print(f"  Size range: {min_length}-{max_length} bp")
        if args.barcode:
            print(f"  Default barcode: {args.barcode}")

    except sqlite3.IntegrityError:
        print(f"Error: Target '{args.name}' already exists. Use --force to overwrite.")
        sys.exit(1)

    conn.close()


def target_list(args):
    """List all registered targets."""
    conn = init_database(args.db)

    cur = conn.execute("""
        SELECT t.target_id, t.name, t.length, t.description,
               s.min_length, s.max_length, t.metadata
        FROM targets t
        LEFT JOIN size_mappings s ON t.target_id = s.target_id
        ORDER BY t.name
    """)

    rows = cur.fetchall()

    if not rows:
        print("No targets registered. Use 'sma_prep.py target add' to add targets.")
        return

    print("=" * 70)
    print("REGISTERED TARGETS")
    print("=" * 70)
    print(f"{'Name':<15} {'Length':>8} {'Size Range':>15} {'Description':<30}")
    print("-" * 70)

    for row in rows:
        size_range = f"{row['min_length']}-{row['max_length']}" if row['min_length'] else "N/A"
        desc = (row['description'] or "")[:28]
        print(f"{row['name']:<15} {row['length']:>8} {size_range:>15} {desc:<30}")

    print("=" * 70)
    conn.close()


def target_import(args):
    """Import targets from FASTA file."""
    conn = init_database(args.db)

    fasta_path = Path(args.fasta)
    if not fasta_path.exists():
        print(f"Error: FASTA file not found: {fasta_path}")
        sys.exit(1)

    # Parse FASTA
    targets = []
    current_name = None
    current_seq = []

    with open(fasta_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if current_name:
                    targets.append((current_name, "".join(current_seq)))
                current_name = line[1:].split()[0]
                current_seq = []
            else:
                current_seq.append(line.upper())

        if current_name:
            targets.append((current_name, "".join(current_seq)))

    print(f"Found {len(targets)} sequences in {fasta_path.name}")

    for name, seq in targets:
        target_id = name.lower().replace(" ", "_")
        length = len(seq)
        tolerance = args.tolerance if args.tolerance else 15.0
        min_length = int(length * (1 - tolerance/100))
        max_length = int(length * (1 + tolerance/100))

        try:
            conn.execute("""
                INSERT OR REPLACE INTO targets (target_id, name, sequence, length, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (target_id, name, seq, length, json.dumps({"source": str(fasta_path)})))

            conn.execute("""
                INSERT OR REPLACE INTO size_mappings
                (target_id, min_length, max_length, expected_length, tolerance_pct)
                VALUES (?, ?, ?, ?, ?)
            """, (target_id, min_length, max_length, length, tolerance))

            print(f"  + {name}: {length} bp ({min_length}-{max_length})")

        except Exception as e:
            print(f"  ! {name}: Failed - {e}")

    conn.commit()
    conn.close()


# =============================================================================
# SAMPLE SHEET GENERATION
# =============================================================================

def generate_samplesheet(args):
    """Generate sample sheet from barcode mapping."""
    samples = []

    if args.barcodes:
        # Parse barcode:sample_id format
        for mapping in args.barcodes.split(","):
            if ":" in mapping:
                bc, sample_id = mapping.split(":", 1)
                samples.append({
                    "barcode": int(bc.strip()),
                    "sample_id": sample_id.strip(),
                    "target": "",
                    "condition": "",
                    "replicate": 1,
                    "notes": "",
                })
            else:
                print(f"Warning: Invalid mapping format '{mapping}'. Use 'barcode:sample_id'")

    elif args.from_csv:
        # Read from existing CSV
        with open(args.from_csv) as f:
            reader = csv.DictReader(f)
            for row in reader:
                samples.append({
                    "barcode": int(row.get("barcode", 0)),
                    "sample_id": row.get("sample_id", ""),
                    "target": row.get("target", ""),
                    "condition": row.get("condition", ""),
                    "replicate": int(row.get("replicate", 1)),
                    "notes": row.get("notes", ""),
                })

    elif args.interactive:
        print("Interactive sample sheet generation")
        print("Enter samples (barcode sample_id target condition), empty line to finish:")
        while True:
            line = input("> ").strip()
            if not line:
                break
            parts = line.split()
            if len(parts) >= 2:
                samples.append({
                    "barcode": int(parts[0]),
                    "sample_id": parts[1],
                    "target": parts[2] if len(parts) > 2 else "",
                    "condition": parts[3] if len(parts) > 3 else "",
                    "replicate": 1,
                    "notes": "",
                })

    if not samples:
        print("No samples defined. Use --barcodes, --from-csv, or --interactive")
        sys.exit(1)

    # Write sample sheet
    output = Path(args.output) if args.output else Path("samples.csv")

    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "barcode", "sample_id", "target", "condition", "replicate", "notes"
        ])
        writer.writeheader()
        writer.writerows(samples)

    print(f"Sample sheet written: {output}")
    print(f"  {len(samples)} samples")

    # Show preview
    print("\nPreview:")
    print(f"{'BC':>4} {'Sample ID':<20} {'Target':<10} {'Condition':<15}")
    print("-" * 55)
    for s in samples[:10]:
        print(f"{s['barcode']:>4} {s['sample_id']:<20} {s['target']:<10} {s['condition']:<15}")
    if len(samples) > 10:
        print(f"  ... and {len(samples) - 10} more")


# =============================================================================
# BARCODE CONFIGURATION
# =============================================================================

def generate_barcodes(args):
    """Generate Dorado barcode configuration files."""
    # Load preset or use custom
    if args.preset:
        if args.preset not in DEFAULT_PRESETS:
            print(f"Error: Unknown preset '{args.preset}'")
            print(f"Available: {', '.join(DEFAULT_PRESETS.keys())}")
            sys.exit(1)
        config = DEFAULT_PRESETS[args.preset].copy()
    else:
        config = {
            "name": args.name or "custom_barcodes",
            "type": "single-ended" if not args.mask2_front else "double-ended",
            "kit": args.kit or "SMA",
            "mask1_front": args.mask1_front or "AAGGTTAA",
            "mask1_rear": args.mask1_rear or "CAGCACCT",
            "mask2_front": args.mask2_front or "",
            "mask2_rear": args.mask2_rear or "",
            "scoring": {
                "max_barcode_penalty": 11,
                "barcode_end_proximity": 75,
                "min_barcode_penalty_dist": 3,
            },
        }

    # Get barcodes from sample sheet or args
    barcodes = []
    if args.sample_sheet:
        with open(args.sample_sheet) as f:
            reader = csv.DictReader(f)
            barcodes = sorted(set(int(row["barcode"]) for row in reader))
    elif args.barcodes:
        barcodes = [int(b) for b in args.barcodes]

    if not barcodes:
        print("Error: No barcodes specified. Use --sample-sheet or --barcodes")
        sys.exit(1)

    # Validate barcodes
    for bc in barcodes:
        if bc < 1 or bc > 96:
            print(f"Error: Invalid barcode {bc}. Must be 1-96")
            sys.exit(1)

    # Generate TOML
    name = config["name"]
    is_double = bool(config.get("mask2_front"))

    toml_content = f"""# Custom Barcode Arrangement for Dorado
# Generated: {datetime.now().isoformat()}
# Config: {name}
# Barcodes: {', '.join(f'NB{b:02d}' for b in sorted(barcodes))}

[arrangement]
name = "{name}"
kit = "{config['kit']}"

# Front barcode flanking sequences
mask1_front = "{config['mask1_front']}"
mask1_rear = "{config['mask1_rear']}"

# Rear barcode flanking sequences
mask2_front = "{config.get('mask2_front', '')}"
mask2_rear = "{config.get('mask2_rear', '')}"

# Barcode pattern
barcode1_pattern = "{name}_NB%02i"
"""

    if is_double:
        toml_content += f'barcode2_pattern = "{name}_NB%02i"\n'

    scoring = config.get("scoring", {})
    toml_content += f"""
first_index = {min(barcodes)}
last_index = {max(barcodes)}

[scoring]
max_barcode_penalty = {scoring.get('max_barcode_penalty', 11)}
barcode_end_proximity = {scoring.get('barcode_end_proximity', 75)}
min_barcode_penalty_dist = {scoring.get('min_barcode_penalty_dist', 3)}
min_separation_only_dist = {scoring.get('min_separation_only_dist', 6)}
flank_left_pad = {scoring.get('flank_left_pad', 5)}
flank_right_pad = {scoring.get('flank_right_pad', 10)}
front_barcode_window = {scoring.get('front_barcode_window', 175)}
rear_barcode_window = {scoring.get('rear_barcode_window', 175)}
"""

    # Generate FASTA
    fasta_lines = [f"# Barcode sequences for {name}"]
    for bc in sorted(barcodes):
        fasta_lines.append(f">{name}_NB{bc:02d}")
        fasta_lines.append(ONT_BARCODES[bc])
    fasta_content = "\n".join(fasta_lines) + "\n"

    # Write files
    output_dir = Path(args.output_dir) if args.output_dir else Path(".")
    output_dir.mkdir(parents=True, exist_ok=True)

    toml_path = output_dir / f"{name}.toml"
    fasta_path = output_dir / f"{name}_sequences.fasta"

    toml_path.write_text(toml_content)
    fasta_path.write_text(fasta_content)

    print(f"Generated barcode configuration:")
    print(f"  TOML:  {toml_path}")
    print(f"  FASTA: {fasta_path}")
    print(f"  Barcodes: {', '.join(f'NB{b:02d}' for b in sorted(barcodes))}")

    # Print Dorado command
    both_ends = "--barcode-both-ends" if is_double else ""
    print(f"\nDorado command:")
    print(f"dorado basecaller sup <pod5_dir> \\")
    print(f"    --kit-name {name} \\")
    print(f"    --barcode-arrangement {toml_path} \\")
    print(f"    --barcode-sequences {fasta_path} \\")
    if both_ends:
        print(f"    {both_ends} \\")
    print(f"    > output.bam")


# =============================================================================
# REFERENCE FASTA GENERATION
# =============================================================================

def generate_reference(args):
    """Generate reference FASTA from registered targets."""
    conn = init_database(args.db)

    # Get targets
    if args.targets:
        target_ids = [t.strip().lower().replace(" ", "_") for t in args.targets.split(",")]
    else:
        # Get all targets
        cur = conn.execute("SELECT target_id FROM targets")
        target_ids = [row[0] for row in cur.fetchall()]

    if not target_ids:
        print("No targets specified or found. Use --targets or add targets first.")
        sys.exit(1)

    # Fetch sequences
    placeholders = ",".join("?" * len(target_ids))
    cur = conn.execute(f"""
        SELECT target_id, name, sequence, length
        FROM targets
        WHERE target_id IN ({placeholders})
    """, target_ids)

    rows = cur.fetchall()

    if not rows:
        print(f"No targets found matching: {', '.join(target_ids)}")
        sys.exit(1)

    # Build FASTA
    fasta_lines = []
    for row in rows:
        header = f">{row['name']}  ({row['length']} bp)"
        fasta_lines.append(header)

        seq = row["sequence"]
        # Wrap at 80 characters
        for i in range(0, len(seq), 80):
            fasta_lines.append(seq[i:i+80])

    # Optionally include barcode sequences
    if args.include_barcodes:
        fasta_lines.append("")
        fasta_lines.append("# Barcode sequences")
        for bc_num, bc_seq in sorted(ONT_BARCODES.items()):
            fasta_lines.append(f">NB{bc_num:02d}")
            fasta_lines.append(bc_seq)

    fasta_content = "\n".join(fasta_lines) + "\n"

    # Write output
    output = Path(args.output) if args.output else Path("reference.fa")
    output.write_text(fasta_content)

    print(f"Reference FASTA written: {output}")
    print(f"  {len(rows)} target(s)")
    for row in rows:
        print(f"    - {row['name']}: {row['length']} bp")

    conn.close()


# =============================================================================
# SIZE RANGE MANAGEMENT
# =============================================================================

def manage_sizes(args):
    """Manage size-to-target mappings."""
    conn = init_database(args.db)

    if args.add:
        # Parse target:min-max format
        for mapping in args.add:
            match = re.match(r"(\w+):(\d+)-(\d+)", mapping)
            if not match:
                print(f"Invalid format: {mapping}. Use 'target:min-max'")
                continue

            target_id = match.group(1).lower()
            min_len = int(match.group(2))
            max_len = int(match.group(3))
            expected = (min_len + max_len) // 2

            # Check target exists
            cur = conn.execute("SELECT target_id FROM targets WHERE target_id = ?", (target_id,))
            if not cur.fetchone():
                print(f"Warning: Target '{target_id}' not found in registry")

            conn.execute("""
                INSERT OR REPLACE INTO size_mappings
                (target_id, min_length, max_length, expected_length)
                VALUES (?, ?, ?, ?)
            """, (target_id, min_len, max_len, expected))

            print(f"Added size mapping: {target_id} -> {min_len}-{max_len} bp")

        conn.commit()

    if args.list or not args.add:
        cur = conn.execute("""
            SELECT s.target_id, t.name, s.min_length, s.max_length, s.expected_length, s.tolerance_pct
            FROM size_mappings s
            LEFT JOIN targets t ON s.target_id = t.target_id
            ORDER BY s.expected_length
        """)

        rows = cur.fetchall()

        print("=" * 60)
        print("SIZE-TO-TARGET MAPPINGS")
        print("=" * 60)
        print(f"{'Target':<15} {'Expected':>10} {'Range':>15} {'Tolerance':>10}")
        print("-" * 60)

        for row in rows:
            name = row["name"] or row["target_id"]
            print(f"{name:<15} {row['expected_length']:>10} {row['min_length']}-{row['max_length']:>10} {row['tolerance_pct']:>9.1f}%")

        print("=" * 60)

    conn.close()


# =============================================================================
# DORADO INTEGRATION
# =============================================================================

def run_dorado(args):
    """Generate or run Dorado basecalling/demultiplexing."""
    # Find config files
    config_dir = Path(args.config_dir) if args.config_dir else Path(".")

    toml_files = list(config_dir.glob("*.toml"))
    fasta_files = list(config_dir.glob("*_sequences.fasta"))

    if not toml_files:
        print(f"No TOML files found in {config_dir}")
        print("Run 'sma_prep.py barcodes' first to generate config files")
        sys.exit(1)

    toml_path = toml_files[0]
    fasta_path = fasta_files[0] if fasta_files else None

    # Extract kit name from TOML
    kit_name = toml_path.stem

    # Build command
    cluster = CLUSTERS.get(args.cluster, CLUSTERS["armis2"])

    pod5_dir = args.pod5_dir
    output_dir = Path(args.output_dir) if args.output_dir else Path("results")
    output_bam = output_dir / f"{kit_name}_demuxed.bam"

    model = args.model or "sup"

    # Check for reference
    ref_arg = ""
    if args.reference:
        ref_arg = f"--reference {args.reference}"

    dorado_cmd = f"""{cluster['dorado']} basecaller {model} {pod5_dir} \\
    --kit-name {kit_name} \\
    --barcode-arrangement {toml_path} \\
    --barcode-sequences {fasta_path} \\
    {ref_arg} \\
    > {output_bam}"""

    if args.slurm:
        # Generate SLURM script
        script = f"""#!/bin/bash
#SBATCH --job-name=sma_{kit_name}
#SBATCH --partition={cluster['partition']}
#SBATCH --account={cluster['account']}
#SBATCH --gres={cluster['gres']}
#SBATCH --cpus-per-task={cluster['cpus']}
#SBATCH --mem={cluster['mem']}
#SBATCH --time={cluster['time']}
#SBATCH --output=sma_{kit_name}_%j.out
#SBATCH --error=sma_{kit_name}_%j.err

# Generated: {datetime.now().isoformat()}
# SMA-seq Dorado Job

echo "Starting SMA-seq basecalling"
echo "Pod5 dir: {pod5_dir}"
echo "Config: {kit_name}"

mkdir -p {output_dir}

"""
        if args.cluster == "greatlakes":
            script += "module load dorado\n\n"

        script += f"""{dorado_cmd}

echo "Basecalling complete"

# Index BAM
samtools index {output_bam}

# Generate summary
{cluster['dorado']} summary {output_bam} > {output_bam}.summary.txt

echo "Done: {output_bam}"
"""

        slurm_path = Path(args.slurm)
        slurm_path.write_text(script)
        print(f"SLURM script written: {slurm_path}")
        print(f"Submit with: sbatch {slurm_path}")

    elif args.run:
        # Direct execution
        print(f"Running Dorado...")
        print(dorado_cmd)
        os.system(dorado_cmd)

    else:
        print("Dorado command:")
        print(dorado_cmd)
        print("\nUse --slurm <file> to generate SLURM script or --run to execute directly")


# =============================================================================
# EXPERIMENT REGISTRATION
# =============================================================================

def register_experiment(args):
    """Register experiment in database."""
    conn = init_database(args.db)

    # Load sample sheet
    samples = []
    barcodes = []
    targets = set()

    if args.sample_sheet:
        with open(args.sample_sheet) as f:
            reader = csv.DictReader(f)
            for row in reader:
                samples.append(row)
                barcodes.append(int(row.get("barcode", 0)))
                if row.get("target"):
                    targets.add(row["target"])

    metadata = {
        "config_dir": str(args.config_dir) if args.config_dir else None,
        "bam_dir": str(args.bam_dir) if args.bam_dir else None,
        "created_by": os.environ.get("USER", "unknown"),
    }

    # Insert experiment
    conn.execute("""
        INSERT OR REPLACE INTO experiments
        (exp_id, sample_sheet_path, config_dir, targets, barcodes, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        args.exp_id,
        str(args.sample_sheet) if args.sample_sheet else None,
        str(args.config_dir) if args.config_dir else None,
        json.dumps(list(targets)),
        json.dumps(sorted(set(barcodes))),
        json.dumps(metadata),
    ))

    # Insert samples
    for sample in samples:
        sample_id = f"{args.exp_id}_{sample.get('sample_id', sample.get('barcode'))}"
        target_id = sample.get("target", "").lower().replace(" ", "_") or None

        conn.execute("""
            INSERT OR REPLACE INTO samples
            (sample_id, exp_id, barcode, target_id, condition, replicate)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            sample_id,
            args.exp_id,
            int(sample.get("barcode", 0)),
            target_id,
            sample.get("condition", ""),
            int(sample.get("replicate", 1)),
        ))

    conn.commit()

    print(f"Registered experiment: {args.exp_id}")
    print(f"  Samples: {len(samples)}")
    print(f"  Barcodes: {sorted(set(barcodes))}")
    print(f"  Targets: {list(targets)}")

    conn.close()


# =============================================================================
# INTERACTIVE WIZARD
# =============================================================================

def run_wizard(args):
    """Interactive setup wizard."""
    print("=" * 60)
    print("SMA-seq Preparation Wizard")
    print("=" * 60)
    print()
    print("This wizard will guide you through setting up an SMA-seq experiment.")
    print()

    # Step 1: Experiment ID
    exp_id = input("Experiment ID (e.g., exp-001): ").strip()
    if not exp_id:
        exp_id = f"exp-{datetime.now().strftime('%Y%m%d')}"
        print(f"  Using: {exp_id}")

    # Step 2: Targets
    print("\nStep 2: Define target sequences")
    print("  Options:")
    print("    1. Import from FASTA file")
    print("    2. Enter sequences manually")
    print("    3. Use existing targets from database")

    choice = input("Choice [1-3]: ").strip()

    targets = []
    if choice == "1":
        fasta_path = input("FASTA file path: ").strip()
        if fasta_path and Path(fasta_path).exists():
            # Parse and add targets
            print(f"  Importing from {fasta_path}...")
            # (actual import would happen here)
    elif choice == "2":
        print("Enter targets (name sequence), empty line to finish:")
        while True:
            line = input("  > ").strip()
            if not line:
                break
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                targets.append({"name": parts[0], "sequence": parts[1]})

    # Step 3: Barcodes and samples
    print("\nStep 3: Define samples")
    print("Enter barcode:sample_id mappings (e.g., 2:WT,4:MUT), or press Enter for interactive:")

    mapping = input("Mappings: ").strip()
    samples = []

    if mapping:
        for m in mapping.split(","):
            if ":" in m:
                bc, sid = m.split(":", 1)
                samples.append({"barcode": int(bc), "sample_id": sid})
    else:
        print("Enter samples (barcode sample_id), empty line to finish:")
        while True:
            line = input("  > ").strip()
            if not line:
                break
            parts = line.split()
            if len(parts) >= 2:
                samples.append({"barcode": int(parts[0]), "sample_id": parts[1]})

    # Step 4: Barcode preset
    print("\nStep 4: Barcode configuration")
    print("  Available presets:")
    for name in DEFAULT_PRESETS:
        print(f"    - {name}")

    preset = input("Preset [sma-single-ended]: ").strip() or "sma-single-ended"

    # Step 5: Output directory
    print("\nStep 5: Output configuration")
    output_dir = input(f"Output directory [{exp_id}/]: ").strip() or f"{exp_id}/"

    # Summary
    print("\n" + "=" * 60)
    print("CONFIGURATION SUMMARY")
    print("=" * 60)
    print(f"Experiment ID: {exp_id}")
    print(f"Targets: {len(targets)}")
    print(f"Samples: {len(samples)}")
    print(f"Preset: {preset}")
    print(f"Output: {output_dir}")
    print("=" * 60)

    confirm = input("\nProceed with setup? [Y/n]: ").strip().lower()
    if confirm in ("", "y", "yes"):
        print("\nGenerating configuration files...")
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate sample sheet
        if samples:
            sample_sheet_path = output_path / "samples.csv"
            with open(sample_sheet_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["barcode", "sample_id", "target", "condition", "replicate", "notes"])
                writer.writeheader()
                for s in samples:
                    writer.writerow({
                        "barcode": s["barcode"],
                        "sample_id": s["sample_id"],
                        "target": "",
                        "condition": "",
                        "replicate": 1,
                        "notes": "",
                    })
            print(f"  Sample sheet: {sample_sheet_path}")

        print("\nSetup complete!")
        print(f"\nNext steps:")
        print(f"  1. Review {output_dir}/samples.csv")
        print(f"  2. Run: python3 sma_prep.py barcodes --preset {preset} --sample-sheet {output_dir}/samples.csv --output-dir {output_dir}")
        print(f"  3. Run: python3 sma_prep.py dorado --config-dir {output_dir} --pod5-dir <path> --slurm job.sbatch")
    else:
        print("Setup cancelled.")


# =============================================================================
# CLI MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="SMA-seq Preparation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--db", type=Path, help="Database path (default: ~/.sma-prep/sma_experiments.db)")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Wizard
    wizard_parser = subparsers.add_parser("wizard", help="Interactive setup wizard")
    wizard_parser.set_defaults(func=run_wizard)

    # Target commands
    target_parser = subparsers.add_parser("target", help="Target sequence management")
    target_sub = target_parser.add_subparsers(dest="target_cmd")

    # target add
    add_parser = target_sub.add_parser("add", help="Add a new target")
    add_parser.add_argument("--name", required=True, help="Target name")
    add_parser.add_argument("--sequence", required=True, help="DNA sequence")
    add_parser.add_argument("--description", help="Description")
    add_parser.add_argument("--barcode", type=int, help="Default barcode number")
    add_parser.add_argument("--min-length", type=int, help="Minimum expected length")
    add_parser.add_argument("--max-length", type=int, help="Maximum expected length")
    add_parser.add_argument("--tolerance", type=float, default=15.0, help="Size tolerance %%")
    add_parser.add_argument("--source", help="Source of sequence")
    add_parser.add_argument("--force", action="store_true", help="Overwrite existing")
    add_parser.set_defaults(func=target_add)

    # target list
    list_parser = target_sub.add_parser("list", help="List targets")
    list_parser.set_defaults(func=target_list)

    # target import
    import_parser = target_sub.add_parser("import", help="Import from FASTA")
    import_parser.add_argument("fasta", help="FASTA file path")
    import_parser.add_argument("--tolerance", type=float, default=15.0, help="Size tolerance %%")
    import_parser.set_defaults(func=target_import)

    # Sample sheet
    ss_parser = subparsers.add_parser("samplesheet", help="Generate sample sheet")
    ss_parser.add_argument("--barcodes", help="Barcode:sample_id mappings (comma-separated)")
    ss_parser.add_argument("--from-csv", help="Input CSV with sample metadata")
    ss_parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    ss_parser.add_argument("--output", "-o", help="Output file (default: samples.csv)")
    ss_parser.set_defaults(func=generate_samplesheet)

    # Barcodes
    bc_parser = subparsers.add_parser("barcodes", help="Generate barcode configuration")
    bc_parser.add_argument("--preset", help="Use built-in preset")
    bc_parser.add_argument("--sample-sheet", help="Sample sheet CSV")
    bc_parser.add_argument("--barcodes", nargs="+", type=int, help="Barcode numbers")
    bc_parser.add_argument("--name", help="Configuration name")
    bc_parser.add_argument("--kit", help="Kit name")
    bc_parser.add_argument("--mask1-front", help="Front barcode leading flank")
    bc_parser.add_argument("--mask1-rear", help="Front barcode trailing flank")
    bc_parser.add_argument("--mask2-front", help="Rear barcode leading flank")
    bc_parser.add_argument("--mask2-rear", help="Rear barcode trailing flank")
    bc_parser.add_argument("--output-dir", help="Output directory")
    bc_parser.set_defaults(func=generate_barcodes)

    # Reference
    ref_parser = subparsers.add_parser("ref", help="Generate reference FASTA")
    ref_parser.add_argument("--targets", help="Comma-separated target names")
    ref_parser.add_argument("--include-barcodes", action="store_true", help="Include barcode sequences")
    ref_parser.add_argument("--output", "-o", help="Output file")
    ref_parser.set_defaults(func=generate_reference)

    # Sizes
    size_parser = subparsers.add_parser("sizes", help="Manage size mappings")
    size_parser.add_argument("--add", nargs="+", help="Add mapping (target:min-max)")
    size_parser.add_argument("--list", action="store_true", help="List mappings")
    size_parser.set_defaults(func=manage_sizes)

    # Dorado
    dorado_parser = subparsers.add_parser("dorado", help="Run Dorado basecalling")
    dorado_parser.add_argument("--pod5-dir", required=True, help="POD5 directory")
    dorado_parser.add_argument("--config-dir", help="Config directory with TOML/FASTA")
    dorado_parser.add_argument("--reference", help="Reference FASTA for alignment")
    dorado_parser.add_argument("--output-dir", help="Output directory")
    dorado_parser.add_argument("--model", default="sup", help="Dorado model (fast/hac/sup)")
    dorado_parser.add_argument("--cluster", choices=["armis2", "greatlakes"], default="armis2")
    dorado_parser.add_argument("--slurm", help="Generate SLURM script")
    dorado_parser.add_argument("--run", action="store_true", help="Run directly")
    dorado_parser.set_defaults(func=run_dorado)

    # Register
    reg_parser = subparsers.add_parser("register", help="Register experiment")
    reg_parser.add_argument("--exp-id", required=True, help="Experiment ID")
    reg_parser.add_argument("--sample-sheet", help="Sample sheet CSV")
    reg_parser.add_argument("--config-dir", help="Config directory")
    reg_parser.add_argument("--bam-dir", help="BAM output directory")
    reg_parser.set_defaults(func=register_experiment)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Handle target subcommands
    if args.command == "target":
        if not args.target_cmd:
            target_parser.print_help()
            return

    if hasattr(args, "func"):
        args.func(args)


if __name__ == "__main__":
    main()
