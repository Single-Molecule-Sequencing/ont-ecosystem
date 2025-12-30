#!/usr/bin/env python3
"""
ingest.py - Main Processing Script

Parses inputs, calculates metrics, tags BAMs, and populates the database.
This is the core processing script for the SMA single-pass pipeline.

Usage:
    python ingest.py --db <database.db> --bam <input.bam> --pod5 <pod5_dir> --ref <ref.fa>

Or with Input directory from inputInit.py:
    python ingest.py --db <database.db> --exp-id <exp_id> --input-dir Input/
"""

import argparse
import hashlib
import math
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys

try:
    import pysam
except ImportError:
    print("Error: pysam required. Install with: pip install pysam")
    sys.exit(1)

try:
    import edlib
except ImportError:
    print("Error: edlib required. Install with: pip install edlib")
    sys.exit(1)

# Optional POD5 support
try:
    import pod5
    HAS_POD5 = True
except ImportError:
    HAS_POD5 = False
    print("Warning: pod5 not available. End reason extraction will be skipped.")

# =============================================================================
# PER-BARCODE SIZE-TO-SEQUENCE MAPPING
# =============================================================================
# After demultiplexing, each barcode directory contains ONE target type.
# This mapping defines which reference to use for each barcode.

BARCODE_TO_REFERENCE = {
    # Forward orientation (barcode01-04)
    'V04_1': {'reference': 'V0-4.1', 'length': 168, 'tolerance': 30},
    'V04_2': {'reference': 'V0-4.2', 'length': 165, 'tolerance': 30},
    'V04_3': {'reference': 'V0-4.3', 'length': 188, 'tolerance': 30},
    'V04_4': {'reference': 'V0-4.4', 'length': 160, 'tolerance': 30},
    'V039': {'reference': 'V0-39', 'length': 110, 'tolerance': 30},

    # Reverse complement orientation (barcode06-09)
    'V04_1_2': {'reference': 'V0-4.1_RC', 'length': 169, 'tolerance': 30},
    'V04_2_2': {'reference': 'V0-4.2_RC', 'length': 165, 'tolerance': 30},
    'V04_3_2': {'reference': 'V0-4.3_RC', 'length': 188, 'tolerance': 30},
    'V04_4_2': {'reference': 'V0-4.4_RC', 'length': 160, 'tolerance': 30},
    'V039_2': {'reference': 'V0-39_RC', 'length': 110, 'tolerance': 30},
}


def get_barcode_reference(barcode_id: str) -> Optional[Dict]:
    """
    Get the expected reference for a barcode directory.

    Returns dict with 'reference', 'length', 'tolerance' or None if not found.
    """
    return BARCODE_TO_REFERENCE.get(barcode_id)


def parse_fasta(fasta_path: Path, tolerance: int = 30) -> Dict[str, Tuple[str, int, int, int]]:
    """
    Parse reference FASTA and calculate length ranges.

    Args:
        fasta_path: Path to FASTA file
        tolerance: Size tolerance in bp (default ±30bp)

    Returns dict: {defline: (sequence, length, range_min, range_max)}
    """
    references = {}

    current_id = None
    current_seq = []

    with open(fasta_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('>'):
                # Save previous sequence
                if current_id is not None:
                    seq = ''.join(current_seq).upper()
                    seq_len = len(seq)
                    references[current_id] = (
                        seq,
                        seq_len,
                        max(0, seq_len - tolerance),
                        seq_len + tolerance
                    )
                # Parse new header - take first word
                current_id = line[1:].split()[0]
                current_seq = []
            else:
                current_seq.append(line)

        # Save last sequence
        if current_id is not None:
            seq = ''.join(current_seq).upper()
            seq_len = len(seq)
            references[current_id] = (
                seq,
                seq_len,
                max(0, seq_len - tolerance),
                seq_len + tolerance
            )

    return references


def parse_fasta_single_ref(fasta_path: Path, target_ref_id: str, tolerance: int = 30) -> Dict[str, Tuple[str, int, int, int]]:
    """
    Parse FASTA but only return the single reference matching target_ref_id.

    This is used for per-barcode processing where we only want ONE reference.

    Args:
        fasta_path: Path to FASTA file
        target_ref_id: Reference ID to extract (e.g., 'V0-4.2')
        tolerance: Size tolerance in bp (default ±30bp)

    Returns dict with single entry: {ref_id: (sequence, length, range_min, range_max)}
    """
    all_refs = parse_fasta(fasta_path, tolerance)

    # Find matching reference
    if target_ref_id in all_refs:
        return {target_ref_id: all_refs[target_ref_id]}

    # Try case-insensitive match
    for ref_id in all_refs:
        if ref_id.upper() == target_ref_id.upper():
            return {target_ref_id: all_refs[ref_id]}

    print(f"  Warning: Reference '{target_ref_id}' not found in FASTA")
    return {}


def load_end_reasons_from_summary(summary_path: Path) -> Dict[str, Tuple[str, int]]:
    """
    Load end reasons from summary TSV file (generated by extractMeta.py).

    Returns dict: {read_id: (end_reason, forced)}
    """
    end_reasons = {}

    if not summary_path.exists():
        print(f"  Warning: Summary file not found: {summary_path}")
        return end_reasons

    print(f"  Loading end reasons from summary: {summary_path}")

    with open(summary_path, 'r') as f:
        # Skip header
        header = f.readline()
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                read_id = parts[0]
                end_reason = parts[1]
                forced = int(parts[2]) if len(parts) > 2 else 0
                end_reasons[read_id] = (end_reason, forced)

    print(f"  Loaded {len(end_reasons):,} end reasons")
    return end_reasons


def load_pod5_end_reasons(pod5_dir: Path) -> Dict[str, Tuple[str, int]]:
    """
    Load end reasons from POD5 files directly.

    Returns dict: {read_id: (end_reason, forced)}
    """
    if not HAS_POD5:
        return {}

    end_reasons = {}

    pod5_files = list(pod5_dir.glob("*.pod5"))
    print(f"  Loading end reasons from {len(pod5_files)} POD5 files...")

    for pod5_file in pod5_files:
        try:
            with pod5.Reader(pod5_file) as reader:
                for read in reader.reads():
                    read_id = str(read.read_id)
                    # End reason is in read.end_reason
                    if hasattr(read, 'end_reason'):
                        er = read.end_reason
                        if hasattr(er, 'name'):
                            end_reason = er.name
                        else:
                            end_reason = str(er)
                    else:
                        end_reason = "unknown"

                    # Check for forced status
                    if hasattr(read, 'end_reason_forced'):
                        forced = 1 if read.end_reason_forced else 0
                    else:
                        forced = 0

                    end_reasons[read_id] = (end_reason, forced)
        except Exception as e:
            print(f"  Warning: Error reading {pod5_file}: {e}")

    print(f"  Loaded {len(end_reasons):,} end reasons")
    return end_reasons


def calculate_q_bc(quality_scores: List[int]) -> float:
    """
    Calculate probability-averaged basecall quality.

    q_bc = -10 * log10(sum(10^(-Q/10)) / n)
    """
    if not quality_scores:
        return 0.0

    # Convert to probabilities, average, convert back
    probs = [10 ** (-q / 10) for q in quality_scores]
    avg_prob = sum(probs) / len(probs)

    # Clamp to avoid log(0)
    avg_prob = max(avg_prob, 1e-10)

    return -10 * math.log10(avg_prob)


def calculate_levenshtein(read_seq: str, ref_seq: str) -> int:
    """Calculate Levenshtein edit distance using edlib."""
    result = edlib.align(read_seq, ref_seq, task="distance")
    return result['editDistance']


def calculate_q_ld(edit_distance: int, ref_length: int) -> float:
    """
    Calculate Levenshtein quality score.

    q_ld = -10 * log10(min(max(1/L^2, ed/L), 1))
    """
    if ref_length == 0:
        return 0.0

    # Calculate error rate
    error_rate = edit_distance / ref_length

    # Apply floor and ceiling
    floor_val = 1 / (ref_length ** 2)
    clamped_rate = min(max(floor_val, error_rate), 1.0)

    # Convert to Q-score
    return -10 * math.log10(clamped_rate)


def generate_unique_id(
    exp_id: str,
    model_tier: str,
    model_ver: str,
    trim: int,
    mod_flag: int,
    read_id: str
) -> str:
    """
    Generate unique read ID.

    Format: {exp_id}{tier}{ver}t{trim}m{mod_flag}_{read_hash}
    """
    # Create short hash of read_id
    read_hash = hashlib.sha256(read_id.encode()).hexdigest()[:8]

    # Clean version string (remove dots)
    ver_clean = model_ver.replace('.', '') if model_ver else '0'

    # Build ID
    tier = model_tier or 'x'
    unique_id = f"{exp_id}{tier}{ver_clean}t{trim}m{mod_flag}_{read_hash}"

    return unique_id


def match_reference(
    read_length: int,
    references: Dict[str, Tuple[str, int, int, int]]
) -> Optional[str]:
    """
    Match read to reference based on length range.

    Returns refseq_id if match found, None otherwise.
    """
    for ref_id, (seq, length, range_min, range_max) in references.items():
        if range_min <= read_length <= range_max:
            return ref_id
    return None


def parse_model_from_rg(rg_tag: str) -> Tuple[str, str]:
    """
    Parse model tier and version from RG tag.

    Example: 34fa833d-..._dna_r10.4.1_e8.2_400bps_sup@v5.2.0_barcode07
    Returns: ('s', '5.2.0')  # 's' for sup
    """
    model_tier = None
    model_ver = None

    # Look for model pattern
    patterns = [
        (r'_sup@v([\d.]+)', 's'),
        (r'_hac@v([\d.]+)', 'h'),
        (r'_fast@v([\d.]+)', 'f'),
    ]

    import re
    for pattern, tier in patterns:
        match = re.search(pattern, rg_tag)
        if match:
            model_tier = tier
            model_ver = match.group(1)
            break

    return model_tier, model_ver


def process_reads(
    db_path: Path,
    bam_path: Path,
    references: Dict[str, Tuple[str, int, int, int]],
    end_reasons: Dict[str, Tuple[str, int]],
    exp_id: str,
    model_tier: str = None,
    model_ver: str = None,
    trim: int = 0,
    mod_bitflag: int = 0,
    output_bam: Path = None,
    batch_size: int = 1000,
    max_reads: int = None
):
    """
    Process reads from BAM, calculate metrics, and insert into database.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # First, insert reference sequences
    print("Inserting reference sequences...")
    for ref_id, (seq, length, range_min, range_max) in references.items():
        cursor.execute(
            """INSERT OR REPLACE INTO Refseq
               (refseq_id, refseq, reflen, refseq_range_min, refseq_range_max)
               VALUES (?, ?, ?, ?, ?)""",
            (ref_id, seq, length, range_min, range_max)
        )
    conn.commit()

    # Process BAM
    print(f"Processing BAM: {bam_path}")

    # Handle BAM directory
    if bam_path.is_dir():
        bam_files = sorted(bam_path.glob("*.bam"))
    else:
        bam_files = [bam_path]

    total_reads = 0
    matched_reads = 0
    batch = []

    for bam_file in bam_files:
        print(f"  Processing: {bam_file.name}")

        with pysam.AlignmentFile(bam_file, 'rb', check_sq=False) as bam:
            for read in bam:
                if read.query_sequence is None:
                    continue

                total_reads += 1
                read_id = read.query_name
                read_seq = read.query_sequence
                read_len = len(read_seq)

                # Get quality scores
                if read.query_qualities is not None:
                    quality_scores = list(read.query_qualities)
                else:
                    quality_scores = []

                # Calculate q_bc
                q_bc = calculate_q_bc(quality_scores)

                # Try to get model info from RG tag
                rg = read.get_tag('RG') if read.has_tag('RG') else None
                if rg and (model_tier is None or model_ver is None):
                    detected_tier, detected_ver = parse_model_from_rg(rg)
                    if model_tier is None:
                        model_tier = detected_tier
                    if model_ver is None:
                        model_ver = detected_ver

                # Match to reference
                refseq_id = match_reference(read_len, references)

                # Calculate Levenshtein if matched
                ed = None
                q_ld = None
                if refseq_id:
                    matched_reads += 1
                    ref_seq = references[refseq_id][0]
                    ed = calculate_levenshtein(read_seq, ref_seq)
                    q_ld = calculate_q_ld(ed, references[refseq_id][1])

                # Get end reason and forced status
                er_data = end_reasons.get(read_id)
                if er_data:
                    er, forced = er_data
                else:
                    er, forced = None, None

                # Get other tags
                channel = read.get_tag('ch') if read.has_tag('ch') else None
                well = read.get_tag('rn') if read.has_tag('rn') else None  # row number
                num_samples = read.get_tag('ns') if read.has_tag('ns') else None
                start_sample = read.get_tag('ts') if read.has_tag('ts') else None
                median_before = read.get_tag('sm') if read.has_tag('sm') else None
                start_time = read.get_tag('st') if read.has_tag('st') else None
                duration = read.get_tag('du') if read.has_tag('du') else None

                # Generate unique ID
                unique_id = generate_unique_id(
                    exp_id, model_tier or 'x', model_ver or '0',
                    trim, mod_bitflag, read_id
                )

                # Prepare record
                record = (
                    unique_id,
                    exp_id,
                    refseq_id,
                    read_id,
                    read_seq,
                    read_len,
                    model_tier,
                    model_ver,
                    trim,
                    mod_bitflag,
                    ed,
                    q_bc,
                    q_ld,
                    er,
                    forced,  # from end_reasons
                    channel,
                    well,
                    None,  # pore_type
                    num_samples,
                    start_sample,
                    median_before,
                    None,  # scale
                    None,  # offset
                    start_time,
                    duration
                )

                batch.append(record)

                # Commit in batches
                if len(batch) >= batch_size:
                    cursor.executemany(
                        """INSERT OR REPLACE INTO Reads
                           (uniq_id, exp_id, refseq_id, read_id, readseq, readlen,
                            model_tier, model_ver, trim, mod_bitflag, ed, q_bc, q_ld,
                            ER, forced, channel, well, pore_type, num_samples,
                            start_sample, median_before, scale, offset, start_time, duration)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        batch
                    )
                    conn.commit()
                    batch = []

                    if total_reads % 10000 == 0:
                        print(f"    Processed {total_reads:,} reads, {matched_reads:,} matched...")

                # Check max_reads limit
                if max_reads and total_reads >= max_reads:
                    print(f"  Reached max_reads limit ({max_reads:,})")
                    break

            # Break outer loop if limit reached
            if max_reads and total_reads >= max_reads:
                break

    # Final batch
    if batch:
        cursor.executemany(
            """INSERT OR REPLACE INTO Reads
               (uniq_id, exp_id, refseq_id, read_id, readseq, readlen,
                model_tier, model_ver, trim, mod_bitflag, ed, q_bc, q_ld,
                ER, forced, channel, well, pore_type, num_samples,
                start_sample, median_before, scale, offset, start_time, duration)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            batch
        )
        conn.commit()

    conn.close()

    print(f"\nProcessing complete:")
    print(f"  Total reads: {total_reads:,}")
    if total_reads > 0:
        print(f"  Matched to reference: {matched_reads:,} ({100*matched_reads/total_reads:.1f}%)")
    else:
        print(f"  Matched to reference: {matched_reads:,}")


def main():
    parser = argparse.ArgumentParser(
        description="Ingest reads into SMA database"
    )
    parser.add_argument(
        "--db", "-d",
        type=Path,
        required=True,
        help="Path to SQLite database (created by mkdb.py)"
    )
    parser.add_argument(
        "--bam", "-b",
        type=Path,
        help="Path to BAM file or directory"
    )
    parser.add_argument(
        "--pod5", "-p",
        type=Path,
        help="Path to POD5 directory"
    )
    parser.add_argument(
        "--ref", "-r",
        type=Path,
        help="Path to reference FASTA"
    )
    parser.add_argument(
        "--exp-id", "-e",
        type=str,
        help="Experiment ID"
    )
    parser.add_argument(
        "--input-dir", "-i",
        type=Path,
        help="Input directory (from inputInit.py)"
    )
    parser.add_argument(
        "--model-tier", "-t",
        choices=['s', 'h', 'f'],
        help="Model tier: s(up), h(ac), f(ast)"
    )
    parser.add_argument(
        "--model-ver", "-v",
        type=str,
        help="Model version (e.g., 5.2.0)"
    )
    parser.add_argument(
        "--trim",
        type=int,
        default=0,
        choices=[0, 1],
        help="Trim status: 0 or 1"
    )
    parser.add_argument(
        "--mod-bitflag", "-m",
        type=int,
        default=0,
        help="Modification bitflag (default: 0)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for database inserts"
    )
    parser.add_argument(
        "--max-reads", "-n",
        type=int,
        help="Maximum number of reads to process"
    )
    parser.add_argument(
        "--summary", "-s",
        type=Path,
        help="Path to summary TSV file (from extractMeta.py)"
    )

    args = parser.parse_args()

    # Validate database exists
    if not args.db.exists():
        raise FileNotFoundError(f"Database not found: {args.db}")

    # Resolve paths from input directory or explicit arguments
    if args.input_dir:
        if not args.exp_id:
            raise ValueError("--exp-id required when using --input-dir")

        bam_path = args.input_dir / f"{args.exp_id}_bam"
        if not bam_path.exists():
            bam_path = args.input_dir / f"{args.exp_id}.bam"

        pod5_path = args.input_dir / f"{args.exp_id}_pod5"
        ref_path = args.input_dir / f"{args.exp_id}.fa"
    else:
        bam_path = args.bam
        pod5_path = args.pod5
        ref_path = args.ref

    # Validate inputs
    if not bam_path or not bam_path.exists():
        raise FileNotFoundError(f"BAM not found: {bam_path}")
    if not ref_path or not ref_path.exists():
        raise FileNotFoundError(f"Reference not found: {ref_path}")

    # Get exp_id from database if not provided
    exp_id = args.exp_id
    if not exp_id:
        conn = sqlite3.connect(args.db)
        cursor = conn.cursor()
        cursor.execute("SELECT exp_id FROM Exp LIMIT 1")
        row = cursor.fetchone()
        if row:
            exp_id = row[0]
        conn.close()

    if not exp_id:
        raise ValueError("Could not determine exp_id")

    print(f"SMA Database Ingestion")
    print(f"=" * 50)
    print(f"Database: {args.db}")
    print(f"Experiment ID: {exp_id}")
    print(f"BAM: {bam_path}")
    print(f"Reference: {ref_path}")
    print(f"POD5: {pod5_path}")
    if args.max_reads:
        print(f"Max reads: {args.max_reads:,}")
    print()

    # Check for per-barcode mapping
    barcode_info = get_barcode_reference(exp_id)

    if barcode_info:
        # Use single reference for this barcode
        target_ref = barcode_info['reference']
        tolerance = barcode_info['tolerance']
        print(f"\nPER-BARCODE MODE: {exp_id} → {target_ref}")
        print(f"  Only comparing against single expected reference")
        print(f"  Size tolerance: ±{tolerance}bp")

        references = parse_fasta_single_ref(ref_path, target_ref, tolerance)
        if not references:
            raise ValueError(f"Reference '{target_ref}' not found in {ref_path}")

        print(f"\nUsing reference:")
        for ref_id, (seq, length, range_min, range_max) in references.items():
            print(f"  {ref_id}: {length} bp (match range: {range_min}-{range_max})")
    else:
        # Legacy mode: use all references (NOT RECOMMENDED)
        print("\nWARNING: Barcode not in mapping, using ALL references (may cause misassignment)")
        print("Parsing reference FASTA...")
        references = parse_fasta(ref_path, tolerance=30)
        print(f"  Found {len(references)} reference sequence(s):")
        for ref_id, (seq, length, range_min, range_max) in references.items():
            print(f"    {ref_id}: {length} bp (match range: {range_min}-{range_max})")

    # Load end reasons - prefer summary file if available
    end_reasons = {}

    # Check for summary file
    summary_path = args.summary
    if not summary_path and args.input_dir and args.exp_id:
        summary_path = args.input_dir / f"{args.exp_id}_summary.tsv"

    if summary_path and summary_path.exists():
        print("\nLoading end reasons from summary file...")
        end_reasons = load_end_reasons_from_summary(summary_path)
    elif pod5_path and pod5_path.exists():
        print("\nLoading POD5 end reasons...")
        end_reasons = load_pod5_end_reasons(pod5_path)

    # Process reads
    print("\nProcessing reads...")
    process_reads(
        db_path=args.db,
        bam_path=bam_path,
        references=references,
        end_reasons=end_reasons,
        exp_id=exp_id,
        model_tier=args.model_tier,
        model_ver=args.model_ver,
        trim=args.trim,
        mod_bitflag=args.mod_bitflag,
        batch_size=args.batch_size,
        max_reads=args.max_reads
    )

    # Print summary stats
    print("\nDatabase summary:")
    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM Reads")
    total = cursor.fetchone()[0]
    print(f"  Total reads: {total:,}")

    cursor.execute("SELECT COUNT(*) FROM Reads WHERE refseq_id IS NOT NULL")
    matched = cursor.fetchone()[0]
    print(f"  Matched reads: {matched:,}")

    cursor.execute("SELECT AVG(q_bc) FROM Reads")
    avg_qbc = cursor.fetchone()[0]
    print(f"  Average Q_bc: {avg_qbc:.2f}")

    cursor.execute("SELECT AVG(q_ld) FROM Reads WHERE q_ld IS NOT NULL")
    avg_qld = cursor.fetchone()[0]
    if avg_qld:
        print(f"  Average Q_ld: {avg_qld:.2f}")

    cursor.execute("SELECT AVG(ed) FROM Reads WHERE ed IS NOT NULL")
    avg_ed = cursor.fetchone()[0]
    if avg_ed:
        print(f"  Average edit distance: {avg_ed:.1f}")

    conn.close()

    print(f"\nDone! Database: {args.db}")


if __name__ == "__main__":
    main()
