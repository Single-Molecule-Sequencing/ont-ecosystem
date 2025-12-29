# GitHub Integration Guide

## Repository Setup

### Initial Push to GitHub

```bash
# 1. Initialize Git LFS (for large files)
git lfs install

# 2. Track large files
git lfs track "*.pdf"
git lfs track "*.png"
git lfs track "*.jpg"

# 3. Add all files
git add .

# 4. Create initial commit
git commit -m "ONT Ecosystem v2.0 - Consolidated Monorepo"

# 5. Add remote and push
git remote add origin git@github.com:Single-Molecule-Sequencing/ont-ecosystem.git
git branch -M main
git push -u origin main
```

### Repository Settings

1. **Enable Git LFS** in repository settings
2. **Branch Protection** for `main`:
   - Require pull request reviews
   - Require status checks to pass
   - Require conversation resolution
3. **Secrets** (for CI):
   - `SSH_PRIVATE_KEY` (for deployment, if needed)

## CI/CD Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CI/CD PIPELINE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Push/PR to main                                                            │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      GitHub Actions                                  │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                      │   │
│  │  Job: test (matrix: Python 3.9, 3.10, 3.11, 3.12)                   │   │
│  │  ├── Checkout (with LFS)                                            │   │
│  │  ├── Install dependencies                                           │   │
│  │  ├── Validate skill frontmatter                                     │   │
│  │  ├── Validate JSON schemas                                          │   │
│  │  ├── Check Python syntax                                            │   │
│  │  ├── Validate YAML files                                            │   │
│  │  └── Run pytest                                                     │   │
│  │                                                                      │   │
│  │  Job: lint                                                          │   │
│  │  └── Check syntax for all bin/*.py                                  │   │
│  │                                                                      │   │
│  │  Job: validate-registry                                             │   │
│  │  ├── Validate registry structure                                   │   │
│  │  └── Verify manuscript templates                                    │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  All checks pass → PR can be merged                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Workflow Files

### `.github/workflows/ci.yml`

The main CI workflow runs on every push and PR:

| Job | Purpose | Matrix |
|-----|---------|--------|
| `test` | Full test suite | Python 3.9-3.12 |
| `lint` | Syntax validation | Python 3.11 |
| `validate-registry` | Registry integrity | Python 3.11 |

### Validation Steps

1. **Skill Frontmatter** - Ensures all SKILL.md files have valid YAML frontmatter
2. **JSON Schemas** - Validates all registry/schemas/*.json
3. **Python Syntax** - Compiles all bin/*.py scripts
4. **YAML Files** - Validates registry and textbook YAML
5. **Tests** - Runs pytest test suite

## Installation from GitHub

### SSH (Recommended for private repo)

```bash
# Clone via SSH
git clone git@github.com:Single-Molecule-Sequencing/ont-ecosystem.git
cd ont-ecosystem

# Run installer
./install.sh

# Activate
source ~/.ont-ecosystem/env.sh

# Verify
ont_experiments.py --help
```

### HTTPS (Public repo)

```bash
# Clone via HTTPS
git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git
cd ont-ecosystem

# Run installer
./install.sh
```

## Development Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DEVELOPMENT WORKFLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Clone Repository                                                        │
│     git clone git@github.com:Single-Molecule-Sequencing/ont-ecosystem.git  │
│                                                                             │
│  2. Create Feature Branch                                                   │
│     git checkout -b feature/new-skill                                      │
│                                                                             │
│  3. Make Changes                                                            │
│     - Add skill in skills/new-skill/SKILL.md                               │
│     - Add script in bin/new_skill.py                                       │
│     - Add tests in tests/test_new_skill.py                                 │
│                                                                             │
│  4. Run Local Tests                                                         │
│     make lint                                                               │
│     make validate                                                           │
│     pytest tests/ -v                                                        │
│                                                                             │
│  5. Commit and Push                                                         │
│     git add .                                                               │
│     git commit -m "Add new-skill for X analysis"                           │
│     git push -u origin feature/new-skill                                   │
│                                                                             │
│  6. Create Pull Request                                                     │
│     - CI automatically runs                                                 │
│     - Review required                                                       │
│     - Merge when approved                                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Makefile Commands

```bash
# Development
make install          # Install core dependencies
make install-dev      # Install with dev dependencies
make lint             # Check Python syntax
make validate         # Validate skill frontmatter
make test             # Run tests
make clean            # Remove build artifacts

# Packaging
make package          # Create .skill packages
make dashboard        # Start web dashboard
```

## Releases

### Creating a Release

```bash
# Tag the release
git tag -a v2.0.0 -m "Release v2.0.0 - Consolidated Monorepo"
git push origin v2.0.0

# GitHub will create the release automatically
# Or create manually via GitHub UI
```

### Release Contents

- Full source code
- Pre-built documentation
- Change log

## Manuscript Repository Connection

When creating a new manuscript that connects to ont-ecosystem:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MANUSCRIPT REPO CONNECTION                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ont-ecosystem (GitHub)                                                     │
│       │                                                                     │
│       │  1. Create manuscript                                               │
│       │     ont_integrate.py create-manuscript my-paper --template paper   │
│       │                                                                     │
│       ▼                                                                     │
│  manuscripts/my-paper/ (local, gitignored)                                 │
│       │                                                                     │
│       │  2. Initialize as separate repo                                     │
│       │     cd manuscripts/my-paper                                        │
│       │     git init                                                        │
│       │     git remote add origin git@github.com:user/my-paper.git         │
│       │                                                                     │
│       │  3. Add ont-ecosystem as submodule                                  │
│       │     git submodule add git@github.com:SMS/ont-ecosystem.git         │
│       │                                                                     │
│       │  4. Push to GitHub                                                  │
│       │     git add .                                                       │
│       │     git commit -m "Initial manuscript setup"                       │
│       │     git push -u origin main                                        │
│       │                                                                     │
│       ▼                                                                     │
│  my-paper (GitHub - separate repo)                                         │
│  ├── ont-ecosystem/  (submodule → ont-ecosystem repo)                      │
│  ├── figures/                                                               │
│  ├── tables/                                                                │
│  ├── main.tex                                                               │
│  └── .manuscript.yaml                                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## GitHub Actions Badges

Add to README.md:

```markdown
![CI](https://github.com/Single-Molecule-Sequencing/ont-ecosystem/actions/workflows/ci.yml/badge.svg)
```

## Security Considerations

1. **Private Repository**: Use SSH for all operations
2. **No Secrets in Code**: All paths are configurable via environment
3. **Git LFS for Large Files**: Prevents repo bloat

## Troubleshooting

### CI Failures

| Error | Solution |
|-------|----------|
| "SKILL.md missing frontmatter" | Add `---\nname: x\ndescription: y\n---` |
| "Invalid JSON schema" | Check JSON syntax in registry/schemas/ |
| "Python syntax error" | Run `python -m py_compile bin/script.py` |
| "Test failed" | Run `pytest tests/ -v` locally |

### LFS Issues

```bash
# If LFS files not downloaded
git lfs pull

# If LFS not installed
git lfs install
git lfs pull
```

## Repository Statistics

After push, repository will contain:

| Component | Count |
|-----------|-------|
| Python scripts | 17 |
| Skills | 8 |
| Equations | ~150 |
| Variables | ~120 |
| Tests | 30 |
| Schemas | 6 |
