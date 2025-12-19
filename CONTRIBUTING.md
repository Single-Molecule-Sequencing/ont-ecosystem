# Contributing to ONT Ecosystem

Thank you for your interest in contributing to the ONT Ecosystem!

## Development Setup

```bash
# Clone the repository
git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git
cd ont-ecosystem

# Install in development mode
./install.sh --prefix ~/.ont-dev --no-deps

# Install development dependencies
pip install pytest pytest-cov black isort flake8

# Run tests
python -m pytest tests/ -v
```

## Code Style

We use:
- **black** for code formatting
- **isort** for import sorting
- **flake8** for linting

```bash
# Format code
black bin/ lib/ tests/
isort bin/ lib/ tests/

# Check style
flake8 bin/ lib/ tests/ --max-line-length=100
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`python -m pytest tests/ -v`)
5. Commit with a descriptive message
6. Push to your fork
7. Open a Pull Request

## Adding a New Analysis Skill

To add a new analysis skill:

1. Create the analysis script in `bin/`:
   ```python
   #!/usr/bin/env python3
   """
   skill_name.py - Description
   """
   # Your implementation
   ```

2. Add to `ANALYSIS_SKILLS` in `ont_experiments.py`:
   ```python
   ANALYSIS_SKILLS = {
       # ... existing skills ...
       "skill_name": {
           "script": "skill_name.py",
           "description": "What it does",
           "result_fields": ["field1", "field2"],
           "input_mode": "location",  # or "explicit"
       },
   }
   ```

3. Add tests in `tests/test_skill_name.py`

4. Update documentation in `README.md`

## Reporting Issues

Please include:
- Python version (`python --version`)
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Relevant log output

## Questions?

Open an issue or contact the maintainers.
