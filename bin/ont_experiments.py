#!/usr/bin/env python3
"""
ONT Experiments v2 - Event-Sourced Nanopore Experiment Registry

A foundational tool for discovering, tracking, and orchestrating Oxford Nanopore
sequencing experiments with full provenance tracking.

Features:
- Event-sourced registry (full audit trail)
- Pattern B orchestration (wraps analysis skills)
- HPC metadata capture (SLURM job ID, nodes, GPUs)
- Public dataset access with S3 fallbacks
- Git-friendly registry format

Usage:
  ont_experiments.py init [--git]                    # Initialize registry
  ont_experiments.py discover /path/to/data          # Find experiments
  ont_experiments.py run end_reasons <id> [args]     # Run analysis with logging
  ont_experiments.py history <id>                    # View event history
  ont_experiments.py export <id>                     # Export commands
"""

import argparse
import json
import os
import re
import sys
import hashlib
import shutil
import subprocess
import socket
import getpass
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple, Union
from collections import defaultdict
import time

# Optional imports
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

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
    from git import Repo
    HAS_GIT = True
except ImportError:
    HAS_GIT = False

try:
    import urllib.request
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except (ImportError, TypeError):
    # TypeError can occur with incompatible referencing package on Python <3.13
    HAS_JSONSCHEMA = False


# =============================================================================
# Configuration
# =============================================================================

REGISTRY_DIR = Path.home() / ".ont-registry"
REGISTRY_FILE = REGISTRY_DIR / "experiments.yaml"
REGISTRY_VERSION = "2.0"

# GitHub sync configuration
# NOTE: Disabled by default for private repository compatibility
# Enable via ONT_GITHUB_SYNC=1 environment variable or config file
GITHUB_REGISTRY_URL = "https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/registry/experiments.yaml"
GITHUB_SYNC_ENABLED = False  # Disabled for private repo; enable with ONT_GITHUB_SYNC=1

# Analysis skill configurations
# Each skill maps to a bin script and defines how results are captured
ANALYSIS_SKILLS = {
    # Signal Stage (σ) - QC analysis of raw signals
    "end_reasons": {
        "script": "end_reason.py",
        "description": "Read end reason QC analysis",
        "result_fields": ["total_reads", "quality_status", "signal_positive_pct",
                         "unblock_mux_pct", "data_service_pct"],
        "input_mode": "location",
        "pipeline_stage": "σ",
        "skill_dir": "end-reason",
    },
    "endreason_qc": {
        "script": "ont_endreason_qc.py",
        "description": "Enhanced end reason QC with KDE visualization",
        "result_fields": ["total_reads", "quality_grade", "signal_positive_pct",
                         "unblock_pct", "mean_sp_length", "mean_unblock_length"],
        "input_mode": "location",
        "pipeline_stage": "σ",
        "skill_dir": "end-reason",
    },
    "monitoring": {
        "script": "ont_monitor.py",
        "description": "Run monitoring snapshot",
        "result_fields": ["total_reads", "total_bases", "mean_qscore", "n50",
                         "throughput_gbp_hr", "pore_activity_pct"],
        "input_mode": "location",
        "default_args": ["--snapshot"],
        "pipeline_stage": "σ",
        "skill_dir": "ont-monitor",
    },

    # Basecalling Stage (r)
    "basecalling": {
        "script": "dorado_basecall.py",
        "description": "Dorado basecalling",
        "result_fields": ["total_reads", "pass_reads", "mean_qscore", "median_qscore",
                         "bases_called", "n50", "model", "model_path", "model_tier",
                         "model_version", "chemistry", "batch_size"],
        "input_mode": "location",
        "capture_model_path": True,
        "pipeline_stage": "r",
        "skill_dir": "dorado-bench-v2",
    },
    "alignment": {
        "script": "ont_align.py",
        "description": "Minimap2/Dorado alignment",
        "result_fields": ["mapped_reads", "mapping_rate", "mean_coverage", "median_coverage"],
        "input_mode": "explicit",
        "default_args": ["align"],
        "pipeline_stage": "r",
        "skill_dir": "ont-align",
    },
    "align_qc": {
        "script": "ont_align.py",
        "description": "BAM QC analysis",
        "result_fields": ["total_reads", "mapped_pct", "mean_mapq", "error_rate"],
        "input_mode": "explicit",
        "default_args": ["qc"],
        "pipeline_stage": "r",
        "skill_dir": "ont-align",
    },
}

# Public datasets catalog (merged from ont-data-access-v2)
PUBLIC_DATASETS = {
    # Human Reference
    "gm24385_2023.12": {
        "name": "GM24385 R10.4.1 Latest",
        "description": "Human reference GM24385, R10.4.1 chemistry, POD5 format",
        "category": "human_reference",
        "s3_path": "s3://ont-open-data/gm24385_2023.12/",
        "web_url": "https://42basepairs.com/browse/s3/ont-open-data/gm24385_2023.12",
        "size": "~300GB",
        "chemistry": "R10.4.1",
        "formats": ["pod5", "bam"],
        "featured": True,
    },
    "lc2024_t2t": {
        "name": "Telomere-to-Telomere Reference",
        "description": "T2T CHM13 reference data",
        "category": "human_reference",
        "s3_path": "s3://ont-open-data/lc2024.01/",
        "web_url": "https://42basepairs.com/browse/s3/ont-open-data/lc2024.01",
        "size": "~200GB",
        "featured": True,
    },
    "gm24385_q20_2021.10": {
        "name": "GM24385 Q20+ R10.4.1",
        "description": "Q20+ chemistry demonstration",
        "category": "human_reference",
        "s3_path": "s3://ont-open-data/gm24385_q20_2021.10/",
        "web_url": "https://42basepairs.com/browse/s3/ont-open-data/gm24385_q20_2021.10",
        "size": "~250GB",
        "chemistry": "R10.4.1",
    },
    
    # GIAB Benchmarks
    "giab_2025.01": {
        "name": "GIAB 2025.01 Latest",
        "description": "Latest GIAB reference samples (HG002, HG003, HG004)",
        "category": "giab",
        "s3_path": "s3://ont-open-data/giab_2025.01/",
        "web_url": "https://42basepairs.com/browse/s3/ont-open-data/giab_2025.01",
        "size": "~400GB",
        "formats": ["pod5", "bam", "vcf"],
        "featured": True,
    },
    "giab_2023.05": {
        "name": "GIAB 2023.05",
        "description": "GIAB reference samples with R10.4.1",
        "category": "giab",
        "s3_path": "s3://ont-open-data/giab_2023.05/",
        "web_url": "https://42basepairs.com/browse/s3/ont-open-data/giab_2023.05",
        "size": "~400GB",
        "chemistry": "R10.4.1",
        "formats": ["pod5", "bam", "vcf"],
    },
    "giab_lsk114_2022.12": {
        "name": "GIAB LSK114",
        "description": "GIAB with LSK114 kit",
        "category": "giab",
        "s3_path": "s3://ont-open-data/giab_lsk114_2022.12/",
        "web_url": "https://42basepairs.com/browse/s3/ont-open-data/giab_lsk114_2022.12",
        "size": "~300GB",
    },
    
    # Cancer/Clinical
    "hereditary_cancer_2025.09": {
        "name": "Hereditary Cancer Panel",
        "description": "Cancer gene panel sequencing",
        "category": "cancer",
        "s3_path": "s3://ont-open-data/hereditary_cancer_2025.09/",
        "web_url": "https://42basepairs.com/browse/s3/ont-open-data/hereditary_cancer_2025.09",
        "size": "~100GB",
        "featured": True,
    },
    "colo829_2024.03": {
        "name": "COLO829 Melanoma 2024",
        "description": "Melanoma cell line reference",
        "category": "cancer",
        "s3_path": "s3://ont-open-data/colo829_2024.03/",
        "web_url": "https://42basepairs.com/browse/s3/ont-open-data/colo829_2024.03",
        "size": "~150GB",
        "formats": ["pod5", "vcf"],
    },
    "colo829_2023.04": {
        "name": "COLO829 Melanoma 2023",
        "description": "Earlier COLO829 release",
        "category": "cancer",
        "s3_path": "s3://ont-open-data/colo829_2023.04/",
        "web_url": "https://42basepairs.com/browse/s3/ont-open-data/colo829_2023.04",
        "size": "~150GB",
    },
    
    # Microbial
    "zymo_16s_2025.09": {
        "name": "ZymoBIOMICS 16S",
        "description": "16S mock community standard",
        "category": "microbial",
        "s3_path": "s3://ont-open-data/zymo_16s_2025.09/",
        "web_url": "https://42basepairs.com/browse/s3/ont-open-data/zymo_16s_2025.09",
        "size": "~20GB",
    },
    "fungal_ITS_2025.09": {
        "name": "Fungal ITS",
        "description": "Fungal ITS sequencing",
        "category": "microbial",
        "s3_path": "s3://ont-open-data/fungal_ITS_2025.09/",
        "web_url": "https://42basepairs.com/browse/s3/ont-open-data/fungal_ITS_2025.09",
        "size": "~15GB",
    },
    "zymo_fecal_2025.05": {
        "name": "Fecal Microbiome",
        "description": "Fecal microbiome standard",
        "category": "microbial",
        "s3_path": "s3://ont-open-data/zymo_fecal_2025.05/",
        "web_url": "https://42basepairs.com/browse/s3/ont-open-data/zymo_fecal_2025.05",
        "size": "~50GB",
    },
    
    # Pathogen
    "pathogen_surveillance_2025.09": {
        "name": "Pathogen Surveillance",
        "description": "Pathogen detection panel",
        "category": "pathogen",
        "s3_path": "s3://ont-open-data/pathogen_surveillance_2025.09/",
        "web_url": "https://42basepairs.com/browse/s3/ont-open-data/pathogen_surveillance_2025.09",
        "size": "~30GB",
        "featured": True,
    },
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class HPCMetadata:
    """HPC job metadata"""
    scheduler: str = "slurm"
    job_id: Optional[str] = None
    job_name: Optional[str] = None
    partition: Optional[str] = None
    nodes: List[str] = field(default_factory=list)
    gpus: List[str] = field(default_factory=list)
    allocated_mem_gb: Optional[float] = None
    walltime_requested: Optional[str] = None
    walltime_used: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v is not None and v != []}


@dataclass
class OutputFile:
    """Output file with verification"""
    path: str
    size_bytes: int = 0
    checksum: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Event:
    """Immutable event in the experiment history"""
    timestamp: str
    type: str  # discovered, registered, analysis, tagged, status_change, archived
    
    # Analysis-specific
    analysis: Optional[str] = None
    command: Optional[str] = None
    working_dir: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    outputs: List[Dict] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)
    
    # Execution metadata
    duration_seconds: Optional[float] = None
    exit_code: Optional[int] = None
    error_message: Optional[str] = None
    
    # Agent tracking
    agent: str = "manual"  # claude-web, claude-code, manual, cron, script
    agent_version: Optional[str] = None
    
    # Machine tracking
    machine: Optional[str] = None
    user: Optional[str] = None
    
    # HPC metadata
    hpc: Optional[Dict] = None
    
    # Notes
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict:
        d = {}
        for k, v in asdict(self).items():
            if v is not None and v != {} and v != []:
                d[k] = v
        return d
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Event':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# =============================================================================
# Domain Memory: Task Tracking (Anthropic Agent Memory Pattern)
# =============================================================================

@dataclass
class Task:
    """A trackable task in the experiment workflow (v2.0 with dependencies)"""
    name: str                           # Task identifier (e.g., "end_reasons")
    status: str                         # pending, in_progress, passing, failing, skipped, blocked
    description: str                    # Human-readable description
    created: str                        # ISO timestamp
    updated: str                        # ISO timestamp
    last_run: Optional[str] = None      # Last execution timestamp
    last_event_id: Optional[str] = None # Reference to Event that updated this
    error: Optional[str] = None         # Error message if failing
    attempts: int = 0                   # Number of execution attempts
    # v2.0 fields
    pipeline_stage: Optional[str] = None  # SMS pipeline stage (h, g, u, d, l, σ, r, C, A)
    skill: Optional[str] = None           # Associated ONT Ecosystem skill name
    dependencies: Optional[List[str]] = None  # Task names that must complete first
    priority: int = 3                     # Priority 1-5 (1=highest)

    def to_dict(self) -> Dict:
        d = {}
        for k, v in asdict(self).items():
            if v is not None:
                d[k] = v
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> 'Task':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def is_runnable(self, task_list: 'TaskList') -> bool:
        """Check if this task can run (all dependencies satisfied)"""
        if self.status in ('passing', 'skipped'):
            return False  # Already done
        if not self.dependencies:
            return True  # No dependencies
        for dep_name in self.dependencies:
            dep_task = task_list.get_task(dep_name)
            if not dep_task or dep_task.status not in ('passing', 'skipped'):
                return False
        return True

    def is_blocked(self, task_list: 'TaskList') -> bool:
        """Check if this task is blocked by failing dependencies"""
        if not self.dependencies:
            return False
        for dep_name in self.dependencies:
            dep_task = task_list.get_task(dep_name)
            if dep_task and dep_task.status == 'failing':
                return True
        return False


@dataclass
class TaskList:
    """Domain memory: task backlog for an experiment"""
    experiment_id: str
    version: str = "1.0"
    created: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tasks: List[Task] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'experiment_id': self.experiment_id,
            'version': self.version,
            'created': self.created,
            'updated': self.updated,
            'tasks': [t.to_dict() for t in self.tasks]
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'TaskList':
        tasks = [Task.from_dict(t) for t in data.get('tasks', [])]
        return cls(
            experiment_id=data['experiment_id'],
            version=data.get('version', '1.0'),
            created=data.get('created', ''),
            updated=data.get('updated', ''),
            tasks=tasks
        )

    def get_task(self, name: str) -> Optional[Task]:
        """Get task by name"""
        return next((t for t in self.tasks if t.name == name), None)

    def update_task(self, name: str, status: str, error: Optional[str] = None):
        """Update task status"""
        task = self.get_task(name)
        if task:
            task.status = status
            task.updated = datetime.now(timezone.utc).isoformat()
            task.error = error
            self.updated = task.updated

    def get_runnable_tasks(self) -> List[Task]:
        """Get tasks that are ready to run (dependencies satisfied)"""
        return [t for t in self.tasks if t.is_runnable(self)]

    def get_blocked_tasks(self) -> List[Task]:
        """Get tasks blocked by failing dependencies"""
        return [t for t in self.tasks if t.is_blocked(self)]

    def get_next_task(self) -> Optional[Task]:
        """Get the highest priority runnable task"""
        runnable = self.get_runnable_tasks()
        if not runnable:
            return None
        # Sort by priority (1 is highest), then by name
        return sorted(runnable, key=lambda t: (t.priority, t.name))[0]

    def validate_dependencies(self) -> List[str]:
        """Check for invalid dependencies (missing tasks, cycles)"""
        errors = []
        task_names = {t.name for t in self.tasks}

        # Check for missing dependencies
        for task in self.tasks:
            if task.dependencies:
                for dep in task.dependencies:
                    if dep not in task_names:
                        errors.append(f"Task '{task.name}' depends on missing task '{dep}'")

        # Check for cycles using DFS
        def has_cycle(task_name: str, visited: set, rec_stack: set) -> bool:
            visited.add(task_name)
            rec_stack.add(task_name)
            task = self.get_task(task_name)
            if task and task.dependencies:
                for dep in task.dependencies:
                    if dep not in visited:
                        if has_cycle(dep, visited, rec_stack):
                            return True
                    elif dep in rec_stack:
                        return True
            rec_stack.remove(task_name)
            return False

        visited = set()
        for task in self.tasks:
            if task.name not in visited:
                if has_cycle(task.name, visited, set()):
                    errors.append(f"Dependency cycle detected involving task '{task.name}'")

        return errors

    def get_progress_summary(self) -> Dict[str, int]:
        """Get summary of task statuses"""
        summary = defaultdict(int)
        for task in self.tasks:
            summary[task.status] += 1
        return dict(summary)


@dataclass
class ExperimentMetadata:
    """Core metadata for a nanopore experiment"""
    id: str
    name: str
    location: str
    source: str = "local"
    status: str = "discovered"
    
    # Run information
    run_id: Optional[str] = None
    sample_id: Optional[str] = None
    experiment_id: Optional[str] = None
    
    # Platform info
    platform: Optional[str] = None
    flowcell_type: Optional[str] = None
    flowcell_id: Optional[str] = None
    kit: Optional[str] = None
    chemistry: Optional[str] = None
    basecall_model: Optional[str] = None
    
    # Data stats
    total_reads: Optional[int] = None
    total_bases: Optional[int] = None
    n50: Optional[float] = None
    mean_quality: Optional[float] = None
    
    # File info
    data_format: Optional[str] = None
    file_count: int = 0
    total_size_gb: float = 0.0
    
    # Timestamps
    run_started: Optional[str] = None
    run_ended: Optional[str] = None
    discovered: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_accessed: Optional[str] = None
    
    # Organization
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    
    # Event log (append-only)
    events: List[Event] = field(default_factory=list)
    
    def add_event(self, event: Event):
        """Append event to history"""
        self.events.append(event)
        self.last_accessed = datetime.now(timezone.utc).isoformat()
    
    def get_latest_analysis(self, analysis_type: str) -> Optional[Event]:
        """Get most recent analysis event of given type"""
        for event in reversed(self.events):
            if event.type == "analysis" and event.analysis == analysis_type:
                return event
        return None
    
    def to_dict(self) -> Dict:
        d = {}
        for k, v in asdict(self).items():
            if k == 'events':
                if v:
                    d['events'] = [e if isinstance(e, dict) else e.to_dict() for e in v]
            elif v is not None and v != [] and v != {} and v != "":
                d[k] = v
        return d
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ExperimentMetadata':
        events = []
        if 'events' in data:
            for e in data['events']:
                if isinstance(e, Event):
                    events.append(e)
                else:
                    events.append(Event.from_dict(e))
            data = {k: v for k, v in data.items() if k != 'events'}
        
        exp = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        exp.events = events
        return exp


@dataclass
class BootupContext:
    """Grounded context for agent execution - the standardized bootup ritual result"""
    experiment: ExperimentMetadata
    tasks: TaskList
    history: List[Event]
    pending_tasks: List[Task]
    failing_tasks: List[Task]
    passing_tasks: List[Task]
    last_run: Optional[Event]
    recommendations: List[str]


@dataclass
class Registry:
    """Experiment registry with event sourcing"""
    version: str = REGISTRY_VERSION
    updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    experiments: List[ExperimentMetadata] = field(default_factory=list)
    
    def find(self, experiment_id: str) -> Optional[ExperimentMetadata]:
        """Find experiment by ID or partial ID"""
        # Exact match
        for exp in self.experiments:
            if exp.id == experiment_id:
                return exp
        # Partial match
        matches = [e for e in self.experiments if experiment_id in e.id]
        if len(matches) == 1:
            return matches[0]
        return None
    
    def find_by_location(self, location: str) -> Optional[ExperimentMetadata]:
        """Find experiment by location path"""
        location = str(Path(location).resolve())
        for exp in self.experiments:
            if str(Path(exp.location).resolve()) == location:
                return exp
        return None
    
    def add(self, exp: ExperimentMetadata) -> bool:
        """Add experiment, returns False if already exists"""
        if self.find(exp.id):
            return False
        self.experiments.append(exp)
        self.updated = datetime.now(timezone.utc).isoformat()
        return True
    
    def update(self, exp: ExperimentMetadata) -> bool:
        """Update existing experiment"""
        for i, existing in enumerate(self.experiments):
            if existing.id == exp.id:
                self.experiments[i] = exp
                self.updated = datetime.now(timezone.utc).isoformat()
                return True
        return False
    
    def remove(self, experiment_id: str) -> bool:
        """Remove experiment from registry"""
        for i, exp in enumerate(self.experiments):
            if exp.id == experiment_id:
                del self.experiments[i]
                self.updated = datetime.now(timezone.utc).isoformat()
                return True
        return False
    
    def to_dict(self) -> Dict:
        return {
            'version': self.version,
            'updated': self.updated,
            'experiments': [e.to_dict() for e in self.experiments]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Registry':
        experiments = []
        for exp_data in data.get('experiments', []):
            experiments.append(ExperimentMetadata.from_dict(exp_data))
        return cls(
            version=data.get('version', REGISTRY_VERSION),
            updated=data.get('updated', datetime.now(timezone.utc).isoformat()),
            experiments=experiments
        )


# =============================================================================
# Registry I/O
# =============================================================================

def fetch_github_registry() -> Optional[Registry]:
    """Fetch registry from GitHub (read-only fallback)"""
    if not HAS_URLLIB or os.environ.get('ONT_NO_GITHUB_SYNC') == '1':
        return None
    
    try:
        req = urllib.request.Request(
            GITHUB_REGISTRY_URL, 
            headers={'User-Agent': 'ont-experiments/2.0'}
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            content = response.read().decode('utf-8')
            if content.startswith('\ufeff'):
                content = content[1:]  # Remove BOM
            if HAS_YAML:
                data = yaml.safe_load(content) or {}
            else:
                data = json.loads(content)
            return Registry.from_dict(data)
    except Exception as e:
        # Silently fail - GitHub is a fallback
        return None


def load_registry(prefer_github: bool = False) -> Registry:
    """Load registry from local file or GitHub fallback
    
    Args:
        prefer_github: If True, fetch from GitHub first (useful for read-only operations)
    
    Priority:
        1. Local registry file (if exists and not prefer_github)
        2. GitHub registry (fallback for read-only access)
        3. Empty registry
    """
    # Option to prefer GitHub (e.g., when running without HPC access)
    if prefer_github and GITHUB_SYNC_ENABLED:
        github_registry = fetch_github_registry()
        if github_registry:
            return github_registry
    
    # Try local file first
    if REGISTRY_FILE.exists():
        try:
            with open(REGISTRY_FILE, 'r') as f:
                if HAS_YAML:
                    data = yaml.safe_load(f) or {}
                else:
                    data = json.load(f)
            return Registry.from_dict(data)
        except Exception:
            pass  # Fall through to GitHub
    
    # Fall back to GitHub if local doesn't exist
    if GITHUB_SYNC_ENABLED:
        github_registry = fetch_github_registry()
        if github_registry:
            return github_registry
    
    return Registry()


def save_registry(registry: Registry):
    """Save registry to file"""
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)

    data = registry.to_dict()

    with open(REGISTRY_FILE, 'w') as f:
        if HAS_YAML:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        else:
            json.dump(data, f, indent=2)


# =============================================================================
# Domain Memory: Task Persistence
# =============================================================================

EXPERIMENTS_DIR = REGISTRY_DIR / "experiments"


def get_experiment_dir(experiment_id: str) -> Path:
    """Get/create experiment-specific domain memory directory"""
    exp_dir = EXPERIMENTS_DIR / experiment_id
    exp_dir.mkdir(parents=True, exist_ok=True)
    return exp_dir


def load_tasks(experiment_id: str) -> Optional[TaskList]:
    """Load task list from experiment directory"""
    tasks_file = get_experiment_dir(experiment_id) / "tasks.yaml"
    if not tasks_file.exists():
        return None

    try:
        with open(tasks_file, 'r') as f:
            if HAS_YAML:
                data = yaml.safe_load(f) or {}
            else:
                data = json.load(f)
        return TaskList.from_dict(data)
    except Exception:
        return None


def save_tasks(task_list: TaskList):
    """Save task list to experiment directory"""
    task_list.updated = datetime.now(timezone.utc).isoformat()
    tasks_file = get_experiment_dir(task_list.experiment_id) / "tasks.yaml"

    data = task_list.to_dict()

    with open(tasks_file, 'w') as f:
        if HAS_YAML:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        else:
            json.dump(data, f, indent=2)


def initialize_tasks(experiment: 'ExperimentMetadata') -> TaskList:
    """Create initial task list with standard analysis tasks (v2.0 with dependencies)

    Task dependency graph:
        end_reasons (σ) ─┐
                        ├─► basecalling (r) ─► alignment ─► haplotype_calling
        signal_qc (σ) ──┘

    Pipeline stages:
        σ = Signal Stage (end_reasons, signal_qc)
        r = Basecalling Stage (basecalling)
        h = Haplotype Stage (haplotype_calling)
    """
    now = datetime.now(timezone.utc).isoformat()

    tasks = [
        # Signal Stage (σ) - No dependencies, can run in parallel
        Task(
            name="end_reasons",
            status="pending",
            description="Read end reason QC analysis",
            created=now,
            updated=now,
            pipeline_stage="σ",
            skill="end-reason",
            dependencies=None,
            priority=1
        ),
        Task(
            name="signal_qc",
            status="pending",
            description="Signal quality metrics (pA levels, dwell times)",
            created=now,
            updated=now,
            pipeline_stage="σ",
            skill="ont-monitor",
            dependencies=None,
            priority=2
        ),

        # Basecalling Stage (r) - Depends on signal QC
        Task(
            name="basecalling",
            status="pending",
            description="Dorado basecalling with SUP model",
            created=now,
            updated=now,
            pipeline_stage="r",
            skill="dorado-bench-v2",
            dependencies=["end_reasons"],
            priority=2
        ),

        # Alignment - Depends on basecalling
        Task(
            name="alignment",
            status="pending",
            description="Reference genome alignment with minimap2",
            created=now,
            updated=now,
            pipeline_stage="r",
            skill="ont-align",
            dependencies=["basecalling"],
            priority=3
        ),

        # Haplotype calling (h) - Depends on alignment
        Task(
            name="haplotype_calling",
            status="pending",
            description="Haplotype classification and phasing",
            created=now,
            updated=now,
            pipeline_stage="h",
            skill=None,
            dependencies=["alignment"],
            priority=4
        ),
    ]

    return TaskList(
        experiment_id=experiment.id,
        version="2.0",
        created=now,
        updated=now,
        tasks=tasks
    )


# =============================================================================
# Domain Memory: Progress Logging
# =============================================================================

def append_progress(experiment_id: str, entry: str, task_name: Optional[str] = None):
    """Append entry to PROGRESS.md"""
    progress_file = get_experiment_dir(experiment_id) / "PROGRESS.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    header = f"## {timestamp}"
    if task_name:
        header += f" - {task_name}"

    with open(progress_file, 'a') as f:
        f.write(f"\n{header}\n{entry}\n")


def initialize_progress(experiment: 'ExperimentMetadata'):
    """Create initial PROGRESS.md"""
    progress_file = get_experiment_dir(experiment.id) / "PROGRESS.md"

    content = f"""# Progress Log: {experiment.name}

**Experiment ID:** {experiment.id}
**Location:** {experiment.location}
**Platform:** {experiment.platform or 'Unknown'}
**Created:** {datetime.now().isoformat()}

---

## {datetime.now().strftime("%Y-%m-%d %H:%M")} - Initialized
- Domain memory scaffolding created
- Task backlog initialized with {len(ANALYSIS_SKILLS)} pending tasks
- Ready for analysis

"""
    progress_file.write_text(content)


# =============================================================================
# Domain Memory: Bootup Ritual
# =============================================================================

def bootup_check(experiment_id: str) -> Optional[BootupContext]:
    """
    Standardized bootup ritual - READ STATE BEFORE ACTING

    This implements Anthropic's agent memory pattern:
    1. Load registry state
    2. Load task state
    3. Categorize tasks
    4. Generate recommendations

    Returns grounded context or None if experiment not found.
    """
    # 1. Load registry
    registry = load_registry()
    exp = registry.find(experiment_id)
    if not exp:
        return None

    # 2. Load task state (initialize if needed)
    tasks = load_tasks(experiment_id)
    if not tasks:
        tasks = initialize_tasks(exp)
        save_tasks(tasks)
        initialize_progress(exp)

    # 3. Get history
    history = exp.events

    # 4. Categorize tasks
    pending = [t for t in tasks.tasks if t.status == "pending"]
    failing = [t for t in tasks.tasks if t.status == "failing"]
    passing = [t for t in tasks.tasks if t.status == "passing"]

    # 5. Get last run
    last_run = None
    for event in reversed(history):
        if event.type == "analysis":
            last_run = event
            break

    # 6. Generate recommendations
    recommendations = []
    if failing:
        recommendations.append(f"Fix failing tasks first: {[t.name for t in failing]}")
    elif pending:
        recommendations.append(f"Next task: {pending[0].name}")
    else:
        recommendations.append("All tasks complete!")

    return BootupContext(
        experiment=exp,
        tasks=tasks,
        history=history,
        pending_tasks=pending,
        failing_tasks=failing,
        passing_tasks=passing,
        last_run=last_run,
        recommendations=recommendations
    )


# =============================================================================
# Environment Detection
# =============================================================================

def detect_agent() -> Tuple[str, Optional[str]]:
    """Detect the agent running this command"""
    agent = os.environ.get('CLAUDE_AGENT', 'manual')
    version = os.environ.get('CLAUDE_VERSION')
    
    # Detect common environments
    if 'CLAUDE_CODE' in os.environ:
        agent = 'claude-code'
    elif 'ANTHROPIC_API_KEY' in os.environ:
        agent = 'claude-api'
    
    return agent, version


def detect_hpc() -> Optional[HPCMetadata]:
    """Detect HPC environment and capture metadata"""
    # SLURM detection
    if 'SLURM_JOB_ID' in os.environ:
        hpc = HPCMetadata(scheduler='slurm')
        hpc.job_id = os.environ.get('SLURM_JOB_ID')
        hpc.job_name = os.environ.get('SLURM_JOB_NAME')
        hpc.partition = os.environ.get('SLURM_JOB_PARTITION')
        
        # Nodes
        nodelist = os.environ.get('SLURM_JOB_NODELIST', '')
        if nodelist:
            # Expand nodelist (simplified)
            hpc.nodes = [nodelist] if '[' not in nodelist else [nodelist]
        
        # Memory
        mem = os.environ.get('SLURM_MEM_PER_NODE')
        if mem:
            try:
                if mem.endswith('G'):
                    hpc.allocated_mem_gb = float(mem[:-1])
                elif mem.endswith('M'):
                    hpc.allocated_mem_gb = float(mem[:-1]) / 1024
            except ValueError:
                pass
        
        # GPUs
        gpus = os.environ.get('SLURM_GPUS', os.environ.get('SLURM_JOB_GPUS', ''))
        if gpus:
            hpc.gpus = gpus.split(',')
        
        # Try to get GPU info from nvidia-smi
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                hpc.gpus = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        return hpc
    
    # PBS detection
    if 'PBS_JOBID' in os.environ:
        hpc = HPCMetadata(scheduler='pbs')
        hpc.job_id = os.environ.get('PBS_JOBID')
        hpc.job_name = os.environ.get('PBS_JOBNAME')
        hpc.partition = os.environ.get('PBS_QUEUE')
        return hpc
    
    return None


def get_machine_info() -> Tuple[str, str]:
    """Get machine hostname and username"""
    machine = socket.gethostname()
    user = getpass.getuser()
    return machine, user


def compute_file_checksum(filepath: Path, algorithm: str = 'sha256') -> str:
    """Compute file checksum"""
    h = hashlib.new(algorithm)
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return f"{algorithm}:{h.hexdigest()}"


# =============================================================================
# Experiment Discovery
# =============================================================================

def generate_experiment_id(path: Path, run_id: Optional[str] = None) -> str:
    """Generate stable experiment ID"""
    if run_id:
        base = run_id
    else:
        base = str(path.resolve())
    
    hash_val = hashlib.sha256(base.encode()).hexdigest()[:12]
    return f"exp-{hash_val}"


def extract_pod5_metadata(pod5_file: Path) -> Dict[str, Any]:
    """Extract metadata from POD5 file"""
    if not HAS_POD5:
        return {}
    
    metadata = {}
    try:
        with pod5.Reader(pod5_file) as reader:
            for read in reader.reads():
                run_info = read.run_info
                metadata['run_id'] = run_info.acquisition_id
                metadata['sample_id'] = run_info.sample_id
                metadata['experiment_id'] = run_info.experiment_name
                metadata['flowcell_id'] = run_info.flow_cell_id
                metadata['flowcell_type'] = run_info.flow_cell_product_code
                metadata['kit'] = run_info.sequencing_kit
                metadata['platform'] = run_info.system_type
                
                # Extract chemistry from context tags
                for tag in run_info.context_tags:
                    if 'basecall_model' in tag[0].lower():
                        metadata['basecall_model'] = tag[1]
                
                break  # Only need first read
    except Exception as e:
        pass
    
    return metadata


def extract_fast5_metadata(fast5_file: Path) -> Dict[str, Any]:
    """Extract metadata from Fast5 file"""
    if not HAS_H5PY:
        return {}
    
    metadata = {}
    try:
        with h5py.File(fast5_file, 'r') as f:
            # Check for multi-read format
            if 'read_' in str(list(f.keys())):
                read_group = list(f.keys())[0]
                tracking = f[f'{read_group}/tracking_id']
            else:
                tracking = f.get('UniqueGlobalKey/tracking_id', {})
            
            if tracking:
                attrs = dict(tracking.attrs)
                metadata['run_id'] = attrs.get('run_id', b'').decode() if isinstance(attrs.get('run_id'), bytes) else attrs.get('run_id')
                metadata['sample_id'] = attrs.get('sample_id', b'').decode() if isinstance(attrs.get('sample_id'), bytes) else attrs.get('sample_id')
                metadata['flowcell_id'] = attrs.get('flow_cell_id', b'').decode() if isinstance(attrs.get('flow_cell_id'), bytes) else attrs.get('flow_cell_id')
                metadata['platform'] = attrs.get('device_type', b'').decode() if isinstance(attrs.get('device_type'), bytes) else attrs.get('device_type')
    except Exception as e:
        pass
    
    return metadata


def parse_final_summary(filepath: Path) -> Dict[str, Any]:
    """Parse final_summary.txt for run information"""
    metadata = {}
    
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key == 'acquisition_run_id':
                        metadata['run_id'] = value
                    elif key == 'sample_id':
                        metadata['sample_id'] = value
                    elif key == 'experiment_name':
                        metadata['experiment_id'] = value
                    elif key == 'flow_cell_id':
                        metadata['flowcell_id'] = value
                    elif key == 'flow_cell_product_code':
                        metadata['flowcell_type'] = value
                    elif key == 'protocol_run_id':
                        metadata['kit'] = value
                    elif key == 'instrument':
                        metadata['platform'] = value
                    elif key == 'started':
                        metadata['run_started'] = value
                    elif key == 'acquisition_stopped':
                        metadata['run_ended'] = value
    except Exception:
        pass
    
    return metadata


# =============================================================================
# MinKNOW Output Structure Detection
# Based on: https://software-docs.nanoporetech.com/output-specifications/latest/minknow/output_structure/
# =============================================================================

# Official MinKNOW data subdirectories
MINKNOW_DATA_DIRS = {
    # POD5 format (current standard)
    'pod5', 'pod5_pass', 'pod5_fail', 'pod5_skip',
    # FASTQ format
    'fastq_pass', 'fastq_fail',
    # BAM format
    'bam_pass', 'bam_fail',
    # Fast5 format (deprecated but still supported)
    'fast5_pass', 'fast5_fail', 'fast5_skip',
}

# MinKNOW metadata file patterns (glob patterns)
MINKNOW_METADATA_PATTERNS = [
    'final_summary*.txt',           # Run completion summary
    'report_*.html',                # HTML report
    'sequencing_summary*.txt',      # Sequencing details
    'sample_sheet*.csv',            # Sample metadata
    'barcode_alignment*.tsv',       # Barcode assignment data
    'output_hash*.csv',             # Output verification
]

# Optional MinKNOW directories
MINKNOW_OPTIONAL_DIRS = {
    'adaptive_sampling',            # Adaptive sampling data
    'other_reports',                # Additional reports
}


def _has_data_files(path: Path) -> bool:
    """Check if a directory contains actual data files (pod5, fast5, bam)."""
    try:
        for item in path.iterdir():
            if item.is_dir() and item.name in MINKNOW_DATA_DIRS:
                # Check if the data directory has files
                try:
                    for _ in item.iterdir():
                        return True
                except PermissionError:
                    pass
        # Also check for direct data files
        for ext in ['*.pod5', '*.fast5', '*.bam']:
            if list(path.glob(ext)):
                return True
    except PermissionError:
        pass
    return False


def _find_minknow_run_dir(path: Path) -> Optional[Path]:
    """Find the actual MinKNOW run directory within a path.

    MinKNOW structure (pooling disabled):
        {protocol_group_id}/{sample_id}/{timestamp}_{device}_{flowcell}_{run_id}/
            ├── pod5/ or pod5_pass/, pod5_fail/, pod5_skip/
            ├── fastq_pass/, fastq_fail/
            ├── final_summary_*.txt
            ├── report_*.html
            └── sequencing_summary_*.txt

    MinKNOW structure (pooling enabled):
        {protocol_group_id}/{sample_id}/
            ├── pod5/ or pod5_pass/, ...
            └── final_summary_*.txt, ...

    Returns the run directory path, or None if not found.
    Prioritizes directories with actual data files over metadata-only directories.
    """
    # Check if this directory itself is a run directory with data
    if _is_minknow_run_dir(path) and _has_data_files(path):
        return path

    candidates = []
    metadata_only = []

    try:
        # Check immediate subdirectories (sample_id level)
        for subdir in path.iterdir():
            if subdir.is_dir() and not subdir.name.startswith('.'):
                if _is_minknow_run_dir(subdir):
                    if _has_data_files(subdir):
                        candidates.append(subdir)
                    else:
                        metadata_only.append(subdir)
                # Check one more level (timestamp_device_flowcell_runid level)
                try:
                    for subsubdir in subdir.iterdir():
                        if subsubdir.is_dir() and not subsubdir.name.startswith('.'):
                            if _is_minknow_run_dir(subsubdir):
                                if _has_data_files(subsubdir):
                                    candidates.append(subsubdir)
                                else:
                                    metadata_only.append(subsubdir)
                except PermissionError:
                    pass
    except PermissionError:
        pass

    # Prefer directories with data, fall back to metadata-only
    if candidates:
        return candidates[0]
    if metadata_only:
        return metadata_only[0]

    # Fall back to checking path itself even without data
    if _is_minknow_run_dir(path):
        return path

    return None


def _is_minknow_run_dir(path: Path) -> bool:
    """Check if a directory is a MinKNOW run directory.

    A MinKNOW run directory contains:
    - At least one MinKNOW data subdirectory (pod5/, fastq_pass/, etc.)
    - OR at least one MinKNOW metadata file (final_summary_*.txt, report_*.html, etc.)
    """
    if not path.is_dir():
        return False

    try:
        # Check for MinKNOW data directories
        for item in path.iterdir():
            if item.is_dir() and item.name in MINKNOW_DATA_DIRS:
                return True

        # Check for MinKNOW metadata files
        for pattern in MINKNOW_METADATA_PATTERNS:
            if list(path.glob(pattern)):
                return True
    except PermissionError:
        return False

    return False


def _count_experiments_in_subdirs(path: Path, max_to_check: int = 10) -> int:
    """Count how many immediate subdirectories contain experiments.

    Used to detect if a directory is a container (multiple experiments)
    vs an experiment itself.
    """
    count = 0
    checked = 0
    try:
        for subdir in path.iterdir():
            if checked >= max_to_check:
                break
            if subdir.is_dir() and not subdir.name.startswith('.'):
                checked += 1
                # Check if this subdir or any of its subdirs is a run directory
                if _is_minknow_run_dir(subdir):
                    count += 1
                else:
                    # Check one level deeper
                    try:
                        for subsubdir in subdir.iterdir():
                            if subsubdir.is_dir() and not subsubdir.name.startswith('.'):
                                if _is_minknow_run_dir(subsubdir):
                                    count += 1
                                    break
                    except PermissionError:
                        pass
    except PermissionError:
        pass
    return count


def discover_experiment(path: Path) -> Optional[ExperimentMetadata]:
    """Discover and extract metadata from an ONT experiment directory.

    Based on MinKNOW output structure specification:
    https://software-docs.nanoporetech.com/output-specifications/latest/minknow/output_structure/

    Directory structure (pooling disabled - default):
        /data/{protocol_group_id}/{sample_id}/{timestamp}_{device}_{flowcell}_{run_id}/
            ├── pod5/ and/or pod5_skip/
            ├── fastq_pass/ and/or fastq_fail/
            ├── bam_pass/ and/or bam_fail/
            ├── final_summary_{flowcell}_{run_id}_{short_run_id}.txt
            ├── report_{flowcell}_{timestamp}_{run_id}.html
            ├── sequencing_summary_{flowcell}_{run_id}_{short_run_id}.txt
            └── adaptive_sampling/ (optional)

    Directory structure (pooling enabled):
        /data/{protocol_group_id}/{sample_id}/
            └── (same contents as above)

    Returns ExperimentMetadata if valid experiment found, None otherwise.
    """
    path = path.resolve()

    if not path.exists():
        return None

    # First, check if this is a container directory (has multiple experiments in subdirs)
    # If 2+ subdirectories contain experiments, this is a container, not an experiment
    exp_count = _count_experiments_in_subdirs(path, max_to_check=10)
    if exp_count >= 2:
        return None

    # Find the actual run directory (handles nested MinKNOW structure)
    run_dir = _find_minknow_run_dir(path)
    if run_dir is None:
        # No MinKNOW structure found - check for raw data files as fallback
        pod5_files = list(path.glob('*.pod5'))
        fast5_files = list(path.glob('*.fast5'))
        bam_files = list(path.glob('*.bam'))
        if not (pod5_files or fast5_files or bam_files):
            return None
        # Has direct data files - treat as simple experiment
        run_dir = path

    # Collect all data files from the run directory
    pod5_files = list(run_dir.rglob('*.pod5'))
    fast5_files = list(run_dir.rglob('*.fast5'))
    bam_files = list(run_dir.rglob('*.bam'))
    fastq_files = list(run_dir.rglob('*.fastq')) + list(run_dir.rglob('*.fastq.gz'))

    if not pod5_files and not fast5_files and not bam_files:
        return None

    # Determine primary format
    if pod5_files:
        data_format = 'pod5'
        data_files = pod5_files
    elif fast5_files:
        data_format = 'fast5'
        data_files = fast5_files
    else:
        data_format = 'bam'
        data_files = bam_files

    # Calculate size
    total_size = sum(f.stat().st_size for f in data_files)
    total_size_gb = total_size / (1024**3)

    # Extract metadata from various sources
    metadata = {}

    # Find and parse final_summary file (in run_dir or its subdirectories)
    final_summary = None
    for pattern in ['final_summary*.txt', '*/final_summary*.txt', '*/*/final_summary*.txt']:
        summaries = list(run_dir.glob(pattern))
        if summaries:
            final_summary = summaries[0]
            break

    if final_summary:
        metadata.update(parse_final_summary(final_summary))
    
    # Try POD5 metadata
    if pod5_files and HAS_POD5:
        pod5_meta = extract_pod5_metadata(pod5_files[0])
        for k, v in pod5_meta.items():
            if k not in metadata or not metadata[k]:
                metadata[k] = v
    
    # Try Fast5 metadata
    if fast5_files and HAS_H5PY:
        fast5_meta = extract_fast5_metadata(fast5_files[0])
        for k, v in fast5_meta.items():
            if k not in metadata or not metadata[k]:
                metadata[k] = v
    
    # Generate ID
    run_id = metadata.get('run_id')
    exp_id = generate_experiment_id(path, run_id)
    
    # Create experiment
    exp = ExperimentMetadata(
        id=exp_id,
        name=metadata.get('experiment_id') or path.name,
        location=str(path),
        source='local',
        status='discovered',
        run_id=metadata.get('run_id'),
        sample_id=metadata.get('sample_id'),
        experiment_id=metadata.get('experiment_id'),
        platform=metadata.get('platform'),
        flowcell_type=metadata.get('flowcell_type'),
        flowcell_id=metadata.get('flowcell_id'),
        kit=metadata.get('kit'),
        basecall_model=metadata.get('basecall_model'),
        run_started=metadata.get('run_started'),
        run_ended=metadata.get('run_ended'),
        data_format=data_format,
        file_count=len(data_files),
        total_size_gb=round(total_size_gb, 2),
    )
    
    # Add discovery event
    agent, agent_version = detect_agent()
    machine, user = get_machine_info()
    
    discovery_event = Event(
        timestamp=datetime.now(timezone.utc).isoformat(),
        type='discovered',
        agent=agent,
        agent_version=agent_version,
        machine=machine,
        user=user,
    )
    exp.add_event(discovery_event)
    
    return exp


def scan_directory(root: Path, recursive: bool = True) -> List[ExperimentMetadata]:
    """Scan directory for nanopore experiments"""
    experiments = []

    root = root.resolve()
    if not root.exists():
        return experiments

    # Check if root itself is an experiment
    exp = discover_experiment(root)
    if exp:
        experiments.append(exp)
        return experiments  # Don't recurse into an experiment

    # Scan subdirectories
    if recursive:
        try:
            for subdir in root.iterdir():
                if subdir.is_dir() and not subdir.name.startswith('.'):
                    try:
                        exp = discover_experiment(subdir)
                        if exp:
                            experiments.append(exp)
                    except PermissionError:
                        pass
        except PermissionError:
            pass

    return experiments


# =============================================================================
# Analysis Orchestration (Pattern B)
# =============================================================================

def run_analysis(
    experiment: ExperimentMetadata,
    analysis_type: str,
    args: List[str],
    capture_output: bool = True
) -> Event:
    """
    Run an analysis skill and capture full provenance.
    
    Pattern B: This function wraps analysis skills, handling:
    - Command construction
    - Environment detection (HPC, agent)
    - Output file tracking
    - Result extraction
    - Event creation
    """
    
    if analysis_type not in ANALYSIS_SKILLS:
        raise ValueError(f"Unknown analysis type: {analysis_type}")
    
    skill_config = ANALYSIS_SKILLS[analysis_type]
    script = skill_config['script']
    input_mode = skill_config.get('input_mode', 'location')
    default_args = skill_config.get('default_args', [])

    # Build command based on input mode
    if input_mode == 'location':
        # Pass experiment location as first argument
        cmd = ['python3', script] + default_args + [experiment.location] + args
    else:
        # Explicit mode - args must include input/output
        cmd = ['python3', script] + default_args + args
    
    command_str = ' '.join(cmd)
    
    # Detect environment
    agent, agent_version = detect_agent()
    machine, user = get_machine_info()
    hpc = detect_hpc()
    
    # Parse parameters from args
    parameters = {}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith('--'):
            key = arg[2:].replace('-', '_')
            if i + 1 < len(args) and not args[i + 1].startswith('--'):
                parameters[key] = args[i + 1]
                i += 2
            else:
                parameters[key] = True
                i += 1
        elif arg.startswith('-') and len(arg) == 2:
            key = arg[1]
            if i + 1 < len(args) and not args[i + 1].startswith('-'):
                parameters[key] = args[i + 1]
                i += 2
            else:
                parameters[key] = True
                i += 1
        else:
            i += 1
    
    # Track output files from parameters
    output_paths = []
    for key in ['json', 'csv', 'plot', 'output', 'o']:
        if key in parameters and isinstance(parameters[key], str):
            output_paths.append(parameters[key])
    
    # Run the command
    start_time = time.time()
    
    try:
        if capture_output:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=experiment.location,
            )
            exit_code = result.returncode
            stdout = result.stdout
            stderr = result.stderr
        else:
            result = subprocess.run(cmd, cwd=experiment.location)
            exit_code = result.returncode
            stdout = ""
            stderr = ""
    except Exception as e:
        exit_code = -1
        stdout = ""
        stderr = str(e)
    
    duration = time.time() - start_time
    
    # Process output files
    outputs = []
    for output_path in output_paths:
        p = Path(output_path)
        if not p.is_absolute():
            p = Path(experiment.location) / p
        
        if p.exists():
            outputs.append({
                'path': str(p),
                'size_bytes': p.stat().st_size,
                'checksum': compute_file_checksum(p) if p.stat().st_size < 100_000_000 else None,  # Skip large files
            })
    
    # Extract results from JSON output if available
    results = {}
    json_output = parameters.get('json')
    if json_output:
        json_path = Path(json_output)
        if not json_path.is_absolute():
            json_path = Path(experiment.location) / json_path
        
        if json_path.exists():
            try:
                with open(json_path) as f:
                    json_data = json.load(f)
                # Extract relevant fields
                for field in skill_config.get('result_fields', []):
                    if field in json_data:
                        results[field] = json_data[field]
                
                # For basecalling, also capture model path in parameters
                if skill_config.get('capture_model_path') and 'model_path' in json_data:
                    parameters['model_path'] = json_data['model_path']
                    if 'model' in json_data:
                        parameters['model'] = json_data['model']
                    if 'model_tier' in json_data:
                        parameters['model_tier'] = json_data['model_tier']
                    if 'model_version' in json_data:
                        parameters['model_version'] = json_data['model_version']
                    if 'chemistry' in json_data:
                        parameters['chemistry'] = json_data['chemistry']
                        
            except Exception:
                pass
    
    # Create event
    event = Event(
        timestamp=datetime.now(timezone.utc).isoformat(),
        type='analysis',
        analysis=analysis_type,
        command=command_str,
        working_dir=experiment.location,
        parameters=parameters,
        outputs=outputs,
        results=results,
        duration_seconds=round(duration, 2),
        exit_code=exit_code,
        error_message=stderr if exit_code != 0 else None,
        agent=agent,
        agent_version=agent_version,
        machine=machine,
        user=user,
        hpc=hpc.to_dict() if hpc else None,
    )
    
    return event


# =============================================================================
# Output Formatting
# =============================================================================

def print_experiment_table(experiments: List[ExperimentMetadata]):
    """Print experiments as formatted table"""
    if not experiments:
        print("  No experiments found.")
        return
    
    # Header (use ASCII for Windows compatibility)
    print(f"\n  {'ID':<16} {'Name':<30} {'Status':<12} {'Format':<6} {'Size':<8} {'Events'}")
    print(f"  {'-' * 16} {'-' * 30} {'-' * 12} {'-' * 6} {'-' * 8} {'-' * 6}")
    
    for exp in experiments:
        name = exp.name[:28] + '..' if len(exp.name) > 30 else exp.name
        size = f"{exp.total_size_gb:.1f}GB" if exp.total_size_gb else "?"
        events = len(exp.events)
        
        print(f"  {exp.id:<16} {name:<30} {exp.status:<12} {exp.data_format or '?':<6} {size:<8} {events}")


def print_experiment_detail(exp: ExperimentMetadata):
    """Print detailed experiment info"""
    print(f"\n  {'=' * 60}")
    print(f"  Experiment: {exp.id}")
    print(f"  {'=' * 60}")
    
    print(f"\n  Name:       {exp.name}")
    print(f"  Location:   {exp.location}")
    print(f"  Status:     {exp.status}")
    print(f"  Source:     {exp.source}")
    
    if exp.tags:
        print(f"  Tags:       {', '.join(exp.tags)}")
    
    print(f"\n  Platform")
    print(f"  {'-' * 40}")
    if exp.platform:
        print(f"  Device:     {exp.platform}")
    if exp.flowcell_type:
        print(f"  Flowcell:   {exp.flowcell_type} ({exp.flowcell_id or 'ID unknown'})")
    if exp.kit:
        print(f"  Kit:        {exp.kit}")
    if exp.chemistry:
        print(f"  Chemistry:  {exp.chemistry}")
    
    print(f"\n  Data")
    print(f"  {'-' * 40}")
    print(f"  Format:     {exp.data_format or 'unknown'}")
    print(f"  Files:      {exp.file_count}")
    print(f"  Size:       {exp.total_size_gb:.2f} GB")
    if exp.total_reads:
        print(f"  Reads:      {exp.total_reads:,}")
    if exp.total_bases:
        print(f"  Bases:      {exp.total_bases:,}")
    
    if exp.events:
        print(f"\n  Recent Events ({len(exp.events)} total)")
        print(f"  {'-' * 40}")
        for i, event in enumerate(exp.events[-5:], start=max(1, len(exp.events)-4)):
            ts = event.timestamp[:19].replace('T', ' ')
            if event.type == 'analysis':
                print(f"  [{i}] {ts} {event.type}: {event.analysis} ({event.exit_code})")
            else:
                print(f"  [{i}] {ts} {event.type}")


def print_event_history(exp: ExperimentMetadata, verbose: bool = False):
    """Print full event history"""
    print(f"\n  Event History: {exp.id}")
    print(f"  {'=' * 60}")
    
    for i, event in enumerate(exp.events, 1):
        ts = event.timestamp[:19].replace('T', ' ')
        print(f"\n  [{i}] {ts}")
        print(f"      Type: {event.type}")
        
        if event.analysis:
            print(f"      Analysis: {event.analysis}")
        
        if event.command and verbose:
            print(f"      Command: {event.command}")
        
        if event.parameters and verbose:
            print(f"      Parameters: {json.dumps(event.parameters, indent=8)}")
        
        if event.results:
            print(f"      Results: {json.dumps(event.results)}")
        
        if event.duration_seconds:
            print(f"      Duration: {event.duration_seconds:.1f}s")
        
        if event.exit_code is not None:
            status = "✓" if event.exit_code == 0 else f"✗ (exit {event.exit_code})"
            print(f"      Status: {status}")
        
        print(f"      Agent: {event.agent} @ {event.machine}")
        
        if event.hpc:
            print(f"      HPC: {event.hpc.get('scheduler')} job {event.hpc.get('job_id')}")
            if event.hpc.get('nodes'):
                print(f"           Nodes: {', '.join(event.hpc['nodes'])}")
            if event.hpc.get('gpus'):
                print(f"           GPUs: {', '.join(event.hpc['gpus'])}")


def export_commands(exp: ExperimentMetadata) -> str:
    """Export all analysis commands as shell script"""
    lines = [
        "#!/bin/bash",
        f"# Replay commands for experiment: {exp.id}",
        f"# Exported: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"cd {exp.location}",
        "",
    ]
    
    for i, event in enumerate(exp.events, 1):
        if event.type == 'analysis' and event.command:
            lines.append(f"# Event {i}: {event.analysis} @ {event.timestamp[:19]}")
            lines.append(event.command)
            lines.append("")
    
    return '\n'.join(lines)


# =============================================================================
# Commands
# =============================================================================

def cmd_init(args):
    """Initialize registry"""
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    
    if not REGISTRY_FILE.exists():
        save_registry(Registry())
        print(f"  Created registry: {REGISTRY_FILE}")
    else:
        print(f"  Registry exists: {REGISTRY_FILE}")
    
    if args.git and HAS_GIT:
        git_dir = REGISTRY_DIR / '.git'
        if not git_dir.exists():
            repo = Repo.init(REGISTRY_DIR)
            
            # Create .gitignore
            gitignore = REGISTRY_DIR / '.gitignore'
            gitignore.write_text("*.tmp\n*.bak\n")
            
            repo.index.add([str(REGISTRY_FILE.name), '.gitignore'])
            repo.index.commit("Initialize ONT experiment registry")
            
            print(f"  Initialized git repository")
            print(f"  Add remote: cd {REGISTRY_DIR} && git remote add origin <url>")
        else:
            print(f"  Git already initialized")
    elif args.git and not HAS_GIT:
        print(f"  Warning: gitpython not installed, skipping git init")
    
    return 0


def cmd_discover(args):
    """Discover experiments with optional quick analysis"""
    path = Path(args.directory).resolve()

    if not path.exists():
        print(f"Error: Path not found: {path}")
        return 1

    print(f"\n  Scanning: {path}")
    experiments = scan_directory(path, recursive=not args.no_recursive)

    print(f"  Found: {len(experiments)} experiments")

    if not experiments:
        return 0

    # --interactive implies --analyze
    if args.interactive:
        args.analyze = True

    # Quick analysis mode
    if args.analyze:
        return cmd_discover_analyze(args, path, experiments)

    # Standard mode: register or display
    if args.register:
        registry = load_registry()
        registered = 0
        for exp in experiments:
            exp.status = 'registered'
            if registry.add(exp):
                registered += 1
                print(f"    + {exp.id}: {exp.name}")
            else:
                print(f"    = {exp.id}: already registered")

        save_registry(registry)
        print(f"\n  Registered: {registered} new experiments")
    else:
        print_experiment_table(experiments)

    return 0


def cmd_discover_analyze(args, path: Path, experiments: list):
    """Run quick analysis on discovered experiments.

    Args:
        args: Command line arguments
        path: Source directory path
        experiments: List of discovered ExperimentMetadata
    """
    import time

    # Import analysis modules - add lib to path first
    import sys
    lib_path = str(Path(__file__).parent.parent / 'lib')
    if lib_path not in sys.path:
        sys.path.insert(0, lib_path)

    from quick_analysis import quick_analyze_batch, aggregate_summaries
    from discovery_report import (
        display_terminal_summary, generate_json_report,
        generate_html_dashboard, generate_comparison_table
    )

    print(f"\n  Running quick analysis on {len(experiments)} experiments...")

    # Run analysis
    start_time = time.time()
    analyzed = 0

    def progress():
        nonlocal analyzed
        analyzed += 1
        pct = int(analyzed / len(experiments) * 100)
        print(f"\r  Analyzing: {analyzed}/{len(experiments)} ({pct}%)", end='', flush=True)

    summaries = quick_analyze_batch(experiments, parallel=True, max_workers=4,
                                    progress_callback=progress)
    elapsed = time.time() - start_time
    print()  # newline after progress

    # Determine output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = path / '.ont-discovery'

    # Display terminal summary
    display_terminal_summary(summaries, str(path), elapsed)

    # Generate reports
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = generate_json_report(summaries, output_dir / 'discovery_report.json',
                                     str(path), elapsed)
    html_path = generate_html_dashboard(summaries, output_dir / 'discovery_dashboard.html',
                                        str(path), elapsed)

    print(f"  Reports saved:")
    print(f"    JSON: {json_path}")
    print(f"    HTML: {html_path}")

    # Generate comparison if multiple experiments
    if len(experiments) > 1 and not args.no_compare:
        csv_path = generate_comparison_table(summaries, output_dir / 'comparison_table.csv')
        print(f"    CSV:  {csv_path}")

    # Interactive menu
    if args.interactive:
        return interactive_discovery_menu(experiments, summaries, path, output_dir)

    return 0


def interactive_discovery_menu(experiments: list, summaries: list, source_path: Path, output_dir: Path) -> int:
    """Interactive menu for post-discovery actions.

    Args:
        experiments: List of ExperimentMetadata objects
        summaries: List of QuickSummary objects
        source_path: Source directory path
        output_dir: Output directory for reports

    Returns:
        Exit code
    """
    import webbrowser

    def print_menu():
        print("\n  " + "=" * 60)
        print("  What would you like to do next?")
        print("  " + "-" * 60)
        print("  [1] Run FULL analysis on all experiments")
        print("  [2] Run FULL analysis on selected experiments")
        print("  [3] Generate comparison heatmap (requires matplotlib)")
        print("  [4] Open HTML dashboard in browser")
        print("  [5] Export to different format (CSV/TSV/JSON)")
        print("  [6] Register all experiments to registry")
        print("  [7] View experiment details")
        print("  [0] Exit")
        print("  " + "=" * 60)

    while True:
        print_menu()
        try:
            choice = input("\n  Enter choice [0-7]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Exiting...")
            return 0

        if choice == '0':
            print("\n  Goodbye!")
            return 0

        elif choice == '1':
            # Full analysis on all
            print("\n  Running full analysis on all experiments...")
            print("  Available analyses: end_reasons")
            analysis_choice = input("  Which analysis? [end_reasons]: ").strip() or 'end_reasons'

            for exp in experiments:
                print(f"\n    [{exp.name}]")
                try:
                    # Run end_reason.py directly on the experiment location
                    import subprocess
                    script_dir = Path(__file__).parent
                    script_path = script_dir / 'end_reason.py'

                    if not script_path.exists():
                        # Try skills location
                        script_path = script_dir.parent / 'skills' / 'end-reason' / 'scripts' / 'end_reason.py'

                    if script_path.exists():
                        # Find the actual data directory (MinKNOW nests data)
                        data_path = Path(exp.location)
                        # Look for sequencing_summary in nested paths
                        seq_summaries = list(data_path.rglob('sequencing_summary*.txt'))
                        if seq_summaries:
                            data_path = seq_summaries[0].parent

                        result = subprocess.run(
                            ['python3', str(script_path), str(data_path), '--quick'],
                            capture_output=True,
                            text=True,
                            timeout=300
                        )
                        # Filter numpy warnings from stderr and show stdout
                        if result.stdout.strip():
                            for line in result.stdout.strip().split('\n'):
                                print(f"      {line}")
                        if result.returncode != 0:
                            # Show error but filter numpy warnings
                            stderr_lines = [l for l in result.stderr.split('\n')
                                          if 'NumPy' not in l and '_ARRAY_API' not in l
                                          and 'pybind11' not in l and l.strip()]
                            if stderr_lines:
                                print(f"      Error: {' '.join(stderr_lines[:3])}")
                    else:
                        print(f"      Error: Analysis script not found")
                except subprocess.TimeoutExpired:
                    print(f"      Error: Analysis timed out (>5 min)")
                except Exception as e:
                    print(f"      Error: {e}")

            print("\n  Full analysis complete!")

        elif choice == '2':
            # Select experiments
            print("\n  Select experiments (comma-separated numbers, or 'all'):")
            for i, exp in enumerate(experiments):
                grade = summaries[i].quality_grade if i < len(summaries) else '?'
                print(f"    [{i+1}] {exp.name} (Grade {grade})")

            selection = input("\n  Selection: ").strip()
            if selection.lower() == 'all':
                selected = experiments
            else:
                try:
                    indices = [int(x.strip()) - 1 for x in selection.split(',')]
                    selected = [experiments[i] for i in indices if 0 <= i < len(experiments)]
                except ValueError:
                    print("  Invalid selection")
                    continue

            print(f"\n  Running full analysis on {len(selected)} experiments...")
            for exp in selected:
                print(f"\n    [{exp.name}]")
                try:
                    import subprocess
                    script_dir = Path(__file__).parent
                    script_path = script_dir / 'end_reason.py'
                    if not script_path.exists():
                        script_path = script_dir.parent / 'skills' / 'end-reason' / 'scripts' / 'end_reason.py'

                    if script_path.exists():
                        # Find the actual data directory (MinKNOW nests data)
                        data_path = Path(exp.location)
                        seq_summaries = list(data_path.rglob('sequencing_summary*.txt'))
                        if seq_summaries:
                            data_path = seq_summaries[0].parent

                        result = subprocess.run(
                            ['python3', str(script_path), str(data_path), '--quick'],
                            capture_output=True, text=True, timeout=300
                        )
                        if result.stdout.strip():
                            for line in result.stdout.strip().split('\n'):
                                print(f"      {line}")
                        if result.returncode != 0:
                            stderr_lines = [l for l in result.stderr.split('\n')
                                          if 'NumPy' not in l and '_ARRAY_API' not in l
                                          and 'pybind11' not in l and l.strip()]
                            if stderr_lines:
                                print(f"      Error: {' '.join(stderr_lines[:3])}")
                    else:
                        print(f"      Error: Analysis script not found")
                except subprocess.TimeoutExpired:
                    print(f"      Error: Timed out (>5 min)")
                except Exception as e:
                    print(f"      Error: {e}")

        elif choice == '3':
            # Generate heatmap
            print("\n  Generating comparison heatmap...")
            try:
                heatmap_path = output_dir / 'metrics_heatmap.png'
                generate_metrics_heatmap(summaries, heatmap_path)
                print(f"  Saved: {heatmap_path}")
            except ImportError as e:
                print("  Error: matplotlib not available")
                print("  This may be due to numpy version incompatibility.")
                print("  To fix, try one of:")
                print("    pip install 'numpy<2'  # downgrade numpy")
                print("    pip install --upgrade matplotlib  # upgrade matplotlib")
            except AttributeError as e:
                if '_ARRAY_API' in str(e) or 'numpy' in str(e).lower():
                    print("  Error: matplotlib/numpy version mismatch")
                    print("  Your matplotlib was compiled against numpy 1.x but numpy 2.x is installed.")
                    print("  To fix, run one of:")
                    print("    pip install 'numpy<2'  # downgrade numpy")
                    print("    pip install --upgrade matplotlib  # upgrade matplotlib")
                else:
                    print(f"  Error: {e}")
            except Exception as e:
                print(f"  Error: {e}")

        elif choice == '4':
            # Open HTML dashboard
            html_path = output_dir / 'discovery_dashboard.html'
            if html_path.exists():
                print(f"\n  Opening: {html_path}")
                webbrowser.open(f'file://{html_path}')
            else:
                print("  Error: HTML dashboard not found")

        elif choice == '5':
            # Export
            print("\n  Export format:")
            print("    [1] CSV")
            print("    [2] TSV")
            print("    [3] JSON")
            fmt_choice = input("  Choice: ").strip()

            from lib.discovery_report import generate_comparison_table

            fmt_map = {'1': 'csv', '2': 'tsv', '3': 'json'}
            fmt = fmt_map.get(fmt_choice, 'csv')
            ext = fmt if fmt != 'tsv' else 'tsv'
            export_path = output_dir / f'experiments.{ext}'
            generate_comparison_table(summaries, export_path, format=fmt)
            print(f"  Exported: {export_path}")

        elif choice == '6':
            # Register all
            registry = load_registry()
            registered = 0
            for exp in experiments:
                exp.status = 'registered'
                if registry.add(exp):
                    registered += 1
                    print(f"    + {exp.id}: {exp.name}")
                else:
                    print(f"    = {exp.id}: already registered")
            save_registry(registry)
            print(f"\n  Registered: {registered} new experiments")

        elif choice == '7':
            # View details
            print("\n  Select experiment:")
            for i, exp in enumerate(experiments):
                print(f"    [{i+1}] {exp.name}")
            try:
                idx = int(input("  Choice: ").strip()) - 1
                if 0 <= idx < len(experiments):
                    print_experiment_detail(experiments[idx])
                    if idx < len(summaries):
                        s = summaries[idx]
                        print(f"\n  Quick Analysis:")
                        print(f"    Grade: {s.quality_grade}")
                        print(f"    Reads: {s.total_reads}")
                        print(f"    Q-Score: {s.mean_qscore}")
                        print(f"    N50: {s.n50}")
                        if s.issues:
                            print(f"    Issues: {', '.join(s.issues)}")
            except (ValueError, IndexError):
                print("  Invalid selection")

        else:
            print("  Invalid choice")

    return 0


def generate_metrics_heatmap(summaries: list, output_path: Path) -> Path:
    """Generate a metrics comparison heatmap.

    Args:
        summaries: List of QuickSummary objects
        output_path: Path for output image

    Returns:
        Path to generated image
    """
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
    except (ImportError, AttributeError) as e:
        # AttributeError catches numpy version incompatibility (_ARRAY_API not found)
        raise ImportError(f"matplotlib required for heatmap generation: {e}")

    # Prepare data
    metrics = ['Q-Score', 'N50 (K)', 'Pass Rate', 'Reads (M)']
    names = [s.name[:20] for s in summaries]

    data = []
    for s in summaries:
        row = [
            s.mean_qscore or 0,
            (s.n50 or 0) / 1000,
            s.pass_rate or 0,
            (s.total_reads or 0) / 1_000_000,
        ]
        data.append(row)

    data = np.array(data)

    # Normalize each column to 0-1 for heatmap
    data_norm = np.zeros_like(data)
    for i in range(data.shape[1]):
        col = data[:, i]
        if col.max() > col.min():
            data_norm[:, i] = (col - col.min()) / (col.max() - col.min())
        else:
            data_norm[:, i] = 0.5

    # Create heatmap
    fig, ax = plt.subplots(figsize=(10, max(6, len(summaries) * 0.4)))

    im = ax.imshow(data_norm, cmap='RdYlGn', aspect='auto')

    # Labels
    ax.set_xticks(range(len(metrics)))
    ax.set_xticklabels(metrics)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)

    # Annotate with actual values
    for i in range(len(names)):
        for j in range(len(metrics)):
            val = data[i, j]
            if j == 2:  # Pass rate
                text = f'{val:.0f}%'
            elif j == 0:  # Q-score
                text = f'{val:.1f}'
            else:
                text = f'{val:.1f}'
            ax.text(j, i, text, ha='center', va='center', fontsize=8)

    ax.set_title('Experiment Metrics Comparison')
    plt.colorbar(im, ax=ax, label='Normalized Value')
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    return output_path


def cmd_register(args):
    """Register single experiment"""
    path = Path(args.directory).resolve()
    
    exp = discover_experiment(path)
    if not exp:
        print(f"Error: No nanopore data found in: {path}")
        return 1
    
    if args.name:
        exp.name = args.name
    if args.tags:
        exp.tags = [t.strip() for t in args.tags.split(',')]
    if args.status:
        exp.status = args.status
    else:
        exp.status = 'registered'
    
    registry = load_registry()
    
    existing = registry.find(exp.id)
    if existing and not args.force:
        print(f"Error: Experiment already registered: {exp.id}")
        print(f"       Use --force to update")
        return 1
    
    if existing:
        registry.update(exp)
        print(f"Updated: {exp.id}")
    else:
        registry.add(exp)
        print(f"Registered: {exp.id}")
    
    save_registry(registry)
    print_experiment_detail(exp)
    
    return 0


def cmd_list(args):
    """List experiments"""
    # Use GitHub if requested or local doesn't exist
    prefer_github = getattr(args, 'github', False)
    registry = load_registry(prefer_github=prefer_github)
    experiments = registry.experiments
    
    # Filter
    if args.status:
        experiments = [e for e in experiments if e.status == args.status]
    if args.tag:
        experiments = [e for e in experiments if args.tag in e.tags]
    if args.source:
        experiments = [e for e in experiments if e.source == args.source]
    
    # Determine source indicator
    if REGISTRY_FILE.exists() and not prefer_github:
        source_msg = f"Local: {REGISTRY_FILE}"
    else:
        source_msg = f"GitHub: {GITHUB_REGISTRY_URL.split('/')[-2]}/registry"
    
    print(f"\n  Registry: {source_msg}")
    print(f"  Updated: {registry.updated[:19] if registry.updated else 'unknown'}")
    print(f"  Total: {len(registry.experiments)} experiments")
    
    if args.status or args.tag or args.source:
        print(f"  Filtered: {len(experiments)}")
    
    print_experiment_table(experiments)
    print()
    
    return 0


def cmd_info(args):
    """Show experiment details"""
    prefer_github = getattr(args, 'github', False)
    registry = load_registry(prefer_github=prefer_github)
    
    exp = registry.find(args.experiment_id)
    if not exp:
        print(f"Error: Experiment not found: {args.experiment_id}")
        return 1
    
    print_experiment_detail(exp)
    
    if args.json:
        print(f"\n  Full JSON:")
        print(json.dumps(exp.to_dict(), indent=2))
    
    return 0


def cmd_run(args):
    """Run analysis with event logging"""
    registry = load_registry()
    
    exp = registry.find(args.experiment_id)
    if not exp:
        print(f"Error: Experiment not found: {args.experiment_id}")
        return 1
    
    analysis_type = args.analysis
    if analysis_type not in ANALYSIS_SKILLS:
        print(f"Error: Unknown analysis: {analysis_type}")
        print(f"       Available: {', '.join(ANALYSIS_SKILLS.keys())}")
        return 1
    
    print(f"\n  Running: {analysis_type}")
    print(f"  Experiment: {exp.id}")
    print(f"  Location: {exp.location}")
    
    # Run analysis
    event = run_analysis(exp, analysis_type, args.args)
    
    # Add event to experiment
    exp.add_event(event)
    exp.status = 'analyzing' if event.exit_code != 0 else 'complete'
    
    registry.update(exp)
    save_registry(registry)
    
    # Report
    if event.exit_code == 0:
        print(f"\n  ✓ Success ({event.duration_seconds:.1f}s)")
        if event.results:
            print(f"  Results: {json.dumps(event.results)}")
    else:
        print(f"\n  ✗ Failed (exit {event.exit_code})")
        if event.error_message:
            print(f"  Error: {event.error_message[:200]}")
    
    if event.hpc:
        print(f"  HPC: {event.hpc.get('scheduler')} job {event.hpc.get('job_id')}")
    
    print(f"\n  Event recorded: #{len(exp.events)}")
    
    return event.exit_code or 0


def cmd_history(args):
    """Show event history"""
    registry = load_registry()
    
    exp = registry.find(args.experiment_id)
    if not exp:
        print(f"Error: Experiment not found: {args.experiment_id}")
        return 1
    
    print_event_history(exp, verbose=args.verbose)
    
    return 0


def cmd_export(args):
    """Export commands as shell script"""
    registry = load_registry()
    
    exp = registry.find(args.experiment_id)
    if not exp:
        print(f"Error: Experiment not found: {args.experiment_id}")
        return 1
    
    script = export_commands(exp)
    print(script)
    
    return 0


def cmd_replay(args):
    """Replay a specific event"""
    registry = load_registry()
    
    exp = registry.find(args.experiment_id)
    if not exp:
        print(f"Error: Experiment not found: {args.experiment_id}")
        return 1
    
    event_num = args.event
    if event_num < 1 or event_num > len(exp.events):
        print(f"Error: Event {event_num} not found (1-{len(exp.events)})")
        return 1
    
    event = exp.events[event_num - 1]
    
    if event.type != 'analysis' or not event.command:
        print(f"Error: Event {event_num} is not a replayable analysis")
        return 1
    
    print(f"\n  Replay Event #{event_num}")
    print(f"  Command: {event.command}")
    print(f"  Working dir: {event.working_dir or exp.location}")
    
    if args.dry_run:
        print(f"\n  [DRY RUN - not executed]")
        return 0
    
    # Execute
    print(f"\n  Executing...")
    result = subprocess.run(
        event.command,
        shell=True,
        cwd=event.working_dir or exp.location,
    )
    
    return result.returncode


def cmd_tag(args):
    """Manage tags"""
    registry = load_registry()
    
    exp = registry.find(args.experiment_id)
    if not exp:
        print(f"Error: Experiment not found: {args.experiment_id}")
        return 1
    
    if args.add:
        for tag in args.add.split(','):
            tag = tag.strip()
            if tag and tag not in exp.tags:
                exp.tags.append(tag)
    
    if args.remove:
        for tag in args.remove.split(','):
            tag = tag.strip()
            if tag in exp.tags:
                exp.tags.remove(tag)
    
    registry.update(exp)
    save_registry(registry)
    
    print(f"Tags: {', '.join(exp.tags) or '(none)'}")
    
    return 0


def cmd_status(args):
    """Update status"""
    registry = load_registry()
    
    exp = registry.find(args.experiment_id)
    if not exp:
        print(f"Error: Experiment not found: {args.experiment_id}")
        return 1
    
    old_status = exp.status
    exp.status = args.status
    
    # Add event
    agent, _ = detect_agent()
    machine, user = get_machine_info()
    
    event = Event(
        timestamp=datetime.now(timezone.utc).isoformat(),
        type='status_change',
        notes=f"{old_status} -> {args.status}",
        agent=agent,
        machine=machine,
        user=user,
    )
    exp.add_event(event)
    
    registry.update(exp)
    save_registry(registry)
    
    print(f"Status: {old_status} -> {args.status}")
    
    return 0


def cmd_public(args):
    """List public datasets"""
    print(f"\n  Public ONT Datasets")
    print(f"  {'=' * 60}")
    
    # Group by category
    categories = defaultdict(list)
    for dataset_id, info in PUBLIC_DATASETS.items():
        categories[info.get('category', 'other')].append((dataset_id, info))
    
    for category, datasets in sorted(categories.items()):
        print(f"\n  {category.replace('_', ' ').title()}")
        print(f"  {'-' * 50}")
        
        for dataset_id, info in datasets:
            featured = " ⭐" if info.get('featured') else ""
            print(f"  {dataset_id}{featured}")
            print(f"    {info['name']}")
            print(f"    Size: {info.get('size', 'unknown')}")
    
    print(f"\n  Access:")
    print(f"    ont_experiments.py public <id> --url   # Get web URL")
    print(f"    ont_experiments.py fetch <id> /dest    # Download")
    
    # Show specific dataset if requested
    if hasattr(args, 'dataset_id') and args.dataset_id:
        dataset_id = args.dataset_id
        if dataset_id not in PUBLIC_DATASETS:
            print(f"\n  Error: Unknown dataset: {dataset_id}")
            return 1
        
        info = PUBLIC_DATASETS[dataset_id]
        
        if args.url:
            print(f"\n  Web URL: {info['web_url']}")
            print(f"  S3 Path: {info['s3_path']}")
    
    return 0


def cmd_fetch(args):
    """Fetch public dataset"""
    dataset_id = args.dataset_id
    
    if dataset_id not in PUBLIC_DATASETS:
        print(f"Error: Unknown dataset: {dataset_id}")
        print(f"       Use 'ont_experiments.py public' to list available datasets")
        return 1
    
    info = PUBLIC_DATASETS[dataset_id]
    dest = Path(args.destination)
    
    print(f"\n  Dataset: {dataset_id}")
    print(f"  Name: {info['name']}")
    print(f"  Size: {info.get('size', 'unknown')}")
    print(f"  Destination: {dest}")
    
    if args.dry_run:
        print(f"\n  [DRY RUN]")
        print(f"  Would download from: {info['s3_path']}")
        print(f"  Web alternative: {info['web_url']}")
        return 0
    
    # Attempt S3 download
    print(f"\n  Attempting S3 download...")
    print(f"  Note: S3 listing may fail (403), use web URL as fallback")
    
    dest.mkdir(parents=True, exist_ok=True)
    
    try:
        result = subprocess.run(
            ['aws', 's3', 'sync', info['s3_path'], str(dest), '--no-sign-request', '--region', 'eu-west-1'],
            capture_output=True,
            text=True,
        )
        
        if result.returncode == 0:
            print(f"  ✓ Download complete")
        else:
            print(f"  ✗ S3 sync failed")
            print(f"  Alternative: {info['web_url']}")
            return 1
    except FileNotFoundError:
        print(f"  AWS CLI not found")
        print(f"  Alternative: {info['web_url']}")
        return 1
    
    # Register if requested
    if args.register:
        exp = discover_experiment(dest)
        if exp:
            exp.source = 'ont-open-data'
            exp.name = info['name']
            
            registry = load_registry()
            registry.add(exp)
            save_registry(registry)
            
            print(f"\n  Registered: {exp.id}")
    
    return 0


def cmd_remove(args):
    """Remove from registry"""
    registry = load_registry()

    if registry.remove(args.experiment_id):
        save_registry(registry)
        print(f"Removed: {args.experiment_id}")
        return 0
    else:
        print(f"Not found: {args.experiment_id}")
        return 1


# =============================================================================
# Domain Memory Commands
# =============================================================================

def cmd_tasks(args):
    """View and manage experiment tasks (v2.0 with dependencies)"""
    ctx = bootup_check(args.experiment_id)
    if not ctx:
        print(f"Error: Experiment not found: {args.experiment_id}")
        return 1

    verbose = getattr(args, 'verbose', False)

    print(f"\nTasks for {ctx.experiment.name}")
    print(f"Version: {ctx.tasks.version}")
    print("=" * 60)

    status_icons = {
        "pending": "○",
        "in_progress": "◐",
        "passing": "✓",
        "failing": "✗",
        "skipped": "−",
        "blocked": "⊘"
    }

    # Group tasks by pipeline stage
    by_stage = defaultdict(list)
    for task in ctx.tasks.tasks:
        stage = task.pipeline_stage or "other"
        by_stage[stage].append(task)

    # Stage display order and labels
    stage_labels = {
        "σ": "Signal (σ)",
        "r": "Basecalling (r)",
        "h": "Haplotype (h)",
        "other": "Other"
    }

    for stage in ["σ", "r", "h", "other"]:
        if stage in by_stage:
            print(f"\n{stage_labels.get(stage, stage)}:")
            for task in by_stage[stage]:
                icon = status_icons.get(task.status, "?")
                priority_marker = f"[P{task.priority}]" if verbose else ""
                runnable = "▶" if task.is_runnable(ctx.tasks) else " "
                print(f"  {runnable}{icon} {task.name}: {task.status} {priority_marker}")

                if task.description and verbose:
                    print(f"       {task.description}")
                if task.skill:
                    print(f"       Skill: {task.skill}")
                if task.dependencies:
                    print(f"       Depends on: {', '.join(task.dependencies)}")
                if task.error:
                    print(f"       Error: {task.error}")
                if task.last_run and verbose:
                    print(f"       Last run: {task.last_run[:19]}")
                if task.attempts > 0 and verbose:
                    print(f"       Attempts: {task.attempts}")

    # Summary
    summary = ctx.tasks.get_progress_summary()
    print("\n" + "=" * 60)
    print("Summary:")
    for status, count in sorted(summary.items()):
        print(f"  {status_icons.get(status, '?')} {status}: {count}")

    # Runnable tasks
    runnable = ctx.tasks.get_runnable_tasks()
    if runnable:
        print(f"\nReady to run ({len(runnable)}):")
        for task in sorted(runnable, key=lambda t: t.priority):
            print(f"  ▶ {task.name}")

    # Blocked tasks
    blocked = ctx.tasks.get_blocked_tasks()
    if blocked:
        print(f"\nBlocked ({len(blocked)}):")
        for task in blocked:
            print(f"  ⊘ {task.name}")

    # Recommendations
    if ctx.recommendations:
        print(f"\nRecommendation: {ctx.recommendations[0]}")

    return 0


def cmd_progress(args):
    """View experiment progress log"""
    progress_file = get_experiment_dir(args.experiment_id) / "PROGRESS.md"

    if progress_file.exists():
        print(progress_file.read_text())
    else:
        print(f"No progress log found for {args.experiment_id}")
        print("Run 'ont_experiments.py init-tasks <exp_id>' to initialize domain memory.")

    return 0


def cmd_init_tasks(args):
    """Initialize domain memory scaffolding for an experiment"""
    registry = load_registry()
    exp = registry.find(args.experiment_id)

    if not exp:
        print(f"Error: Experiment not found: {args.experiment_id}")
        return 1

    exp_dir = get_experiment_dir(exp.id)

    # Check if already initialized
    tasks_file = exp_dir / "tasks.yaml"
    if tasks_file.exists() and not args.force:
        print(f"Domain memory already initialized for {exp.id}")
        print(f"  Tasks: {tasks_file}")
        print("Use --force to reinitialize.")
        return 0

    # Create task list
    tasks = initialize_tasks(exp)
    save_tasks(tasks)

    # Create progress log
    initialize_progress(exp)

    # Optionally create experiment CLAUDE.md
    if args.claude_md:
        claude_md_file = exp_dir / "CLAUDE.md"
        claude_md_content = f"""# CLAUDE.md - {exp.name}

This file provides context for AI agents working with this experiment.

## Experiment Info
- **ID:** {exp.id}
- **Name:** {exp.name}
- **Location:** {exp.location}
- **Platform:** {exp.platform or 'Unknown'}
- **Status:** {exp.status}

## Task Workflow

1. Run `ont_experiments.py tasks {exp.id}` to see current task status
2. Run `ont_experiments.py next {exp.id}` to get the next recommended task
3. Execute analyses via `ont_experiments.py run <task> {exp.id}`
4. Check progress with `ont_experiments.py progress {exp.id}`

## Notes

Add experiment-specific notes here.
"""
        claude_md_file.write_text(claude_md_content)
        print(f"  CLAUDE.md: {claude_md_file}")

    print(f"Initialized domain memory for {exp.id}")
    print(f"  Directory: {exp_dir}")
    print(f"  Tasks: {tasks_file}")
    print(f"  Progress: {exp_dir / 'PROGRESS.md'}")

    return 0


def cmd_next(args):
    """Get next recommended task for an experiment (v2.0 with dependency awareness)"""
    ctx = bootup_check(args.experiment_id)

    if not ctx:
        print(f"Error: Experiment not found: {args.experiment_id}")
        return 1

    # Use v2.0 dependency-aware task selection
    next_task = ctx.tasks.get_next_task()
    blocked_tasks = ctx.tasks.get_blocked_tasks()
    summary = ctx.tasks.get_progress_summary()

    if args.json:
        # Machine-readable output for agents
        output = {
            "experiment_id": ctx.experiment.id,
            "experiment_name": ctx.experiment.name,
            "version": ctx.tasks.version,
            "summary": summary,
            "blocked_count": len(blocked_tasks),
        }

        if ctx.failing_tasks:
            task = ctx.failing_tasks[0]
            output["recommendation"] = "fix"
            output["task"] = task.name
            output["pipeline_stage"] = task.pipeline_stage
            output["skill"] = task.skill
            output["error"] = task.error
            output["command"] = f"ont_experiments.py run {task.name} {ctx.experiment.id}"
        elif next_task:
            output["recommendation"] = "next"
            output["task"] = next_task.name
            output["pipeline_stage"] = next_task.pipeline_stage
            output["skill"] = next_task.skill
            output["priority"] = next_task.priority
            output["dependencies"] = next_task.dependencies
            output["command"] = f"ont_experiments.py run {next_task.name} {ctx.experiment.id}"
        elif blocked_tasks:
            output["recommendation"] = "blocked"
            output["task"] = None
            output["blocked_by"] = [t.name for t in blocked_tasks]
            output["command"] = None
        else:
            output["recommendation"] = "done"
            output["task"] = None
            output["command"] = None

        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        if ctx.failing_tasks:
            task = ctx.failing_tasks[0]
            print(f"FIX: {task.name} (failing)")
            if task.pipeline_stage:
                print(f"Stage: {task.pipeline_stage}")
            if task.skill:
                print(f"Skill: {task.skill}")
            if task.error:
                print(f"Error: {task.error}")
            print(f"Run: ont_experiments.py run {task.name} {ctx.experiment.id}")
        elif next_task:
            print(f"NEXT: {next_task.name} [P{next_task.priority}]")
            print(f"Description: {next_task.description}")
            if next_task.pipeline_stage:
                print(f"Stage: {next_task.pipeline_stage}")
            if next_task.skill:
                print(f"Skill: {next_task.skill}")
            if next_task.dependencies:
                print(f"Dependencies: {', '.join(next_task.dependencies)} (satisfied)")
            print(f"Run: ont_experiments.py run {next_task.name} {ctx.experiment.id}")
        elif blocked_tasks:
            print("BLOCKED: All pending tasks are blocked by failing dependencies")
            for task in blocked_tasks[:3]:
                print(f"  - {task.name} blocked by failing dependency")
            print("\nFix failing tasks first.")
        else:
            print("DONE: All tasks complete!")
            print(f"Summary: {summary}")

    return 0


# =============================================================================
# Math Registry Commands
# =============================================================================

def get_registry_path() -> Path:
    """Get path to the registry directory (relative to this script)"""
    script_dir = Path(__file__).parent.parent
    return script_dir / "registry"


def load_math_registry() -> Dict:
    """Load the math equations registry

    Authoritative source: textbook/equations.yaml
    """
    # Primary location: textbook/equations.yaml (authoritative)
    script_dir = Path(__file__).parent.parent
    textbook_path = script_dir / "textbook" / "equations.yaml"

    if textbook_path.exists() and HAS_YAML:
        with open(textbook_path) as f:
            return yaml.safe_load(f)

    return {"equations": {}}


def load_variables_registry() -> Dict:
    """Load the variables registry

    Authoritative source: textbook/variables.yaml
    """
    # Primary location: textbook/variables.yaml (authoritative)
    script_dir = Path(__file__).parent.parent
    textbook_path = script_dir / "textbook" / "variables.yaml"

    if textbook_path.exists() and HAS_YAML:
        with open(textbook_path) as f:
            return yaml.safe_load(f)

    return {"variables": {}}


def load_pipeline_stages() -> Dict:
    """Load the pipeline stages registry"""
    registry_path = get_registry_path() / "pipeline"
    filepath = registry_path / "stages.yaml"

    if filepath.exists() and HAS_YAML:
        with open(filepath) as f:
            return yaml.safe_load(f)

    return {"stages": []}


# =============================================================================
# Schema Validation
# =============================================================================

def load_schema(schema_name: str) -> Optional[Dict]:
    """Load a JSON schema from the registry/schemas directory"""
    schema_path = get_registry_path() / "schemas" / f"{schema_name}.json"
    if schema_path.exists():
        with open(schema_path) as f:
            return json.load(f)
    return None


def validate_equation(equation: Dict, equation_id: str) -> List[str]:
    """Validate a single equation against the schema"""
    errors = []
    schema = load_schema("equation")

    if not schema:
        return ["Schema not found: equation.json"]

    if not HAS_JSONSCHEMA:
        return ["jsonschema not installed"]

    try:
        jsonschema.validate(equation, schema)
    except jsonschema.ValidationError as e:
        errors.append(f"{equation_id}: {e.message}")

    return errors


def validate_pipeline_stage(stage: Dict, stage_id: str) -> List[str]:
    """Validate a single pipeline stage against the schema"""
    errors = []
    schema = load_schema("pipeline_stage")

    if not schema:
        return ["Schema not found: pipeline_stage.json"]

    if not HAS_JSONSCHEMA:
        return ["jsonschema not installed"]

    try:
        jsonschema.validate(stage, schema)
    except jsonschema.ValidationError as e:
        errors.append(f"{stage_id}: {e.message}")

    return errors


def validate_task(task: Dict, task_name: str) -> List[str]:
    """Validate a single task against the schema"""
    errors = []
    schema = load_schema("task")

    if not schema:
        return ["Schema not found: task.json"]

    if not HAS_JSONSCHEMA:
        return ["jsonschema not installed"]

    try:
        jsonschema.validate(task, schema)
    except jsonschema.ValidationError as e:
        errors.append(f"{task_name}: {e.message}")

    return errors


def validate_registry(target: str = "all") -> Dict[str, List[str]]:
    """
    Validate registry files against their schemas

    Args:
        target: What to validate - 'all', 'equations', 'stages', 'tasks', 'experiments'

    Returns:
        Dict mapping category to list of validation errors
    """
    results = {}

    if target in ("all", "equations"):
        results["equations"] = []
        registry = load_math_registry()
        equations = registry.get("equations", {})
        for eq_id, eq in equations.items():
            errors = validate_equation(eq, eq_id)
            results["equations"].extend(errors)

    if target in ("all", "stages"):
        results["stages"] = []
        data = load_pipeline_stages()
        stages = data.get("stages", [])
        for stage in stages:
            stage_id = stage.get("id", "unknown")
            errors = validate_pipeline_stage(stage, stage_id)
            results["stages"].extend(errors)

    if target in ("all", "experiments"):
        results["experiments"] = []
        # Validate experiments in user registry
        registry = load_registry()
        schema = load_schema("experiment")
        if schema and HAS_JSONSCHEMA:
            for exp in registry.experiments:
                try:
                    exp_dict = asdict(exp)
                    jsonschema.validate(exp_dict, schema)
                except jsonschema.ValidationError as e:
                    results["experiments"].append(f"{exp.id}: {e.message}")

    return results


def cmd_validate(args):
    """Validate registry files against JSON schemas"""
    if not HAS_JSONSCHEMA:
        print("Error: jsonschema required. Install with: pip install jsonschema")
        return 1

    if not HAS_YAML:
        print("Error: PyYAML required. Install with: pip install pyyaml")
        return 1

    target = getattr(args, 'target', 'all')
    verbose = getattr(args, 'verbose', False)

    print(f"Validating registry: {target}")
    print("=" * 50)

    results = validate_registry(target)

    total_errors = 0
    for category, errors in results.items():
        if errors:
            print(f"\n{category}: {len(errors)} errors")
            for error in errors:
                print(f"  - {error}")
            total_errors += len(errors)
        else:
            print(f"{category}: OK")

    print("=" * 50)
    if total_errors == 0:
        print("All validations passed")
        return 0
    else:
        print(f"Total errors: {total_errors}")
        return 1


def cmd_math(args):
    """Query the math equations registry"""
    if not HAS_YAML:
        print("Error: PyYAML required for math registry. Install with: pip install pyyaml")
        return 1

    registry = load_math_registry()
    equations = registry.get("equations", {})

    if args.math_command == "list":
        # List all equations
        if not equations:
            print("No equations in registry")
            return 0

        print(f"{'ID':<10} {'Title':<45} {'Chapter':<8} {'Type':<12}")
        print("-" * 80)

        for eq_id, eq in sorted(equations.items()):
            title = eq.get("title", "")[:44]
            chapter = eq.get("chapter", "")
            eq_type = eq.get("type", "")
            print(f"{eq_id:<10} {title:<45} {chapter:<8} {eq_type:<12}")

        print(f"\nTotal: {len(equations)} equations")
        return 0

    elif args.math_command == "get":
        eq_id = args.equation_id
        if eq_id not in equations:
            print(f"Error: Equation '{eq_id}' not found")
            print(f"Available: {', '.join(sorted(equations.keys())[:10])}...")
            return 1

        eq = equations[eq_id]

        if args.json:
            print(json.dumps(eq, indent=2, default=str))
        else:
            print(f"Equation {eq_id}: {eq.get('title', 'Untitled')}")
            print("=" * 60)
            print(f"Chapter: {eq.get('chapter', 'N/A')}")
            print(f"Type: {eq.get('type', 'N/A')}")
            print(f"Category: {eq.get('category', 'N/A')}")
            print(f"\nLaTeX: {eq.get('latex', 'N/A')}")
            if eq.get('description'):
                print(f"\nDescription:\n{eq.get('description')}")
            if eq.get('variables'):
                print(f"\nVariables: {', '.join(eq.get('variables', []))}")
            if eq.get('related_equations'):
                print(f"Related: {', '.join(eq.get('related_equations', []))}")

        return 0

    elif args.math_command == "latex":
        eq_id = args.equation_id
        if eq_id not in equations:
            print(f"Error: Equation '{eq_id}' not found")
            return 1

        eq = equations[eq_id]
        if args.full:
            print(eq.get("latex_full", eq.get("latex", "")))
        else:
            print(eq.get("latex", ""))
        return 0

    elif args.math_command == "search":
        query = args.query.lower()
        matches = []

        for eq_id, eq in equations.items():
            searchable = f"{eq_id} {eq.get('title', '')} {eq.get('description', '')} {' '.join(eq.get('tags', []))}".lower()
            if query in searchable:
                matches.append((eq_id, eq))

        if not matches:
            print(f"No equations matching '{args.query}'")
            return 0

        print(f"Found {len(matches)} equations matching '{args.query}':")
        print(f"{'ID':<10} {'Title':<50}")
        print("-" * 65)
        for eq_id, eq in matches[:20]:
            print(f"{eq_id:<10} {eq.get('title', '')[:49]:<50}")

        if len(matches) > 20:
            print(f"... and {len(matches) - 20} more")

        return 0

    elif args.math_command == "variables":
        var_registry = load_variables_registry()
        variables = var_registry.get("variables", {})

        if args.variable_id:
            var_id = args.variable_id
            if var_id not in variables:
                print(f"Error: Variable '{var_id}' not found")
                return 1

            var = variables[var_id]
            if args.json:
                print(json.dumps(var, indent=2, default=str))
            else:
                print(f"Variable: {var.get('symbol_display', var_id)} ({var.get('name', 'Untitled')})")
                print("=" * 60)
                print(f"Symbol (LaTeX): {var.get('symbol', 'N/A')}")
                print(f"Domain: {var.get('domain', 'N/A')}")
                print(f"Units: {var.get('units', 'N/A')}")
                print(f"Typical Range: {var.get('typical_range', 'N/A')}")
                if var.get('description'):
                    print(f"\nDescription:\n{var.get('description')}")
        else:
            # List all variables
            print(f"{'Symbol':<12} {'Name':<30} {'Domain':<15}")
            print("-" * 60)
            for var_id, var in sorted(variables.items()):
                symbol = var.get('symbol_display', var_id)[:11]
                name = var.get('name', '')[:29]
                domain = var.get('domain', '')[:14]
                print(f"{symbol:<12} {name:<30} {domain:<15}")
            print(f"\nTotal: {len(variables)} variables")

        return 0

    return 0


def cmd_stages(args):
    """List pipeline stages"""
    if not HAS_YAML:
        print("Error: PyYAML required. Install with: pip install pyyaml")
        return 1

    data = load_pipeline_stages()
    stages = data.get("stages", [])

    if not stages:
        print("No pipeline stages found in registry")
        return 1

    if args.json:
        print(json.dumps(stages, indent=2))
        return 0

    print("SMS Pipeline Stages")
    print("=" * 80)
    print(f"{'Symbol':<6} {'Name':<30} {'Probability Term':<20} {'Team':<15}")
    print("-" * 80)

    for stage in stages:
        symbol = stage.get("symbol", "?")
        name = stage.get("name", "")[:29]
        prob = stage.get("probability_term", "")[:19]
        team = stage.get("primary_team", "")[:14]
        print(f"{symbol:<6} {name:<30} {prob:<20} {team:<15}")

    print(f"\nTotal: {len(stages)} stages")
    print("\nUse 'ont_experiments.py stage <symbol>' for details")
    return 0


def cmd_stage(args):
    """Show details of a specific pipeline stage"""
    if not HAS_YAML:
        print("Error: PyYAML required. Install with: pip install pyyaml")
        return 1

    data = load_pipeline_stages()
    stages = {s.get("stage_id") or s.get("symbol"): s for s in data.get("stages", [])}

    stage_id = args.stage_id
    if stage_id not in stages:
        print(f"Error: Stage '{stage_id}' not found")
        print(f"Available: {', '.join(sorted(stages.keys()))}")
        return 1

    stage = stages[stage_id]

    if args.json:
        print(json.dumps(stage, indent=2))
        return 0

    print(f"Stage {stage.get('symbol', stage_id)}: {stage.get('name', 'Untitled')}")
    print("=" * 60)
    print(f"Probability Term: {stage.get('probability_term', 'N/A')}")
    print(f"Primary Team: {stage.get('primary_team', 'N/A')}")
    print(f"Dependencies: {', '.join(stage.get('dependencies', [])) or 'None'}")

    if stage.get('description'):
        print(f"\nDescription:\n{stage.get('description')}")

    if stage.get('outputs'):
        print(f"\nOutputs:")
        for output in stage.get('outputs', []):
            print(f"  - {output}")

    if stage.get('key_methods'):
        print(f"\nKey Methods:")
        for method in stage.get('key_methods', []):
            print(f"  - {method}")

    return 0


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='ONT Experiments v2 - Event-Sourced Nanopore Registry',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # init
    p_init = subparsers.add_parser('init', help='Initialize registry')
    p_init.add_argument('--git', action='store_true', help='Initialize git repository')
    
    # discover
    p_discover = subparsers.add_parser('discover', help='Discover experiments')
    p_discover.add_argument('directory', help='Directory to scan')
    p_discover.add_argument('--register', '-r', action='store_true', help='Register discovered')
    p_discover.add_argument('--no-recursive', action='store_true', help='Do not recurse')
    p_discover.add_argument('--analyze', '-a', action='store_true',
                            help='Run quick analysis after discovery')
    p_discover.add_argument('--interactive', '-i', action='store_true',
                            help='Interactive menu after analysis (implies --analyze)')
    p_discover.add_argument('--output', '-o', type=str, default=None,
                            help='Output directory for reports (default: .ont-discovery in scanned dir)')
    p_discover.add_argument('--no-compare', action='store_true',
                            help='Skip comparison across experiments')
    
    # register
    p_register = subparsers.add_parser('register', help='Register experiment')
    p_register.add_argument('directory', help='Experiment directory')
    p_register.add_argument('--name', help='Override name')
    p_register.add_argument('--tags', help='Comma-separated tags')
    p_register.add_argument('--status', help='Initial status')
    p_register.add_argument('--force', '-f', action='store_true', help='Update if exists')
    
    # list
    p_list = subparsers.add_parser('list', help='List experiments')
    p_list.add_argument('--status', help='Filter by status')
    p_list.add_argument('--tag', help='Filter by tag')
    p_list.add_argument('--source', help='Filter by source')
    p_list.add_argument('--github', '-g', action='store_true', 
                        help='Fetch from GitHub instead of local registry')
    
    # info
    p_info = subparsers.add_parser('info', help='Show details')
    p_info.add_argument('experiment_id', help='Experiment ID')
    p_info.add_argument('--github', '-g', action='store_true',
                        help='Fetch from GitHub instead of local registry')
    p_info.add_argument('--json', action='store_true', help='Output JSON')
    
    # run
    p_run = subparsers.add_parser('run', help='Run analysis with logging')
    p_run.add_argument('analysis', help='Analysis type (end_reasons, basecalling, ...)')
    p_run.add_argument('experiment_id', help='Experiment ID')
    p_run.add_argument('args', nargs='*', help='Arguments to pass to analysis')
    
    # history
    p_history = subparsers.add_parser('history', help='Show event history')
    p_history.add_argument('experiment_id', help='Experiment ID')
    p_history.add_argument('--verbose', '-v', action='store_true', help='Show full details')
    
    # export
    p_export = subparsers.add_parser('export', help='Export commands')
    p_export.add_argument('experiment_id', help='Experiment ID')
    
    # replay
    p_replay = subparsers.add_parser('replay', help='Replay event')
    p_replay.add_argument('experiment_id', help='Experiment ID')
    p_replay.add_argument('--event', '-e', type=int, required=True, help='Event number')
    p_replay.add_argument('--dry-run', action='store_true', help='Show without executing')
    
    # tag
    p_tag = subparsers.add_parser('tag', help='Manage tags')
    p_tag.add_argument('experiment_id', help='Experiment ID')
    p_tag.add_argument('--add', help='Tags to add')
    p_tag.add_argument('--remove', help='Tags to remove')
    
    # status
    p_status = subparsers.add_parser('status', help='Update status')
    p_status.add_argument('experiment_id', help='Experiment ID')
    p_status.add_argument('status', help='New status')
    
    # public
    p_public = subparsers.add_parser('public', help='List public datasets')
    p_public.add_argument('dataset_id', nargs='?', help='Dataset ID for details')
    p_public.add_argument('--url', action='store_true', help='Show URLs')
    
    # fetch
    p_fetch = subparsers.add_parser('fetch', help='Fetch public dataset')
    p_fetch.add_argument('dataset_id', help='Dataset ID')
    p_fetch.add_argument('destination', help='Destination directory')
    p_fetch.add_argument('--dry-run', action='store_true', help='Show what would download')
    p_fetch.add_argument('--register', '-r', action='store_true', help='Register after download')
    
    # remove
    p_remove = subparsers.add_parser('remove', help='Remove from registry')
    p_remove.add_argument('experiment_id', help='Experiment ID')

    # ==========================================================================
    # Domain Memory Commands
    # ==========================================================================

    # tasks - View task backlog (v2.0 with dependencies)
    p_tasks = subparsers.add_parser('tasks', help='View experiment task backlog')
    p_tasks.add_argument('experiment_id', help='Experiment ID')
    p_tasks.add_argument('--verbose', '-v', action='store_true', help='Show detailed task info')

    # progress - View progress log
    p_progress = subparsers.add_parser('progress', help='View experiment progress log')
    p_progress.add_argument('experiment_id', help='Experiment ID')

    # init-tasks - Initialize domain memory
    p_init_tasks = subparsers.add_parser('init-tasks', help='Initialize domain memory for experiment')
    p_init_tasks.add_argument('experiment_id', help='Experiment ID')
    p_init_tasks.add_argument('--force', '-f', action='store_true', help='Reinitialize if exists')
    p_init_tasks.add_argument('--claude-md', action='store_true', help='Create experiment CLAUDE.md')

    # next - Get next recommended task
    p_next = subparsers.add_parser('next', help='Get next recommended task (agent-friendly)')
    p_next.add_argument('experiment_id', help='Experiment ID')
    p_next.add_argument('--json', action='store_true', help='Output JSON for machine parsing')

    # ==========================================================================
    # Math Registry Commands
    # ==========================================================================

    p_math = subparsers.add_parser('math', help='Query math equations registry')
    math_sub = p_math.add_subparsers(dest='math_command', help='Math subcommands')

    # math list
    math_sub.add_parser('list', help='List all equations')

    # math get
    p_math_get = math_sub.add_parser('get', help='Get equation details')
    p_math_get.add_argument('equation_id', help='Equation ID (e.g., 5.1, 6.6)')
    p_math_get.add_argument('--json', action='store_true', help='Output JSON')

    # math latex
    p_math_latex = math_sub.add_parser('latex', help='Get equation LaTeX')
    p_math_latex.add_argument('equation_id', help='Equation ID')
    p_math_latex.add_argument('--full', action='store_true', help='Include full equation environment')

    # math search
    p_math_search = math_sub.add_parser('search', help='Search equations')
    p_math_search.add_argument('query', help='Search query')

    # math variables
    p_math_vars = math_sub.add_parser('variables', help='List or get variable details')
    p_math_vars.add_argument('variable_id', nargs='?', help='Variable ID (optional)')
    p_math_vars.add_argument('--json', action='store_true', help='Output JSON')

    # ==========================================================================
    # Pipeline Stage Commands
    # ==========================================================================

    # stages - List all pipeline stages
    p_stages = subparsers.add_parser('stages', help='List SMS pipeline stages')
    p_stages.add_argument('--json', action='store_true', help='Output JSON')

    # stage - Get stage details
    p_stage = subparsers.add_parser('stage', help='Get pipeline stage details')
    p_stage.add_argument('stage_id', help='Stage symbol (h, g, u, d, l, σ, r, C, A)')
    p_stage.add_argument('--json', action='store_true', help='Output JSON')

    # validate - Validate registry files against schemas
    p_validate = subparsers.add_parser('validate', help='Validate registry against schemas')
    p_validate.add_argument('target', nargs='?', default='all',
                            choices=['all', 'equations', 'stages', 'experiments', 'tasks'],
                            help='What to validate (default: all)')
    p_validate.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    commands = {
        'init': cmd_init,
        'discover': cmd_discover,
        'register': cmd_register,
        'list': cmd_list,
        'info': cmd_info,
        'run': cmd_run,
        'history': cmd_history,
        'export': cmd_export,
        'replay': cmd_replay,
        'tag': cmd_tag,
        'status': cmd_status,
        'public': cmd_public,
        'fetch': cmd_fetch,
        'remove': cmd_remove,
        # Domain Memory commands
        'tasks': cmd_tasks,
        'progress': cmd_progress,
        'init-tasks': cmd_init_tasks,
        'next': cmd_next,
        # Math Registry commands
        'math': cmd_math,
        # Pipeline Stage commands
        'stages': cmd_stages,
        'stage': cmd_stage,
        # Validation commands
        'validate': cmd_validate,
    }

    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
