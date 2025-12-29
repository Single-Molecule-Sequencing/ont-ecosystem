#!/usr/bin/env python3
"""
ONT Ecosystem Update - Check for and apply updates

Usage:
    ont_update.py              # Check for updates
    ont_update.py --apply      # Apply updates
    ont_update.py --status     # Show current version status
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

# Add paths
bin_dir = Path(__file__).parent
lib_dir = bin_dir.parent / 'lib'
sys.path.insert(0, str(bin_dir))
sys.path.insert(0, str(lib_dir.parent))

try:
    from lib import __version__
except ImportError:
    __version__ = "3.0.0"

# Installation directory
INSTALL_DIR = Path(os.environ.get("ONT_ECOSYSTEM_HOME", Path.home() / ".ont-ecosystem"))
CONFIG_FILE = INSTALL_DIR / "config" / "source.conf"


def get_source_repo() -> Optional[Path]:
    """Get the source repository path from config"""
    if CONFIG_FILE.exists():
        content = CONFIG_FILE.read_text()
        for line in content.splitlines():
            if line.startswith("REPO_SOURCE="):
                repo_path = Path(line.split("=", 1)[1].strip())
                if repo_path.exists():
                    return repo_path
    return None


def get_current_version() -> str:
    """Get current installed version"""
    return __version__


def get_repo_version(repo_path: Path) -> Optional[str]:
    """Get version from repository"""
    version_file = repo_path / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()

    # Try lib/__init__.py
    lib_init = repo_path / "lib" / "__init__.py"
    if lib_init.exists():
        content = lib_init.read_text()
        for line in content.splitlines():
            if line.startswith("__version__"):
                return line.split("=")[1].strip().strip('"\'')

    return None


def get_git_status(repo_path: Path) -> Dict:
    """Get git status of repository"""
    result = {
        "is_git_repo": False,
        "branch": None,
        "commits_behind": 0,
        "commits_ahead": 0,
        "has_changes": False,
        "last_commit": None,
        "remote_url": None,
    }

    if not (repo_path / ".git").exists():
        return result

    result["is_git_repo"] = True

    try:
        # Get current branch
        proc = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        if proc.returncode == 0:
            result["branch"] = proc.stdout.strip()

        # Get remote URL
        proc = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        if proc.returncode == 0:
            result["remote_url"] = proc.stdout.strip()

        # Check for local changes
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        if proc.returncode == 0:
            result["has_changes"] = len(proc.stdout.strip()) > 0

        # Get last commit
        proc = subprocess.run(
            ["git", "log", "-1", "--format=%h %s"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        if proc.returncode == 0:
            result["last_commit"] = proc.stdout.strip()

        # Fetch and check for updates (don't fail if offline)
        subprocess.run(
            ["git", "fetch", "--quiet"],
            cwd=repo_path,
            capture_output=True,
            timeout=10
        )

        # Check commits behind/ahead
        proc = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", "HEAD...@{upstream}"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        if proc.returncode == 0:
            parts = proc.stdout.strip().split()
            if len(parts) == 2:
                result["commits_ahead"] = int(parts[0])
                result["commits_behind"] = int(parts[1])

    except (subprocess.TimeoutExpired, Exception) as e:
        pass

    return result


def pull_updates(repo_path: Path) -> Tuple[bool, str]:
    """Pull updates from remote"""
    try:
        proc = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        if proc.returncode == 0:
            return True, proc.stdout.strip()
        else:
            return False, proc.stderr.strip()
    except Exception as e:
        return False, str(e)


def reinstall_from_repo(repo_path: Path) -> Tuple[bool, str]:
    """Reinstall from repository"""
    try:
        # Copy bin scripts
        for script in (repo_path / "bin").glob("*.py"):
            dest = INSTALL_DIR / "bin" / script.name
            shutil.copy2(script, dest)

        # Copy lib
        lib_src = repo_path / "lib"
        lib_dest = INSTALL_DIR / "lib"
        if lib_src.exists():
            shutil.rmtree(lib_dest, ignore_errors=True)
            shutil.copytree(lib_src, lib_dest)

        # Copy skills
        skills_src = repo_path / "skills"
        skills_dest = INSTALL_DIR / "skills"
        if skills_src.exists():
            shutil.rmtree(skills_dest, ignore_errors=True)
            shutil.copytree(skills_src, skills_dest)

        # Copy other directories
        for dirname in ["registry", "completions", "textbook", "data"]:
            src = repo_path / dirname
            dest = INSTALL_DIR / dirname
            if src.exists():
                shutil.rmtree(dest, ignore_errors=True)
                shutil.copytree(src, dest)

        # Make scripts executable
        for script in (INSTALL_DIR / "bin").glob("*.py"):
            script.chmod(0o755)

        return True, "Installation updated successfully"

    except Exception as e:
        return False, str(e)


def check_for_updates() -> Dict:
    """Check for available updates"""
    result = {
        "current_version": get_current_version(),
        "repo_path": None,
        "repo_version": None,
        "git_status": None,
        "update_available": False,
        "update_type": None,  # "version", "commits", or None
    }

    repo_path = get_source_repo()
    if not repo_path:
        result["error"] = "No source repository configured. Reinstall from git clone."
        return result

    result["repo_path"] = str(repo_path)
    result["repo_version"] = get_repo_version(repo_path)
    result["git_status"] = get_git_status(repo_path)

    # Check if version update available
    if result["repo_version"] and result["repo_version"] != result["current_version"]:
        result["update_available"] = True
        result["update_type"] = "version"

    # Check if git commits available
    git_status = result["git_status"]
    if git_status and git_status.get("commits_behind", 0) > 0:
        result["update_available"] = True
        result["update_type"] = "commits"

    return result


def print_status(status: Dict):
    """Print status information"""
    print("=" * 60)
    print("  ONT Ecosystem Update Status")
    print("=" * 60)
    print()

    print(f"Current Version: {status['current_version']}")

    if status.get("error"):
        print(f"\nError: {status['error']}")
        return

    print(f"Source Repo: {status['repo_path']}")

    if status["repo_version"]:
        print(f"Repo Version: {status['repo_version']}")

    git = status.get("git_status", {})
    if git.get("is_git_repo"):
        print()
        print("Git Status:")
        print(f"  Branch: {git.get('branch', 'unknown')}")
        print(f"  Last Commit: {git.get('last_commit', 'unknown')}")
        if git.get("has_changes"):
            print("  Local Changes: Yes (uncommitted)")
        if git.get("commits_behind", 0) > 0:
            print(f"  Updates Available: {git['commits_behind']} commits behind")
        if git.get("commits_ahead", 0) > 0:
            print(f"  Local Commits: {git['commits_ahead']} commits ahead")

    print()
    if status["update_available"]:
        print("Status: UPDATE AVAILABLE")
        print()
        print("Run 'ont_update.py --apply' to update")
    else:
        print("Status: UP TO DATE")

    print()
    print("=" * 60)


def apply_updates(status: Dict) -> bool:
    """Apply available updates"""
    if not status.get("update_available"):
        print("No updates available.")
        return True

    repo_path = Path(status["repo_path"])
    git_status = status.get("git_status", {})

    print("Applying updates...")
    print()

    # If there are remote commits, pull them
    if git_status.get("commits_behind", 0) > 0:
        print("Pulling updates from remote...")
        success, message = pull_updates(repo_path)
        if success:
            print(f"  {message}")
        else:
            print(f"  Error: {message}")
            print()
            print("Try manually: cd {} && git pull".format(repo_path))
            return False

    # Reinstall from repo
    print("Reinstalling from repository...")
    success, message = reinstall_from_repo(repo_path)
    if success:
        print(f"  {message}")

        # Show new version
        new_version = get_repo_version(repo_path)
        print()
        print(f"Updated to version: {new_version}")
        print()
        print("Restart your shell or run:")
        print(f"  source {INSTALL_DIR}/env.sh")
        return True
    else:
        print(f"  Error: {message}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="ONT Ecosystem Update",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--apply", action="store_true",
                        help="Apply available updates")
    parser.add_argument("--status", action="store_true",
                        help="Show detailed status")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    args = parser.parse_args()

    status = check_for_updates()

    if args.json:
        print(json.dumps(status, indent=2, default=str))
        return

    if args.apply:
        success = apply_updates(status)
        sys.exit(0 if success else 1)
    else:
        print_status(status)


if __name__ == "__main__":
    main()
