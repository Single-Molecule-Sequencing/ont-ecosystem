#!/usr/bin/env python3
"""
Comprehensive Nanopore Experiment Database Builder
Scans multiple data locations and builds unified database.
Pure Python implementation (no pandas/numpy required).
"""

import os
import sqlite3
import csv
from pathlib import Path
from collections import defaultdict
import json
from datetime import datetime
import glob as glob_module
import hashlib

# Database location
DB_PATH = "/nfs/turbo/umms-atheylab/nanopore_experiments.db"

# All data roots to scan
DATA_ROOTS = [
    "/data1",
    "/nfs/turbo/umms-atheylab/sequencing_data",
    "/nfs/turbo/umms-atheylab/backup_from_desktop",
    "/nfs/turbo/umms-atheylab/end_reason",
]

def create_database():
    """Create SQLite database with schema for experiments."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Experiments table - metadata from final_summary
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_path TEXT UNIQUE,
            data_root TEXT,
            unique_id TEXT,
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

    conn.commit()
    return conn

def get_experiment_unique_id(exp_path, metadata):
    """Generate unique ID for experiment to detect duplicates."""
    # Use protocol_run_id if available (most unique)
    if metadata.get('protocol_run_id'):
        return metadata['protocol_run_id']

    # Otherwise use combination of flow_cell + acquisition_run_id
    if metadata.get('flow_cell_id') and metadata.get('acquisition_run_id'):
        return f"{metadata['flow_cell_id']}_{metadata['acquisition_run_id']}"

    # Fall back to path-based hash
    return hashlib.md5(exp_path.encode()).hexdigest()[:16]

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
        print(f"Error parsing {filepath}: {e}")
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
    """Parse sequencing_summary.txt and calculate statistics using pure Python."""
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
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f, delimiter='\t')

            # Get column names (they vary between versions)
            fieldnames = reader.fieldnames
            if not fieldnames:
                return None

            length_col = None
            for col in ['sequence_length_template', 'sequence_length']:
                if col in fieldnames:
                    length_col = col
                    break

            qscore_col = None
            for col in ['mean_qscore_template', 'mean_qscore']:
                if col in fieldnames:
                    qscore_col = col
                    break

            duration_col = 'duration' if 'duration' in fieldnames else None
            passes_col = 'passes_filtering' if 'passes_filtering' in fieldnames else None
            end_reason_col = 'end_reason' if 'end_reason' in fieldnames else None

            for row in reader:
                stats['total_reads'] += 1

                # Parse passes_filtering
                passed = False
                if passes_col and row.get(passes_col):
                    val = row[passes_col].strip().upper()
                    passed = val in ['TRUE', '1', 'PASS']
                    if passed:
                        stats['passed_reads'] += 1
                    else:
                        stats['failed_reads'] += 1

                # Parse length
                if length_col and row.get(length_col):
                    try:
                        length = int(float(row[length_col]))
                        stats['lengths'].append(length)
                        stats['total_bases'] += length
                        if passed:
                            stats['passed_bases'] += length
                    except (ValueError, TypeError):
                        pass

                # Parse qscore
                if qscore_col and row.get(qscore_col):
                    try:
                        qscore = float(row[qscore_col])
                        stats['qscores'].append(qscore)
                    except (ValueError, TypeError):
                        pass

                # Parse duration
                if duration_col and row.get(duration_col):
                    try:
                        duration = float(row[duration_col])
                        stats['durations'].append(duration)
                    except (ValueError, TypeError):
                        pass

                # Parse end_reason
                if end_reason_col and row.get(end_reason_col):
                    stats['end_reasons'][row[end_reason_col]] += 1

    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return None

    # Calculate summary statistics
    lengths = stats['lengths']
    qscores = stats['qscores']
    durations = stats['durations']

    result = {
        'total_reads': stats['total_reads'],
        'passed_reads': stats['passed_reads'],
        'failed_reads': stats['failed_reads'],
        'total_bases': stats['total_bases'],
        'passed_bases': stats['passed_bases'],
        'mean_read_length': sum(lengths) / len(lengths) if lengths else 0,
        'median_read_length': sorted(lengths)[len(lengths)//2] if lengths else 0,
        'max_read_length': max(lengths) if lengths else 0,
        'min_read_length': min(lengths) if lengths else 0,
        'n50': calculate_n50(lengths),
        'mean_qscore': sum(qscores) / len(qscores) if qscores else 0,
        'median_qscore': sorted(qscores)[len(qscores)//2] if qscores else 0,
        'mean_duration': sum(durations) / len(durations) if durations else 0,
        'total_duration_hours': sum(durations) / 3600 if durations else 0,
        'end_reasons': dict(stats['end_reasons'])
    }

    return result

def find_experiments(data_root):
    """Find all nanopore experiment directories with sequencing summaries in a data root."""
    experiments = []

    print(f"Scanning {data_root}...")

    # Find all sequencing_summary files
    summary_files = glob_module.glob(f"{data_root}/**/sequencing_summary*.txt", recursive=True)

    for seq_summary in summary_files:
        # Skip files in pod5_pass, pod5_skip directories (often duplicates)
        if any(skip in seq_summary for skip in ['pod5_pass', 'pod5_skip']):
            continue

        exp_dir = os.path.dirname(seq_summary)

        # Look for corresponding final_summary
        final_summaries = glob_module.glob(os.path.join(exp_dir, "final_summary*.txt"))
        final_summary = final_summaries[0] if final_summaries else None

        experiments.append({
            'path': exp_dir,
            'data_root': data_root,
            'sequencing_summary': seq_summary,
            'final_summary': final_summary
        })

    print(f"  Found {len(experiments)} experiments in {data_root}")
    return experiments

def load_experiments_to_db(conn):
    """Find and load all experiments from all data roots into the database."""
    cursor = conn.cursor()

    # Track unique experiments to avoid duplicates
    seen_unique_ids = set()

    # Get already processed unique IDs
    cursor.execute("SELECT unique_id FROM experiments WHERE unique_id IS NOT NULL")
    for row in cursor.fetchall():
        seen_unique_ids.add(row[0])

    all_experiments = []
    for data_root in DATA_ROOTS:
        if os.path.exists(data_root):
            all_experiments.extend(find_experiments(data_root))

    print(f"\nTotal experiments found: {len(all_experiments)}")

    processed = 0
    skipped_existing = 0
    skipped_duplicate = 0

    for i, exp in enumerate(all_experiments, 1):
        print(f"\n[{i}/{len(all_experiments)}] {os.path.basename(exp['path'])}")

        # Check if already in database by path
        cursor.execute("SELECT id FROM experiments WHERE experiment_path = ?", (exp['path'],))
        existing = cursor.fetchone()
        if existing:
            print(f"  -> Already in database (path)")
            skipped_existing += 1
            continue

        # Parse final summary for metadata
        metadata = {}
        if exp['final_summary']:
            metadata = parse_final_summary(exp['final_summary'])

        # Generate unique ID
        unique_id = get_experiment_unique_id(exp['path'], metadata)

        # Check for duplicate based on unique_id (same experiment in different locations)
        if unique_id in seen_unique_ids:
            print(f"  -> Duplicate (unique_id: {unique_id[:20]}...)")
            skipped_duplicate += 1
            continue

        seen_unique_ids.add(unique_id)

        # Insert experiment record
        cursor.execute('''
            INSERT INTO experiments (
                experiment_path, data_root, unique_id, instrument, flow_cell_id, sample_id,
                protocol_group_id, protocol, protocol_run_id, acquisition_run_id,
                started, acquisition_stopped, processing_stopped,
                basecalling_enabled, pod5_files, fastq_files, bam_files
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            exp['path'],
            exp['data_root'],
            unique_id,
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

        # Parse sequencing summary for statistics
        print(f"  -> Parsing sequencing summary...")
        stats = parse_sequencing_summary(exp['sequencing_summary'])

        if stats:
            # Insert read statistics
            cursor.execute('''
                INSERT INTO read_statistics (
                    experiment_id, total_reads, passed_reads, failed_reads,
                    total_bases, passed_bases, mean_read_length, median_read_length,
                    max_read_length, min_read_length, n50, mean_qscore,
                    median_qscore, mean_duration, total_duration_hours
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                experiment_id,
                stats['total_reads'],
                stats['passed_reads'],
                stats['failed_reads'],
                stats['total_bases'],
                stats['passed_bases'],
                stats['mean_read_length'],
                stats['median_read_length'],
                stats['max_read_length'],
                stats['min_read_length'],
                stats['n50'],
                stats['mean_qscore'],
                stats['median_qscore'],
                stats['mean_duration'],
                stats['total_duration_hours']
            ))

            # Insert end reason distribution
            total_reads = stats['total_reads']
            for reason, count in stats['end_reasons'].items():
                percentage = (count / total_reads * 100) if total_reads > 0 else 0
                cursor.execute('''
                    INSERT INTO end_reason_distribution (
                        experiment_id, end_reason, count, percentage
                    ) VALUES (?, ?, ?, ?)
                ''', (experiment_id, reason, count, percentage))

            print(f"  -> Reads: {stats['total_reads']:,} | Bases: {stats['total_bases']:,} | Q: {stats['mean_qscore']:.1f}")
            processed += 1

        conn.commit()

    print(f"\n\n{'='*60}")
    print("PROCESSING SUMMARY")
    print(f"{'='*60}")
    print(f"  Total found: {len(all_experiments)}")
    print(f"  Processed: {processed}")
    print(f"  Skipped (already in DB): {skipped_existing}")
    print(f"  Skipped (duplicate): {skipped_duplicate}")

    return processed

def generate_report(conn):
    """Generate summary report from database."""
    cursor = conn.cursor()

    print("\n" + "="*80)
    print("NANOPORE EXPERIMENTS DATABASE REPORT")
    print("="*80)

    # Overview
    cursor.execute("SELECT COUNT(*) FROM experiments")
    total_experiments = cursor.fetchone()[0]
    print(f"\nTotal Unique Experiments: {total_experiments}")

    # By data root
    cursor.execute("SELECT data_root, COUNT(*) FROM experiments GROUP BY data_root")
    print("\nExperiments by Data Location:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")

    cursor.execute("SELECT SUM(total_reads), SUM(total_bases) FROM read_statistics")
    totals = cursor.fetchone()
    total_reads = totals[0] or 0
    total_bases = totals[1] or 0
    print(f"\nTotal Reads Across All Experiments: {total_reads:,}")
    print(f"Total Bases Across All Experiments: {total_bases:,}")
    print(f"Total Gigabases: {total_bases / 1e9:.2f} Gb")

    # End Reason Distribution (aggregate)
    print("\n" + "-"*80)
    print("END REASON DISTRIBUTION (All Experiments)")
    print("-"*80)

    cursor.execute('''
        SELECT end_reason, SUM(count) as total_count
        FROM end_reason_distribution
        GROUP BY end_reason
        ORDER BY total_count DESC
    ''')

    end_reasons = cursor.fetchall()
    total_all = sum(r[1] for r in end_reasons)

    print(f"\n{'End Reason':<40} {'Count':>15} {'Percentage':>12}")
    print("-"*70)

    for reason, count in end_reasons:
        pct = (count / total_all * 100) if total_all > 0 else 0
        print(f"{reason:<40} {count:>15,} {pct:>11.2f}%")

    # Top 20 experiments by reads
    print("\n" + "-"*80)
    print("TOP 20 EXPERIMENTS BY READ COUNT")
    print("-"*80)

    cursor.execute('''
        SELECT
            e.sample_id,
            e.protocol_group_id,
            e.flow_cell_id,
            e.data_root,
            r.total_reads,
            r.total_bases,
            r.mean_qscore,
            r.n50
        FROM experiments e
        LEFT JOIN read_statistics r ON e.id = r.experiment_id
        ORDER BY r.total_reads DESC
        LIMIT 20
    ''')

    print(f"\n{'Sample ID':<35} {'Protocol':<25} {'Flow Cell':<12} {'Reads':>12} {'Bases':>12} {'Q':>6}")
    print("-"*110)

    for row in cursor.fetchall():
        sample_id = (row[0] or 'N/A')[:34]
        protocol_group = (row[1] or 'N/A')[:24]
        flow_cell = (row[2] or 'N/A')[:11]
        total_reads = f"{row[4]:,}" if row[4] else "N/A"
        total_bases = f"{row[5]/1e6:.1f}M" if row[5] else "N/A"
        mean_qscore = f"{row[6]:.1f}" if row[6] else "N/A"

        print(f"{sample_id:<35} {protocol_group:<25} {flow_cell:<12} {total_reads:>12} {total_bases:>12} {mean_qscore:>6}")

    return total_experiments

def export_registry(conn, output_path):
    """Export experiment registry as JSON for GitHub."""
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            e.id,
            e.experiment_path,
            e.data_root,
            e.unique_id,
            e.instrument,
            e.flow_cell_id,
            e.sample_id,
            e.protocol_group_id,
            e.started,
            r.total_reads,
            r.total_bases,
            r.mean_qscore,
            r.n50
        FROM experiments e
        LEFT JOIN read_statistics r ON e.id = r.experiment_id
        ORDER BY e.started DESC
    ''')

    experiments = []
    for row in cursor.fetchall():
        experiments.append({
            'id': row[0],
            'path': row[1],
            'data_root': row[2],
            'unique_id': row[3],
            'instrument': row[4],
            'flow_cell_id': row[5],
            'sample_id': row[6],
            'protocol_group_id': row[7],
            'started': row[8],
            'total_reads': row[9],
            'total_bases': row[10],
            'mean_qscore': row[11],
            'n50': row[12]
        })

    # Get aggregate end reasons
    cursor.execute('''
        SELECT end_reason, SUM(count) as total_count
        FROM end_reason_distribution
        GROUP BY end_reason
        ORDER BY total_count DESC
    ''')

    end_reasons = {row[0]: row[1] for row in cursor.fetchall()}

    registry = {
        'generated_at': datetime.now().isoformat(),
        'total_experiments': len(experiments),
        'total_reads': sum(e['total_reads'] or 0 for e in experiments),
        'total_bases': sum(e['total_bases'] or 0 for e in experiments),
        'end_reason_distribution': end_reasons,
        'experiments': experiments
    }

    with open(output_path, 'w') as f:
        json.dump(registry, f, indent=2)

    print(f"\nExported registry to: {output_path}")
    return registry

def main():
    print("Comprehensive Nanopore Experiment Database Builder")
    print("="*60)
    print(f"Database: {DB_PATH}")
    print(f"Data roots: {', '.join(DATA_ROOTS)}\n")

    # Create/connect to database
    conn = create_database()

    # Load experiments
    num_experiments = load_experiments_to_db(conn)

    # Generate report
    generate_report(conn)

    # Export registry for GitHub
    registry_path = "/nfs/turbo/umms-atheylab/experiment_registry.json"
    export_registry(conn, registry_path)

    conn.close()
    print(f"\n\nDatabase saved to: {DB_PATH}")

if __name__ == "__main__":
    main()
