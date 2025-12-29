#!/usr/bin/env python3
"""
ONT Changelog Generator

Generate changelog entries from git commits with conventional commit parsing.

Usage:
    ont_changelog.py                        # Generate since last tag
    ont_changelog.py --since v2.0.0         # Generate since specific tag
    ont_changelog.py --range v2.0.0..v3.0.0 # Generate for range
    ont_changelog.py --format markdown      # Output format
    ont_changelog.py --output CHANGELOG.md  # Write to file
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from lib import __version__
except ImportError:
    __version__ = "unknown"


# =============================================================================
# Conventional Commit Parsing
# =============================================================================

# Conventional commit types and their changelog sections
COMMIT_TYPES = {
    "feat": "Features",
    "fix": "Bug Fixes",
    "docs": "Documentation",
    "style": "Style",
    "refactor": "Refactoring",
    "perf": "Performance",
    "test": "Tests",
    "build": "Build",
    "ci": "CI/CD",
    "chore": "Chores",
    "revert": "Reverts",
}

# Types that should appear in user-facing changelog
USER_FACING_TYPES = ["feat", "fix", "perf", "docs", "revert"]

# Regex for conventional commit format
CONVENTIONAL_COMMIT_RE = re.compile(
    r"^(?P<type>\w+)"
    r"(?:\((?P<scope>[^)]+)\))?"
    r"(?P<breaking>!)?"
    r":\s*"
    r"(?P<description>.+)$",
    re.MULTILINE
)


def parse_conventional_commit(message: str) -> Optional[Dict[str, Any]]:
    """
    Parse a conventional commit message.

    Args:
        message: Full commit message

    Returns:
        Parsed commit dict or None if not conventional format
    """
    # Get first line (subject)
    subject = message.split("\n")[0].strip()

    match = CONVENTIONAL_COMMIT_RE.match(subject)
    if not match:
        return None

    return {
        "type": match.group("type"),
        "scope": match.group("scope"),
        "breaking": bool(match.group("breaking")),
        "description": match.group("description"),
        "body": "\n".join(message.split("\n")[1:]).strip(),
    }


# =============================================================================
# Git Operations
# =============================================================================

def run_git(args: List[str]) -> str:
    """Run git command and return output."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        check=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"Git command failed: {result.stderr}")
    return result.stdout.strip()


def get_latest_tag() -> Optional[str]:
    """Get the latest git tag."""
    try:
        return run_git(["describe", "--tags", "--abbrev=0"])
    except RuntimeError:
        return None


def get_all_tags() -> List[str]:
    """Get all git tags."""
    try:
        output = run_git(["tag", "-l", "--sort=-creatordate"])
        return [t for t in output.split("\n") if t]
    except RuntimeError:
        return []


def get_commits(since: Optional[str] = None, until: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get commits in range.

    Args:
        since: Start reference (tag/commit)
        until: End reference (default: HEAD)

    Returns:
        List of commit dicts
    """
    # Build range
    if since and until:
        ref_range = f"{since}..{until}"
    elif since:
        ref_range = f"{since}..HEAD"
    else:
        ref_range = "HEAD"

    # Format: hash|author|date|subject|body
    format_str = "%H|%an|%ai|%s|%b"
    separator = "---COMMIT---"

    try:
        output = run_git([
            "log",
            ref_range,
            f"--pretty=format:{format_str}{separator}",
            "--no-merges"
        ])
    except RuntimeError:
        return []

    commits = []
    for entry in output.split(separator):
        entry = entry.strip()
        if not entry:
            continue

        parts = entry.split("|", 4)
        if len(parts) < 4:
            continue

        hash_val, author, date, subject = parts[:4]
        body = parts[4] if len(parts) > 4 else ""

        # Parse conventional commit
        message = f"{subject}\n\n{body}".strip()
        parsed = parse_conventional_commit(message)

        commits.append({
            "hash": hash_val,
            "author": author,
            "date": date.split()[0],  # Just the date part
            "subject": subject,
            "body": body,
            "conventional": parsed,
        })

    return commits


# =============================================================================
# Changelog Generation
# =============================================================================

def group_commits_by_type(
    commits: List[Dict[str, Any]],
    user_facing_only: bool = True
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group commits by type.

    Args:
        commits: List of commit dicts
        user_facing_only: Only include user-facing types

    Returns:
        Dict mapping type to commits
    """
    groups: Dict[str, List[Dict[str, Any]]] = {}

    for commit in commits:
        conv = commit.get("conventional")
        if conv:
            commit_type = conv["type"]
            if user_facing_only and commit_type not in USER_FACING_TYPES:
                continue
        else:
            commit_type = "other"
            if user_facing_only:
                continue

        if commit_type not in groups:
            groups[commit_type] = []
        groups[commit_type].append(commit)

    return groups


def generate_changelog_entry(
    version: str,
    date: str,
    commits: List[Dict[str, Any]],
    user_facing_only: bool = True
) -> Dict[str, Any]:
    """
    Generate a changelog entry.

    Args:
        version: Version string
        date: Release date
        commits: List of commits
        user_facing_only: Only include user-facing changes

    Returns:
        Changelog entry dict
    """
    groups = group_commits_by_type(commits, user_facing_only)

    # Collect breaking changes
    breaking = []
    for commit in commits:
        conv = commit.get("conventional")
        if conv and conv.get("breaking"):
            breaking.append(commit)

    return {
        "version": version,
        "date": date,
        "breaking_changes": breaking,
        "sections": groups,
        "total_commits": len(commits),
    }


# =============================================================================
# Formatters
# =============================================================================

def format_markdown(entry: Dict[str, Any]) -> str:
    """Format changelog entry as Markdown."""
    lines = []

    # Header
    lines.append(f"## [{entry['version']}] - {entry['date']}")
    lines.append("")

    # Breaking changes
    if entry.get("breaking_changes"):
        lines.append("### Breaking Changes")
        lines.append("")
        for commit in entry["breaking_changes"]:
            conv = commit["conventional"]
            scope = f"**{conv['scope']}**: " if conv.get("scope") else ""
            lines.append(f"- {scope}{conv['description']}")
        lines.append("")

    # Sections
    for commit_type, commits in entry.get("sections", {}).items():
        section_title = COMMIT_TYPES.get(commit_type, commit_type.title())
        lines.append(f"### {section_title}")
        lines.append("")

        for commit in commits:
            conv = commit.get("conventional")
            if conv:
                scope = f"**{conv['scope']}**: " if conv.get("scope") else ""
                desc = conv["description"]
            else:
                scope = ""
                desc = commit["subject"]

            short_hash = commit["hash"][:7]
            lines.append(f"- {scope}{desc} ({short_hash})")

        lines.append("")

    return "\n".join(lines)


def format_text(entry: Dict[str, Any]) -> str:
    """Format changelog entry as plain text."""
    lines = []

    # Header
    lines.append(f"Version {entry['version']} ({entry['date']})")
    lines.append("=" * 50)
    lines.append("")

    # Breaking changes
    if entry.get("breaking_changes"):
        lines.append("BREAKING CHANGES:")
        for commit in entry["breaking_changes"]:
            conv = commit["conventional"]
            lines.append(f"  - {conv['description']}")
        lines.append("")

    # Sections
    for commit_type, commits in entry.get("sections", {}).items():
        section_title = COMMIT_TYPES.get(commit_type, commit_type.title())
        lines.append(f"{section_title}:")

        for commit in commits:
            conv = commit.get("conventional")
            if conv:
                desc = conv["description"]
            else:
                desc = commit["subject"]
            lines.append(f"  - {desc}")

        lines.append("")

    return "\n".join(lines)


def format_json(entry: Dict[str, Any]) -> str:
    """Format changelog entry as JSON."""
    return json.dumps(entry, indent=2, default=str)


FORMATTERS = {
    "markdown": format_markdown,
    "md": format_markdown,
    "text": format_text,
    "txt": format_text,
    "json": format_json,
}


# =============================================================================
# CLI Commands
# =============================================================================

def cmd_generate(args):
    """Generate changelog."""
    # Determine range
    if args.range:
        if ".." in args.range:
            since, until = args.range.split("..", 1)
        else:
            since = args.range
            until = "HEAD"
    else:
        since = args.since or get_latest_tag()
        until = "HEAD"

    # Get commits
    commits = get_commits(since, until)

    if not commits:
        if not args.quiet:
            print(f"No commits found since {since or 'beginning'}")
        return 0

    # Generate entry
    version = args.version or until
    date = args.date or datetime.now().strftime("%Y-%m-%d")

    entry = generate_changelog_entry(
        version=version,
        date=date,
        commits=commits,
        user_facing_only=not args.all
    )

    # Format output
    formatter = FORMATTERS.get(args.format, format_markdown)
    output = formatter(entry)

    # Write or print
    if args.output:
        output_path = Path(args.output)
        if args.prepend and output_path.exists():
            existing = output_path.read_text()
            output = output + "\n" + existing
        output_path.write_text(output)
        if not args.quiet:
            print(f"Wrote changelog to {args.output}")
    else:
        print(output)

    return 0


def cmd_tags(args):
    """List available tags."""
    tags = get_all_tags()

    if args.json:
        print(json.dumps(tags, indent=2))
    else:
        if not tags:
            print("No tags found")
        else:
            print("Available tags:")
            for tag in tags:
                print(f"  {tag}")

    return 0


def cmd_unreleased(args):
    """Show unreleased changes."""
    latest_tag = get_latest_tag()
    commits = get_commits(since=latest_tag)

    if not commits:
        print("No unreleased changes")
        return 0

    # Generate entry
    entry = generate_changelog_entry(
        version="Unreleased",
        date=datetime.now().strftime("%Y-%m-%d"),
        commits=commits,
        user_facing_only=not args.all
    )

    # Format
    formatter = FORMATTERS.get(args.format, format_markdown)
    print(formatter(entry))

    return 0


def cmd_stats(args):
    """Show commit statistics."""
    since = args.since or get_latest_tag()
    commits = get_commits(since=since)

    if not commits:
        print(f"No commits since {since or 'beginning'}")
        return 0

    # Count by type
    type_counts: Dict[str, int] = {}
    author_counts: Dict[str, int] = {}
    breaking_count = 0

    for commit in commits:
        conv = commit.get("conventional")
        if conv:
            commit_type = conv["type"]
            type_counts[commit_type] = type_counts.get(commit_type, 0) + 1
            if conv.get("breaking"):
                breaking_count += 1
        else:
            type_counts["other"] = type_counts.get("other", 0) + 1

        author = commit["author"]
        author_counts[author] = author_counts.get(author, 0) + 1

    if args.json:
        print(json.dumps({
            "since": since,
            "total_commits": len(commits),
            "breaking_changes": breaking_count,
            "by_type": type_counts,
            "by_author": author_counts,
        }, indent=2))
    else:
        print(f"Commits since {since or 'beginning'}: {len(commits)}")
        print(f"Breaking changes: {breaking_count}")
        print()
        print("By type:")
        for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            print(f"  {t}: {count}")
        print()
        print("By author:")
        for a, count in sorted(author_counts.items(), key=lambda x: -x[1]):
            print(f"  {a}: {count}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="ONT Changelog Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ont_changelog.py                          # Changes since last tag
  ont_changelog.py --since v2.0.0           # Changes since v2.0.0
  ont_changelog.py --range v2.0.0..v3.0.0   # Changes in range
  ont_changelog.py unreleased               # Show unreleased changes
  ont_changelog.py stats                    # Commit statistics
  ont_changelog.py tags                     # List available tags
"""
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    # Generate command (default)
    p_gen = subparsers.add_parser("generate", help="Generate changelog")
    p_gen.add_argument("--since", help="Start reference (tag/commit)")
    p_gen.add_argument("--range", help="Commit range (e.g., v1.0..v2.0)")
    p_gen.add_argument("--version", "-v", dest="version", help="Version string for header")
    p_gen.add_argument("--date", "-d", help="Release date (default: today)")
    p_gen.add_argument("--format", "-f", choices=list(FORMATTERS.keys()),
                      default="markdown", help="Output format")
    p_gen.add_argument("--output", "-o", help="Output file")
    p_gen.add_argument("--prepend", action="store_true",
                      help="Prepend to existing file")
    p_gen.add_argument("--all", "-a", action="store_true",
                      help="Include all commit types (not just user-facing)")
    p_gen.add_argument("--quiet", "-q", action="store_true",
                      help="Suppress informational messages")
    p_gen.set_defaults(func=cmd_generate)

    # Tags command
    p_tags = subparsers.add_parser("tags", help="List available tags")
    p_tags.add_argument("--json", "-j", action="store_true", help="JSON output")
    p_tags.set_defaults(func=cmd_tags)

    # Unreleased command
    p_unrel = subparsers.add_parser("unreleased", help="Show unreleased changes")
    p_unrel.add_argument("--format", "-f", choices=list(FORMATTERS.keys()),
                        default="markdown", help="Output format")
    p_unrel.add_argument("--all", "-a", action="store_true",
                        help="Include all commit types")
    p_unrel.set_defaults(func=cmd_unreleased)

    # Stats command
    p_stats = subparsers.add_parser("stats", help="Show commit statistics")
    p_stats.add_argument("--since", help="Start reference")
    p_stats.add_argument("--json", "-j", action="store_true", help="JSON output")
    p_stats.set_defaults(func=cmd_stats)

    args = parser.parse_args()

    # Default to generate if no command
    if not args.command:
        # Re-parse with generate defaults
        args = parser.parse_args(["generate"] + sys.argv[1:])

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
