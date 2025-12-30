#!/usr/bin/env python3
"""
End-Reason Manuscript - Data Processing Hub

Orchestrates data collection, analysis, and figure/table generation for
end-reason focused bioRxiv preprint.

Commands:
    init        Initialize manuscript directory structure
    fetch       Fetch data from internal/public sources
    analyze     Run analysis on all experiments
    generate    Generate figures and tables
    build       Build LaTeX manuscript
    pipeline    Run full pipeline (init + fetch + analyze + generate)

Usage:
    endreason_manuscript.py init --output manuscript/endreason/
    endreason_manuscript.py fetch --internal --public
    endreason_manuscript.py analyze --all
    endreason_manuscript.py generate --figures --tables
    endreason_manuscript.py build --latex
    endreason_manuscript.py pipeline --output manuscript/endreason/

Part of: https://github.com/Single-Molecule-Sequencing/ont-ecosystem
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Import data hub
from data_hub import (
    load_internal_experiments,
    load_public_experiments,
    load_physical_sizes,
    merge_data_sources,
    compute_comparison_matrix,
    classify_adaptive_status,
    export_merged_data,
)

# Optional imports
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR = Path(__file__).parent
GENERATORS_DIR = SCRIPT_DIR.parent / "generators"
BIN_DIR = SCRIPT_DIR.parent.parent.parent / "bin"

# Default output directory
DEFAULT_OUTPUT_DIR = Path("manuscript/endreason")

# Directory structure template
DIRECTORY_STRUCTURE = {
    "data": {
        "internal": {},
        "public": {},
        "physical": {},
        "merged": {},
    },
    "figures": {},
    "tables": {},
    "text": {},
    "supplementary": {
        "supp_figures": {},
    },
    "submission": {
        "biorxiv": {},
    },
    "scripts": {},
}

# Figure generators available (in priority order)
FIGURE_GENERATORS = [
    "gen_adaptive_efficiency.py",     # Adaptive vs non-adaptive comparison
    "gen_endreason_breakdown.py",     # Detailed per-end-reason analysis
    "gen_channel_analysis.py",        # Channel-level heatmaps
    "gen_library_quality.py",         # Library quality assessment
    # "gen_read_vs_physical.py",      # Deferred - needs physical size data
    # "gen_multi_experiment.py",      # Future - multi-experiment grid
]

# Table generators available
TABLE_GENERATORS = [
    "gen_endreason_summary_table.py",   # Per-end-reason statistics
    "gen_adaptive_metrics_table.py",    # Adaptive sampling efficiency
]


# =============================================================================
# Directory Initialization
# =============================================================================

def create_directory_structure(base_path: Path, structure: dict):
    """Recursively create directory structure."""
    base_path.mkdir(parents=True, exist_ok=True)
    for name, substructure in structure.items():
        subpath = base_path / name
        subpath.mkdir(exist_ok=True)
        if substructure:
            create_directory_structure(subpath, substructure)


def init_manuscript_dir(output_dir: Path) -> bool:
    """
    Initialize manuscript directory structure.

    Creates:
    - data/{internal,public,physical,merged}/
    - figures/
    - tables/
    - text/
    - supplementary/
    - submission/
    - scripts/
    - README.md
    - INDEX.md
    """
    print(f"Initializing manuscript directory at {output_dir}")

    # Create directory structure
    create_directory_structure(output_dir, DIRECTORY_STRUCTURE)

    # Create README.md
    readme_content = f"""# End-Reason Manuscript

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Directory Structure

```
{output_dir.name}/
├── data/           # Source data
│   ├── internal/   # HPC experiments
│   ├── public/     # ONT Open Data
│   ├── physical/   # TapeStation/Bioanalyzer
│   └── merged/     # Combined datasets
├── figures/        # Generated figures (PDF, PNG)
├── tables/         # Generated tables (LaTeX, CSV)
├── text/           # Manuscript text sections
├── supplementary/  # Supplementary materials
├── submission/     # Final compiled outputs
└── scripts/        # Build scripts
```

## Commands

```bash
# Fetch data
endreason_manuscript.py fetch --internal --public

# Generate figures and tables
endreason_manuscript.py generate --figures --tables

# Build manuscript
endreason_manuscript.py build --latex
```

## Data Sources

- **Internal**: HPC experiments from registry
- **Public**: ONT Open Data S3 bucket
- **Physical**: TapeStation/Bioanalyzer (when available)
"""

    readme_path = output_dir / "README.md"
    readme_path.write_text(readme_content)
    print(f"  Created {readme_path}")

    # Create INDEX.md
    index_content = f"""# File Index

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Figures

| ID | Description | Path |
|----|-------------|------|
| fig_adaptive_efficiency | Adaptive vs non-adaptive comparison | figures/fig_adaptive_efficiency.pdf |
| fig_endreason_breakdown | Per-end-reason breakdown | figures/fig_endreason_breakdown.pdf |
| fig_channel_analysis | Channel-level heatmaps | figures/fig_channel_analysis.pdf |
| fig_library_quality | Library quality assessment | figures/fig_library_quality.pdf |
| fig_multi_experiment | Multi-experiment comparison | figures/fig_multi_experiment.pdf |

## Tables

| ID | Description | Path |
|----|-------------|------|
| tbl_endreason_summary | Per-end-reason statistics | tables/tbl_endreason_summary.tex |
| tbl_adaptive_metrics | Adaptive sampling efficiency | tables/tbl_adaptive_metrics.tex |

## Data Files

| File | Description |
|------|-------------|
| data/merged/all_experiments.json | Combined experiment data |
| data/merged/comparison_matrix.json | Cross-experiment metrics |
"""

    index_path = output_dir / "INDEX.md"
    index_path.write_text(index_content)
    print(f"  Created {index_path}")

    # Create placeholder build script
    build_script = output_dir / "scripts" / "build_all.sh"
    build_script.write_text("""#!/bin/bash
# Build all manuscript outputs

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MANUSCRIPT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Building manuscript in $MANUSCRIPT_DIR"

# Generate figures and tables
endreason_manuscript.py generate --figures --tables --output "$MANUSCRIPT_DIR"

# Compile LaTeX (if available)
if [ -f "$MANUSCRIPT_DIR/submission/main_manuscript.tex" ]; then
    cd "$MANUSCRIPT_DIR/submission"
    pdflatex main_manuscript.tex
    bibtex main_manuscript
    pdflatex main_manuscript.tex
    pdflatex main_manuscript.tex
fi

echo "Build complete"
""")
    build_script.chmod(0o755)
    print(f"  Created {build_script}")

    print(f"\nManuscript directory initialized at {output_dir}")
    return True


# =============================================================================
# Data Fetching
# =============================================================================

def fetch_internal_data(output_dir: Path) -> dict:
    """Fetch internal experiment data from registry."""
    print("Fetching internal experiment data...")

    experiments = load_internal_experiments()
    print(f"  Found {len(experiments)} internal experiments")

    # Filter to those with end-reason data
    with_end_reasons = [e for e in experiments if e.end_reasons]
    print(f"  {len(with_end_reasons)} have end-reason data")

    # Export to data/internal/
    internal_dir = output_dir / "data" / "internal"
    internal_dir.mkdir(parents=True, exist_ok=True)

    # Export experiment list
    experiments_file = internal_dir / "experiments.json"
    export_merged_data(with_end_reasons, experiments_file, format="json")
    print(f"  Exported to {experiments_file}")

    return {
        "total": len(experiments),
        "with_end_reasons": len(with_end_reasons),
        "output_file": str(experiments_file),
    }


def fetch_public_data(output_dir: Path, datasets: list = None) -> dict:
    """Fetch public ONT data."""
    print("Fetching public ONT data...")

    # Check if ont_public_data.py is available
    ont_public_data = BIN_DIR / "ont_public_data.py"
    if not ont_public_data.exists():
        # Try skills location
        ont_public_data = (
            SCRIPT_DIR.parent.parent / "ont-public-data" / "scripts" / "ont_public_data.py"
        )

    if ont_public_data.exists():
        print(f"  Using {ont_public_data}")
        # Run analyze-all to fetch public data
        public_dir = output_dir / "data" / "public"
        public_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable,
            str(ont_public_data),
            "analyze-all",
            "--output", str(public_dir),
            "--max-reads", "50000",
        ]

        if datasets:
            cmd.extend(["--datasets", ",".join(datasets)])

        print(f"  Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"  Warning: ont_public_data.py failed: {result.stderr}")
            return {"error": result.stderr}

        print(f"  Output: {public_dir}")
    else:
        print("  Warning: ont_public_data.py not found")
        print("  Loading from existing public data directory...")

    # Load whatever public data exists
    experiments = load_public_experiments(output_dir / "data" / "public")
    print(f"  Found {len(experiments)} public experiments")

    return {
        "total": len(experiments),
        "output_dir": str(output_dir / "data" / "public"),
    }


def fetch_physical_data(output_dir: Path) -> dict:
    """Fetch physical size data (placeholder)."""
    print("Fetching physical size data...")

    physical_dir = output_dir / "data" / "physical"
    physical_dir.mkdir(parents=True, exist_ok=True)

    # Check for existing data
    sizes = load_physical_sizes(physical_dir)

    if sizes:
        print(f"  Found {len(sizes)} physical size records")
    else:
        print("  No physical size data found (will be added later)")
        # Create placeholder file
        placeholder = physical_dir / "README.md"
        placeholder.write_text("""# Physical Size Data

Place TapeStation or Bioanalyzer CSV files here.

Expected format:
- tapestation/*.csv - TapeStation 4150 exports
- bioanalyzer/*.csv - Bioanalyzer 2100 exports

Once files are added, run:
```bash
endreason_manuscript.py fetch --physical
```
""")

    return {
        "total": len(sizes),
        "output_dir": str(physical_dir),
    }


# =============================================================================
# Analysis
# =============================================================================

def analyze_all(output_dir: Path) -> dict:
    """Run analysis on all experiments."""
    print("Analyzing all experiments...")

    # Load all data
    internal = load_internal_experiments()
    internal_with_er = [e for e in internal if e.end_reasons]

    public = load_public_experiments(output_dir / "data" / "public")

    physical = load_physical_sizes(output_dir / "data" / "physical")

    # Merge
    all_experiments = merge_data_sources(internal_with_er, public, physical)
    print(f"  Total experiments: {len(all_experiments)}")

    # Compute comparison matrix
    matrix = compute_comparison_matrix(all_experiments)
    print(f"  Summary: {matrix['summary']}")

    # Classify by adaptive status
    by_adaptive = classify_adaptive_status(all_experiments)
    print(f"  Adaptive: {len(by_adaptive['adaptive'])}")
    print(f"  Non-adaptive: {len(by_adaptive['non_adaptive'])}")

    # Export merged data
    merged_dir = output_dir / "data" / "merged"
    merged_dir.mkdir(parents=True, exist_ok=True)

    all_experiments_file = merged_dir / "all_experiments.json"
    export_merged_data(all_experiments, all_experiments_file)
    print(f"  Exported: {all_experiments_file}")

    matrix_file = merged_dir / "comparison_matrix.json"
    with open(matrix_file, "w") as f:
        json.dump(matrix, f, indent=2)
    print(f"  Exported: {matrix_file}")

    return {
        "total_experiments": len(all_experiments),
        "adaptive": len(by_adaptive["adaptive"]),
        "non_adaptive": len(by_adaptive["non_adaptive"]),
        "matrix": matrix["summary"],
    }


# =============================================================================
# Generation
# =============================================================================

def generate_figures(output_dir: Path, figures: list = None) -> dict:
    """Generate all figures."""
    print("Generating figures...")

    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Load merged data
    merged_file = output_dir / "data" / "merged" / "all_experiments.json"
    if not merged_file.exists():
        print("  Warning: No merged data found. Run 'analyze' first.")
        return {"error": "No merged data"}

    results = {"generated": [], "failed": []}

    for generator_name in FIGURE_GENERATORS:
        # Skip if not in filter
        fig_id = generator_name.replace("gen_", "").replace(".py", "")
        if figures and fig_id not in figures:
            continue

        generator_path = GENERATORS_DIR / generator_name

        if not generator_path.exists():
            print(f"  Skipping {generator_name} (not implemented yet)")
            results["failed"].append({"figure": fig_id, "reason": "not implemented"})
            continue

        print(f"  Generating {fig_id}...")

        output_file = figures_dir / f"fig_{fig_id}.pdf"

        cmd = [
            sys.executable,
            str(generator_path),
            "--input", str(merged_file),
            "--output", str(output_file),
            "--format", "pdf",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"    Created: {output_file}")
            results["generated"].append(str(output_file))
        else:
            print(f"    Failed: {result.stderr}")
            results["failed"].append({"figure": fig_id, "reason": result.stderr})

    return results


def generate_tables(output_dir: Path, tables: list = None) -> dict:
    """Generate all tables."""
    print("Generating tables...")

    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    # Load merged data
    merged_file = output_dir / "data" / "merged" / "all_experiments.json"
    if not merged_file.exists():
        print("  Warning: No merged data found. Run 'analyze' first.")
        return {"error": "No merged data"}

    results = {"generated": [], "failed": []}

    for generator_name in TABLE_GENERATORS:
        # Skip if not in filter
        tbl_id = generator_name.replace("gen_", "").replace("_table.py", "")
        if tables and tbl_id not in tables:
            continue

        generator_path = GENERATORS_DIR / generator_name

        if not generator_path.exists():
            print(f"  Skipping {generator_name} (not implemented yet)")
            results["failed"].append({"table": tbl_id, "reason": "not implemented"})
            continue

        print(f"  Generating {tbl_id}...")

        # Generate in multiple formats
        for fmt in ["tex", "csv", "json"]:
            output_file = tables_dir / f"tbl_{tbl_id}.{fmt}"

            cmd = [
                sys.executable,
                str(generator_path),
                "--input", str(merged_file),
                "--output", str(output_file),
                "--format", fmt,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"    Created: {output_file}")
                results["generated"].append(str(output_file))
            else:
                print(f"    Failed ({fmt}): {result.stderr}")
                results["failed"].append({"table": tbl_id, "format": fmt, "reason": result.stderr})

    return results


# =============================================================================
# Build
# =============================================================================

def build_latex(output_dir: Path) -> dict:
    """Build LaTeX manuscript."""
    print("Building LaTeX manuscript...")

    submission_dir = output_dir / "submission"

    main_tex = submission_dir / "main_manuscript.tex"
    if not main_tex.exists():
        print("  Warning: main_manuscript.tex not found")
        return {"error": "No main_manuscript.tex"}

    # Run pdflatex
    cmd = ["pdflatex", "-interaction=nonstopmode", str(main_tex)]
    result = subprocess.run(cmd, cwd=submission_dir, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  pdflatex failed: {result.stderr}")
        return {"error": result.stderr}

    # Run bibtex if bib file exists
    bib_file = submission_dir / "references.bib"
    if bib_file.exists():
        subprocess.run(
            ["bibtex", "main_manuscript"],
            cwd=submission_dir,
            capture_output=True,
        )
        subprocess.run(cmd, cwd=submission_dir, capture_output=True)
        subprocess.run(cmd, cwd=submission_dir, capture_output=True)

    pdf_file = submission_dir / "main_manuscript.pdf"
    if pdf_file.exists():
        print(f"  Created: {pdf_file}")
        return {"output": str(pdf_file)}

    return {"error": "PDF not generated"}


# =============================================================================
# Pipeline
# =============================================================================

def run_pipeline(output_dir: Path, datasets: list = None) -> dict:
    """Run full pipeline: init + fetch + analyze + generate."""
    print(f"Running full pipeline to {output_dir}")
    print("=" * 60)

    results = {}

    # 1. Initialize
    print("\n[1/4] Initializing...")
    init_manuscript_dir(output_dir)
    results["init"] = True

    # 2. Fetch data
    print("\n[2/4] Fetching data...")
    results["fetch_internal"] = fetch_internal_data(output_dir)
    results["fetch_public"] = fetch_public_data(output_dir, datasets)
    results["fetch_physical"] = fetch_physical_data(output_dir)

    # 3. Analyze
    print("\n[3/4] Analyzing...")
    results["analyze"] = analyze_all(output_dir)

    # 4. Generate
    print("\n[4/4] Generating outputs...")
    results["figures"] = generate_figures(output_dir)
    results["tables"] = generate_tables(output_dir)

    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print(f"Output directory: {output_dir}")

    return results


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="End-Reason Manuscript Data Processing Hub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Initialize manuscript directory
    endreason_manuscript.py init --output manuscript/endreason/

    # Fetch all data
    endreason_manuscript.py fetch --internal --public

    # Run analysis
    endreason_manuscript.py analyze --all

    # Generate figures and tables
    endreason_manuscript.py generate --figures --tables

    # Run full pipeline
    endreason_manuscript.py pipeline --output manuscript/endreason/
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # init command
    init_parser = subparsers.add_parser("init", help="Initialize manuscript directory")
    init_parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory (default: manuscript/endreason/)",
    )

    # fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch data from sources")
    fetch_parser.add_argument("--internal", action="store_true", help="Fetch internal HPC data")
    fetch_parser.add_argument("--public", action="store_true", help="Fetch public ONT data")
    fetch_parser.add_argument("--physical", action="store_true", help="Fetch physical size data")
    fetch_parser.add_argument(
        "--datasets",
        help="Comma-separated list of public datasets to fetch",
    )
    fetch_parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory",
    )

    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Run analysis")
    analyze_parser.add_argument("--all", action="store_true", help="Analyze all experiments")
    analyze_parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory",
    )

    # generate command
    generate_parser = subparsers.add_parser("generate", help="Generate figures and tables")
    generate_parser.add_argument("--figures", action="store_true", help="Generate figures")
    generate_parser.add_argument("--tables", action="store_true", help="Generate tables")
    generate_parser.add_argument("--figure", help="Generate specific figure")
    generate_parser.add_argument("--table", help="Generate specific table")
    generate_parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory",
    )

    # build command
    build_parser = subparsers.add_parser("build", help="Build manuscript")
    build_parser.add_argument("--latex", action="store_true", help="Build LaTeX PDF")
    build_parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory",
    )

    # pipeline command
    pipeline_parser = subparsers.add_parser("pipeline", help="Run full pipeline")
    pipeline_parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory",
    )
    pipeline_parser.add_argument(
        "--datasets",
        help="Comma-separated list of public datasets to fetch",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    if args.command == "init":
        init_manuscript_dir(args.output)

    elif args.command == "fetch":
        if args.internal:
            fetch_internal_data(args.output)
        if args.public:
            datasets = args.datasets.split(",") if args.datasets else None
            fetch_public_data(args.output, datasets)
        if args.physical:
            fetch_physical_data(args.output)
        if not (args.internal or args.public or args.physical):
            print("Specify --internal, --public, or --physical")
            return 1

    elif args.command == "analyze":
        analyze_all(args.output)

    elif args.command == "generate":
        if args.figures or args.figure:
            figures = [args.figure] if args.figure else None
            generate_figures(args.output, figures)
        if args.tables or args.table:
            tables = [args.table] if args.table else None
            generate_tables(args.output, tables)
        if not (args.figures or args.tables or args.figure or args.table):
            print("Specify --figures, --tables, --figure, or --table")
            return 1

    elif args.command == "build":
        if args.latex:
            build_latex(args.output)
        else:
            print("Specify --latex")
            return 1

    elif args.command == "pipeline":
        datasets = args.datasets.split(",") if args.datasets else None
        run_pipeline(args.output, datasets)

    return 0


if __name__ == "__main__":
    sys.exit(main())
