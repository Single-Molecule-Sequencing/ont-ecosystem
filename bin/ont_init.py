#!/usr/bin/env python3
"""
ONT Project Initialization Wizard

Creates new project directories with proper structure and configuration
for ONT sequencing analysis projects.

Usage:
    ont_init.py project my-project          # Create new project
    ont_init.py project my-project --full   # Full project with all directories
    ont_init.py experiment exp-001          # Initialize experiment structure
    ont_init.py config                      # Generate default configuration
    ont_init.py templates                   # List available templates
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from lib import __version__
except ImportError:
    __version__ = "unknown"


# =============================================================================
# Project Templates
# =============================================================================

TEMPLATES = {
    "minimal": {
        "description": "Minimal project structure for quick analysis",
        "directories": [
            "data/raw",
            "data/processed",
            "results",
            "scripts",
        ],
        "files": {
            "README.md": "readme_minimal",
            "config.yaml": "config_minimal",
            ".gitignore": "gitignore_standard",
        }
    },
    "standard": {
        "description": "Standard project structure for typical experiments",
        "directories": [
            "data/raw",
            "data/processed",
            "data/reference",
            "results/figures",
            "results/tables",
            "results/reports",
            "scripts",
            "logs",
        ],
        "files": {
            "README.md": "readme_standard",
            "config.yaml": "config_standard",
            ".gitignore": "gitignore_standard",
            "Makefile": "makefile_standard",
        }
    },
    "full": {
        "description": "Full project structure with all components",
        "directories": [
            "data/raw/pod5",
            "data/raw/fast5",
            "data/raw/fastq",
            "data/processed/bam",
            "data/processed/vcf",
            "data/reference/genome",
            "data/reference/annotations",
            "results/figures",
            "results/tables",
            "results/reports",
            "results/qc",
            "scripts/analysis",
            "scripts/pipeline",
            "scripts/utils",
            "logs",
            "notebooks",
            "docs",
            "tests",
        ],
        "files": {
            "README.md": "readme_full",
            "config.yaml": "config_full",
            ".gitignore": "gitignore_standard",
            "Makefile": "makefile_full",
            "pyproject.toml": "pyproject_template",
        }
    },
    "experiment": {
        "description": "Single experiment directory structure",
        "directories": [
            "raw",
            "processed",
            "results",
            "logs",
        ],
        "files": {
            "README.md": "readme_experiment",
            "metadata.yaml": "metadata_experiment",
        }
    },
}


# =============================================================================
# File Templates
# =============================================================================

FILE_TEMPLATES = {
    "readme_minimal": """# {project_name}

ONT sequencing analysis project.

## Quick Start

```bash
# Process data
ont_pipeline.py run --config config.yaml
```

## Structure

- `data/` - Raw and processed sequencing data
- `results/` - Analysis results
- `scripts/` - Custom analysis scripts

Created: {date}
""",

    "readme_standard": """# {project_name}

ONT sequencing analysis project.

## Overview

{description}

## Quick Start

```bash
# Configure environment
source ~/.ont-ecosystem/env.sh

# Run pipeline
ont_pipeline.py run --config config.yaml

# Generate report
ont_report.py --output results/reports/
```

## Project Structure

```
{project_name}/
├── data/
│   ├── raw/           # Raw sequencing data (POD5, FAST5)
│   ├── processed/     # Basecalled and aligned data
│   └── reference/     # Reference genomes and annotations
├── results/
│   ├── figures/       # Publication-ready figures
│   ├── tables/        # Summary tables
│   └── reports/       # Analysis reports
├── scripts/           # Custom analysis scripts
└── logs/              # Processing logs
```

## Configuration

Edit `config.yaml` to customize analysis parameters.

## Requirements

- ONT Ecosystem v{version}+
- Dorado basecaller
- Minimap2 aligner

Created: {date}
""",

    "readme_full": """# {project_name}

Comprehensive ONT sequencing analysis project.

## Overview

{description}

## Quick Start

```bash
# Setup
source ~/.ont-ecosystem/env.sh
pip install -e .

# Run full pipeline
make pipeline

# Generate manuscript figures
make figures
```

## Project Structure

```
{project_name}/
├── data/
│   ├── raw/           # Raw sequencing data
│   │   ├── pod5/      # POD5 signal files
│   │   ├── fast5/     # FAST5 signal files
│   │   └── fastq/     # FASTQ sequence files
│   ├── processed/     # Processed data
│   │   ├── bam/       # Aligned reads
│   │   └── vcf/       # Variant calls
│   └── reference/     # Reference data
├── results/
│   ├── figures/       # Publication figures
│   ├── tables/        # Summary tables
│   ├── reports/       # Analysis reports
│   └── qc/            # Quality control
├── scripts/           # Analysis scripts
├── notebooks/         # Jupyter notebooks
├── docs/              # Documentation
└── tests/             # Unit tests
```

## Usage

### Pipeline Execution
```bash
ont_pipeline.py run --config config.yaml
```

### Custom Analysis
```bash
python scripts/analysis/custom_analysis.py
```

### Manuscript Generation
```bash
ont_manuscript.py pipeline qc-report EXP-001
```

## Configuration

See `config.yaml` for all configurable parameters.

## Dependencies

- ONT Ecosystem v{version}+
- Dorado basecaller v0.5+
- Minimap2 v2.26+
- Samtools v1.18+

## License

{license}

Created: {date}
""",

    "readme_experiment": """# Experiment: {project_name}

## Overview

{description}

## Metadata

- **Date**: {date}
- **Flowcell**: {flowcell}
- **Sample**: {sample}
- **Protocol**: {protocol}

## Files

- `raw/` - Raw sequencing data
- `processed/` - Processed files
- `results/` - Analysis results
- `logs/` - Processing logs

## Analysis

```bash
# Run analysis
ont_experiments.py run end_reasons {project_name}
```
""",

    "config_minimal": """# ONT Project Configuration
# Project: {project_name}

project:
  name: {project_name}
  created: {date}

paths:
  data: ./data
  results: ./results

analysis:
  model: sup
  reference: null
""",

    "config_standard": """# ONT Project Configuration
# Project: {project_name}

project:
  name: {project_name}
  description: {description}
  created: {date}
  version: "1.0.0"

paths:
  data: ./data
  raw: ./data/raw
  processed: ./data/processed
  reference: ./data/reference
  results: ./results
  logs: ./logs

basecalling:
  model: sup
  device: auto
  batchsize: auto

alignment:
  reference: null
  preset: map-ont
  threads: 8

analysis:
  end_reasons: true
  signal_qc: true

output:
  formats: [json, csv]
  figures: true
""",

    "config_full": """# ONT Project Configuration
# Project: {project_name}

project:
  name: {project_name}
  description: {description}
  created: {date}
  version: "1.0.0"
  authors:
    - {author}

paths:
  data: ./data
  raw: ./data/raw
  processed: ./data/processed
  reference: ./data/reference
  results: ./results
  logs: ./logs
  notebooks: ./notebooks

basecalling:
  model: sup
  device: auto
  batchsize: auto
  modifications:
    - 5mCG_5hmCG

alignment:
  reference: null
  preset: map-ont
  threads: 8
  secondary: false

variant_calling:
  caller: clair3
  model: auto
  min_coverage: 10

analysis:
  end_reasons: true
  signal_qc: true
  methylation: true
  structural_variants: false

manuscript:
  auto_figures: true
  formats: [pdf, png]
  dpi: 300

pipeline:
  stages:
    - basecalling
    - alignment
    - analysis
  parallel: true
  max_jobs: 4

output:
  formats: [json, csv]
  figures: true
  latex_tables: true
""",

    "metadata_experiment": """# Experiment Metadata
id: {project_name}
date: {date}
status: pending

sample:
  name: null
  type: null
  source: null

sequencing:
  flowcell: null
  kit: null
  protocol: null
  device: null

analysis:
  model: sup
  reference: null

notes: |
  Add experiment notes here.
""",

    "gitignore_standard": """# ONT Ecosystem Project .gitignore

# Data files (typically large)
*.pod5
*.fast5
*.fastq
*.fastq.gz
*.fq.gz
*.bam
*.bam.bai
*.sam
*.vcf
*.vcf.gz

# Logs
logs/
*.log

# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Temporary files
*.tmp
*.temp
.cache/

# Results (optional - uncomment to track results)
# results/

# Jupyter
.ipynb_checkpoints/
""",

    "makefile_standard": """# Makefile for {project_name}

.PHONY: all pipeline clean help

# Default target
all: pipeline

# Run full pipeline
pipeline:
	ont_pipeline.py run --config config.yaml

# Run basecalling only
basecall:
	ont_pipeline.py run --config config.yaml --stage basecalling

# Run alignment only
align:
	ont_pipeline.py run --config config.yaml --stage alignment

# Run analysis
analyze:
	ont_pipeline.py run --config config.yaml --stage analysis

# Generate figures
figures:
	ont_manuscript.py pipeline qc-report .

# Clean temporary files
clean:
	rm -rf logs/*.log
	rm -rf __pycache__
	rm -rf .cache

# Deep clean (removes processed data)
clean-all: clean
	rm -rf data/processed/*
	rm -rf results/*

# Help
help:
	@echo "Available targets:"
	@echo "  pipeline   - Run full analysis pipeline"
	@echo "  basecall   - Run basecalling only"
	@echo "  align      - Run alignment only"
	@echo "  analyze    - Run analysis only"
	@echo "  figures    - Generate manuscript figures"
	@echo "  clean      - Remove temporary files"
	@echo "  clean-all  - Remove all generated files"
""",

    "makefile_full": """# Makefile for {project_name}

.PHONY: all pipeline test lint clean help

SHELL := /bin/bash
PYTHON := python3

# Default target
all: pipeline

# Run full pipeline
pipeline:
	ont_pipeline.py run --config config.yaml

# Run individual stages
basecall:
	ont_pipeline.py run --config config.yaml --stage basecalling

align:
	ont_pipeline.py run --config config.yaml --stage alignment

analyze:
	ont_pipeline.py run --config config.yaml --stage analysis

# QC and reporting
qc:
	ont_endreason_qc.py ./data/processed --output ./results/qc

figures:
	ont_manuscript.py pipeline full-analysis .

report:
	ont_report.py --format markdown --output ./results/reports/report.md

# Development
test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m flake8 scripts/ --max-line-length=100

# Cleanup
clean:
	rm -rf logs/*.log
	rm -rf __pycache__ */__pycache__
	rm -rf .cache .pytest_cache
	rm -rf *.egg-info

clean-results:
	rm -rf results/figures/*
	rm -rf results/tables/*
	rm -rf results/reports/*

clean-processed:
	rm -rf data/processed/*

clean-all: clean clean-results clean-processed

# Help
help:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  {project_name} - Makefile Targets"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "  Pipeline:"
	@echo "    pipeline     Run full analysis pipeline"
	@echo "    basecall     Basecalling stage only"
	@echo "    align        Alignment stage only"
	@echo "    analyze      Analysis stage only"
	@echo ""
	@echo "  Reporting:"
	@echo "    qc           Run QC analysis"
	@echo "    figures      Generate manuscript figures"
	@echo "    report       Generate project report"
	@echo ""
	@echo "  Development:"
	@echo "    test         Run unit tests"
	@echo "    lint         Run linter"
	@echo ""
	@echo "  Cleanup:"
	@echo "    clean        Remove temp files"
	@echo "    clean-all    Remove all generated files"
""",

    "pyproject_template": """[project]
name = "{project_name}"
version = "0.1.0"
description = "{description}"
requires-python = ">=3.9"
dependencies = [
    "numpy>=1.21",
    "pandas>=1.3",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "flake8>=5.0",
]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
""",
}


# =============================================================================
# Project Creation
# =============================================================================

def create_project(
    name: str,
    path: Optional[Path] = None,
    template: str = "standard",
    description: str = "",
    author: str = "",
    initialize_git: bool = True,
    force: bool = False
) -> Path:
    """Create a new project with the specified template."""

    if template not in TEMPLATES:
        raise ValueError(f"Unknown template: {template}. Available: {list(TEMPLATES.keys())}")

    project_path = (path or Path.cwd()) / name

    if project_path.exists() and not force:
        raise FileExistsError(f"Project directory already exists: {project_path}")

    tmpl = TEMPLATES[template]

    # Create project directory
    project_path.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    for dir_path in tmpl["directories"]:
        (project_path / dir_path).mkdir(parents=True, exist_ok=True)

    # Create files from templates
    template_vars = {
        "project_name": name,
        "description": description or f"ONT analysis project: {name}",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "version": __version__,
        "author": author or os.environ.get("USER", "Unknown"),
        "license": "Internal Use Only",
        "flowcell": "FLO-MIN114",
        "sample": "Unknown",
        "protocol": "Standard",
    }

    for filename, template_name in tmpl["files"].items():
        if template_name in FILE_TEMPLATES:
            content = FILE_TEMPLATES[template_name].format(**template_vars)
            (project_path / filename).write_text(content)

    # Initialize git repository
    if initialize_git:
        import subprocess
        subprocess.run(
            ["git", "init"],
            cwd=project_path,
            capture_output=True,
            check=False
        )

    return project_path


def create_experiment(
    exp_id: str,
    path: Optional[Path] = None,
    metadata: Optional[Dict[str, Any]] = None,
    force: bool = False
) -> Path:
    """Create an experiment directory structure."""

    exp_path = (path or Path.cwd()) / exp_id

    if exp_path.exists() and not force:
        raise FileExistsError(f"Experiment directory already exists: {exp_path}")

    tmpl = TEMPLATES["experiment"]

    # Create experiment directory
    exp_path.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    for dir_path in tmpl["directories"]:
        (exp_path / dir_path).mkdir(parents=True, exist_ok=True)

    # Create files
    template_vars = {
        "project_name": exp_id,
        "description": metadata.get("description", "") if metadata else "",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "flowcell": metadata.get("flowcell", "Unknown") if metadata else "Unknown",
        "sample": metadata.get("sample", "Unknown") if metadata else "Unknown",
        "protocol": metadata.get("protocol", "Standard") if metadata else "Standard",
    }

    for filename, template_name in tmpl["files"].items():
        if template_name in FILE_TEMPLATES:
            content = FILE_TEMPLATES[template_name].format(**template_vars)
            (exp_path / filename).write_text(content)

    return exp_path


def generate_config(
    config_type: str = "standard",
    project_name: str = "my-project",
    output: Optional[Path] = None
) -> str:
    """Generate a configuration file."""

    template_map = {
        "minimal": "config_minimal",
        "standard": "config_standard",
        "full": "config_full",
    }

    if config_type not in template_map:
        raise ValueError(f"Unknown config type: {config_type}")

    template_vars = {
        "project_name": project_name,
        "description": f"ONT analysis project: {project_name}",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "author": os.environ.get("USER", "Unknown"),
    }

    content = FILE_TEMPLATES[template_map[config_type]].format(**template_vars)

    if output:
        output.write_text(content)

    return content


# =============================================================================
# CLI Commands
# =============================================================================

def cmd_project(args):
    """Create a new project."""
    try:
        template = "full" if args.full else (args.template or "standard")

        project_path = create_project(
            name=args.name,
            path=Path(args.path) if args.path else None,
            template=template,
            description=args.description or "",
            author=args.author or "",
            initialize_git=not args.no_git,
            force=args.force
        )

        print(f"Created project: {project_path}")
        print(f"Template: {template}")
        print()
        print("Next steps:")
        print(f"  cd {project_path}")
        print("  # Add your data to data/raw/")
        print("  # Edit config.yaml")
        print("  # Run: ont_pipeline.py run --config config.yaml")

    except FileExistsError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Use --force to overwrite", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error creating project: {e}", file=sys.stderr)
        return 1

    return 0


def cmd_experiment(args):
    """Create an experiment directory."""
    try:
        metadata = {}
        if args.flowcell:
            metadata["flowcell"] = args.flowcell
        if args.sample:
            metadata["sample"] = args.sample
        if args.description:
            metadata["description"] = args.description

        exp_path = create_experiment(
            exp_id=args.exp_id,
            path=Path(args.path) if args.path else None,
            metadata=metadata if metadata else None,
            force=args.force
        )

        print(f"Created experiment: {exp_path}")
        print()
        print("Next steps:")
        print(f"  # Add data to {exp_path}/raw/")
        print(f"  # Edit {exp_path}/metadata.yaml")
        print(f"  # Register: ont_experiments.py register {exp_path}")

    except FileExistsError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Use --force to overwrite", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error creating experiment: {e}", file=sys.stderr)
        return 1

    return 0


def cmd_config(args):
    """Generate configuration file."""
    try:
        config_type = args.type or "standard"
        project_name = args.name or "my-project"

        content = generate_config(
            config_type=config_type,
            project_name=project_name,
            output=Path(args.output) if args.output else None
        )

        if args.output:
            print(f"Created config: {args.output}")
        else:
            print(content)

    except Exception as e:
        print(f"Error generating config: {e}", file=sys.stderr)
        return 1

    return 0


def cmd_templates(args):
    """List available templates."""

    if args.json:
        output = {
            name: {
                "description": tmpl["description"],
                "directories": tmpl["directories"],
                "files": list(tmpl["files"].keys())
            }
            for name, tmpl in TEMPLATES.items()
        }
        print(json.dumps(output, indent=2))
    else:
        print("Available Templates")
        print("=" * 50)
        print()

        for name, tmpl in TEMPLATES.items():
            print(f"  {name}")
            print(f"    {tmpl['description']}")
            print(f"    Directories: {len(tmpl['directories'])}")
            print(f"    Files: {', '.join(tmpl['files'].keys())}")
            print()

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="ONT Project Initialization Wizard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ont_init.py project my-project              # Standard project
  ont_init.py project my-project --full       # Full project structure
  ont_init.py project my-project -t minimal   # Minimal project
  ont_init.py experiment EXP-001              # Experiment directory
  ont_init.py config --type full              # Generate full config
  ont_init.py templates                       # List templates
"""
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Project command
    p_project = subparsers.add_parser("project", help="Create new project")
    p_project.add_argument("name", help="Project name")
    p_project.add_argument("--path", "-p", help="Parent directory (default: current)")
    p_project.add_argument("--template", "-t", choices=list(TEMPLATES.keys()),
                          help="Project template (default: standard)")
    p_project.add_argument("--full", action="store_true",
                          help="Use full template (shortcut for -t full)")
    p_project.add_argument("--description", "-d", help="Project description")
    p_project.add_argument("--author", "-a", help="Author name")
    p_project.add_argument("--no-git", action="store_true",
                          help="Don't initialize git repository")
    p_project.add_argument("--force", "-f", action="store_true",
                          help="Overwrite existing directory")
    p_project.set_defaults(func=cmd_project)

    # Experiment command
    p_exp = subparsers.add_parser("experiment", help="Create experiment directory")
    p_exp.add_argument("exp_id", help="Experiment ID")
    p_exp.add_argument("--path", "-p", help="Parent directory (default: current)")
    p_exp.add_argument("--flowcell", help="Flowcell ID")
    p_exp.add_argument("--sample", help="Sample name")
    p_exp.add_argument("--description", "-d", help="Experiment description")
    p_exp.add_argument("--force", "-f", action="store_true",
                      help="Overwrite existing directory")
    p_exp.set_defaults(func=cmd_experiment)

    # Config command
    p_config = subparsers.add_parser("config", help="Generate configuration file")
    p_config.add_argument("--type", "-t", choices=["minimal", "standard", "full"],
                         help="Config type (default: standard)")
    p_config.add_argument("--name", "-n", help="Project name")
    p_config.add_argument("--output", "-o", help="Output file path")
    p_config.set_defaults(func=cmd_config)

    # Templates command
    p_templates = subparsers.add_parser("templates", help="List available templates")
    p_templates.add_argument("--json", "-j", action="store_true",
                            help="Output as JSON")
    p_templates.set_defaults(func=cmd_templates)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
