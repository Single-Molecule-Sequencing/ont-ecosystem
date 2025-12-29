---
name: skill-maker
description: Create, update, and manage Claude skills automatically. Use when developing
  new analysis functions, fixing skill bugs, improving existing skills, or packaging
  skills for distribution. Handles SKILL.md creation, slash commands, ZIP packaging,
  and ecosystem integration.
metadata:
  version: 1.0.0
  author: ONT Ecosystem
  category: meta
  command: /skill-maker
  tags:
  - meta
  - automation
  - skill-creation
  - packaging
  - integration
  dependencies:
  - pyyaml
  inputs:
  - skill name
  - skill description
  - script files
  outputs:
  - SKILL.md
  - slash command (.md)
  - ZIP file for Desktop/Web
---

# Skill Maker

Automates the creation, updating, and distribution of Claude skills across all platforms.

## When to Use This Skill

Claude should automatically invoke this skill when:
- A new analysis function or workflow is developed
- An existing skill has bugs that need fixing
- A skill can be significantly improved
- New functionality should be packaged for distribution
- Skills need to be synchronized across platforms

## Quick Start

```bash
# Create a new skill
python skills/skill-maker/scripts/skill_maker.py create my-new-skill \
    --description "What it does. Use when..." \
    --script /path/to/script.py

# Update an existing skill
python skills/skill-maker/scripts/skill_maker.py update end-reason \
    --description "Updated description" \
    --version "1.1.0"

# Package all skills for distribution
python skills/skill-maker/scripts/skill_maker.py package --all

# Check skill health and suggest improvements
python skills/skill-maker/scripts/skill_maker.py audit

# Sync skills across all platforms
python skills/skill-maker/scripts/skill_maker.py sync
```

## Automated Triggers

The skill-maker automatically activates when Claude detects:

1. **New Function Development**
   - New Python scripts created in `skills/*/scripts/`
   - New analysis workflows implemented
   - New CLI tools developed

2. **Bug Fixes**
   - Errors reported in existing skills
   - Test failures in skill scripts
   - User-reported issues

3. **Improvements**
   - Performance optimizations
   - New features added to existing functions
   - Documentation updates needed

## Skill Creation Workflow

When creating a new skill, skill-maker:

1. **Generates SKILL.md** with proper YAML frontmatter
   - `name`: lowercase, hyphens only (max 64 chars)
   - `description`: what it does + when to use (max 1024 chars)
   - Version, author, category, tags, dependencies

2. **Creates Slash Command** for Claude Code
   - Generates `installable-skills/{name}/{name}.md`
   - Adds YAML frontmatter with description
   - Syncs to `.claude/commands/`

3. **Packages ZIP** for Claude Desktop/Web
   - Creates `installable-skills/zip/{name}.zip`
   - Includes SKILL.md and scripts
   - Excludes __pycache__ and .pyc files

4. **Integrates with Ecosystem**
   - Updates install-all.sh
   - Updates README.md skill lists
   - Registers in ont_experiments.py if analysis skill

## Skill Update Workflow

When updating an existing skill:

1. **Version Bump**
   - Increments version in SKILL.md
   - Updates changelog if present

2. **Regenerates Artifacts**
   - Updates slash command file
   - Regenerates ZIP file
   - Syncs to .claude/commands/

3. **Validates Changes**
   - Runs skill audit
   - Checks YAML frontmatter
   - Verifies script imports

## Commands

| Command | Description |
|---------|-------------|
| `create <name>` | Create new skill from scratch |
| `update <name>` | Update existing skill |
| `package <name>` | Generate ZIP for single skill |
| `package --all` | Generate ZIPs for all skills |
| `audit` | Check all skills for issues |
| `sync` | Sync skills to all platforms |
| `list` | List all available skills |
| `info <name>` | Show skill details |

## Options

| Option | Description |
|--------|-------------|
| `--description` | Skill description (required for create) |
| `--script` | Path to main script file |
| `--version` | Version string (default: 1.0.0) |
| `--category` | Skill category (analysis, meta, utility) |
| `--tags` | Comma-separated tags |
| `--deps` | Comma-separated Python dependencies |
| `--force` | Overwrite existing files |

## Skill Quality Guidelines

### Description Best Practices

Good descriptions include:
- What the skill does (specific actions)
- When to use it (trigger keywords)
- Requirements or prerequisites

```yaml
# Good
description: "Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction."

# Bad
description: "Helps with documents"
```

### SKILL.md Structure

```yaml
---
name: skill-name
version: "1.0.0"
description: "What it does. Use when..."
author: "Your Name"
category: analysis
tags:
  - relevant
  - tags
dependencies:
  - required
  - packages
---

# Skill Name

## Overview
Brief description of the skill.

## Quick Start
Basic usage examples.

## Commands
Available commands/options.

## Examples
Detailed usage examples.
```

## Audit Checks

The audit command checks for:

1. **YAML Frontmatter**
   - Required fields present (name, description)
   - Name format valid (lowercase, hyphens)
   - Description under 1024 chars

2. **File Structure**
   - SKILL.md exists
   - Scripts are executable
   - No broken imports

3. **Consistency**
   - Version numbers match
   - Slash command exists
   - ZIP file is current

4. **Quality**
   - Description includes trigger keywords
   - Examples are provided
   - Dependencies listed

## Integration Points

### ont_experiments.py
Analysis skills are auto-registered:
```python
ANALYSIS_SKILLS = {
    'end_reasons': 'skills/end-reason/scripts/end_reason.py',
    'basecalling': 'skills/dorado-bench-v2/scripts/dorado_basecall.py',
    # ... auto-added by skill-maker
}
```

### .claude/commands/
Slash commands auto-synced:
```
.claude/commands/
├── comprehensive-analysis.md
├── end-reason.md
├── skill-maker.md  # This skill
└── ...
```

### installable-skills/zip/
ZIP files auto-generated:
```
installable-skills/zip/
├── comprehensive-analysis.zip
├── end-reason.zip
├── skill-maker.zip  # This skill
└── ...
```

## Example: Creating a New Analysis Skill

```bash
# 1. Develop your analysis script
vim skills/my-analysis/scripts/my_analysis.py

# 2. Create the skill
python skills/skill-maker/scripts/skill_maker.py create my-analysis \
    --description "Analyze XYZ data with ABC method. Use when processing XYZ files or running ABC analysis." \
    --script skills/my-analysis/scripts/my_analysis.py \
    --category analysis \
    --tags "analysis,xyz,abc" \
    --deps "numpy,pandas"

# 3. Verify
python skills/skill-maker/scripts/skill_maker.py audit my-analysis

# 4. Package and sync
python skills/skill-maker/scripts/skill_maker.py sync
```

## Example: Fixing a Bug in Existing Skill

```bash
# 1. Fix the bug in the script
vim skills/end-reason/scripts/end_reason.py

# 2. Update the skill version
python skills/skill-maker/scripts/skill_maker.py update end-reason \
    --version "1.1.1" \
    --changelog "Fixed edge case in end_reason parsing"

# 3. Regenerate artifacts
python skills/skill-maker/scripts/skill_maker.py package end-reason
python skills/skill-maker/scripts/skill_maker.py sync
```

## Automatic Improvement Detection

When Claude notices potential improvements during conversation:

1. **Performance Issues**
   - Slow execution reported
   - Memory usage concerns
   - Inefficient algorithms identified

2. **Missing Features**
   - User requests unsupported functionality
   - Common workarounds needed
   - Feature gaps identified

3. **Documentation Gaps**
   - Unclear instructions
   - Missing examples
   - Outdated information

Claude will:
1. Note the improvement opportunity
2. Propose changes to the skill
3. Use skill-maker to implement updates
4. Sync changes across platforms
