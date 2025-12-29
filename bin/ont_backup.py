#!/usr/bin/env python3
"""
ONT Ecosystem Backup - Backup and restore registry data

Usage:
    ont_backup.py create                    # Create backup
    ont_backup.py create --output backup.tar.gz
    ont_backup.py list                      # List backups
    ont_backup.py restore backup.tar.gz    # Restore from backup
    ont_backup.py info backup.tar.gz       # Show backup info
"""

import argparse
import json
import os
import shutil
import sys
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add paths
bin_dir = Path(__file__).parent
lib_dir = bin_dir.parent / 'lib'
sys.path.insert(0, str(bin_dir))
sys.path.insert(0, str(lib_dir.parent))

try:
    from lib import __version__
except ImportError:
    __version__ = "3.0.0"

# Default directories
REGISTRY_DIR = Path(os.environ.get("ONT_REGISTRY_DIR", Path.home() / ".ont-registry"))
BACKUP_DIR = Path(os.environ.get("ONT_BACKUP_DIR", Path.home() / ".ont-backups"))
ECOSYSTEM_HOME = Path(os.environ.get("ONT_ECOSYSTEM_HOME", Path.home() / ".ont-ecosystem"))


def get_backup_dirs() -> List[Path]:
    """Get list of directories to backup"""
    dirs = []

    # Registry directory
    if REGISTRY_DIR.exists():
        dirs.append(REGISTRY_DIR)

    # Ecosystem config
    config_dir = ECOSYSTEM_HOME / "config"
    if config_dir.exists():
        dirs.append(config_dir)

    # Ecosystem logs
    logs_dir = ECOSYSTEM_HOME / "logs"
    if logs_dir.exists():
        dirs.append(logs_dir)

    return dirs


def get_backup_metadata() -> Dict:
    """Generate backup metadata"""
    return {
        "version": __version__,
        "created_at": datetime.now().isoformat(),
        "hostname": os.uname().nodename if hasattr(os, 'uname') else "unknown",
        "user": os.environ.get("USER", "unknown"),
        "registry_dir": str(REGISTRY_DIR),
        "ecosystem_home": str(ECOSYSTEM_HOME),
    }


def create_backup(output_path: Optional[Path] = None, verbose: bool = False) -> Path:
    """Create a backup archive"""
    # Ensure backup directory exists
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # Generate backup filename
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = BACKUP_DIR / f"ont-backup-{timestamp}.tar.gz"

    output_path = Path(output_path)

    if verbose:
        print(f"Creating backup: {output_path}")

    # Get directories to backup
    dirs = get_backup_dirs()

    if not dirs:
        print("Warning: No directories to backup")
        return output_path

    # Create metadata
    metadata = get_backup_metadata()
    metadata["directories"] = [str(d) for d in dirs]

    # Create temporary metadata file
    metadata_file = BACKUP_DIR / ".backup_metadata.json"
    metadata_file.write_text(json.dumps(metadata, indent=2))

    # Create archive
    with tarfile.open(output_path, "w:gz") as tar:
        # Add metadata
        tar.add(metadata_file, arcname="metadata.json")

        # Add directories
        for dir_path in dirs:
            arcname = dir_path.name
            if verbose:
                print(f"  Adding: {dir_path} -> {arcname}/")
            tar.add(dir_path, arcname=arcname)

    # Clean up metadata file
    metadata_file.unlink()

    # Get backup size
    size = output_path.stat().st_size
    if verbose:
        print()
        print(f"Backup created: {output_path}")
        print(f"Size: {format_size(size)}")

    return output_path


def list_backups() -> List[Dict]:
    """List available backups"""
    backups = []

    if not BACKUP_DIR.exists():
        return backups

    for backup_file in sorted(BACKUP_DIR.glob("ont-backup-*.tar.gz"), reverse=True):
        info = {
            "path": str(backup_file),
            "name": backup_file.name,
            "size": backup_file.stat().st_size,
            "modified": datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat(),
        }

        # Try to read metadata
        try:
            with tarfile.open(backup_file, "r:gz") as tar:
                metadata_member = tar.getmember("metadata.json")
                f = tar.extractfile(metadata_member)
                if f:
                    metadata = json.loads(f.read().decode())
                    info["version"] = metadata.get("version")
                    info["created_at"] = metadata.get("created_at")
        except Exception:
            pass

        backups.append(info)

    return backups


def get_backup_info(backup_path: Path) -> Optional[Dict]:
    """Get information about a backup"""
    if not backup_path.exists():
        return None

    info = {
        "path": str(backup_path),
        "name": backup_path.name,
        "size": backup_path.stat().st_size,
        "modified": datetime.fromtimestamp(backup_path.stat().st_mtime).isoformat(),
        "contents": [],
    }

    try:
        with tarfile.open(backup_path, "r:gz") as tar:
            # Read metadata
            try:
                metadata_member = tar.getmember("metadata.json")
                f = tar.extractfile(metadata_member)
                if f:
                    info["metadata"] = json.loads(f.read().decode())
            except KeyError:
                info["metadata"] = None

            # List contents
            for member in tar.getmembers():
                if member.name != "metadata.json":
                    info["contents"].append({
                        "name": member.name,
                        "size": member.size,
                        "is_dir": member.isdir(),
                    })

    except Exception as e:
        info["error"] = str(e)

    return info


def restore_backup(backup_path: Path, target_dir: Optional[Path] = None,
                   force: bool = False, verbose: bool = False) -> bool:
    """Restore from a backup"""
    if not backup_path.exists():
        print(f"Error: Backup not found: {backup_path}")
        return False

    # Determine target directory
    if target_dir is None:
        target_dir = Path.home()

    if verbose:
        print(f"Restoring from: {backup_path}")
        print(f"Target: {target_dir}")

    try:
        with tarfile.open(backup_path, "r:gz") as tar:
            # Read metadata
            try:
                metadata_member = tar.getmember("metadata.json")
                f = tar.extractfile(metadata_member)
                if f:
                    metadata = json.loads(f.read().decode())
                    if verbose:
                        print(f"Backup version: {metadata.get('version')}")
                        print(f"Created: {metadata.get('created_at')}")
            except KeyError:
                pass

            # Check for existing directories
            members = [m for m in tar.getmembers() if m.name != "metadata.json"]
            top_dirs = set()
            for m in members:
                top_dir = m.name.split("/")[0]
                top_dirs.add(top_dir)

            for top_dir in top_dirs:
                dest = target_dir / f".{top_dir}"  # Add dot prefix
                if dest.exists() and not force:
                    print(f"Warning: {dest} already exists")
                    response = input("Overwrite? [y/N]: ")
                    if response.lower() != 'y':
                        print("Aborted.")
                        return False
                    shutil.rmtree(dest)

            # Extract
            for member in members:
                # Remap paths
                parts = member.name.split("/")
                parts[0] = f".{parts[0]}"  # Add dot prefix to top-level dir
                member.name = "/".join(parts)

                if verbose:
                    print(f"  Extracting: {member.name}")

            tar.extractall(target_dir, members=members)

    except Exception as e:
        print(f"Error: {e}")
        return False

    if verbose:
        print()
        print("Restore complete!")

    return True


def format_size(size: int) -> str:
    """Format size in bytes to human-readable"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def cmd_create(args):
    """Create backup command"""
    output = Path(args.output) if args.output else None
    backup_path = create_backup(output, verbose=not args.quiet)
    print(backup_path)


def cmd_list(args):
    """List backups command"""
    backups = list_backups()

    if not backups:
        print("No backups found")
        print(f"Backup directory: {BACKUP_DIR}")
        return

    if args.json:
        print(json.dumps(backups, indent=2))
        return

    print(f"Backups in {BACKUP_DIR}:")
    print()
    for backup in backups:
        size = format_size(backup["size"])
        version = backup.get("version", "?")
        created = backup.get("created_at", backup["modified"])[:19]
        print(f"  {backup['name']:40} {size:>10}  v{version}  {created}")


def cmd_restore(args):
    """Restore backup command"""
    backup_path = Path(args.backup)
    target = Path(args.target) if args.target else None
    success = restore_backup(backup_path, target, args.force, verbose=True)
    sys.exit(0 if success else 1)


def cmd_info(args):
    """Show backup info command"""
    backup_path = Path(args.backup)
    info = get_backup_info(backup_path)

    if not info:
        print(f"Error: Cannot read backup: {backup_path}")
        sys.exit(1)

    if args.json:
        print(json.dumps(info, indent=2))
        return

    print(f"Backup: {info['name']}")
    print(f"Size: {format_size(info['size'])}")
    print(f"Modified: {info['modified']}")

    if info.get("metadata"):
        meta = info["metadata"]
        print()
        print("Metadata:")
        print(f"  Version: {meta.get('version')}")
        print(f"  Created: {meta.get('created_at')}")
        print(f"  Host: {meta.get('hostname')}")
        print(f"  User: {meta.get('user')}")

    if info.get("contents"):
        print()
        print("Contents:")
        dirs = set()
        files = 0
        total_size = 0
        for item in info["contents"]:
            if item["is_dir"]:
                dirs.add(item["name"].split("/")[0])
            else:
                files += 1
                total_size += item["size"]

        for d in sorted(dirs):
            print(f"  {d}/")
        print()
        print(f"  {len(dirs)} directories, {files} files, {format_size(total_size)} total")


def main():
    parser = argparse.ArgumentParser(
        description="ONT Ecosystem Backup",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Create
    p_create = subparsers.add_parser("create", help="Create backup")
    p_create.add_argument("-o", "--output", help="Output path")
    p_create.add_argument("-q", "--quiet", action="store_true", help="Quiet mode")
    p_create.set_defaults(func=cmd_create)

    # List
    p_list = subparsers.add_parser("list", help="List backups")
    p_list.add_argument("--json", action="store_true", help="JSON output")
    p_list.set_defaults(func=cmd_list)

    # Restore
    p_restore = subparsers.add_parser("restore", help="Restore backup")
    p_restore.add_argument("backup", help="Backup file path")
    p_restore.add_argument("-t", "--target", help="Target directory")
    p_restore.add_argument("-f", "--force", action="store_true", help="Force overwrite")
    p_restore.set_defaults(func=cmd_restore)

    # Info
    p_info = subparsers.add_parser("info", help="Show backup info")
    p_info.add_argument("backup", help="Backup file path")
    p_info.add_argument("--json", action="store_true", help="JSON output")
    p_info.set_defaults(func=cmd_info)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
