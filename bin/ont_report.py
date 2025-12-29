#!/usr/bin/env python3
"""
ONT Ecosystem Report Generator - Generate project summary reports

Usage:
    ont_report.py                    # Generate text summary
    ont_report.py --format markdown  # Generate markdown report
    ont_report.py --format json      # Generate JSON report
    ont_report.py --output report.md # Save to file
"""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add paths
bin_dir = Path(__file__).parent
lib_dir = bin_dir.parent / 'lib'
sys.path.insert(0, str(bin_dir))
sys.path.insert(0, str(lib_dir.parent))

try:
    from lib import __version__
except ImportError:
    __version__ = "3.0.0"


@dataclass
class ReportSection:
    """A section of the report"""
    title: str
    items: Dict[str, Any] = field(default_factory=dict)
    subsections: List['ReportSection'] = field(default_factory=list)


class ReportGenerator:
    """Generate comprehensive project reports"""

    def __init__(self):
        self.ecosystem_home = Path(os.environ.get(
            "ONT_ECOSYSTEM_HOME",
            Path.home() / ".ont-ecosystem"
        ))
        self.registry_dir = Path(os.environ.get(
            "ONT_REGISTRY_DIR",
            Path.home() / ".ont-registry"
        ))

    def generate(self) -> Dict[str, Any]:
        """Generate complete project report data"""
        return {
            "metadata": self._get_metadata(),
            "ecosystem": self._get_ecosystem_info(),
            "experiments": self._get_experiment_summary(),
            "skills": self._get_skills_summary(),
            "generators": self._get_generators_summary(),
            "tests": self._get_test_summary(),
            "git": self._get_git_info(),
            "dependencies": self._get_dependencies_info(),
        }

    def _get_metadata(self) -> Dict[str, Any]:
        """Get report metadata"""
        return {
            "generated_at": datetime.now().isoformat(),
            "version": __version__,
            "hostname": os.uname().nodename if hasattr(os, 'uname') else "unknown",
            "user": os.environ.get("USER", os.environ.get("USERNAME", "unknown")),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        }

    def _get_ecosystem_info(self) -> Dict[str, Any]:
        """Get ecosystem installation info"""
        info = {
            "install_location": str(self.ecosystem_home),
            "installed": self.ecosystem_home.exists(),
            "registry_location": str(self.registry_dir),
            "registry_exists": self.registry_dir.exists(),
        }

        # Check bin scripts
        if self.ecosystem_home.exists():
            bin_path = self.ecosystem_home / "bin"
            if bin_path.exists():
                info["bin_scripts"] = len(list(bin_path.glob("*.py")))

        # Check from source
        source_bin = bin_dir
        info["source_scripts"] = len(list(source_bin.glob("*.py")))

        return info

    def _get_experiment_summary(self) -> Dict[str, Any]:
        """Get experiment registry summary"""
        registry_file = bin_dir.parent / "data" / "experiment_registry.json"

        if not registry_file.exists():
            return {"available": False}

        try:
            with open(registry_file) as f:
                data = json.load(f)

            summary = {
                "available": True,
                "total_experiments": data.get("total_experiments", 0),
                "total_reads": data.get("total_reads", 0),
                "total_bases": data.get("total_bases", 0),
            }

            # Count by device type
            if "experiments" in data:
                devices = {}
                statuses = {}
                for exp in data["experiments"]:
                    device = exp.get("device_type", "unknown")
                    devices[device] = devices.get(device, 0) + 1
                    status = exp.get("status", "unknown")
                    statuses[status] = statuses.get(status, 0) + 1

                summary["by_device"] = devices
                summary["by_status"] = statuses

            return summary
        except Exception as e:
            return {"available": False, "error": str(e)}

    def _get_skills_summary(self) -> Dict[str, Any]:
        """Get skills summary"""
        skills_dir = bin_dir.parent / "skills"

        if not skills_dir.exists():
            return {"available": False}

        skills = []
        for skill_path in skills_dir.iterdir():
            if skill_path.is_dir() and (skill_path / "SKILL.md").exists():
                skill_info = {"name": skill_path.name}

                # Check for scripts
                scripts_dir = skill_path / "scripts"
                if scripts_dir.exists():
                    skill_info["scripts"] = len(list(scripts_dir.glob("*.py")))

                skills.append(skill_info)

        return {
            "available": True,
            "total": len(skills),
            "skills": skills,
        }

    def _get_generators_summary(self) -> Dict[str, Any]:
        """Get figure/table generators summary"""
        gen_dir = bin_dir.parent / "skills" / "manuscript" / "generators"

        if not gen_dir.exists():
            return {"available": False}

        generators = list(gen_dir.glob("gen_*.py"))
        figure_gens = [g.stem for g in generators if "fig" in g.stem.lower()]
        table_gens = [g.stem for g in generators if "tbl" in g.stem.lower()]

        return {
            "available": True,
            "total": len(generators),
            "figure_generators": len(figure_gens),
            "table_generators": len(table_gens),
            "generators": [g.stem for g in generators],
        }

    def _get_test_summary(self) -> Dict[str, Any]:
        """Get test suite summary"""
        tests_dir = bin_dir.parent / "tests"

        if not tests_dir.exists():
            return {"available": False}

        test_files = list(tests_dir.glob("test_*.py"))

        # Count test functions
        total_tests = 0
        test_counts = {}
        for test_file in test_files:
            try:
                content = test_file.read_text()
                count = content.count("def test_")
                test_counts[test_file.stem] = count
                total_tests += count
            except Exception:
                pass

        return {
            "available": True,
            "test_files": len(test_files),
            "total_tests": total_tests,
            "by_file": test_counts,
        }

    def _get_git_info(self) -> Dict[str, Any]:
        """Get git repository info"""
        repo_dir = bin_dir.parent

        if not (repo_dir / ".git").exists():
            return {"available": False}

        info = {"available": True}

        try:
            # Get current branch
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=repo_dir, capture_output=True, text=True
            )
            if result.returncode == 0:
                info["branch"] = result.stdout.strip()

            # Get commit count
            result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=repo_dir, capture_output=True, text=True
            )
            if result.returncode == 0:
                info["commit_count"] = int(result.stdout.strip())

            # Get latest commit
            result = subprocess.run(
                ["git", "log", "-1", "--format=%h %s"],
                cwd=repo_dir, capture_output=True, text=True
            )
            if result.returncode == 0:
                info["latest_commit"] = result.stdout.strip()

            # Get status
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_dir, capture_output=True, text=True
            )
            if result.returncode == 0:
                changes = result.stdout.strip().split('\n') if result.stdout.strip() else []
                info["uncommitted_changes"] = len(changes)

            # Get tags
            result = subprocess.run(
                ["git", "tag", "-l"],
                cwd=repo_dir, capture_output=True, text=True
            )
            if result.returncode == 0:
                tags = result.stdout.strip().split('\n') if result.stdout.strip() else []
                info["tags"] = len([t for t in tags if t])

        except Exception as e:
            info["error"] = str(e)

        return info

    def _get_dependencies_info(self) -> Dict[str, Any]:
        """Get Python dependencies info"""
        dependencies = {
            "core": [],
            "optional": [],
        }

        # Core dependencies
        core_packages = [
            ("pyyaml", "yaml"),
            ("jsonschema", "jsonschema"),
        ]

        for package, module in core_packages:
            try:
                mod = __import__(module)
                version = getattr(mod, "__version__", "unknown")
                dependencies["core"].append({
                    "name": package,
                    "installed": True,
                    "version": version,
                })
            except ImportError:
                dependencies["core"].append({
                    "name": package,
                    "installed": False,
                })

        # Optional dependencies
        optional_packages = [
            ("numpy", "numpy"),
            ("pandas", "pandas"),
            ("matplotlib", "matplotlib"),
            ("pysam", "pysam"),
            ("edlib", "edlib"),
            ("pod5", "pod5"),
            ("h5py", "h5py"),
        ]

        for package, module in optional_packages:
            try:
                mod = __import__(module)
                version = getattr(mod, "__version__", "unknown")
                dependencies["optional"].append({
                    "name": package,
                    "installed": True,
                    "version": version,
                })
            except ImportError:
                dependencies["optional"].append({
                    "name": package,
                    "installed": False,
                })

        return dependencies


def format_text(data: Dict[str, Any]) -> str:
    """Format report as plain text"""
    lines = []
    lines.append("=" * 70)
    lines.append("  ONT Ecosystem Project Report")
    lines.append("=" * 70)
    lines.append("")

    # Metadata
    meta = data["metadata"]
    lines.append(f"Generated: {meta['generated_at']}")
    lines.append(f"Version: {meta['version']}")
    lines.append(f"Python: {meta['python_version']}")
    lines.append("")

    # Ecosystem
    lines.append("-" * 70)
    lines.append("Ecosystem Installation")
    lines.append("-" * 70)
    eco = data["ecosystem"]
    lines.append(f"  Installed: {eco['installed']}")
    lines.append(f"  Source scripts: {eco['source_scripts']}")
    lines.append("")

    # Experiments
    lines.append("-" * 70)
    lines.append("Experiment Registry")
    lines.append("-" * 70)
    exp = data["experiments"]
    if exp.get("available"):
        lines.append(f"  Total experiments: {exp['total_experiments']}")
        lines.append(f"  Total reads: {exp['total_reads']:,}")
        lines.append(f"  Total bases: {exp['total_bases']:,}")
        if "by_device" in exp:
            lines.append(f"  By device: {exp['by_device']}")
    else:
        lines.append("  Registry not available")
    lines.append("")

    # Skills
    lines.append("-" * 70)
    lines.append("Skills")
    lines.append("-" * 70)
    skills = data["skills"]
    if skills.get("available"):
        lines.append(f"  Total skills: {skills['total']}")
        for s in skills["skills"]:
            scripts = s.get("scripts", 0)
            lines.append(f"    - {s['name']}: {scripts} scripts")
    else:
        lines.append("  Skills not available")
    lines.append("")

    # Generators
    lines.append("-" * 70)
    lines.append("Figure/Table Generators")
    lines.append("-" * 70)
    gens = data["generators"]
    if gens.get("available"):
        lines.append(f"  Total generators: {gens['total']}")
        lines.append(f"  Figure generators: {gens['figure_generators']}")
        lines.append(f"  Table generators: {gens['table_generators']}")
    else:
        lines.append("  Generators not available")
    lines.append("")

    # Tests
    lines.append("-" * 70)
    lines.append("Test Suite")
    lines.append("-" * 70)
    tests = data["tests"]
    if tests.get("available"):
        lines.append(f"  Test files: {tests['test_files']}")
        lines.append(f"  Total tests: {tests['total_tests']}")
    else:
        lines.append("  Tests not available")
    lines.append("")

    # Git
    lines.append("-" * 70)
    lines.append("Git Repository")
    lines.append("-" * 70)
    git = data["git"]
    if git.get("available"):
        lines.append(f"  Branch: {git.get('branch', 'unknown')}")
        lines.append(f"  Commits: {git.get('commit_count', 'unknown')}")
        lines.append(f"  Latest: {git.get('latest_commit', 'unknown')}")
        lines.append(f"  Uncommitted: {git.get('uncommitted_changes', 0)}")
        lines.append(f"  Tags: {git.get('tags', 0)}")
    else:
        lines.append("  Git not available")
    lines.append("")

    # Dependencies
    lines.append("-" * 70)
    lines.append("Dependencies")
    lines.append("-" * 70)
    deps = data["dependencies"]
    lines.append("  Core:")
    for d in deps["core"]:
        status = f"v{d['version']}" if d.get("installed") else "not installed"
        lines.append(f"    - {d['name']}: {status}")
    lines.append("  Optional:")
    installed = [d for d in deps["optional"] if d.get("installed")]
    missing = [d for d in deps["optional"] if not d.get("installed")]
    lines.append(f"    Installed: {len(installed)}/{len(deps['optional'])}")
    if missing:
        lines.append(f"    Missing: {', '.join(d['name'] for d in missing)}")
    lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


def format_markdown(data: Dict[str, Any]) -> str:
    """Format report as Markdown"""
    lines = []
    lines.append("# ONT Ecosystem Project Report")
    lines.append("")

    # Metadata
    meta = data["metadata"]
    lines.append(f"**Generated:** {meta['generated_at']}  ")
    lines.append(f"**Version:** {meta['version']}  ")
    lines.append(f"**Python:** {meta['python_version']}")
    lines.append("")

    # Ecosystem
    lines.append("## Ecosystem Installation")
    lines.append("")
    eco = data["ecosystem"]
    lines.append(f"- **Installed:** {eco['installed']}")
    lines.append(f"- **Source scripts:** {eco['source_scripts']}")
    lines.append("")

    # Experiments
    lines.append("## Experiment Registry")
    lines.append("")
    exp = data["experiments"]
    if exp.get("available"):
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total experiments | {exp['total_experiments']} |")
        lines.append(f"| Total reads | {exp['total_reads']:,} |")
        lines.append(f"| Total bases | {exp['total_bases']:,} |")
    else:
        lines.append("*Registry not available*")
    lines.append("")

    # Skills
    lines.append("## Skills")
    lines.append("")
    skills = data["skills"]
    if skills.get("available"):
        lines.append(f"**Total:** {skills['total']} skills")
        lines.append("")
        lines.append("| Skill | Scripts |")
        lines.append("|-------|---------|")
        for s in skills["skills"]:
            lines.append(f"| {s['name']} | {s.get('scripts', 0)} |")
    else:
        lines.append("*Skills not available*")
    lines.append("")

    # Generators
    lines.append("## Figure/Table Generators")
    lines.append("")
    gens = data["generators"]
    if gens.get("available"):
        lines.append(f"- **Total:** {gens['total']}")
        lines.append(f"- **Figures:** {gens['figure_generators']}")
        lines.append(f"- **Tables:** {gens['table_generators']}")
    else:
        lines.append("*Generators not available*")
    lines.append("")

    # Tests
    lines.append("## Test Suite")
    lines.append("")
    tests = data["tests"]
    if tests.get("available"):
        lines.append(f"| File | Tests |")
        lines.append(f"|------|-------|")
        for fname, count in tests.get("by_file", {}).items():
            lines.append(f"| {fname} | {count} |")
        lines.append(f"| **Total** | **{tests['total_tests']}** |")
    else:
        lines.append("*Tests not available*")
    lines.append("")

    # Git
    lines.append("## Git Repository")
    lines.append("")
    git = data["git"]
    if git.get("available"):
        lines.append(f"- **Branch:** `{git.get('branch', 'unknown')}`")
        lines.append(f"- **Commits:** {git.get('commit_count', 'unknown')}")
        lines.append(f"- **Latest:** `{git.get('latest_commit', 'unknown')}`")
        lines.append(f"- **Uncommitted:** {git.get('uncommitted_changes', 0)}")
        lines.append(f"- **Tags:** {git.get('tags', 0)}")
    else:
        lines.append("*Git not available*")
    lines.append("")

    # Dependencies
    lines.append("## Dependencies")
    lines.append("")
    deps = data["dependencies"]
    lines.append("### Core")
    lines.append("")
    lines.append("| Package | Status |")
    lines.append("|---------|--------|")
    for d in deps["core"]:
        status = f"v{d['version']}" if d.get("installed") else "not installed"
        lines.append(f"| {d['name']} | {status} |")
    lines.append("")
    lines.append("### Optional")
    lines.append("")
    installed = [d for d in deps["optional"] if d.get("installed")]
    missing = [d for d in deps["optional"] if not d.get("installed")]
    lines.append(f"**Installed:** {len(installed)}/{len(deps['optional'])}")
    if missing:
        lines.append(f"  ")
        lines.append(f"**Missing:** {', '.join(d['name'] for d in missing)}")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="ONT Ecosystem Report Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--format", "-f", choices=["text", "markdown", "json"],
                        default="text", help="Output format")
    parser.add_argument("--output", "-o", help="Output file path")
    args = parser.parse_args()

    generator = ReportGenerator()
    data = generator.generate()

    if args.format == "json":
        output = json.dumps(data, indent=2)
    elif args.format == "markdown":
        output = format_markdown(data)
    else:
        output = format_text(data)

    if args.output:
        Path(args.output).write_text(output)
        print(f"Report saved to: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
