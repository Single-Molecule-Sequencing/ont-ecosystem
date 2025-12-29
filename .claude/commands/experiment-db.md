---
description: SQLite database for tracking nanopore experiments with fast SQL queries. Use when building experiment databases, querying sequencing statistics, searching for experiments, or running custom SQL on ONT data.
---

# /experiment-db

SQLite database for tracking nanopore experiments with fast SQL queries and statistics.

## Usage

Build and query experiment databases:

$ARGUMENTS

## Commands

### Build Database
```bash
# Build from experiment directory
experiment_db.py build --data_dir /data1 --db_path experiments.db

# Force rebuild
experiment_db.py build --data_dir /data1 --db_path experiments.db --rebuild
```

### Query Database
```bash
# Show summary
experiment_db.py query --db_path experiments.db --summary

# End reason distribution
experiment_db.py query --db_path experiments.db --end_reasons

# Search for experiment
experiment_db.py query --db_path experiments.db --experiment "sample_name"

# Custom SQL
experiment_db.py query --db_path experiments.db --sql "SELECT * FROM experiments WHERE sample_id LIKE '%cyp2d6%'"
```

## Database Schema

### experiments table
| Column | Type | Description |
|--------|------|-------------|
| experiment_path | TEXT | Full path |
| flow_cell_id | TEXT | Flow cell ID |
| sample_id | TEXT | Sample name |
| started | TEXT | Start timestamp |

### read_statistics table
| Column | Type | Description |
|--------|------|-------------|
| total_reads | INTEGER | Read count |
| total_bases | INTEGER | Base count |
| n50 | INTEGER | N50 length |
| mean_qscore | REAL | Mean Q |

### end_reason_distribution table
| Column | Type | Description |
|--------|------|-------------|
| end_reason | TEXT | Category |
| count | INTEGER | Read count |
| percentage | REAL | Percentage |

## Example Queries

```sql
-- High signal_positive experiments
SELECT e.sample_id, erd.percentage
FROM experiments e
JOIN end_reason_distribution erd ON e.id = erd.experiment_id
WHERE erd.end_reason = 'signal_positive' AND erd.percentage > 70;

-- Average N50 by protocol
SELECT protocol, AVG(n50) as avg_n50
FROM experiments e
JOIN read_statistics rs ON e.id = rs.experiment_id
GROUP BY protocol;
```

## Dependencies

- sqlite3 (standard library)
- pandas (optional)
