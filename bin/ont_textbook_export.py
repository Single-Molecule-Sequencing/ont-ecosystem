#!/usr/bin/env python3
"""
ONT Textbook Export - Export Artifacts to SMS_textbook Format

Exports experiment figures and tables to the SMS Haplotype Framework Textbook
repository format with versioned directories.

Part of: https://github.com/Single-Molecule-Sequencing/ont-ecosystem

Usage:
    ont_textbook_export.py <experiment_id> <textbook_dir>
    ont_textbook_export.py exp-abc123 /mnt/d/repos/SMS_textbook
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Optional imports
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Try to import context module
try:
    from ont_context import load_experiment_context, list_experiments
    HAS_CONTEXT = True
except ImportError:
    HAS_CONTEXT = False

# Try to import manuscript module
try:
    from ont_manuscript import list_artifacts, ARTIFACTS_DIR
    HAS_MANUSCRIPT = True
except ImportError:
    HAS_MANUSCRIPT = False
    ARTIFACTS_DIR = Path.home() / ".ont-manuscript" / "artifacts"

# Try to import config module
try:
    from ont_config import load_config
    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False


# =============================================================================
# Textbook Directory Structure
# =============================================================================

TEXTBOOK_STRUCTURE = """
SMS_textbook/
├── figures/
│   ├── fig_end_reason_kde/
│   │   ├── v1/
│   │   │   ├── fig_end_reason_kde.pdf
│   │   │   └── metadata.yaml
│   │   └── latest -> v1
│   └── fig_quality_dist/
└── tables/
    └── tbl_qc_summary/
        ├── v1/
        │   ├── tbl_qc_summary.tex
        │   └── metadata.yaml
        └── latest -> v1
"""


# =============================================================================
# Export Functions
# =============================================================================

def get_textbook_dir() -> Path:
    """Get textbook directory from config or common locations"""
    # Try config file first
    if HAS_CONFIG:
        config = load_config()
        if config.paths.textbook_dir:
            return Path(config.paths.textbook_dir)

    # Check internal textbook first (consolidated monorepo)
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    internal_textbook = repo_root / "textbook"

    if internal_textbook.exists() and (internal_textbook / "equations.yaml").exists():
        return internal_textbook

    # Fallback to external locations (legacy)
    common_paths = [
        Path("/mnt/d/repos/SMS_textbook"),
        Path("/mnt/d/Google_Drive_umich/SMS_textbook"),
        Path.home() / "repos" / "SMS_textbook",
        Path.home() / "SMS_textbook",
    ]

    for p in common_paths:
        if p.exists() and (p / "equations.yaml").exists():
            return p

    return None


def get_next_version(artifact_dir: Path) -> int:
    """Get next version number for artifact in textbook"""
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


def export_figure(fig_path: Path, fig_id: str, textbook_dir: Path,
                  experiment_id: str, metadata: dict = None) -> Path:
    """
    Export a figure to textbook format.

    Args:
        fig_path: Path to figure file
        fig_id: Figure identifier
        textbook_dir: Textbook root directory
        experiment_id: Source experiment ID
        metadata: Additional metadata

    Returns:
        Path to exported figure
    """
    figures_dir = textbook_dir / "figures" / fig_id
    version = get_next_version(figures_dir)
    version_dir = figures_dir / f"v{version}"
    version_dir.mkdir(parents=True, exist_ok=True)

    # Copy figure
    ext = fig_path.suffix or ".pdf"
    dest_path = version_dir / f"{fig_id}{ext}"
    shutil.copy(fig_path, dest_path)

    # Create metadata
    meta = {
        "id": fig_id,
        "version": version,
        "experiment_id": experiment_id,
        "source": str(fig_path),
        "exported_at": datetime.now().isoformat(),
        "format": ext.lstrip("."),
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

    # Update latest symlink
    latest_link = figures_dir / "latest"
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    latest_link.symlink_to(f"v{version}")

    return dest_path


def export_table(tbl_path: Path, tbl_id: str, textbook_dir: Path,
                 experiment_id: str, metadata: dict = None) -> Path:
    """
    Export a table to textbook format.

    Args:
        tbl_path: Path to table file
        tbl_id: Table identifier
        textbook_dir: Textbook root directory
        experiment_id: Source experiment ID
        metadata: Additional metadata

    Returns:
        Path to exported table
    """
    tables_dir = textbook_dir / "tables" / tbl_id
    version = get_next_version(tables_dir)
    version_dir = tables_dir / f"v{version}"
    version_dir.mkdir(parents=True, exist_ok=True)

    # Copy table
    ext = tbl_path.suffix or ".tex"
    dest_path = version_dir / f"{tbl_id}{ext}"
    shutil.copy(tbl_path, dest_path)

    # Create metadata
    meta = {
        "id": tbl_id,
        "version": version,
        "experiment_id": experiment_id,
        "source": str(tbl_path),
        "exported_at": datetime.now().isoformat(),
        "format": ext.lstrip("."),
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

    # Update latest symlink
    latest_link = tables_dir / "latest"
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    latest_link.symlink_to(f"v{version}")

    return dest_path


def export_experiment_to_textbook(experiment_id: str, textbook_dir: Path,
                                  figure_format: str = "pdf",
                                  table_format: str = "tex") -> dict:
    """
    Export all artifacts for an experiment to textbook.

    Args:
        experiment_id: Experiment ID
        textbook_dir: Textbook root directory
        figure_format: Preferred figure format
        table_format: Preferred table format

    Returns:
        Dict with export results
    """
    results = {
        "experiment_id": experiment_id,
        "textbook_dir": str(textbook_dir),
        "figures_exported": [],
        "tables_exported": [],
        "errors": [],
    }

    # Get artifacts from manuscript storage
    exp_artifacts_dir = ARTIFACTS_DIR / experiment_id

    if not exp_artifacts_dir.exists():
        results["errors"].append(f"No artifacts found for {experiment_id}")
        return results

    # Export figures
    figures_dir = exp_artifacts_dir / "figures"
    if figures_dir.exists():
        for fig_dir in figures_dir.iterdir():
            if not fig_dir.is_dir():
                continue

            fig_id = fig_dir.name
            latest = fig_dir / "latest"

            if not latest.exists():
                continue

            # Find figure file with preferred format
            fig_file = None
            for candidate in latest.iterdir():
                if candidate.suffix == f".{figure_format}":
                    fig_file = candidate
                    break
                if candidate.name.startswith(fig_id) and candidate.suffix in (".pdf", ".png"):
                    fig_file = candidate

            if fig_file:
                try:
                    # Load metadata
                    meta = {}
                    meta_file = latest / "metadata.yaml"
                    if not meta_file.exists():
                        meta_file = latest / "metadata.json"
                    if meta_file.exists():
                        if HAS_YAML and meta_file.suffix == ".yaml":
                            with open(meta_file) as f:
                                meta = yaml.safe_load(f) or {}
                        else:
                            with open(meta_file) as f:
                                meta = json.load(f)

                    exported = export_figure(fig_file, fig_id, textbook_dir, experiment_id, meta)
                    results["figures_exported"].append({
                        "id": fig_id,
                        "path": str(exported),
                    })
                except Exception as e:
                    results["errors"].append(f"Failed to export {fig_id}: {e}")

    # Export tables
    tables_dir = exp_artifacts_dir / "tables"
    if tables_dir.exists():
        for tbl_dir in tables_dir.iterdir():
            if not tbl_dir.is_dir():
                continue

            tbl_id = tbl_dir.name
            latest = tbl_dir / "latest"

            if not latest.exists():
                continue

            # Find table file with preferred format
            tbl_file = None
            for candidate in latest.iterdir():
                if candidate.suffix == f".{table_format}":
                    tbl_file = candidate
                    break
                if candidate.name.startswith(tbl_id) and candidate.suffix in (".tex", ".csv", ".json"):
                    tbl_file = candidate

            if tbl_file:
                try:
                    # Load metadata
                    meta = {}
                    meta_file = latest / "metadata.yaml"
                    if not meta_file.exists():
                        meta_file = latest / "metadata.json"
                    if meta_file.exists():
                        if HAS_YAML and meta_file.suffix == ".yaml":
                            with open(meta_file) as f:
                                meta = yaml.safe_load(f) or {}
                        else:
                            with open(meta_file) as f:
                                meta = json.load(f)

                    exported = export_table(tbl_file, tbl_id, textbook_dir, experiment_id, meta)
                    results["tables_exported"].append({
                        "id": tbl_id,
                        "path": str(exported),
                    })
                except Exception as e:
                    results["errors"].append(f"Failed to export {tbl_id}: {e}")

    return results


def export_all_experiments(textbook_dir: Path, **kwargs) -> dict:
    """Export artifacts from all experiments to textbook"""
    if not HAS_CONTEXT:
        return {"error": "ont_context module required"}

    exp_ids = list_experiments()
    results = {
        "experiments": [],
        "total_figures": 0,
        "total_tables": 0,
        "total_errors": 0,
    }

    for exp_id in exp_ids:
        exp_result = export_experiment_to_textbook(exp_id, textbook_dir, **kwargs)
        results["experiments"].append(exp_result)
        results["total_figures"] += len(exp_result.get("figures_exported", []))
        results["total_tables"] += len(exp_result.get("tables_exported", []))
        results["total_errors"] += len(exp_result.get("errors", []))

    return results


# =============================================================================
# CLI
# =============================================================================

def cmd_export(args):
    """Export experiment artifacts to textbook"""
    textbook_dir = Path(args.textbook_dir) if args.textbook_dir else get_textbook_dir()

    if textbook_dir is None:
        print("Error: Could not find textbook directory")
        print("Specify with: ont_textbook_export.py <exp_id> <textbook_dir>")
        print("Or configure: ont_config.py set paths.textbook_dir /path/to/SMS_textbook")
        sys.exit(1)

    if not textbook_dir.exists():
        print(f"Error: Textbook directory not found: {textbook_dir}")
        sys.exit(1)

    print(f"Exporting to: {textbook_dir}")

    if args.experiment_id == "all":
        results = export_all_experiments(
            textbook_dir,
            figure_format=args.figure_format,
            table_format=args.table_format
        )
        print(f"\nExported from {len(results['experiments'])} experiments:")
        print(f"  Figures: {results['total_figures']}")
        print(f"  Tables: {results['total_tables']}")
        if results['total_errors']:
            print(f"  Errors: {results['total_errors']}")
    else:
        results = export_experiment_to_textbook(
            args.experiment_id, textbook_dir,
            figure_format=args.figure_format,
            table_format=args.table_format
        )

        print(f"\nExported from {args.experiment_id}:")
        for fig in results.get("figures_exported", []):
            print(f"  [fig] {fig['id']} -> {fig['path']}")
        for tbl in results.get("tables_exported", []):
            print(f"  [tbl] {tbl['id']} -> {tbl['path']}")

        if results.get("errors"):
            print(f"\nErrors:")
            for err in results["errors"]:
                print(f"  - {err}")

    if args.json:
        print(json.dumps(results, indent=2))


def cmd_show_structure(args):
    """Show expected textbook structure"""
    print("SMS_textbook Directory Structure:")
    print(TEXTBOOK_STRUCTURE)


def cmd_list(args):
    """List available artifacts for export"""
    if not HAS_CONTEXT:
        print("Error: ont_context module required")
        sys.exit(1)

    exp_ids = list_experiments()
    print(f"Available experiments with artifacts:\n")

    for exp_id in exp_ids:
        exp_dir = ARTIFACTS_DIR / exp_id
        if exp_dir.exists():
            figures = list((exp_dir / "figures").iterdir()) if (exp_dir / "figures").exists() else []
            tables = list((exp_dir / "tables").iterdir()) if (exp_dir / "tables").exists() else []

            if figures or tables:
                print(f"  {exp_id}:")
                if figures:
                    print(f"    Figures: {', '.join(f.name for f in figures if f.is_dir())}")
                if tables:
                    print(f"    Tables: {', '.join(t.name for t in tables if t.is_dir())}")
                print()


def main():
    parser = argparse.ArgumentParser(
        description="Export ONT artifacts to SMS_textbook format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export single experiment
  ont_textbook_export.py exp-abc123 /mnt/d/repos/SMS_textbook

  # Export all experiments
  ont_textbook_export.py all /mnt/d/repos/SMS_textbook

  # List available artifacts
  ont_textbook_export.py --list
"""
    )

    parser.add_argument("experiment_id", nargs="?", default=None,
                       help="Experiment ID (or 'all' for all experiments)")
    parser.add_argument("textbook_dir", nargs="?", default=None,
                       help="Path to SMS_textbook repository")
    parser.add_argument("--figure-format", default="pdf", choices=["pdf", "png"],
                       help="Preferred figure format")
    parser.add_argument("--table-format", default="tex", choices=["tex", "csv", "json"],
                       help="Preferred table format")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--list", action="store_true", help="List available artifacts")
    parser.add_argument("--structure", action="store_true", help="Show textbook structure")

    args = parser.parse_args()

    if args.structure:
        cmd_show_structure(args)
    elif args.list:
        cmd_list(args)
    elif args.experiment_id:
        cmd_export(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
