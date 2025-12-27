# Skill Development Guide

Complete guide for developing, testing, and deploying skills for the ONT Ecosystem.

## Overview

The ONT Ecosystem uses a **dual-location skill architecture**:

1. **`bin/`** - Standalone executable scripts for CLI usage
2. **`skills/`** - Packaged skills for Claude integration

Both locations contain the same code, enabling:
- Direct CLI execution without Claude
- Claude-assisted workflows with provenance tracking
- Flexible deployment options

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Claude Projects                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ .skill file  │  │ .skill file  │  │ CLAUDE.md    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    ont-experiments.py                        │
│                   (Core Orchestrator)                        │
│  - Experiment registry management                            │
│  - Provenance tracking (Pattern B)                          │
│  - Skill invocation and result capture                      │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │end_reason│        │ ont_align│        │ont_monitor│
    │   .py    │        │   .py    │        │   .py    │
    └──────────┘        └──────────┘        └──────────┘
```

## Creating a New Skill

### Step 1: Plan Your Skill

Define:
- **Purpose**: What problem does it solve?
- **Inputs**: What data does it need?
- **Outputs**: JSON fields, plots, reports?
- **Integration**: How does it fit with existing skills?

### Step 2: Create Directory Structure

```bash
# Create skill directory
mkdir -p skills/my-new-skill/scripts
mkdir -p skills/my-new-skill/assets      # Optional
mkdir -p skills/my-new-skill/references  # Optional

# Create main files
touch skills/my-new-skill/SKILL.md
touch skills/my-new-skill/scripts/my_script.py
```

### Step 3: Implement the Script

Follow the template in `docs/SKILL_TEMPLATE.md`. Key requirements:

#### Required Features

```python
#!/usr/bin/env python3
"""
Docstring with:
- Description
- Pattern B integration example
- Standalone usage example
- Output fields documentation
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

VERSION = "1.0.0"

def main():
    parser = argparse.ArgumentParser(...)

    # Required arguments
    parser.add_argument('path', help='Input data path')

    # Standard options
    parser.add_argument('--json', type=Path, help='JSON output file')
    parser.add_argument('--quiet', '-q', action='store_true')
    parser.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')

    args = parser.parse_args()

    # ... implementation ...

    # IMPORTANT: Print machine-readable output for Pattern B capture
    print(json.dumps({
        'experiment_id': experiment_id,
        'key_metric': value,
        'quality_status': status,
    }))

if __name__ == '__main__':
    main()
```

#### Graceful Dependency Handling

```python
# Optional imports with fallback
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# Check before use
def generate_plot(data, output_path):
    if not HAS_MATPLOTLIB:
        raise ImportError("matplotlib required: pip install matplotlib")
    # ... plotting code ...
```

#### Dataclass Results Pattern

```python
from dataclasses import dataclass, asdict

@dataclass
class AnalysisResult:
    experiment_id: str
    metric_1: float
    metric_2: float
    quality_status: str
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
```

### Step 4: Write Documentation (SKILL.md)

Follow the template structure:

```markdown
---
name: my-new-skill
version: 1.0.0
description: One-line description
author: Your Name
category: analysis
tags: [nanopore, analysis]
---

# My New Skill

## Features
## Installation
## Usage
## Command-Line Options
## Output Format
## Examples
## Integration
## Troubleshooting
## Version History
```

### Step 5: Create Standalone Executable

```bash
# Copy to bin/
cp skills/my-new-skill/scripts/my_script.py bin/

# Make executable
chmod +x bin/my_script.py

# Optionally create standalone docs
cp skills/my-new-skill/SKILL.md bin/my_script_SKILL.md
```

### Step 6: Register Version

Edit `lib/__init__.py`:

```python
SKILL_VERSIONS = {
    # ... existing skills ...
    "my-new-skill": "1.0.0",
}
```

### Step 7: Package the Skill

```bash
# Create ZIP package
cd skills/my-new-skill
zip -r ../my-new-skill.skill SKILL.md scripts/

# Verify
unzip -l ../my-new-skill.skill
```

### Step 8: Test

```bash
# Test standalone
python3 bin/my_script.py /path/to/test/data --json test.json

# Test with ont-experiments (if integrated)
python3 bin/ont_experiments.py run my_command exp-test --json test.json

# Run unit tests
pytest tests/test_my_skill.py
```

### Step 9: Update Documentation

1. Add to `CLAUDE.md` skill directory table
2. Add to `docs/SKILLS.md`
3. Update `README.md` if needed

---

## Pattern B Integration

Pattern B enables provenance tracking through ont-experiments.

### Registering with ont-experiments

Edit `bin/ont_experiments.py` to add your skill:

```python
# In the SKILL_COMMANDS dictionary
SKILL_COMMANDS = {
    # ... existing commands ...
    'my_command': {
        'script': 'my_script.py',
        'description': 'Run my analysis',
        'requires': ['data'],
    },
}
```

### Output Requirements for Pattern B

Your script must print JSON to stdout for capture:

```python
# At end of main(), print machine-readable output
result = {
    'experiment_id': exp_id,
    'primary_metric': value,
    'quality_status': 'OK',  # OK, CHECK, or FAIL
}
print(json.dumps(result))
```

ont-experiments captures this and stores it in the registry.

---

## Testing Skills

### Unit Tests

Create `tests/test_my_skill.py`:

```python
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / 'bin'))
from my_script import analyze_data, AnalysisResult

def test_basic_analysis():
    """Test basic analysis functionality"""
    result = analyze_data(Path('/tmp/test'), {})
    assert isinstance(result, AnalysisResult)
    assert result.quality_status in ('OK', 'CHECK', 'FAIL')

def test_missing_data():
    """Test handling of missing data"""
    with pytest.raises(FileNotFoundError):
        analyze_data(Path('/nonexistent'), {})
```

### Integration Tests

```python
def test_pattern_b_integration():
    """Test integration with ont-experiments"""
    import subprocess
    result = subprocess.run([
        'python3', 'bin/ont_experiments.py',
        'run', 'my_command', 'exp-test',
        '--json', '/tmp/test.json'
    ], capture_output=True, text=True)

    assert result.returncode == 0
    # Check JSON output
```

### Run Tests

```bash
# All tests
pytest tests/

# Specific skill
pytest tests/test_my_skill.py -v

# With coverage
pytest tests/ --cov=bin --cov-report=html
```

---

## Quality Guidelines

### Code Quality

- Follow PEP 8 style guide
- Use type hints for function signatures
- Document all public functions
- Handle errors gracefully with informative messages

### Output Quality

- All plots should be publication-ready (300+ DPI)
- JSON output should be well-structured and documented
- Quality status should be consistently applied

### Documentation Quality

- SKILL.md should be comprehensive
- Include working examples
- Document all options and outputs
- Include troubleshooting section

---

## Deployment Checklist

Before releasing a new skill:

- [ ] Script runs standalone without errors
- [ ] All dependencies documented
- [ ] Graceful handling of missing optional dependencies
- [ ] SKILL.md complete with all sections
- [ ] Version registered in `lib/__init__.py`
- [ ] .skill package created and tested
- [ ] Unit tests passing
- [ ] Integration with ont-experiments tested (if applicable)
- [ ] CLAUDE.md updated
- [ ] docs/SKILLS.md updated
- [ ] README.md updated (if major feature)
- [ ] Commit message follows conventions

---

## Updating Existing Skills

### Version Bumping

1. Update version in script: `VERSION = "1.1.0"`
2. Update version in SKILL.md frontmatter
3. Update version in `lib/__init__.py`
4. Add entry to Version History in SKILL.md
5. Rebuild .skill package

### Backward Compatibility

- Don't remove CLI options (deprecate instead)
- Don't change JSON output field names
- Add new fields, don't modify existing ones
- Document breaking changes clearly

### Migration Guide

If breaking changes are necessary:

```markdown
## Migration from 1.x to 2.0

### Breaking Changes

1. **Option renamed**: `--old-option` → `--new-option`
2. **Output format**: `field_name` → `new_field_name`

### Migration Steps

1. Update your scripts to use `--new-option`
2. Update any JSON parsing to use `new_field_name`
```

---

## Common Patterns

### Reading Sequencing Summary

```python
def parse_sequencing_summary(filepath: Path) -> List[dict]:
    """Parse sequencing_summary.txt"""
    import gzip

    opener = gzip.open if str(filepath).endswith('.gz') else open

    with opener(filepath, 'rt') as f:
        header = f.readline().strip().split('\t')
        col_map = {col.lower(): i for i, col in enumerate(header)}

        for line in f:
            parts = line.strip().split('\t')
            yield {col: parts[i] for col, i in col_map.items() if i < len(parts)}
```

### Quality Status Assignment

```python
def assign_quality_status(metrics: dict) -> str:
    """Assign quality status based on metrics"""
    if metrics['primary_metric'] >= 0.9 and metrics['secondary_metric'] >= 0.8:
        return "OK"
    elif metrics['primary_metric'] >= 0.7 or metrics['secondary_metric'] >= 0.6:
        return "CHECK"
    else:
        return "FAIL"
```

### Publication-Quality Plots

```python
def setup_publication_style():
    """Configure matplotlib for publication-quality output"""
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
        'font.size': 10,
        'axes.linewidth': 1.2,
        'axes.labelsize': 12,
        'axes.titlesize': 14,
        'xtick.major.width': 1.2,
        'ytick.major.width': 1.2,
        'legend.fontsize': 9,
        'figure.dpi': 300,
    })
```

---

## Resources

- **Template**: `docs/SKILL_TEMPLATE.md`
- **Existing Skills**: `skills/*/` directories
- **Core Orchestrator**: `bin/ont_experiments.py`
- **Tests**: `tests/` directory
- **Claude Guide**: `CLAUDE.md`
