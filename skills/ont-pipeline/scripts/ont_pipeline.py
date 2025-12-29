#!/usr/bin/env python3
"""
ONT Pipeline - Multi-step Workflow Orchestration

Coordinates analysis pipelines with unified QC aggregation and pharmacogenomics support.

Usage:
  ont_pipeline.py list                          # List available pipelines
  ont_pipeline.py run pharmaco-clinical exp-id  # Execute pipeline
  ont_pipeline.py resume exp-id                 # Resume from checkpoint
  ont_pipeline.py report exp-id --format html   # Generate report
"""

import argparse
import json
import os
import sys
import subprocess
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict
import time

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    from jinja2 import Environment, FileSystemLoader
    HAS_JINJA = True
except ImportError:
    HAS_JINJA = False


# =============================================================================
# Configuration
# =============================================================================

REGISTRY_DIR = Path.home() / ".ont-registry"
PIPELINES_DIR = REGISTRY_DIR / "pipelines"
REGISTRY_FILE = REGISTRY_DIR / "experiments.yaml"

# Built-in pipeline definitions
BUILTIN_PIPELINES = {
    "pharmaco-clinical": {
        "name": "pharmaco-clinical",
        "description": "Clinical pharmacogenomics workflow with PharmCAT",
        "version": "1.0",
        "steps": [
            {
                "name": "end_reasons",
                "analysis": "end_reasons",
                "required": True,
                "pass_criteria": {"signal_positive_pct": ">=75"},
                "outputs": ["json", "plot"],
            },
            {
                "name": "basecalling",
                "analysis": "basecalling",
                "depends_on": ["end_reasons"],
                "parameters": {"model": "sup"},
                "outputs": ["bam", "json"],
            },
            {
                "name": "alignment",
                "analysis": "alignment",
                "depends_on": ["basecalling"],
                "parameters": {"reference": "GRCh38", "preset": "map-ont"},
                "outputs": ["bam", "stats"],
            },
            {
                "name": "variants",
                "analysis": "variant_calling",
                "depends_on": ["alignment"],
                "parameters": {"caller": "clair3"},
                "outputs": ["vcf", "json"],
            },
            {
                "name": "cyp2d6",
                "analysis": "cyp2d6_calling",
                "depends_on": ["variants"],
                "parameters": {"caller": "cyrius"},
                "outputs": ["json", "tsv"],
            },
            {
                "name": "pharmcat",
                "analysis": "pharmcat",
                "depends_on": ["variants", "cyp2d6"],
                "parameters": {"reporter": True},
                "outputs": ["json", "html"],
            },
        ],
        "aggregation": {
            "metrics": [
                {"source": "end_reasons", "fields": ["quality_status", "signal_positive_pct"]},
                {"source": "basecalling", "fields": ["mean_qscore", "n50", "total_reads"]},
                {"source": "alignment", "fields": ["mapped_pct", "mean_coverage"]},
                {"source": "variants", "fields": ["total_variants", "pass_variants"]},
                {"source": "cyp2d6", "fields": ["diplotype", "phenotype", "activity_score"]},
                {"source": "pharmcat", "fields": ["drug_count", "actionable_count"]},
            ]
        },
    },
    "qc-fast": {
        "name": "qc-fast",
        "description": "Quick QC assessment",
        "version": "1.0",
        "steps": [
            {
                "name": "end_reasons",
                "analysis": "end_reasons",
                "required": True,
                "outputs": ["json"],
            },
            {
                "name": "basecalling",
                "analysis": "basecalling",
                "depends_on": ["end_reasons"],
                "parameters": {"model": "fast"},
                "outputs": ["json"],
            },
        ],
    },
    "research-full": {
        "name": "research-full",
        "description": "Complete research workflow with methylation",
        "version": "1.0",
        "steps": [
            {
                "name": "end_reasons",
                "analysis": "end_reasons",
                "required": True,
                "outputs": ["json", "plot"],
            },
            {
                "name": "basecalling",
                "analysis": "basecalling",
                "depends_on": ["end_reasons"],
                "parameters": {"model": "sup", "modifications": "5mCG_5hmCG"},
                "outputs": ["bam", "json"],
            },
            {
                "name": "alignment",
                "analysis": "alignment",
                "depends_on": ["basecalling"],
                "outputs": ["bam", "stats"],
            },
            {
                "name": "variants",
                "analysis": "variant_calling",
                "depends_on": ["alignment"],
                "outputs": ["vcf", "json"],
            },
            {
                "name": "sv_calling",
                "analysis": "sv_calling",
                "depends_on": ["alignment"],
                "parameters": {"caller": "sniffles2"},
                "outputs": ["vcf"],
            },
        ],
    },
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PipelineStep:
    """Single step in a pipeline"""
    name: str
    analysis: str
    depends_on: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    required: bool = True
    pass_criteria: Dict[str, str] = field(default_factory=dict)
    outputs: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PipelineStep':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Pipeline:
    """Pipeline definition"""
    name: str
    description: str = ""
    version: str = "1.0"
    author: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    steps: List[PipelineStep] = field(default_factory=list)
    aggregation: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Pipeline':
        steps = []
        for step_data in data.get('steps', []):
            steps.append(PipelineStep.from_dict(step_data))
        
        return cls(
            name=data.get('name', ''),
            description=data.get('description', ''),
            version=data.get('version', '1.0'),
            author=data.get('author', ''),
            parameters=data.get('parameters', {}),
            steps=steps,
            aggregation=data.get('aggregation', {}),
        )
    
    def get_execution_order(self) -> List[PipelineStep]:
        """Topological sort of steps based on dependencies"""
        # Build dependency graph
        in_degree = {s.name: 0 for s in self.steps}
        graph = defaultdict(list)
        step_map = {s.name: s for s in self.steps}
        
        for step in self.steps:
            for dep in step.depends_on:
                if dep in step_map:
                    graph[dep].append(step.name)
                    in_degree[step.name] += 1
        
        # Kahn's algorithm
        queue = [name for name, deg in in_degree.items() if deg == 0]
        order = []
        
        while queue:
            node = queue.pop(0)
            order.append(step_map[node])
            
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(order) != len(self.steps):
            raise ValueError("Circular dependency detected in pipeline")
        
        return order


@dataclass
class StepResult:
    """Result of a pipeline step execution"""
    step_name: str
    status: str  # pending, running, completed, failed, skipped
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    exit_code: Optional[int] = None
    outputs: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class PipelineExecution:
    """Tracks a pipeline execution"""
    pipeline_name: str
    pipeline_version: str
    experiment_id: str
    status: str = "pending"  # pending, running, completed, failed
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    current_step: Optional[str] = None
    step_results: Dict[str, StepResult] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['step_results'] = {k: asdict(v) for k, v in self.step_results.items()}
        return d


# =============================================================================
# Pipeline Management
# =============================================================================

def list_pipelines() -> Dict[str, Pipeline]:
    """List all available pipelines (built-in + custom)"""
    pipelines = {}
    
    # Built-in pipelines
    for name, data in BUILTIN_PIPELINES.items():
        pipelines[name] = Pipeline.from_dict(data)
    
    # Custom pipelines from registry
    if PIPELINES_DIR.exists():
        for yaml_file in PIPELINES_DIR.glob("*.yaml"):
            try:
                with open(yaml_file) as f:
                    if HAS_YAML:
                        data = yaml.safe_load(f)
                    else:
                        continue
                if data:
                    pipeline = Pipeline.from_dict(data)
                    pipelines[pipeline.name] = pipeline
            except Exception as e:
                print(f"Warning: Could not load {yaml_file}: {e}")
    
    return pipelines


def get_pipeline(name: str) -> Optional[Pipeline]:
    """Get a specific pipeline by name"""
    pipelines = list_pipelines()
    return pipelines.get(name)


def validate_pipeline(pipeline: Pipeline) -> List[str]:
    """Validate pipeline definition, return list of errors"""
    errors = []
    
    if not pipeline.name:
        errors.append("Pipeline name is required")
    
    if not pipeline.steps:
        errors.append("Pipeline must have at least one step")
    
    step_names = {s.name for s in pipeline.steps}
    
    for step in pipeline.steps:
        if not step.name:
            errors.append("Step name is required")
        if not step.analysis:
            errors.append(f"Step '{step.name}' missing analysis type")
        
        for dep in step.depends_on:
            if dep not in step_names:
                errors.append(f"Step '{step.name}' depends on unknown step '{dep}'")
    
    # Check for cycles
    try:
        pipeline.get_execution_order()
    except ValueError as e:
        errors.append(str(e))
    
    return errors


# =============================================================================
# Pipeline Execution
# =============================================================================

def check_pass_criteria(criteria: Dict[str, str], results: Dict[str, Any]) -> bool:
    """Check if step results meet pass criteria"""
    for metric, condition in criteria.items():
        if metric not in results:
            return False
        
        value = results[metric]
        
        # Parse condition
        if condition.startswith(">="):
            threshold = float(condition[2:])
            if value < threshold:
                return False
        elif condition.startswith("<="):
            threshold = float(condition[2:])
            if value > threshold:
                return False
        elif condition.startswith(">"):
            threshold = float(condition[1:])
            if value <= threshold:
                return False
        elif condition.startswith("<"):
            threshold = float(condition[1:])
            if value >= threshold:
                return False
        elif condition.startswith("=="):
            expected = condition[2:]
            if str(value) != expected:
                return False
    
    return True


def run_step(
    step: PipelineStep,
    experiment_id: str,
    experiment_location: str,
    param_overrides: Dict[str, Any] = None,
    dry_run: bool = False,
) -> StepResult:
    """Execute a single pipeline step"""
    
    result = StepResult(
        step_name=step.name,
        status="running",
        start_time=datetime.now(timezone.utc).isoformat(),
    )
    
    # Merge parameters
    params = {**step.parameters}
    if param_overrides:
        for key, value in param_overrides.items():
            if key.startswith(f"{step.name}."):
                param_key = key[len(step.name) + 1:]
                params[param_key] = value
    
    # Build command
    # Use ont_experiments.py run for provenance tracking
    cmd = ["python3", "ont_experiments.py", "run", step.analysis, experiment_id]
    
    # Add parameters as CLI args
    for key, value in params.items():
        if isinstance(value, bool):
            if value:
                cmd.append(f"--{key.replace('_', '-')}")
        else:
            cmd.extend([f"--{key.replace('_', '-')}", str(value)])
    
    # Add output files
    output_dir = Path(experiment_location) / "pipeline_outputs" / step.name
    for output_type in step.outputs:
        if output_type == "json":
            cmd.extend(["--json", str(output_dir / f"{step.name}.json")])
            result.outputs.append(str(output_dir / f"{step.name}.json"))
        elif output_type == "plot":
            cmd.extend(["--plot", str(output_dir / f"{step.name}.png")])
            result.outputs.append(str(output_dir / f"{step.name}.png"))
        elif output_type == "bam":
            cmd.extend(["--output", str(output_dir / f"{step.name}.bam")])
            result.outputs.append(str(output_dir / f"{step.name}.bam"))
        elif output_type == "vcf":
            cmd.extend(["--output", str(output_dir / f"{step.name}.vcf.gz")])
            result.outputs.append(str(output_dir / f"{step.name}.vcf.gz"))
    
    if dry_run:
        print(f"  [DRY RUN] Would execute: {' '.join(cmd)}")
        result.status = "skipped"
        result.end_time = datetime.now(timezone.utc).isoformat()
        return result
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Execute
    start_time = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=experiment_location,
        )
        result.exit_code = proc.returncode
        
        if proc.returncode != 0:
            result.status = "failed"
            result.error_message = proc.stderr[:500] if proc.stderr else "Unknown error"
        else:
            result.status = "completed"
            
            # Load metrics from JSON output if available
            json_output = output_dir / f"{step.name}.json"
            if json_output.exists():
                try:
                    with open(json_output) as f:
                        result.metrics = json.load(f)
                except Exception:
                    pass
    
    except Exception as e:
        result.status = "failed"
        result.exit_code = -1
        result.error_message = str(e)
    
    result.duration_seconds = round(time.time() - start_time, 2)
    result.end_time = datetime.now(timezone.utc).isoformat()
    
    return result


def run_pipeline(
    pipeline: Pipeline,
    experiment_id: str,
    experiment_location: str,
    param_overrides: Dict[str, Any] = None,
    from_step: Optional[str] = None,
    skip_steps: Set[str] = None,
    dry_run: bool = False,
) -> PipelineExecution:
    """Execute a complete pipeline"""
    
    execution = PipelineExecution(
        pipeline_name=pipeline.name,
        pipeline_version=pipeline.version,
        experiment_id=experiment_id,
        status="running",
        start_time=datetime.now(timezone.utc).isoformat(),
        parameters=param_overrides or {},
    )
    
    skip_steps = skip_steps or set()
    
    # Get execution order
    steps = pipeline.get_execution_order()
    
    # Find starting point if resuming
    start_idx = 0
    if from_step:
        for i, step in enumerate(steps):
            if step.name == from_step:
                start_idx = i
                break
    
    print(f"\n  Pipeline: {pipeline.name} v{pipeline.version}")
    print(f"  Experiment: {experiment_id}")
    print(f"  Steps: {len(steps)}")
    print(f"  {'─' * 50}")
    
    failed = False
    
    for i, step in enumerate(steps):
        execution.current_step = step.name
        
        # Skip if before start point
        if i < start_idx:
            print(f"  [{i+1}/{len(steps)}] {step.name}: SKIPPED (before start)")
            execution.step_results[step.name] = StepResult(
                step_name=step.name,
                status="skipped",
            )
            continue
        
        # Skip if in skip list
        if step.name in skip_steps:
            print(f"  [{i+1}/{len(steps)}] {step.name}: SKIPPED (requested)")
            execution.step_results[step.name] = StepResult(
                step_name=step.name,
                status="skipped",
            )
            continue
        
        # Check dependencies
        deps_met = True
        for dep in step.depends_on:
            if dep in execution.step_results:
                dep_result = execution.step_results[dep]
                if dep_result.status == "failed":
                    deps_met = False
                    break
        
        if not deps_met:
            print(f"  [{i+1}/{len(steps)}] {step.name}: SKIPPED (dependency failed)")
            execution.step_results[step.name] = StepResult(
                step_name=step.name,
                status="skipped",
                error_message="Dependency failed",
            )
            continue
        
        # Run step
        print(f"  [{i+1}/{len(steps)}] {step.name}: RUNNING...", end="", flush=True)
        
        result = run_step(
            step=step,
            experiment_id=experiment_id,
            experiment_location=experiment_location,
            param_overrides=param_overrides,
            dry_run=dry_run,
        )
        
        execution.step_results[step.name] = result
        
        if result.status == "completed":
            duration = f"({result.duration_seconds:.1f}s)" if result.duration_seconds else ""
            print(f"\r  [{i+1}/{len(steps)}] {step.name}: ✓ COMPLETED {duration}")
            
            # Check pass criteria
            if step.pass_criteria and result.metrics:
                if not check_pass_criteria(step.pass_criteria, result.metrics):
                    print(f"       ⚠ Warning: Pass criteria not met")
                    if step.required:
                        failed = True
        
        elif result.status == "failed":
            print(f"\r  [{i+1}/{len(steps)}] {step.name}: ✗ FAILED")
            if result.error_message:
                print(f"       Error: {result.error_message[:100]}")
            
            if step.required:
                failed = True
                break
        
        else:
            print(f"\r  [{i+1}/{len(steps)}] {step.name}: {result.status}")
    
    execution.end_time = datetime.now(timezone.utc).isoformat()
    execution.status = "failed" if failed else "completed"
    execution.current_step = None
    
    # Summary
    completed = sum(1 for r in execution.step_results.values() if r.status == "completed")
    failed_count = sum(1 for r in execution.step_results.values() if r.status == "failed")
    skipped = sum(1 for r in execution.step_results.values() if r.status == "skipped")
    
    print(f"  {'─' * 50}")
    print(f"  Status: {execution.status.upper()}")
    print(f"  Completed: {completed}, Failed: {failed_count}, Skipped: {skipped}")
    
    return execution


# =============================================================================
# QC Report Generation
# =============================================================================

def aggregate_metrics(execution: PipelineExecution, pipeline: Pipeline) -> Dict[str, Any]:
    """Aggregate metrics from all pipeline steps"""
    aggregated = {
        "pipeline": pipeline.name,
        "version": pipeline.version,
        "experiment": execution.experiment_id,
        "status": execution.status,
        "start_time": execution.start_time,
        "end_time": execution.end_time,
        "steps": {},
        "summary": {},
    }
    
    # Collect all step metrics
    for step_name, result in execution.step_results.items():
        aggregated["steps"][step_name] = {
            "status": result.status,
            "duration_seconds": result.duration_seconds,
            "metrics": result.metrics,
        }
    
    # Build summary from aggregation config
    if pipeline.aggregation and "metrics" in pipeline.aggregation:
        for metric_config in pipeline.aggregation["metrics"]:
            source = metric_config["source"]
            if source in execution.step_results:
                step_result = execution.step_results[source]
                for field in metric_config.get("fields", []):
                    if field in step_result.metrics:
                        aggregated["summary"][f"{source}.{field}"] = step_result.metrics[field]
    
    return aggregated


def generate_html_report(aggregated: Dict[str, Any], output_path: Path):
    """Generate HTML QC report"""
    
    html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>ONT Pipeline Report - {{ experiment }}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 20px; }
        .header h1 { margin: 0 0 10px 0; font-size: 24px; }
        .header .meta { opacity: 0.9; font-size: 14px; }
        .status { display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: 600; text-transform: uppercase; font-size: 12px; }
        .status.completed { background: #10b981; }
        .status.failed { background: #ef4444; }
        .card { background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .card h2 { margin: 0 0 15px 0; font-size: 18px; color: #374151; }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; }
        .metric { background: #f9fafb; border-radius: 8px; padding: 15px; text-align: center; }
        .metric-value { font-size: 24px; font-weight: 700; color: #1f2937; }
        .metric-label { font-size: 12px; color: #6b7280; margin-top: 5px; }
        .steps-list { display: flex; flex-direction: column; gap: 10px; }
        .step { display: flex; align-items: center; gap: 15px; padding: 12px; background: #f9fafb; border-radius: 8px; }
        .step-icon { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 16px; }
        .step-icon.completed { background: #d1fae5; color: #10b981; }
        .step-icon.failed { background: #fee2e2; color: #ef4444; }
        .step-icon.skipped { background: #e5e7eb; color: #6b7280; }
        .step-info { flex: 1; }
        .step-name { font-weight: 600; color: #1f2937; }
        .step-duration { font-size: 12px; color: #6b7280; }
        table { width: 100%; border-collapse: collapse; }
        th, td { text-align: left; padding: 10px; border-bottom: 1px solid #e5e7eb; }
        th { font-weight: 600; color: #6b7280; font-size: 12px; text-transform: uppercase; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ pipeline }} Pipeline Report</h1>
            <div class="meta">
                Experiment: {{ experiment }} &bull; 
                Version: {{ version }} &bull;
                <span class="status {{ status }}">{{ status }}</span>
            </div>
        </div>
        
        <div class="card">
            <h2>Summary Metrics</h2>
            <div class="metrics-grid">
                {% for key, value in summary.items() %}
                <div class="metric">
                    <div class="metric-value">{{ value }}</div>
                    <div class="metric-label">{{ key }}</div>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <div class="card">
            <h2>Pipeline Steps</h2>
            <div class="steps-list">
                {% for name, step in steps.items() %}
                <div class="step">
                    <div class="step-icon {{ step.status }}">
                        {% if step.status == 'completed' %}✓{% elif step.status == 'failed' %}✗{% else %}○{% endif %}
                    </div>
                    <div class="step-info">
                        <div class="step-name">{{ name }}</div>
                        <div class="step-duration">
                            {% if step.duration_seconds %}{{ step.duration_seconds }}s{% else %}—{% endif %}
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <div class="card">
            <h2>Detailed Metrics</h2>
            <table>
                <thead>
                    <tr>
                        <th>Step</th>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody>
                    {% for step_name, step in steps.items() %}
                    {% for metric, value in step.metrics.items() %}
                    <tr>
                        <td>{{ step_name }}</td>
                        <td>{{ metric }}</td>
                        <td>{{ value }}</td>
                    </tr>
                    {% endfor %}
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
    """
    
    if HAS_JINJA:
        from jinja2 import Template
        template = Template(html_template)
        html = template.render(**aggregated)
    else:
        # Simple string replacement fallback
        html = html_template
        html = html.replace("{{ pipeline }}", aggregated["pipeline"])
        html = html.replace("{{ experiment }}", aggregated["experiment"])
        html = html.replace("{{ version }}", aggregated["version"])
        html = html.replace("{{ status }}", aggregated["status"])
    
    with open(output_path, 'w') as f:
        f.write(html)
    
    print(f"  Report saved: {output_path}")


# =============================================================================
# CLI Commands
# =============================================================================

def cmd_list(args):
    """List available pipelines"""
    pipelines = list_pipelines()
    
    print(f"\n  Available Pipelines")
    print(f"  {'═' * 50}")
    
    for name, pipeline in pipelines.items():
        steps = len(pipeline.steps)
        print(f"\n  {name} (v{pipeline.version})")
        print(f"    {pipeline.description}")
        print(f"    Steps: {steps}")
    
    return 0


def cmd_show(args):
    """Show pipeline details"""
    pipeline = get_pipeline(args.pipeline)
    
    if not pipeline:
        print(f"Error: Pipeline '{args.pipeline}' not found")
        return 1
    
    print(f"\n  Pipeline: {pipeline.name}")
    print(f"  {'═' * 50}")
    print(f"  Description: {pipeline.description}")
    print(f"  Version: {pipeline.version}")
    
    print(f"\n  Steps:")
    for i, step in enumerate(pipeline.get_execution_order(), 1):
        deps = f" (depends: {', '.join(step.depends_on)})" if step.depends_on else ""
        print(f"    {i}. {step.name} → {step.analysis}{deps}")
    
    return 0


def cmd_validate(args):
    """Validate pipeline"""
    pipeline = get_pipeline(args.pipeline)
    
    if not pipeline:
        print(f"Error: Pipeline '{args.pipeline}' not found")
        return 1
    
    errors = validate_pipeline(pipeline)
    
    if errors:
        print(f"\n  Validation FAILED:")
        for error in errors:
            print(f"    ✗ {error}")
        return 1
    else:
        print(f"\n  Validation PASSED: {pipeline.name}")
        return 0


def cmd_run(args):
    """Run pipeline on experiment"""
    pipeline = get_pipeline(args.pipeline)
    
    if not pipeline:
        print(f"Error: Pipeline '{args.pipeline}' not found")
        return 1
    
    # Parse parameter overrides
    param_overrides = {}
    if args.param:
        for p in args.param:
            if '=' in p:
                key, value = p.split('=', 1)
                param_overrides[key] = value
    
    # Parse skip steps
    skip_steps = set(args.skip_step) if args.skip_step else set()
    
    # TODO: Load experiment location from registry
    experiment_location = "/tmp/experiment"  # Placeholder
    
    execution = run_pipeline(
        pipeline=pipeline,
        experiment_id=args.experiment,
        experiment_location=experiment_location,
        param_overrides=param_overrides,
        from_step=args.from_step,
        skip_steps=skip_steps,
        dry_run=args.dry_run,
    )
    
    return 0 if execution.status == "completed" else 1


def cmd_report(args):
    """Generate unified report"""
    print(f"\n  Generating report for {args.experiment}...")
    
    # TODO: Load execution from registry
    # For now, create mock data
    pipeline = get_pipeline("pharmaco-clinical")
    
    mock_execution = PipelineExecution(
        pipeline_name="pharmaco-clinical",
        pipeline_version="1.0",
        experiment_id=args.experiment,
        status="completed",
        step_results={
            "end_reasons": StepResult(
                step_name="end_reasons",
                status="completed",
                duration_seconds=245,
                metrics={"quality_status": "PASS", "signal_positive_pct": 92.3, "total_reads": 15420000}
            ),
            "basecalling": StepResult(
                step_name="basecalling",
                status="completed",
                duration_seconds=7200,
                metrics={"mean_qscore": 18.7, "n50": 12500, "total_reads": 15420000}
            ),
        }
    )
    
    aggregated = aggregate_metrics(mock_execution, pipeline)
    
    output_path = Path(args.output) if args.output else Path(f"{args.experiment}_report.html")
    
    if args.format == "html":
        generate_html_report(aggregated, output_path)
    elif args.format == "json":
        with open(output_path, 'w') as f:
            json.dump(aggregated, f, indent=2)
        print(f"  Report saved: {output_path}")
    
    return 0


def cmd_create(args):
    """Create new pipeline template"""
    PIPELINES_DIR.mkdir(parents=True, exist_ok=True)
    
    template = {
        "name": args.name,
        "description": "Custom analysis workflow",
        "version": "1.0",
        "author": os.getenv("USER", ""),
        "steps": [
            {
                "name": "qc",
                "analysis": "end_reasons",
                "required": True,
                "outputs": ["json"],
            },
            {
                "name": "basecalling",
                "analysis": "basecalling",
                "depends_on": ["qc"],
                "parameters": {"model": "hac"},
                "outputs": ["bam", "json"],
            },
        ],
        "aggregation": {
            "metrics": [
                {"source": "qc", "fields": ["quality_status"]},
                {"source": "basecalling", "fields": ["mean_qscore"]},
            ]
        }
    }
    
    output_path = PIPELINES_DIR / f"{args.name}.yaml"
    
    if output_path.exists() and not args.force:
        print(f"Error: Pipeline '{args.name}' already exists. Use --force to overwrite.")
        return 1
    
    with open(output_path, 'w') as f:
        if HAS_YAML:
            yaml.dump(template, f, default_flow_style=False, sort_keys=False)
        else:
            json.dump(template, f, indent=2)
    
    print(f"\n  Created: {output_path}")
    print(f"  Edit this file to customize your pipeline.")
    
    return 0


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='ONT Pipeline - Multi-step Workflow Orchestration',
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # list
    p_list = subparsers.add_parser('list', help='List available pipelines')
    
    # show
    p_show = subparsers.add_parser('show', help='Show pipeline details')
    p_show.add_argument('pipeline', help='Pipeline name')
    
    # validate
    p_validate = subparsers.add_parser('validate', help='Validate pipeline')
    p_validate.add_argument('pipeline', help='Pipeline name')
    
    # run
    p_run = subparsers.add_parser('run', help='Run pipeline on experiment')
    p_run.add_argument('pipeline', help='Pipeline name')
    p_run.add_argument('experiment', help='Experiment ID')
    p_run.add_argument('--param', action='append', help='Parameter override (key=value)')
    p_run.add_argument('--skip-step', action='append', help='Steps to skip')
    p_run.add_argument('--from-step', help='Start from this step')
    p_run.add_argument('--dry-run', action='store_true', help='Show execution plan')
    
    # report
    p_report = subparsers.add_parser('report', help='Generate unified report')
    p_report.add_argument('experiment', help='Experiment ID')
    p_report.add_argument('--format', choices=['html', 'json', 'pdf', 'markdown'], default='html')
    p_report.add_argument('--output', '-o', help='Output file path')
    
    # create
    p_create = subparsers.add_parser('create', help='Create pipeline template')
    p_create.add_argument('name', help='Pipeline name')
    p_create.add_argument('--force', '-f', action='store_true', help='Overwrite existing')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    commands = {
        'list': cmd_list,
        'show': cmd_show,
        'validate': cmd_validate,
        'run': cmd_run,
        'report': cmd_report,
        'create': cmd_create,
    }
    
    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
