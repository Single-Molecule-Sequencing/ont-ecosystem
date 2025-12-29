#!/usr/bin/env python3
"""
ONT Ecosystem Help - Show all available commands and quick reference

Usage:
    ont_help.py              # Show all commands
    ont_help.py <command>    # Show help for specific command
    ont_help.py --examples   # Show common usage examples
"""

import argparse
import sys
from pathlib import Path

# Add paths
bin_dir = Path(__file__).parent
lib_dir = bin_dir.parent / 'lib'
sys.path.insert(0, str(bin_dir))
sys.path.insert(0, str(lib_dir.parent))

try:
    from lib import __version__
except ImportError:
    __version__ = "3.0.0"


# Command registry
COMMANDS = {
    "Core Commands": {
        "ont_experiments.py": {
            "description": "Main orchestrator - register, discover, run analyses",
            "examples": [
                "ont_experiments.py init --git",
                "ont_experiments.py discover /path/to/data --register",
                "ont_experiments.py run end_reasons exp-abc123",
                "ont_experiments.py history exp-abc123",
            ]
        },
        "ont_pipeline.py": {
            "description": "Run multi-step analysis pipelines",
            "examples": [
                "ont_pipeline.py run pharmaco-clinical exp-abc123",
                "ont_pipeline.py list",
                "ont_pipeline.py resume exp-abc123",
            ]
        },
        "ont_manuscript.py": {
            "description": "Generate figures and tables for manuscripts",
            "examples": [
                "ont_manuscript.py list-figures",
                "ont_manuscript.py figure fig_end_reason_kde exp-abc123",
                "ont_manuscript.py export exp-abc123 ./paper --target latex",
            ]
        },
    },
    "Analysis Commands": {
        "end_reason.py": {
            "description": "Analyze read end reasons (QC)",
            "examples": [
                "end_reason.py /path/to/pod5 --json results.json",
                "end_reason.py /path/to/bam --plot qc.png",
            ]
        },
        "ont_align.py": {
            "description": "Alignment and edit distance calculations",
            "examples": [
                "ont_align.py editdist ACGT ACTT --cigar",
                "ont_align.py align reads.fastq --ref GRCh38 --output aligned.bam",
            ]
        },
        "dorado_basecall.py": {
            "description": "Basecalling with Dorado",
            "examples": [
                "dorado_basecall.py /path/to/pod5 --model sup@v5.0.0 --output calls.bam",
                "dorado_basecall.py /path/to/pod5 --slurm job.sh --partition spgpu",
            ]
        },
        "ont_monitor.py": {
            "description": "Monitor sequencing runs",
            "examples": [
                "ont_monitor.py /path/to/run --live --interval 60",
                "ont_monitor.py /path/to/run --plot metrics.png",
            ]
        },
    },
    "Utility Commands": {
        "ont_stats.py": {
            "description": "Show ecosystem statistics",
            "examples": [
                "ont_stats.py",
                "ont_stats.py --brief",
                "ont_stats.py --json",
            ]
        },
        "ont_check.py": {
            "description": "Validate installation and dependencies",
            "examples": [
                "ont_check.py",
                "ont_check.py --json",
            ]
        },
        "ont_update.py": {
            "description": "Check for and apply updates",
            "examples": [
                "ont_update.py",
                "ont_update.py --apply",
                "ont_update.py --status",
            ]
        },
        "ont_backup.py": {
            "description": "Backup and restore registry data",
            "examples": [
                "ont_backup.py create",
                "ont_backup.py list",
                "ont_backup.py restore backup.tar.gz",
            ]
        },
        "ont_doctor.py": {
            "description": "Diagnose issues and suggest fixes",
            "examples": [
                "ont_doctor.py",
                "ont_doctor.py --fix",
                "ont_doctor.py --quick",
                "ont_doctor.py --json",
            ]
        },
        "ont_context.py": {
            "description": "Unified experiment context and equation execution",
            "examples": [
                "ont_context.py load exp-abc123",
                "ont_context.py compute QC.signal_positive_pct exp-abc123",
            ]
        },
        "experiment_db.py": {
            "description": "Database operations for experiments",
            "examples": [
                "experiment_db.py find --tag cyp2d6",
                "experiment_db.py stats",
            ]
        },
    },
    "HPC Commands": {
        "calculate_resources.py": {
            "description": "Calculate GPU/memory resources for basecalling",
            "examples": [
                "calculate_resources.py /path/to/pod5 --model sup@v5.0.0",
            ]
        },
        "make_sbatch_from_cmdtxt.py": {
            "description": "Generate SLURM batch scripts",
            "examples": [
                "make_sbatch_from_cmdtxt.py commands.txt --partition spgpu",
            ]
        },
    },
}

EXAMPLES = """
# Initialize new experiment registry
ont_experiments.py init --git

# Discover experiments in a directory
ont_experiments.py discover /nfs/turbo/data/sequencing --register

# Run QC analysis with provenance tracking
ont_experiments.py run end_reasons exp-2024-001 --json qc.json --plot qc.png

# Run basecalling on HPC
ont_experiments.py run basecalling exp-2024-001 --model sup@v5.0.0 --output calls.bam

# Run complete clinical pipeline
ont_experiments.py pipeline run pharmaco-clinical exp-2024-001

# Generate figures for manuscript
ont_manuscript.py figure fig_end_reason_kde exp-2024-001 --format pdf

# Export all artifacts for paper
ont_manuscript.py export exp-2024-001 ./paper_figures --target latex

# Check ecosystem health
ont_check.py

# View statistics
ont_stats.py --brief

# Compare two experiments
ont_manuscript.py compare exp-001 exp-002 --output comparison
"""


def print_all_commands():
    """Print all available commands"""
    print("=" * 70)
    print(f"  ONT Ecosystem v{__version__} - Command Reference")
    print("=" * 70)
    print()

    for category, commands in COMMANDS.items():
        print(f"{category}")
        print("-" * len(category))
        for cmd, info in commands.items():
            print(f"  {cmd:30} {info['description']}")
        print()

    print("=" * 70)
    print("  Use 'ont_help.py <command>' for detailed help")
    print("  Use 'ont_help.py --examples' for common usage examples")
    print("=" * 70)


def print_command_help(command: str):
    """Print help for a specific command"""
    # Normalize command name
    if not command.endswith('.py'):
        command = command + '.py'
    command = command.replace('-', '_')

    # Find command
    found = None
    for category, commands in COMMANDS.items():
        if command in commands:
            found = (category, command, commands[command])
            break

    if not found:
        print(f"Unknown command: {command}")
        print("Use 'ont_help.py' to see all available commands")
        return

    category, cmd, info = found

    print("=" * 70)
    print(f"  {cmd}")
    print("=" * 70)
    print()
    print(f"Category: {category}")
    print(f"Description: {info['description']}")
    print()
    print("Examples:")
    for example in info['examples']:
        print(f"  $ {example}")
    print()

    # Try to run --help on the actual command
    cmd_path = bin_dir / cmd
    if cmd_path.exists():
        print("-" * 70)
        print("Full help (from --help):")
        print("-" * 70)
        import subprocess
        try:
            result = subprocess.run(
                [sys.executable, str(cmd_path), '--help'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(result.stdout)
            else:
                print(result.stderr or "(no help available)")
        except Exception as e:
            print(f"(could not get help: {e})")


def print_examples():
    """Print common usage examples"""
    print("=" * 70)
    print(f"  ONT Ecosystem v{__version__} - Common Examples")
    print("=" * 70)
    print(EXAMPLES)


def main():
    parser = argparse.ArgumentParser(
        description="ONT Ecosystem Help",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("command", nargs="?", help="Command to get help for")
    parser.add_argument("--examples", action="store_true", help="Show common examples")
    parser.add_argument("--version", action="store_true", help="Show version")
    args = parser.parse_args()

    if args.version:
        print(f"ONT Ecosystem v{__version__}")
        return

    if args.examples:
        print_examples()
        return

    if args.command:
        print_command_help(args.command)
    else:
        print_all_commands()


if __name__ == "__main__":
    main()
