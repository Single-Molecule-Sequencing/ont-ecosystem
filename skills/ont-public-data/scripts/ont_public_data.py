#!/usr/bin/env python3
"""
ONT Public Data - Stream and analyze public ONT datasets from S3.

This tool discovers, streams, and analyzes public Oxford Nanopore datasets
from the ONT Open Data S3 bucket without requiring full file downloads.

Usage:
    ont_public_data.py list [--filter PATTERN]
    ont_public_data.py discover DATASET [--json OUTPUT]
    ont_public_data.py analyze DATASET [--max-reads N] [--max-experiments N] [--output DIR]
    ont_public_data.py analyze-all [--datasets LIST] [--output DIR]
    ont_public_data.py report OUTPUT_DIR [--format FORMAT]
"""

import argparse
import subprocess
import sys
import os
import json
from pathlib import Path
from datetime import datetime
from collections import Counter

# Try to import optional dependencies
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# Constants
S3_BUCKET = "s3://ont-open-data"
AWS_CMD = os.path.expanduser("~/.local/bin/aws")
DEFAULT_OUTPUT_DIR = Path.home() / "ont_public_analysis"
DEFAULT_MAX_READS = 50000


# =============================================================================
# Q-score Utilities (Phred scale - MUST average in probability space)
# =============================================================================
# IMPORTANT: Q-scores are logarithmic and cannot be averaged directly.
# Must convert to probability, average, then convert back.

import math

def _mean_qscore(qscores):
    """
    Calculate mean Q-score correctly via probability space.

    Q-scores are logarithmic (Phred scale), so we MUST:
    1. Convert each Q to error probability: P = 10^(-Q/10)
    2. Average the probabilities
    3. Convert back to Q-score: Q = -10 * log10(P_avg)

    Direct averaging of Q-scores is INCORRECT.
    """
    if not qscores:
        return 0.0
    if HAS_NUMPY:
        probs = np.power(10, -np.array(qscores) / 10)
        mean_prob = np.mean(probs)
    else:
        probs = [10 ** (-q / 10) for q in qscores]
        mean_prob = sum(probs) / len(probs)
    if mean_prob <= 0:
        return 60.0  # Cap at Q60
    return -10 * math.log10(mean_prob)


def run_aws_cmd(args, capture=True):
    """Run AWS CLI command with no-sign-request."""
    cmd = [AWS_CMD] + args + ["--no-sign-request"]
    if capture:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout, result.stderr, result.returncode
    else:
        return subprocess.run(cmd)


def list_s3_path(path):
    """List contents of S3 path."""
    stdout, _, rc = run_aws_cmd(["s3", "ls", path])
    if rc != 0:
        return []
    items = []
    for line in stdout.strip().split('\n'):
        if line.strip():
            parts = line.split()
            if parts:
                items.append(parts[-1])
    return items


def get_s3_file_size(s3_path):
    """Get size of S3 file."""
    stdout, _, rc = run_aws_cmd(["s3", "ls", s3_path])
    if rc == 0 and stdout.strip():
        parts = stdout.strip().split()
        if len(parts) >= 3:
            try:
                return int(parts[2])
            except ValueError:
                pass
    return None


def stream_s3_file_head(s3_path, max_bytes=50_000_000):
    """Stream first N bytes of an S3 file using byte range."""
    https_url = s3_path.replace("s3://", "https://").replace(
        "ont-open-data", "ont-open-data.s3.amazonaws.com")
    cmd = ["curl", "-s", "-r", f"0-{max_bytes}", https_url]
    result = subprocess.run(cmd, capture_output=True)
    return result.stdout


def parse_sequencing_summary(data, max_reads=DEFAULT_MAX_READS):
    """Parse sequencing summary data and extract stats."""
    lines = data.decode('utf-8', errors='replace').strip().split('\n')
    if not lines:
        return None

    header = lines[0].split('\t')
    col_idx = {col: i for i, col in enumerate(header)}

    # Handle alternative column names
    alt_mapping = {
        'sequence_length_template': 'sequence_length',
        'mean_qscore_template': 'mean_qscore'
    }
    for old, new in alt_mapping.items():
        if old not in col_idx and new in col_idx:
            col_idx[old] = col_idx[new]

    stats = {
        'read_lengths': [],
        'qscores': [],
        'passes_filtering': [],
        'end_reasons': Counter(),
        'channels': set(),
        'durations': []
    }

    read_count = 0
    for line in lines[1:]:
        if read_count >= max_reads:
            break

        parts = line.split('\t')
        if len(parts) < len(header):
            continue

        try:
            if 'sequence_length_template' in col_idx:
                length = int(float(parts[col_idx['sequence_length_template']]))
                stats['read_lengths'].append(length)

            if 'mean_qscore_template' in col_idx:
                qscore = float(parts[col_idx['mean_qscore_template']])
                stats['qscores'].append(qscore)

            if 'passes_filtering' in col_idx:
                pf = parts[col_idx['passes_filtering']].lower() in ('true', '1', 'pass')
                stats['passes_filtering'].append(pf)

            if 'end_reason' in col_idx:
                end_reason = parts[col_idx['end_reason']]
                stats['end_reasons'][end_reason] += 1

            if 'channel' in col_idx:
                stats['channels'].add(int(parts[col_idx['channel']]))

            if 'duration' in col_idx:
                duration = float(parts[col_idx['duration']])
                stats['durations'].append(duration)

            read_count += 1
        except (ValueError, IndexError):
            continue

    stats['total_reads'] = read_count
    stats['channels'] = len(stats['channels'])
    return stats


def stream_bam_reads(s3_path, max_reads=DEFAULT_MAX_READS):
    """Stream reads from a BAM file using samtools."""
    https_url = s3_path.replace("s3://", "https://").replace(
        "ont-open-data", "ont-open-data.s3.amazonaws.com")

    cmd = f"samtools view {https_url} 2>/dev/null | head -n {max_reads}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode != 0 or not result.stdout.strip():
        return None

    stats = {
        'read_lengths': [],
        'qscores': [],
        'mapping_qualities': [],
        'flags': Counter()
    }

    for line in result.stdout.strip().split('\n'):
        if not line or line.startswith('@'):
            continue

        parts = line.split('\t')
        if len(parts) < 11:
            continue

        try:
            flag = int(parts[1])
            mapq = int(parts[4])
            seq = parts[9]
            qual = parts[10]

            stats['read_lengths'].append(len(seq))
            stats['mapping_qualities'].append(mapq)

            if qual != '*':
                qscores = [ord(c) - 33 for c in qual]
                mean_q = _mean_qscore(qscores)  # Correct: average in probability space
                stats['qscores'].append(mean_q)

            if flag & 4:
                stats['flags']['unmapped'] += 1
            else:
                stats['flags']['mapped'] += 1

        except (ValueError, IndexError):
            continue

    stats['total_reads'] = len(stats['read_lengths'])
    return stats


def compute_statistics(stats):
    """Compute summary statistics from parsed data."""
    result = {
        'total_reads_sampled': stats.get('total_reads', 0),
        'total_bases': sum(stats.get('read_lengths', [])),
    }

    if stats.get('read_lengths'):
        lengths = sorted(stats['read_lengths'], reverse=True)
        result['mean_read_length'] = sum(lengths) / len(lengths)
        result['median_read_length'] = lengths[len(lengths) // 2]
        result['max_read_length'] = max(lengths)
        result['min_read_length'] = min(lengths)

        # N50 calculation
        total = sum(lengths)
        cumsum = 0
        for l in lengths:
            cumsum += l
            if cumsum >= total / 2:
                result['n50'] = l
                break

    if stats.get('qscores'):
        qscores = stats['qscores']
        result['mean_qscore'] = _mean_qscore(qscores)  # Correct: average in probability space
        result['median_qscore'] = sorted(qscores)[len(qscores) // 2]
        result['q10_reads'] = sum(1 for q in qscores if q >= 10)
        result['q20_reads'] = sum(1 for q in qscores if q >= 20)
        result['q30_reads'] = sum(1 for q in qscores if q >= 30)

    if stats.get('passes_filtering'):
        result['pass_reads'] = sum(stats['passes_filtering'])
        result['fail_reads'] = len(stats['passes_filtering']) - result['pass_reads']
        result['pass_rate'] = result['pass_reads'] / len(stats['passes_filtering']) * 100

    if stats.get('end_reasons'):
        result['end_reasons'] = dict(stats['end_reasons'])
        total_er = sum(stats['end_reasons'].values())
        result['end_reason_percentages'] = {
            k: v/total_er*100 for k, v in stats['end_reasons'].items()
        }

    if stats.get('durations'):
        result['mean_duration'] = sum(stats['durations']) / len(stats['durations'])

    if 'channels' in stats:
        result['active_channels'] = stats['channels']

    if stats.get('mapping_qualities'):
        mq = stats['mapping_qualities']
        result['mean_mapq'] = sum(mq) / len(mq)
        result['mapq_60_reads'] = sum(1 for m in mq if m >= 60)

    return result


def generate_plots(stats, summary, output_dir, experiment_name):
    """Generate comprehensive plots for the experiment."""
    if not HAS_MATPLOTLIB:
        return []

    plots_dir = output_dir / "plots"
    plots_dir.mkdir(exist_ok=True)

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle(f'{experiment_name} - Read Statistics (n={stats.get("total_reads", 0):,})', fontsize=14)

    # 1. Read length distribution
    ax = axes[0, 0]
    if stats.get('read_lengths'):
        lengths = stats['read_lengths']
        if HAS_NUMPY:
            bins = np.logspace(np.log10(max(1, min(lengths))), np.log10(max(lengths)), 50)
            ax.hist(lengths, bins=bins, edgecolor='black', alpha=0.7, color='steelblue')
            ax.set_xscale('log')
        else:
            ax.hist(lengths, bins=50, edgecolor='black', alpha=0.7, color='steelblue')
        ax.axvline(summary.get('n50', 0), color='red', linestyle='--',
                  label=f'N50: {summary.get("n50", 0):,}')
        ax.axvline(summary.get('mean_read_length', 0), color='green', linestyle='--',
                  label=f'Mean: {summary.get("mean_read_length", 0):,.0f}')
        ax.set_xlabel('Read Length (bp)')
        ax.set_ylabel('Count')
        ax.set_title('Read Length Distribution')
        ax.legend(fontsize=8)

    # 2. Q-score distribution
    ax = axes[0, 1]
    if stats.get('qscores'):
        ax.hist(stats['qscores'], bins=50, edgecolor='black', alpha=0.7, color='forestgreen')
        ax.axvline(10, color='orange', linestyle='--', alpha=0.7, label='Q10')
        ax.axvline(20, color='red', linestyle='--', alpha=0.7, label='Q20')
        ax.axvline(summary.get('mean_qscore', 0), color='blue', linestyle='-',
                  label=f'Mean: {summary.get("mean_qscore", 0):.1f}')
        ax.set_xlabel('Mean Q-score')
        ax.set_ylabel('Count')
        ax.set_title('Quality Score Distribution')
        ax.legend(fontsize=8)

    # 3. End reason pie chart
    ax = axes[0, 2]
    if stats.get('end_reasons'):
        labels, sizes = [], []
        colors = ['#2ecc71', '#e74c3c', '#3498db', '#f39c12', '#9b59b6', '#1abc9c']
        for reason, count in sorted(stats['end_reasons'].items(), key=lambda x: -x[1])[:6]:
            pct = count / sum(stats['end_reasons'].values()) * 100
            labels.append(f'{reason}\n({pct:.1f}%)')
            sizes.append(count)
        ax.pie(sizes, labels=labels, colors=colors[:len(sizes)], startangle=90)
        ax.set_title('End Reason Distribution')
    else:
        ax.text(0.5, 0.5, 'No end reason data', ha='center', va='center', transform=ax.transAxes)
        ax.set_title('End Reason Distribution')

    # 4. Length vs Q-score scatter
    ax = axes[1, 0]
    if stats.get('read_lengths') and stats.get('qscores'):
        n_sample = min(5000, len(stats['read_lengths']))
        if HAS_NUMPY and len(stats['read_lengths']) == len(stats['qscores']):
            idx = np.random.choice(len(stats['read_lengths']), n_sample, replace=False)
            lengths_sample = [stats['read_lengths'][i] for i in idx]
            qscores_sample = [stats['qscores'][i] for i in idx]
            ax.scatter(lengths_sample, qscores_sample, alpha=0.3, s=1, c='steelblue')
            ax.set_xlabel('Read Length (bp)')
            ax.set_ylabel('Mean Q-score')
            ax.set_title(f'Length vs Quality (n={n_sample:,})')
            ax.set_xscale('log')
        else:
            ax.text(0.5, 0.5, 'Insufficient data', ha='center', va='center', transform=ax.transAxes)

    # 5. Cumulative yield
    ax = axes[1, 1]
    if stats.get('read_lengths'):
        sorted_lengths = sorted(stats['read_lengths'], reverse=True)
        cumsum = []
        total = 0
        for l in sorted_lengths:
            total += l
            cumsum.append(total)
        ax.plot(range(len(cumsum)), [c/1e9 for c in cumsum], color='steelblue')
        ax.axhline(summary.get('total_bases', 0)/2/1e9, color='red', linestyle='--',
                  alpha=0.7, label='50% yield')
        ax.set_xlabel('Reads (sorted by length)')
        ax.set_ylabel('Cumulative Yield (Gb)')
        ax.set_title('Cumulative Yield')
        ax.legend(fontsize=8)

    # 6. Quality thresholds bar chart
    ax = axes[1, 2]
    if 'q10_reads' in summary and stats.get('total_reads', 0) > 0:
        thresholds = ['Q10+', 'Q20+', 'Q30+']
        values = [
            summary.get('q10_reads', 0) / stats['total_reads'] * 100,
            summary.get('q20_reads', 0) / stats['total_reads'] * 100,
            summary.get('q30_reads', 0) / stats['total_reads'] * 100
        ]
        bars = ax.bar(thresholds, values, color=['#3498db', '#2ecc71', '#e74c3c'])
        ax.set_ylabel('Percentage of Reads')
        ax.set_title('Reads Above Quality Thresholds')
        ax.set_ylim(0, 100)
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f'{val:.1f}%',
                   ha='center', va='bottom', fontsize=10)

    plt.tight_layout()
    plot_path = plots_dir / f"{experiment_name}_summary.png"
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()

    return [str(plot_path)]


def discover_experiments(dataset):
    """Discover all experiments in a dataset."""
    experiments = []

    # Check for flowcells structure (sequencing summary data)
    flowcells_path = f"{S3_BUCKET}/{dataset}/flowcells/"
    samples = list_s3_path(flowcells_path)

    for sample in samples:
        if sample.endswith('/'):
            sample = sample[:-1]
        sample_path = f"{flowcells_path}{sample}/"
        flowcells = list_s3_path(sample_path)

        for fc in flowcells:
            if fc.endswith('/'):
                fc = fc[:-1]
            experiments.append({
                'dataset': dataset,
                'sample': sample,
                'flowcell': fc,
                'type': 'sequencing_summary'
            })

    # Check for basecalling structure (BAM data)
    if not experiments:
        basecall_path = f"{S3_BUCKET}/{dataset}/basecalling/"
        items = list_s3_path(basecall_path)

        for item in items:
            if item.endswith('/'):
                item = item[:-1]
                sub_path = f"{basecall_path}{item}/"
                sub_items = list_s3_path(sub_path)

                for sub in sub_items:
                    if sub.endswith('.bam'):
                        experiments.append({
                            'dataset': dataset,
                            'sample': item,
                            'bam_file': f"basecalling/{item}/{sub}",
                            'type': 'bam'
                        })
                    elif sub.endswith('/'):
                        sub = sub[:-1]
                        files = list_s3_path(f"{sub_path}{sub}/")
                        for f in files:
                            if f.endswith('.bam'):
                                experiments.append({
                                    'dataset': dataset,
                                    'sample': f"{item}_{sub}",
                                    'bam_file': f"basecalling/{item}/{sub}/{f}",
                                    'type': 'bam'
                                })

    return experiments


def analyze_sequencing_summary_experiment(exp, output_dir, max_reads):
    """Analyze an experiment using sequencing summary."""
    experiment_name = f"{exp['dataset']}_{exp['sample']}_{exp['flowcell']}"
    print(f"\nAnalyzing: {experiment_name}")

    base_path = f"{S3_BUCKET}/{exp['dataset']}/flowcells/{exp['sample']}/{exp['flowcell']}/"
    files = list_s3_path(base_path)

    summary_file = None
    for f in files:
        if 'sequencing_summary' in f and f.endswith('.txt'):
            summary_file = f
            break

    if not summary_file:
        print(f"  No sequencing summary found")
        return None

    summary_path = f"{base_path}{summary_file}"
    print(f"  Streaming: {summary_path}")

    data = stream_s3_file_head(summary_path, 30_000_000)
    print(f"  Downloaded {len(data):,} bytes")

    stats = parse_sequencing_summary(data, max_reads)
    if not stats or stats['total_reads'] == 0:
        print(f"  Failed to parse data")
        return None

    print(f"  Parsed {stats['total_reads']:,} reads")

    summary = compute_statistics(stats)
    summary['experiment_name'] = experiment_name
    summary['dataset'] = exp['dataset']
    summary['sample'] = exp['sample']
    summary['flowcell'] = exp['flowcell']
    summary['source'] = summary_path
    summary['analysis_date'] = datetime.now().isoformat()
    summary['data_type'] = 'sequencing_summary'

    plots = generate_plots(stats, summary, output_dir, experiment_name)
    summary['plots'] = plots

    summaries_dir = output_dir / "summaries"
    summaries_dir.mkdir(exist_ok=True)
    summary_json_path = summaries_dir / f"{experiment_name}_summary.json"
    with open(summary_json_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"  Saved: {summary_json_path}")

    return summary


def analyze_bam_experiment(exp, output_dir, max_reads):
    """Analyze an experiment using BAM streaming."""
    experiment_name = f"{exp['dataset']}_{exp['sample']}_{Path(exp['bam_file']).stem}"
    print(f"\nAnalyzing: {experiment_name}")

    s3_path = f"{S3_BUCKET}/{exp['dataset']}/{exp['bam_file']}"
    print(f"  Streaming BAM: {s3_path}")

    stats = stream_bam_reads(s3_path, max_reads)
    if not stats or stats['total_reads'] == 0:
        print(f"  Failed to parse BAM data")
        return None

    print(f"  Parsed {stats['total_reads']:,} reads")

    summary = compute_statistics(stats)
    summary['experiment_name'] = experiment_name
    summary['dataset'] = exp['dataset']
    summary['sample'] = exp['sample']
    summary['source'] = s3_path
    summary['analysis_date'] = datetime.now().isoformat()
    summary['data_type'] = 'bam'

    plots = generate_plots(stats, summary, output_dir, experiment_name)
    summary['plots'] = plots

    summaries_dir = output_dir / "summaries"
    summaries_dir.mkdir(exist_ok=True)
    summary_json_path = summaries_dir / f"{experiment_name}_summary.json"
    with open(summary_json_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"  Saved: {summary_json_path}")

    return summary


# CLI Commands

def cmd_list(args):
    """List available datasets."""
    print("Listing ONT Open Data datasets...")
    items = list_s3_path(f"{S3_BUCKET}/")

    datasets = []
    for item in items:
        if item.endswith('/'):
            name = item[:-1]
            if args.filter and args.filter not in name:
                continue
            datasets.append(name)

    print(f"\nFound {len(datasets)} datasets:\n")
    for ds in sorted(datasets):
        print(f"  - {ds}")

    return 0


def cmd_discover(args):
    """Discover experiments in a dataset."""
    print(f"Discovering experiments in: {args.dataset}")
    experiments = discover_experiments(args.dataset)

    print(f"\nFound {len(experiments)} experiments:\n")
    for exp in experiments[:20]:
        print(f"  - {exp.get('sample', 'unknown')}/{exp.get('flowcell', exp.get('bam_file', 'unknown'))}")

    if len(experiments) > 20:
        print(f"  ... and {len(experiments) - 20} more")

    if args.json:
        with open(args.json, 'w') as f:
            json.dump(experiments, f, indent=2)
        print(f"\nSaved to: {args.json}")

    return 0


def cmd_analyze(args):
    """Analyze experiments from a dataset."""
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Analyzing dataset: {args.dataset}")
    print(f"Max reads per experiment: {args.max_reads:,}")
    print(f"Output directory: {output_dir}")

    experiments = discover_experiments(args.dataset)
    print(f"Found {len(experiments)} experiments")

    if args.max_experiments:
        experiments = experiments[:args.max_experiments]
        print(f"Limiting to {len(experiments)} experiments")

    all_summaries = []
    for exp in experiments:
        try:
            if exp.get('type') == 'bam':
                summary = analyze_bam_experiment(exp, output_dir, args.max_reads)
            else:
                summary = analyze_sequencing_summary_experiment(exp, output_dir, args.max_reads)

            if summary:
                all_summaries.append(summary)
        except Exception as e:
            print(f"  Error: {e}")

    # Save combined summary
    if all_summaries:
        combined_path = output_dir / "all_experiments_summary.json"
        with open(combined_path, 'w') as f:
            json.dump({
                'analysis_date': datetime.now().isoformat(),
                'dataset': args.dataset,
                'total_experiments': len(all_summaries),
                'max_reads_per_experiment': args.max_reads,
                'experiments': all_summaries
            }, f, indent=2)
        print(f"\nCombined summary: {combined_path}")
        print(f"Total experiments analyzed: {len(all_summaries)}")

    return 0


def cmd_report(args):
    """Generate comprehensive report."""
    output_dir = Path(args.output_dir)
    summaries_dir = output_dir / "summaries"

    experiments = []
    for json_file in sorted(summaries_dir.glob("*.json")):
        if 'all_experiments' in json_file.name:
            continue
        with open(json_file) as f:
            experiments.append(json.load(f))

    print(f"Loaded {len(experiments)} experiments")

    # Generate report
    report = []
    report.append("# ONT Public Data Analysis Report")
    report.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"\nTotal experiments: {len(experiments)}")

    by_dataset = {}
    for exp in experiments:
        ds = exp.get('dataset', 'unknown')
        if ds not in by_dataset:
            by_dataset[ds] = []
        by_dataset[ds].append(exp)

    for dataset, exps in sorted(by_dataset.items()):
        report.append(f"\n## {dataset} ({len(exps)} experiments)")

        total_reads = sum(e.get('total_reads_sampled', 0) for e in exps)
        total_bases = sum(e.get('total_bases', 0) for e in exps)
        n50s = [e.get('n50', 0) for e in exps if e.get('n50', 0) > 0]
        qscores = [e.get('mean_qscore', 0) for e in exps if e.get('mean_qscore', 0) > 0]

        report.append(f"\n- Total reads sampled: {total_reads:,}")
        report.append(f"- Total bases: {total_bases:,} ({total_bases/1e9:.2f} Gb)")
        if n50s:
            report.append(f"- Mean N50: {sum(n50s)/len(n50s):,.0f} bp")
        if qscores:
            report.append(f"- Mean Q-score: {_mean_qscore(qscores):.1f}")

    report_path = output_dir / "analysis_report.md"
    with open(report_path, 'w') as f:
        f.write('\n'.join(report))
    print(f"Report saved: {report_path}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Stream and analyze public ONT datasets from S3"
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # list command
    p_list = subparsers.add_parser('list', help='List available datasets')
    p_list.add_argument('--filter', help='Filter datasets by pattern')
    p_list.set_defaults(func=cmd_list)

    # discover command
    p_discover = subparsers.add_parser('discover', help='Discover experiments in a dataset')
    p_discover.add_argument('dataset', help='Dataset name')
    p_discover.add_argument('--json', help='Output JSON file')
    p_discover.set_defaults(func=cmd_discover)

    # analyze command
    p_analyze = subparsers.add_parser('analyze', help='Analyze experiments from a dataset')
    p_analyze.add_argument('dataset', help='Dataset name')
    p_analyze.add_argument('--max-reads', type=int, default=DEFAULT_MAX_READS,
                          help=f'Max reads per experiment (default: {DEFAULT_MAX_READS})')
    p_analyze.add_argument('--max-experiments', type=int,
                          help='Max experiments to analyze')
    p_analyze.add_argument('--output', '-o', default=str(DEFAULT_OUTPUT_DIR),
                          help=f'Output directory (default: {DEFAULT_OUTPUT_DIR})')
    p_analyze.set_defaults(func=cmd_analyze)

    # report command
    p_report = subparsers.add_parser('report', help='Generate analysis report')
    p_report.add_argument('output_dir', help='Directory containing analysis results')
    p_report.add_argument('--format', choices=['markdown', 'html'], default='markdown')
    p_report.set_defaults(func=cmd_report)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
