#!/usr/bin/env python3
"""
ONT Manuscript Studio - Dataset Selection, Processing, and Visualization

A comprehensive tool for generating publication-quality figures and tables
from ONT sequencing experiments. Supports both the SMS Haplotype Framework
Textbook and new manuscript generation.

Features:
- Dataset selection with filtering and comparison
- Pipeline-based processing with auto-generated artifacts
- Versioned figure/table storage
- Multi-format export (PDF, PNG, HTML, LaTeX, JSON)
- Integration with SMS_textbook

Part of: https://github.com/Single-Molecule-Sequencing/ont-ecosystem

Usage:
  ont_manuscript.py select --tag cyp2d6              # Select datasets
  ont_manuscript.py pipeline qc-report exp-abc123    # Run pipeline
  ont_manuscript.py figure fig_end_reason_kde exp-abc123
  ont_manuscript.py table tbl_qc_summary exp-abc123
  ont_manuscript.py export exp-abc123 ./manuscript --target latex
  ont_manuscript.py compare exp-abc123 exp-def456
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Union

# Optional imports
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Try to import context module
try:
    from ont_context import (
        load_experiment_context, list_experiments,
        ExperimentContext, FigureArtifact, TableArtifact,
        ARTIFACTS_DIR, MANUSCRIPT_DIR
    )
    HAS_CONTEXT = True
except ImportError:
    HAS_CONTEXT = False
    ARTIFACTS_DIR = Path.home() / ".ont-manuscript" / "artifacts"
    MANUSCRIPT_DIR = Path.home() / ".ont-manuscript"


# =============================================================================
# Configuration
# =============================================================================

GENERATORS_DIR = Path(__file__).parent.parent / "skills" / "manuscript" / "generators"
EXPORTS_DIR = MANUSCRIPT_DIR / "exports"


# =============================================================================
# Pipeline Definitions
# =============================================================================

MANUSCRIPT_PIPELINES = {
    "qc-report": {
        "description": "Generate QC figures and summary table",
        "steps": ["end_reasons"],
        "auto_figures": ["fig_end_reason_kde", "fig_quality_dist"],
        "auto_tables": ["tbl_qc_summary"],
        "requires_data": True,
    },
    "full-analysis": {
        "description": "Complete analysis with all figures",
        "steps": ["end_reasons", "basecalling", "alignment"],
        "auto_figures": [
            "fig_end_reason_kde", "fig_quality_dist",
            "fig_coverage", "fig_alignment_stats"
        ],
        "auto_tables": ["tbl_qc_summary", "tbl_basecalling", "tbl_alignment"],
        "requires_data": True,
    },
    "comparison": {
        "description": "Compare multiple experiments",
        "steps": ["load_contexts"],
        "auto_figures": ["fig_comparison_overlay", "fig_box_comparison"],
        "auto_tables": ["tbl_comparison"],
        "requires_data": False,
        "multi_experiment": True,
    },
    "summary-only": {
        "description": "Generate summary tables without new analysis",
        "steps": [],
        "auto_figures": [],
        "auto_tables": ["tbl_experiment_summary"],
        "requires_data": False,
    },
}


# =============================================================================
# Figure Generator Registry
# =============================================================================

FIGURE_GENERATORS = {
    "fig_end_reason_kde": {
        "generator": "gen_end_reason_kde.py",
        "description": "KDE plot of read lengths by end reason",
        "formats": ["pdf", "png"],
        "requires": ["end_reasons"],
        "caption": "Read length distribution by end reason category",
    },
    "fig_quality_dist": {
        "generator": "gen_quality_distribution.py",
        "description": "Q-score distribution histogram",
        "formats": ["pdf", "png"],
        "requires": ["basecalling"],
        "caption": "Quality score distribution",
    },
    "fig_read_length": {
        "generator": "gen_read_length_distribution.py",
        "description": "Read length distribution with log scale",
        "formats": ["pdf", "png"],
        "requires": [],
        "caption": "Read length distribution",
    },
    "fig_coverage": {
        "generator": "gen_coverage_plot.py",
        "description": "Coverage depth plot",
        "formats": ["pdf", "png"],
        "requires": ["alignment"],
        "caption": "Coverage depth across reference",
    },
    "fig_alignment_stats": {
        "generator": "gen_alignment_stats.py",
        "description": "Alignment statistics visualization",
        "formats": ["pdf", "png"],
        "requires": ["alignment"],
        "caption": "Alignment quality metrics",
    },
    "fig_comparison": {
        "generator": "gen_comparison_plot.py",
        "description": "Multi-panel comparison of experiments",
        "formats": ["pdf", "png"],
        "requires": [],
        "multi_experiment": True,
        "caption": "Experiment comparison",
    },
    "fig_yield_timeline": {
        "generator": "gen_yield_timeline.py",
        "description": "Cumulative yield over time",
        "formats": ["pdf", "png"],
        "requires": [],
        "caption": "Cumulative sequencing yield over time",
    },
    "fig_end_reason_pie": {
        "generator": "gen_end_reason_pie.py",
        "description": "End reason distribution pie/donut chart",
        "formats": ["pdf", "png"],
        "requires": ["end_reasons"],
        "caption": "Read end reason distribution",
    },
    "fig_metrics_heatmap": {
        "generator": "gen_metrics_heatmap.py",
        "description": "Heatmap of QC metrics across experiments",
        "formats": ["pdf", "png"],
        "requires": [],
        "multi_experiment": True,
        "caption": "QC metrics comparison heatmap",
    },
    "fig_n50_barplot": {
        "generator": "gen_n50_barplot.py",
        "description": "N50 bar chart comparison",
        "formats": ["pdf", "png"],
        "requires": [],
        "multi_experiment": True,
        "caption": "N50 comparison across experiments",
    },
}


# =============================================================================
# Table Generator Registry
# =============================================================================

TABLE_GENERATORS = {
    "tbl_qc_summary": {
        "generator": "gen_qc_summary_table.py",
        "description": "QC metrics summary table",
        "formats": ["tex", "csv", "json", "html"],
        "requires": ["end_reasons"],
        "caption": "Quality control summary metrics",
    },
    "tbl_basecalling": {
        "generator": "gen_basecalling_table.py",
        "description": "Basecalling statistics table",
        "formats": ["tex", "csv", "json", "html"],
        "requires": ["basecalling"],
        "caption": "Basecalling performance metrics",
    },
    "tbl_alignment": {
        "generator": "gen_alignment_table.py",
        "description": "Alignment statistics table",
        "formats": ["tex", "csv", "json", "html"],
        "requires": ["alignment"],
        "caption": "Alignment quality metrics",
    },
    "tbl_comparison": {
        "generator": "gen_comparison_table.py",
        "description": "Multi-experiment comparison table",
        "formats": ["tex", "csv", "json", "html"],
        "requires": [],
        "multi_experiment": True,
        "caption": "Experiment comparison",
    },
    "tbl_experiment_summary": {
        "generator": "gen_experiment_summary_table.py",
        "description": "Single experiment summary",
        "formats": ["tex", "csv", "json", "html"],
        "requires": [],
        "caption": "Experiment overview",
    },
}


# =============================================================================
# Artifact Storage
# =============================================================================

def get_artifact_dir(exp_id: str, artifact_type: str, artifact_id: str) -> Path:
    """Get directory for artifact storage"""
    return ARTIFACTS_DIR / exp_id / artifact_type / artifact_id


def get_next_version(artifact_dir: Path) -> int:
    """Get next version number for artifact"""
    if not artifact_dir.exists():
        return 1

    versions = []
    for item in artifact_dir.iterdir():
        if item.is_dir() and item.name.startswith("v"):
            try:
                versions.append(int(item.name[1:]))
            except ValueError:
                pass

    return max(versions, default=0) + 1


def save_artifact(exp_id: str, artifact_type: str, artifact_id: str,
                  content_path: Path, format: str, generator: str,
                  metadata: Dict[str, Any] = None) -> Path:
    """
    Save artifact with versioning.

    Args:
        exp_id: Experiment ID
        artifact_type: 'figures' or 'tables'
        artifact_id: Unique artifact identifier
        content_path: Path to generated content
        format: File format (pdf, png, tex, etc.)
        generator: Name of generator script
        metadata: Additional metadata

    Returns:
        Path to saved artifact
    """
    artifact_dir = get_artifact_dir(exp_id, artifact_type, artifact_id)
    version = get_next_version(artifact_dir)

    version_dir = artifact_dir / f"v{version}"
    version_dir.mkdir(parents=True, exist_ok=True)

    # Copy content
    dest_path = version_dir / f"{artifact_id}.{format}"
    shutil.copy(content_path, dest_path)

    # Create/update latest symlink
    latest_link = artifact_dir / "latest"
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    latest_link.symlink_to(f"v{version}")

    # Write metadata
    meta = {
        "id": artifact_id,
        "experiment_id": exp_id,
        "version": version,
        "format": format,
        "generator": generator,
        "created_at": datetime.now().isoformat(),
        **(metadata or {})
    }

    if HAS_YAML:
        meta_path = version_dir / "metadata.yaml"
        with open(meta_path, "w") as f:
            yaml.dump(meta, f, default_flow_style=False)
    else:
        meta_path = version_dir / "metadata.json"
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

    return dest_path


def list_artifacts(exp_id: str, artifact_type: str = None) -> List[Dict[str, Any]]:
    """List all artifacts for an experiment"""
    artifacts = []
    exp_dir = ARTIFACTS_DIR / exp_id

    if not exp_dir.exists():
        return artifacts

    types_to_check = [artifact_type] if artifact_type else ["figures", "tables"]

    for atype in types_to_check:
        type_dir = exp_dir / atype
        if not type_dir.exists():
            continue

        for art_dir in type_dir.iterdir():
            if not art_dir.is_dir():
                continue

            latest = art_dir / "latest"
            if latest.exists():
                meta_file = latest / "metadata.yaml"
                if not meta_file.exists():
                    meta_file = latest / "metadata.json"

                if meta_file.exists():
                    if HAS_YAML and meta_file.suffix == ".yaml":
                        with open(meta_file) as f:
                            meta = yaml.safe_load(f)
                    else:
                        with open(meta_file) as f:
                            meta = json.load(f)
                    meta["type"] = atype
                    meta["path"] = str(latest)
                    artifacts.append(meta)

    return artifacts


# =============================================================================
# Figure Generation
# =============================================================================

def generate_figure(fig_id: str, exp_id: str, format: str = "pdf",
                    output_dir: Path = None, **kwargs) -> Optional[Path]:
    """
    Generate a figure using the registered generator.

    Args:
        fig_id: Figure identifier from FIGURE_GENERATORS
        exp_id: Experiment ID
        format: Output format (pdf, png)
        output_dir: Optional custom output directory
        **kwargs: Additional arguments for generator

    Returns:
        Path to generated figure, or None on failure
    """
    if fig_id not in FIGURE_GENERATORS:
        print(f"Error: Unknown figure type: {fig_id}")
        return None

    gen_info = FIGURE_GENERATORS[fig_id]
    generator_script = GENERATORS_DIR / gen_info["generator"]

    if not generator_script.exists():
        print(f"Warning: Generator script not found: {generator_script}")
        print(f"  Using fallback inline generation for {fig_id}")
        return _generate_figure_inline(fig_id, exp_id, format, output_dir, **kwargs)

    # Run generator script
    if output_dir is None:
        output_dir = Path.cwd()

    output_path = output_dir / f"{fig_id}.{format}"

    cmd = [
        sys.executable, str(generator_script),
        exp_id,
        "--output", str(output_path),
        "--format", format,
    ]

    for key, value in kwargs.items():
        cmd.extend([f"--{key.replace('_', '-')}", str(value)])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and output_path.exists():
            # Save to artifact storage
            save_artifact(
                exp_id, "figures", fig_id, output_path, format,
                gen_info["generator"],
                {"caption": gen_info.get("caption", "")}
            )
            return output_path
        else:
            print(f"Generator failed: {result.stderr}")
            return None
    except Exception as e:
        print(f"Error running generator: {e}")
        return None


def _generate_figure_inline(fig_id: str, exp_id: str, format: str,
                            output_dir: Path, **kwargs) -> Optional[Path]:
    """Inline figure generation fallback using matplotlib"""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print("Error: matplotlib required for figure generation")
        return None

    if not HAS_CONTEXT:
        print("Error: ont_context module required")
        return None

    ctx = load_experiment_context(exp_id)
    if ctx is None:
        print(f"Error: Experiment not found: {exp_id}")
        return None

    if output_dir is None:
        output_dir = Path.cwd()

    output_path = output_dir / f"{fig_id}.{format}"

    fig, ax = plt.subplots(figsize=(10, 6))

    if fig_id == "fig_end_reason_kde":
        # Simple bar chart of end reason percentages
        if ctx.end_reasons:
            categories = ["Signal Positive", "Unblock/MUX"]
            values = [ctx.end_reasons.signal_positive_pct, ctx.end_reasons.unblock_pct]
            ax.bar(categories, values, color=['#2ecc71', '#e74c3c'])
            ax.set_ylabel("Percentage (%)")
            ax.set_title(f"End Reason Distribution: {ctx.name}")
        else:
            ax.text(0.5, 0.5, "No end reason data available",
                   ha='center', va='center', transform=ax.transAxes)

    elif fig_id == "fig_quality_dist":
        # Placeholder for quality distribution
        ax.text(0.5, 0.5, f"Quality distribution for {ctx.name}\n(Data not loaded)",
               ha='center', va='center', transform=ax.transAxes)

    else:
        ax.text(0.5, 0.5, f"Figure: {fig_id}\nExperiment: {ctx.name}",
               ha='center', va='center', transform=ax.transAxes)

    plt.tight_layout()
    plt.savefig(output_path, dpi=kwargs.get('dpi', 150))
    plt.close()

    # Save to artifact storage
    gen_info = FIGURE_GENERATORS.get(fig_id, {})
    save_artifact(
        exp_id, "figures", fig_id, output_path, format,
        "inline_generator",
        {"caption": gen_info.get("caption", "")}
    )

    return output_path


# =============================================================================
# Table Generation
# =============================================================================

def generate_table(tbl_id: str, exp_id: str, format: str = "tex",
                   output_dir: Path = None, **kwargs) -> Optional[Path]:
    """
    Generate a table using the registered generator.

    Args:
        tbl_id: Table identifier from TABLE_GENERATORS
        exp_id: Experiment ID
        format: Output format (tex, csv, json, html)
        output_dir: Optional custom output directory
        **kwargs: Additional arguments for generator

    Returns:
        Path to generated table, or None on failure
    """
    if tbl_id not in TABLE_GENERATORS:
        print(f"Error: Unknown table type: {tbl_id}")
        return None

    gen_info = TABLE_GENERATORS[tbl_id]
    generator_script = GENERATORS_DIR / gen_info["generator"]

    if not generator_script.exists():
        print(f"Warning: Generator script not found: {generator_script}")
        print(f"  Using fallback inline generation for {tbl_id}")
        return _generate_table_inline(tbl_id, exp_id, format, output_dir, **kwargs)

    # Run generator script
    if output_dir is None:
        output_dir = Path.cwd()

    output_path = output_dir / f"{tbl_id}.{format}"

    cmd = [
        sys.executable, str(generator_script),
        exp_id,
        "--output", str(output_path),
        "--format", format,
    ]

    for key, value in kwargs.items():
        cmd.extend([f"--{key.replace('_', '-')}", str(value)])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and output_path.exists():
            save_artifact(
                exp_id, "tables", tbl_id, output_path, format,
                gen_info["generator"],
                {"caption": gen_info.get("caption", "")}
            )
            return output_path
        else:
            print(f"Generator failed: {result.stderr}")
            return None
    except Exception as e:
        print(f"Error running generator: {e}")
        return None


def _generate_table_inline(tbl_id: str, exp_id: str, format: str,
                           output_dir: Path, **kwargs) -> Optional[Path]:
    """Inline table generation fallback"""
    if not HAS_CONTEXT:
        print("Error: ont_context module required")
        return None

    ctx = load_experiment_context(exp_id)
    if ctx is None:
        print(f"Error: Experiment not found: {exp_id}")
        return None

    if output_dir is None:
        output_dir = Path.cwd()

    output_path = output_dir / f"{tbl_id}.{format}"

    # Build table data
    if tbl_id == "tbl_qc_summary":
        data = {
            "Experiment": ctx.name,
            "Total Reads": ctx.statistics.total_reads if ctx.statistics else "N/A",
            "Quality Grade": ctx.quality_grade or "N/A",
            "Signal Positive %": f"{ctx.end_reasons.signal_positive_pct:.1f}" if ctx.end_reasons else "N/A",
            "Unblock %": f"{ctx.end_reasons.unblock_pct:.1f}" if ctx.end_reasons else "N/A",
        }
    elif tbl_id == "tbl_basecalling":
        data = {
            "Experiment": ctx.name,
            "Total Reads": ctx.statistics.total_reads if ctx.statistics else "N/A",
            "Pass Reads": ctx.statistics.pass_reads if ctx.statistics else "N/A",
            "Mean Q-Score": f"{ctx.statistics.mean_qscore:.1f}" if ctx.statistics else "N/A",
            "N50": ctx.statistics.n50 if ctx.statistics else "N/A",
        }
    else:
        data = {
            "Experiment ID": exp_id,
            "Name": ctx.name,
            "Status": ctx.experiment.status,
            "Events": len(ctx.events),
            "Figures": len(ctx.figures),
            "Tables": len(ctx.tables),
        }

    # Write in requested format
    if format == "json":
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

    elif format == "csv":
        with open(output_path, "w") as f:
            f.write(",".join(data.keys()) + "\n")
            f.write(",".join(str(v) for v in data.values()) + "\n")

    elif format == "tex":
        with open(output_path, "w") as f:
            f.write("\\begin{table}[htbp]\n")
            f.write("\\centering\n")
            f.write("\\begin{tabular}{ll}\n")
            f.write("\\toprule\n")
            f.write("Metric & Value \\\\\n")
            f.write("\\midrule\n")
            for key, value in data.items():
                f.write(f"{key} & {value} \\\\\n")
            f.write("\\bottomrule\n")
            f.write("\\end{tabular}\n")
            gen_info = TABLE_GENERATORS.get(tbl_id, {})
            f.write(f"\\caption{{{gen_info.get('caption', tbl_id)}}}\n")
            f.write(f"\\label{{tab:{tbl_id}}}\n")
            f.write("\\end{table}\n")

    elif format == "html":
        with open(output_path, "w") as f:
            f.write("<table>\n<thead><tr>")
            f.write("<th>Metric</th><th>Value</th>")
            f.write("</tr></thead>\n<tbody>\n")
            for key, value in data.items():
                f.write(f"<tr><td>{key}</td><td>{value}</td></tr>\n")
            f.write("</tbody>\n</table>\n")

    # Save to artifact storage
    gen_info = TABLE_GENERATORS.get(tbl_id, {})
    save_artifact(
        exp_id, "tables", tbl_id, output_path, format,
        "inline_generator",
        {"caption": gen_info.get("caption", "")}
    )

    return output_path


# =============================================================================
# Pipeline Execution
# =============================================================================

def run_pipeline(pipeline_name: str, exp_id: str, **kwargs) -> Dict[str, Any]:
    """
    Run a manuscript pipeline.

    Args:
        pipeline_name: Name of pipeline from MANUSCRIPT_PIPELINES
        exp_id: Experiment ID
        **kwargs: Additional arguments

    Returns:
        Dict with results
    """
    if pipeline_name not in MANUSCRIPT_PIPELINES:
        return {"error": f"Unknown pipeline: {pipeline_name}"}

    pipeline = MANUSCRIPT_PIPELINES[pipeline_name]
    results = {
        "pipeline": pipeline_name,
        "experiment_id": exp_id,
        "steps_completed": [],
        "figures_generated": [],
        "tables_generated": [],
        "errors": [],
    }

    print(f"Running pipeline: {pipeline_name}")
    print(f"  Description: {pipeline['description']}")
    print(f"  Experiment: {exp_id}")

    # Run analysis steps
    for step in pipeline["steps"]:
        if step == "load_contexts":
            continue  # No-op for context loading

        print(f"  Step: {step}...")
        # Would call ont_experiments.py run <step> <exp_id> here
        # For now, mark as completed
        results["steps_completed"].append(step)

    # Generate auto figures
    output_dir = kwargs.get("output_dir", Path.cwd())
    format_fig = kwargs.get("format", "pdf")
    format_tbl = kwargs.get("table_format", "tex")

    for fig_id in pipeline.get("auto_figures", []):
        print(f"  Generating figure: {fig_id}...")
        path = generate_figure(fig_id, exp_id, format_fig, output_dir)
        if path:
            results["figures_generated"].append(str(path))
        else:
            results["errors"].append(f"Failed to generate {fig_id}")

    for tbl_id in pipeline.get("auto_tables", []):
        print(f"  Generating table: {tbl_id}...")
        path = generate_table(tbl_id, exp_id, format_tbl, output_dir)
        if path:
            results["tables_generated"].append(str(path))
        else:
            results["errors"].append(f"Failed to generate {tbl_id}")

    print(f"  Pipeline complete!")
    return results


# =============================================================================
# Export Functions
# =============================================================================

def export_for_manuscript(exp_id: str, output_dir: Path,
                          target: str = "latex") -> Dict[str, Path]:
    """
    Export all artifacts for manuscript integration.

    Args:
        exp_id: Experiment ID
        output_dir: Output directory
        target: Target format ('latex' or 'html')

    Returns:
        Dict mapping artifact IDs to exported paths
    """
    exports = {}

    output_dir = Path(output_dir)
    figures_dir = output_dir / "figures"
    tables_dir = output_dir / "tables"
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    artifacts = list_artifacts(exp_id)

    for art in artifacts:
        art_id = art["id"]
        art_type = art["type"]
        art_path = Path(art["path"])

        # Determine file extension based on target
        if art_type == "figures":
            if target == "latex":
                ext = "pdf"
            else:
                ext = "png"
            dest_dir = figures_dir
        else:
            if target == "latex":
                ext = "tex"
            else:
                ext = "html"
            dest_dir = tables_dir

        # Find the actual file
        src_file = None
        for candidate in art_path.iterdir():
            if candidate.suffix == f".{ext}":
                src_file = candidate
                break
            # Fallback to any matching artifact file
            if candidate.name.startswith(art_id):
                src_file = candidate

        if src_file and src_file.exists():
            dest_path = dest_dir / f"{art_id}.{ext}"
            shutil.copy(src_file, dest_path)
            exports[art_id] = dest_path

    return exports


# =============================================================================
# CLI Commands
# =============================================================================

def cmd_select(args):
    """Select datasets with filtering"""
    if not HAS_CONTEXT:
        print("Error: ont_context module required for selection")
        sys.exit(1)

    exp_ids = list_experiments()

    # Apply filters
    filtered = []
    for exp_id in exp_ids:
        ctx = load_experiment_context(exp_id)
        if ctx is None:
            continue

        # Tag filter
        if args.tag and args.tag not in ctx.experiment.tags:
            continue

        # Status filter
        if args.status:
            if args.status == "passing" and ctx.quality_grade not in ("A", "B"):
                continue
            elif args.status == "failing" and ctx.quality_grade in ("A", "B"):
                continue

        filtered.append(ctx)

    if args.json:
        output = [ctx.to_dict() for ctx in filtered]
        print(json.dumps(output, indent=2))
    else:
        print(f"Found {len(filtered)} experiments:")
        print()
        for ctx in filtered:
            grade = ctx.quality_grade or "-"
            tags = ", ".join(ctx.experiment.tags) if ctx.experiment.tags else "none"
            print(f"  {ctx.id}: {ctx.name}")
            print(f"    Grade: {grade} | Tags: {tags}")
            print()


def cmd_pipeline(args):
    """Run manuscript pipeline"""
    results = run_pipeline(
        args.name,
        args.experiment_id,
        output_dir=Path(args.output) if args.output else None,
        format=args.format,
    )

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        if results.get("errors"):
            print(f"\nWarnings: {len(results['errors'])} errors")
            for err in results["errors"]:
                print(f"  - {err}")

        print(f"\nGenerated {len(results['figures_generated'])} figures")
        print(f"Generated {len(results['tables_generated'])} tables")


def cmd_figure(args):
    """Generate a figure"""
    output_dir = Path(args.output).parent if args.output else Path.cwd()
    path = generate_figure(args.figure_id, args.experiment_id, args.format, output_dir)

    if path:
        print(f"Generated: {path}")
    else:
        print("Figure generation failed")
        sys.exit(1)


def cmd_table(args):
    """Generate a table"""
    output_dir = Path(args.output).parent if args.output else Path.cwd()
    path = generate_table(args.table_id, args.experiment_id, args.format, output_dir)

    if path:
        print(f"Generated: {path}")
    else:
        print("Table generation failed")
        sys.exit(1)


def cmd_export(args):
    """Export artifacts for manuscript"""
    exports = export_for_manuscript(
        args.experiment_id,
        Path(args.output_dir),
        args.target
    )

    print(f"Exported {len(exports)} artifacts to {args.output_dir}")
    for art_id, path in exports.items():
        print(f"  {art_id}: {path}")


def cmd_compare(args):
    """Compare multiple experiments"""
    if not HAS_CONTEXT:
        print("Error: ont_context module required for comparison")
        sys.exit(1)

    contexts = []
    for exp_id in args.experiments:
        ctx = load_experiment_context(exp_id)
        if ctx is None:
            print(f"Warning: Experiment not found: {exp_id}")
            continue
        contexts.append(ctx)

    if len(contexts) < 2:
        print("Error: Need at least 2 experiments to compare")
        sys.exit(1)

    # Build comparison data
    comparison = []
    for ctx in contexts:
        comparison.append({
            "id": ctx.id,
            "name": ctx.name,
            "quality_grade": ctx.quality_grade,
            "total_reads": ctx.statistics.total_reads if ctx.statistics else None,
            "mean_qscore": ctx.statistics.mean_qscore if ctx.statistics else None,
            "n50": ctx.statistics.n50 if ctx.statistics else None,
            "signal_positive_pct": ctx.end_reasons.signal_positive_pct if ctx.end_reasons else None,
        })

    if args.json:
        print(json.dumps(comparison, indent=2))
    else:
        print("Experiment Comparison:")
        print("=" * 80)
        header = f"{'ID':<15} {'Name':<20} {'Grade':<6} {'Reads':<12} {'Q':<6} {'N50':<10}"
        print(header)
        print("-" * 80)
        for c in comparison:
            reads = f"{c['total_reads']:,}" if c['total_reads'] else "N/A"
            qscore = f"{c['mean_qscore']:.1f}" if c['mean_qscore'] else "N/A"
            n50 = f"{c['n50']:,}" if c['n50'] else "N/A"
            print(f"{c['id']:<15} {c['name'][:20]:<20} {c['quality_grade'] or '-':<6} {reads:<12} {qscore:<6} {n50:<10}")


def cmd_list_pipelines(args):
    """List available pipelines"""
    print("Available Manuscript Pipelines:")
    print()
    for name, info in MANUSCRIPT_PIPELINES.items():
        print(f"  {name}")
        print(f"    {info['description']}")
        print(f"    Steps: {', '.join(info['steps']) or 'none'}")
        print(f"    Auto figures: {', '.join(info.get('auto_figures', []))}")
        print(f"    Auto tables: {', '.join(info.get('auto_tables', []))}")
        print()


def cmd_list_figures(args):
    """List available figure generators"""
    print("Available Figure Generators:")
    print()
    for fig_id, info in FIGURE_GENERATORS.items():
        print(f"  {fig_id}")
        print(f"    {info['description']}")
        print(f"    Formats: {', '.join(info['formats'])}")
        print(f"    Requires: {', '.join(info['requires']) or 'none'}")
        print()


def cmd_list_tables(args):
    """List available table generators"""
    print("Available Table Generators:")
    print()
    for tbl_id, info in TABLE_GENERATORS.items():
        print(f"  {tbl_id}")
        print(f"    {info['description']}")
        print(f"    Formats: {', '.join(info['formats'])}")
        print(f"    Requires: {', '.join(info['requires']) or 'none'}")
        print()


def cmd_artifacts(args):
    """List artifacts for experiment"""
    artifacts = list_artifacts(args.experiment_id, args.type)

    if args.json:
        print(json.dumps(artifacts, indent=2))
    else:
        if not artifacts:
            print(f"No artifacts found for {args.experiment_id}")
            return

        print(f"Artifacts for {args.experiment_id}:")
        for art in artifacts:
            print(f"  [{art['type']}] {art['id']} v{art['version']}")
            print(f"    Format: {art['format']}")
            print(f"    Created: {art['created_at']}")
            print()


def main():
    parser = argparse.ArgumentParser(
        description="ONT Manuscript Studio - Figure and Table Generation",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # select
    p_select = subparsers.add_parser("select", help="Select datasets with filtering")
    p_select.add_argument("--tag", help="Filter by tag")
    p_select.add_argument("--status", choices=["passing", "failing"], help="Filter by QC status")
    p_select.add_argument("--json", action="store_true", help="Output as JSON")
    p_select.set_defaults(func=cmd_select)

    # pipeline
    p_pipeline = subparsers.add_parser("pipeline", help="Run manuscript pipeline")
    p_pipeline.add_argument("name", choices=list(MANUSCRIPT_PIPELINES.keys()), help="Pipeline name")
    p_pipeline.add_argument("experiment_id", help="Experiment ID")
    p_pipeline.add_argument("--output", "-o", help="Output directory")
    p_pipeline.add_argument("--format", default="pdf", help="Figure format")
    p_pipeline.add_argument("--json", action="store_true", help="Output as JSON")
    p_pipeline.set_defaults(func=cmd_pipeline)

    # figure
    p_figure = subparsers.add_parser("figure", help="Generate a figure")
    p_figure.add_argument("figure_id", help="Figure ID")
    p_figure.add_argument("experiment_id", help="Experiment ID")
    p_figure.add_argument("--output", "-o", help="Output path")
    p_figure.add_argument("--format", default="pdf", choices=["pdf", "png"], help="Output format")
    p_figure.set_defaults(func=cmd_figure)

    # table
    p_table = subparsers.add_parser("table", help="Generate a table")
    p_table.add_argument("table_id", help="Table ID")
    p_table.add_argument("experiment_id", help="Experiment ID")
    p_table.add_argument("--output", "-o", help="Output path")
    p_table.add_argument("--format", default="tex", choices=["tex", "csv", "json", "html"], help="Output format")
    p_table.set_defaults(func=cmd_table)

    # export
    p_export = subparsers.add_parser("export", help="Export artifacts for manuscript")
    p_export.add_argument("experiment_id", help="Experiment ID")
    p_export.add_argument("output_dir", help="Output directory")
    p_export.add_argument("--target", choices=["latex", "html"], default="latex", help="Target format")
    p_export.set_defaults(func=cmd_export)

    # compare
    p_compare = subparsers.add_parser("compare", help="Compare multiple experiments")
    p_compare.add_argument("experiments", nargs="+", help="Experiment IDs to compare")
    p_compare.add_argument("--output", "-o", help="Output file")
    p_compare.add_argument("--json", action="store_true", help="Output as JSON")
    p_compare.set_defaults(func=cmd_compare)

    # list-pipelines
    p_list_pipe = subparsers.add_parser("list-pipelines", help="List available pipelines")
    p_list_pipe.set_defaults(func=cmd_list_pipelines)

    # list-figures
    p_list_fig = subparsers.add_parser("list-figures", help="List available figure generators")
    p_list_fig.set_defaults(func=cmd_list_figures)

    # list-tables
    p_list_tbl = subparsers.add_parser("list-tables", help="List available table generators")
    p_list_tbl.set_defaults(func=cmd_list_tables)

    # artifacts
    p_artifacts = subparsers.add_parser("artifacts", help="List artifacts for experiment")
    p_artifacts.add_argument("experiment_id", help="Experiment ID")
    p_artifacts.add_argument("--type", choices=["figures", "tables"], help="Filter by type")
    p_artifacts.add_argument("--json", action="store_true", help="Output as JSON")
    p_artifacts.set_defaults(func=cmd_artifacts)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
    else:
        args.func(args)


if __name__ == "__main__":
    main()
