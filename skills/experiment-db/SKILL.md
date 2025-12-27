---
name: experiment-db
version: 2.0.0
description: SQLite database for fast querying and tracking of nanopore experiments
author: Single Molecule Sequencing Lab
category: data-management
tags: [nanopore, database, sqlite, experiments, query]
---

# Experiment Database

SQLite-based experiment database that complements the YAML registry with fast SQL queries and persistent storage.

## Features

- **Experiment Discovery**: Automatically finds experiments by locating sequencing_summary files
- **Metadata Parsing**: Extracts metadata from final_summary.txt files
- **Statistics Calculation**: Computes per-experiment statistics (reads, bases, N50, Q-scores)
- **End Reason Tracking**: Stores end_reason distribution for each experiment
- **Fast SQL Queries**: Enables complex queries across all experiments
- **Export Capabilities**: Export to CSV, JSON, or formatted tables

## Installation

```bash
# Required (standard library)
# sqlite3 is included with Python

# Optional (for faster parsing)
pip install pandas
```

## Usage

### Build Database

```bash
# Discover and index experiments from a data directory
python3 experiment_db.py build --data_dir /data1 --db_path experiments.db

# Build from multiple directories
python3 experiment_db.py build \
    --data_dir /data1 /data2 /nfs/turbo/data \
    --db_path experiments.db

# Update existing database with new experiments
python3 experiment_db.py build --data_dir /data1 --db_path experiments.db --update
```

### Query Database

```bash
# Show summary statistics
python3 experiment_db.py query --db_path experiments.db --summary

# List all experiments
python3 experiment_db.py query --db_path experiments.db --list

# Query specific experiment by name
python3 experiment_db.py query --db_path experiments.db --experiment "sample_name"

# Query by instrument
python3 experiment_db.py query --db_path experiments.db --instrument PromethION

# Show end reason distribution
python3 experiment_db.py query --db_path experiments.db --end_reasons
```

### Export Data

```bash
# Export to CSV
python3 experiment_db.py export --db_path experiments.db --format csv --output experiments.csv

# Export to JSON
python3 experiment_db.py export --db_path experiments.db --format json --output experiments.json

# Export specific experiments
python3 experiment_db.py export --db_path experiments.db \
    --filter "total_reads > 1000000" \
    --format csv --output high_yield.csv
```

## Command-Line Options

### build command

| Option | Description |
|--------|-------------|
| `--data_dir` | Directory(ies) to search for experiments |
| `--db_path` | Path to SQLite database file |
| `--update` | Update existing database (don't recreate) |
| `--recursive` | Search directories recursively (default: True) |

### query command

| Option | Description |
|--------|-------------|
| `--db_path` | Path to SQLite database file |
| `--summary` | Show summary statistics |
| `--list` | List all experiments |
| `--experiment NAME` | Query specific experiment |
| `--instrument TYPE` | Filter by instrument type |
| `--end_reasons` | Show end reason distribution |
| `--sql QUERY` | Execute custom SQL query |

### export command

| Option | Description |
|--------|-------------|
| `--db_path` | Path to SQLite database file |
| `--format` | Output format (csv, json, table) |
| `--output` | Output file path |
| `--filter` | SQL WHERE clause filter |

## Database Schema

### experiments table

```sql
CREATE TABLE experiments (
    id INTEGER PRIMARY KEY,
    experiment_path TEXT UNIQUE,
    instrument TEXT,
    flow_cell_id TEXT,
    sample_id TEXT,
    protocol_group_id TEXT,
    protocol TEXT,
    started TEXT,
    acquisition_stopped TEXT,
    pod5_files INTEGER,
    fastq_files INTEGER,
    bam_files INTEGER,
    created_at TEXT
);
```

### read_statistics table

```sql
CREATE TABLE read_statistics (
    id INTEGER PRIMARY KEY,
    experiment_id INTEGER REFERENCES experiments(id),
    total_reads INTEGER,
    passed_reads INTEGER,
    failed_reads INTEGER,
    total_bases INTEGER,
    mean_read_length REAL,
    median_read_length REAL,
    max_read_length INTEGER,
    n50 INTEGER,
    mean_qscore REAL,
    median_qscore REAL,
    mean_duration REAL,
    total_duration_hours REAL
);
```

### end_reason_distribution table

```sql
CREATE TABLE end_reason_distribution (
    id INTEGER PRIMARY KEY,
    experiment_id INTEGER REFERENCES experiments(id),
    end_reason TEXT,
    count INTEGER,
    percentage REAL
);
```

## Output Examples

### Summary Query

```
Database: experiments.db
Total experiments: 145
Total reads: 461,421,627
Total bases: 828.2 Gb

Instruments:
  PromethION: 81 experiments
  MinION: 33 experiments
  P2 Solo: 9 experiments

Date range: 2024-01-15 to 2025-12-08
```

### Experiment Query

```json
{
  "experiment_path": "/data1/12082025_IF_NewBCPart4_SMA_seq/...",
  "instrument": "PromethION",
  "flow_cell_id": "FBD70608",
  "sample_id": "no_sample_id",
  "total_reads": 4688237,
  "total_bases": 18807281227,
  "n50": 5406,
  "mean_qscore": 19.2,
  "end_reasons": {
    "signal_positive": 78.5,
    "data_service_unblock_mux_change": 15.2,
    "unblock_mux_change": 5.1,
    "mux_change": 1.2
  }
}
```

## Integration with ONT Ecosystem

### With ont-experiments Registry

```bash
# Sync database with YAML registry
python3 experiment_db.py sync \
    --registry ~/.ont-registry/experiments.yaml \
    --db_path experiments.db
```

### With Analysis Skills

```bash
# Query database for experiments to analyze
python3 experiment_db.py query --db_path experiments.db \
    --sql "SELECT experiment_path FROM experiments WHERE n50 > 5000" \
    | xargs -I {} python3 ont_smaseq_readlen.py {}
```

## Custom SQL Queries

```bash
# Find high-quality SMAseq experiments
python3 experiment_db.py query --db_path experiments.db \
    --sql "SELECT sample_id, n50, mean_qscore
           FROM experiments e
           JOIN read_statistics r ON e.id = r.experiment_id
           WHERE sample_id LIKE '%SMA%' AND n50 > 2000
           ORDER BY n50 DESC"

# Aggregate end reasons across all experiments
python3 experiment_db.py query --db_path experiments.db \
    --sql "SELECT end_reason, SUM(count) as total, AVG(percentage) as avg_pct
           FROM end_reason_distribution
           GROUP BY end_reason
           ORDER BY total DESC"
```

## Performance

- **Build time**: ~1 minute per 100 experiments
- **Query time**: <100ms for most queries
- **Database size**: ~1 MB per 1000 experiments

## Troubleshooting

### "No experiments found"

1. Check that the data directory contains sequencing_summary.txt files
2. Verify the directory structure follows ONT conventions
3. Try with `--recursive` flag

### "Database locked"

1. Close any other processes using the database
2. Use a different database file path
3. Check file permissions

### "Pandas not available"

The tool works without pandas but is slower. Install for better performance:
```bash
pip install pandas
```

## Version History

- **2.0.0** (2025-12): Major update
  - Added end_reason_distribution table
  - Added export capabilities
  - Improved query interface
  - Added sync with YAML registry

- **1.0.0** (2025-10): Initial release
  - Basic experiment discovery
  - SQLite storage
  - Summary queries
