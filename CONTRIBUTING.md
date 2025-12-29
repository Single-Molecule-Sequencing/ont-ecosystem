# Contributing to ONT Ecosystem

Thank you for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git
cd ont-ecosystem
pip install pyyaml pytest pysam edlib numpy pandas matplotlib
```

## Running Tests

```bash
pytest tests/ -v
```

## Validating Skills

```bash
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

## Code Style

- Python 3.9+ compatible
- Use type hints where practical
- Document public functions
- Include docstrings

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest tests/`)
5. Commit (`git commit -m 'Add amazing feature'`)
6. Push (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Adding a New Skill

1. Create `skills/my-skill/SKILL.md` with frontmatter
2. Add implementation in `skills/my-skill/scripts/`
3. Add to `ANALYSIS_SKILLS` in `ont_experiments.py`
4. Add tests in `tests/`
5. Update documentation

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
