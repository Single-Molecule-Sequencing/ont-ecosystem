#!/usr/bin/env python3
"""
schedule.py - Cron job management for Great Lakes discovery

Manages scheduled discovery jobs:
- Install weekly cron job
- Remove scheduled job
- Show status of scheduled jobs

Part of: https://github.com/Single-Molecule-Sequencing/ont-ecosystem
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Configuration
GREATLAKES_CONFIG = {
    'sync_dir': '/nfs/turbo/umms-atheylab/.ont-sync',
    'logs_dir': '/nfs/turbo/umms-atheylab/logs',
}

CRON_MARKER = '# ONT-GREATLAKES-SYNC'

WRAPPER_SCRIPT = """#!/bin/bash
# ONT Experiment Discovery - Scheduled Job
# Generated: {timestamp}
# {cron_marker}

set -euo pipefail

LOG_DIR="{logs_dir}"
SYNC_DIR="{sync_dir}"
SCRIPT_DIR="{script_dir}"

# Create log directory
mkdir -p "$LOG_DIR"

# Timestamp for this run
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/scheduled_discovery_$TIMESTAMP.log"

echo "=== Scheduled Discovery Job ===" >> "$LOG_FILE"
echo "Time: $(date)" >> "$LOG_FILE"

# Submit discovery job
cd "$SCRIPT_DIR"
python3 greatlakes_sync.py discover --submit {notify_flag} >> "$LOG_FILE" 2>&1

echo "Job submitted. See SLURM logs for details." >> "$LOG_FILE"
"""

DAY_MAP = {
    'sunday': 0, 'sun': 0,
    'monday': 1, 'mon': 1,
    'tuesday': 2, 'tue': 2,
    'wednesday': 3, 'wed': 3,
    'thursday': 4, 'thu': 4,
    'friday': 5, 'fri': 5,
    'saturday': 6, 'sat': 6,
}


def get_script_dir() -> Path:
    """Get the directory containing the sync scripts."""
    return Path(__file__).parent


def get_wrapper_path() -> Path:
    """Get the path to the wrapper script."""
    return Path(GREATLAKES_CONFIG['sync_dir']) / 'run_discovery.sh'


def create_wrapper_script(notify_email: Optional[str] = None) -> Path:
    """Create the wrapper script for cron execution."""
    wrapper_path = get_wrapper_path()
    wrapper_path.parent.mkdir(parents=True, exist_ok=True)

    notify_flag = f"--notify {notify_email}" if notify_email else ""

    content = WRAPPER_SCRIPT.format(
        timestamp=datetime.now().isoformat(),
        cron_marker=CRON_MARKER,
        logs_dir=GREATLAKES_CONFIG['logs_dir'],
        sync_dir=GREATLAKES_CONFIG['sync_dir'],
        script_dir=get_script_dir(),
        notify_flag=notify_flag,
    )

    with open(wrapper_path, 'w') as f:
        f.write(content)

    os.chmod(wrapper_path, 0o755)
    return wrapper_path


def get_current_crontab() -> str:
    """Get the current user's crontab."""
    try:
        result = subprocess.run(
            ['crontab', '-l'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout
        return ""
    except FileNotFoundError:
        print("Warning: crontab command not found")
        return ""


def set_crontab(content: str) -> bool:
    """Set the user's crontab."""
    try:
        process = subprocess.Popen(
            ['crontab', '-'],
            stdin=subprocess.PIPE,
            text=True
        )
        process.communicate(input=content)
        return process.returncode == 0
    except FileNotFoundError:
        print("Error: crontab command not found")
        return False


def install_cron(
    weekly: bool = True,
    day: str = 'sunday',
    hour: int = 2,
    notify_email: Optional[str] = None
) -> int:
    """
    Install cron job for scheduled discovery.

    Args:
        weekly: Run weekly (True) or daily (False)
        day: Day of week for weekly jobs
        hour: Hour to run (0-23)
        notify_email: Email for notifications

    Returns:
        Exit code (0 for success)
    """
    print("Installing scheduled discovery job...")

    # Create wrapper script
    wrapper_path = create_wrapper_script(notify_email)
    print(f"Created wrapper script: {wrapper_path}")

    # Build cron schedule
    if weekly:
        day_num = DAY_MAP.get(day.lower(), 0)
        schedule = f"0 {hour} * * {day_num}"
        schedule_desc = f"weekly on {day} at {hour:02d}:00"
    else:
        schedule = f"0 {hour} * * *"
        schedule_desc = f"daily at {hour:02d}:00"

    cron_line = f"{schedule} {wrapper_path} {CRON_MARKER}"

    # Get current crontab and remove old entries
    current = get_current_crontab()
    lines = [
        line for line in current.splitlines()
        if CRON_MARKER not in line
    ]

    # Add new entry
    lines.append(cron_line)
    new_crontab = "\n".join(lines) + "\n"

    # Install
    if set_crontab(new_crontab):
        print(f"Installed cron job: {schedule_desc}")
        print(f"Cron entry: {cron_line}")
        return 0
    else:
        print("Failed to install cron job")
        return 1


def remove_cron() -> int:
    """
    Remove scheduled discovery cron job.

    Returns:
        Exit code (0 for success)
    """
    print("Removing scheduled discovery job...")

    # Get current crontab
    current = get_current_crontab()
    if not current:
        print("No crontab found")
        return 0

    # Remove our entries
    lines = [
        line for line in current.splitlines()
        if CRON_MARKER not in line
    ]

    # Check if anything was removed
    if len(lines) == len(current.splitlines()):
        print("No scheduled discovery job found")
        return 0

    new_crontab = "\n".join(lines) + "\n" if lines else ""

    if set_crontab(new_crontab):
        print("Removed scheduled discovery job")

        # Also remove wrapper script
        wrapper_path = get_wrapper_path()
        if wrapper_path.exists():
            wrapper_path.unlink()
            print(f"Removed wrapper script: {wrapper_path}")

        return 0
    else:
        print("Failed to update crontab")
        return 1


def show_status() -> int:
    """
    Show status of scheduled discovery job.

    Returns:
        Exit code (0 for success)
    """
    print("Scheduled Discovery Job Status")
    print("=" * 40)

    # Check crontab
    current = get_current_crontab()
    cron_lines = [
        line for line in current.splitlines()
        if CRON_MARKER in line
    ]

    if cron_lines:
        print("Status: ACTIVE")
        print()
        print("Cron entry:")
        for line in cron_lines:
            # Parse schedule
            parts = line.split()
            if len(parts) >= 5:
                minute, hour, dom, month, dow = parts[:5]
                day_names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
                if dow != '*':
                    day_name = day_names[int(dow)]
                    print(f"  Schedule: {day_name} at {hour}:{minute}")
                else:
                    print(f"  Schedule: Daily at {hour}:{minute}")
            print(f"  Raw: {line}")
    else:
        print("Status: NOT INSTALLED")
        print()
        print("To install:")
        print("  greatlakes_sync.py schedule install --weekly")

    # Check wrapper script
    wrapper_path = get_wrapper_path()
    print()
    print("Wrapper script:")
    if wrapper_path.exists():
        print(f"  Path: {wrapper_path}")
        print(f"  Size: {wrapper_path.stat().st_size} bytes")
        mtime = datetime.fromtimestamp(wrapper_path.stat().st_mtime)
        print(f"  Modified: {mtime.isoformat()}")
    else:
        print("  Not found")

    # Check recent logs
    logs_dir = Path(GREATLAKES_CONFIG['logs_dir'])
    if logs_dir.exists():
        logs = sorted(logs_dir.glob('scheduled_discovery_*.log'), reverse=True)
        if logs:
            print()
            print("Recent scheduled runs:")
            for log in logs[:5]:
                mtime = datetime.fromtimestamp(log.stat().st_mtime)
                print(f"  {mtime.isoformat()} - {log.name}")

    return 0


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Manage scheduled discovery jobs'
    )
    parser.add_argument('action', choices=['install', 'remove', 'status'],
                        help='Action to perform')
    parser.add_argument('--weekly', action='store_true',
                        help='Run weekly (default)')
    parser.add_argument('--daily', action='store_true',
                        help='Run daily instead of weekly')
    parser.add_argument('--day', default='sunday',
                        help='Day of week for weekly jobs')
    parser.add_argument('--hour', type=int, default=2,
                        help='Hour to run (0-23)')
    parser.add_argument('--notify', metavar='EMAIL',
                        help='Email for notifications')

    args = parser.parse_args()

    if args.action == 'install':
        weekly = not args.daily
        return install_cron(
            weekly=weekly,
            day=args.day,
            hour=args.hour,
            notify_email=args.notify
        )
    elif args.action == 'remove':
        return remove_cron()
    elif args.action == 'status':
        return show_status()

    return 0


if __name__ == '__main__':
    sys.exit(main())
