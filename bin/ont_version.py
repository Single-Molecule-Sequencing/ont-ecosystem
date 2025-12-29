#!/usr/bin/env python3
"""
ONT Ecosystem Version Manager - Comprehensive version information and management

Usage:
    ont_version.py              # Show version summary
    ont_version.py --full       # Show full version info including dependencies
    ont_version.py --json       # Output as JSON
    ont_version.py --skills     # Show skill versions
    ont_version.py --check      # Check for version mismatches
    ont_version.py bump patch   # Bump version (patch/minor/major)
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add paths
bin_dir = Path(__file__).parent
lib_dir = bin_dir.parent / 'lib'
sys.path.insert(0, str(bin_dir))
sys.path.insert(0, str(lib_dir.parent))

try:
    from lib import __version__, VERSION_INFO, SKILL_VERSIONS, REPOSITORY_URL
except ImportError:
    __version__ = "3.0.0"
    VERSION_INFO = {"major": 3, "minor": 0, "patch": 0, "release": "stable"}
    SKILL_VERSIONS = {}
    REPOSITORY_URL = "https://github.com/Single-Molecule-Sequencing/ont-ecosystem"


@dataclass
class VersionInfo:
    """Complete version information"""
    version: str
    major: int
    minor: int
    patch: int
    release: str
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    git_tag: Optional[str] = None
    git_dirty: bool = False
    build_date: Optional[str] = None
    python_version: str = ""
    platform: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "version": self.version,
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "release": self.release,
            "git_commit": self.git_commit,
            "git_branch": self.git_branch,
            "git_tag": self.git_tag,
            "git_dirty": self.git_dirty,
            "build_date": self.build_date,
            "python_version": self.python_version,
            "platform": self.platform,
        }

    @property
    def full_version(self) -> str:
        """Get full version string with git info"""
        parts = [self.version]
        if self.git_commit:
            parts.append(f"+{self.git_commit[:7]}")
        if self.git_dirty:
            parts.append("-dirty")
        return "".join(parts)


def get_git_info() -> Dict[str, Any]:
    """Get git repository information"""
    repo_dir = bin_dir.parent
    info = {}

    if not (repo_dir / ".git").exists():
        return info

    try:
        # Commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir, capture_output=True, text=True
        )
        if result.returncode == 0:
            info["commit"] = result.stdout.strip()

        # Branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_dir, capture_output=True, text=True
        )
        if result.returncode == 0:
            info["branch"] = result.stdout.strip()

        # Tag
        result = subprocess.run(
            ["git", "describe", "--tags", "--exact-match"],
            cwd=repo_dir, capture_output=True, text=True
        )
        if result.returncode == 0:
            info["tag"] = result.stdout.strip()

        # Dirty status
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_dir, capture_output=True, text=True
        )
        if result.returncode == 0:
            info["dirty"] = bool(result.stdout.strip())

        # Commit date
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ci"],
            cwd=repo_dir, capture_output=True, text=True
        )
        if result.returncode == 0:
            info["commit_date"] = result.stdout.strip()

    except Exception:
        pass

    return info


def get_version_info() -> VersionInfo:
    """Get complete version information"""
    git_info = get_git_info()

    return VersionInfo(
        version=__version__,
        major=VERSION_INFO.get("major", 0),
        minor=VERSION_INFO.get("minor", 0),
        patch=VERSION_INFO.get("patch", 0),
        release=VERSION_INFO.get("release", "unknown"),
        git_commit=git_info.get("commit"),
        git_branch=git_info.get("branch"),
        git_tag=git_info.get("tag"),
        git_dirty=git_info.get("dirty", False),
        build_date=git_info.get("commit_date"),
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        platform=sys.platform,
    )


def get_dependency_versions() -> Dict[str, Optional[str]]:
    """Get versions of all dependencies"""
    dependencies = {}

    packages = [
        ("pyyaml", "yaml"),
        ("jsonschema", "jsonschema"),
        ("numpy", "numpy"),
        ("pandas", "pandas"),
        ("matplotlib", "matplotlib"),
        ("pysam", "pysam"),
        ("edlib", "edlib"),
        ("pod5", "pod5"),
        ("h5py", "h5py"),
        ("flask", "flask"),
        ("pytest", "pytest"),
    ]

    for package, module in packages:
        try:
            mod = __import__(module)
            version = getattr(mod, "__version__", "installed")
            dependencies[package] = version
        except ImportError:
            dependencies[package] = None

    return dependencies


def get_tool_versions() -> Dict[str, Optional[str]]:
    """Get versions of external tools"""
    tools = {}

    tool_commands = [
        ("minimap2", ["minimap2", "--version"]),
        ("samtools", ["samtools", "--version"]),
        ("dorado", ["dorado", "--version"]),
        ("git", ["git", "--version"]),
        ("python", ["python", "--version"]),
    ]

    for tool, cmd in tool_commands:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                output = result.stdout.strip() or result.stderr.strip()
                # Extract first line or version number
                version = output.split('\n')[0]
                tools[tool] = version
            else:
                tools[tool] = None
        except Exception:
            tools[tool] = None

    return tools


def check_version_consistency() -> List[Tuple[str, str, str]]:
    """Check for version inconsistencies"""
    issues = []

    # Check VERSION file matches lib version
    version_file = bin_dir.parent / "VERSION"
    if version_file.exists():
        file_version = version_file.read_text().strip()
        if file_version != __version__:
            issues.append((
                "VERSION file mismatch",
                f"VERSION file: {file_version}",
                f"lib/__init__.py: {__version__}"
            ))

    # Check pyproject.toml version
    pyproject = bin_dir.parent / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text()
        match = re.search(r'version\s*=\s*"([^"]+)"', content)
        if match:
            pyproject_version = match.group(1)
            if pyproject_version != __version__:
                issues.append((
                    "pyproject.toml mismatch",
                    f"pyproject.toml: {pyproject_version}",
                    f"lib/__init__.py: {__version__}"
                ))

    return issues


def bump_version(bump_type: str) -> Tuple[str, str]:
    """Bump version number"""
    current = __version__
    parts = current.split(".")
    major = int(parts[0])
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch = int(parts[2]) if len(parts) > 2 else 0

    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")

    new_version = f"{major}.{minor}.{patch}"
    return current, new_version


def update_version_files(new_version: str) -> List[str]:
    """Update all version files"""
    updated = []

    # Update VERSION file
    version_file = bin_dir.parent / "VERSION"
    if version_file.exists():
        version_file.write_text(new_version + "\n")
        updated.append(str(version_file))

    # Update lib/__init__.py
    lib_init = lib_dir / "__init__.py"
    if lib_init.exists():
        content = lib_init.read_text()
        content = re.sub(
            r'__version__\s*=\s*"[^"]+"',
            f'__version__ = "{new_version}"',
            content
        )

        # Update VERSION_INFO
        parts = new_version.split(".")
        content = re.sub(
            r'"major":\s*\d+',
            f'"major": {parts[0]}',
            content
        )
        content = re.sub(
            r'"minor":\s*\d+',
            f'"minor": {parts[1] if len(parts) > 1 else 0}',
            content
        )
        content = re.sub(
            r'"patch":\s*\d+',
            f'"patch": {parts[2] if len(parts) > 2 else 0}',
            content
        )

        lib_init.write_text(content)
        updated.append(str(lib_init))

    # Update pyproject.toml
    pyproject = bin_dir.parent / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text()
        content = re.sub(
            r'version\s*=\s*"[^"]+"',
            f'version = "{new_version}"',
            content
        )
        pyproject.write_text(content)
        updated.append(str(pyproject))

    return updated


def print_version_summary(info: VersionInfo, full: bool = False):
    """Print version summary"""
    print("=" * 60)
    print("  ONT Ecosystem Version Information")
    print("=" * 60)
    print()
    print(f"  Version: {info.version}")
    print(f"  Release: {info.release}")
    print(f"  Python:  {info.python_version}")
    print(f"  Platform: {info.platform}")

    if info.git_commit:
        print()
        print("Git:")
        print(f"  Branch:  {info.git_branch}")
        print(f"  Commit:  {info.git_commit[:12]}")
        if info.git_tag:
            print(f"  Tag:     {info.git_tag}")
        if info.git_dirty:
            print(f"  Status:  dirty (uncommitted changes)")
        if info.build_date:
            print(f"  Date:    {info.build_date}")

    if full:
        print()
        print("-" * 60)
        print("Skills:")
        for skill, version in SKILL_VERSIONS.items():
            print(f"  {skill:25} {version}")

        print()
        print("-" * 60)
        print("Dependencies:")
        deps = get_dependency_versions()
        for pkg, version in sorted(deps.items()):
            status = version if version else "not installed"
            print(f"  {pkg:15} {status}")

        print()
        print("-" * 60)
        print("External Tools:")
        tools = get_tool_versions()
        for tool, version in sorted(tools.items()):
            status = version if version else "not found"
            print(f"  {tool:15} {status}")

    print()
    print("=" * 60)


def print_skills(as_json: bool = False):
    """Print skill versions"""
    if as_json:
        print(json.dumps(SKILL_VERSIONS, indent=2))
        return

    print("=" * 60)
    print("  ONT Ecosystem Skill Versions")
    print("=" * 60)
    print()
    for skill, version in sorted(SKILL_VERSIONS.items()):
        print(f"  {skill:25} v{version}")
    print()
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="ONT Ecosystem Version Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--full", "-f", action="store_true",
                        help="Show full version info")
    parser.add_argument("--json", "-j", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--skills", "-s", action="store_true",
                        help="Show skill versions")
    parser.add_argument("--check", "-c", action="store_true",
                        help="Check for version mismatches")
    parser.add_argument("--deps", "-d", action="store_true",
                        help="Show dependency versions")

    subparsers = parser.add_subparsers(dest="command")

    # bump command
    p_bump = subparsers.add_parser('bump', help='Bump version')
    p_bump.add_argument('type', choices=['major', 'minor', 'patch'],
                        help='Version component to bump')
    p_bump.add_argument('--dry-run', action='store_true',
                        help='Show what would change without modifying files')

    args = parser.parse_args()

    # Handle bump command
    if args.command == "bump":
        old_version, new_version = bump_version(args.type)
        print(f"Bumping version: {old_version} -> {new_version}")

        if args.dry_run:
            print("\nDry run - no files modified")
            print("Would update:")
            print("  - VERSION")
            print("  - lib/__init__.py")
            print("  - pyproject.toml")
        else:
            updated = update_version_files(new_version)
            print("\nUpdated files:")
            for f in updated:
                print(f"  - {f}")
            print("\nDon't forget to commit the changes!")
        return

    # Get version info
    info = get_version_info()

    # Handle different output modes
    if args.json:
        output = info.to_dict()
        if args.full:
            output["skills"] = SKILL_VERSIONS
            output["dependencies"] = get_dependency_versions()
            output["tools"] = get_tool_versions()
        print(json.dumps(output, indent=2))
        return

    if args.skills:
        print_skills(as_json=False)
        return

    if args.deps:
        print("=" * 60)
        print("  Dependencies")
        print("=" * 60)
        print()
        deps = get_dependency_versions()
        for pkg, version in sorted(deps.items()):
            status = f"v{version}" if version else "not installed"
            print(f"  {pkg:15} {status}")
        print()
        return

    if args.check:
        print("Checking version consistency...")
        issues = check_version_consistency()
        if issues:
            print("\nVersion mismatches found:")
            for name, found, expected in issues:
                print(f"\n  {name}:")
                print(f"    Found: {found}")
                print(f"    Expected: {expected}")
            sys.exit(1)
        else:
            print("All versions are consistent!")
            sys.exit(0)

    # Default: print version summary
    print_version_summary(info, full=args.full)


if __name__ == "__main__":
    main()
