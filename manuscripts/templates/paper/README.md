# {{NAME}}

Research paper generated with [ONT Ecosystem](https://github.com/Single-Molecule-Sequencing/ont-ecosystem).

## Structure

```
{{ID}}/
├── main.tex              # Main document
├── .manuscript.yaml      # Configuration (do not edit manually)
├── ont-ecosystem/        # Git submodule link
├── figures/              # Synced figures from experiments
├── tables/               # Synced tables from experiments
└── local.bib            # Local bibliography entries
```

## Quick Start

```bash
# Compile PDF
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex

# Sync figures/tables from experiments
ont_integrate.py sync . --experiments exp-abc123 exp-def456

# Update submodule
git submodule update --remote
```

## Linked Experiments

Experiments linked to this manuscript are listed in `.manuscript.yaml`.

## Generated With

- ONT Ecosystem v2.0.0
- Template: paper
- Created: {{CREATED_AT}}
