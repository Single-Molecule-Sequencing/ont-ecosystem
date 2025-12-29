#!/usr/bin/env python3
"""
ONT Ecosystem - Install Claude Code Skills

This script installs all ONT Ecosystem skills for Claude Code discovery.
Skills can be installed to:
- Project scope (.claude/skills/) - for team use
- User scope (~/.claude/skills/) - for personal use

Usage:
    ont_install_skills.py              # Install to project scope
    ont_install_skills.py --user       # Install to user scope
    ont_install_skills.py --list       # List available skills
    ont_install_skills.py --check      # Check installed skills
"""

import argparse
import shutil
import sys
from pathlib import Path


def get_skills_source() -> Path:
    """Get the source skills directory"""
    # Try relative to this script
    script_dir = Path(__file__).parent.parent
    skills_dir = script_dir / "skills"

    if skills_dir.exists():
        return skills_dir

    # Try current working directory
    cwd_skills = Path.cwd() / "skills"
    if cwd_skills.exists():
        return cwd_skills

    raise FileNotFoundError("Cannot find skills directory")


def get_available_skills(skills_dir: Path) -> dict:
    """Get all available skills with SKILL.md files"""
    skills = {}

    for skill_path in skills_dir.iterdir():
        if skill_path.is_dir():
            skill_md = skill_path / "SKILL.md"
            if skill_md.exists():
                # Parse name from SKILL.md frontmatter
                content = skill_md.read_text()
                name = skill_path.name
                description = ""

                if content.startswith("---"):
                    try:
                        import yaml
                        end = content.find("---", 3)
                        if end > 0:
                            frontmatter = yaml.safe_load(content[3:end])
                            name = frontmatter.get("name", skill_path.name)
                            description = frontmatter.get("description", "")[:100]
                    except Exception:
                        pass

                skills[skill_path.name] = {
                    "name": name,
                    "path": skill_path,
                    "skill_md": skill_md,
                    "description": description,
                }

    return skills


def install_skills(skills: dict, target_dir: Path, force: bool = False) -> int:
    """Install skills to target directory"""
    target_dir.mkdir(parents=True, exist_ok=True)

    installed = 0
    for skill_name, skill_info in skills.items():
        dest = target_dir / skill_name

        if dest.exists() and not force:
            print(f"  Skip: {skill_name} (already exists, use --force to overwrite)")
            continue

        # Create skill directory
        dest.mkdir(parents=True, exist_ok=True)

        # Copy SKILL.md
        shutil.copy2(skill_info["skill_md"], dest / "SKILL.md")

        print(f"  Installed: {skill_name}")
        installed += 1

    return installed


def check_skills(skills: dict, project_dir: Path, user_dir: Path) -> None:
    """Check which skills are installed where"""
    print("\nSkill Installation Status:")
    print("-" * 60)
    print(f"{'Skill':<25} {'Project':<12} {'User':<12}")
    print("-" * 60)

    for skill_name in sorted(skills.keys()):
        project_installed = (project_dir / skill_name / "SKILL.md").exists()
        user_installed = (user_dir / skill_name / "SKILL.md").exists()

        project_status = "Yes" if project_installed else "-"
        user_status = "Yes" if user_installed else "-"

        print(f"{skill_name:<25} {project_status:<12} {user_status:<12}")

    print("-" * 60)


def list_skills(skills: dict) -> None:
    """List available skills"""
    print("\nAvailable ONT Ecosystem Skills:")
    print("-" * 70)

    for skill_name in sorted(skills.keys()):
        info = skills[skill_name]
        desc = info["description"]
        if len(desc) > 50:
            desc = desc[:47] + "..."
        print(f"  {skill_name:<25} {desc}")

    print("-" * 70)
    print(f"\nTotal: {len(skills)} skills")


def main():
    parser = argparse.ArgumentParser(
        description="Install ONT Ecosystem skills for Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    ont_install_skills.py              # Install to project scope
    ont_install_skills.py --user       # Install to user scope
    ont_install_skills.py --both       # Install to both scopes
    ont_install_skills.py --list       # List available skills
    ont_install_skills.py --check      # Check installation status
"""
    )

    parser.add_argument("--user", action="store_true",
                        help="Install to user scope (~/.claude/skills/)")
    parser.add_argument("--both", action="store_true",
                        help="Install to both project and user scope")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing skills")
    parser.add_argument("--list", action="store_true",
                        help="List available skills")
    parser.add_argument("--check", action="store_true",
                        help="Check installed skills")

    args = parser.parse_args()

    # Find skills
    try:
        skills_dir = get_skills_source()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    skills = get_available_skills(skills_dir)

    if not skills:
        print("No skills found in skills/ directory")
        sys.exit(1)

    # Define target directories
    project_dir = Path.cwd() / ".claude" / "skills"
    user_dir = Path.home() / ".claude" / "skills"

    if args.list:
        list_skills(skills)
        return

    if args.check:
        check_skills(skills, project_dir, user_dir)
        return

    # Install skills
    print(f"\nONT Ecosystem Skill Installation")
    print("=" * 40)
    print(f"Source: {skills_dir}")
    print(f"Skills found: {len(skills)}")
    print()

    total_installed = 0

    if args.both:
        print(f"Installing to project scope ({project_dir}):")
        total_installed += install_skills(skills, project_dir, args.force)
        print()
        print(f"Installing to user scope ({user_dir}):")
        total_installed += install_skills(skills, user_dir, args.force)
    elif args.user:
        print(f"Installing to user scope ({user_dir}):")
        total_installed = install_skills(skills, user_dir, args.force)
    else:
        print(f"Installing to project scope ({project_dir}):")
        total_installed = install_skills(skills, project_dir, args.force)

    print()
    print(f"Installation complete: {total_installed} skills installed")
    print()
    print("Skills will be automatically available in Claude Code.")
    print("Use '/help' or ask 'What skills are available?' to see them.")


if __name__ == "__main__":
    main()
