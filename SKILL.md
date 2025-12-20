---
name: ont-monitor
description: "Real-time and retrospective Oxford Nanopore sequencing run monitoring. Use when tracking active sequencing runs, analyzing completed run performance, checking throughput/quality/pore activity metrics, generating run reports, or diagnosing sequencing issues. Integrates with ont-experiments for provenance tracking via Pattern B orchestration."
license: MIT
repository: https://github.com/Single-Molecule-Sequencing/ont-ecosystem
---

# ONT Monitor - Run Monitoring & Metrics

## Overview

Real-time and retrospective monitoring for Oxford Nanopore sequencing runs. Provides dashboards, metrics extraction, alerts, and integration with the ont-experiments registry.

### Key Capabilities

1. **Live Monitoring**: Real-time dashboard during active sequencing
2. **Metrics Extraction**: Parse sequencing_summary.txt and final_summary.txt
3. **Time-Series Analysis**: Track throughput, quality, pore activity over time
4. **Quality Thresholds**: Configurable alerts for QC failures
5. **Pattern B Integration**: Automatic provenance tracking via ont-experiments

## Installation

Part of the ONT Ecosystem:

```bash
curl -sSL https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/install.sh | bash
source ~/.ont-ecosystem/env.sh
```

## Quick Start

```bash
# Monitor completed run
ont_monitor.py /path/to/run --json metrics.json

# Live monitoring during sequencing
ont_monitor.py /path/to/run --live --interval 60

# With provenance tracking (recommended)
ont_experiments.py run monitoring exp-abc123 --json metrics.json
```

## Commands Reference

### Basic Monitoring

```bash
# Analyze completed run
ont_monitor.py <run_path>

# Output as JSON
ont_monitor.py <run_path> --json metrics.json

# ASCII dashboard
ont_monitor.py <run_path> --dashboard
```

### Live Monitoring

```bash
# Live mode with 60-second refresh
ont_monitor.py <run_path> --live --interval 60

# Live with alerts
ont_monitor.py <run_path> --live --alert-qscore 10 --alert-throughput 1000000

# Stop after N updates
ont_monitor.py <run_path> --live --max-updates 100
```

### Time-Series Analysis

```bash
# Generate time-series data
ont_monitor.py <run_path> --timeseries ts.json

# Plot throughput over time
ont_monitor.py <run_path> --plot throughput.png

# Specify time window
ont_monitor.py <run_path> --timeseries ts.json --window 3600
```

### Pattern B Integration

```bash
# Run via ont-experiments for provenance tracking
ont_experiments.py run monitoring exp-abc123 --json metrics.json

# Live monitoring with provenance
ont_experiments.py run monitoring exp-abc123 --live --interval 60
```

## Metrics Extracted

### From sequencing_summary.txt

| Metric | Description |
|--------|-------------|
| `total_reads` | Total number of reads |
| `total_bases` | Total bases sequenced |
| `mean_qscore` | Mean quality score |
| `median_qscore` | Median quality score |
| `n50` | Read length N50 |
| `mean_length` | Mean read length |
| `max_length` | Maximum read length |
| `pass_reads` | Reads passing QC filter |
| `pass_bases` | Bases from passing reads |

### From final_summary.txt

| Metric | Description |
|--------|-------------|
| `protocol` | Sequencing protocol |
| `sample_id` | Sample identifier |
| `flow_cell_id` | Flow cell ID |
| `run_id` | Run identifier |
| `started` | Run start time |
| `ended` | Run end time |
| `duration_hours` | Total run duration |
| `yield_gb` | Total yield in GB |

### Derived Metrics

| Metric | Description |
|--------|-------------|
| `throughput_bases_per_hour` | Sequencing throughput |
| `pore_efficiency` | Active pore percentage |
| `quality_pass_rate` | Percentage of reads passing QC |
| `is_active` | Whether run is still active |

## JSON Output Format

```json
{
  "run_path": "/path/to/run",
  "timestamp": "2024-01-15T12:00:00Z",
  "is_active": false,
  "summary": {
    "total_reads": 15000000,
    "total_bases": 75000000000,
    "mean_qscore": 18.5,
    "median_qscore": 19.2,
    "n50": 12500,
    "mean_length": 5000,
    "pass_reads": 14250000,
    "pass_bases": 71250000000,
    "pass_rate": 0.95
  },
  "run_info": {
    "protocol": "sequencing/sequencing_MIN114_DNA_e8_2_400K",
    "sample_id": "CYP2D6_cohort",
    "flow_cell_id": "FAW12345",
    "run_id": "abc123def456",
    "started": "2024-01-15T08:00:00Z",
    "duration_hours": 48.5
  },
  "throughput": {
    "bases_per_hour": 1546391753,
    "reads_per_hour": 309278,
    "yield_gb": 75.0
  },
  "quality": {
    "mean_qscore": 18.5,
    "q10_rate": 0.98,
    "q20_rate": 0.45,
    "quality_status": "PASS"
  },
  "alerts": []
}
```

## Dashboard Display

```
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘                    ONT Run Monitoring Dashboard                   â•‘
â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£
â•‘ Run: /nfs/turbo/umms-athey/runs/20240115                         â•‘
â•‘ Status: ACTIVE â— | Updated: 2024-01-15 14:32:00                  â•‘
â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•¦â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£
â•‘ THROUGHPUT            â•‘ QUALITY                                  â•‘
â•‘ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€     â•‘ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€                        â•‘
â•‘ Total Reads: 15.0M    â•‘ Mean Q-Score: 18.5                       â•‘
â•‘ Total Bases: 75.0 Gb  â•‘ Median Q-Score: 19.2                     â•‘
â•‘ N50: 12.5 kb          â•‘ Pass Rate: 95.0%                         â•‘
â•‘ Mean Length: 5.0 kb   â•‘ Q20 Rate: 45.0%                          â•‘
â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•¬â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£
â•‘ PERFORMANCE           â•‘ RUN INFO                                 â•‘
â•‘ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€     â•‘ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€                        â•‘
â•‘ Throughput: 1.5 Gb/hr â•‘ Sample: CYP2D6_cohort                    â•‘
â•‘ Reads/hr: 309.3K      â•‘ Flow Cell: FAW12345                      â•‘
â•‘ Duration: 48.5 hrs    â•‘ Protocol: DNA_e8_2_400K                  â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•©â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
```

## Quality Thresholds

Default thresholds (configurable):

| Metric | PASS | WARN | FAIL |
|--------|------|------|------|
| Mean Q-Score | â‰¥15 | 10-15 | <10 |
| Pass Rate | â‰¥90% | 80-90% | <80% |
| N50 | â‰¥5kb | 2-5kb | <2kb |

```bash
# Custom thresholds
ont_monitor.py <run_path> \
  --qscore-pass 15 --qscore-warn 10 \
  --passrate-pass 0.9 --passrate-warn 0.8 \
  --n50-pass 5000 --n50-warn 2000
```

## Alert Configuration

```bash
# Email alerts (requires SMTP config)
ont_monitor.py <run_path> --live \
  --alert-email user@example.com \
  --alert-qscore 10 \
  --alert-throughput 500000000

# Slack webhook
ont_monitor.py <run_path> --live \
  --alert-slack https://hooks.slack.com/... \
  --alert-pore-death 0.5
```

## Time-Series Analysis

### Generate Time-Series Data

```bash
ont_monitor.py <run_path> --timeseries ts.json --window 3600
```

### Time-Series JSON Format

```json
{
  "run_path": "/path/to/run",
  "window_seconds": 3600,
  "datapoints": [
    {
      "timestamp": "2024-01-15T08:00:00Z",
      "hour": 0,
      "cumulative_reads": 150000,
      "cumulative_bases": 750000000,
      "hourly_reads": 150000,
      "hourly_bases": 750000000,
      "mean_qscore": 18.2
    },
    {
      "timestamp": "2024-01-15T09:00:00Z",
      "hour": 1,
      "cumulative_reads": 310000,
      "cumulative_bases": 1550000000,
      "hourly_reads": 160000,
      "hourly_bases": 800000000,
      "mean_qscore": 18.5
    }
  ]
}
```

## Python API

```python
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/path/to/ont-ecosystem/bin')
from ont_monitor import RunMonitor, parse_sequencing_summary

# Initialize monitor
monitor = RunMonitor('/path/to/run')

# Get current metrics
metrics = monitor.get_metrics()
print(f"Total reads: {metrics['summary']['total_reads']:,}")
print(f"Mean Q-Score: {metrics['quality']['mean_qscore']:.1f}")

# Check if active
if monitor.is_active():
    print("Run is still active!")

# Get time-series
ts = monitor.get_timeseries(window_seconds=3600)
for dp in ts['datapoints']:
    print(f"Hour {dp['hour']}: {dp['hourly_bases']/1e9:.2f} Gb")

# Check alerts
alerts = monitor.check_alerts(qscore_min=10, throughput_min=1e9)
for alert in alerts:
    print(f"ALERT: {alert['type']}: {alert['message']}")
```

## Integration with ont-experiments

When run via Pattern B, monitoring results are captured in the experiment registry:

```bash
# Run with provenance
ont_experiments.py run monitoring exp-abc123 --json metrics.json

# View in history
ont_experiments.py history exp-abc123
```

Registry event:
```yaml
- timestamp: "2024-01-15T14:32:00Z"
  type: analysis
  analysis: monitoring
  command: "ont_monitor.py /path/to/run --json metrics.json"
  parameters:
    output_json: metrics.json
  outputs:
    - path: /path/metrics.json
      checksum: sha256:abc123...
  results:
    total_reads: 15000000
    total_bases: 75000000000
    mean_qscore: 18.5
    n50: 12500
    is_active: false
  duration_seconds: 5
  exit_code: 0
```

## File Detection

The monitor looks for these files:

| File | Purpose |
|------|---------|
| `sequencing_summary*.txt` | Per-read metrics |
| `final_summary*.txt` | Run-level summary |
| `report*.json` | MinKNOW report |
| `pore_activity*.csv` | Pore activity data |

## Troubleshooting

### No Data Found

```bash
# Check for expected files
ls -la /path/to/run/sequencing_summary*.txt
ls -la /path/to/run/final_summary*.txt

# Run in verbose mode
ont_monitor.py /path/to/run --verbose
```

### Parsing Errors

```bash
# Check file format
head -5 /path/to/run/sequencing_summary_*.txt

# Specify file explicitly
ont_monitor.py /path/to/run --summary-file /path/to/specific_file.txt
```

## Related Skills

- **ont-experiments**: Core registry (run monitoring via Pattern B)
- **end-reason**: Read end reason QC
- **ont-align**: Alignment metrics
- **dorado-bench**: Basecalling quality metrics

## Author

Single Molecule Sequencing Lab, Athey Lab, University of Michigan
