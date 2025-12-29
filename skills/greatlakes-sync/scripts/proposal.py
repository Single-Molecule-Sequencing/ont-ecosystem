#!/usr/bin/env python3
"""
proposal.py - Proposal generation and management for Great Lakes sync

Handles:
- Proposal YAML format creation and parsing
- Experiment comparison (new/updated/removed/unchanged)
- Change detection using content hashing
- Proposal approval workflow

Part of: https://github.com/Single-Molecule-Sequencing/ont-ecosystem
"""

import hashlib
import os
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@dataclass
class ExperimentChange:
    """Represents a change to an experiment."""
    field: str
    old_value: Any
    new_value: Any


@dataclass
class ExperimentEntry:
    """Represents a discovered experiment."""
    id: str
    path: str
    sample_id: str = ""
    flow_cell_id: str = ""
    protocol_group_id: str = ""
    protocol: str = ""
    instrument: str = ""
    started: str = ""
    acquisition_stopped: str = ""
    metadata_source: str = "final_summary"
    pod5_files: int = 0
    fast5_files: int = 0
    fastq_files: int = 0
    bam_files: int = 0
    discovered_at: str = ""
    changes: List[ExperimentChange] = field(default_factory=list)
    removal_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        d = asdict(self)
        if not self.changes:
            del d['changes']
        if not self.removal_reason:
            del d['removal_reason']
        return d

    def compute_hash(self) -> str:
        """Compute content hash for change detection."""
        components = [
            self.path,
            str(self.pod5_files),
            str(self.fast5_files),
            str(self.fastq_files),
            str(self.bam_files),
            self.sample_id or "",
            self.flow_cell_id or "",
        ]
        return hashlib.sha256("|".join(components).encode()).hexdigest()[:16]


@dataclass
class ProposalSummary:
    """Summary statistics for a proposal."""
    total_discovered: int = 0
    current_in_registry: int = 0
    new_count: int = 0
    updated_count: int = 0
    removed_count: int = 0
    unchanged_count: int = 0

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


@dataclass
class Proposal:
    """
    Represents a discovery proposal with changes to be reviewed and applied.

    Attributes:
        version: Proposal format version
        generated_at: ISO timestamp of generation
        slurm_job_id: SLURM job ID that generated this proposal
        slurm_node: Node where discovery ran
        scan_duration_seconds: How long the scan took
        scan_paths: Directories that were scanned
        summary: Statistics about changes
        new: List of new experiments
        updated: List of updated experiments
        removed: List of removed experiments
        unchanged: List of unchanged experiments
        approval_status: pending | approved | rejected | partial
        approved_at: ISO timestamp of approval
        approved_by: Username who approved
        applied_at: ISO timestamp of application
    """
    version: str = "1.0"
    generated_at: str = ""
    slurm_job_id: str = ""
    slurm_node: str = ""
    scan_duration_seconds: float = 0.0
    scan_paths: List[str] = field(default_factory=list)
    summary: ProposalSummary = field(default_factory=ProposalSummary)
    new: List[ExperimentEntry] = field(default_factory=list)
    updated: List[ExperimentEntry] = field(default_factory=list)
    removed: List[ExperimentEntry] = field(default_factory=list)
    unchanged: List[ExperimentEntry] = field(default_factory=list)
    approval_status: str = "pending"
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
    applied_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        return {
            'version': self.version,
            'generated_at': self.generated_at,
            'slurm_job_id': self.slurm_job_id,
            'slurm_node': self.slurm_node,
            'scan_duration_seconds': self.scan_duration_seconds,
            'scan_paths': self.scan_paths,
            'summary': self.summary.to_dict(),
            'changes': {
                'new': [e.to_dict() for e in self.new],
                'updated': [e.to_dict() for e in self.updated],
                'removed': [e.to_dict() for e in self.removed],
            },
            'unchanged_count': len(self.unchanged),
            'approval_status': self.approval_status,
            'approved_at': self.approved_at,
            'approved_by': self.approved_by,
            'applied_at': self.applied_at,
        }

    def save(self, path: Path) -> None:
        """Save proposal to YAML file."""
        if not HAS_YAML:
            raise RuntimeError("PyYAML is required for saving proposals")

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)

    @classmethod
    def load(cls, path: Path) -> 'Proposal':
        """Load proposal from YAML file."""
        if not HAS_YAML:
            raise RuntimeError("PyYAML is required for loading proposals")

        with open(path, 'r') as f:
            data = yaml.safe_load(f)

        proposal = cls(
            version=data.get('version', '1.0'),
            generated_at=data.get('generated_at', ''),
            slurm_job_id=data.get('slurm_job_id', ''),
            slurm_node=data.get('slurm_node', ''),
            scan_duration_seconds=data.get('scan_duration_seconds', 0.0),
            scan_paths=data.get('scan_paths', []),
            approval_status=data.get('approval_status', 'pending'),
            approved_at=data.get('approved_at'),
            approved_by=data.get('approved_by'),
            applied_at=data.get('applied_at'),
        )

        # Parse summary
        summary_data = data.get('summary', {})
        proposal.summary = ProposalSummary(
            total_discovered=summary_data.get('total_discovered', 0),
            current_in_registry=summary_data.get('current_in_registry', 0),
            new_count=summary_data.get('new_count', 0),
            updated_count=summary_data.get('updated_count', 0),
            removed_count=summary_data.get('removed_count', 0),
            unchanged_count=summary_data.get('unchanged_count', 0),
        )

        # Parse changes
        changes = data.get('changes', {})
        for exp_data in changes.get('new', []):
            proposal.new.append(_parse_experiment_entry(exp_data))
        for exp_data in changes.get('updated', []):
            proposal.updated.append(_parse_experiment_entry(exp_data))
        for exp_data in changes.get('removed', []):
            proposal.removed.append(_parse_experiment_entry(exp_data))

        return proposal

    def approve(self, username: Optional[str] = None) -> None:
        """Mark proposal as approved."""
        self.approval_status = "approved"
        self.approved_at = datetime.now(timezone.utc).isoformat()
        self.approved_by = username or os.environ.get('USER', 'unknown')

    def mark_applied(self) -> None:
        """Mark proposal as applied."""
        self.applied_at = datetime.now(timezone.utc).isoformat()


def _parse_experiment_entry(data: Dict[str, Any]) -> ExperimentEntry:
    """Parse experiment entry from dictionary."""
    changes = []
    for change_data in data.get('changes', []):
        changes.append(ExperimentChange(
            field=change_data.get('field', ''),
            old_value=change_data.get('old_value'),
            new_value=change_data.get('new_value'),
        ))

    return ExperimentEntry(
        id=data.get('id', ''),
        path=data.get('path', ''),
        sample_id=data.get('sample_id', ''),
        flow_cell_id=data.get('flow_cell_id', ''),
        protocol_group_id=data.get('protocol_group_id', ''),
        protocol=data.get('protocol', ''),
        instrument=data.get('instrument', ''),
        started=data.get('started', ''),
        acquisition_stopped=data.get('acquisition_stopped', ''),
        metadata_source=data.get('metadata_source', 'final_summary'),
        pod5_files=data.get('pod5_files', 0),
        fast5_files=data.get('fast5_files', 0),
        fastq_files=data.get('fastq_files', 0),
        bam_files=data.get('bam_files', 0),
        discovered_at=data.get('discovered_at', ''),
        changes=changes,
        removal_reason=data.get('removal_reason', ''),
    )


def load_database_experiments(db_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Load current experiments from SQLite database.

    Returns:
        Dict mapping experiment path to metadata
    """
    if not os.path.exists(db_path):
        return {}

    experiments = {}
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT experiment_path, sample_id, flow_cell_id, protocol_group_id,
                   started, pod5_files, fastq_files, bam_files, instrument
            FROM experiments
        """)

        for row in cursor.fetchall():
            experiments[row[0]] = {
                'path': row[0],
                'sample_id': row[1] or '',
                'flow_cell_id': row[2] or '',
                'protocol_group_id': row[3] or '',
                'started': row[4] or '',
                'pod5_files': row[5] or 0,
                'fastq_files': row[6] or 0,
                'bam_files': row[7] or 0,
                'instrument': row[8] or '',
            }
    except sqlite3.OperationalError:
        pass

    conn.close()
    return experiments


def load_registry_experiments(registry_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Load current experiments from YAML registry.

    Returns:
        Dict mapping experiment path/id to metadata
    """
    if not os.path.exists(registry_path):
        return {}

    if not HAS_YAML:
        return {}

    experiments = {}

    with open(registry_path, 'r') as f:
        registry = yaml.safe_load(f) or {}

    for exp in registry.get('experiments', []):
        path = exp.get('location') or exp.get('path', '')
        if path:
            experiments[path] = exp

    return experiments


def compare_experiments(
    discovered: List[Dict[str, Any]],
    current_db: Dict[str, Dict[str, Any]],
    current_registry: Optional[Dict[str, Dict[str, Any]]] = None
) -> Proposal:
    """
    Compare discovered experiments against current database and registry.

    Args:
        discovered: List of discovered experiment dicts
        current_db: Current database experiments (path -> metadata)
        current_registry: Current registry experiments (path -> metadata)

    Returns:
        Proposal with categorized changes
    """
    current_registry = current_registry or {}

    # Merge database and registry for comprehensive comparison
    current_all: Dict[str, Dict[str, Any]] = {}
    current_all.update(current_db)
    for path, exp in current_registry.items():
        if path not in current_all:
            current_all[path] = exp

    seen_paths: Set[str] = set()
    proposal = Proposal(
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    # Categorize discovered experiments
    for exp_dict in discovered:
        path = exp_dict.get('path', '')
        seen_paths.add(path)

        exp = ExperimentEntry(
            id=exp_dict.get('id', ''),
            path=path,
            sample_id=exp_dict.get('sample_id', ''),
            flow_cell_id=exp_dict.get('flow_cell_id', ''),
            protocol_group_id=exp_dict.get('protocol_group_id', ''),
            protocol=exp_dict.get('protocol', ''),
            instrument=exp_dict.get('instrument', ''),
            started=exp_dict.get('started', ''),
            acquisition_stopped=exp_dict.get('acquisition_stopped', ''),
            metadata_source=exp_dict.get('metadata_source', 'final_summary'),
            pod5_files=exp_dict.get('pod5_files', 0),
            fast5_files=exp_dict.get('fast5_files', 0),
            fastq_files=exp_dict.get('fastq_files', 0),
            bam_files=exp_dict.get('bam_files', 0),
            discovered_at=exp_dict.get('discovered_at', ''),
        )

        if path not in current_all:
            # New experiment
            proposal.new.append(exp)
        else:
            # Check for changes
            current = current_all[path]
            changes = _detect_changes(exp, current)

            if changes:
                exp.changes = changes
                proposal.updated.append(exp)
            else:
                proposal.unchanged.append(exp)

    # Find removed experiments (in database but not discovered)
    for path, current in current_all.items():
        if path not in seen_paths:
            # Check if directory still exists
            if not os.path.isdir(path):
                exp = ExperimentEntry(
                    id=current.get('id', ''),
                    path=path,
                    sample_id=current.get('sample_id', ''),
                    flow_cell_id=current.get('flow_cell_id', ''),
                    removal_reason='directory_not_found',
                )
                proposal.removed.append(exp)

    # Update summary
    proposal.summary = ProposalSummary(
        total_discovered=len(discovered),
        current_in_registry=len(current_all),
        new_count=len(proposal.new),
        updated_count=len(proposal.updated),
        removed_count=len(proposal.removed),
        unchanged_count=len(proposal.unchanged),
    )

    return proposal


def _detect_changes(
    discovered: ExperimentEntry,
    current: Dict[str, Any]
) -> List[ExperimentChange]:
    """Detect changes between discovered and current experiment."""
    changes = []

    # Fields to compare
    compare_fields = [
        ('pod5_files', 'pod5_files'),
        ('fast5_files', 'fast5_files'),
        ('fastq_files', 'fastq_files'),
        ('bam_files', 'bam_files'),
    ]

    for disc_field, curr_field in compare_fields:
        disc_val = getattr(discovered, disc_field, 0) or 0
        curr_val = current.get(curr_field, 0) or 0

        if disc_val != curr_val:
            changes.append(ExperimentChange(
                field=disc_field,
                old_value=curr_val,
                new_value=disc_val,
            ))

    return changes


def format_proposal_report(proposal: Proposal) -> str:
    """Format proposal as a readable text report."""
    lines = []
    lines.append("=" * 70)
    lines.append("EXPERIMENT DISCOVERY PROPOSAL")
    lines.append("=" * 70)
    lines.append(f"Generated: {proposal.generated_at}")
    if proposal.slurm_job_id:
        lines.append(f"SLURM Job: {proposal.slurm_job_id}")
    if proposal.scan_duration_seconds:
        lines.append(f"Scan Duration: {proposal.scan_duration_seconds:.1f}s")
    lines.append("")

    # Summary
    s = proposal.summary
    lines.append("SUMMARY")
    lines.append("-" * 40)
    lines.append(f"  Total discovered:    {s.total_discovered}")
    lines.append(f"  Currently in DB:     {s.current_in_registry}")
    lines.append(f"  New experiments:     {s.new_count}")
    lines.append(f"  Updated:             {s.updated_count}")
    lines.append(f"  Removed:             {s.removed_count}")
    lines.append(f"  Unchanged:           {s.unchanged_count}")
    lines.append("")

    # New experiments
    if proposal.new:
        lines.append("NEW EXPERIMENTS")
        lines.append("-" * 40)
        for exp in proposal.new:
            lines.append(f"  + {exp.sample_id or 'unknown'} [{exp.metadata_source}]")
            lines.append(f"    Path: {exp.path}")
            lines.append(f"    Flow Cell: {exp.flow_cell_id}")
            lines.append(f"    Files: POD5={exp.pod5_files}, Fast5={exp.fast5_files}, "
                        f"FASTQ={exp.fastq_files}, BAM={exp.bam_files}")
            lines.append("")

    # Updated experiments
    if proposal.updated:
        lines.append("UPDATED EXPERIMENTS")
        lines.append("-" * 40)
        for exp in proposal.updated:
            lines.append(f"  ~ {exp.sample_id or 'unknown'}")
            lines.append(f"    Path: {exp.path}")
            for change in exp.changes:
                lines.append(f"    {change.field}: {change.old_value} -> {change.new_value}")
            lines.append("")

    # Removed experiments
    if proposal.removed:
        lines.append("REMOVED EXPERIMENTS")
        lines.append("-" * 40)
        for exp in proposal.removed:
            lines.append(f"  - {exp.sample_id or 'unknown'}")
            lines.append(f"    Path: {exp.path}")
            lines.append(f"    Reason: {exp.removal_reason}")
            lines.append("")

    # Approval status
    lines.append("STATUS")
    lines.append("-" * 40)
    lines.append(f"  Approval: {proposal.approval_status}")
    if proposal.approved_at:
        lines.append(f"  Approved: {proposal.approved_at} by {proposal.approved_by}")
    if proposal.applied_at:
        lines.append(f"  Applied: {proposal.applied_at}")

    return "\n".join(lines)


def get_latest_proposal(proposals_dir: Path) -> Optional[Path]:
    """Find the most recent proposal file."""
    if not proposals_dir.exists():
        return None

    proposals = sorted(proposals_dir.glob("proposal_*.yaml"), reverse=True)
    return proposals[0] if proposals else None


def generate_proposal_filename() -> str:
    """Generate timestamped proposal filename."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"proposal_{ts}.yaml"
