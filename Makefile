# ONT Ecosystem Makefile

.PHONY: install test lint clean package help validate validate-skills validate-registry

PYTHON := python3
PIP := pip3

help:
	@echo "ONT Ecosystem v2.1"
	@echo ""
	@echo "Available targets:"
	@echo "  install     Install dependencies and scripts"
	@echo "  install-dev Install with development dependencies"
	@echo "  test        Run tests"
	@echo "  lint        Check Python syntax"
	@echo "  validate    Validate skills and registry schemas"
	@echo "  package     Create skill packages"
	@echo "  clean       Remove build artifacts"
	@echo "  dashboard   Start web dashboard"
	@echo ""

install:
	$(PIP) install pyyaml jsonschema
	chmod +x bin/*.py
	@echo "✅ Installation complete"
	@echo "Run: source install.sh to set up PATH"

install-dev:
	$(PIP) install pyyaml jsonschema pytest pysam edlib numpy pandas matplotlib flask
	chmod +x bin/*.py
	@echo "✅ Development installation complete"

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	@for script in bin/*.py; do \
		$(PYTHON) -m py_compile "$$script" && echo "✅ $$script"; \
	done

validate: validate-skills validate-registry
	@echo "✅ All validations complete"

validate-skills:
	@echo "Validating SKILL.md files..."
	@$(PYTHON) -c "\
import yaml, re; \
from pathlib import Path; \
[print(f'  ✅ {d.name}') for d in Path('skills').iterdir() if d.is_dir() and \
 (d / 'SKILL.md').exists() and \
 re.match(r'^---\n.*?\n---', (d / 'SKILL.md').read_text(), re.DOTALL)]"

validate-registry:
	@echo "Validating registry schemas..."
	@$(PYTHON) bin/ont_experiments.py validate

package:
	@for skill in skills/*/; do \
		name=$$(basename "$$skill"); \
		cd "$$skill" && zip -r "../$$name.skill" . -x "*.pyc" -x "__pycache__/*" > /dev/null && cd ../..; \
		echo "📦 Created $$name.skill"; \
	done

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf build/ dist/ *.egg-info/
	@echo "🧹 Cleaned"

dashboard:
	$(PYTHON) bin/ont_dashboard.py --port 8080
