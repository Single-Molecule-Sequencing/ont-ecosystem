# ONT Ecosystem Makefile
# Version 3.0.0

.PHONY: install install-dev test test-quick test-coverage test-lib lint validate clean package dashboard help
.PHONY: validate-skills validate-registry validate-equations pre-commit pre-commit-install
.PHONY: list-figures list-tables list-pipes version stats check docs
.PHONY: doctor report hooks init-project

PYTHON := python3
PIP := pip3
VERSION := 3.0.0

help:
	@echo "ONT Ecosystem v$(VERSION)"
	@echo ""
	@echo "Setup:"
	@echo "  install         Install core dependencies"
	@echo "  install-dev     Install with development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test            Run all tests (162 tests)"
	@echo "  test-quick      Run core tests only"
	@echo "  test-lib        Run library module tests"
	@echo "  test-coverage   Run tests with coverage report"
	@echo "  lint            Check Python syntax"
	@echo ""
	@echo "Validation:"
	@echo "  validate        Validate skills, registry, and equations"
	@echo "  validate-skills Validate SKILL.md frontmatter"
	@echo "  validate-registry Validate experiment registry"
	@echo "  validate-equations Validate equations YAML"
	@echo ""
	@echo "Utilities:"
	@echo "  stats           Show ecosystem statistics"
	@echo "  check           Run health check"
	@echo "  doctor          Diagnose issues and suggest fixes"
	@echo "  report          Generate project report"
	@echo "  version         Show version information"
	@echo "  docs            List documentation files"
	@echo ""
	@echo "Development:"
	@echo "  hooks           Install git hooks"
	@echo "  init-project    Create new project from template"
	@echo "  pre-commit      Run pre-commit hooks"
	@echo ""
	@echo "Manuscript:"
	@echo "  list-figures    List available figure generators"
	@echo "  list-tables     List available table generators"
	@echo "  list-pipes      List available pipelines"
	@echo ""
	@echo "Other:"
	@echo "  package         Create skill packages"
	@echo "  dashboard       Start web dashboard"
	@echo "  clean           Remove build artifacts"
	@echo ""

# Installation
install:
	$(PIP) install pyyaml jsonschema
	chmod +x bin/*.py
	@echo "✅ Installation complete"
	@echo "Run: source install.sh to set up PATH"

install-dev:
	$(PIP) install pyyaml jsonschema pytest pytest-cov
	$(PIP) install pysam edlib numpy pandas matplotlib flask || true
	$(PIP) install pre-commit || true
	chmod +x bin/*.py
	@echo "✅ Development installation complete"

# Testing
test:
	$(PYTHON) -m pytest tests/ -v

test-quick:
	$(PYTHON) -m pytest tests/test_core.py -v

test-coverage:
	$(PYTHON) -m pytest tests/ -v --cov=bin --cov-report=term-missing

# Linting
lint:
	@echo "Checking Python syntax..."
	@for script in bin/*.py; do \
		$(PYTHON) -m py_compile "$$script" && echo "  ✅ $$script"; \
	done
	@echo "✅ All scripts valid"

# Validation
validate: validate-skills validate-registry validate-equations
	@echo "✅ All validations complete"

validate-skills:
	@echo "Validating SKILL.md files..."
	@$(PYTHON) -c "\
import yaml, re; \
from pathlib import Path; \
count = 0; \
for d in Path('skills').iterdir(): \
    if d.is_dir() and (d / 'SKILL.md').exists(): \
        content = (d / 'SKILL.md').read_text(); \
        if re.match(r'^---\n.*?\n---', content, re.DOTALL): \
            print(f'  ✅ {d.name}'); count += 1; \
print(f'\n✅ {count} skills validated')"

validate-registry:
	@echo "Validating registry..."
	@$(PYTHON) -c "\
import json; \
from pathlib import Path; \
reg = json.load(open('data/experiment_registry.json')); \
print(f'  Experiments: {reg[\"total_experiments\"]}'); \
print(f'  Total reads: {reg[\"total_reads\"]:,}'); \
print('✅ Registry valid')"

validate-equations:
	@echo "Validating equations..."
	@$(PYTHON) -c "\
import sys; sys.path.insert(0, 'bin'); \
from ont_context import load_equations; \
eqs = load_equations(); \
total = len(eqs.get('equations', {})); \
computable = len([e for e, d in eqs.get('equations', {}).items() if isinstance(d, dict) and d.get('python')]); \
print(f'  Total equations: {total}'); \
print(f'  Computable: {computable}'); \
print('✅ Equations valid')"

# Pre-commit
pre-commit:
	pre-commit run --all-files

pre-commit-install:
	pre-commit install

# Packaging
package:
	@for skill in skills/*/; do \
		name=$$(basename "$$skill"); \
		cd "$$skill" && zip -r "../$$name.skill" . -x "*.pyc" -x "__pycache__/*" > /dev/null && cd ../..; \
		echo "📦 Created $$name.skill"; \
	done

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/
	rm -rf .coverage htmlcov/
	@echo "🧹 Cleaned"

# Dashboard
dashboard:
	$(PYTHON) bin/ont_dashboard.py --port 8080

# Manuscript shortcuts
list-figures:
	@$(PYTHON) bin/ont_manuscript.py list-figures

list-tables:
	@$(PYTHON) bin/ont_manuscript.py list-tables

list-pipes:
	@$(PYTHON) bin/ont_manuscript.py list-pipelines

# Version info
version:
	@echo "ONT Ecosystem v$(VERSION)"
	@echo "Python: $$($(PYTHON) --version)"
	@$(PYTHON) -c "from lib import __version__; print(f'lib version: {__version__}')"

# Ecosystem stats
stats:
	@$(PYTHON) bin/ont_stats.py

stats-brief:
	@$(PYTHON) bin/ont_stats.py --brief

# Health check
check:
	@$(PYTHON) bin/ont_check.py

# Documentation
docs:
	@echo "Documentation Files:"
	@echo ""
	@echo "  README.md              - Project overview"
	@echo "  CONTRIBUTING.md        - Contribution guide"
	@echo "  CHANGELOG.md           - Version history"
	@echo "  LICENSE                - MIT License"
	@echo ""
	@echo "  docs/ENVIRONMENT.md    - Environment variables"
	@echo "  docs/QUICKSTART.md     - Quick start guide"
	@echo "  docs/SKILLS.md         - Skills documentation"
	@echo "  docs/GITHUB-SETUP.md   - GitHub setup guide"
	@echo "  docs/DEVELOPMENT.md    - Development guide"
	@echo "  docs/API_REFERENCE.md  - Library API reference"
	@echo ""
	@echo "  CLAUDE.md              - Claude Code guidance"
	@echo "  AUTHORITATIVE_SOURCES.md - Source code locations"
	@echo ""
	@ls -la docs/*.md 2>/dev/null | awk '{print "  " $$NF " (" $$5 " bytes)"}' || true

# Library tests
test-lib:
	$(PYTHON) -m pytest tests/test_lib.py -v

# Diagnostics
doctor:
	@$(PYTHON) bin/ont_doctor.py

doctor-fix:
	@$(PYTHON) bin/ont_doctor.py --fix

# Report generation
report:
	@$(PYTHON) bin/ont_report.py

report-md:
	@$(PYTHON) bin/ont_report.py --format markdown

report-json:
	@$(PYTHON) bin/ont_report.py --format json

# Git hooks
hooks:
	@$(PYTHON) bin/ont_hooks.py install

hooks-status:
	@$(PYTHON) bin/ont_hooks.py status

# Project initialization
init-project:
	@echo "Usage: make init-project NAME=my-project"
	@echo "  Options: TEMPLATE=minimal|standard|full (default: standard)"
ifdef NAME
	@$(PYTHON) bin/ont_init.py project $(NAME) --template $(or $(TEMPLATE),standard)
endif
