"""
ONT Ecosystem Core Library
Shared utilities for experiment management, registry access, and visualization.
"""

import os
import sys
import json
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Iterator, Tuple
from collections import defaultdict

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# =============================================================================
# Configuration
# =============================================================================

def get_config_dir() -> Path:
    """Get configuration directory."""
    return Path(os.environ.get('ONT_ECOSYSTEM_HOME', Path.home() / '.ont-ecosystem'))

def get_registry_dir() -> Path:
    """Get experiment registry directory."""
    return Path(os.environ.get('ONT_REGISTRY_DIR', Path.home() / '.ont-registry'))

def get_references_dir() -> Path:
    """Get reference genome registry directory."""
    return Path(os.environ.get('ONT_REFERENCES_DIR', Path.home() / '.ont-references'))

def load_config(config_name: str) -> Dict:
    """Load a configuration file."""
    config_dir = get_config_dir() / 'config'
    
    for ext in ['.yaml', '.yml', '.json']:
        config_file = config_dir / f"{config_name}{ext}"
        if config_file.exists():
            with open(config_file) as f:
                if ext == '.json':
                    return json.load(f)
                elif HAS_YAML:
                    return yaml.safe_load(f)
    return {}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Event:
    """An event in the experiment history."""
    timestamp: str
    type: str  # discovered, registered, analysis, tag, status, note
    agent: str = "manual"
    machine: str = ""
    
    # Analysis-specific
    analysis: str = ""
    command: str = ""
    parameters: Dict = field(default_factory=dict)
    outputs: List[Dict] = field(default_factory=list)
    results: Dict = field(default_factory=dict)
    duration_seconds: float = 0.0
    exit_code: int = 0
    
    # HPC-specific
    hpc: Dict = field(default_factory=dict)
    
    # Other
    details: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        d = {k: v for k, v in asdict(self).items() if v}
        return d
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Event':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Experiment:
    """An ONT sequencing experiment."""
    id: str
    name: str
    location: str
    
    # Status
    status: str = "discovered"  # discovered, registered, analyzing, complete, archived
    source: str = "local"  # local, hpc, s3, ont-open-data
    
    # Run Information
    run_id: str = ""
    sample_id: str = ""
    experiment_id: str = ""
    
    # Platform
    platform: str = ""
    flowcell_type: str = ""
    flowcell_id: str = ""
    kit: str = ""
    chemistry: str = ""
    
    # Data Stats
    total_reads: int = 0
    total_bases: int = 0
    n50: int = 0
    mean_quality: float = 0.0
    
    # File Info
    data_format: str = ""
    file_count: int = 0
    total_size_gb: float = 0.0
    
    # Timestamps
    run_started: str = ""
    run_ended: str = ""
    discovered: str = ""
    last_accessed: str = ""
    
    # Organization
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    
    # Event History
    events: List[Event] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['events'] = [e.to_dict() if isinstance(e, Event) else e for e in self.events]
        return {k: v for k, v in d.items() if v or k in ['events', 'tags']}
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Experiment':
        events = [Event.from_dict(e) if isinstance(e, dict) else e 
                  for e in data.pop('events', [])]
        return cls(events=events, **{k: v for k, v in data.items() 
                                      if k in cls.__dataclass_fields__ and k != 'events'})
    
    def add_event(self, event: Event):
        """Add an event to history."""
        self.events.append(event)
        self.last_accessed = datetime.now(timezone.utc).isoformat()
    
    def get_latest_analysis(self, analysis_type: str) -> Optional[Event]:
        """Get the most recent successful analysis of a type."""
        for event in reversed(self.events):
            if event.type == 'analysis' and event.analysis == analysis_type and event.exit_code == 0:
                return event
        return None
    
    @property
    def analysis_count(self) -> int:
        return sum(1 for e in self.events if e.type == 'analysis')
    
    @property
    def successful_analyses(self) -> List[Event]:
        return [e for e in self.events if e.type == 'analysis' and e.exit_code == 0]


# =============================================================================
# Registry Manager
# =============================================================================

class Registry:
    """Manage the experiment registry."""
    
    def __init__(self, registry_dir: Path = None):
        self.registry_dir = registry_dir or get_registry_dir()
        self.registry_file = self.registry_dir / 'experiments.yaml'
        self._experiments: Dict[str, Experiment] = {}
        self._loaded = False
    
    def _ensure_loaded(self):
        """Lazy load registry."""
        if not self._loaded:
            self._load()
            self._loaded = True
    
    def _load(self):
        """Load registry from disk."""
        if not self.registry_file.exists():
            return
        
        try:
            with open(self.registry_file) as f:
                if HAS_YAML:
                    data = yaml.safe_load(f) or {}
                else:
                    # Fall back to JSON-style YAML
                    data = json.load(f)
            
            for exp_data in data.get('experiments', []):
                exp = Experiment.from_dict(exp_data)
                self._experiments[exp.id] = exp
                
        except Exception as e:
            print(f"Warning: Could not load registry: {e}", file=sys.stderr)
    
    def _save(self):
        """Save registry to disk."""
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        
        data = {
            'version': '2.0',
            'updated': datetime.now(timezone.utc).isoformat(),
            'experiments': [exp.to_dict() for exp in self._experiments.values()]
        }
        
        with open(self.registry_file, 'w') as f:
            if HAS_YAML:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            else:
                json.dump(data, f, indent=2)
    
    def get(self, experiment_id: str) -> Optional[Experiment]:
        """Get experiment by ID."""
        self._ensure_loaded()
        return self._experiments.get(experiment_id)
    
    def add(self, experiment: Experiment):
        """Add or update experiment."""
        self._ensure_loaded()
        self._experiments[experiment.id] = experiment
        self._save()
    
    def remove(self, experiment_id: str) -> bool:
        """Remove experiment from registry."""
        self._ensure_loaded()
        if experiment_id in self._experiments:
            del self._experiments[experiment_id]
            self._save()
            return True
        return False
    
    def list(self, 
             tags: List[str] = None,
             status: str = None,
             source: str = None,
             limit: int = None) -> List[Experiment]:
        """List experiments with optional filters."""
        self._ensure_loaded()
        
        results = list(self._experiments.values())
        
        if tags:
            results = [e for e in results if any(t in e.tags for t in tags)]
        if status:
            results = [e for e in results if e.status == status]
        if source:
            results = [e for e in results if e.source == source]
        
        # Sort by last accessed
        results.sort(key=lambda e: e.last_accessed or e.discovered or '', reverse=True)
        
        if limit:
            results = results[:limit]
        
        return results
    
    def search(self, query: str) -> List[Experiment]:
        """Search experiments by name, ID, tags, or notes."""
        self._ensure_loaded()
        query_lower = query.lower()
        
        results = []
        for exp in self._experiments.values():
            if (query_lower in exp.id.lower() or
                query_lower in exp.name.lower() or
                query_lower in exp.sample_id.lower() or
                query_lower in exp.notes.lower() or
                any(query_lower in tag.lower() for tag in exp.tags)):
                results.append(exp)
        
        return results
    
    def iter_all(self) -> Iterator[Experiment]:
        """Iterate over all experiments."""
        self._ensure_loaded()
        yield from self._experiments.values()
    
    @property
    def count(self) -> int:
        """Total number of experiments."""
        self._ensure_loaded()
        return len(self._experiments)
    
    def get_stats(self) -> Dict:
        """Get registry statistics."""
        self._ensure_loaded()
        
        stats = {
            'total_experiments': self.count,
            'by_status': defaultdict(int),
            'by_source': defaultdict(int),
            'by_platform': defaultdict(int),
            'by_chemistry': defaultdict(int),
            'total_reads': 0,
            'total_bases': 0,
            'total_size_gb': 0.0,
            'total_analyses': 0,
            'tags': defaultdict(int),
        }
        
        for exp in self._experiments.values():
            stats['by_status'][exp.status] += 1
            stats['by_source'][exp.source] += 1
            if exp.platform:
                stats['by_platform'][exp.platform] += 1
            if exp.chemistry:
                stats['by_chemistry'][exp.chemistry] += 1
            stats['total_reads'] += exp.total_reads
            stats['total_bases'] += exp.total_bases
            stats['total_size_gb'] += exp.total_size_gb
            stats['total_analyses'] += exp.analysis_count
            for tag in exp.tags:
                stats['tags'][tag] += 1
        
        # Convert defaultdicts to regular dicts
        stats = {k: dict(v) if isinstance(v, defaultdict) else v for k, v in stats.items()}
        
        return stats


# =============================================================================
# Utility Functions
# =============================================================================

def generate_experiment_id(location: str) -> str:
    """Generate a unique experiment ID from location."""
    h = hashlib.sha256(location.encode()).hexdigest()[:12]
    return f"exp-{h}"

def compute_file_checksum(path: Path, algorithm: str = 'sha256', 
                          chunk_size: int = 1024 * 1024) -> str:
    """Compute file checksum."""
    hasher = hashlib.new(algorithm)
    with open(path, 'rb') as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return f"{algorithm}:{hasher.hexdigest()}"

def detect_agent() -> Tuple[str, str]:
    """Detect the agent running this code."""
    agent = os.environ.get('CLAUDE_AGENT', 
            os.environ.get('ONT_AGENT', 'manual'))
    version = os.environ.get('CLAUDE_VERSION',
              os.environ.get('ONT_AGENT_VERSION', ''))
    return agent, version

def get_machine_info() -> Tuple[str, str]:
    """Get machine and user info."""
    import socket
    machine = socket.gethostname()
    user = os.environ.get('USER', os.environ.get('USERNAME', 'unknown'))
    return machine, user

def detect_hpc() -> Dict:
    """Detect HPC environment."""
    hpc = {}
    
    # SLURM
    if os.environ.get('SLURM_JOB_ID'):
        hpc['scheduler'] = 'slurm'
        hpc['job_id'] = os.environ.get('SLURM_JOB_ID')
        hpc['job_name'] = os.environ.get('SLURM_JOB_NAME', '')
        hpc['partition'] = os.environ.get('SLURM_JOB_PARTITION', '')
        hpc['nodes'] = os.environ.get('SLURM_JOB_NODELIST', '').split(',')
        hpc['cpus'] = os.environ.get('SLURM_CPUS_ON_NODE', '')
        hpc['mem_gb'] = os.environ.get('SLURM_MEM_PER_NODE', '')
        
        # Detect GPUs
        gpu_str = os.environ.get('SLURM_GPUS', os.environ.get('SLURM_JOB_GPUS', ''))
        if gpu_str:
            hpc['gpus'] = gpu_str
    
    # PBS
    elif os.environ.get('PBS_JOBID'):
        hpc['scheduler'] = 'pbs'
        hpc['job_id'] = os.environ.get('PBS_JOBID')
        hpc['job_name'] = os.environ.get('PBS_JOBNAME', '')
        hpc['queue'] = os.environ.get('PBS_QUEUE', '')
    
    return hpc

def format_bytes(size: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(size) < 1024.0:
            return f"{size:,.1f} {unit}"
        size /= 1024.0
    return f"{size:,.1f} PB"

def format_duration(seconds: float) -> str:
    """Format duration as human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


# =============================================================================
# Export Utilities
# =============================================================================

def export_experiment_json(experiment: Experiment, include_events: bool = True) -> str:
    """Export experiment as JSON."""
    data = experiment.to_dict()
    if not include_events:
        data.pop('events', None)
    return json.dumps(data, indent=2)

def export_experiment_commands(experiment: Experiment) -> str:
    """Export experiment commands as shell script."""
    lines = [
        "#!/bin/bash",
        f"# Commands for experiment: {experiment.id}",
        f"# Name: {experiment.name}",
        f"# Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
    ]
    
    for i, event in enumerate(experiment.events, 1):
        if event.type == 'analysis' and event.command:
            lines.append(f"# Event {i}: {event.analysis} ({event.timestamp})")
            lines.append(event.command)
            lines.append("")
    
    return '\n'.join(lines)

def export_registry_csv(registry: Registry) -> str:
    """Export registry as CSV."""
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'id', 'name', 'status', 'platform', 'chemistry', 'sample_id',
        'total_reads', 'total_bases', 'n50', 'mean_quality',
        'total_size_gb', 'tags', 'location'
    ])
    
    for exp in registry.iter_all():
        writer.writerow([
            exp.id, exp.name, exp.status, exp.platform, exp.chemistry, exp.sample_id,
            exp.total_reads, exp.total_bases, exp.n50, exp.mean_quality,
            exp.total_size_gb, ','.join(exp.tags), exp.location
        ])
    
    return output.getvalue()
