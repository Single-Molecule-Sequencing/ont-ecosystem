# /ont-monitor

Real-time and retrospective Oxford Nanopore sequencing run monitoring.

## Usage

Monitor sequencing runs:

$ARGUMENTS

## Quick Start

```bash
# Live monitoring dashboard
ont_monitor.py /path/to/run --live

# Single snapshot with outputs
ont_monitor.py /path/to/run --json metrics.json --plot run.png --csv timeseries.csv

# Custom thresholds
ont_monitor.py /path/to/run --min-qscore 12 --min-n50 5000 --live

# With provenance tracking
ont_experiments.py run monitoring exp-abc123 --live
```

## Metrics Tracked

### Read Statistics
- Total reads and bases
- Pass/fail counts
- Mean/median Q-score
- N50, longest read

### Throughput
- Reads/bases per hour
- Cumulative yield
- Estimated time to target

### Pore Activity
- Active pore count
- Channel occupancy
- Sequencing states

## Alert Thresholds

| Metric | Threshold | Alert |
|--------|-----------|-------|
| Mean Q-score | < 10 | Warning |
| N50 | < 1,000 bp | Warning |
| Active pores | < 50% | Warning |
| Reads/hour | < 10,000 | Warning |
| Pass rate | < 80% | Warning |

## Output Formats

### JSON (--json)
```json
{
  "is_active": true,
  "metadata": {"run_id": "abc123", "flow_cell_id": "FAX12345"},
  "read_stats": {"count": 5000000, "mean_qscore": 15.2, "n50": 12500},
  "alerts": []
}
```

### Plot (--plot)
Four-panel figure: yield, throughput, read count, Q-score trend

### CSV (--csv)
Time-series: timestamp, reads, bases, qscore, n50

## CLI Options

```
ont_monitor.py <path> [options]

Mode:
  --live               Live dashboard
  --snapshot           Single snapshot (default)
  --history            Full time-series

Output:
  --json FILE          JSON summary
  --plot FILE          Metrics plot
  --csv FILE           Time-series CSV

Live:
  --interval SEC       Refresh interval (default: 30)

Thresholds:
  --min-qscore FLOAT   Min Q-score
  --min-n50 INT        Min N50
```

## Dependencies

- pod5
- matplotlib
- pandas
- numpy
