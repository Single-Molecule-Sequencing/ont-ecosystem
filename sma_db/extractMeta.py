#!/usr/bin/env python3
"""
extractMeta.py - Metadata Extraction Script

Generates a lightweight metadata summary from POD5 files using either
the pod5 CLI or Python library for efficient I/O.

Usage:
    python extractMeta.py --exp-id <exp_id> [--input-dir Input/]

    # Or with explicit paths
    python extractMeta.py --pod5 <pod5_dir> --output <output.tsv>

Output:
    Input/{exp_id}_summary.tsv with columns: read_id, end_reason, forced
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Optional POD5 support
try:
    import pod5
    HAS_POD5 = True
except ImportError:
    HAS_POD5 = False


def extract_via_cli(pod5_dir: Path, output_path: Path) -> int:
    """
    Extract metadata using pod5 CLI tool.

    Returns number of reads extracted.
    """
    pod5_files = list(pod5_dir.glob("*.pod5"))
    if not pod5_files:
        print(f"Error: No POD5 files found in {pod5_dir}")
        return 0

    # Build file list for pod5 view
    file_args = [str(f) for f in pod5_files]

    cmd = [
        "pod5", "view",
        *file_args,
        "--include", "read_id,end_reason,end_reason_forced",
        "--output", str(output_path)
    ]

    print(f"Extracting metadata from {len(pod5_files)} POD5 files...")
    print(f"Command: pod5 view ... --include read_id,end_reason,end_reason_forced --output {output_path}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        # Count lines in output
        with open(output_path, 'r') as f:
            line_count = sum(1 for _ in f) - 1  # Subtract header

        print(f"Extracted {line_count:,} read metadata records")
        return line_count

    except subprocess.CalledProcessError as e:
        print(f"Error running pod5 CLI: {e}")
        print(f"stderr: {e.stderr}")
        return 0
    except FileNotFoundError:
        print("Error: pod5 CLI not found. Install with: pip install pod5")
        return 0


def extract_via_library(pod5_dir: Path, output_path: Path, max_reads: Optional[int] = None) -> int:
    """
    Extract metadata using pod5 Python library.

    Args:
        pod5_dir: Directory containing POD5 files
        output_path: Output TSV file path
        max_reads: Maximum reads to extract (None for all)

    Returns number of reads extracted.
    """
    if not HAS_POD5:
        print("Error: pod5 library not available. Install with: pip install pod5")
        return 0

    pod5_files = sorted(pod5_dir.glob("*.pod5"))
    if not pod5_files:
        print(f"Error: No POD5 files found in {pod5_dir}")
        return 0

    print(f"Extracting metadata from {len(pod5_files)} POD5 files...")

    read_count = 0

    with open(output_path, 'w') as out:
        # Write header
        out.write("read_id\tend_reason\tforced\n")

        for pod5_file in pod5_files:
            print(f"  Processing: {pod5_file.name}")

            try:
                with pod5.Reader(pod5_file) as reader:
                    for read in reader.reads():
                        read_id = str(read.read_id)

                        # Get end reason
                        if hasattr(read, 'end_reason'):
                            er = read.end_reason
                            if hasattr(er, 'name'):
                                end_reason = er.name
                            else:
                                end_reason = str(er)
                        else:
                            end_reason = "unknown"

                        # Get forced status
                        if hasattr(read, 'end_reason_forced'):
                            forced = 1 if read.end_reason_forced else 0
                        else:
                            forced = 0

                        out.write(f"{read_id}\t{end_reason}\t{forced}\n")
                        read_count += 1

                        if max_reads and read_count >= max_reads:
                            print(f"  Reached max_reads limit ({max_reads})")
                            break

                        if read_count % 100000 == 0:
                            print(f"    Processed {read_count:,} reads...")

            except Exception as e:
                print(f"  Warning: Error reading {pod5_file}: {e}")

            if max_reads and read_count >= max_reads:
                break

    print(f"Extracted {read_count:,} read metadata records")
    return read_count


def main():
    parser = argparse.ArgumentParser(
        description="Extract metadata from POD5 files for SMA pipeline"
    )
    parser.add_argument(
        "--exp-id", "-e",
        type=str,
        help="Experiment ID (used with --input-dir)"
    )
    parser.add_argument(
        "--input-dir", "-i",
        type=Path,
        default=Path("Input"),
        help="Input directory with symlinks (default: ./Input)"
    )
    parser.add_argument(
        "--pod5", "-p",
        type=Path,
        help="Direct path to POD5 directory"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output TSV file path"
    )
    parser.add_argument(
        "--use-cli",
        action="store_true",
        help="Use pod5 CLI instead of Python library"
    )
    parser.add_argument(
        "--max-reads", "-n",
        type=int,
        help="Maximum number of reads to extract (for subsampling)"
    )

    args = parser.parse_args()

    # Resolve paths
    if args.pod5:
        pod5_dir = args.pod5
    elif args.exp_id:
        pod5_dir = args.input_dir / f"{args.exp_id}_pod5"
    else:
        parser.error("Either --exp-id or --pod5 is required")

    if args.output:
        output_path = args.output
    elif args.exp_id:
        output_path = args.input_dir / f"{args.exp_id}_summary.tsv"
    else:
        output_path = Path("metadata_summary.tsv")

    # Validate
    if not pod5_dir.exists():
        raise FileNotFoundError(f"POD5 directory not found: {pod5_dir}")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"POD5 Metadata Extraction")
    print(f"=" * 50)
    print(f"POD5 directory: {pod5_dir}")
    print(f"Output file: {output_path}")
    if args.max_reads:
        print(f"Max reads: {args.max_reads:,}")
    print()

    # Extract
    if args.use_cli:
        count = extract_via_cli(pod5_dir, output_path)
    else:
        count = extract_via_library(pod5_dir, output_path, args.max_reads)

    if count > 0:
        print(f"\nMetadata extracted to: {output_path}")
        print(f"Total reads: {count:,}")
    else:
        print("\nNo metadata extracted.")
        sys.exit(1)


if __name__ == "__main__":
    main()
