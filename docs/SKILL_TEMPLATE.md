# Skill Template

Use this template when creating new skills for the ONT Ecosystem.

---

## Directory Structure

Create the following structure for your new skill:

```
skills/
└── your-skill-name/
    ├── SKILL.md              # Required: Skill documentation
    ├── scripts/
    │   └── your_script.py    # Required: Main implementation
    ├── assets/               # Optional: Configuration files
    │   └── config.yaml
    ├── references/           # Optional: Reference documentation
    │   └── interpretation.md
    └── requirements.txt      # Optional: Python dependencies
```

Also create:
```
bin/
└── your_script.py            # Standalone executable (copy of scripts/)
└── your_script_SKILL.md      # Optional: Standalone documentation
```

---

## SKILL.md Template

```markdown
---
name: your-skill-name
version: 1.0.0
description: Brief one-line description of what this skill does
author: Your Name
category: analysis|qc|pipeline|data-management|basecalling
tags: [nanopore, relevant, tags]
---

# Your Skill Name

Brief description of the skill's purpose and capabilities.

## Features

- Feature 1
- Feature 2
- Feature 3

## Installation

\`\`\`bash
# Dependencies
pip install required-package

# Optional dependencies
pip install optional-package  # For enhanced feature X
\`\`\`

## Usage

### Standalone Execution

\`\`\`bash
python3 your_script.py /path/to/data --option value
\`\`\`

### Pattern B Integration (Recommended)

\`\`\`bash
ont_experiments.py run your_command exp-abc123 --option value
\`\`\`

## Command-Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--option` | `value` | Description of option |
| `--flag` | `False` | Description of flag |
| `--json FILE` | None | Output JSON results to FILE |

## Output Format

### JSON Output

\`\`\`json
{
  "experiment_id": "exp-abc123",
  "metric_1": 100,
  "metric_2": 0.95,
  "quality_status": "OK"
}
\`\`\`

### Plot Output

Generates the following plots:
- `output_plot.png` - Description of plot

## Examples

### Example 1: Basic Usage

\`\`\`bash
python3 your_script.py /path/to/experiment --json results.json
\`\`\`

### Example 2: With Options

\`\`\`bash
python3 your_script.py /path/to/data \\
    --option value \\
    --flag \\
    --output-dir ./results
\`\`\`

## Integration with ONT Ecosystem

This skill integrates with:
- **ont-experiments**: For provenance tracking (Pattern B)
- **ont-pipeline**: Can be included in YAML workflows

### Pipeline Integration

\`\`\`yaml
# In your pipeline YAML
steps:
  - name: your_skill_step
    skill: your-skill-name
    options:
      option: value
\`\`\`

## Troubleshooting

### Common Issues

**Issue: Error message X**
- Cause: Description
- Solution: How to fix

**Issue: Error message Y**
- Cause: Description
- Solution: How to fix

## Version History

- **1.0.0** (YYYY-MM-DD): Initial release
```

---

## Python Script Template

```python
#!/usr/bin/env python3
"""
Your Skill Name - ONT Ecosystem Skill

Brief description of what this skill does.

Designed for Pattern B integration with ont-experiments:
  ont_experiments.py run your_command <exp_id> --json results.json

Can also run standalone:
  python3 your_script.py /path/to/data --json results.json

Output fields (captured by ont-experiments):
  - field_1
  - field_2
  - quality_status
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Optional imports with graceful fallback
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


# =============================================================================
# Constants
# =============================================================================

VERSION = "1.0.0"

DEFAULT_OPTION = "default_value"


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class AnalysisResult:
    """Result container for the analysis"""
    experiment_id: str
    metric_1: float
    metric_2: float
    quality_status: str
    timestamp: str = ""

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict"""
        return asdict(self)


# =============================================================================
# Core Functions
# =============================================================================

def analyze_data(data_path: Path, options: Dict[str, Any]) -> AnalysisResult:
    """
    Main analysis function.

    Args:
        data_path: Path to input data
        options: Analysis options

    Returns:
        AnalysisResult with computed metrics
    """
    # Your analysis logic here

    result = AnalysisResult(
        experiment_id=options.get('experiment_id', 'unknown'),
        metric_1=0.0,
        metric_2=0.0,
        quality_status="OK",
        timestamp=datetime.utcnow().isoformat() + "Z"
    )

    return result


def generate_plot(result: AnalysisResult, output_path: Path, dpi: int = 300):
    """Generate visualization plot"""
    if not HAS_MATPLOTLIB:
        raise ImportError("matplotlib required for plotting")

    # Your plotting logic here
    fig, ax = plt.subplots(figsize=(10, 6))
    # ... plot creation ...
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    plt.close()


# =============================================================================
# CLI Interface
# =============================================================================

def print_summary(result: AnalysisResult):
    """Print human-readable summary"""
    print(f"\n{'='*50}")
    print(f"Analysis Results: {result.experiment_id}")
    print(f"{'='*50}")
    print(f"Metric 1: {result.metric_1}")
    print(f"Metric 2: {result.metric_2}")
    print(f"Quality Status: {result.quality_status}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Your Skill Description",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/data --json results.json
  %(prog)s /path/to/data --option value --plot output.png
        """
    )

    parser.add_argument('path', help='Path to input data')
    parser.add_argument('--json', type=Path, help='Output JSON file')
    parser.add_argument('--plot', type=Path, help='Output plot file')
    parser.add_argument('--option', default=DEFAULT_OPTION,
                       help=f'Analysis option (default: {DEFAULT_OPTION})')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress output')
    parser.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')

    args = parser.parse_args()

    try:
        # Run analysis
        options = {
            'option': args.option,
        }

        result = analyze_data(Path(args.path), options)

        # Print summary
        if not args.quiet:
            print_summary(result)

        # Generate plot
        if args.plot:
            generate_plot(result, args.plot)
            if not args.quiet:
                print(f"Saved plot to {args.plot}")

        # Output JSON
        if args.json:
            with open(args.json, 'w') as f:
                json.dump(result.to_dict(), f, indent=2)
            if not args.quiet:
                print(f"Saved results to {args.json}")

        # Print for Pattern B capture (machine-readable)
        print(json.dumps({
            'experiment_id': result.experiment_id,
            'quality_status': result.quality_status,
        }))

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
```

---

## .skill Package Format

### Option 1: ZIP Format (Recommended)

Create a ZIP archive containing:
```
your-skill-name.skill (ZIP file)
├── SKILL.md
└── scripts/
    └── your_script.py
```

Build with:
```bash
cd skills/your-skill-name
zip -r ../your-skill-name.skill SKILL.md scripts/
```

### Option 2: YAML Text Format (Simple Skills)

```yaml
name: your-skill-name
version: 1.0.0
description: Brief description

triggers:
  - keyword 1
  - keyword 2

metadata:
  author: Your Name
  category: analysis
  tags: [nanopore, analysis]

instructions: |
  # Your Skill Name

  Full markdown documentation here...

files:
  script: skills/your-skill-name/scripts/your_script.py
  bin: bin/your_script.py

dependencies:
  python: ">=3.7"
  required:
    - numpy
  optional:
    - matplotlib
```

---

## Checklist for New Skills

- [ ] Create `skills/your-skill-name/` directory
- [ ] Create `skills/your-skill-name/SKILL.md` documentation
- [ ] Create `skills/your-skill-name/scripts/your_script.py`
- [ ] Copy script to `bin/your_script.py`
- [ ] Make bin script executable: `chmod +x bin/your_script.py`
- [ ] Add version to `lib/__init__.py` SKILL_VERSIONS
- [ ] Create `.skill` package (ZIP or YAML)
- [ ] Test standalone execution
- [ ] Test Pattern B integration with ont-experiments
- [ ] Update `CLAUDE.md` skill directory table
- [ ] Add to `docs/SKILLS.md`
