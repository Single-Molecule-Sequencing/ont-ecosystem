#!/usr/bin/env python3
"""
experiment_db.py - SQLite Experiment Database for ONT Ecosystem

Creates and manages a persistent SQLite database of nanopore experiments,
complementing the YAML-based event-sourced registry with fast SQL queries.

Features:
- Discovers experiments by finding sequencing_summary files
- Parses final_summary files for experiment metadata
- Calculates per-experiment statistics (reads, bases, N50, Q-scores)
- Tracks end_reason distribution for each experiment
- Stores all data in a persistent SQLite database
- Provides fast SQL-based query interface

Part of: https://github.com/Single-Molecule-Sequencing/ont-ecosystem

Usage:
  experiment_db.py build --data_dir /data1 --db_path experiments.db
  experiment_db.py query --db_path experiments.db --summary
  experiment_db.py query --db_path experiments.db --end_reasons
  experiment_db.py query --db_path experiments.db --experiment "sample_name"
"""

import argparse
import os
import sqlite3
import sys
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import glob as glob_module

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Try to import pandas for faster parsing
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    logger.debug("pandas not available, using fallback CSV parsing")

import math


# =============================================================================
# Q-score Utilities (Phred scale - MUST average in probability space)
# =============================================================================
# IMPORTANT: Q-scores are logarithmic and cannot be averaged directly.
# Must convert to probability, average, then convert back.

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
    probs = [10 ** (-q / 10) for q in qscores]
    mean_prob = sum(probs) / len(probs)
    if mean_prob <= 0:
        return 60.0  # Cap at Q60
    return -10 * math.log10(mean_prob)


# =============================================================================
# Database Class
# =============================================================================

class ExperimentDatabase:
    """SQLite database for nanopore experiment management."""

    def __init__(self, db_path):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """Establish database connection."""
        self.conn = sqlite3.connect(self.db_path)
        self._create_tables()
        return self.conn

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def _create_tables(self):
        """Create database schema."""
        cursor = self.conn.cursor()

        # Experiments table - metadata from final_summary
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_path TEXT UNIQUE,
                instrument TEXT,
                flow_cell_id TEXT,
                sample_id TEXT,
                protocol_group_id TEXT,
                protocol TEXT,
                protocol_run_id TEXT,
                acquisition_run_id TEXT,
                started TEXT,
                acquisition_stopped TEXT,
                processing_stopped TEXT,
                basecalling_enabled INTEGER,
                pod5_files INTEGER,
                fastq_files INTEGER,
                bam_files INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Read statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS read_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER,
                total_reads INTEGER,
                passed_reads INTEGER,
                failed_reads INTEGER,
                total_bases INTEGER,
                passed_bases INTEGER,
                mean_read_length REAL,
                median_read_length REAL,
                max_read_length INTEGER,
                min_read_length INTEGER,
                n50 INTEGER,
                mean_qscore REAL,
                median_qscore REAL,
                mean_duration REAL,
                total_duration_hours REAL,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id)
            )
        ''')

        # End reason distribution table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS end_reason_distribution (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER,
                end_reason TEXT,
                count INTEGER,
                percentage REAL,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id)
            )
        ''')

        # Create indexes for common queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_exp_sample ON experiments(sample_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_exp_flow_cell ON experiments(flow_cell_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_end_reason ON end_reason_distribution(end_reason)')

        self.conn.commit()

    def experiment_exists(self, path):
        """Check if experiment already exists in database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM experiments WHERE experiment_path = ?", (path,))
        return cursor.fetchone() is not None

    def insert_experiment(self, metadata, stats, end_reasons):
        """Insert experiment with statistics and end reasons.

        Args:
            metadata: dict with experiment metadata
            stats: dict with read statistics
            end_reasons: dict mapping end_reason -> count

        Returns:
            Experiment ID
        """
        cursor = self.conn.cursor()

        # Insert experiment
        cursor.execute('''
            INSERT INTO experiments (
                experiment_path, instrument, flow_cell_id, sample_id,
                protocol_group_id, protocol, protocol_run_id, acquisition_run_id,
                started, acquisition_stopped, processing_stopped,
                basecalling_enabled, pod5_files, fastq_files, bam_files
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metadata.get('path', ''),
            metadata.get('instrument', ''),
            metadata.get('flow_cell_id', ''),
            metadata.get('sample_id', ''),
            metadata.get('protocol_group_id', ''),
            metadata.get('protocol', ''),
            metadata.get('protocol_run_id', ''),
            metadata.get('acquisition_run_id', ''),
            metadata.get('started', ''),
            metadata.get('acquisition_stopped', ''),
            metadata.get('processing_stopped', ''),
            int(metadata.get('basecalling_enabled', 0) or 0),
            int(metadata.get('pod5_files_in_final_dest', 0) or 0),
            int(metadata.get('fastq_files_in_final_dest', 0) or 0),
            int(metadata.get('bam_files_in_final_dest', 0) or 0)
        ))
        experiment_id = cursor.lastrowid

        # Insert statistics
        if stats:
            cursor.execute('''
                INSERT INTO read_statistics (
                    experiment_id, total_reads, passed_reads, failed_reads,
                    total_bases, passed_bases, mean_read_length, median_read_length,
                    max_read_length, min_read_length, n50, mean_qscore,
                    median_qscore, mean_duration, total_duration_hours
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                experiment_id,
                stats.get('total_reads', 0),
                stats.get('passed_reads', 0),
                stats.get('failed_reads', 0),
                stats.get('total_bases', 0),
                stats.get('passed_bases', 0),
                stats.get('mean_read_length', 0),
                stats.get('median_read_length', 0),
                stats.get('max_read_length', 0),
                stats.get('min_read_length', 0),
                stats.get('n50', 0),
                stats.get('mean_qscore', 0),
                stats.get('median_qscore', 0),
                stats.get('mean_duration', 0),
                stats.get('total_duration_hours', 0)
            ))

        # Insert end reason distribution
        total_reads = stats.get('total_reads', 0) if stats else 0
        for reason, count in end_reasons.items():
            percentage = (count / total_reads * 100) if total_reads > 0 else 0
            cursor.execute('''
                INSERT INTO end_reason_distribution (
                    experiment_id, end_reason, count, percentage
                ) VALUES (?, ?, ?, ?)
            ''', (experiment_id, reason, count, percentage))

        self.conn.commit()
        return experiment_id

    def get_all_experiments(self):
        """Get all experiments with their statistics."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT
                e.id, e.sample_id, e.protocol_group_id, e.flow_cell_id,
                e.started, r.total_reads, r.total_bases, r.mean_qscore, r.n50
            FROM experiments e
            LEFT JOIN read_statistics r ON e.id = r.experiment_id
            ORDER BY e.started DESC
        ''')
        return cursor.fetchall()

    def get_end_reason_summary(self):
        """Get aggregate end reason distribution."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT end_reason, SUM(count) as total
            FROM end_reason_distribution
            GROUP BY end_reason
            ORDER BY total DESC
        ''')
        return cursor.fetchall()

    def get_experiment_end_reasons(self, experiment_id):
        """Get end reason distribution for a specific experiment."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT end_reason, count, percentage
            FROM end_reason_distribution
            WHERE experiment_id = ?
            ORDER BY count DESC
        ''', (experiment_id,))
        return cursor.fetchall()

    def search_experiments(self, search_term):
        """Search experiments by sample_id or protocol_group_id."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT e.sample_id, e.protocol_group_id, e.flow_cell_id,
                   e.started, r.total_reads, r.total_bases, r.mean_qscore, r.n50
            FROM experiments e
            LEFT JOIN read_statistics r ON e.id = r.experiment_id
            WHERE e.sample_id LIKE ? OR e.protocol_group_id LIKE ?
        ''', (f'%{search_term}%', f'%{search_term}%'))
        return cursor.fetchall()

    def sync_from_event(self, experiment_id, event):
        """
        Sync analysis event results to database.

        This is called by ont_experiments.py after running an analysis
        to keep the database in sync with the registry.

        Args:
            experiment_id: Registry experiment ID (used to find DB record)
            event: Event dict with analysis results

        Returns:
            True if sync succeeded, False otherwise
        """
        cursor = self.conn.cursor()

        # Find experiment by path containing the ID
        cursor.execute("""
            SELECT id FROM experiments
            WHERE experiment_path LIKE ?
            LIMIT 1
        """, (f'%{experiment_id}%',))
        row = cursor.fetchone()

        if row is None:
            logger.debug(f"Experiment {experiment_id} not found in database")
            return False

        db_exp_id = row[0]
        analysis = event.get('analysis', '')
        results = event.get('results', {})

        if analysis in ('end_reasons', 'endreason_qc'):
            # Update end reason distribution
            total_reads = results.get('total_reads', 0)
            sp_pct = results.get('signal_positive_pct', 0)
            unblock_pct = results.get('unblock_mux_pct', results.get('unblock_pct', 0))

            # Delete existing end reasons for this experiment
            cursor.execute("DELETE FROM end_reason_distribution WHERE experiment_id = ?", (db_exp_id,))

            # Insert new end reasons
            if sp_pct and total_reads:
                sp_count = int(total_reads * sp_pct / 100)
                cursor.execute("""
                    INSERT INTO end_reason_distribution (experiment_id, end_reason, count, percentage)
                    VALUES (?, 'signal_positive', ?, ?)
                """, (db_exp_id, sp_count, sp_pct))

            if unblock_pct and total_reads:
                unblock_count = int(total_reads * unblock_pct / 100)
                cursor.execute("""
                    INSERT INTO end_reason_distribution (experiment_id, end_reason, count, percentage)
                    VALUES (?, 'unblock_mux_change', ?, ?)
                """, (db_exp_id, unblock_count, unblock_pct))

            self.conn.commit()
            logger.debug(f"Synced end_reasons for {experiment_id}")
            return True

        elif analysis == 'basecalling':
            # Update read statistics
            cursor.execute("SELECT id FROM read_statistics WHERE experiment_id = ?", (db_exp_id,))
            stats_row = cursor.fetchone()

            if stats_row:
                # Update existing
                cursor.execute("""
                    UPDATE read_statistics SET
                        total_reads = COALESCE(?, total_reads),
                        passed_reads = COALESCE(?, passed_reads),
                        total_bases = COALESCE(?, total_bases),
                        mean_qscore = COALESCE(?, mean_qscore),
                        median_qscore = COALESCE(?, median_qscore),
                        n50 = COALESCE(?, n50)
                    WHERE experiment_id = ?
                """, (
                    results.get('total_reads'),
                    results.get('pass_reads'),
                    results.get('bases_called'),
                    results.get('mean_qscore'),
                    results.get('median_qscore'),
                    results.get('n50'),
                    db_exp_id
                ))
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO read_statistics (
                        experiment_id, total_reads, passed_reads, total_bases,
                        mean_qscore, median_qscore, n50
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    db_exp_id,
                    results.get('total_reads', 0),
                    results.get('pass_reads', 0),
                    results.get('bases_called', 0),
                    results.get('mean_qscore', 0),
                    results.get('median_qscore', 0),
                    results.get('n50', 0)
                ))

            self.conn.commit()
            logger.debug(f"Synced basecalling stats for {experiment_id}")
            return True

        elif analysis == 'monitoring':
            # Update from monitoring snapshot
            cursor.execute("SELECT id FROM read_statistics WHERE experiment_id = ?", (db_exp_id,))
            stats_row = cursor.fetchone()

            if stats_row:
                cursor.execute("""
                    UPDATE read_statistics SET
                        total_reads = COALESCE(?, total_reads),
                        total_bases = COALESCE(?, total_bases),
                        mean_qscore = COALESCE(?, mean_qscore),
                        n50 = COALESCE(?, n50)
                    WHERE experiment_id = ?
                """, (
                    results.get('total_reads'),
                    results.get('total_bases'),
                    results.get('mean_qscore'),
                    results.get('n50'),
                    db_exp_id
                ))
            else:
                cursor.execute("""
                    INSERT INTO read_statistics (
                        experiment_id, total_reads, total_bases, mean_qscore, n50
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    db_exp_id,
                    results.get('total_reads', 0),
                    results.get('total_bases', 0),
                    results.get('mean_qscore', 0),
                    results.get('n50', 0)
                ))

            self.conn.commit()
            logger.debug(f"Synced monitoring stats for {experiment_id}")
            return True

        return False


# =============================================================================
# Sync Helper Function
# =============================================================================

def sync_event_to_database(experiment_id, event, db_path=None):
    """
    Convenience function to sync an event to the database.

    Called by ont_experiments.py after analysis completion.

    Args:
        experiment_id: Registry experiment ID
        event: Event dict with analysis results
        db_path: Optional database path (defaults to ~/.ont-registry/experiments.db)

    Returns:
        True if sync succeeded, False otherwise
    """
    if db_path is None:
        db_path = Path.home() / ".ont-registry" / "experiments.db"

    if not Path(db_path).exists():
        return False

    try:
        db = ExperimentDatabase(str(db_path))
        db.connect()
        result = db.sync_from_event(experiment_id, event)
        db.close()
        return result
    except Exception as e:
        logger.warning(f"Failed to sync event to database: {e}")
        return False


# =============================================================================
# Parsing Functions
# =============================================================================

def parse_final_summary(filepath):
    """Parse final_summary.txt file into a dictionary."""
    data = {}
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line:
                    key, value = line.split('=', 1)
                    data[key] = value
    except Exception as e:
        logger.warning(f"Error parsing {filepath}: {e}")
    return data


def calculate_n50(lengths):
    """Calculate N50 from a list of read lengths."""
    if not lengths:
        return 0
    sorted_lengths = sorted(lengths, reverse=True)
    total = sum(sorted_lengths)
    running_sum = 0
    for length in sorted_lengths:
        running_sum += length
        if running_sum >= total / 2:
            return length
    return 0


def parse_sequencing_summary(filepath):
    """Parse sequencing_summary.txt and calculate statistics."""
    stats = {
        'total_reads': 0,
        'passed_reads': 0,
        'failed_reads': 0,
        'total_bases': 0,
        'passed_bases': 0,
        'lengths': [],
        'qscores': [],
        'durations': [],
        'end_reasons': defaultdict(int)
    }

    try:
        if HAS_PANDAS:
            # Use pandas for efficient chunk processing
            chunk_size = 100000
            for chunk in pd.read_csv(filepath, sep='\t', chunksize=chunk_size, low_memory=False):
                stats['total_reads'] += len(chunk)

                # Get column names (they vary between versions)
                length_col = None
                for col in ['sequence_length_template', 'sequence_length']:
                    if col in chunk.columns:
                        length_col = col
                        break

                qscore_col = None
                for col in ['mean_qscore_template', 'mean_qscore']:
                    if col in chunk.columns:
                        qscore_col = col
                        break

                duration_col = 'duration' if 'duration' in chunk.columns else None
                passes_col = 'passes_filtering' if 'passes_filtering' in chunk.columns else None
                end_reason_col = 'end_reason' if 'end_reason' in chunk.columns else None

                if passes_col:
                    passed = chunk[passes_col].astype(str).str.upper().isin(['TRUE', '1', 'PASS'])
                    stats['passed_reads'] += passed.sum()
                    stats['failed_reads'] += (~passed).sum()

                if length_col:
                    lengths = chunk[length_col].dropna().astype(int).tolist()
                    stats['lengths'].extend(lengths)
                    stats['total_bases'] += sum(lengths)
                    if passes_col:
                        stats['passed_bases'] += chunk.loc[passed, length_col].dropna().astype(int).sum()

                if qscore_col:
                    stats['qscores'].extend(chunk[qscore_col].dropna().tolist())

                if duration_col:
                    stats['durations'].extend(chunk[duration_col].dropna().tolist())

                if end_reason_col:
                    for reason, count in chunk[end_reason_col].value_counts().items():
                        stats['end_reasons'][reason] += count
        else:
            # Fallback: manual parsing without pandas
            with open(filepath, 'r') as f:
                header = f.readline().strip().split('\t')
                col_idx = {name: i for i, name in enumerate(header)}

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

                duration_idx = col_idx.get('duration')
                passes_idx = col_idx.get('passes_filtering')
                end_reason_idx = col_idx.get('end_reason')

                for line in f:
                    fields = line.strip().split('\t')
                    stats['total_reads'] += 1

                    if passes_idx is not None and passes_idx < len(fields):
                        passed = fields[passes_idx].upper() in ['TRUE', '1', 'PASS']
                        if passed:
                            stats['passed_reads'] += 1
                        else:
                            stats['failed_reads'] += 1

                    if length_col is not None and length_col < len(fields):
                        try:
                            length = int(float(fields[length_col]))
                            stats['lengths'].append(length)
                            stats['total_bases'] += length
                        except (ValueError, IndexError):
                            pass

                    if qscore_col is not None and qscore_col < len(fields):
                        try:
                            stats['qscores'].append(float(fields[qscore_col]))
                        except (ValueError, IndexError):
                            pass

                    if duration_idx is not None and duration_idx < len(fields):
                        try:
                            stats['durations'].append(float(fields[duration_idx]))
                        except (ValueError, IndexError):
                            pass

                    if end_reason_idx is not None and end_reason_idx < len(fields):
                        stats['end_reasons'][fields[end_reason_idx]] += 1

    except Exception as e:
        logger.error(f"Error parsing {filepath}: {e}")
        return None

    # Calculate summary statistics
    result = {
        'total_reads': stats['total_reads'],
        'passed_reads': stats['passed_reads'],
        'failed_reads': stats['failed_reads'],
        'total_bases': stats['total_bases'],
        'passed_bases': stats['passed_bases'],
        'mean_read_length': sum(stats['lengths']) / len(stats['lengths']) if stats['lengths'] else 0,
        'median_read_length': sorted(stats['lengths'])[len(stats['lengths'])//2] if stats['lengths'] else 0,
        'max_read_length': max(stats['lengths']) if stats['lengths'] else 0,
        'min_read_length': min(stats['lengths']) if stats['lengths'] else 0,
        'n50': calculate_n50(stats['lengths']),
        'mean_qscore': _mean_qscore(stats['qscores']) if stats['qscores'] else 0,
        'median_qscore': sorted(stats['qscores'])[len(stats['qscores'])//2] if stats['qscores'] else 0,
        'mean_duration': sum(stats['durations']) / len(stats['durations']) if stats['durations'] else 0,
        'total_duration_hours': sum(stats['durations']) / 3600 if stats['durations'] else 0,
        'end_reasons': dict(stats['end_reasons'])
    }

    return result


def find_experiments(data_root):
    """Find all nanopore experiment directories with sequencing summaries.

    Args:
        data_root: Root directory to search

    Returns:
        List of dicts with path, sequencing_summary, and final_summary
    """
    experiments = []

    # Find all sequencing_summary files (excluding those in pod5_pass subdirs)
    summary_files = glob_module.glob(f"{data_root}/**/sequencing_summary*.txt", recursive=True)

    for seq_summary in summary_files:
        # Skip files in pod5_pass directories (duplicates from basecalling)
        if 'pod5_pass' in seq_summary:
            continue

        exp_dir = os.path.dirname(seq_summary)

        # Look for corresponding final_summary
        final_summaries = glob_module.glob(os.path.join(exp_dir, "final_summary*.txt"))
        final_summary = final_summaries[0] if final_summaries else None

        experiments.append({
            'path': exp_dir,
            'sequencing_summary': seq_summary,
            'final_summary': final_summary
        })

    return experiments


# =============================================================================
# Database Builder
# =============================================================================

def build_experiment_database(data_root, db_path, force_rebuild=False):
    """Build or update experiment database from a data directory.

    Args:
        data_root: Root directory containing nanopore experiments
        db_path: Path for SQLite database
        force_rebuild: If True, drop and rebuild all tables

    Returns:
        ExperimentDatabase instance
    """
    db = ExperimentDatabase(db_path)
    db.connect()

    if force_rebuild:
        cursor = db.conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS end_reason_distribution")
        cursor.execute("DROP TABLE IF EXISTS read_statistics")
        cursor.execute("DROP TABLE IF EXISTS experiments")
        db.conn.commit()
        db._create_tables()

    experiments = find_experiments(data_root)
    logger.info(f"Found {len(experiments)} experiments in {data_root}")

    for i, exp in enumerate(experiments, 1):
        exp_name = os.path.basename(exp['path'])
        logger.info(f"Processing {i}/{len(experiments)}: {exp_name}")

        if db.experiment_exists(exp['path']):
            logger.info(f"  Already in database, skipping...")
            continue

        # Parse metadata
        metadata = {'path': exp['path']}
        if exp['final_summary']:
            metadata.update(parse_final_summary(exp['final_summary']))

        # Parse sequencing summary
        logger.info(f"  Parsing sequencing summary...")
        stats = parse_sequencing_summary(exp['sequencing_summary'])

        if stats:
            end_reasons = stats.pop('end_reasons', {})
            db.insert_experiment(metadata, stats, end_reasons)
            logger.info(f"  Total reads: {stats['total_reads']:,}")
            logger.info(f"  Total bases: {stats['total_bases']:,}")
            logger.info(f"  Mean Q-score: {stats['mean_qscore']:.2f}")
        else:
            db.insert_experiment(metadata, None, {})
            logger.warning(f"  No statistics available")

    return db


def generate_database_report(db):
    """Generate a text report from the database.

    Args:
        db: ExperimentDatabase instance

    Returns:
        Report string
    """
    lines = []
    lines.append("=" * 80)
    lines.append("NANOPORE EXPERIMENTS DATABASE REPORT")
    lines.append("=" * 80)

    # Overview
    cursor = db.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM experiments")
    total_experiments = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(total_reads), SUM(total_bases) FROM read_statistics")
    totals = cursor.fetchone()

    lines.append(f"\nTotal Experiments: {total_experiments}")
    if totals[0]:
        lines.append(f"Total Reads: {totals[0]:,}")
        lines.append(f"Total Bases: {totals[1]:,}")

    # Experiment summaries
    lines.append("\n" + "-" * 80)
    lines.append("EXPERIMENT SUMMARIES")
    lines.append("-" * 80)

    header = f"{'Sample ID':<35} {'Protocol Group':<30} {'Reads':>12} {'Bases':>15} {'Q':>6}"
    lines.append(header)
    lines.append("-" * len(header))

    for exp in db.get_all_experiments():
        sample_id = (exp[1] or 'N/A')[:34]
        protocol = (exp[2] or 'N/A')[:29]
        reads = f"{exp[5]:,}" if exp[5] else "N/A"
        bases = f"{exp[6]:,}" if exp[6] else "N/A"
        qscore = f"{exp[7]:.1f}" if exp[7] else "N/A"
        lines.append(f"{sample_id:<35} {protocol:<30} {reads:>12} {bases:>15} {qscore:>6}")

    # End reason summary
    lines.append("\n" + "-" * 80)
    lines.append("END REASON DISTRIBUTION (All Experiments)")
    lines.append("-" * 80)

    end_reasons = db.get_end_reason_summary()
    total_all = sum(r[1] for r in end_reasons)

    lines.append(f"\n{'End Reason':<40} {'Count':>15} {'Percentage':>12}")
    lines.append("-" * 70)

    for reason, count in end_reasons:
        pct = (count / total_all * 100) if total_all > 0 else 0
        lines.append(f"{reason:<40} {count:>15,} {pct:>11.2f}%")

    return "\n".join(lines)


# =============================================================================
# CLI Commands
# =============================================================================

def cmd_build(args):
    """Build experiment database."""
    if not os.path.isdir(args.data_dir):
        logger.error(f"Data directory not found: {args.data_dir}")
        return 1

    logger.info("Nanopore Experiment Database Builder")
    logger.info("=" * 40)

    db = build_experiment_database(
        args.data_dir,
        args.db_path,
        force_rebuild=args.rebuild
    )

    report = generate_database_report(db)
    print(report)

    if args.output_report:
        with open(args.output_report, 'w') as f:
            f.write(report)
        logger.info(f"Report saved to: {args.output_report}")

    logger.info(f"\nDatabase saved to: {args.db_path}")
    db.close()
    return 0


def cmd_query(args):
    """Query experiment database."""
    if not os.path.isfile(args.db_path):
        logger.error(f"Database not found: {args.db_path}")
        return 1

    db = ExperimentDatabase(args.db_path)
    db.connect()

    if args.sql:
        # Custom SQL query
        cursor = db.conn.cursor()
        try:
            cursor.execute(args.sql)
            cols = [desc[0] for desc in cursor.description] if cursor.description else []
            if cols:
                print("\t".join(cols))
                for row in cursor.fetchall():
                    print("\t".join(str(x) for x in row))
        except Exception as e:
            logger.error(f"SQL error: {e}")
            return 1

    elif args.experiment:
        # Search for experiment
        results = db.search_experiments(args.experiment)
        if not results:
            print(f"No experiments found matching: {args.experiment}")
        else:
            for row in results:
                print(f"\nExperiment: {row[0]} ({row[1]})")
                print(f"  Flow Cell: {row[2]}")
                print(f"  Started: {row[3]}")
                print(f"  Total Reads: {row[4]:,}" if row[4] else "  Total Reads: N/A")
                print(f"  Total Bases: {row[5]:,}" if row[5] else "  Total Bases: N/A")
                print(f"  Mean Q-score: {row[6]:.2f}" if row[6] else "  Mean Q-score: N/A")
                print(f"  N50: {row[7]:,}" if row[7] else "  N50: N/A")

    elif args.end_reasons:
        # Show end reason distribution
        print("\n" + "=" * 70)
        print("END REASON DISTRIBUTION (All Experiments)")
        print("=" * 70)

        end_reasons = db.get_end_reason_summary()
        total_all = sum(r[1] for r in end_reasons)

        print(f"\n{'End Reason':<40} {'Count':>15} {'Percentage':>12}")
        print("-" * 70)

        for reason, count in end_reasons:
            pct = (count / total_all * 100) if total_all > 0 else 0
            print(f"{reason:<40} {count:>15,} {pct:>11.2f}%")

    else:
        # Default: show summary
        report = generate_database_report(db)
        print(report)

    db.close()
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='ONT Experiment Database - SQLite storage for nanopore experiments',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Part of: https://github.com/Single-Molecule-Sequencing/ont-ecosystem

Examples:
  # Build database from /data1
  experiment_db.py build --data_dir /data1 --db_path experiments.db

  # Query existing database
  experiment_db.py query --db_path experiments.db --summary

  # Show end reason distribution
  experiment_db.py query --db_path experiments.db --end_reasons

  # Search for specific experiment
  experiment_db.py query --db_path experiments.db --experiment "greg"
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Build command
    build_parser = subparsers.add_parser('build', help='Build experiment database')
    build_parser.add_argument('--data_dir', required=True,
                              help='Root directory containing nanopore experiments')
    build_parser.add_argument('--db_path', required=True,
                              help='Path for SQLite database file')
    build_parser.add_argument('--rebuild', action='store_true',
                              help='Force rebuild of database (drop existing tables)')
    build_parser.add_argument('--output_report', '-o',
                              help='Save report to file')
    build_parser.add_argument('--verbose', '-v', action='store_true',
                              help='Enable verbose output')

    # Query command
    query_parser = subparsers.add_parser('query', help='Query experiment database')
    query_parser.add_argument('--db_path', required=True,
                              help='Path to SQLite database file')
    query_parser.add_argument('--summary', action='store_true',
                              help='Show experiment summary')
    query_parser.add_argument('--end_reasons', action='store_true',
                              help='Show end reason distribution')
    query_parser.add_argument('--experiment', '-e',
                              help='Search for experiment by name')
    query_parser.add_argument('--sql',
                              help='Run custom SQL query')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    if args.command == 'build':
        return cmd_build(args)
    elif args.command == 'query':
        return cmd_query(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
