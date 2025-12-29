#!/usr/bin/env python3
"""
ONT Ecosystem Health Check - Validate installation and dependencies

Usage:
    ont_check.py              # Full health check
    ont_check.py --fix        # Attempt to fix issues
    ont_check.py --json       # JSON output
"""

import argparse
import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Check results
PASS = "✅"
WARN = "⚠️"
FAIL = "❌"
INFO = "ℹ️"


def check_python_version() -> Tuple[str, str]:
    """Check Python version"""
    version = sys.version_info
    if version >= (3, 9):
        return PASS, f"Python {version.major}.{version.minor}.{version.micro}"
    elif version >= (3, 7):
        return WARN, f"Python {version.major}.{version.minor} (3.9+ recommended)"
    else:
        return FAIL, f"Python {version.major}.{version.minor} (3.9+ required)"


def check_required_modules() -> List[Tuple[str, str, str]]:
    """Check required Python modules"""
    required = [
        ("pyyaml", "yaml", "Core functionality"),
        ("jsonschema", "jsonschema", "Schema validation"),
    ]

    results = []
    for package, module, purpose in required:
        try:
            importlib.import_module(module)
            results.append((PASS, package, f"Installed ({purpose})"))
        except ImportError:
            results.append((FAIL, package, f"Missing ({purpose}) - pip install {package}"))

    return results


def check_optional_modules() -> List[Tuple[str, str, str]]:
    """Check optional Python modules"""
    optional = [
        ("numpy", "numpy", "Numerical computing"),
        ("pandas", "pandas", "Data analysis"),
        ("matplotlib", "matplotlib", "Plotting"),
        ("pysam", "pysam", "BAM/SAM handling"),
        ("edlib", "edlib", "Edit distance"),
        ("pod5", "pod5", "POD5 file support"),
        ("h5py", "h5py", "HDF5/Fast5 support"),
        ("flask", "flask", "Web dashboard"),
    ]

    results = []
    for package, module, purpose in optional:
        try:
            importlib.import_module(module)
            results.append((PASS, package, f"Installed ({purpose})"))
        except ImportError:
            results.append((INFO, package, f"Not installed ({purpose})"))

    return results


def check_external_tools() -> List[Tuple[str, str, str]]:
    """Check external tools"""
    tools = [
        ("minimap2", "Alignment"),
        ("samtools", "BAM processing"),
        ("dorado", "Basecalling"),
    ]

    results = []
    for tool, purpose in tools:
        try:
            result = subprocess.run(
                [tool, "--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                try:
                    version = result.stdout.decode('utf-8', errors='ignore').split('\n')[0][:50]
                except Exception:
                    version = "installed"
                results.append((PASS, tool, f"Found: {version}"))
            else:
                results.append((INFO, tool, f"Not found ({purpose})"))
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            results.append((INFO, tool, f"Not found ({purpose})"))

    return results


def check_directories() -> List[Tuple[str, str, str]]:
    """Check directory structure"""
    home = Path.home()

    dirs = [
        (home / ".ont-registry", "Experiment registry"),
        (home / ".ont-manuscript", "Manuscript artifacts"),
        (home / ".ont-ecosystem", "Installation directory"),
    ]

    results = []
    for path, purpose in dirs:
        if path.exists():
            results.append((PASS, str(path), f"Exists ({purpose})"))
        else:
            results.append((INFO, str(path), f"Not created yet ({purpose})"))

    return results


def check_ecosystem_files() -> List[Tuple[str, str, str]]:
    """Check ecosystem files"""
    bin_dir = Path(__file__).parent
    root_dir = bin_dir.parent

    files = [
        (root_dir / "textbook" / "equations.yaml", "Equations database"),
        (root_dir / "textbook" / "variables.yaml", "Variables database"),
        (root_dir / "data" / "experiment_registry.json", "Experiment registry"),
        (root_dir / "registry" / "INDEX.yaml", "Registry index"),
    ]

    results = []
    for path, purpose in files:
        if path.exists():
            size = path.stat().st_size
            if size > 1024 * 1024:
                size_str = f"{size / 1024 / 1024:.1f} MB"
            elif size > 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size} bytes"
            results.append((PASS, path.name, f"{size_str} ({purpose})"))
        else:
            results.append((WARN, path.name, f"Missing ({purpose})"))

    return results


def check_skills() -> Tuple[str, str]:
    """Check installed skills"""
    bin_dir = Path(__file__).parent
    skills_dir = bin_dir.parent / "skills"

    if not skills_dir.exists():
        return WARN, "Skills directory not found"

    skills = [d for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]
    return PASS, f"{len(skills)} skills installed"


def check_generators() -> Tuple[str, str]:
    """Check manuscript generators"""
    bin_dir = Path(__file__).parent
    gen_dir = bin_dir.parent / "skills" / "manuscript" / "generators"

    if not gen_dir.exists():
        return WARN, "Generators directory not found"

    generators = list(gen_dir.glob("gen_*.py"))
    return PASS, f"{len(generators)} generators available"


def run_health_check(fix: bool = False) -> Dict:
    """Run full health check"""
    results = {
        "status": "healthy",
        "checks": []
    }

    # Python version
    status, msg = check_python_version()
    results["checks"].append({"category": "Python", "status": status, "message": msg})
    if status == FAIL:
        results["status"] = "unhealthy"

    # Required modules
    for status, name, msg in check_required_modules():
        results["checks"].append({"category": "Required", "name": name, "status": status, "message": msg})
        if status == FAIL:
            results["status"] = "unhealthy"

    # Optional modules
    for status, name, msg in check_optional_modules():
        results["checks"].append({"category": "Optional", "name": name, "status": status, "message": msg})

    # External tools
    for status, name, msg in check_external_tools():
        results["checks"].append({"category": "Tools", "name": name, "status": status, "message": msg})

    # Directories
    for status, name, msg in check_directories():
        results["checks"].append({"category": "Directories", "name": name, "status": status, "message": msg})

    # Ecosystem files
    for status, name, msg in check_ecosystem_files():
        results["checks"].append({"category": "Files", "name": name, "status": status, "message": msg})
        if status == FAIL:
            results["status"] = "degraded"

    # Skills
    status, msg = check_skills()
    results["checks"].append({"category": "Skills", "status": status, "message": msg})

    # Generators
    status, msg = check_generators()
    results["checks"].append({"category": "Generators", "status": status, "message": msg})

    return results


def print_results(results: Dict):
    """Print health check results"""
    print("=" * 60)
    print("  ONT Ecosystem Health Check")
    print("=" * 60)
    print()

    current_category = None
    for check in results["checks"]:
        category = check.get("category", "")
        if category != current_category:
            if current_category:
                print()
            print(f"{category.upper()}")
            current_category = category

        status = check["status"]
        name = check.get("name", "")
        msg = check["message"]

        if name:
            print(f"  {status} {name}: {msg}")
        else:
            print(f"  {status} {msg}")

    print()
    print("=" * 60)
    status = results["status"]
    if status == "healthy":
        print(f"  {PASS} System Status: HEALTHY")
    elif status == "degraded":
        print(f"  {WARN} System Status: DEGRADED (some features unavailable)")
    else:
        print(f"  {FAIL} System Status: UNHEALTHY (fix required issues)")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="ONT Ecosystem Health Check",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--fix", action="store_true", help="Attempt to fix issues")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    results = run_health_check(fix=args.fix)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_results(results)

    # Exit code based on status
    if results["status"] == "unhealthy":
        sys.exit(1)
    elif results["status"] == "degraded":
        sys.exit(0)  # Degraded is still usable
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
