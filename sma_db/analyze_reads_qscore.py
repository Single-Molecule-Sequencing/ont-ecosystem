#!/usr/bin/env python3
"""
SMA-seq Read Quality Analysis

Analyzes reads from BAM files with:
- Reference matching via Levenshtein edit distance (edlib)
- Per-read and per-base Q-score analysis
- Empirical vs predicted Q-score comparison
- Sequence frequency analysis

Usage:
    python analyze_reads_qscore.py --bam-dir /path/to/bam_pass --reference reference.fa --output output_dir --sample-size 100000
"""

import argparse
import sys
import os
import json
from pathlib import Path
from collections import defaultdict, Counter
import random

import numpy as np

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

try:
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not available, plots will be skipped")


def load_references(fasta_path: str) -> dict:
    """Load reference sequences from FASTA file."""
    refs = {}
    current_name = None
    current_seq = []

    with open(fasta_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('>'):
                if current_name:
                    refs[current_name] = ''.join(current_seq).upper()
                # Parse header - get first word
                header = line[1:].split()[0]
                current_name = header
                current_seq = []
            else:
                current_seq.append(line)
        if current_name:
            refs[current_name] = ''.join(current_seq).upper()

    print(f"Loaded {len(refs)} reference sequences")
    for name, seq in refs.items():
        print(f"  {name}: {len(seq)}bp")

    return refs


def find_best_reference(sequence: str, references: dict) -> tuple:
    """
    Find best matching reference using edlib.

    Returns:
        (ref_name, edit_distance, cigar, alignment)
    """
    sequence = sequence.upper()
    best_ref = None
    best_ed = float('inf')
    best_result = None

    for ref_name, ref_seq in references.items():
        result = edlib.align(sequence, ref_seq, mode="NW", task="path")
        ed = result['editDistance']

        if ed < best_ed:
            best_ed = ed
            best_ref = ref_name
            best_result = result

    return best_ref, best_ed, best_result


def compute_per_base_alignment(sequence: str, reference: str, cigar: str) -> list:
    """
    Compute per-base alignment status (match/mismatch/insertion/deletion).

    Returns list of tuples: (seq_pos, ref_pos, status, seq_base, ref_base)
    where status is 'M' (match), 'X' (mismatch), 'I' (insertion), 'D' (deletion)
    """
    alignment = []
    seq_pos = 0
    ref_pos = 0

    # Parse CIGAR-like operations from edlib
    # edlib uses: = (match), X (mismatch), I (insertion), D (deletion)
    import re
    ops = re.findall(r'(\d+)([=XIDM])', cigar)

    for length_str, op in ops:
        length = int(length_str)

        if op == '=' or op == 'M':
            # Match
            for _ in range(length):
                if seq_pos < len(sequence) and ref_pos < len(reference):
                    seq_base = sequence[seq_pos]
                    ref_base = reference[ref_pos]
                    status = 'M' if seq_base == ref_base else 'X'
                    alignment.append((seq_pos, ref_pos, status, seq_base, ref_base))
                    seq_pos += 1
                    ref_pos += 1

        elif op == 'X':
            # Mismatch (edlib specific)
            for _ in range(length):
                if seq_pos < len(sequence) and ref_pos < len(reference):
                    seq_base = sequence[seq_pos]
                    ref_base = reference[ref_pos]
                    alignment.append((seq_pos, ref_pos, 'X', seq_base, ref_base))
                    seq_pos += 1
                    ref_pos += 1

        elif op == 'I':
            # Insertion in sequence (not in reference)
            for _ in range(length):
                if seq_pos < len(sequence):
                    seq_base = sequence[seq_pos]
                    alignment.append((seq_pos, None, 'I', seq_base, '-'))
                    seq_pos += 1

        elif op == 'D':
            # Deletion from sequence (in reference)
            for _ in range(length):
                if ref_pos < len(reference):
                    ref_base = reference[ref_pos]
                    alignment.append((None, ref_pos, 'D', '-', ref_base))
                    ref_pos += 1

    return alignment


def qscore_to_prob(q: float) -> float:
    """Convert Q-score to error probability."""
    return 10 ** (-q / 10)


def prob_to_qscore(p: float) -> float:
    """Convert error probability to Q-score."""
    if p <= 0:
        return 60  # Cap at Q60
    if p >= 1:
        return 0
    return -10 * np.log10(p)


def mean_qscore_correct(qscores: list) -> float:
    """
    Compute mean Q-score correctly (via probability space).
    """
    if not qscores:
        return 0
    probs = [qscore_to_prob(q) for q in qscores]
    mean_prob = np.mean(probs)
    return prob_to_qscore(mean_prob)


def analyze_bam_files(bam_dir: str, references: dict, sample_size: int = 100000,
                      target_filter: str = None) -> dict:
    """
    Analyze BAM files and extract read statistics.

    Returns dict with tagged reads and statistics.
    """
    bam_dir = Path(bam_dir)
    bam_files = list(bam_dir.rglob("*.bam"))

    if not bam_files:
        print(f"No BAM files found in {bam_dir}")
        return {}

    print(f"Found {len(bam_files)} BAM files")

    # Collect all reads first (for sampling)
    all_reads = []

    for bam_path in bam_files:
        # Extract target from path (e.g., V04_2)
        target_from_path = bam_path.parent.name

        if target_filter and target_filter not in target_from_path:
            continue

        try:
            with pysam.AlignmentFile(str(bam_path), "rb", check_sq=False) as bam:
                for read in bam.fetch(until_eof=True):
                    if read.is_unmapped or read.query_sequence is None:
                        continue

                    # Get quality scores
                    quals = read.query_qualities
                    if quals is None:
                        continue

                    all_reads.append({
                        'name': read.query_name,
                        'sequence': read.query_sequence,
                        'qualities': list(quals),
                        'source_target': target_from_path,
                        'bam_file': str(bam_path)
                    })

        except Exception as e:
            print(f"Error reading {bam_path}: {e}")
            continue

    print(f"Total reads collected: {len(all_reads)}")

    # Subsample if needed
    if len(all_reads) > sample_size:
        print(f"Subsampling to {sample_size} reads...")
        all_reads = random.sample(all_reads, sample_size)

    # Tag each read with reference match
    print(f"Classifying {len(all_reads)} reads against {len(references)} references...")

    tagged_reads = []
    stats = {
        'total_reads': len(all_reads),
        'by_reference': defaultdict(int),
        'by_edit_distance': defaultdict(int),
        'perfect_reads': 0,
        'sequence_counts': Counter(),
        'ed_distribution': [],
        'qscore_distribution': [],
    }

    # Per-base statistics
    perbase_stats = {
        'correct_qscores': defaultdict(list),  # position -> list of qscores for correct bases
        'incorrect_qscores': defaultdict(list),  # position -> list of qscores for incorrect bases
        'all_qscores': defaultdict(list),  # position -> all qscores
    }

    for i, read in enumerate(all_reads):
        if (i + 1) % 10000 == 0:
            print(f"  Processed {i + 1}/{len(all_reads)} reads...")

        sequence = read['sequence']
        qualities = read['qualities']

        # Find best reference
        best_ref, edit_distance, result = find_best_reference(sequence, references)

        if best_ref is None:
            continue

        # Compute per-read average Q-score
        avg_qscore = mean_qscore_correct(qualities)

        # Get alignment details
        ref_seq = references[best_ref]
        cigar = result.get('cigar', '')

        # Per-base analysis if we have a CIGAR
        if cigar:
            alignment = compute_per_base_alignment(sequence, ref_seq, cigar)

            for seq_pos, ref_pos, status, seq_base, ref_base in alignment:
                if seq_pos is not None and seq_pos < len(qualities):
                    q = qualities[seq_pos]

                    if ref_pos is not None:
                        perbase_stats['all_qscores'][ref_pos].append(q)

                        if status == 'M':  # Match
                            perbase_stats['correct_qscores'][ref_pos].append(q)
                        elif status in ('X', 'I'):  # Mismatch or insertion
                            perbase_stats['incorrect_qscores'][ref_pos].append(q)

        # Tag the read
        tagged_read = {
            **read,
            'matched_reference': best_ref,
            'edit_distance': edit_distance,
            'avg_qscore': avg_qscore,
            'read_length': len(sequence),
        }
        tagged_reads.append(tagged_read)

        # Update stats
        stats['by_reference'][best_ref] += 1
        stats['by_edit_distance'][edit_distance] += 1
        stats['ed_distribution'].append(edit_distance)
        stats['qscore_distribution'].append(avg_qscore)
        stats['sequence_counts'][sequence] += 1

        if edit_distance == 0:
            stats['perfect_reads'] += 1

    # Compute sequence frequency statistics
    counts = list(stats['sequence_counts'].values())
    stats['unique_sequences'] = len(stats['sequence_counts'])
    stats['singleton_sequences'] = sum(1 for c in counts if c == 1)
    stats['multi_occurrence_sequences'] = sum(1 for c in counts if c > 1)
    stats['max_occurrence'] = max(counts) if counts else 0
    stats['mean_occurrence'] = np.mean(counts) if counts else 0

    # Compute per-base summary statistics
    max_ref_len = max(len(ref) for ref in references.values())
    perbase_summary = {
        'positions': list(range(max_ref_len)),
        'mean_qscore_all': [],
        'mean_qscore_correct': [],
        'mean_qscore_incorrect': [],
        'empirical_error_rate': [],
        'predicted_error_rate': [],
        'count_correct': [],
        'count_incorrect': [],
    }

    for pos in range(max_ref_len):
        all_q = perbase_stats['all_qscores'].get(pos, [])
        correct_q = perbase_stats['correct_qscores'].get(pos, [])
        incorrect_q = perbase_stats['incorrect_qscores'].get(pos, [])

        perbase_summary['count_correct'].append(len(correct_q))
        perbase_summary['count_incorrect'].append(len(incorrect_q))

        # Mean Q-scores
        if all_q:
            perbase_summary['mean_qscore_all'].append(mean_qscore_correct(all_q))
            perbase_summary['predicted_error_rate'].append(np.mean([qscore_to_prob(q) for q in all_q]))
        else:
            perbase_summary['mean_qscore_all'].append(np.nan)
            perbase_summary['predicted_error_rate'].append(np.nan)

        if correct_q:
            perbase_summary['mean_qscore_correct'].append(mean_qscore_correct(correct_q))
        else:
            perbase_summary['mean_qscore_correct'].append(np.nan)

        if incorrect_q:
            perbase_summary['mean_qscore_incorrect'].append(mean_qscore_correct(incorrect_q))
        else:
            perbase_summary['mean_qscore_incorrect'].append(np.nan)

        # Empirical error rate
        total = len(correct_q) + len(incorrect_q)
        if total > 0:
            perbase_summary['empirical_error_rate'].append(len(incorrect_q) / total)
        else:
            perbase_summary['empirical_error_rate'].append(np.nan)

    return {
        'tagged_reads': tagged_reads,
        'stats': stats,
        'perbase_summary': perbase_summary,
        'references': {k: len(v) for k, v in references.items()},
    }


def create_visualizations(results: dict, output_dir: str):
    """Create comprehensive visualizations."""
    if not HAS_MATPLOTLIB:
        print("Matplotlib not available, skipping visualizations")
        return

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stats = results['stats']
    perbase = results['perbase_summary']

    # Set up style - use default matplotlib style with grid
    plt.rcParams['axes.grid'] = True
    plt.rcParams['grid.alpha'] = 0.3
    plt.rcParams['figure.facecolor'] = 'white'
    plt.rcParams['axes.facecolor'] = 'white'

    # ==================== Figure 1: Overview ====================
    fig = plt.figure(figsize=(16, 12))
    gs = gridspec.GridSpec(3, 3, figure=fig)

    # 1a. Edit distance distribution
    ax1 = fig.add_subplot(gs[0, 0])
    ed_counts = sorted(stats['by_edit_distance'].items())
    eds, counts = zip(*ed_counts) if ed_counts else ([], [])
    ax1.bar(eds, counts, color='steelblue', edgecolor='black', alpha=0.7)
    ax1.set_xlabel('Edit Distance')
    ax1.set_ylabel('Read Count')
    ax1.set_title(f'Edit Distance Distribution\n(Perfect reads: {stats["perfect_reads"]:,})')
    ax1.axvline(x=0, color='green', linestyle='--', alpha=0.7, label='Perfect')

    # 1b. Per-reference read counts
    ax2 = fig.add_subplot(gs[0, 1])
    ref_counts = sorted(stats['by_reference'].items(), key=lambda x: x[1], reverse=True)
    if ref_counts:
        refs, rcounts = zip(*ref_counts)
        colors = plt.cm.tab10(np.linspace(0, 1, len(refs)))
        ax2.barh(range(len(refs)), rcounts, color=colors)
        ax2.set_yticks(range(len(refs)))
        ax2.set_yticklabels(refs, fontsize=8)
        ax2.set_xlabel('Read Count')
        ax2.set_title('Reads per Reference')
        ax2.invert_yaxis()

    # 1c. Q-score distribution
    ax3 = fig.add_subplot(gs[0, 2])
    qscores = stats['qscore_distribution']
    ax3.hist(qscores, bins=50, color='coral', edgecolor='black', alpha=0.7)
    ax3.axvline(np.mean(qscores), color='red', linestyle='--', label=f'Mean: {np.mean(qscores):.1f}')
    ax3.axvline(np.median(qscores), color='blue', linestyle='--', label=f'Median: {np.median(qscores):.1f}')
    ax3.set_xlabel('Average Q-score')
    ax3.set_ylabel('Read Count')
    ax3.set_title('Per-Read Average Q-score Distribution')
    ax3.legend()

    # 1d. Sequence occurrence frequency
    ax4 = fig.add_subplot(gs[1, 0])
    seq_counts = list(stats['sequence_counts'].values())
    max_count = min(20, max(seq_counts) if seq_counts else 1)
    bins = range(1, max_count + 2)
    ax4.hist(seq_counts, bins=bins, color='purple', edgecolor='black', alpha=0.7)
    ax4.set_xlabel('Times Observed')
    ax4.set_ylabel('Number of Unique Sequences')
    ax4.set_title(f'Sequence Occurrence Frequency\n(Singletons: {stats["singleton_sequences"]:,}, Multi: {stats["multi_occurrence_sequences"]:,})')

    # 1e. Per-base mean Q-score (all)
    ax5 = fig.add_subplot(gs[1, 1:])
    positions = perbase['positions']
    mean_q_all = perbase['mean_qscore_all']

    # Trim to valid positions
    valid_mask = ~np.isnan(mean_q_all)
    valid_positions = [p for p, v in zip(positions, valid_mask) if v]
    valid_mean_q = [q for q, v in zip(mean_q_all, valid_mask) if v]

    ax5.plot(valid_positions, valid_mean_q, 'b-', linewidth=1, alpha=0.8, label='All bases')
    ax5.fill_between(valid_positions, valid_mean_q, alpha=0.3)
    ax5.set_xlabel('Reference Position')
    ax5.set_ylabel('Mean Q-score')
    ax5.set_title('Per-Position Mean Q-score')
    ax5.set_ylim(0, 40)

    # 1f. Statistics text
    ax6 = fig.add_subplot(gs[2, 0])
    ax6.axis('off')
    stats_text = f"""
    Summary Statistics
    ==================
    Total reads: {stats['total_reads']:,}
    Perfect reads (ED=0): {stats['perfect_reads']:,} ({100*stats['perfect_reads']/stats['total_reads']:.1f}%)

    Unique sequences: {stats['unique_sequences']:,}
    Singleton sequences: {stats['singleton_sequences']:,}
    Multi-occurrence: {stats['multi_occurrence_sequences']:,}
    Max occurrence: {stats['max_occurrence']:,}

    Mean Q-score: {np.mean(qscores):.2f}
    Median Q-score: {np.median(qscores):.2f}
    Mean edit distance: {np.mean(stats['ed_distribution']):.2f}
    """
    ax6.text(0.1, 0.9, stats_text, transform=ax6.transAxes, fontsize=10,
             verticalalignment='top', fontfamily='monospace')

    # 1g. Correct vs Incorrect Q-scores
    ax7 = fig.add_subplot(gs[2, 1:])
    mean_q_correct = perbase['mean_qscore_correct']
    mean_q_incorrect = perbase['mean_qscore_incorrect']

    valid_correct = [(p, q) for p, q in zip(positions, mean_q_correct) if not np.isnan(q)]
    valid_incorrect = [(p, q) for p, q in zip(positions, mean_q_incorrect) if not np.isnan(q)]

    if valid_correct:
        pc, qc = zip(*valid_correct)
        ax7.plot(pc, qc, 'g-', linewidth=1.5, alpha=0.8, label='Correct bases')
    if valid_incorrect:
        pi, qi = zip(*valid_incorrect)
        ax7.plot(pi, qi, 'r-', linewidth=1.5, alpha=0.8, label='Incorrect bases')

    ax7.set_xlabel('Reference Position')
    ax7.set_ylabel('Mean Q-score')
    ax7.set_title('Q-score by Correctness')
    ax7.legend()
    ax7.set_ylim(0, 40)

    plt.tight_layout()
    plt.savefig(output_dir / 'overview_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()

    # ==================== Figure 2: Q-score Calibration ====================
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))

    # 2a. Empirical vs Predicted error rate
    ax = axes[0, 0]
    empirical = perbase['empirical_error_rate']
    predicted = perbase['predicted_error_rate']

    valid_emp = [(e, p) for e, p in zip(empirical, predicted) if not np.isnan(e) and not np.isnan(p)]
    if valid_emp:
        emp, pred = zip(*valid_emp)
        ax.scatter(pred, emp, alpha=0.5, s=20)
        ax.plot([0, 0.5], [0, 0.5], 'r--', label='Perfect calibration')
        ax.set_xlabel('Predicted Error Rate (from Q-score)')
        ax.set_ylabel('Empirical Error Rate')
        ax.set_title('Q-score Calibration')
        ax.legend()
        ax.set_xlim(0, max(0.1, max(pred) * 1.1))
        ax.set_ylim(0, max(0.1, max(emp) * 1.1))

    # 2b. Q-score distribution for correct vs incorrect
    ax = axes[0, 1]
    all_correct_q = []
    all_incorrect_q = []
    for pos in positions:
        all_correct_q.extend(perbase['mean_qscore_correct'])
        all_incorrect_q.extend(perbase['mean_qscore_incorrect'])

    # Actually, let's use the raw data - get from tagged_reads later
    # For now, plot the per-position averages
    if valid_correct:
        ax.hist([q for _, q in valid_correct], bins=30, alpha=0.6, label='Correct', color='green')
    if valid_incorrect:
        ax.hist([q for _, q in valid_incorrect], bins=30, alpha=0.6, label='Incorrect', color='red')
    ax.set_xlabel('Mean Q-score at Position')
    ax.set_ylabel('Count')
    ax.set_title('Q-score Distribution by Correctness')
    ax.legend()

    # 2c. Coverage by position
    ax = axes[1, 0]
    count_correct = perbase['count_correct']
    count_incorrect = perbase['count_incorrect']
    total_count = [c + i for c, i in zip(count_correct, count_incorrect)]

    valid_cov = [(p, t) for p, t in zip(positions, total_count) if t > 0]
    if valid_cov:
        pc, tc = zip(*valid_cov)
        ax.fill_between(pc, tc, alpha=0.7, color='steelblue')
        ax.set_xlabel('Reference Position')
        ax.set_ylabel('Coverage')
        ax.set_title('Coverage by Position')

    # 2d. Error rate by position
    ax = axes[1, 1]
    valid_err = [(p, e) for p, e in zip(positions, empirical) if not np.isnan(e)]
    if valid_err:
        pe, ee = zip(*valid_err)
        ax.plot(pe, ee, 'r-', linewidth=1, alpha=0.8)
        ax.fill_between(pe, ee, alpha=0.3, color='red')
        ax.set_xlabel('Reference Position')
        ax.set_ylabel('Error Rate')
        ax.set_title('Empirical Error Rate by Position')
        mean_err = np.nanmean(empirical)
        ax.axhline(mean_err, color='black', linestyle='--', label=f'Mean: {mean_err:.4f}')
        ax.legend()

    plt.tight_layout()
    plt.savefig(output_dir / 'qscore_calibration.png', dpi=150, bbox_inches='tight')
    plt.close()

    # ==================== Figure 3: Edit Distance Analysis ====================
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 3a. ED vs Q-score scatter
    ax = axes[0, 0]
    eds = stats['ed_distribution']
    qscores = stats['qscore_distribution']
    ax.scatter(qscores, eds, alpha=0.1, s=5)
    ax.set_xlabel('Average Q-score')
    ax.set_ylabel('Edit Distance')
    ax.set_title('Edit Distance vs Q-score')

    # 3b. ED distribution by reference
    ax = axes[0, 1]
    # Get ED per reference from tagged reads
    ed_by_ref = defaultdict(list)
    for read in results['tagged_reads']:
        ed_by_ref[read['matched_reference']].append(read['edit_distance'])

    ref_names = sorted(ed_by_ref.keys())
    data = [ed_by_ref[r] for r in ref_names]
    if data:
        bp = ax.boxplot(data, labels=ref_names, patch_artist=True)
        for patch, color in zip(bp['boxes'], plt.cm.tab10(np.linspace(0, 1, len(ref_names)))):
            patch.set_facecolor(color)
        ax.set_xlabel('Reference')
        ax.set_ylabel('Edit Distance')
        ax.set_title('Edit Distance by Reference')
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # 3c. Cumulative ED distribution
    ax = axes[1, 0]
    sorted_eds = sorted(eds)
    cumulative = np.arange(1, len(sorted_eds) + 1) / len(sorted_eds)
    ax.plot(sorted_eds, cumulative, 'b-', linewidth=2)
    ax.set_xlabel('Edit Distance')
    ax.set_ylabel('Cumulative Fraction')
    ax.set_title('Cumulative Edit Distance Distribution')
    ax.axhline(0.5, color='gray', linestyle='--', alpha=0.5)
    ax.axhline(0.9, color='gray', linestyle='--', alpha=0.5)

    # Find median and 90th percentile
    if eds:
        median_ed = np.median(eds)
        p90_ed = np.percentile(eds, 90)
        ax.axvline(median_ed, color='blue', linestyle='--', alpha=0.5, label=f'Median: {median_ed:.0f}')
        ax.axvline(p90_ed, color='red', linestyle='--', alpha=0.5, label=f'90th: {p90_ed:.0f}')
        ax.legend()

    # 3d. Q-score by ED bin
    ax = axes[1, 1]
    ed_qscore = defaultdict(list)
    for read in results['tagged_reads']:
        ed = read['edit_distance']
        ed_bin = min(ed, 10)  # Cap at 10+
        ed_qscore[ed_bin].append(read['avg_qscore'])

    ed_bins = sorted(ed_qscore.keys())
    means = [np.mean(ed_qscore[b]) for b in ed_bins]
    stds = [np.std(ed_qscore[b]) for b in ed_bins]

    ax.bar(ed_bins, means, yerr=stds, capsize=5, color='steelblue', alpha=0.7)
    ax.set_xlabel('Edit Distance')
    ax.set_ylabel('Mean Q-score')
    ax.set_title('Mean Q-score by Edit Distance')
    ax.set_xticks(ed_bins)
    ax.set_xticklabels([str(b) if b < 10 else '10+' for b in ed_bins])

    plt.tight_layout()
    plt.savefig(output_dir / 'edit_distance_analysis.png', dpi=150, bbox_inches='tight')
    plt.close()

    print(f"Saved visualizations to {output_dir}")


def save_results(results: dict, output_dir: str):
    """Save results to files."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save statistics as JSON
    stats_to_save = {
        'total_reads': results['stats']['total_reads'],
        'perfect_reads': results['stats']['perfect_reads'],
        'unique_sequences': results['stats']['unique_sequences'],
        'singleton_sequences': results['stats']['singleton_sequences'],
        'multi_occurrence_sequences': results['stats']['multi_occurrence_sequences'],
        'max_occurrence': results['stats']['max_occurrence'],
        'mean_edit_distance': float(np.mean(results['stats']['ed_distribution'])),
        'median_edit_distance': float(np.median(results['stats']['ed_distribution'])),
        'mean_qscore': float(np.mean(results['stats']['qscore_distribution'])),
        'median_qscore': float(np.median(results['stats']['qscore_distribution'])),
        'by_reference': dict(results['stats']['by_reference']),
        'by_edit_distance': {str(k): v for k, v in results['stats']['by_edit_distance'].items()},
        'references': results['references'],
    }

    with open(output_dir / 'statistics.json', 'w') as f:
        json.dump(stats_to_save, f, indent=2)

    # Save per-base summary as TSV
    perbase = results['perbase_summary']
    with open(output_dir / 'perbase_stats.tsv', 'w') as f:
        f.write("position\tmean_q_all\tmean_q_correct\tmean_q_incorrect\tempirical_error_rate\tpredicted_error_rate\tcount_correct\tcount_incorrect\n")
        for i, pos in enumerate(perbase['positions']):
            if i < len(perbase['mean_qscore_all']):
                f.write(f"{pos}\t{perbase['mean_qscore_all'][i]:.2f}\t"
                       f"{perbase['mean_qscore_correct'][i]:.2f}\t"
                       f"{perbase['mean_qscore_incorrect'][i]:.2f}\t"
                       f"{perbase['empirical_error_rate'][i]:.6f}\t"
                       f"{perbase['predicted_error_rate'][i]:.6f}\t"
                       f"{perbase['count_correct'][i]}\t"
                       f"{perbase['count_incorrect'][i]}\n")

    # Save tagged reads as TSV (sample for large datasets)
    reads_to_save = results['tagged_reads'][:10000]  # Save first 10K
    with open(output_dir / 'tagged_reads_sample.tsv', 'w') as f:
        f.write("read_name\tmatched_reference\tedit_distance\tavg_qscore\tread_length\tsource_target\n")
        for read in reads_to_save:
            f.write(f"{read['name']}\t{read['matched_reference']}\t{read['edit_distance']}\t"
                   f"{read['avg_qscore']:.2f}\t{read['read_length']}\t{read['source_target']}\n")

    print(f"Saved results to {output_dir}")


def main():
    parser = argparse.ArgumentParser(description='SMA-seq Read Quality Analysis')
    parser.add_argument('--bam-dir', required=True, help='Directory containing BAM files')
    parser.add_argument('--reference', required=True, help='Reference FASTA file')
    parser.add_argument('--output', required=True, help='Output directory')
    parser.add_argument('--sample-size', type=int, default=100000, help='Number of reads to sample')
    parser.add_argument('--target-filter', help='Filter to specific target (e.g., V04_2)')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for sampling')

    args = parser.parse_args()

    # Set random seed
    random.seed(args.seed)
    np.random.seed(args.seed)

    # Load references
    references = load_references(args.reference)

    if not references:
        print("No references loaded!")
        sys.exit(1)

    # Analyze BAMs
    results = analyze_bam_files(
        args.bam_dir,
        references,
        sample_size=args.sample_size,
        target_filter=args.target_filter
    )

    if not results:
        print("No results!")
        sys.exit(1)

    # Save results
    save_results(results, args.output)

    # Create visualizations
    create_visualizations(results, args.output)

    print("\nAnalysis complete!")
    print(f"  Total reads: {results['stats']['total_reads']:,}")
    print(f"  Perfect reads: {results['stats']['perfect_reads']:,}")
    print(f"  Mean Q-score: {np.mean(results['stats']['qscore_distribution']):.2f}")
    print(f"  Mean ED: {np.mean(results['stats']['ed_distribution']):.2f}")


if __name__ == '__main__':
    main()
