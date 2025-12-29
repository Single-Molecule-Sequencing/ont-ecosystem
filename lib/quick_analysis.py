"""Quick Analysis Module for ONT Experiment Discovery

Provides fast experiment summary extraction without full analysis.
Designed for ~2-5 seconds per experiment by sampling data.

Sampling Priority:
1. sequencing_summary.txt (fastest, most complete)
2. fastq/fastq.gz files (good Q-scores and lengths)
3. BAM files (requires pysam)
4. pod5 files (requires pod5 library, limited metrics without basecalling)
"""

import gzip
import math
import os
import random
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Maximum reads to sample for quick analysis
MAX_SAMPLE_READS = 50000


# =============================================================================
# Q-score Utilities (Phred scale - must average in probability space)
# =============================================================================

def _qscore_to_error_prob(q: float) -> float:
    """Convert Q-score to error probability: P = 10^(-Q/10)"""
    return 10 ** (-q / 10)

def _error_prob_to_qscore(p: float) -> float:
    """Convert error probability to Q-score: Q = -10 * log10(P)"""
    if p <= 0:
        return 60.0  # Cap at Q60 for zero probability
    return -10 * math.log10(p)

def _mean_qscore_from_quals(quals: List[int]) -> float:
    """
    Calculate mean Q-score correctly via probability space.

    Q-scores are logarithmic (Phred scale), so we must:
    1. Convert each Q to error probability
    2. Average the probabilities
    3. Convert back to Q-score
    """
    if not quals:
        return 0.0
    probs = [_qscore_to_error_prob(q) for q in quals]
    mean_prob = sum(probs) / len(probs)
    return _error_prob_to_qscore(mean_prob)


@dataclass
class QuickSummary:
    """Quick summary of an ONT experiment."""
    # Identification
    experiment_id: str
    name: str
    location: str

    # Completeness indicators
    has_final_summary: bool = False
    has_sequencing_summary: bool = False
    has_report: bool = False
    has_pod5: bool = False
    has_fast5: bool = False
    has_fastq: bool = False
    has_bam: bool = False

    # File counts and sizes
    pod5_count: int = 0
    fast5_count: int = 0
    fastq_count: int = 0
    bam_count: int = 0
    total_size_gb: float = 0.0

    # Metadata from final_summary
    run_id: Optional[str] = None
    sample_id: Optional[str] = None
    flow_cell_id: Optional[str] = None
    device_id: Optional[str] = None
    protocol: Optional[str] = None
    kit: Optional[str] = None
    started: Optional[str] = None  # Raw ISO timestamp
    ended: Optional[str] = None    # Raw ISO timestamp

    # Parsed time info for display
    start_date: Optional[str] = None      # e.g., "2025-11-24"
    start_time: Optional[str] = None      # e.g., "20:37"
    duration_hours: Optional[float] = None  # e.g., 72.5

    # Metrics (actual totals, not sampled)
    total_reads: Optional[int] = None
    passed_reads: Optional[int] = None
    failed_reads: Optional[int] = None
    total_bases: Optional[int] = None
    mean_qscore: Optional[float] = None
    median_qscore: Optional[float] = None
    n50: Optional[int] = None
    mean_length: Optional[float] = None
    pass_rate: Optional[float] = None

    # End reason summary (sampled)
    signal_positive_pct: Optional[float] = None
    unblock_pct: Optional[float] = None

    # Quality assessment
    quality_grade: str = "?"  # A/B/C/D/F/?
    issues: List[str] = field(default_factory=list)

    # Timing
    analysis_time_sec: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @property
    def completeness_score(self) -> int:
        """Calculate completeness score (0-100)."""
        checks = [
            self.has_final_summary,
            self.has_sequencing_summary or self.has_report,
            self.has_pod5 or self.has_fast5,
            self.total_reads is not None and self.total_reads > 0,
            self.mean_qscore is not None,
        ]
        return int(sum(checks) / len(checks) * 100)

    @property
    def data_format(self) -> str:
        """Primary data format."""
        if self.has_pod5:
            return "pod5"
        elif self.has_fast5:
            return "fast5"
        elif self.has_bam:
            return "bam"
        elif self.has_fastq:
            return "fastq"
        return "unknown"


def parse_final_summary(filepath: Path) -> Dict[str, str]:
    """Parse final_summary.txt into a dictionary.

    Format: key=value pairs, one per line.
    """
    data = {}
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line:
                    key, value = line.split('=', 1)
                    data[key.strip()] = value.strip()
    except Exception:
        pass
    return data


def parse_timestamp(ts: Optional[str]) -> Optional[Tuple[str, str]]:
    """Parse ISO timestamp into date and time strings.

    Args:
        ts: ISO format timestamp (e.g., "2025-11-24T20:37:26.111070-05:00")

    Returns:
        Tuple of (date_str, time_str) or None if parsing fails
    """
    if not ts:
        return None
    try:
        # Handle ISO format with timezone
        # Remove microseconds and timezone for simpler parsing
        ts_clean = ts.split('.')[0]  # Remove microseconds
        if 'T' in ts_clean:
            date_part, time_part = ts_clean.split('T')
            return date_part, time_part[:5]  # Just HH:MM
        return None
    except Exception:
        return None


def calculate_duration_hours(start: Optional[str], end: Optional[str]) -> Optional[float]:
    """Calculate duration in hours between two ISO timestamps.

    Args:
        start: Start ISO timestamp
        end: End ISO timestamp

    Returns:
        Duration in hours, or None if calculation fails
    """
    if not start or not end:
        return None
    try:
        from datetime import datetime

        # Parse ISO format (handle various formats)
        def parse_iso(ts):
            ts_clean = ts.split('.')[0]  # Remove microseconds
            # Remove timezone offset for parsing
            if '+' in ts_clean:
                ts_clean = ts_clean.split('+')[0]
            elif ts_clean.count('-') > 2:
                # Has negative timezone like -05:00
                parts = ts_clean.rsplit('-', 1)
                if ':' in parts[-1]:
                    ts_clean = parts[0]
            return datetime.fromisoformat(ts_clean)

        start_dt = parse_iso(start)
        end_dt = parse_iso(end)

        duration = end_dt - start_dt
        return duration.total_seconds() / 3600
    except Exception:
        return None


def count_sequencing_summary_reads(filepath: Path) -> Optional[int]:
    """Count total reads in sequencing_summary.txt (fast line count).

    Args:
        filepath: Path to sequencing_summary.txt

    Returns:
        Total read count (excluding header), or None on error
    """
    try:
        # Fast line count using buffer reading
        count = 0
        with open(filepath, 'rb') as f:
            # Skip header
            f.readline()
            # Count remaining lines
            buf_size = 1024 * 1024  # 1MB buffer
            while True:
                buf = f.read(buf_size)
                if not buf:
                    break
                count += buf.count(b'\n')
        return count
    except Exception:
        return None


def sample_sequencing_summary(
    filepath: Path,
    max_rows: int = 10000,
    skip_rows: int = 0
) -> Optional[Dict[str, Any]]:
    """Parse first N rows of sequencing_summary.txt for quick metrics.

    Much faster than full parse - targets <2s per experiment.

    Args:
        filepath: Path to sequencing_summary.txt
        max_rows: Maximum rows to sample
        skip_rows: Rows to skip at start (after header)

    Returns:
        Dictionary with sampled statistics, or None on error
    """
    lengths = []
    qscores = []
    passed = 0
    failed = 0
    end_reasons = defaultdict(int)

    try:
        with open(filepath, 'r') as f:
            # Parse header
            header = f.readline().strip().split('\t')
            col_idx = {name: i for i, name in enumerate(header)}

            # Find column indices
            length_col = None
            for col in ['sequence_length_template', 'sequence_length']:
                if col in col_idx:
                    length_col = col_idx[col]
                    break

            qscore_col = None
            for col in ['mean_qscore_template', 'mean_qscore']:
                if col in col_idx:
                    qscore_col = col_idx[col]
                    break

            passes_idx = col_idx.get('passes_filtering')
            end_reason_idx = col_idx.get('end_reason')

            # Skip rows if requested
            for _ in range(skip_rows):
                f.readline()

            # Sample rows
            row_count = 0
            for line in f:
                if row_count >= max_rows:
                    break

                fields = line.strip().split('\t')
                row_count += 1

                # Pass/fail
                if passes_idx is not None and passes_idx < len(fields):
                    if fields[passes_idx].upper() in ['TRUE', '1', 'PASS']:
                        passed += 1
                    else:
                        failed += 1

                # Length
                if length_col is not None and length_col < len(fields):
                    try:
                        lengths.append(int(float(fields[length_col])))
                    except (ValueError, IndexError):
                        pass

                # Q-score
                if qscore_col is not None and qscore_col < len(fields):
                    try:
                        qscores.append(float(fields[qscore_col]))
                    except (ValueError, IndexError):
                        pass

                # End reason
                if end_reason_idx is not None and end_reason_idx < len(fields):
                    end_reasons[fields[end_reason_idx]] += 1

        if not lengths:
            return None

        # Calculate statistics
        sorted_lengths = sorted(lengths, reverse=True)
        total_bases = sum(sorted_lengths)

        # N50 calculation
        n50 = 0
        running_sum = 0
        for length in sorted_lengths:
            running_sum += length
            if running_sum >= total_bases / 2:
                n50 = length
                break

        # End reason percentages
        total_reasons = sum(end_reasons.values())
        signal_positive_pct = None
        unblock_pct = None
        if total_reasons > 0:
            signal_positive = end_reasons.get('signal_positive', 0)
            signal_positive_pct = (signal_positive / total_reasons) * 100

            unblock = (end_reasons.get('unblock_mux_change', 0) +
                      end_reasons.get('data_service_unblock_mux_change', 0))
            unblock_pct = (unblock / total_reasons) * 100

        return {
            'sampled_reads': row_count,
            'passed_reads': passed,
            'failed_reads': failed,
            'total_bases': total_bases,
            'mean_length': sum(lengths) / len(lengths),
            'n50': n50,
            'mean_qscore': _mean_qscore_from_quals(qscores) if qscores else None,
            'median_qscore': sorted(qscores)[len(qscores)//2] if qscores else None,
            'pass_rate': (passed / (passed + failed) * 100) if (passed + failed) > 0 else None,
            'signal_positive_pct': signal_positive_pct,
            'unblock_pct': unblock_pct,
            'end_reasons': dict(end_reasons),
        }

    except Exception:
        return None


def sample_fastq_files(
    path: Path,
    max_reads: int = MAX_SAMPLE_READS
) -> Optional[Dict[str, Any]]:
    """Sample reads from fastq/fastq.gz files for quick metrics.

    Randomly samples files and reads to get representative statistics.

    Args:
        path: Experiment directory path
        max_reads: Maximum reads to sample

    Returns:
        Dictionary with sampled statistics, or None on error
    """
    lengths = []
    qscores = []
    passed = 0
    failed = 0

    try:
        # Find all fastq files
        fastq_files = list(path.rglob('*.fastq')) + list(path.rglob('*.fastq.gz'))
        if not fastq_files:
            return None

        # Separate pass/fail files
        pass_files = [f for f in fastq_files if 'pass' in str(f).lower()]
        fail_files = [f for f in fastq_files if 'fail' in str(f).lower()]

        # If no pass/fail distinction, use all files as "pass"
        if not pass_files and not fail_files:
            pass_files = fastq_files

        # Shuffle for random sampling
        random.shuffle(pass_files)
        random.shuffle(fail_files)

        # Calculate how many reads per file category
        reads_per_category = max_reads // 2 if (pass_files and fail_files) else max_reads
        reads_collected = 0

        def read_fastq(filepath: Path, max_to_read: int, is_pass: bool) -> int:
            """Read reads from a single fastq file."""
            nonlocal lengths, qscores, passed, failed, reads_collected

            count = 0
            try:
                opener = gzip.open if str(filepath).endswith('.gz') else open
                mode = 'rt' if str(filepath).endswith('.gz') else 'r'

                with opener(filepath, mode) as f:
                    while count < max_to_read and reads_collected < max_reads:
                        # Read 4 lines per record
                        header = f.readline()
                        if not header:
                            break
                        seq = f.readline().strip()
                        plus = f.readline()
                        qual = f.readline().strip()

                        if not seq or not qual:
                            break

                        # Calculate length and Q-score
                        length = len(seq)
                        lengths.append(length)

                        # Convert quality string to Q-scores (Phred+33)
                        # Must average via probability space since Q-scores are logarithmic
                        if qual:
                            q_vals = [ord(c) - 33 for c in qual]
                            mean_q = _mean_qscore_from_quals(q_vals)
                            qscores.append(mean_q)

                        if is_pass:
                            passed += 1
                        else:
                            failed += 1

                        count += 1
                        reads_collected += 1

            except Exception:
                pass

            return count

        # Sample from pass files
        reads_per_file = max(100, reads_per_category // max(len(pass_files), 1))
        for fq in pass_files[:50]:  # Limit to 50 files
            if reads_collected >= max_reads:
                break
            read_fastq(fq, reads_per_file, is_pass=True)

        # Sample from fail files
        reads_per_file = max(100, reads_per_category // max(len(fail_files), 1))
        for fq in fail_files[:50]:
            if reads_collected >= max_reads:
                break
            read_fastq(fq, reads_per_file, is_pass=False)

        if not lengths:
            return None

        # Calculate statistics
        sorted_lengths = sorted(lengths, reverse=True)
        total_bases = sum(sorted_lengths)

        # N50 calculation
        n50 = 0
        running_sum = 0
        for length in sorted_lengths:
            running_sum += length
            if running_sum >= total_bases / 2:
                n50 = length
                break

        return {
            'sampled_reads': len(lengths),
            'passed_reads': passed,
            'failed_reads': failed,
            'total_bases': total_bases,
            'mean_length': sum(lengths) / len(lengths),
            'n50': n50,
            'mean_qscore': _mean_qscore_from_quals(qscores) if qscores else None,
            'median_qscore': sorted(qscores)[len(qscores)//2] if qscores else None,
            'pass_rate': (passed / (passed + failed) * 100) if (passed + failed) > 0 else None,
            'source': 'fastq',
        }

    except Exception:
        return None


def sample_bam_files(
    path: Path,
    max_reads: int = MAX_SAMPLE_READS
) -> Optional[Dict[str, Any]]:
    """Sample reads from BAM files for quick metrics.

    Requires pysam library.

    Args:
        path: Experiment directory path
        max_reads: Maximum reads to sample

    Returns:
        Dictionary with sampled statistics, or None on error
    """
    try:
        import pysam
    except ImportError:
        return None

    lengths = []
    qscores = []
    passed = 0
    failed = 0

    try:
        # Find all BAM files
        bam_files = list(path.rglob('*.bam'))
        if not bam_files:
            return None

        # Separate pass/fail files
        pass_files = [f for f in bam_files if 'pass' in str(f).lower()]
        fail_files = [f for f in bam_files if 'fail' in str(f).lower()]

        if not pass_files and not fail_files:
            pass_files = bam_files

        random.shuffle(pass_files)
        random.shuffle(fail_files)

        reads_collected = 0
        reads_per_category = max_reads // 2 if (pass_files and fail_files) else max_reads

        def read_bam(filepath: Path, max_to_read: int, is_pass: bool) -> int:
            """Read reads from a single BAM file."""
            nonlocal lengths, qscores, passed, failed, reads_collected

            count = 0
            try:
                with pysam.AlignmentFile(str(filepath), "rb", check_sq=False) as bam:
                    for read in bam.fetch(until_eof=True):
                        if count >= max_to_read or reads_collected >= max_reads:
                            break

                        # Get length
                        length = read.query_length or len(read.query_sequence or '')
                        if length > 0:
                            lengths.append(length)

                            # Get mean Q-score
                            quals = read.query_qualities
                            if quals is not None and len(quals) > 0:
                                mean_q = sum(quals) / len(quals)
                                qscores.append(mean_q)

                            if is_pass:
                                passed += 1
                            else:
                                failed += 1

                            count += 1
                            reads_collected += 1

            except Exception:
                pass

            return count

        # Sample from pass files
        reads_per_file = max(100, reads_per_category // max(len(pass_files), 1))
        for bam in pass_files[:20]:
            if reads_collected >= max_reads:
                break
            read_bam(bam, reads_per_file, is_pass=True)

        # Sample from fail files
        reads_per_file = max(100, reads_per_category // max(len(fail_files), 1))
        for bam in fail_files[:20]:
            if reads_collected >= max_reads:
                break
            read_bam(bam, reads_per_file, is_pass=False)

        if not lengths:
            return None

        # Calculate statistics
        sorted_lengths = sorted(lengths, reverse=True)
        total_bases = sum(sorted_lengths)

        # N50 calculation
        n50 = 0
        running_sum = 0
        for length in sorted_lengths:
            running_sum += length
            if running_sum >= total_bases / 2:
                n50 = length
                break

        return {
            'sampled_reads': len(lengths),
            'passed_reads': passed,
            'failed_reads': failed,
            'total_bases': total_bases,
            'mean_length': sum(lengths) / len(lengths),
            'n50': n50,
            'mean_qscore': _mean_qscore_from_quals(qscores) if qscores else None,
            'median_qscore': sorted(qscores)[len(qscores)//2] if qscores else None,
            'pass_rate': (passed / (passed + failed) * 100) if (passed + failed) > 0 else None,
            'source': 'bam',
        }

    except Exception:
        return None


def sample_pod5_files(
    path: Path,
    max_reads: int = MAX_SAMPLE_READS
) -> Optional[Dict[str, Any]]:
    """Sample reads from pod5 files for quick metrics.

    Requires pod5 library. Note: pod5 files contain raw signal data,
    so Q-scores are not available without basecalling.

    Args:
        path: Experiment directory path
        max_reads: Maximum reads to sample

    Returns:
        Dictionary with sampled statistics, or None on error
    """
    try:
        import pod5
    except ImportError:
        return None

    read_count = 0
    signal_durations = []
    channel_counts = defaultdict(int)
    sample_rates = []

    try:
        # Find all pod5 files
        pod5_files = list(path.rglob('*.pod5'))
        if not pod5_files:
            return None

        random.shuffle(pod5_files)
        reads_per_file = max(100, max_reads // max(len(pod5_files), 1))

        for pod5_path in pod5_files[:50]:  # Limit files to process
            if read_count >= max_reads:
                break

            try:
                with pod5.Reader(str(pod5_path)) as reader:
                    for read in reader.reads():
                        if read_count >= max_reads:
                            break

                        # Get signal info
                        signal_len = read.num_samples
                        sample_rate = read.run_info.sample_rate

                        if signal_len > 0 and sample_rate > 0:
                            # Estimate read duration in seconds
                            duration = signal_len / sample_rate
                            signal_durations.append(duration)
                            sample_rates.append(sample_rate)

                            # Track channel distribution
                            channel_counts[read.pore.channel] += 1

                        read_count += 1

            except Exception:
                continue

        if read_count == 0:
            return None

        # Estimate bases from signal duration
        # Rough estimate: ~450 bases/second for DNA at standard speed
        # This varies significantly based on chemistry and conditions
        BASES_PER_SECOND = 450

        estimated_lengths = [int(d * BASES_PER_SECOND) for d in signal_durations]

        if estimated_lengths:
            sorted_lengths = sorted(estimated_lengths, reverse=True)
            total_bases = sum(sorted_lengths)

            # N50 calculation
            n50 = 0
            running_sum = 0
            for length in sorted_lengths:
                running_sum += length
                if running_sum >= total_bases / 2:
                    n50 = length
                    break

            mean_length = sum(estimated_lengths) / len(estimated_lengths)
        else:
            total_bases = 0
            n50 = 0
            mean_length = 0

        # Count unique channels (active pores)
        active_channels = len(channel_counts)

        return {
            'sampled_reads': read_count,
            'passed_reads': read_count,  # Can't determine from pod5 alone
            'failed_reads': 0,
            'total_bases': total_bases,
            'mean_length': mean_length,
            'n50': n50,
            'mean_qscore': None,  # Not available in pod5
            'median_qscore': None,
            'pass_rate': None,  # Can't determine from pod5 alone
            'source': 'pod5',
            'active_channels': active_channels,
            'signal_only': True,  # Flag that this is estimated from signal
        }

    except Exception:
        return None


def sample_fast5_files(
    path: Path,
    max_reads: int = MAX_SAMPLE_READS
) -> Optional[Dict[str, Any]]:
    """Sample reads from fast5 files for quick metrics.

    Requires h5py library. Fast5 files may contain basecalled data
    (if basecalling was performed) or raw signal only.

    Args:
        path: Experiment directory path
        max_reads: Maximum reads to sample

    Returns:
        Dictionary with sampled statistics, or None on error
    """
    try:
        import h5py
    except ImportError:
        return None

    lengths = []
    qscores = []
    passed = 0
    failed = 0
    signal_only_count = 0

    try:
        # Find all fast5 files
        fast5_files = list(path.rglob('*.fast5'))
        if not fast5_files:
            return None

        # Separate pass/fail files
        pass_files = [f for f in fast5_files if 'pass' in str(f).lower()]
        fail_files = [f for f in fast5_files if 'fail' in str(f).lower()]

        if not pass_files and not fail_files:
            pass_files = fast5_files

        random.shuffle(pass_files)
        random.shuffle(fail_files)

        read_count = 0
        reads_per_file = max(1, max_reads // max(len(fast5_files), 1))

        def read_fast5(filepath: Path, max_to_read: int, is_pass: bool) -> int:
            """Read data from a fast5 file (may be single or multi-read)."""
            nonlocal lengths, qscores, passed, failed, read_count, signal_only_count

            count = 0
            try:
                with h5py.File(str(filepath), 'r') as f5:
                    # Check if multi-read or single-read fast5
                    if 'read_' in str(list(f5.keys())):
                        # Multi-read format
                        read_groups = [k for k in f5.keys() if k.startswith('read_')]
                    else:
                        # Single-read or old format
                        read_groups = ['']

                    for rg in read_groups[:max_to_read]:
                        if count >= max_to_read or read_count >= max_reads:
                            break

                        base = f5[rg] if rg else f5

                        # Try to find basecalled data
                        seq = None
                        qual = None

                        # Check various possible locations for basecalled data
                        basecall_paths = [
                            'Analyses/Basecall_1D_000/BaseCalled_template/Fastq',
                            'Analyses/Basecall_1D_001/BaseCalled_template/Fastq',
                            'BaseCalled_template/Fastq',
                        ]

                        for bp in basecall_paths:
                            try:
                                if bp in base:
                                    fastq_data = base[bp][()].decode('utf-8')
                                    lines = fastq_data.strip().split('\n')
                                    if len(lines) >= 4:
                                        seq = lines[1]
                                        qual = lines[3]
                                    break
                            except Exception:
                                continue

                        if seq:
                            lengths.append(len(seq))

                            if qual:
                                # Must average via probability space since Q-scores are logarithmic
                                q_vals = [ord(c) - 33 for c in qual]
                                mean_q = _mean_qscore_from_quals(q_vals)
                                qscores.append(mean_q)

                            if is_pass:
                                passed += 1
                            else:
                                failed += 1

                            count += 1
                            read_count += 1
                        else:
                            # No basecalled data - try to get signal length
                            signal_only_count += 1
                            try:
                                signal_path = 'Raw/Signal' if 'Raw/Signal' in base else 'Raw/Reads'
                                # Skip signal-only for now, just count
                                count += 1
                                read_count += 1
                            except Exception:
                                pass

            except Exception:
                pass

            return count

        # Sample from pass files
        reads_per_file = max(1, (max_reads // 2) // max(len(pass_files), 1))
        for f5 in pass_files[:100]:
            if read_count >= max_reads:
                break
            read_fast5(f5, reads_per_file, is_pass=True)

        # Sample from fail files
        if fail_files:
            reads_per_file = max(1, (max_reads // 2) // max(len(fail_files), 1))
            for f5 in fail_files[:100]:
                if read_count >= max_reads:
                    break
                read_fast5(f5, reads_per_file, is_pass=False)

        if not lengths and signal_only_count == 0:
            return None

        # Calculate statistics if we have basecalled data
        if lengths:
            sorted_lengths = sorted(lengths, reverse=True)
            total_bases = sum(sorted_lengths)

            # N50 calculation
            n50 = 0
            running_sum = 0
            for length in sorted_lengths:
                running_sum += length
                if running_sum >= total_bases / 2:
                    n50 = length
                    break

            return {
                'sampled_reads': len(lengths),
                'passed_reads': passed,
                'failed_reads': failed,
                'total_bases': total_bases,
                'mean_length': sum(lengths) / len(lengths),
                'n50': n50,
                'mean_qscore': _mean_qscore_from_quals(qscores) if qscores else None,
                'median_qscore': sorted(qscores)[len(qscores)//2] if qscores else None,
                'pass_rate': (passed / (passed + failed) * 100) if (passed + failed) > 0 else None,
                'source': 'fast5',
            }
        else:
            # Signal-only fast5 files
            return {
                'sampled_reads': signal_only_count,
                'passed_reads': signal_only_count,
                'failed_reads': 0,
                'total_bases': None,
                'mean_length': None,
                'n50': None,
                'mean_qscore': None,
                'median_qscore': None,
                'pass_rate': None,
                'source': 'fast5',
                'signal_only': True,
            }

    except Exception:
        return None


def calculate_quality_grade(summary: QuickSummary) -> Tuple[str, List[str]]:
    """Calculate quality grade based on metrics.

    Grade A: Q-score >= 12, pass_rate >= 90%, complete data
    Grade B: Q-score >= 10, pass_rate >= 80%
    Grade C: Q-score >= 8, pass_rate >= 70%
    Grade D: Q-score >= 6, pass_rate >= 50%
    Grade F: Below D thresholds or missing critical data
    Grade S: Signal-only data (pod5/fast5 without basecalling)
    Grade ?: Unable to determine
    """
    issues = []

    # Check for missing data files
    if not (summary.has_pod5 or summary.has_fast5 or summary.has_bam or summary.has_fastq):
        issues.append("No data files found")
        return "F", issues

    if summary.total_reads is None or summary.total_reads == 0:
        issues.append("No read statistics available")
        return "?", issues

    # Check if we only have signal data (no Q-scores available)
    if summary.mean_qscore is None and summary.total_reads is not None:
        # Signal-only data from pod5/fast5
        issues.append("Q-score not available (basecalling required)")
        if summary.total_reads > 0:
            if summary.n50 and summary.n50 > 1000:
                issues.append(f"Estimated N50: {summary.n50:,} bp")
            return "S", issues  # Signal-only grade
        return "?", issues

    qscore = summary.mean_qscore or 0
    pass_rate = summary.pass_rate or 0

    # Grade determination based on Q-score and pass rate
    if qscore >= 12 and pass_rate >= 90:
        if not summary.has_final_summary:
            issues.append("Missing final_summary.txt")
        if summary.completeness_score >= 80:
            return "A", issues
        return "B", issues

    if qscore >= 10 and pass_rate >= 80:
        if qscore < 12:
            issues.append(f"Q-score {qscore:.1f} < 12")
        if pass_rate < 90:
            issues.append(f"Pass rate {pass_rate:.1f}% < 90%")
        return "B", issues

    if qscore >= 8 and pass_rate >= 70:
        if qscore < 10:
            issues.append(f"Q-score {qscore:.1f} < 10")
        if pass_rate < 80:
            issues.append(f"Pass rate {pass_rate:.1f}% < 80%")
        return "C", issues

    if qscore >= 6 and pass_rate >= 50:
        issues.append(f"Low Q-score: {qscore:.1f}")
        issues.append(f"Low pass rate: {pass_rate:.1f}%")
        return "D", issues

    issues.append(f"Very low Q-score: {qscore:.1f}")
    issues.append(f"Very low pass rate: {pass_rate:.1f}%")
    return "F", issues


def find_minknow_files(path: Path) -> Dict[str, Any]:
    """Find MinKNOW output files in an experiment directory.

    Searches up to 4 levels deep for standard MinKNOW outputs.
    """
    result = {
        'final_summary': None,
        'sequencing_summary': None,
        'report': None,
        'pod5_count': 0,
        'fast5_count': 0,
        'fastq_count': 0,
        'bam_count': 0,
    }

    # Search patterns at different depths
    patterns = ['', '*/', '*/*/', '*/*/*/']

    for pattern in patterns:
        base = path / pattern.rstrip('/') if pattern else path

        # Final summary
        if result['final_summary'] is None:
            for f in path.glob(f'{pattern}final_summary*.txt'):
                result['final_summary'] = f
                break

        # Sequencing summary
        if result['sequencing_summary'] is None:
            for f in path.glob(f'{pattern}sequencing_summary*.txt'):
                result['sequencing_summary'] = f
                break

        # Report
        if result['report'] is None:
            for f in path.glob(f'{pattern}report_*.html'):
                result['report'] = f
                break

    # Count data files (use rglob for full count)
    try:
        result['pod5_count'] = len(list(path.rglob('*.pod5')))
        result['fast5_count'] = len(list(path.rglob('*.fast5')))
        result['fastq_count'] = len(list(path.rglob('*.fastq'))) + len(list(path.rglob('*.fastq.gz')))
        result['bam_count'] = len(list(path.rglob('*.bam')))
    except PermissionError:
        pass

    return result


def quick_summary(
    experiment_id: str,
    name: str,
    location: str,
    total_size_gb: float = 0.0
) -> QuickSummary:
    """Extract quick metrics from an experiment without full analysis.

    Args:
        experiment_id: Unique experiment identifier
        name: Experiment name
        location: Path to experiment directory
        total_size_gb: Pre-calculated total size in GB

    Returns:
        QuickSummary with available metrics
    """
    start_time = time.time()
    path = Path(location)

    summary = QuickSummary(
        experiment_id=experiment_id,
        name=name,
        location=location,
        total_size_gb=total_size_gb,
    )

    if not path.exists():
        summary.issues.append("Directory not found")
        summary.quality_grade = "F"
        return summary

    # Find MinKNOW files
    files = find_minknow_files(path)

    summary.has_final_summary = files['final_summary'] is not None
    summary.has_sequencing_summary = files['sequencing_summary'] is not None
    summary.has_report = files['report'] is not None
    summary.pod5_count = files['pod5_count']
    summary.fast5_count = files['fast5_count']
    summary.fastq_count = files['fastq_count']
    summary.bam_count = files['bam_count']
    summary.has_pod5 = files['pod5_count'] > 0
    summary.has_fast5 = files['fast5_count'] > 0
    summary.has_fastq = files['fastq_count'] > 0
    summary.has_bam = files['bam_count'] > 0

    # Parse final_summary for metadata
    if files['final_summary']:
        meta = parse_final_summary(files['final_summary'])
        summary.run_id = meta.get('protocol_run_id') or meta.get('run_id')
        summary.sample_id = meta.get('sample_id')
        summary.flow_cell_id = meta.get('flow_cell_id')
        summary.device_id = meta.get('device_id') or meta.get('instrument')
        summary.protocol = meta.get('protocol')
        summary.kit = meta.get('kit')
        summary.started = meta.get('started') or meta.get('protocol_start_time')
        summary.ended = meta.get('processing_stopped') or meta.get('acquisition_stopped')

        # Parse timestamps for display
        ts_parsed = parse_timestamp(summary.started)
        if ts_parsed:
            summary.start_date, summary.start_time = ts_parsed

        # Calculate run duration
        summary.duration_hours = calculate_duration_hours(summary.started, summary.ended)

    # Sample data for metrics using fallback chain:
    # 1. sequencing_summary.txt (fastest, most complete)
    # 2. fastq/fastq.gz files (good Q-scores and lengths)
    # 3. BAM files (requires pysam)
    # 4. pod5 files (limited metrics - signal only)
    # 5. fast5 files (may have basecalled data)

    stats = None
    stats_source = None

    # Try sequencing_summary first (fastest)
    if files['sequencing_summary']:
        stats = sample_sequencing_summary(files['sequencing_summary'], max_rows=MAX_SAMPLE_READS)
        if stats:
            stats_source = 'sequencing_summary'
            # Get ACTUAL total reads by counting lines (fast)
            actual_reads = count_sequencing_summary_reads(files['sequencing_summary'])
            if actual_reads:
                summary.total_reads = actual_reads
                # Scale pass/fail/bases based on sample ratio
                scale = actual_reads / max(stats['sampled_reads'], 1)
                summary.passed_reads = int(stats['passed_reads'] * scale)
                summary.failed_reads = int(stats['failed_reads'] * scale)
                summary.total_bases = int(stats['total_bases'] * scale)
            else:
                summary.total_reads = stats['sampled_reads']
                summary.passed_reads = stats['passed_reads']
                summary.failed_reads = stats['failed_reads']
                summary.total_bases = stats['total_bases']

    # Fallback: try fastq files
    if stats is None and summary.has_fastq:
        stats = sample_fastq_files(path, max_reads=MAX_SAMPLE_READS)
        if stats:
            stats_source = 'fastq'
            summary.total_reads = stats['sampled_reads']
            summary.passed_reads = stats['passed_reads']
            summary.failed_reads = stats['failed_reads']
            summary.total_bases = stats['total_bases']

    # Fallback: try BAM files
    if stats is None and summary.has_bam:
        stats = sample_bam_files(path, max_reads=MAX_SAMPLE_READS)
        if stats:
            stats_source = 'bam'
            summary.total_reads = stats['sampled_reads']
            summary.passed_reads = stats['passed_reads']
            summary.failed_reads = stats['failed_reads']
            summary.total_bases = stats['total_bases']

    # Fallback: try pod5 files (signal only - no Q-scores)
    if stats is None and summary.has_pod5:
        stats = sample_pod5_files(path, max_reads=MAX_SAMPLE_READS)
        if stats:
            stats_source = 'pod5'
            summary.total_reads = stats['sampled_reads']
            summary.passed_reads = stats.get('passed_reads')
            summary.failed_reads = stats.get('failed_reads', 0)
            summary.total_bases = stats.get('total_bases')
            # Note: pod5 provides estimated lengths, not Q-scores

    # Fallback: try fast5 files
    if stats is None and summary.has_fast5:
        stats = sample_fast5_files(path, max_reads=MAX_SAMPLE_READS)
        if stats:
            stats_source = 'fast5'
            summary.total_reads = stats['sampled_reads']
            summary.passed_reads = stats.get('passed_reads')
            summary.failed_reads = stats.get('failed_reads', 0)
            summary.total_bases = stats.get('total_bases')

    # Apply common stats if we got data
    if stats:
        summary.mean_qscore = stats.get('mean_qscore')
        summary.median_qscore = stats.get('median_qscore')
        summary.n50 = stats.get('n50')
        summary.mean_length = stats.get('mean_length')
        summary.pass_rate = stats.get('pass_rate')
        summary.signal_positive_pct = stats.get('signal_positive_pct')
        summary.unblock_pct = stats.get('unblock_pct')

        # Add note if using signal-only source
        if stats.get('signal_only'):
            summary.issues.append(f"Metrics estimated from {stats_source} signal data")

    # Calculate quality grade
    grade, issues = calculate_quality_grade(summary)
    summary.quality_grade = grade
    summary.issues = issues

    summary.analysis_time_sec = time.time() - start_time
    return summary


def quick_analyze_batch(
    experiments: List[Any],
    parallel: bool = True,
    max_workers: int = 4,
    progress_callback: Optional[Callable[[], None]] = None
) -> List[QuickSummary]:
    """Analyze multiple experiments in parallel.

    Args:
        experiments: List of ExperimentMetadata objects (or similar with id, name, location, total_size_gb)
        parallel: Whether to run in parallel
        max_workers: Maximum parallel workers
        progress_callback: Called after each experiment completes

    Returns:
        List of QuickSummary objects
    """
    def analyze_one(exp):
        result = quick_summary(
            experiment_id=exp.id,
            name=exp.name,
            location=exp.location,
            total_size_gb=getattr(exp, 'total_size_gb', 0.0)
        )
        if progress_callback:
            progress_callback()
        return result

    if not parallel or len(experiments) <= 1:
        return [analyze_one(exp) for exp in experiments]

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(analyze_one, exp): exp for exp in experiments}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                exp = futures[future]
                summary = QuickSummary(
                    experiment_id=exp.id,
                    name=exp.name,
                    location=exp.location,
                    quality_grade="F",
                    issues=[f"Analysis failed: {str(e)}"]
                )
                results.append(summary)
                if progress_callback:
                    progress_callback()

    # Sort by original order
    id_to_idx = {exp.id: i for i, exp in enumerate(experiments)}
    results.sort(key=lambda s: id_to_idx.get(s.experiment_id, 999))

    return results


def aggregate_summaries(summaries: List[QuickSummary]) -> Dict[str, Any]:
    """Aggregate statistics across multiple experiments.

    Args:
        summaries: List of QuickSummary objects

    Returns:
        Dictionary with aggregate statistics
    """
    total_reads = sum(s.total_reads or 0 for s in summaries)
    total_bases = sum(s.total_bases or 0 for s in summaries)
    total_size = sum(s.total_size_gb for s in summaries)

    qscores = [s.mean_qscore for s in summaries if s.mean_qscore is not None]
    n50s = [s.n50 for s in summaries if s.n50 is not None]

    grade_counts = defaultdict(int)
    for s in summaries:
        grade_counts[s.quality_grade] += 1

    return {
        'experiment_count': len(summaries),
        'total_reads': total_reads,
        'total_bases': total_bases,
        'total_size_gb': total_size,
        'avg_qscore': _mean_qscore_from_quals(qscores) if qscores else None,
        'avg_n50': sum(n50s) / len(n50s) if n50s else None,
        'grade_distribution': dict(grade_counts),
        'grade_a_count': grade_counts.get('A', 0),
        'grade_b_count': grade_counts.get('B', 0),
        'grade_c_count': grade_counts.get('C', 0),
        'grade_d_count': grade_counts.get('D', 0),
        'grade_f_count': grade_counts.get('F', 0),
        'issues_count': sum(1 for s in summaries if s.issues),
    }
