# Contributing to ONT Ecosystem

Thank you for your interest in contributing!

## Development Setup

```bash
# Clone the repository
git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git
cd ont-ecosystem

# Install dependencies
pip install -r requirements.txt           # Core dependencies
pip install -r requirements-dev.txt       # Development dependencies

# Install pre-commit hooks (recommended)
pre-commit install

# Verify installation
python bin/ont_check.py
python bin/ont_stats.py --brief
```

## Development Workflow

```bash
# 1. Create a feature branch
git checkout -b feature/amazing-feature

# 2. Make your changes

# 3. Run health check
python bin/ont_check.py

# 4. Run tests
pytest tests/ -v

# 5. Run pre-commit hooks manually (optional)
pre-commit run --all-files

# 6. Commit and push
git commit -m 'Add amazing feature'
git push origin feature/amazing-feature

# 7. Open a Pull Request
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_core.py -v

# Run with coverage
pytest tests/ --cov=bin --cov-report=html
```

## Validating Skills

```bash
# Quick validation using make
make validate-skills

# Or manually:
python -c "
import yaml, re
from pathlib import Path
for skill_dir in Path('skills').iterdir():
    if skill_dir.is_dir():
        skill_md = skill_dir / 'SKILL.md'
        if skill_md.exists():
            content = skill_md.read_text()
            match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if match:
                fm = yaml.safe_load(match.group(1))
                print(f'✅ {skill_dir.name}: {fm[\"name\"]}')
"
```

## Useful Make Targets

```bash
make help                    # Show all targets
make test                    # Run tests
make validate-skills         # Validate skill frontmatter
make validate-equations      # Validate equations YAML
make version                 # Show version info
make list-figures            # List available figure generators
make list-tables             # List available table generators
```

## Code Style

- Python 3.9+ compatible
- Use type hints where practical
- Document public functions with docstrings
- Follow existing code patterns

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run health check (`python bin/ont_check.py`)
5. Run tests (`pytest tests/`)
6. Commit (`git commit -m 'Add amazing feature'`)
7. Push (`git push origin feature/amazing-feature`)
8. Open a Pull Request using the template

## Adding a New Skill

1. Create skill directory with structure:
   ```
   skills/my-skill/
   ├── SKILL.md           # Frontmatter with name, description
   └── scripts/
       └── my_skill.py    # Implementation
   ```

2. Add frontmatter to SKILL.md:
   ```yaml
   ---
   name: my-skill
   description: What the skill does
   version: 1.0.0
   ---
   ```

3. Add wrapper to `bin/` if needed

4. Register in `ont_experiments.py` ANALYSIS_SKILLS

5. Add tests in `tests/test_core.py`

6. Update documentation

## Adding a Figure/Table Generator

1. Create generator in `skills/manuscript/generators/`:
   ```
   skills/manuscript/generators/
   └── gen_my_figure.py
   ```

2. Implement `generate()` function following existing patterns

3. Register in `ont_manuscript.py` FIGURE_GENERATORS or TABLE_GENERATORS

4. Add tests in `tests/test_generators.py`

## Architecture Notes

- **SSOT Pattern**: Analysis code lives in `skills/` as the single source of truth
- **Pattern B Orchestration**: All analyses go through `ont_experiments.py` for provenance
- **Wrappers in bin/**: `bin/` scripts are thin wrappers that import from `skills/`

See [AUTHORITATIVE_SOURCES.md](AUTHORITATIVE_SOURCES.md) for detailed source locations.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
