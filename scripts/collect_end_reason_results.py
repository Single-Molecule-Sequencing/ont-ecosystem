#!/usr/bin/env python3
"""
Collect End Reason Results
==========================
Consolidates all individual experiment results into a single dataset.

Usage:
    python3 collect_end_reason_results.py [--results-dir DIR] [--output FILE]

Run this after all SLURM array jobs complete.
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path


def collect_results(results_dir, output_file):
    """Collect all JSON results into a consolidated dataset."""

    results_path = Path(results_dir)
    json_files = list(results_path.glob("*_end_reason.json"))

    print(f"Found {len(json_files)} result files in {results_dir}")

    all_results = []
    success_count = 0
    error_count = 0
    total_reads = 0

    for json_file in sorted(json_files):
        try:
            with open(json_file) as f:
                data = json.load(f)

            if data.get('status') == 'success':
                success_count += 1
                total_reads += data.get('total_reads', 0)
            else:
                error_count += 1

            all_results.append(data)

        except Exception as e:
            print(f"  Warning: Error reading {json_file.name}: {e}")
            error_count += 1

    # Create consolidated output
    consolidated = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "source_dir": str(results_dir),
            "total_experiments": len(all_results),
            "successful": success_count,
            "errors": error_count,
            "total_reads_analyzed": total_reads
        },
        "experiments": all_results
    }

    # Calculate aggregate statistics
    if success_count > 0:
        # Aggregate end_reason percentages
        end_reason_totals = {}
        for exp in all_results:
            if exp.get('status') != 'success':
                continue
            counts = exp.get('end_reason_counts', {})
            for reason, count in counts.items():
                end_reason_totals[reason] = end_reason_totals.get(reason, 0) + count

        # Calculate overall percentages
        total = sum(end_reason_totals.values())
        if total > 0:
            consolidated["aggregate_end_reasons"] = {
                reason: {
                    "count": count,
                    "percentage": round(100.0 * count / total, 2)
                }
                for reason, count in sorted(end_reason_totals.items(), key=lambda x: -x[1])
            }

    # Save consolidated results
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(consolidated, f, indent=2)

    # Also create a CSV for easy analysis
    csv_path = output_path.with_suffix('.csv')
    with open(csv_path, 'w') as f:
        # Header
        all_reasons = set()
        for exp in all_results:
            all_reasons.update(exp.get('end_reason_percentages', {}).keys())
        all_reasons = sorted(all_reasons)

        header = ['experiment_id', 'status', 'total_reads', 'pod5_files'] + \
                 [f'{r}_pct' for r in all_reasons] + \
                 [f'{r}_count' for r in all_reasons]
        f.write(','.join(header) + '\n')

        # Data rows
        for exp in all_results:
            row = [
                exp.get('experiment_id', ''),
                exp.get('status', ''),
                str(exp.get('total_reads', 0)),
                str(exp.get('pod5_file_count', 0))
            ]
            pcts = exp.get('end_reason_percentages', {})
            counts = exp.get('end_reason_counts', {})
            for r in all_reasons:
                row.append(str(pcts.get(r, 0)))
            for r in all_reasons:
                row.append(str(counts.get(r, 0)))
            f.write(','.join(row) + '\n')

    print(f"\n{'=' * 60}")
    print("COLLECTION COMPLETE")
    print('=' * 60)
    print(f"Successful experiments: {success_count}")
    print(f"Errors: {error_count}")
    print(f"Total reads analyzed: {total_reads:,}")
    print(f"\nConsolidated JSON: {output_path}")
    print(f"CSV export: {csv_path}")

    if 'aggregate_end_reasons' in consolidated:
        print("\nAggregate End Reason Distribution:")
        for reason, data in consolidated['aggregate_end_reasons'].items():
            print(f"  {reason:35} {data['percentage']:6.2f}% ({data['count']:,})")

    return consolidated


def main():
    parser = argparse.ArgumentParser(description="Collect end_reason analysis results")
    parser.add_argument("--results-dir", "-r",
                        default="/nfs/turbo/umms-atheylab/end_reason_results",
                        help="Directory containing result JSON files")
    parser.add_argument("--output", "-o",
                        default="consolidated_end_reasons.json",
                        help="Output file path")

    args = parser.parse_args()

    collect_results(args.results_dir, args.output)


if __name__ == "__main__":
    main()
