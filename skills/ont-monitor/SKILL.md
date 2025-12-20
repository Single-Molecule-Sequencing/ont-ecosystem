---
name: ont-monitor
description: Real-time and retrospective Oxford Nanopore sequencing run monitoring. Use when tracking active sequencing runs, analyzing completed run performance, checking throughput/quality/pore activity metrics, generating run reports, or diagnosing sequencing issues. Integrates with ont-experiments for provenance tracking via Pattern B orchestration.
---

# ONT Monitor - Sequencing Run Monitoring

Monitor Oxford Nanopore sequencing runs in real-time or analyze completed runs retrospectively.

## Integration with ont-experiments

This skill uses **Pattern B orchestration**:

```bash
# Recommended: Run through ont-experiments for full provenance tracking
ont_experiments.py run monitoring exp-abc123 --live
ont_experiments.py run monitoring exp-abc123 --json report.json --plot metrics.png

# Direct execution (no registry event logging)
python3 ont_monitor.py /path/to/run --live
```

When run through `ont_experiments.py run`, automatically captures:
- Full command with parameters
- Output file checksums
- Duration and exit code
- HPC metadata (SLURM job ID, nodes)
- Results summary in registry

## Quick Start

```bash
# Live monitoring dashboard (auto-refresh every 30s)
ont_monitor.py /path/to/run --live

# Single snapshot with outputs
ont_monitor.py /path/to/run --json metrics.json --plot run.png --csv timeseries.csv

# Quiet mode (JSON only, no terminal output)
ont_monitor.py /path/to/run --json metrics.json --quiet

# Custom thresholds
ont_monitor.py /path/to/run --min-qscore 12 --min-n50 5000 --live
```

## Data Sources

Auto-detects and uses available sources (priority order):

| Source | File Pattern | Live Support | Best For |
|--------|--------------|--------------|----------|
| sequencing_summary | `sequencing_summary*.txt` | ✓ Yes | Read stats, Q-scores, lengths |
| final_summary | `final_summary*.txt` | No | Run metadata, completion stats |
| POD5 | `*.pod5` | Limited | Run metadata, read counts |
| MinKNOW logs | `*.log`, `*.csv` | ✓ Yes | Pore activity, channel states |

## Metrics Tracked

### Read Statistics
- Total reads and bases
- Pass/fail counts and rate
- Mean/median Q-score
- Mean/median read length
- N50, longest read

### Throughput
- Reads per hour
- Bases per hour (Mb/h, Gb/h)
- Cumulative yield over time
- Estimated time to target

### Pore Activity
- Active pore count and percentage
- Channel occupancy
- Sequencing/available/adapter states
- Mux scan results

### Quality Trends
- Q-score over time
- N50 progression
- Pass rate trends

## Alert Thresholds

Default thresholds (configurable via CLI):

| Metric | Threshold | Alert Level |
|--------|-----------|-------------|
| Mean Q-score | < 10 | Warning |
| N50 | < 1,000 bp | Warning |
| Active pores | < 50% | Warning |
| Reads/hour | < 10,000 | Warning |
| Bases/hour | < 100 Mb | Warning |
| Pass rate | < 80% | Warning |

## Output Formats

### JSON (--json)

```json
{
  "snapshot_time": "2024-01-15T12:00:00Z",
  "is_active": true,
  "metadata": {
    "run_id": "abc123",
    "flow_cell_id": "FAX12345",
    "sample_id": "sample_01",
    "duration_hours": 24.5
  },
  "read_stats": {
    "count": 5000000,
    "total_bases": 25000000000,
    "mean_qscore": 15.2,
    "n50": 12500
  },
  "time_series": [...],
  "alerts": [...]
}
```

### Plot (--plot)

Four-panel figure showing:
1. Cumulative yield over time
2. Throughput rate (Mb/hour)
3. Cumulative read count
4. Q-score trend

### CSV (--csv)

Time-series data with columns: timestamp, cumulative_reads, cumulative_bases, reads_per_hour, bases_per_hour, mean_qscore, n50, active_pores

## CLI Reference

```
ont_monitor.py <path> [options]

Arguments:
  path                  Run directory path

Mode:
  --live               Live dashboard with auto-refresh
  --snapshot           Single snapshot (default)
  --history            Full time-series analysis

Output:
  --json FILE          Output JSON summary
  --plot FILE          Output metrics plot (PNG/PDF)
  --csv FILE           Output time-series CSV

Live options:
  --interval SEC       Refresh interval (default: 30)

Thresholds:
  --min-qscore FLOAT   Override min Q-score threshold
  --min-n50 INT        Override min N50 threshold

Display:
  --no-color           Disable colored output
  --quiet              Suppress terminal output
  --verbose            Show detailed progress
```

## Workflow Examples

### Monitor Active PromethION Run

```bash
# Start live monitoring
ont_experiments.py run monitoring exp-promethion-001 \
  --live \
  --interval 60 \
  --json /path/to/live_metrics.json

# Or direct
ont_monitor.py /data/promethion/run_20240115 --live --interval 60
```

### Post-Run Analysis

```bash
# Generate comprehensive report
ont_experiments.py run monitoring exp-completed-001 \
  --json final_report.json \
  --plot final_metrics.png \
  --csv timeseries.csv
```

### Batch Analysis

```bash
# Analyze all runs with a tag
for exp in $(ont_experiments.py list --tag batch1 --format ids); do
  ont_experiments.py run monitoring $exp --json ${exp}_metrics.json --quiet
done
```

### HPC Monitoring Job

```bash
# Submit long-running monitor
sbatch --job-name=ont-monitor --time=72:00:00 --wrap="\
  ont_experiments.py run monitoring exp-abc123 \
    --live --interval 300 --json metrics.json"
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success, no alerts |
| 1 | Success, warnings present |
| 2 | Success, critical alerts present |

## Dependencies

```
pod5>=0.3.0        # POD5 support (recommended)
h5py>=3.0.0        # Fast5 support (optional)
matplotlib>=3.5    # Plotting (optional)
pandas>=1.3        # CSV export (optional)
numpy>=1.20        # Statistics (optional)
```

## Interpreting Results

See [references/metric_interpretation.md](references/metric_interpretation.md) for detailed guidance on:
- Expected metric ranges by device type
- Troubleshooting common issues
- Correlating metrics with run quality
