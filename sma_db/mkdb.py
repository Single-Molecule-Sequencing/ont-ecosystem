#!/usr/bin/env python3
"""
mkdb.py - Database Initialization Script

Creates the SQLite database schema and populates static lookup tables
for the SMA single-pass ingestion pipeline.

Usage:
    python mkdb.py <exp_id>

Output:
    SMA_<exp_id>.db
"""

import argparse
import sqlite3
from pathlib import Path


# Modification bitflag definitions
MODIFICATION_FLAGS = {
    0: 'non',           # No modifications
    1: '6mA',           # N6-methyladenine
    2: '5mCG_5hmCG',    # 5-methylcytosine + 5-hydroxymethylcytosine (CpG context)
    4: '5mC_5hmC',      # 5-methylcytosine + 5-hydroxymethylcytosine (all contexts)
    8: '4mC_5mC',       # 4-methylcytosine + 5-methylcytosine
    16: '5mC',          # 5-methylcytosine only
}


def create_database(exp_id: str, output_dir: Path = None) -> Path:
    """Create and initialize the SQLite database."""

    if output_dir is None:
        output_dir = Path.cwd()

    db_path = output_dir / f"SMA_{exp_id}.db"

    # Remove existing database if present
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # === Create Tables ===

    # Mods table - Modification bitflag lookup
    cursor.execute("""
        CREATE TABLE Mods (
            mod_bitflag INTEGER PRIMARY KEY,
            mods TEXT NOT NULL
        )
    """)

    # Exp table - Experiment metadata
    cursor.execute("""
        CREATE TABLE Exp (
            exp_id TEXT PRIMARY KEY,
            exp_desc TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Refseq table - Reference sequences
    cursor.execute("""
        CREATE TABLE Refseq (
            refseq_id TEXT PRIMARY KEY,
            refseq TEXT NOT NULL,
            reflen INTEGER NOT NULL,
            refseq_range_min INTEGER,
            refseq_range_max INTEGER
        )
    """)

    # Reads table - Main read data
    cursor.execute("""
        CREATE TABLE Reads (
            uniq_id TEXT PRIMARY KEY,
            exp_id TEXT NOT NULL,
            refseq_id TEXT,
            read_id TEXT NOT NULL,
            readseq TEXT NOT NULL,
            readlen INTEGER NOT NULL,
            model_tier TEXT,
            model_ver TEXT,
            trim INTEGER,
            mod_bitflag INTEGER,
            ed INTEGER,
            q_bc REAL,
            q_ld REAL,
            ER TEXT,
            forced INTEGER,
            channel INTEGER,
            well INTEGER,
            pore_type TEXT,
            num_samples INTEGER,
            start_sample INTEGER,
            median_before REAL,
            scale REAL,
            offset REAL,
            start_time TEXT,
            duration REAL,
            FOREIGN KEY (exp_id) REFERENCES Exp(exp_id),
            FOREIGN KEY (refseq_id) REFERENCES Refseq(refseq_id),
            FOREIGN KEY (mod_bitflag) REFERENCES Mods(mod_bitflag)
        )
    """)

    # Create indexes for common queries
    cursor.execute("CREATE INDEX idx_reads_exp ON Reads(exp_id)")
    cursor.execute("CREATE INDEX idx_reads_refseq ON Reads(refseq_id)")
    cursor.execute("CREATE INDEX idx_reads_readlen ON Reads(readlen)")
    cursor.execute("CREATE INDEX idx_reads_q_bc ON Reads(q_bc)")
    cursor.execute("CREATE INDEX idx_reads_q_ld ON Reads(q_ld)")
    cursor.execute("CREATE INDEX idx_reads_ed ON Reads(ed)")
    cursor.execute("CREATE INDEX idx_reads_er ON Reads(ER)")

    # === Populate Mods Table ===

    # Generate all possible modification combinations
    # Bit 0 (1): 6mA - can combine with any C-mod
    # Bits 1-4 (2,4,8,16): C-mods are mutually exclusive

    mod_combinations = []

    # No modifications
    mod_combinations.append((0, 'non'))

    # Single modifications
    for bitflag, mod_name in MODIFICATION_FLAGS.items():
        if bitflag > 0:
            mod_combinations.append((bitflag, mod_name))

    # 6mA combinations with C-mods
    for c_bit in [2, 4, 8, 16]:
        combined_flag = 1 | c_bit  # 6mA + C-mod
        combined_name = f"6mA+{MODIFICATION_FLAGS[c_bit]}"
        mod_combinations.append((combined_flag, combined_name))

    cursor.executemany(
        "INSERT INTO Mods (mod_bitflag, mods) VALUES (?, ?)",
        mod_combinations
    )

    # === Insert Experiment Record ===
    cursor.execute(
        "INSERT INTO Exp (exp_id, exp_desc) VALUES (?, ?)",
        (exp_id, f"SMA experiment {exp_id}")
    )

    conn.commit()
    conn.close()

    return db_path


def main():
    parser = argparse.ArgumentParser(
        description="Initialize SQLite database for SMA pipeline"
    )
    parser.add_argument(
        "exp_id",
        help="Experiment ID (used in database filename)"
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Output directory for database file (default: current directory)"
    )

    args = parser.parse_args()

    db_path = create_database(args.exp_id, args.output_dir)

    print(f"Database created: {db_path}")
    print(f"  - Tables: Mods, Exp, Refseq, Reads")
    print(f"  - Exp ID: {args.exp_id}")

    # Verify
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Mods")
    mod_count = cursor.fetchone()[0]
    print(f"  - Modification flags: {mod_count}")
    conn.close()


if __name__ == "__main__":
    main()
