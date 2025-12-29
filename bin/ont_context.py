#!/usr/bin/env python3
"""
ONT Experiment Context - Unified Experiment View

Provides a holistic view of an experiment across all system components:
- Registry metadata and events
- Database statistics
- Pipeline state and task dependencies
- Computed equations
- Generated figures and tables
- Related experiments

This module serves as the integration layer connecting experiments to:
- ont_experiments.py (registry)
- experiment_db.py (database)
- ont_manuscript.py (figure/table generation)
- textbook/ (equations and definitions - consolidated)

Part of: https://github.com/Single-Molecule-Sequencing/ont-ecosystem
"""

import os
import sys
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

# Optional imports
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import sqlite3
    HAS_SQLITE = True
except ImportError:
    HAS_SQLITE = False


# =============================================================================
# Configuration
# =============================================================================

REGISTRY_DIR = Path(os.environ.get("ONT_REGISTRY_DIR", Path.home() / ".ont-registry"))
MANUSCRIPT_DIR = Path(os.environ.get("ONT_MANUSCRIPT_DIR", Path.home() / ".ont-manuscript"))
ARTIFACTS_DIR = MANUSCRIPT_DIR / "artifacts"


# =============================================================================
# Data Classes - Core Types
# =============================================================================

@dataclass
class ExperimentMetadata:
    """Core experiment metadata from registry"""
    id: str
    name: str
    location: str
    platform: Optional[str] = None
    flowcell: Optional[str] = None
    kit: Optional[str] = None
    sample_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    status: str = "registered"
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Event:
    """Analysis event from registry"""
    event_id: str
    timestamp: str
    event_type: str
    analysis: Optional[str] = None
    results: Dict[str, Any] = field(default_factory=dict)
    hpc_metadata: Dict[str, Any] = field(default_factory=dict)
    exit_code: int = 0
    duration_seconds: float = 0.0


@dataclass
class Task:
    """Task from domain memory"""
    name: str
    status: str  # pending, in_progress, passing, failing, skipped
    pipeline_stage: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)
    priority: int = 0
    error_message: Optional[str] = None


@dataclass
class TaskList:
    """Domain memory task list"""
    tasks: List[Task] = field(default_factory=list)
    version: str = "2.0"

    @property
    def pending_tasks(self) -> List[Task]:
        return [t for t in self.tasks if t.status == "pending"]

    @property
    def failing_tasks(self) -> List[Task]:
        return [t for t in self.tasks if t.status == "failing"]

    @property
    def completed_tasks(self) -> List[Task]:
        return [t for t in self.tasks if t.status == "passing"]

    def get_next_runnable(self) -> Optional[Task]:
        """Get next task with satisfied dependencies"""
        completed_names = {t.name for t in self.completed_tasks}
        for task in self.pending_tasks:
            if all(dep in completed_names for dep in task.depends_on):
                return task
        return None


# =============================================================================
# Data Classes - Database Integration
# =============================================================================

@dataclass
class ReadStatistics:
    """Read statistics from database"""
    total_reads: int = 0
    total_bases: int = 0
    mean_length: float = 0.0
    n50: int = 0
    mean_qscore: float = 0.0
    median_qscore: float = 0.0
    pass_reads: int = 0
    fail_reads: int = 0


@dataclass
class EndReasonDistribution:
    """End reason distribution from database"""
    signal_positive: int = 0
    unblock_mux_change: int = 0
    data_service_unblock_mux_change: int = 0
    other: int = 0
    total: int = 0

    @property
    def signal_positive_pct(self) -> float:
        return (self.signal_positive / self.total * 100) if self.total > 0 else 0

    @property
    def unblock_pct(self) -> float:
        return (self.unblock_mux_change / self.total * 100) if self.total > 0 else 0


@dataclass
class DBExperiment:
    """Database record for experiment"""
    db_id: int
    experiment_path: str
    instrument: Optional[str] = None
    flow_cell_id: Optional[str] = None
    sample_id: Optional[str] = None
    protocol: Optional[str] = None
    started: Optional[str] = None


# =============================================================================
# Data Classes - Equation System
# =============================================================================

@dataclass
class Equation:
    """Mathematical equation from textbook registry"""
    id: str
    name: str
    latex: str
    description: str
    variables: List[str] = field(default_factory=list)
    python: Optional[str] = None  # Python implementation
    pipeline_stage: Optional[str] = None
    source: str = "textbook"


@dataclass
class EquationResult:
    """Result of equation computation"""
    equation_id: str
    inputs: Dict[str, Any]
    output: Any
    computed_at: str
    event_id: Optional[str] = None
    success: bool = True
    error: Optional[str] = None


# =============================================================================
# Data Classes - Manuscript Artifacts
# =============================================================================

@dataclass
class FigureArtifact:
    """Generated figure artifact"""
    id: str
    experiment_id: str
    version: int = 1
    path: str = ""
    format: str = "pdf"
    generator: str = ""
    created_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TableArtifact:
    """Generated table artifact"""
    id: str
    experiment_id: str
    version: int = 1
    path: str = ""
    format: str = "tex"
    generator: str = ""
    created_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Data Classes - Pipeline State
# =============================================================================

@dataclass
class PipelineExecution:
    """Pipeline execution record"""
    pipeline_name: str
    started_at: str
    completed_at: Optional[str] = None
    status: str = "running"
    steps_completed: List[str] = field(default_factory=list)
    current_step: Optional[str] = None
    results: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Main Context Class
# =============================================================================

@dataclass
class ExperimentContext:
    """
    Unified view of an experiment across all system components.

    This class aggregates data from:
    - Registry (metadata, events)
    - Database (statistics, end reasons)
    - Domain memory (tasks)
    - Equations (computed results)
    - Artifacts (figures, tables)
    """

    # Core metadata
    experiment: ExperimentMetadata
    tasks: TaskList = field(default_factory=TaskList)
    events: List[Event] = field(default_factory=list)

    # Database connection
    db_record: Optional[DBExperiment] = None
    statistics: Optional[ReadStatistics] = None
    end_reasons: Optional[EndReasonDistribution] = None

    # Pipeline state
    pipeline_executions: List[PipelineExecution] = field(default_factory=list)
    current_pipeline: Optional[str] = None

    # Equation bindings
    computed_equations: Dict[str, EquationResult] = field(default_factory=dict)
    applicable_equations: List[Equation] = field(default_factory=list)

    # Manuscript artifacts
    figures: List[FigureArtifact] = field(default_factory=list)
    tables: List[TableArtifact] = field(default_factory=list)

    # Cross-references
    related_experiments: List[str] = field(default_factory=list)
    public_dataset_source: Optional[str] = None

    @property
    def id(self) -> str:
        return self.experiment.id

    @property
    def name(self) -> str:
        return self.experiment.name

    @property
    def has_qc(self) -> bool:
        """Check if QC analysis has been run"""
        return any(e.analysis in ("end_reasons", "endreason_qc") for e in self.events)

    @property
    def has_basecalling(self) -> bool:
        """Check if basecalling has been run"""
        return any(e.analysis == "basecalling" for e in self.events)

    @property
    def quality_grade(self) -> Optional[str]:
        """Get quality grade from most recent QC event"""
        for event in reversed(self.events):
            if event.analysis in ("end_reasons", "endreason_qc"):
                return event.results.get("quality_grade") or event.results.get("quality_status")
        return None

    def get_latest_result(self, field: str) -> Optional[Any]:
        """Get most recent result value for a field"""
        for event in reversed(self.events):
            if field in event.results:
                return event.results[field]
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON/YAML serialization"""
        return {
            "experiment_id": self.experiment.id,
            "experiment_name": self.experiment.name,
            "location": self.experiment.location,
            "status": self.experiment.status,
            "tags": self.experiment.tags,
            "pending_tasks": [t.name for t in self.tasks.pending_tasks],
            "failing_tasks": [{"name": t.name, "error": t.error_message} for t in self.tasks.failing_tasks],
            "completed_tasks": [t.name for t in self.tasks.completed_tasks],
            "has_qc": self.has_qc,
            "has_basecalling": self.has_basecalling,
            "quality_grade": self.quality_grade,
            "statistics": asdict(self.statistics) if self.statistics else None,
            "end_reasons": asdict(self.end_reasons) if self.end_reasons else None,
            "figures_count": len(self.figures),
            "tables_count": len(self.tables),
            "related_experiments": self.related_experiments,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent)


# =============================================================================
# Context Loading Functions
# =============================================================================

def load_registry_experiment(exp_id: str) -> Optional[ExperimentMetadata]:
    """Load experiment metadata from registry"""
    if not HAS_YAML:
        return None

    registry_file = REGISTRY_DIR / "experiments.yaml"
    if not registry_file.exists():
        return None

    with open(registry_file) as f:
        registry = yaml.safe_load(f) or {}

    experiments = registry.get("experiments", {})
    if exp_id not in experiments:
        return None

    exp = experiments[exp_id]
    return ExperimentMetadata(
        id=exp_id,
        name=exp.get("name", exp_id),
        location=exp.get("location", ""),
        platform=exp.get("platform"),
        flowcell=exp.get("flowcell"),
        kit=exp.get("kit"),
        sample_id=exp.get("sample_id"),
        tags=exp.get("tags", []),
        status=exp.get("status", "registered"),
        created_at=exp.get("created_at", ""),
        updated_at=exp.get("updated_at", ""),
    )


def load_registry_events(exp_id: str) -> List[Event]:
    """Load events for experiment from registry"""
    if not HAS_YAML:
        return []

    events_file = REGISTRY_DIR / "events" / f"{exp_id}.yaml"
    if not events_file.exists():
        return []

    with open(events_file) as f:
        data = yaml.safe_load(f) or {}

    events = []
    for evt in data.get("events", []):
        events.append(Event(
            event_id=evt.get("event_id", ""),
            timestamp=evt.get("timestamp", ""),
            event_type=evt.get("event_type", ""),
            analysis=evt.get("analysis"),
            results=evt.get("results", {}),
            hpc_metadata=evt.get("hpc_metadata", {}),
            exit_code=evt.get("exit_code", 0),
            duration_seconds=evt.get("duration_seconds", 0.0),
        ))

    return events


def load_task_list(exp_id: str) -> TaskList:
    """Load domain memory tasks for experiment"""
    if not HAS_YAML:
        return TaskList()

    tasks_file = REGISTRY_DIR / "tasks" / f"{exp_id}.yaml"
    if not tasks_file.exists():
        return TaskList()

    with open(tasks_file) as f:
        data = yaml.safe_load(f) or {}

    tasks = []
    for t in data.get("tasks", []):
        tasks.append(Task(
            name=t.get("name", ""),
            status=t.get("status", "pending"),
            pipeline_stage=t.get("pipeline_stage"),
            depends_on=t.get("depends_on", []),
            priority=t.get("priority", 0),
            error_message=t.get("error_message"),
        ))

    return TaskList(tasks=tasks, version=data.get("version", "2.0"))


def load_db_experiment(exp_id: str, db_path: Optional[str] = None) -> Optional[DBExperiment]:
    """Load experiment from SQLite database"""
    if not HAS_SQLITE:
        return None

    if db_path is None:
        db_path = REGISTRY_DIR / "experiments.db"

    if not Path(db_path).exists():
        return None

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Try to find by experiment path containing the ID
        cursor.execute("""
            SELECT id, experiment_path, instrument, flow_cell_id, sample_id, protocol, started
            FROM experiments
            WHERE experiment_path LIKE ?
            LIMIT 1
        """, (f"%{exp_id}%",))

        row = cursor.fetchone()
        conn.close()

        if row:
            return DBExperiment(
                db_id=row[0],
                experiment_path=row[1],
                instrument=row[2],
                flow_cell_id=row[3],
                sample_id=row[4],
                protocol=row[5],
                started=row[6],
            )
    except Exception:
        pass

    return None


def load_artifacts(exp_id: str) -> tuple:
    """Load generated figures and tables for experiment"""
    figures = []
    tables = []

    exp_artifacts_dir = ARTIFACTS_DIR / exp_id
    if not exp_artifacts_dir.exists():
        return figures, tables

    # Load figures
    figures_dir = exp_artifacts_dir / "figures"
    if figures_dir.exists():
        for fig_dir in figures_dir.iterdir():
            if fig_dir.is_dir():
                metadata_file = fig_dir / "metadata.yaml"
                if metadata_file.exists() and HAS_YAML:
                    with open(metadata_file) as f:
                        meta = yaml.safe_load(f) or {}
                    figures.append(FigureArtifact(
                        id=fig_dir.name,
                        experiment_id=exp_id,
                        version=meta.get("version", 1),
                        path=str(fig_dir / "latest"),
                        format=meta.get("format", "pdf"),
                        generator=meta.get("generator", ""),
                        created_at=meta.get("created_at", ""),
                        metadata=meta,
                    ))

    # Load tables
    tables_dir = exp_artifacts_dir / "tables"
    if tables_dir.exists():
        for tbl_dir in tables_dir.iterdir():
            if tbl_dir.is_dir():
                metadata_file = tbl_dir / "metadata.yaml"
                if metadata_file.exists() and HAS_YAML:
                    with open(metadata_file) as f:
                        meta = yaml.safe_load(f) or {}
                    tables.append(TableArtifact(
                        id=tbl_dir.name,
                        experiment_id=exp_id,
                        version=meta.get("version", 1),
                        path=str(tbl_dir / "latest"),
                        format=meta.get("format", "tex"),
                        generator=meta.get("generator", ""),
                        created_at=meta.get("created_at", ""),
                        metadata=meta,
                    ))

    return figures, tables


def find_related_experiments(experiment: ExperimentMetadata) -> List[str]:
    """Find experiments related by sample_id, flowcell, or tags"""
    if not HAS_YAML:
        return []

    registry_file = REGISTRY_DIR / "experiments.yaml"
    if not registry_file.exists():
        return []

    with open(registry_file) as f:
        registry = yaml.safe_load(f) or {}

    related = []
    experiments = registry.get("experiments", {})

    for exp_id, exp in experiments.items():
        if exp_id == experiment.id:
            continue

        # Match by sample_id
        if experiment.sample_id and exp.get("sample_id") == experiment.sample_id:
            related.append(exp_id)
            continue

        # Match by flowcell
        if experiment.flowcell and exp.get("flowcell") == experiment.flowcell:
            related.append(exp_id)
            continue

        # Match by shared tags
        exp_tags = set(exp.get("tags", []))
        if experiment.tags and exp_tags & set(experiment.tags):
            related.append(exp_id)

    return related


def load_experiment_context(exp_id: str, db_path: Optional[str] = None) -> Optional[ExperimentContext]:
    """
    Load complete context for an experiment.

    This is the main entry point for getting a unified view of an experiment.

    Args:
        exp_id: Experiment identifier
        db_path: Optional path to SQLite database

    Returns:
        ExperimentContext with all available data, or None if experiment not found
    """
    # Load registry metadata
    experiment = load_registry_experiment(exp_id)
    if experiment is None:
        return None

    # Load events
    events = load_registry_events(exp_id)

    # Load tasks
    tasks = load_task_list(exp_id)

    # Load database record
    db_record = load_db_experiment(exp_id, db_path)

    # Load artifacts
    figures, tables = load_artifacts(exp_id)

    # Find related experiments
    related = find_related_experiments(experiment)

    # Build statistics from events
    statistics = None
    end_reasons = None
    for event in reversed(events):
        if statistics is None and event.results:
            if "total_reads" in event.results and "n50" in event.results:
                statistics = ReadStatistics(
                    total_reads=event.results.get("total_reads", 0),
                    total_bases=event.results.get("total_bases", 0),
                    mean_length=event.results.get("mean_length", 0),
                    n50=event.results.get("n50", 0),
                    mean_qscore=event.results.get("mean_qscore", 0),
                    median_qscore=event.results.get("median_qscore", 0),
                    pass_reads=event.results.get("pass_reads", 0),
                    fail_reads=event.results.get("fail_reads", 0),
                )

        if end_reasons is None and event.analysis in ("end_reasons", "endreason_qc"):
            results = event.results
            # Calculate from percentages if raw counts not available
            total = results.get("total_reads", 0)
            sp_pct = results.get("signal_positive_pct", 0)
            unblock_pct = results.get("unblock_mux_pct", results.get("unblock_pct", 0))

            end_reasons = EndReasonDistribution(
                signal_positive=int(total * sp_pct / 100) if sp_pct else 0,
                unblock_mux_change=int(total * unblock_pct / 100) if unblock_pct else 0,
                total=total,
            )

    return ExperimentContext(
        experiment=experiment,
        tasks=tasks,
        events=events,
        db_record=db_record,
        statistics=statistics,
        end_reasons=end_reasons,
        figures=figures,
        tables=tables,
        related_experiments=related,
    )


# =============================================================================
# Equation Execution System
# =============================================================================

def load_equations() -> Dict[str, Any]:
    """Load equations from textbook/equations.yaml"""
    if not HAS_YAML:
        return {}

    # Look for equations.yaml in textbook/
    script_dir = Path(__file__).parent.parent
    equations_path = script_dir / "textbook" / "equations.yaml"

    if not equations_path.exists():
        return {}

    with open(equations_path) as f:
        return yaml.safe_load(f) or {}


def get_applicable_equations(ctx: ExperimentContext) -> List[Equation]:
    """
    Find equations applicable to an experiment based on available data.

    Args:
        ctx: ExperimentContext

    Returns:
        List of applicable Equation objects
    """
    equations_db = load_equations()
    applicable = []

    for eq_id, eq_data in equations_db.get("equations", {}).items():
        if not isinstance(eq_data, dict):
            continue

        # Check if we have the required data for this equation
        required_stage = eq_data.get("pipeline_stage", "")
        variables = eq_data.get("variables", [])

        can_compute = True

        # Check based on pipeline stage
        if required_stage == "end_reasons" and not ctx.has_qc:
            can_compute = False
        elif required_stage == "basecalling" and not ctx.has_basecalling:
            can_compute = False

        if can_compute:
            applicable.append(Equation(
                id=eq_id,
                name=eq_data.get("name", eq_id),
                latex=eq_data.get("latex", ""),
                description=eq_data.get("description", ""),
                variables=variables if isinstance(variables, list) else [],
                python=eq_data.get("python"),
                pipeline_stage=required_stage,
            ))

    return applicable


def bind_variables(equation: Equation, ctx: ExperimentContext) -> Dict[str, Any]:
    """
    Bind equation variables to experiment context values.

    Args:
        equation: Equation to bind
        ctx: ExperimentContext with data

    Returns:
        Dict of variable name -> value
    """
    bindings = {}

    # Common variable mappings
    var_mapping = {
        # Read statistics
        "N": lambda c: c.statistics.total_reads if c.statistics else None,
        "total_reads": lambda c: c.statistics.total_reads if c.statistics else None,
        "total_bases": lambda c: c.statistics.total_bases if c.statistics else None,
        "n50": lambda c: c.statistics.n50 if c.statistics else None,
        "mean_length": lambda c: c.statistics.mean_length if c.statistics else None,
        "mean_qscore": lambda c: c.statistics.mean_qscore if c.statistics else None,
        "median_qscore": lambda c: c.statistics.median_qscore if c.statistics else None,
        "pass_reads": lambda c: c.statistics.pass_reads if c.statistics else None,
        "fail_reads": lambda c: c.statistics.fail_reads if c.statistics else None,

        # End reason metrics
        "signal_positive": lambda c: c.end_reasons.signal_positive if c.end_reasons else None,
        "signal_positive_pct": lambda c: c.end_reasons.signal_positive_pct if c.end_reasons else None,
        "unblock_pct": lambda c: c.end_reasons.unblock_pct if c.end_reasons else None,
    }

    for var in equation.variables:
        var_name = var if isinstance(var, str) else var.get("name", "")
        if var_name in var_mapping:
            bindings[var_name] = var_mapping[var_name](ctx)

    return bindings


def compute_equation(equation: Equation, ctx: ExperimentContext) -> EquationResult:
    """
    Execute an equation with experiment data as inputs.

    Args:
        equation: Equation to compute
        ctx: ExperimentContext with data

    Returns:
        EquationResult with computed value
    """
    inputs = bind_variables(equation, ctx)
    computed_at = datetime.now().isoformat()

    # Check if we have a Python implementation
    if not equation.python:
        return EquationResult(
            equation_id=equation.id,
            inputs=inputs,
            output=None,
            computed_at=computed_at,
            success=False,
            error="No Python implementation available",
        )

    # Check if all required inputs are available
    missing = [k for k, v in inputs.items() if v is None]
    if missing:
        return EquationResult(
            equation_id=equation.id,
            inputs=inputs,
            output=None,
            computed_at=computed_at,
            success=False,
            error=f"Missing inputs: {', '.join(missing)}",
        )

    try:
        # Create safe execution environment
        safe_globals = {
            "__builtins__": {},
            "abs": abs,
            "min": min,
            "max": max,
            "sum": sum,
            "len": len,
            "round": round,
            "pow": pow,
            "sqrt": lambda x: x ** 0.5,
            "log": lambda x: __import__('math').log(x),
            "log10": lambda x: __import__('math').log10(x),
            "exp": lambda x: __import__('math').exp(x),
        }
        safe_globals.update(inputs)

        result = eval(equation.python, safe_globals)

        return EquationResult(
            equation_id=equation.id,
            inputs=inputs,
            output=result,
            computed_at=computed_at,
            success=True,
        )

    except Exception as e:
        return EquationResult(
            equation_id=equation.id,
            inputs=inputs,
            output=None,
            computed_at=computed_at,
            success=False,
            error=str(e),
        )


def compute_all_equations(ctx: ExperimentContext) -> Dict[str, EquationResult]:
    """
    Compute all applicable equations for an experiment.

    Args:
        ctx: ExperimentContext

    Returns:
        Dict of equation_id -> EquationResult
    """
    results = {}
    applicable = get_applicable_equations(ctx)

    for equation in applicable:
        if equation.python:  # Only compute if we have implementation
            results[equation.id] = compute_equation(equation, ctx)

    return results


# =============================================================================
# Utility Functions
# =============================================================================

def list_experiments() -> List[str]:
    """List all experiment IDs in registry"""
    if not HAS_YAML:
        return []

    registry_file = REGISTRY_DIR / "experiments.yaml"
    if not registry_file.exists():
        return []

    with open(registry_file) as f:
        registry = yaml.safe_load(f) or {}

    return list(registry.get("experiments", {}).keys())


def get_experiment_summary(exp_id: str) -> Dict[str, Any]:
    """Get a quick summary of an experiment"""
    ctx = load_experiment_context(exp_id)
    if ctx is None:
        return {"error": f"Experiment {exp_id} not found"}

    return {
        "id": ctx.id,
        "name": ctx.name,
        "status": ctx.experiment.status,
        "quality_grade": ctx.quality_grade,
        "pending_tasks": len(ctx.tasks.pending_tasks),
        "completed_tasks": len(ctx.tasks.completed_tasks),
        "events_count": len(ctx.events),
        "figures_count": len(ctx.figures),
        "tables_count": len(ctx.tables),
    }


# =============================================================================
# CLI
# =============================================================================

def cmd_show(args):
    """Show experiment context"""
    ctx = load_experiment_context(args.experiment_id)
    if ctx is None:
        print(f"Experiment not found: {args.experiment_id}")
        sys.exit(1)

    if args.json:
        print(ctx.to_json())
    else:
        print(f"Experiment: {ctx.name} ({ctx.id})")
        print(f"Location: {ctx.experiment.location}")
        print(f"Status: {ctx.experiment.status}")
        print(f"Quality Grade: {ctx.quality_grade or 'N/A'}")
        print()
        print(f"Tasks:")
        print(f"  Pending: {len(ctx.tasks.pending_tasks)}")
        print(f"  Completed: {len(ctx.tasks.completed_tasks)}")
        print(f"  Failing: {len(ctx.tasks.failing_tasks)}")
        print()
        print(f"Events: {len(ctx.events)}")
        print(f"Figures: {len(ctx.figures)}")
        print(f"Tables: {len(ctx.tables)}")
        print(f"Related: {len(ctx.related_experiments)}")


def cmd_list(args):
    """List all experiments"""
    exp_ids = list_experiments()
    if args.json:
        summaries = [get_experiment_summary(eid) for eid in exp_ids]
        print(json.dumps(summaries, indent=2))
    else:
        for eid in exp_ids:
            summary = get_experiment_summary(eid)
            grade = summary.get("quality_grade", "-")
            pending = summary.get("pending_tasks", 0)
            print(f"{eid}: {summary['name']} [Grade: {grade}] [{pending} pending]")


def cmd_equations(args):
    """List or compute equations"""
    equations_db = load_equations()
    equations = equations_db.get("equations", {})

    if args.json:
        print(json.dumps({"total": len(equations), "equations": list(equations.keys())}, indent=2))
    else:
        print(f"Available Equations: {len(equations)}")
        print()

        # Group by category/chapter
        by_chapter = {}
        for eq_id, eq_data in equations.items():
            if isinstance(eq_data, dict):
                chapter = eq_data.get("chapter", "uncategorized")
                if chapter not in by_chapter:
                    by_chapter[chapter] = []
                by_chapter[chapter].append((eq_id, eq_data))

        for chapter in sorted(by_chapter.keys(), key=str):
            eqs = by_chapter[chapter]
            print(f"  {chapter}: {len(eqs)} equations")


def cmd_compute(args):
    """Compute equations for an experiment"""
    ctx = load_experiment_context(args.experiment_id)
    if ctx is None:
        print(f"Experiment not found: {args.experiment_id}")
        sys.exit(1)

    if args.equation_id:
        # Compute single equation
        equations_db = load_equations()
        eq_data = equations_db.get("equations", {}).get(args.equation_id)
        if not eq_data:
            print(f"Equation not found: {args.equation_id}")
            sys.exit(1)

        equation = Equation(
            id=args.equation_id,
            name=eq_data.get("name", args.equation_id),
            latex=eq_data.get("latex", ""),
            description=eq_data.get("description", ""),
            variables=eq_data.get("variables", []),
            python=eq_data.get("python"),
        )

        result = compute_equation(equation, ctx)

        if args.json:
            print(json.dumps({
                "equation_id": result.equation_id,
                "inputs": result.inputs,
                "output": result.output,
                "success": result.success,
                "error": result.error,
            }, indent=2))
        else:
            print(f"Equation: {equation.name}")
            print(f"LaTeX: {equation.latex[:60]}..." if len(equation.latex) > 60 else f"LaTeX: {equation.latex}")
            print(f"Inputs: {result.inputs}")
            if result.success:
                print(f"Result: {result.output}")
            else:
                print(f"Error: {result.error}")
    else:
        # Compute all applicable equations
        results = compute_all_equations(ctx)

        if args.json:
            output = {
                "experiment_id": ctx.id,
                "computed": len([r for r in results.values() if r.success]),
                "failed": len([r for r in results.values() if not r.success]),
                "results": {
                    eq_id: {
                        "output": r.output,
                        "success": r.success,
                        "error": r.error
                    } for eq_id, r in results.items()
                }
            }
            print(json.dumps(output, indent=2))
        else:
            successful = [r for r in results.values() if r.success]
            failed = [r for r in results.values() if not r.success]

            print(f"Experiment: {ctx.name}")
            print(f"Computed: {len(successful)} equations")
            print(f"Failed: {len(failed)} equations")
            print()

            if successful:
                print("Results:")
                for result in successful[:10]:  # Show first 10
                    print(f"  {result.equation_id}: {result.output}")
                if len(successful) > 10:
                    print(f"  ... and {len(successful) - 10} more")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="ONT Experiment Context - Unified Experiment View",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # show
    p_show = subparsers.add_parser("show", help="Show experiment context")
    p_show.add_argument("experiment_id", help="Experiment ID")
    p_show.add_argument("--json", action="store_true", help="Output as JSON")
    p_show.set_defaults(func=cmd_show)

    # list
    p_list = subparsers.add_parser("list", help="List all experiments")
    p_list.add_argument("--json", action="store_true", help="Output as JSON")
    p_list.set_defaults(func=cmd_list)

    # equations
    p_equations = subparsers.add_parser("equations", help="List available equations")
    p_equations.add_argument("--json", action="store_true", help="Output as JSON")
    p_equations.set_defaults(func=cmd_equations)

    # compute
    p_compute = subparsers.add_parser("compute", help="Compute equations for experiment")
    p_compute.add_argument("experiment_id", help="Experiment ID")
    p_compute.add_argument("--equation", "-e", dest="equation_id", help="Specific equation ID")
    p_compute.add_argument("--json", action="store_true", help="Output as JSON")
    p_compute.set_defaults(func=cmd_compute)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
    else:
        args.func(args)


if __name__ == "__main__":
    main()
