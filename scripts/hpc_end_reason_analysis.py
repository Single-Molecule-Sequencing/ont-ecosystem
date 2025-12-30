#!/usr/bin/env python3
"""
End Reason Analysis Script for HPC
===================================
Analyzes POD5 files to extract end_reason distributions.

Usage:
    python3 hpc_end_reason_analysis.py <pod5_dir> <output_json> [--experiment-id EXP_ID]

Output JSON structure:
{
    "experiment_id": "exp-xxx",
    "pod5_dir": "/path/to/pod5",
    "timestamp": "2025-12-30T...",
    "total_reads": 12345,
    "end_reason_counts": {
        "signal_positive": 11000,
        "unblock_mux_change": 1000,
        ...
    },
    "end_reason_percentages": {
        "signal_positive": 89.1,
        ...
    },
    "quality_metrics": {
        "mean_qscore": 15.2,
        "median_qscore": 16.1,
        ...
    },
    "length_metrics": {
        "mean_length": 4500,
        "n50": 5200,
        ...
    }
}
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

def analyze_pod5_directory(pod5_dir, experiment_id=None):
    """Analyze all POD5 files in directory for end_reason distribution."""

    try:
        import pod5
    except ImportError:
        print("ERROR: pod5 library not installed. Run: pip install pod5", file=sys.stderr)
        sys.exit(1)

    try:
        import numpy as np
    except ImportError:
        np = None
        print("WARNING: numpy not installed, some metrics will be unavailable", file=sys.stderr)

    pod5_path = Path(pod5_dir)
    pod5_files = list(pod5_path.glob("*.pod5"))

    if not pod5_files:
        # Check subdirectories
        for subdir in ['pod5_pass', 'pass', 'pod5']:
            subpath = pod5_path / subdir
            if subpath.exists():
                pod5_files = list(subpath.glob("*.pod5"))
                if pod5_files:
                    pod5_path = subpath
                    break

    if not pod5_files:
        return {
            "experiment_id": experiment_id or "unknown",
            "pod5_dir": str(pod5_dir),
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": "No POD5 files found",
            "total_reads": 0
        }

    print(f"Analyzing {len(pod5_files)} POD5 files in {pod5_path}")

    # Collect end_reason data
    end_reason_counts = Counter()
    qscores = []
    lengths = []
    total_reads = 0

    for i, pod5_file in enumerate(pod5_files):
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/{len(pod5_files)} files")

        try:
            with pod5.Reader(pod5_file) as reader:
                for read in reader.reads():
                    total_reads += 1

                    # Get end_reason
                    end_reason = read.end_reason.name if hasattr(read, 'end_reason') else 'unknown'
                    end_reason_counts[end_reason] += 1

                    # Get quality score if available
                    if hasattr(read, 'run_info') and hasattr(read.run_info, 'sample_rate'):
                        pass  # Could compute from signal

                    # Track read metadata
                    if hasattr(read, 'num_samples') and hasattr(read, 'run_info'):
                        sample_rate = read.run_info.sample_rate
                        if sample_rate > 0:
                            duration_sec = read.num_samples / sample_rate
                            # Estimate length from duration (rough approximation)
                            estimated_bases = int(duration_sec * 450)  # ~450 bases/sec typical
                            lengths.append(estimated_bases)

        except Exception as e:
            print(f"  Warning: Error reading {pod5_file.name}: {e}", file=sys.stderr)
            continue

    # Calculate percentages
    end_reason_pcts = {}
    if total_reads > 0:
        for reason, count in end_reason_counts.items():
            end_reason_pcts[reason] = round(100.0 * count / total_reads, 2)

    # Calculate length metrics
    length_metrics = {}
    if lengths and np is not None:
        lengths_arr = np.array(lengths)
        length_metrics = {
            "mean_length": int(np.mean(lengths_arr)),
            "median_length": int(np.median(lengths_arr)),
            "min_length": int(np.min(lengths_arr)),
            "max_length": int(np.max(lengths_arr)),
            "n50": int(calculate_n50(lengths_arr)) if len(lengths_arr) > 0 else 0
        }

    result = {
        "experiment_id": experiment_id or "unknown",
        "pod5_dir": str(pod5_path),
        "timestamp": datetime.now().isoformat(),
        "status": "success",
        "total_reads": total_reads,
        "pod5_file_count": len(pod5_files),
        "end_reason_counts": dict(end_reason_counts),
        "end_reason_percentages": end_reason_pcts,
        "length_metrics": length_metrics
    }

    return result


def calculate_n50(lengths):
    """Calculate N50 from array of lengths."""
    import numpy as np
    sorted_lengths = np.sort(lengths)[::-1]
    cumsum = np.cumsum(sorted_lengths)
    total = cumsum[-1]
    n50_idx = np.searchsorted(cumsum, total / 2)
    return sorted_lengths[min(n50_idx, len(sorted_lengths) - 1)]


def main():
    parser = argparse.ArgumentParser(description="Analyze POD5 files for end_reason distribution")
    parser.add_argument("pod5_dir", help="Directory containing POD5 files")
    parser.add_argument("output_json", help="Output JSON file path")
    parser.add_argument("--experiment-id", "-e", help="Experiment ID for labeling")

    args = parser.parse_args()

    print("=" * 60)
    print("END REASON ANALYSIS")
    print(f"POD5 directory: {args.pod5_dir}")
    print(f"Output: {args.output_json}")
    print("=" * 60)

    result = analyze_pod5_directory(args.pod5_dir, args.experiment_id)

    # Save results
    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    # Print summary
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Status: {result.get('status', 'unknown')}")
    print(f"Total reads: {result.get('total_reads', 0):,}")

    if result.get('status') == 'success':
        print("\nEnd Reason Distribution:")
        for reason, pct in sorted(result.get('end_reason_percentages', {}).items(),
                                   key=lambda x: -x[1]):
            count = result.get('end_reason_counts', {}).get(reason, 0)
            print(f"  {reason:35} {pct:6.2f}% ({count:,} reads)")

    print(f"\nResults saved to: {args.output_json}")


if __name__ == "__main__":
    main()
