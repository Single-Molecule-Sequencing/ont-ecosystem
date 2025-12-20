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


# =============================================================================
# Configuration
# =============================================================================

REGISTRY_DIR = Path.home() / ".ont-registry"
REGISTRY_FILE = REGISTRY_DIR / "experiments.yaml"
REGISTRY_VERSION = "2.0"

# Analysis skill configurations
ANALYSIS_SKILLS = {
    "end_reasons": {
        "script": "end_reason.py",
        "description": "Read end reason QC analysis",
        "result_fields": ["total_reads", "quality_status", "signal_positive_pct", 
                         "unblock_mux_pct", "data_service_pct"],
        "input_mode": "location",  # Pass experiment location as first arg
    },
    "basecalling": {
        "script": "dorado_basecall.py",
        "description": "Dorado basecalling",
        "result_fields": ["total_reads", "pass_reads", "mean_qscore", "median_qscore",
                         "bases_called", "n50", "model", "model_path", "model_tier",
                         "model_version", "chemistry", "batch_size"],
        "input_mode": "location",  # Pass experiment location as first arg
        "capture_model_path": True,  # Capture model path in event
    },
    "alignment": {
        "script": "minimap2",
        "description": "Minimap2 alignment",
        "result_fields": ["mapped_reads", "mapping_rate", "mean_coverage"],
        "input_mode": "explicit",  # Requires explicit input/output args
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

def load_registry() -> Registry:
    """Load registry from file"""
    if not REGISTRY_FILE.exists():
        return Registry()
    
    with open(REGISTRY_FILE, 'r') as f:
        if HAS_YAML:
            data = yaml.safe_load(f) or {}
        else:
            data = json.load(f)
    
    return Registry.from_dict(data)


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


def discover_experiment(path: Path) -> Optional[ExperimentMetadata]:
    """Discover and extract metadata from an experiment directory"""
    path = path.resolve()
    
    if not path.exists():
        return None
    
    # Find data files
    pod5_files = list(path.rglob('*.pod5'))
    fast5_files = list(path.rglob('*.fast5'))
    bam_files = list(path.rglob('*.bam'))
    
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
    
    # Try final_summary.txt first
    final_summary = path / 'final_summary.txt'
    if not final_summary.exists():
        final_summary = list(path.rglob('final_summary*.txt'))
        final_summary = final_summary[0] if final_summary else None
    
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
        for subdir in root.iterdir():
            if subdir.is_dir() and not subdir.name.startswith('.'):
                exp = discover_experiment(subdir)
                if exp:
                    experiments.append(exp)
    
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
    
    # Build command based on input mode
    if input_mode == 'location':
        # Pass experiment location as first argument
        cmd = ['python3', script, experiment.location] + args
    else:
        # Explicit mode - args must include input/output
        cmd = ['python3', script] + args
    
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
    
    # Header
    print(f"\n  {'ID':<16} {'Name':<30} {'Status':<12} {'Format':<6} {'Size':<8} {'Events'}")
    print(f"  {'─' * 16} {'─' * 30} {'─' * 12} {'─' * 6} {'─' * 8} {'─' * 6}")
    
    for exp in experiments:
        name = exp.name[:28] + '..' if len(exp.name) > 30 else exp.name
        size = f"{exp.total_size_gb:.1f}GB" if exp.total_size_gb else "?"
        events = len(exp.events)
        
        print(f"  {exp.id:<16} {name:<30} {exp.status:<12} {exp.data_format or '?':<6} {size:<8} {events}")


def print_experiment_detail(exp: ExperimentMetadata):
    """Print detailed experiment info"""
    print(f"\n  {'═' * 60}")
    print(f"  Experiment: {exp.id}")
    print(f"  {'═' * 60}")
    
    print(f"\n  Name:       {exp.name}")
    print(f"  Location:   {exp.location}")
    print(f"  Status:     {exp.status}")
    print(f"  Source:     {exp.source}")
    
    if exp.tags:
        print(f"  Tags:       {', '.join(exp.tags)}")
    
    print(f"\n  Platform")
    print(f"  {'─' * 40}")
    if exp.platform:
        print(f"  Device:     {exp.platform}")
    if exp.flowcell_type:
        print(f"  Flowcell:   {exp.flowcell_type} ({exp.flowcell_id or 'ID unknown'})")
    if exp.kit:
        print(f"  Kit:        {exp.kit}")
    if exp.chemistry:
        print(f"  Chemistry:  {exp.chemistry}")
    
    print(f"\n  Data")
    print(f"  {'─' * 40}")
    print(f"  Format:     {exp.data_format or 'unknown'}")
    print(f"  Files:      {exp.file_count}")
    print(f"  Size:       {exp.total_size_gb:.2f} GB")
    if exp.total_reads:
        print(f"  Reads:      {exp.total_reads:,}")
    if exp.total_bases:
        print(f"  Bases:      {exp.total_bases:,}")
    
    if exp.events:
        print(f"\n  Recent Events ({len(exp.events)} total)")
        print(f"  {'─' * 40}")
        for i, event in enumerate(exp.events[-5:], start=max(1, len(exp.events)-4)):
            ts = event.timestamp[:19].replace('T', ' ')
            if event.type == 'analysis':
                print(f"  [{i}] {ts} {event.type}: {event.analysis} ({event.exit_code})")
            else:
                print(f"  [{i}] {ts} {event.type}")


def print_event_history(exp: ExperimentMetadata, verbose: bool = False):
    """Print full event history"""
    print(f"\n  Event History: {exp.id}")
    print(f"  {'═' * 60}")
    
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
    """Discover experiments"""
    path = Path(args.directory).resolve()
    
    if not path.exists():
        print(f"Error: Path not found: {path}")
        return 1
    
    print(f"\n  Scanning: {path}")
    experiments = scan_directory(path, recursive=not args.no_recursive)
    
    print(f"  Found: {len(experiments)} experiments")
    
    if args.register and experiments:
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
    registry = load_registry()
    experiments = registry.experiments
    
    # Filter
    if args.status:
        experiments = [e for e in experiments if e.status == args.status]
    if args.tag:
        experiments = [e for e in experiments if args.tag in e.tags]
    if args.source:
        experiments = [e for e in experiments if e.source == args.source]
    
    print(f"\n  Registry: {REGISTRY_FILE}")
    print(f"  Total: {len(registry.experiments)} experiments")
    
    if args.status or args.tag or args.source:
        print(f"  Filtered: {len(experiments)}")
    
    print_experiment_table(experiments)
    print()
    
    return 0


def cmd_info(args):
    """Show experiment details"""
    registry = load_registry()
    
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
    print(f"  {'═' * 60}")
    
    # Group by category
    categories = defaultdict(list)
    for dataset_id, info in PUBLIC_DATASETS.items():
        categories[info.get('category', 'other')].append((dataset_id, info))
    
    for category, datasets in sorted(categories.items()):
        print(f"\n  {category.replace('_', ' ').title()}")
        print(f"  {'─' * 50}")
        
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
    
    # info
    p_info = subparsers.add_parser('info', help='Show details')
    p_info.add_argument('experiment_id', help='Experiment ID')
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
    }
    
    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
