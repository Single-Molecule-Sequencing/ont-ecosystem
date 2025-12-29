#!/usr/bin/env python3
"""
Skill Maker - Automate Claude skill creation, updating, and distribution.

Usage:
    python skill_maker.py create <name> --description "..." [options]
    python skill_maker.py update <name> [options]
    python skill_maker.py package <name>|--all
    python skill_maker.py audit [name]
    python skill_maker.py sync
    python skill_maker.py list
    python skill_maker.py info <name>
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Find repository root
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = SKILL_DIR.parent.parent

SKILLS_DIR = REPO_ROOT / "skills"
INSTALLABLE_DIR = REPO_ROOT / "installable-skills"
ZIP_DIR = INSTALLABLE_DIR / "zip"
COMMANDS_DIR = REPO_ROOT / ".claude" / "commands"
USER_COMMANDS_DIR = Path.home() / ".claude" / "commands"


def load_yaml_frontmatter(content: str) -> Tuple[Dict, str]:
    """Extract YAML frontmatter from markdown content."""
    if not content.startswith('---'):
        return {}, content

    # Find the closing ---
    end_match = re.search(r'\n---\n', content[3:])
    if not end_match:
        return {}, content

    yaml_content = content[3:end_match.start() + 3]
    body = content[end_match.end() + 3 + 1:]

    # Simple YAML parsing (avoiding external dependency)
    metadata = {}
    current_key = None
    current_list = None

    for line in yaml_content.split('\n'):
        line = line.rstrip()
        if not line:
            continue

        # Check for list item
        if line.startswith('  - '):
            if current_list is not None:
                current_list.append(line[4:].strip())
            continue

        # Check for key: value
        if ':' in line:
            key, _, value = line.partition(':')
            key = key.strip()
            value = value.strip()

            if value:
                # Remove quotes
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                metadata[key] = value
                current_list = None
            else:
                # Start of list
                metadata[key] = []
                current_list = metadata[key]
            current_key = key

    return metadata, body


def create_yaml_frontmatter(metadata: Dict) -> str:
    """Create YAML frontmatter from dictionary."""
    lines = ['---']

    for key, value in metadata.items():
        if isinstance(value, list):
            lines.append(f'{key}:')
            for item in value:
                lines.append(f'  - {item}')
        elif isinstance(value, str) and ('\n' in value or ':' in value or '"' in value):
            lines.append(f'{key}: "{value}"')
        else:
            lines.append(f'{key}: "{value}"' if isinstance(value, str) else f'{key}: {value}')

    lines.append('---')
    return '\n'.join(lines)


def validate_skill_name(name: str) -> bool:
    """Validate skill name format."""
    if len(name) > 64:
        return False
    if not re.match(r'^[a-z0-9-]+$', name):
        return False
    if 'anthropic' in name.lower() or 'claude' in name.lower():
        return False
    return True


def get_skill_info(name: str) -> Optional[Dict]:
    """Get information about an existing skill."""
    skill_md = SKILLS_DIR / name / "SKILL.md"
    if not skill_md.exists():
        return None

    content = skill_md.read_text()
    metadata, body = load_yaml_frontmatter(content)

    # Check for scripts
    scripts_dir = SKILLS_DIR / name / "scripts"
    scripts = []
    if scripts_dir.exists():
        scripts = [f.name for f in scripts_dir.glob("*.py") if not f.name.startswith('__')]

    return {
        'name': name,
        'path': str(skill_md),
        'metadata': metadata,
        'scripts': scripts,
        'has_slash_command': (INSTALLABLE_DIR / name / f"{name}.md").exists(),
        'has_zip': (ZIP_DIR / f"{name}.zip").exists(),
        'in_commands': (COMMANDS_DIR / f"{name}.md").exists(),
    }


def list_skills() -> List[str]:
    """List all available skills."""
    skills = []
    for skill_dir in SKILLS_DIR.iterdir():
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            skills.append(skill_dir.name)
    return sorted(skills)


def create_skill(
    name: str,
    description: str,
    version: str = "1.0.0",
    category: str = "analysis",
    tags: List[str] = None,
    dependencies: List[str] = None,
    script_path: Optional[str] = None,
    force: bool = False
) -> bool:
    """Create a new skill from scratch."""

    # Validate name
    if not validate_skill_name(name):
        print(f"Error: Invalid skill name '{name}'")
        print("  - Must be lowercase letters, numbers, and hyphens only")
        print("  - Maximum 64 characters")
        print("  - Cannot contain 'anthropic' or 'claude'")
        return False

    # Check if exists
    skill_dir = SKILLS_DIR / name
    if skill_dir.exists() and not force:
        print(f"Error: Skill '{name}' already exists. Use --force to overwrite.")
        return False

    # Validate description
    if len(description) > 1024:
        print(f"Warning: Description exceeds 1024 chars, truncating...")
        description = description[:1021] + "..."

    print(f"Creating skill: {name}")

    # Create directories
    skill_dir.mkdir(parents=True, exist_ok=True)
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir(exist_ok=True)

    # Build metadata
    metadata = {
        'name': name,
        'version': version,
        'description': description,
        'author': 'ONT Ecosystem',
        'category': category,
        'command': f'/{name}',
        'tags': tags or [category],
        'dependencies': dependencies or [],
    }

    # Create SKILL.md
    skill_md_content = create_yaml_frontmatter(metadata)
    skill_md_content += f"""

# {name.replace('-', ' ').title()}

{description.split('. Use when')[0]}.

## Quick Start

```bash
# Basic usage
python skills/{name}/scripts/{name.replace('-', '_')}.py [arguments]

# With provenance tracking
ont_experiments.py run {name.replace('-', '_')} exp-001 [options]
```

## Usage

$ARGUMENTS

## Options

| Option | Description |
|--------|-------------|
| `--help` | Show help message |
| `--json FILE` | Output JSON results |
| `--verbose` | Verbose output |

## Examples

```bash
# Example 1
python skills/{name}/scripts/{name.replace('-', '_')}.py input_file --json results.json

# Example 2
python skills/{name}/scripts/{name.replace('-', '_')}.py input_dir --verbose
```

## Output

Results are saved to the specified output location.

## Dependencies

{chr(10).join(f'- {dep}' for dep in (dependencies or ['(none)']))}
"""

    (skill_dir / "SKILL.md").write_text(skill_md_content)
    print(f"  Created: {skill_dir / 'SKILL.md'}")

    # Copy or create script
    script_name = f"{name.replace('-', '_')}.py"
    target_script = scripts_dir / script_name

    if script_path and Path(script_path).exists():
        shutil.copy(script_path, target_script)
        print(f"  Copied script: {target_script}")
    else:
        # Create template script
        template = f'''#!/usr/bin/env python3
"""
{name.replace('-', ' ').title()} - {description.split('.')[0]}

Usage:
    python {script_name} [arguments]
"""

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="{description.split('.')[0]}"
    )
    parser.add_argument('input', help='Input file or directory')
    parser.add_argument('--json', help='Output JSON file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    # TODO: Implement skill logic here
    print(f"Processing: {{args.input}}")

    results = {{
        'status': 'success',
        'input': args.input,
    }}

    if args.json:
        with open(args.json, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to: {{args.json}}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
'''
        target_script.write_text(template)
        target_script.chmod(0o755)
        print(f"  Created template: {target_script}")

    # Create slash command
    create_slash_command(name, description)

    # Create ZIP
    create_zip(name)

    # Sync to commands directory
    sync_to_commands(name)

    print(f"\nSkill '{name}' created successfully!")
    print(f"\nNext steps:")
    print(f"  1. Edit the script: skills/{name}/scripts/{script_name}")
    print(f"  2. Update SKILL.md with detailed documentation")
    print(f"  3. Run: python skill_maker.py audit {name}")
    print(f"  4. Run: python skill_maker.py sync")

    return True


def create_slash_command(name: str, description: str) -> bool:
    """Create slash command markdown file."""
    cmd_dir = INSTALLABLE_DIR / name
    cmd_dir.mkdir(parents=True, exist_ok=True)

    # Get full SKILL.md content for reference
    skill_md = SKILLS_DIR / name / "SKILL.md"
    if skill_md.exists():
        content = skill_md.read_text()
        metadata, body = load_yaml_frontmatter(content)
        description = metadata.get('description', description)

    cmd_content = f"""---
description: {description}
---

# /{name}

{description.split('. Use when')[0]}.

## Usage

$ARGUMENTS

## Quick Start

```bash
# Basic usage
python skills/{name}/scripts/{name.replace('-', '_')}.py [input]

# With provenance tracking
ont_experiments.py run {name.replace('-', '_')} exp-001 [options]
```

## Options

See `/{name} --help` for all available options.

## Installation

```bash
# Clone repository
git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git

# Install to Claude commands
cp ont-ecosystem/installable-skills/{name}/{name}.md ~/.claude/commands/
```
"""

    cmd_file = cmd_dir / f"{name}.md"
    cmd_file.write_text(cmd_content)
    print(f"  Created slash command: {cmd_file}")
    return True


def create_zip(name: str) -> bool:
    """Create ZIP file for Claude Desktop/Web."""
    skill_dir = SKILLS_DIR / name
    if not skill_dir.exists():
        print(f"Error: Skill directory not found: {skill_dir}")
        return False

    ZIP_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = ZIP_DIR / f"{name}.zip"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_skill = Path(tmp) / name
        tmp_skill.mkdir()

        # Copy SKILL.md
        shutil.copy(skill_dir / "SKILL.md", tmp_skill / "SKILL.md")

        # Copy scripts (excluding __pycache__)
        scripts_src = skill_dir / "scripts"
        if scripts_src.exists():
            scripts_dst = tmp_skill / "scripts"
            scripts_dst.mkdir()
            for f in scripts_src.glob("*.py"):
                if not f.name.startswith('__'):
                    shutil.copy(f, scripts_dst / f.name)

        # Copy any additional .md files
        for md_file in skill_dir.glob("*.md"):
            if md_file.name != "SKILL.md":
                shutil.copy(md_file, tmp_skill / md_file.name)

        # Create ZIP
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in tmp_skill.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(tmp)
                    zf.write(file_path, arcname)

    print(f"  Created ZIP: {zip_path} ({zip_path.stat().st_size // 1024}KB)")
    return True


def sync_to_commands(name: str) -> bool:
    """Sync slash command to .claude/commands/."""
    src = INSTALLABLE_DIR / name / f"{name}.md"
    if not src.exists():
        print(f"Warning: Slash command not found: {src}")
        return False

    # Sync to project commands
    COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, COMMANDS_DIR / f"{name}.md")
    print(f"  Synced to: {COMMANDS_DIR / f'{name}.md'}")

    # Sync to user commands
    USER_COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, USER_COMMANDS_DIR / f"{name}.md")
    print(f"  Synced to: {USER_COMMANDS_DIR / f'{name}.md'}")

    return True


def update_skill(
    name: str,
    description: Optional[str] = None,
    version: Optional[str] = None,
    changelog: Optional[str] = None
) -> bool:
    """Update an existing skill."""
    skill_md = SKILLS_DIR / name / "SKILL.md"
    if not skill_md.exists():
        print(f"Error: Skill not found: {name}")
        return False

    print(f"Updating skill: {name}")

    content = skill_md.read_text()
    metadata, body = load_yaml_frontmatter(content)

    # Update metadata
    if description:
        metadata['description'] = description
    if version:
        metadata['version'] = version

    # Write updated SKILL.md
    new_content = create_yaml_frontmatter(metadata) + '\n' + body
    skill_md.write_text(new_content)
    print(f"  Updated: {skill_md}")

    # Regenerate slash command
    create_slash_command(name, metadata.get('description', ''))

    # Regenerate ZIP
    create_zip(name)

    # Sync to commands
    sync_to_commands(name)

    print(f"\nSkill '{name}' updated to version {metadata.get('version', 'unknown')}")
    return True


def audit_skill(name: Optional[str] = None) -> Dict:
    """Audit skill(s) for issues."""
    skills_to_audit = [name] if name else list_skills()
    results = {'passed': [], 'warnings': [], 'errors': []}

    print("Auditing skills...\n")

    for skill_name in skills_to_audit:
        issues = []
        warnings = []

        skill_dir = SKILLS_DIR / skill_name
        skill_md = skill_dir / "SKILL.md"

        # Check SKILL.md exists
        if not skill_md.exists():
            issues.append("SKILL.md not found")
            results['errors'].append((skill_name, issues))
            continue

        content = skill_md.read_text()
        metadata, body = load_yaml_frontmatter(content)

        # Check required fields
        if 'name' not in metadata:
            issues.append("Missing 'name' in frontmatter")
        elif metadata['name'] != skill_name:
            warnings.append(f"Name mismatch: '{metadata['name']}' vs directory '{skill_name}'")

        if 'description' not in metadata:
            issues.append("Missing 'description' in frontmatter")
        else:
            desc = metadata['description']
            if len(desc) > 1024:
                issues.append(f"Description too long ({len(desc)} > 1024 chars)")
            if 'use when' not in desc.lower():
                warnings.append("Description should include 'Use when...' trigger")

        # Check name format
        if not validate_skill_name(skill_name):
            issues.append(f"Invalid skill name format")

        # Check scripts
        scripts_dir = skill_dir / "scripts"
        if not scripts_dir.exists() or not list(scripts_dir.glob("*.py")):
            warnings.append("No Python scripts found")

        # Check artifacts
        if not (INSTALLABLE_DIR / skill_name / f"{skill_name}.md").exists():
            warnings.append("Slash command not found")

        if not (ZIP_DIR / f"{skill_name}.zip").exists():
            warnings.append("ZIP file not found")

        if not (COMMANDS_DIR / f"{skill_name}.md").exists():
            warnings.append("Not synced to .claude/commands/")

        # Report
        if issues:
            results['errors'].append((skill_name, issues))
            print(f"❌ {skill_name}")
            for issue in issues:
                print(f"   ERROR: {issue}")
        elif warnings:
            results['warnings'].append((skill_name, warnings))
            print(f"⚠️  {skill_name}")
            for warning in warnings:
                print(f"   WARNING: {warning}")
        else:
            results['passed'].append(skill_name)
            print(f"✓  {skill_name}")

    # Summary
    print(f"\n{'='*50}")
    print(f"Audit Summary")
    print(f"{'='*50}")
    print(f"Passed:   {len(results['passed'])}")
    print(f"Warnings: {len(results['warnings'])}")
    print(f"Errors:   {len(results['errors'])}")

    return results


def sync_all() -> bool:
    """Sync all skills to all platforms."""
    print("Syncing all skills...\n")

    skills = list_skills()

    for skill_name in skills:
        print(f"Processing: {skill_name}")

        # Ensure slash command exists
        skill_md = SKILLS_DIR / skill_name / "SKILL.md"
        if skill_md.exists():
            content = skill_md.read_text()
            metadata, _ = load_yaml_frontmatter(content)
            desc = metadata.get('description', '')

            # Create/update slash command
            create_slash_command(skill_name, desc)

            # Create/update ZIP
            create_zip(skill_name)

            # Sync to commands
            sync_to_commands(skill_name)

    print(f"\n✓ Synced {len(skills)} skills to all platforms")
    return True


def package_skills(name: Optional[str] = None) -> bool:
    """Package skill(s) as ZIP files."""
    if name:
        return create_zip(name)

    # Package all
    print("Packaging all skills...\n")
    skills = list_skills()

    for skill_name in skills:
        create_zip(skill_name)

    print(f"\n✓ Created {len(skills)} ZIP files in {ZIP_DIR}")
    return True


def show_info(name: str) -> bool:
    """Show detailed information about a skill."""
    info = get_skill_info(name)
    if not info:
        print(f"Error: Skill not found: {name}")
        return False

    print(f"\n{'='*50}")
    print(f"Skill: {name}")
    print(f"{'='*50}")
    print(f"Path: {info['path']}")
    print(f"Version: {info['metadata'].get('version', 'unknown')}")
    print(f"Category: {info['metadata'].get('category', 'unknown')}")
    print(f"Description: {info['metadata'].get('description', 'N/A')}")
    print(f"\nScripts: {', '.join(info['scripts']) or 'None'}")
    print(f"\nArtifacts:")
    print(f"  Slash command: {'✓' if info['has_slash_command'] else '✗'}")
    print(f"  ZIP file: {'✓' if info['has_zip'] else '✗'}")
    print(f"  In .claude/commands: {'✓' if info['in_commands'] else '✗'}")

    if info['metadata'].get('tags'):
        print(f"\nTags: {', '.join(info['metadata']['tags'])}")
    if info['metadata'].get('dependencies'):
        print(f"Dependencies: {', '.join(info['metadata']['dependencies'])}")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Skill Maker - Create, update, and manage Claude skills"
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new skill')
    create_parser.add_argument('name', help='Skill name (lowercase, hyphens)')
    create_parser.add_argument('--description', '-d', required=True, help='Skill description')
    create_parser.add_argument('--script', '-s', help='Path to main script')
    create_parser.add_argument('--version', '-v', default='1.0.0', help='Version')
    create_parser.add_argument('--category', '-c', default='analysis', help='Category')
    create_parser.add_argument('--tags', '-t', help='Comma-separated tags')
    create_parser.add_argument('--deps', help='Comma-separated dependencies')
    create_parser.add_argument('--force', '-f', action='store_true', help='Overwrite existing')

    # Update command
    update_parser = subparsers.add_parser('update', help='Update an existing skill')
    update_parser.add_argument('name', help='Skill name')
    update_parser.add_argument('--description', '-d', help='New description')
    update_parser.add_argument('--version', '-v', help='New version')
    update_parser.add_argument('--changelog', help='Changelog entry')

    # Package command
    package_parser = subparsers.add_parser('package', help='Package skill(s) as ZIP')
    package_parser.add_argument('name', nargs='?', help='Skill name (or --all)')
    package_parser.add_argument('--all', '-a', action='store_true', help='Package all skills')

    # Audit command
    audit_parser = subparsers.add_parser('audit', help='Audit skill(s) for issues')
    audit_parser.add_argument('name', nargs='?', help='Skill name (or all)')

    # Sync command
    subparsers.add_parser('sync', help='Sync skills to all platforms')

    # List command
    subparsers.add_parser('list', help='List all skills')

    # Info command
    info_parser = subparsers.add_parser('info', help='Show skill details')
    info_parser.add_argument('name', help='Skill name')

    args = parser.parse_args()

    if args.command == 'create':
        tags = args.tags.split(',') if args.tags else None
        deps = args.deps.split(',') if args.deps else None
        success = create_skill(
            args.name,
            args.description,
            args.version,
            args.category,
            tags,
            deps,
            args.script,
            args.force
        )
        sys.exit(0 if success else 1)

    elif args.command == 'update':
        success = update_skill(args.name, args.description, args.version, args.changelog)
        sys.exit(0 if success else 1)

    elif args.command == 'package':
        if args.all:
            success = package_skills()
        else:
            success = package_skills(args.name)
        sys.exit(0 if success else 1)

    elif args.command == 'audit':
        results = audit_skill(args.name)
        sys.exit(0 if not results['errors'] else 1)

    elif args.command == 'sync':
        success = sync_all()
        sys.exit(0 if success else 1)

    elif args.command == 'list':
        skills = list_skills()
        print(f"Available skills ({len(skills)}):\n")
        for skill in skills:
            info = get_skill_info(skill)
            version = info['metadata'].get('version', '?') if info else '?'
            print(f"  {skill} (v{version})")
        sys.exit(0)

    elif args.command == 'info':
        success = show_info(args.name)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
