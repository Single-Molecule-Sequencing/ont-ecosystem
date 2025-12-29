#!/usr/bin/env python3
"""
ONT Ecosystem Doctor - Diagnose issues and suggest fixes

Usage:
    ont_doctor.py              # Run full diagnostics
    ont_doctor.py --fix        # Attempt automatic fixes
    ont_doctor.py --quick      # Quick check only
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

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
class DiagnosticResult:
    """Result of a diagnostic check"""
    name: str
    status: str  # "ok", "warning", "error"
    message: str
    fix_available: bool = False
    fix_command: Optional[str] = None
    fix_description: Optional[str] = None


class Doctor:
    """Diagnostic engine for ONT Ecosystem"""

    def __init__(self):
        self.results: List[DiagnosticResult] = []
        self.ecosystem_home = Path(os.environ.get(
            "ONT_ECOSYSTEM_HOME",
            Path.home() / ".ont-ecosystem"
        ))
        self.registry_dir = Path(os.environ.get(
            "ONT_REGISTRY_DIR",
            Path.home() / ".ont-registry"
        ))

    def add_result(self, result: DiagnosticResult):
        """Add a diagnostic result"""
        self.results.append(result)

    def run_all(self, quick: bool = False) -> List[DiagnosticResult]:
        """Run all diagnostics"""
        self.results = []

        # Core checks
        self.check_python_version()
        self.check_ecosystem_installation()
        self.check_required_packages()

        if not quick:
            self.check_optional_packages()
            self.check_external_tools()
            self.check_registry()
            self.check_skills()
            self.check_generators()
            self.check_disk_space()
            self.check_permissions()
            self.check_git_repo()

        return self.results

    def check_python_version(self):
        """Check Python version"""
        version = sys.version_info
        if version >= (3, 11):
            self.add_result(DiagnosticResult(
                name="Python Version",
                status="ok",
                message=f"Python {version.major}.{version.minor}.{version.micro} (optimal)"
            ))
        elif version >= (3, 9):
            self.add_result(DiagnosticResult(
                name="Python Version",
                status="ok",
                message=f"Python {version.major}.{version.minor}.{version.micro}"
            ))
        elif version >= (3, 7):
            self.add_result(DiagnosticResult(
                name="Python Version",
                status="warning",
                message=f"Python {version.major}.{version.minor} (3.9+ recommended)",
                fix_available=True,
                fix_description="Upgrade to Python 3.9 or later"
            ))
        else:
            self.add_result(DiagnosticResult(
                name="Python Version",
                status="error",
                message=f"Python {version.major}.{version.minor} (3.9+ required)",
                fix_available=True,
                fix_description="Upgrade to Python 3.9 or later"
            ))

    def check_ecosystem_installation(self):
        """Check ecosystem installation"""
        if self.ecosystem_home.exists():
            # Check for key directories
            missing = []
            for subdir in ["bin", "lib", "skills"]:
                if not (self.ecosystem_home / subdir).exists():
                    missing.append(subdir)

            if missing:
                self.add_result(DiagnosticResult(
                    name="Installation",
                    status="warning",
                    message=f"Missing directories: {', '.join(missing)}",
                    fix_available=True,
                    fix_command="./install.sh",
                    fix_description="Reinstall from repository"
                ))
            else:
                self.add_result(DiagnosticResult(
                    name="Installation",
                    status="ok",
                    message=f"Installed at {self.ecosystem_home}"
                ))
        else:
            self.add_result(DiagnosticResult(
                name="Installation",
                status="warning",
                message="Ecosystem not installed to ~/.ont-ecosystem",
                fix_available=True,
                fix_command="./install.sh",
                fix_description="Run install.sh from repository"
            ))

    def check_required_packages(self):
        """Check required Python packages"""
        required = [
            ("pyyaml", "yaml"),
            ("jsonschema", "jsonschema"),
        ]

        missing = []
        for package, module in required:
            try:
                __import__(module)
            except ImportError:
                missing.append(package)

        if missing:
            self.add_result(DiagnosticResult(
                name="Required Packages",
                status="error",
                message=f"Missing: {', '.join(missing)}",
                fix_available=True,
                fix_command=f"pip install {' '.join(missing)}",
                fix_description="Install missing packages"
            ))
        else:
            self.add_result(DiagnosticResult(
                name="Required Packages",
                status="ok",
                message="All required packages installed"
            ))

    def check_optional_packages(self):
        """Check optional Python packages"""
        optional = [
            ("numpy", "numpy", "Numerical computing"),
            ("pandas", "pandas", "Data analysis"),
            ("matplotlib", "matplotlib", "Plotting"),
            ("pysam", "pysam", "BAM/SAM handling"),
        ]

        installed = []
        missing = []

        for package, module, purpose in optional:
            try:
                __import__(module)
                installed.append(package)
            except ImportError:
                missing.append(f"{package} ({purpose})")

        if missing:
            self.add_result(DiagnosticResult(
                name="Optional Packages",
                status="warning",
                message=f"Not installed: {', '.join(missing)}",
                fix_available=True,
                fix_command="pip install " + " ".join([m.split()[0] for m in missing]),
                fix_description="Install for full functionality"
            ))
        else:
            self.add_result(DiagnosticResult(
                name="Optional Packages",
                status="ok",
                message=f"All optional packages installed ({len(installed)})"
            ))

    def check_external_tools(self):
        """Check external tools"""
        tools = [
            ("minimap2", "Alignment"),
            ("samtools", "BAM processing"),
            ("dorado", "Basecalling"),
        ]

        found = []
        missing = []

        for tool, purpose in tools:
            if shutil.which(tool):
                found.append(tool)
            else:
                missing.append(f"{tool} ({purpose})")

        if missing:
            self.add_result(DiagnosticResult(
                name="External Tools",
                status="warning",
                message=f"Not found: {', '.join(missing)}",
                fix_description="Install missing tools or add to PATH"
            ))
        else:
            self.add_result(DiagnosticResult(
                name="External Tools",
                status="ok",
                message=f"All tools found ({len(found)})"
            ))

    def check_registry(self):
        """Check experiment registry"""
        registry_file = bin_dir.parent / "data" / "experiment_registry.json"

        if registry_file.exists():
            try:
                with open(registry_file) as f:
                    data = json.load(f)
                exp_count = data.get("total_experiments", 0)
                self.add_result(DiagnosticResult(
                    name="Experiment Registry",
                    status="ok",
                    message=f"{exp_count} experiments registered"
                ))
            except Exception as e:
                self.add_result(DiagnosticResult(
                    name="Experiment Registry",
                    status="error",
                    message=f"Failed to load: {e}",
                    fix_description="Check registry file format"
                ))
        else:
            self.add_result(DiagnosticResult(
                name="Experiment Registry",
                status="warning",
                message="No experiment registry found",
                fix_available=True,
                fix_command="ont_experiments.py init",
                fix_description="Initialize experiment registry"
            ))

    def check_skills(self):
        """Check skills installation"""
        skills_dir = bin_dir.parent / "skills"

        if skills_dir.exists():
            skills = [d for d in skills_dir.iterdir()
                      if d.is_dir() and (d / "SKILL.md").exists()]

            if len(skills) >= 7:
                self.add_result(DiagnosticResult(
                    name="Skills",
                    status="ok",
                    message=f"{len(skills)} skills installed"
                ))
            else:
                self.add_result(DiagnosticResult(
                    name="Skills",
                    status="warning",
                    message=f"Only {len(skills)} skills found (expected 7+)",
                    fix_available=True,
                    fix_command="./install.sh",
                    fix_description="Reinstall to get all skills"
                ))
        else:
            self.add_result(DiagnosticResult(
                name="Skills",
                status="error",
                message="Skills directory not found",
                fix_available=True,
                fix_command="./install.sh",
                fix_description="Run install.sh"
            ))

    def check_generators(self):
        """Check figure/table generators"""
        gen_dir = bin_dir.parent / "skills" / "manuscript" / "generators"

        if gen_dir.exists():
            generators = list(gen_dir.glob("gen_*.py"))

            if len(generators) >= 10:
                self.add_result(DiagnosticResult(
                    name="Generators",
                    status="ok",
                    message=f"{len(generators)} generators available"
                ))
            else:
                self.add_result(DiagnosticResult(
                    name="Generators",
                    status="warning",
                    message=f"Only {len(generators)} generators (expected 10+)"
                ))
        else:
            self.add_result(DiagnosticResult(
                name="Generators",
                status="warning",
                message="Generators directory not found"
            ))

    def check_disk_space(self):
        """Check available disk space"""
        try:
            stat = os.statvfs(str(Path.home()))
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)

            if free_gb > 50:
                self.add_result(DiagnosticResult(
                    name="Disk Space",
                    status="ok",
                    message=f"{free_gb:.1f} GB free"
                ))
            elif free_gb > 10:
                self.add_result(DiagnosticResult(
                    name="Disk Space",
                    status="warning",
                    message=f"{free_gb:.1f} GB free (consider cleanup)",
                    fix_description="Free up disk space for large analyses"
                ))
            else:
                self.add_result(DiagnosticResult(
                    name="Disk Space",
                    status="error",
                    message=f"{free_gb:.1f} GB free (low!)",
                    fix_description="Free up disk space immediately"
                ))
        except Exception:
            pass  # Skip on systems without statvfs

    def check_permissions(self):
        """Check file permissions"""
        issues = []

        # Check bin scripts are executable
        for script in (bin_dir).glob("*.py"):
            if not os.access(script, os.X_OK):
                issues.append(script.name)

        if issues:
            self.add_result(DiagnosticResult(
                name="Permissions",
                status="warning",
                message=f"{len(issues)} scripts not executable",
                fix_available=True,
                fix_command="chmod +x bin/*.py",
                fix_description="Make scripts executable"
            ))
        else:
            self.add_result(DiagnosticResult(
                name="Permissions",
                status="ok",
                message="All scripts executable"
            ))

    def check_git_repo(self):
        """Check git repository status"""
        repo_dir = bin_dir.parent

        if (repo_dir / ".git").exists():
            try:
                # Check for uncommitted changes
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True
                )
                changes = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0

                if changes == 0:
                    self.add_result(DiagnosticResult(
                        name="Git Repository",
                        status="ok",
                        message="Clean working directory"
                    ))
                else:
                    self.add_result(DiagnosticResult(
                        name="Git Repository",
                        status="warning",
                        message=f"{changes} uncommitted changes",
                        fix_command="git status",
                        fix_description="Review and commit changes"
                    ))
            except Exception:
                self.add_result(DiagnosticResult(
                    name="Git Repository",
                    status="warning",
                    message="Could not check git status"
                ))

    def apply_fixes(self) -> List[Tuple[str, bool, str]]:
        """Apply available fixes"""
        fixes_applied = []

        for result in self.results:
            if result.fix_available and result.fix_command:
                print(f"Applying fix for {result.name}...")
                print(f"  Command: {result.fix_command}")

                try:
                    if result.fix_command.startswith("pip install"):
                        subprocess.run(
                            result.fix_command.split(),
                            check=True,
                            capture_output=True
                        )
                        fixes_applied.append((result.name, True, "Installed"))
                    elif result.fix_command.startswith("chmod"):
                        subprocess.run(
                            result.fix_command,
                            shell=True,
                            check=True,
                            cwd=bin_dir.parent
                        )
                        fixes_applied.append((result.name, True, "Fixed permissions"))
                    else:
                        fixes_applied.append((result.name, False, "Manual fix required"))
                except Exception as e:
                    fixes_applied.append((result.name, False, str(e)))

        return fixes_applied


def print_results(results: List[DiagnosticResult], verbose: bool = False):
    """Print diagnostic results"""
    print("=" * 60)
    print("  ONT Ecosystem Doctor")
    print("=" * 60)
    print()

    # Count by status
    ok_count = sum(1 for r in results if r.status == "ok")
    warn_count = sum(1 for r in results if r.status == "warning")
    error_count = sum(1 for r in results if r.status == "error")

    # Print results
    for result in results:
        if result.status == "ok":
            icon = "✅"
        elif result.status == "warning":
            icon = "⚠️ "
        else:
            icon = "❌"

        print(f"{icon} {result.name}: {result.message}")

        if verbose and result.fix_description:
            print(f"     Fix: {result.fix_description}")
            if result.fix_command:
                print(f"     Command: {result.fix_command}")

    # Summary
    print()
    print("-" * 60)
    print(f"Summary: {ok_count} OK, {warn_count} warnings, {error_count} errors")

    if error_count > 0:
        print()
        print("Run 'ont_doctor.py --fix' to attempt automatic fixes")
    elif warn_count > 0:
        print()
        print("Run 'ont_doctor.py --fix' to resolve warnings")
    else:
        print()
        print("All checks passed! System is healthy.")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="ONT Ecosystem Doctor - Diagnose and fix issues",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--fix", action="store_true",
                        help="Attempt to fix issues automatically")
    parser.add_argument("--quick", action="store_true",
                        help="Quick check only (core checks)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show fix suggestions")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    args = parser.parse_args()

    doctor = Doctor()
    results = doctor.run_all(quick=args.quick)

    if args.json:
        output = [
            {
                "name": r.name,
                "status": r.status,
                "message": r.message,
                "fix_available": r.fix_available,
                "fix_command": r.fix_command,
                "fix_description": r.fix_description,
            }
            for r in results
        ]
        print(json.dumps(output, indent=2))
        return

    print_results(results, verbose=args.verbose or args.fix)

    if args.fix:
        print()
        print("Attempting fixes...")
        print()
        fixes = doctor.apply_fixes()
        for name, success, message in fixes:
            status = "✅" if success else "❌"
            print(f"  {status} {name}: {message}")

        # Re-run checks
        print()
        print("Re-running diagnostics...")
        results = doctor.run_all(quick=args.quick)
        print_results(results)

    # Exit code
    error_count = sum(1 for r in results if r.status == "error")
    sys.exit(1 if error_count > 0 else 0)


if __name__ == "__main__":
    main()
