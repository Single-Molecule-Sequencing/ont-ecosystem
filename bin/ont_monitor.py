#!/usr/bin/env python3
"""
ONT Monitor - Real-time and retrospective Oxford Nanopore run monitoring.

Features:
- Live monitoring during active sequencing runs
- Retrospective analysis of completed runs
- Multiple data sources: MinKNOW logs, sequencing_summary, POD5, final_summary
- Terminal dashboard with auto-refresh
- JSON snapshots for programmatic access
- Time-series plots for visualization
- Configurable alerts/thresholds

Usage:
  ont_monitor.py /path/to/run --live                    # Live dashboard
  ont_monitor.py /path/to/run --snapshot --json out.json  # Single snapshot
  ont_monitor.py /path/to/run --plot metrics.png        # Generate plots
  ont_monitor.py /path/to/run --history --json history.json  # Full history

Integration with ont-experiments:
  ont_experiments.py run monitoring exp-abc123 --live
"""

import argparse
import json
import os
import sys
import time
import glob
import re
import signal
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple, Iterator
from collections import defaultdict
import threading

# Optional imports
try:
    import pod5
    HAS_POD5 = True
except ImportError:
    HAS_POD5 = False

try:
    import h5py
    HAS_H5PY = True
except ImportError:
    HAS_H5PY = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


# =============================================================================
# Configuration & Thresholds
# =============================================================================

DEFAULT_THRESHOLDS = {
    # Pore activity
    "min_active_pores_pct": 50.0,      # Alert if <50% pores active
    "min_channel_occupancy": 0.3,       # Alert if <30% occupancy
    
    # Quality
    "min_mean_qscore": 10.0,            # Alert if mean Q < 10
    "min_pass_rate": 0.8,               # Alert if <80% reads pass
    
    # Throughput
    "min_reads_per_hour": 10000,        # Alert if throughput drops
    "min_bases_per_hour": 100_000_000,  # 100Mb/hour minimum
    
    # N50
    "min_n50": 1000,                    # Alert if N50 < 1kb
    
    # Run health
    "max_mux_scan_interval_min": 120,   # Alert if no mux scan in 2h
}

# MinKNOW log patterns
MINKNOW_PATTERNS = {
    "run_start": r"Run started: (.+)",
    "run_id": r"run_id=([a-f0-9\-]+)",
    "protocol": r"protocol: (.+)",
    "flow_cell_id": r"flow_cell_id: (\w+)",
    "sample_id": r"sample_id: (.+)",
    "mux_scan": r"Mux scan complete.+active_pores=(\d+)",
    "reads_written": r"(\d+) reads? written",
    "bases_written": r"([\d,]+) bases? written",
    "channel_states": r"channel_states: (.+)",
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ReadStats:
    """Statistics for a collection of reads."""
    count: int = 0
    total_bases: int = 0
    pass_count: int = 0
    fail_count: int = 0
    mean_qscore: float = 0.0
    median_qscore: float = 0.0
    mean_length: float = 0.0
    median_length: float = 0.0
    n50: int = 0
    longest_read: int = 0
    shortest_read: int = 0
    lengths: List[int] = field(default_factory=list, repr=False)
    qscores: List[float] = field(default_factory=list, repr=False)
    
    def compute_derived(self):
        """Compute derived statistics from lengths and qscores."""
        if self.lengths:
            self.count = len(self.lengths)
            self.total_bases = sum(self.lengths)
            self.mean_length = self.total_bases / self.count
            self.longest_read = max(self.lengths)
            self.shortest_read = min(self.lengths)
            
            sorted_lengths = sorted(self.lengths, reverse=True)
            self.median_length = sorted_lengths[len(sorted_lengths) // 2]
            
            # N50 calculation
            cumsum = 0
            half_total = self.total_bases / 2
            for length in sorted_lengths:
                cumsum += length
                if cumsum >= half_total:
                    self.n50 = length
                    break
        
        if self.qscores:
            self.mean_qscore = sum(self.qscores) / len(self.qscores)
            sorted_qscores = sorted(self.qscores)
            self.median_qscore = sorted_qscores[len(sorted_qscores) // 2]
    
    def to_dict(self, include_arrays: bool = False) -> Dict:
        d = {
            "count": self.count,
            "total_bases": self.total_bases,
            "pass_count": self.pass_count,
            "fail_count": self.fail_count,
            "mean_qscore": round(self.mean_qscore, 2),
            "median_qscore": round(self.median_qscore, 2),
            "mean_length": round(self.mean_length, 1),
            "median_length": round(self.median_length, 1),
            "n50": self.n50,
            "longest_read": self.longest_read,
            "shortest_read": self.shortest_read,
        }
        if include_arrays:
            d["lengths"] = self.lengths
            d["qscores"] = self.qscores
        return d


@dataclass
class PoreActivity:
    """Pore and channel activity metrics."""
    total_channels: int = 512  # MinION default
    active_pores: int = 0
    sequencing: int = 0
    pore_available: int = 0
    adapter: int = 0
    unclassified: int = 0
    inactive: int = 0
    
    @property
    def active_pct(self) -> float:
        return (self.active_pores / self.total_channels * 100) if self.total_channels else 0
    
    @property
    def occupancy(self) -> float:
        return (self.sequencing / self.active_pores) if self.active_pores else 0
    
    def to_dict(self) -> Dict:
        return {
            "total_channels": self.total_channels,
            "active_pores": self.active_pores,
            "active_pct": round(self.active_pct, 1),
            "sequencing": self.sequencing,
            "pore_available": self.pore_available,
            "adapter": self.adapter,
            "unclassified": self.unclassified,
            "inactive": self.inactive,
            "occupancy": round(self.occupancy, 3),
        }


@dataclass
class TimePoint:
    """Metrics at a specific time point."""
    timestamp: datetime
    cumulative_reads: int = 0
    cumulative_bases: int = 0
    reads_per_hour: float = 0.0
    bases_per_hour: float = 0.0
    mean_qscore: float = 0.0
    n50: int = 0
    active_pores: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "cumulative_reads": self.cumulative_reads,
            "cumulative_bases": self.cumulative_bases,
            "reads_per_hour": round(self.reads_per_hour, 1),
            "bases_per_hour": round(self.bases_per_hour, 0),
            "mean_qscore": round(self.mean_qscore, 2),
            "n50": self.n50,
            "active_pores": self.active_pores,
        }


@dataclass
class RunMetadata:
    """Run identification and configuration."""
    run_id: str = ""
    run_path: str = ""
    flow_cell_id: str = ""
    sample_id: str = ""
    protocol: str = ""
    kit: str = ""
    experiment_name: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    device_type: str = ""  # MinION, GridION, PromethION
    device_id: str = ""
    software_version: str = ""
    
    @property
    def duration(self) -> Optional[timedelta]:
        if self.start_time:
            end = self.end_time or datetime.now(timezone.utc)
            return end - self.start_time
        return None
    
    @property
    def duration_hours(self) -> float:
        d = self.duration
        return d.total_seconds() / 3600 if d else 0.0
    
    def to_dict(self) -> Dict:
        d = {
            "run_id": self.run_id,
            "run_path": self.run_path,
            "flow_cell_id": self.flow_cell_id,
            "sample_id": self.sample_id,
            "protocol": self.protocol,
            "kit": self.kit,
            "experiment_name": self.experiment_name,
            "device_type": self.device_type,
            "device_id": self.device_id,
            "software_version": self.software_version,
        }
        if self.start_time:
            d["start_time"] = self.start_time.isoformat()
        if self.end_time:
            d["end_time"] = self.end_time.isoformat()
        if self.duration:
            d["duration_hours"] = round(self.duration_hours, 2)
        return d


@dataclass
class Alert:
    """Alert/warning from monitoring."""
    timestamp: datetime
    level: str  # info, warning, critical
    category: str  # throughput, quality, pores, run_health
    message: str
    metric_name: str = ""
    metric_value: Any = None
    threshold: Any = None
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "category": self.category,
            "message": self.message,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
        }


@dataclass
class MonitoringSnapshot:
    """Complete snapshot of run state at a moment in time."""
    snapshot_time: datetime
    metadata: RunMetadata
    read_stats: ReadStats
    pore_activity: PoreActivity
    time_series: List[TimePoint]
    alerts: List[Alert]
    data_sources: List[str]
    is_active: bool = False
    estimated_completion: Optional[datetime] = None
    target_yield_gb: Optional[float] = None
    current_yield_gb: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "snapshot_time": self.snapshot_time.isoformat(),
            "is_active": self.is_active,
            "metadata": self.metadata.to_dict(),
            "read_stats": self.read_stats.to_dict(),
            "pore_activity": self.pore_activity.to_dict(),
            "time_series": [tp.to_dict() for tp in self.time_series],
            "alerts": [a.to_dict() for a in self.alerts],
            "data_sources": self.data_sources,
            "current_yield_gb": round(self.current_yield_gb, 3),
            "target_yield_gb": self.target_yield_gb,
            "estimated_completion": self.estimated_completion.isoformat() if self.estimated_completion else None,
        }


# =============================================================================
# Data Source Parsers
# =============================================================================

class SequencingSummaryParser:
    """Parse sequencing_summary.txt files (works during active runs)."""
    
    def __init__(self, path: Path):
        self.path = path
        self.last_position = 0
        self.header = None
        self.column_indices = {}
        
    def _parse_header(self, header_line: str):
        """Parse header and store column indices."""
        self.header = header_line.strip().split('\t')
        important_cols = [
            'read_id', 'run_id', 'channel', 'start_time', 'duration',
            'sequence_length_template', 'mean_qscore_template',
            'passes_filtering', 'end_reason', 'sample_id', 'flow_cell_id'
        ]
        for col in important_cols:
            if col in self.header:
                self.column_indices[col] = self.header.index(col)
    
    def parse_incremental(self) -> Iterator[Dict]:
        """Parse new lines since last read (for live monitoring)."""
        if not self.path.exists():
            return
        
        with open(self.path, 'r') as f:
            f.seek(self.last_position)
            
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                if self.header is None:
                    self._parse_header(line)
                    continue
                
                fields = line.split('\t')
                if len(fields) != len(self.header):
                    continue
                
                record = {}
                for name, idx in self.column_indices.items():
                    record[name] = fields[idx]
                
                # Type conversions
                if 'sequence_length_template' in record:
                    try:
                        record['length'] = int(record['sequence_length_template'])
                    except ValueError:
                        record['length'] = 0
                
                if 'mean_qscore_template' in record:
                    try:
                        record['qscore'] = float(record['mean_qscore_template'])
                    except ValueError:
                        record['qscore'] = 0.0
                
                if 'passes_filtering' in record:
                    record['passes'] = record['passes_filtering'].lower() == 'true'
                
                if 'start_time' in record:
                    try:
                        record['start_time_seconds'] = float(record['start_time'])
                    except ValueError:
                        pass
                
                yield record
            
            self.last_position = f.tell()
    
    def parse_all(self) -> List[Dict]:
        """Parse entire file."""
        self.last_position = 0
        self.header = None
        return list(self.parse_incremental())
    
    def get_stats(self, records: List[Dict]) -> ReadStats:
        """Compute ReadStats from parsed records."""
        stats = ReadStats()
        stats.lengths = [r['length'] for r in records if 'length' in r and r['length'] > 0]
        stats.qscores = [r['qscore'] for r in records if 'qscore' in r]
        stats.pass_count = sum(1 for r in records if r.get('passes', False))
        stats.fail_count = len(records) - stats.pass_count
        stats.compute_derived()
        return stats


class FinalSummaryParser:
    """Parse final_summary.txt for completed runs."""
    
    @staticmethod
    def parse(path: Path) -> Dict[str, Any]:
        """Parse final summary file."""
        result = {}
        if not path.exists():
            return result
        
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Type conversion
                    if value.isdigit():
                        value = int(value)
                    elif value.replace('.', '').replace('-', '').isdigit():
                        try:
                            value = float(value)
                        except ValueError:
                            pass
                    
                    result[key] = value
        
        return result


class MinKNOWLogParser:
    """Parse MinKNOW log files for real-time metrics."""
    
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.last_positions = {}
    
    def find_logs(self) -> List[Path]:
        """Find all MinKNOW log files."""
        patterns = [
            "**/*.log",
            "**/minknow*.log",
            "**/duty_time*.csv",
            "**/throughput*.csv",
        ]
        logs = []
        for pattern in patterns:
            logs.extend(self.log_dir.glob(pattern))
        return sorted(logs, key=lambda p: p.stat().st_mtime, reverse=True)
    
    def parse_duty_time_csv(self, path: Path) -> List[Dict]:
        """Parse duty_time.csv for channel state history."""
        records = []
        if not path.exists():
            return records
        
        try:
            with open(path, 'r') as f:
                header = None
                for line in f:
                    parts = line.strip().split(',')
                    if header is None:
                        header = parts
                        continue
                    if len(parts) == len(header):
                        records.append(dict(zip(header, parts)))
        except Exception:
            pass
        
        return records
    
    def parse_throughput_csv(self, path: Path) -> List[TimePoint]:
        """Parse throughput.csv for time series data."""
        points = []
        if not path.exists():
            return points
        
        try:
            with open(path, 'r') as f:
                header = None
                for line in f:
                    parts = line.strip().split(',')
                    if header is None:
                        header = parts
                        continue
                    if len(parts) == len(header):
                        row = dict(zip(header, parts))
                        tp = TimePoint(
                            timestamp=datetime.fromisoformat(row.get('timestamp', '')),
                            cumulative_reads=int(row.get('reads', 0)),
                            cumulative_bases=int(row.get('bases', 0)),
                        )
                        points.append(tp)
        except Exception:
            pass
        
        return points


class POD5Parser:
    """Extract statistics from POD5 files."""
    
    @staticmethod
    def get_file_stats(pod5_path: Path) -> Dict:
        """Get basic stats from a POD5 file."""
        if not HAS_POD5:
            return {"error": "pod5 not installed"}
        
        stats = {
            "file": str(pod5_path),
            "read_count": 0,
            "total_samples": 0,
        }
        
        try:
            with pod5.Reader(pod5_path) as reader:
                for read in reader.reads():
                    stats["read_count"] += 1
                    stats["total_samples"] += read.num_samples
                    
                    # Get run info from first read
                    if stats["read_count"] == 1:
                        run_info = read.run_info
                        stats["run_id"] = run_info.acquisition_id
                        stats["flow_cell_id"] = run_info.flow_cell_id
                        stats["sample_id"] = run_info.sample_id
                        stats["experiment_name"] = run_info.experiment_name
                        stats["protocol"] = run_info.protocol_name
                        stats["device_type"] = run_info.system_type
        except Exception as e:
            stats["error"] = str(e)
        
        return stats
    
    @staticmethod
    def scan_directory(directory: Path, limit: int = 100) -> Tuple[Dict, List[Dict]]:
        """Scan directory for POD5 files and aggregate stats."""
        if not HAS_POD5:
            return {"error": "pod5 not installed"}, []
        
        pod5_files = list(directory.glob("**/*.pod5"))[:limit]
        
        aggregate = {
            "file_count": len(pod5_files),
            "total_reads": 0,
            "total_samples": 0,
        }
        file_stats = []
        
        for pod5_path in pod5_files:
            stats = POD5Parser.get_file_stats(pod5_path)
            file_stats.append(stats)
            if "error" not in stats:
                aggregate["total_reads"] += stats["read_count"]
                aggregate["total_samples"] += stats["total_samples"]
                
                # Capture metadata from first file
                if "run_id" not in aggregate and "run_id" in stats:
                    for key in ["run_id", "flow_cell_id", "sample_id", "experiment_name", "protocol", "device_type"]:
                        if key in stats:
                            aggregate[key] = stats[key]
        
        return aggregate, file_stats


# =============================================================================
# Run Monitor Core
# =============================================================================

class RunMonitor:
    """Main monitoring orchestrator."""
    
    def __init__(self, run_path: Path, thresholds: Dict = None):
        self.run_path = Path(run_path)
        self.thresholds = thresholds or DEFAULT_THRESHOLDS
        self.alerts = []
        self.time_series = []
        self.data_sources = []
        
        # Parsers
        self.seq_summary_parser = None
        self.minknow_parser = None
        
        # State
        self.metadata = RunMetadata(run_path=str(self.run_path))
        self.read_stats = ReadStats()
        self.pore_activity = PoreActivity()
        
        self._detect_data_sources()
    
    def _detect_data_sources(self):
        """Detect available data sources."""
        # Sequencing summary
        patterns = [
            "sequencing_summary*.txt",
            "**/sequencing_summary*.txt",
            "fastq_*/sequencing_summary*.txt",
        ]
        for pattern in patterns:
            matches = list(self.run_path.glob(pattern))
            if matches:
                self.seq_summary_parser = SequencingSummaryParser(matches[0])
                self.data_sources.append(f"sequencing_summary:{matches[0].name}")
                break
        
        # Final summary
        final_summary = self.run_path / "final_summary.txt"
        if not final_summary.exists():
            final_summary = next(self.run_path.glob("**/final_summary*.txt"), None)
        if final_summary and final_summary.exists():
            self.data_sources.append(f"final_summary:{final_summary.name}")
        
        # POD5 files
        pod5_files = list(self.run_path.glob("**/*.pod5"))
        if pod5_files:
            self.data_sources.append(f"pod5:{len(pod5_files)}_files")
        
        # MinKNOW logs
        log_dirs = [
            self.run_path / "other_reports",
            self.run_path / "logs",
            self.run_path,
        ]
        for log_dir in log_dirs:
            if log_dir.exists():
                logs = list(log_dir.glob("*.log")) + list(log_dir.glob("*.csv"))
                if logs:
                    self.minknow_parser = MinKNOWLogParser(log_dir)
                    self.data_sources.append(f"minknow_logs:{log_dir.name}")
                    break
    
    def _check_thresholds(self, snapshot: MonitoringSnapshot):
        """Check metrics against thresholds and generate alerts."""
        now = datetime.now(timezone.utc)
        
        # Quality checks
        if snapshot.read_stats.mean_qscore < self.thresholds["min_mean_qscore"]:
            self.alerts.append(Alert(
                timestamp=now,
                level="warning",
                category="quality",
                message=f"Mean Q-score ({snapshot.read_stats.mean_qscore:.1f}) below threshold",
                metric_name="mean_qscore",
                metric_value=snapshot.read_stats.mean_qscore,
                threshold=self.thresholds["min_mean_qscore"],
            ))
        
        # N50 check
        if snapshot.read_stats.n50 > 0 and snapshot.read_stats.n50 < self.thresholds["min_n50"]:
            self.alerts.append(Alert(
                timestamp=now,
                level="warning",
                category="quality",
                message=f"N50 ({snapshot.read_stats.n50:,}) below threshold",
                metric_name="n50",
                metric_value=snapshot.read_stats.n50,
                threshold=self.thresholds["min_n50"],
            ))
        
        # Pore activity
        if snapshot.pore_activity.active_pct < self.thresholds["min_active_pores_pct"]:
            self.alerts.append(Alert(
                timestamp=now,
                level="warning",
                category="pores",
                message=f"Active pores ({snapshot.pore_activity.active_pct:.1f}%) below threshold",
                metric_name="active_pores_pct",
                metric_value=snapshot.pore_activity.active_pct,
                threshold=self.thresholds["min_active_pores_pct"],
            ))
        
        # Throughput (only if we have time series data)
        if len(snapshot.time_series) >= 2:
            recent = snapshot.time_series[-1]
            if recent.reads_per_hour < self.thresholds["min_reads_per_hour"]:
                self.alerts.append(Alert(
                    timestamp=now,
                    level="warning",
                    category="throughput",
                    message=f"Reads/hour ({recent.reads_per_hour:.0f}) below threshold",
                    metric_name="reads_per_hour",
                    metric_value=recent.reads_per_hour,
                    threshold=self.thresholds["min_reads_per_hour"],
                ))
    
    def _load_metadata(self):
        """Load run metadata from available sources."""
        # Try final_summary first
        final_summary = self.run_path / "final_summary.txt"
        if not final_summary.exists():
            final_summary = next(self.run_path.glob("**/final_summary*.txt"), None)
        
        if final_summary and final_summary.exists():
            data = FinalSummaryParser.parse(final_summary)
            self.metadata.run_id = data.get("acquisition_run_id", self.metadata.run_id)
            self.metadata.flow_cell_id = data.get("flow_cell_id", self.metadata.flow_cell_id)
            self.metadata.sample_id = data.get("sample_id", self.metadata.sample_id)
            self.metadata.protocol = data.get("protocol", self.metadata.protocol)
            self.metadata.kit = data.get("kit", self.metadata.kit)
            self.metadata.device_type = data.get("instrument", self.metadata.device_type)
            
            if "started" in data:
                try:
                    self.metadata.start_time = datetime.fromisoformat(data["started"])
                except ValueError:
                    pass
        
        # Try POD5 metadata
        if not self.metadata.run_id and HAS_POD5:
            pod5_files = list(self.run_path.glob("**/*.pod5"))[:1]
            if pod5_files:
                stats = POD5Parser.get_file_stats(pod5_files[0])
                self.metadata.run_id = stats.get("run_id", self.metadata.run_id)
                self.metadata.flow_cell_id = stats.get("flow_cell_id", self.metadata.flow_cell_id)
                self.metadata.sample_id = stats.get("sample_id", self.metadata.sample_id)
                self.metadata.protocol = stats.get("protocol", self.metadata.protocol)
                self.metadata.device_type = stats.get("device_type", self.metadata.device_type)
    
    def _compute_time_series(self, records: List[Dict]) -> List[TimePoint]:
        """Compute time series from sequencing summary records."""
        if not records:
            return []
        
        # Group by time buckets (5-minute intervals)
        bucket_size = 300  # seconds
        buckets = defaultdict(list)
        
        for r in records:
            if 'start_time_seconds' in r:
                bucket = int(r['start_time_seconds'] // bucket_size) * bucket_size
                buckets[bucket].append(r)
        
        if not buckets:
            return []
        
        # Compute cumulative stats at each time point
        points = []
        sorted_buckets = sorted(buckets.keys())
        cumulative_reads = 0
        cumulative_bases = 0
        
        start_time = self.metadata.start_time or datetime.now(timezone.utc)
        
        for bucket_time in sorted_buckets:
            bucket_records = buckets[bucket_time]
            bucket_lengths = [r.get('length', 0) for r in bucket_records]
            bucket_qscores = [r.get('qscore', 0) for r in bucket_records if r.get('qscore', 0) > 0]
            
            cumulative_reads += len(bucket_records)
            cumulative_bases += sum(bucket_lengths)
            
            # Compute rates (extrapolated to per-hour)
            hours_elapsed = (bucket_time + bucket_size) / 3600
            reads_per_hour = cumulative_reads / hours_elapsed if hours_elapsed > 0 else 0
            bases_per_hour = cumulative_bases / hours_elapsed if hours_elapsed > 0 else 0
            
            # N50 for this bucket
            n50 = 0
            if bucket_lengths:
                sorted_lengths = sorted(bucket_lengths, reverse=True)
                half = sum(bucket_lengths) / 2
                cumsum = 0
                for length in sorted_lengths:
                    cumsum += length
                    if cumsum >= half:
                        n50 = length
                        break
            
            timestamp = start_time + timedelta(seconds=bucket_time)
            
            points.append(TimePoint(
                timestamp=timestamp,
                cumulative_reads=cumulative_reads,
                cumulative_bases=cumulative_bases,
                reads_per_hour=reads_per_hour,
                bases_per_hour=bases_per_hour,
                mean_qscore=sum(bucket_qscores) / len(bucket_qscores) if bucket_qscores else 0,
                n50=n50,
            ))
        
        return points
    
    def get_snapshot(self) -> MonitoringSnapshot:
        """Get current monitoring snapshot."""
        self._load_metadata()
        
        # Parse sequencing summary
        records = []
        if self.seq_summary_parser:
            records = self.seq_summary_parser.parse_all()
            self.read_stats = self.seq_summary_parser.get_stats(records)
        
        # Compute time series
        self.time_series = self._compute_time_series(records)
        
        # Check if run is active (sequencing_summary modified recently)
        is_active = False
        if self.seq_summary_parser and self.seq_summary_parser.path.exists():
            mtime = datetime.fromtimestamp(self.seq_summary_parser.path.stat().st_mtime, tz=timezone.utc)
            is_active = (datetime.now(timezone.utc) - mtime).total_seconds() < 300  # 5 min
        
        # Build snapshot
        snapshot = MonitoringSnapshot(
            snapshot_time=datetime.now(timezone.utc),
            metadata=self.metadata,
            read_stats=self.read_stats,
            pore_activity=self.pore_activity,
            time_series=self.time_series,
            alerts=[],
            data_sources=self.data_sources,
            is_active=is_active,
            current_yield_gb=self.read_stats.total_bases / 1e9,
        )
        
        # Check thresholds
        self._check_thresholds(snapshot)
        snapshot.alerts = self.alerts
        
        return snapshot
    
    def get_incremental_update(self) -> MonitoringSnapshot:
        """Get incremental update (for live monitoring)."""
        if self.seq_summary_parser:
            new_records = list(self.seq_summary_parser.parse_incremental())
            if new_records:
                # Update stats with new records
                for r in new_records:
                    if 'length' in r:
                        self.read_stats.lengths.append(r['length'])
                    if 'qscore' in r:
                        self.read_stats.qscores.append(r['qscore'])
                    if r.get('passes', False):
                        self.read_stats.pass_count += 1
                    else:
                        self.read_stats.fail_count += 1
                
                self.read_stats.compute_derived()
        
        return self.get_snapshot()


# =============================================================================
# Output Formatters
# =============================================================================

def format_bytes(n: int) -> str:
    """Format bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def format_number(n: int) -> str:
    """Format number with commas."""
    return f"{n:,}"


def format_duration(td: timedelta) -> str:
    """Format timedelta to human readable."""
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


class TerminalDashboard:
    """Terminal-based monitoring dashboard."""
    
    COLORS = {
        'green': '\033[92m',
        'yellow': '\033[93m',
        'red': '\033[91m',
        'blue': '\033[94m',
        'bold': '\033[1m',
        'reset': '\033[0m',
    }
    
    def __init__(self, use_colors: bool = True):
        self.use_colors = use_colors and sys.stdout.isatty()
    
    def _color(self, text: str, color: str) -> str:
        if self.use_colors:
            return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"
        return text
    
    def _status_indicator(self, is_ok: bool) -> str:
        if is_ok:
            return self._color("✓", "green")
        return self._color("✗", "red")
    
    def render(self, snapshot: MonitoringSnapshot) -> str:
        """Render snapshot as terminal dashboard."""
        lines = []
        
        # Header
        status = self._color("● ACTIVE", "green") if snapshot.is_active else self._color("○ COMPLETED", "blue")
        lines.append(f"\n{'='*60}")
        lines.append(f"  ONT Run Monitor  {status}")
        lines.append(f"{'='*60}")
        
        # Metadata
        m = snapshot.metadata
        lines.append(f"\n{self._color('Run Information', 'bold')}")
        lines.append(f"  Run ID:       {m.run_id or 'Unknown'}")
        lines.append(f"  Flow Cell:    {m.flow_cell_id or 'Unknown'}")
        lines.append(f"  Sample:       {m.sample_id or 'Unknown'}")
        lines.append(f"  Protocol:     {m.protocol or 'Unknown'}")
        if m.duration:
            lines.append(f"  Duration:     {format_duration(m.duration)}")
        
        # Read Statistics
        s = snapshot.read_stats
        lines.append(f"\n{self._color('Read Statistics', 'bold')}")
        lines.append(f"  Total Reads:  {format_number(s.count)}")
        lines.append(f"  Total Bases:  {format_bytes(s.total_bases)}")
        lines.append(f"  Pass/Fail:    {format_number(s.pass_count)} / {format_number(s.fail_count)}")
        
        qscore_ok = s.mean_qscore >= DEFAULT_THRESHOLDS["min_mean_qscore"]
        lines.append(f"  Mean Q:       {s.mean_qscore:.1f} {self._status_indicator(qscore_ok)}")
        
        n50_ok = s.n50 >= DEFAULT_THRESHOLDS["min_n50"]
        lines.append(f"  N50:          {format_number(s.n50)} bp {self._status_indicator(n50_ok)}")
        lines.append(f"  Longest:      {format_number(s.longest_read)} bp")
        lines.append(f"  Mean Length:  {s.mean_length:.0f} bp")
        
        # Throughput
        if snapshot.time_series:
            latest = snapshot.time_series[-1]
            lines.append(f"\n{self._color('Throughput', 'bold')}")
            lines.append(f"  Reads/hour:   {latest.reads_per_hour:,.0f}")
            lines.append(f"  Bases/hour:   {format_bytes(int(latest.bases_per_hour))}")
            lines.append(f"  Yield:        {snapshot.current_yield_gb:.2f} Gb")
        
        # Pore Activity (if available)
        p = snapshot.pore_activity
        if p.active_pores > 0:
            lines.append(f"\n{self._color('Pore Activity', 'bold')}")
            pore_ok = p.active_pct >= DEFAULT_THRESHOLDS["min_active_pores_pct"]
            lines.append(f"  Active:       {p.active_pores}/{p.total_channels} ({p.active_pct:.1f}%) {self._status_indicator(pore_ok)}")
            lines.append(f"  Sequencing:   {p.sequencing}")
            lines.append(f"  Occupancy:    {p.occupancy:.1%}")
        
        # Alerts
        if snapshot.alerts:
            lines.append(f"\n{self._color('Alerts', 'bold')}")
            for alert in snapshot.alerts[-5:]:  # Show last 5
                icon = "⚠" if alert.level == "warning" else "❌"
                color = "yellow" if alert.level == "warning" else "red"
                lines.append(f"  {self._color(icon, color)} {alert.message}")
        
        # Data sources
        lines.append(f"\n{self._color('Data Sources', 'bold')}")
        for src in snapshot.data_sources:
            lines.append(f"  • {src}")
        
        # Timestamp
        lines.append(f"\nLast updated: {snapshot.snapshot_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("")
        
        return '\n'.join(lines)


class PlotGenerator:
    """Generate time-series plots."""
    
    @staticmethod
    def generate(snapshot: MonitoringSnapshot, output_path: Path):
        """Generate comprehensive monitoring plots."""
        if not HAS_MATPLOTLIB:
            print("Warning: matplotlib not available, skipping plots", file=sys.stderr)
            return
        
        if not snapshot.time_series:
            print("Warning: No time series data available for plotting", file=sys.stderr)
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(f"Run Monitoring: {snapshot.metadata.run_id or 'Unknown'}", fontsize=14, fontweight='bold')
        
        timestamps = [tp.timestamp for tp in snapshot.time_series]
        
        # Plot 1: Cumulative yield
        ax1 = axes[0, 0]
        bases_gb = [tp.cumulative_bases / 1e9 for tp in snapshot.time_series]
        ax1.plot(timestamps, bases_gb, 'b-', linewidth=2)
        ax1.fill_between(timestamps, bases_gb, alpha=0.3)
        ax1.set_ylabel('Yield (Gb)')
        ax1.set_title('Cumulative Yield')
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        
        # Plot 2: Throughput rate
        ax2 = axes[0, 1]
        bases_per_hour = [tp.bases_per_hour / 1e6 for tp in snapshot.time_series]
        ax2.plot(timestamps, bases_per_hour, 'g-', linewidth=2)
        ax2.axhline(y=DEFAULT_THRESHOLDS["min_bases_per_hour"] / 1e6, color='r', linestyle='--', label='Min threshold')
        ax2.set_ylabel('Mb/hour')
        ax2.set_title('Throughput Rate')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        
        # Plot 3: Read count
        ax3 = axes[1, 0]
        reads = [tp.cumulative_reads for tp in snapshot.time_series]
        ax3.plot(timestamps, reads, 'purple', linewidth=2)
        ax3.fill_between(timestamps, reads, alpha=0.3, color='purple')
        ax3.set_ylabel('Read Count')
        ax3.set_xlabel('Time')
        ax3.set_title('Cumulative Reads')
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        
        # Plot 4: Quality score
        ax4 = axes[1, 1]
        qscores = [tp.mean_qscore for tp in snapshot.time_series if tp.mean_qscore > 0]
        if qscores:
            qscore_times = [tp.timestamp for tp in snapshot.time_series if tp.mean_qscore > 0]
            ax4.plot(qscore_times, qscores, 'orange', linewidth=2)
            ax4.axhline(y=DEFAULT_THRESHOLDS["min_mean_qscore"], color='r', linestyle='--', label='Min threshold')
            ax4.set_ylabel('Mean Q-score')
            ax4.set_xlabel('Time')
            ax4.set_title('Quality Score Trend')
            ax4.grid(True, alpha=0.3)
            ax4.legend()
            ax4.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        else:
            ax4.text(0.5, 0.5, 'No Q-score data', ha='center', va='center', transform=ax4.transAxes)
            ax4.set_title('Quality Score Trend')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"Plot saved to: {output_path}")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="ONT Run Monitor - Real-time and retrospective sequencing run monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Live monitoring dashboard (auto-refresh)
  ont_monitor.py /path/to/run --live
  
  # Single snapshot to JSON
  ont_monitor.py /path/to/run --snapshot --json metrics.json
  
  # Generate plots
  ont_monitor.py /path/to/run --plot run_metrics.png
  
  # Full history analysis
  ont_monitor.py /path/to/run --history --json history.json
  
  # Via ont-experiments (recommended)
  ont_experiments.py run monitoring exp-abc123 --live
        """
    )
    
    parser.add_argument("path", help="Path to sequencing run directory")
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--live", action="store_true",
                          help="Live monitoring dashboard with auto-refresh")
    mode_group.add_argument("--snapshot", action="store_true",
                          help="Single snapshot (default)")
    mode_group.add_argument("--history", action="store_true",
                          help="Full time-series history analysis")
    
    # Output options
    parser.add_argument("--json", metavar="FILE",
                       help="Output JSON file")
    parser.add_argument("--plot", metavar="FILE",
                       help="Output plot file (PNG/PDF)")
    parser.add_argument("--csv", metavar="FILE",
                       help="Output time series CSV")
    
    # Live mode options
    parser.add_argument("--interval", type=int, default=30,
                       help="Refresh interval in seconds for live mode (default: 30)")
    
    # Threshold overrides
    parser.add_argument("--min-qscore", type=float,
                       help="Override minimum Q-score threshold")
    parser.add_argument("--min-n50", type=int,
                       help="Override minimum N50 threshold")
    
    # Display options
    parser.add_argument("--no-color", action="store_true",
                       help="Disable colored output")
    parser.add_argument("--quiet", action="store_true",
                       help="Suppress terminal output (JSON/plot only)")
    parser.add_argument("--verbose", action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    
    # Validate path
    run_path = Path(args.path)
    if not run_path.exists():
        print(f"Error: Path does not exist: {run_path}", file=sys.stderr)
        sys.exit(1)
    
    # Configure thresholds
    thresholds = DEFAULT_THRESHOLDS.copy()
    if args.min_qscore:
        thresholds["min_mean_qscore"] = args.min_qscore
    if args.min_n50:
        thresholds["min_n50"] = args.min_n50
    
    # Initialize monitor
    monitor = RunMonitor(run_path, thresholds)
    
    if not monitor.data_sources:
        print(f"Warning: No recognized data sources found in {run_path}", file=sys.stderr)
        print("Looking for: sequencing_summary.txt, final_summary.txt, *.pod5, MinKNOW logs", file=sys.stderr)
    
    # Live monitoring mode
    if args.live:
        dashboard = TerminalDashboard(use_colors=not args.no_color)
        
        def signal_handler(sig, frame):
            print("\nMonitoring stopped.")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        print(f"Starting live monitoring (Ctrl+C to stop, refresh every {args.interval}s)...")
        
        while True:
            # Clear screen
            os.system('clear' if os.name == 'posix' else 'cls')
            
            snapshot = monitor.get_incremental_update()
            print(dashboard.render(snapshot))
            
            # Save JSON if requested
            if args.json:
                with open(args.json, 'w') as f:
                    json.dump(snapshot.to_dict(), f, indent=2)
            
            # Generate plot if requested
            if args.plot:
                PlotGenerator.generate(snapshot, Path(args.plot))
            
            time.sleep(args.interval)
    
    # Snapshot/history mode
    else:
        snapshot = monitor.get_snapshot()
        
        # Terminal output
        if not args.quiet:
            dashboard = TerminalDashboard(use_colors=not args.no_color)
            print(dashboard.render(snapshot))
        
        # JSON output
        if args.json:
            with open(args.json, 'w') as f:
                json.dump(snapshot.to_dict(), f, indent=2)
            if not args.quiet:
                print(f"JSON saved to: {args.json}")
        
        # Plot output
        if args.plot:
            PlotGenerator.generate(snapshot, Path(args.plot))
        
        # CSV output
        if args.csv and snapshot.time_series:
            if HAS_PANDAS:
                df = pd.DataFrame([tp.to_dict() for tp in snapshot.time_series])
                df.to_csv(args.csv, index=False)
            else:
                with open(args.csv, 'w') as f:
                    if snapshot.time_series:
                        headers = list(snapshot.time_series[0].to_dict().keys())
                        f.write(','.join(headers) + '\n')
                        for tp in snapshot.time_series:
                            f.write(','.join(str(v) for v in tp.to_dict().values()) + '\n')
            if not args.quiet:
                print(f"CSV saved to: {args.csv}")
        
        # Return appropriate exit code based on alerts
        critical_alerts = [a for a in snapshot.alerts if a.level == "critical"]
        if critical_alerts:
            sys.exit(2)
        elif snapshot.alerts:
            sys.exit(1)
        sys.exit(0)


if __name__ == "__main__":
    main()
