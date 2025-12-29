# CLAUDE.md - AI Assistant Guide for SMS Textbook

This document provides guidance for AI assistants working with the SMS Haplotype Framework Textbook content within the ont-ecosystem monorepo.

**Last Updated:** 2025-12-28
**Location:** `ont-ecosystem/textbook/`
**Parent Repository:** ont-ecosystem (consolidated monorepo)

> **Note:** This textbook content is now part of the ont-ecosystem monorepo.
> The authoritative equation and variable databases are:
> - `textbook/equations.yaml` (4087 lines)
> - `textbook/variables.yaml` (3532 lines)
> - `data/math/All_Math.pdf` (takes precedence on conflicts)

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Repository Architecture](#repository-architecture)
3. [Quick Start](#quick-start)
4. [Build Commands & Compilation](#build-commands--compilation)
5. [Directory Structure](#directory-structure)
6. [Development Workflows](#development-workflows)
7. [GitHub Actions CI/CD](#github-actions-cicd)
8. [Custom LaTeX Features](#custom-latex-features)
9. [Testing Infrastructure](#testing-infrastructure)
10. [Python Automation Scripts](#python-automation-scripts)
11. [Common Tasks](#common-tasks)
12. [File Status & Organization](#file-status--organization)
13. [Troubleshooting](#troubleshooting)
14. [Best Practices for AI Assistants](#best-practices-for-ai-assistants)

---

## Project Overview

**SMS Haplotype Classification Framework** is a comprehensive academic textbook (~250 pages) covering single-molecule sequencing methods for pharmacogenomic haplotype classification.

### Key Facts

- **Document Type:** LaTeX-based academic textbook
- **Current Status:** 75% complete (15/20 chapters production-ready)
- **Total Pages:** ~195 pages (current), 250-300 estimated when complete
- **File Size:** ~1.6 MB
- **Primary Output:** PDF compilation via pdflatex
- **Version:** 6.0 - Complete Edition (Released October 2025, Updated November 2025)

### Document Structure

- **7 Parts** covering Foundation, Mathematical Framework, Reference Standards, Computational Methods, Quality Control, Clinical Applications, and Operations
- **20 Chapters** (15 complete, 5 placeholders)
- **5 Appendices** (4 complete)
- **Custom Features:** Core Equation reference system (CE#1-15), custom environments, professional dark theme

---

## Repository Architecture

This repository follows a **dual-architecture pattern** separating core compilation files from supporting infrastructure:

### Core vs FAT Split

**CORE (Root Level)** - 31 files essential for PDF compilation:
- Master LaTeX document
- Compilation scripts
- Source files (chapters/appendices in `src/`)
- Essential templates (3 files)
- Bibliography

**FAT (Features, Automation, Tools)** - ~150+ supporting files:
- GitHub Actions workflows
- Python automation scripts (7 scripts, 2,371 LOC)
- Testing infrastructure (24 test files)
- Comprehensive documentation (23+ docs)
- Web visualizer application
- Build artifacts
- Historical versions

### Why This Architecture?

1. **Clean Imports:** Easier Overleaf imports (only essential files)
2. **Fast Cloning:** Core compilation needs minimal files
3. **Organized Tools:** Development infrastructure still accessible
4. **Clear Purpose:** Separation of concerns between compilation and development

---

## Quick Start

### Download Pre-Built PDF

PDFs are automatically compiled via GitHub Actions:

1. **Latest Full Textbook:** [Releases → latest](../../releases/tag/latest)
2. **Individual Chapters/Appendices:** [Releases → individual-docs-latest](../../releases/tag/individual-docs-latest)
3. **Workflow Artifacts:** [Actions page](../../actions) (90-day retention)

### Compile Locally

**Windows:**
```cmd
compile.bat
```

**Mac/Linux:**
```bash
chmod +x compile.sh
./compile.sh
```

**Output:** `SMS_Haplotype_Framework_Textbook.pdf`

### Testing Compilation

```bash
python3 FAT/scripts/test_pdf_compilation.py
```

Validates LaTeX installation, compiles document, checks PDF validity.

---

## Build Commands & Compilation

### Why Three Passes?

LaTeX requires multiple compilation passes to resolve all cross-references, hyperlinks, and table of contents entries:

1. **Pass 1:** Generates .aux files with labels and references
2. **Pass 2:** Resolves cross-references and creates table of contents
3. **Pass 3:** Finalizes hyperlinks and page number references

### Manual Compilation

```bash
pdflatex -interaction=nonstopmode -jobname=SMS_Haplotype_Framework_Textbook haplotype_v6_complete_FIXED.tex
pdflatex -interaction=nonstopmode -jobname=SMS_Haplotype_Framework_Textbook haplotype_v6_complete_FIXED.tex
pdflatex -interaction=nonstopmode -jobname=SMS_Haplotype_Framework_Textbook haplotype_v6_complete_FIXED.tex
```

### Compilation Scripts

Both scripts (`compile.sh`, `compile.bat`) perform:
- Prerequisite checking (pdflatex, main file existence)
- Three-pass compilation with progress reporting
- Exit code validation per pass
- PDF creation verification
- Log file error checking
- Automatic PDF viewer launching (local only)

**Key Variables:**
- `COMPILER`: Path to pdflatex
- `MAINFILE`: `haplotype_v6_complete_FIXED.tex`
- `OUTPUTNAME`: `SMS_Haplotype_Framework_Textbook`

---

## Directory Structure

### Root Level (Core Files)

```
SMS_textbook/
├── haplotype_v6_complete_FIXED.tex    # Master LaTeX document (~25 KB, ~600 lines)
├── compile.sh                          # Mac/Linux build script
├── compile.bat                         # Windows build script
├── references.bib                      # Bibliography database
├── README.md                           # Main project documentation
├── CLAUDE.md                           # This file
├── REORGANIZATION_SUMMARY.md           # Reorganization details
├── FILE_LOCATIONS.md                   # File location reference
├── .gitignore                          # Git ignore rules (excludes FAT/)
├── src/                                # Source files
│   ├── chapters/                       # 20 chapter files
│   └── appendices/                     # 5 appendix files
└── templates/                          # Essential LaTeX templates (3 files)
    ├── eqbox_improved_v5style.tex      # Main equation box template
    ├── eqbox_example_rigorous.tex      # Example template
    └── table_example_realistic.tex     # Table example template
```

### FAT Directory Structure

```
FAT/
├── .github/workflows/                  # GitHub Actions (5 workflows)
│   ├── compile-pdf.yml                 # Main PDF compilation + release
│   ├── compile-individual-docs.yml     # Individual chapter/appendix PDFs
│   ├── build-pdf.yml                   # Alternative PDF build
│   ├── generate-tutorials.yml          # Tutorial PDF generation
│   └── wiki-sync.yml                   # Automated wiki generation and sync
├── scripts/                            # Python automation (10 scripts)
│   ├── compile_individual_docs.py      # Standalone chapter compilation
│   ├── generate_tutorials.py           # Tutorial PDF generation
│   ├── test_pdf_compilation.py         # PDF compilation validation
│   ├── test_individual_docs.py         # Individual docs validation
│   ├── test_tutorials.py               # Tutorial structure validation
│   ├── validate_latex_structure.py     # LaTeX structure validation
│   └── validate_workflow.py            # GitHub workflow validation
├── tests/                              # LaTeX test wrappers (24 files)
│   └── _test_chapter*_*.tex            # Test files for chapters
├── docs/                               # Documentation (23+ files)
│   ├── CLAUDE.md                       # Legacy Claude guide (superseded)
│   ├── COMPILATION_TUTORIAL.md         # Detailed build guide
│   ├── EQBOX_AUTHORING_GUIDE.md        # Equation box styling
│   ├── FILE_INVENTORY.md               # Complete file manifest
│   ├── GITHUB_ACTIONS.md               # Workflow documentation
│   └── [20+ other documentation files]
├── tutorials/                          # Tutorial generation system
│   ├── templates/                      # Tutorial templates
│   ├── output/                         # Generated tutorial PDFs
│   └── README.md, INDEX.md, etc.
├── build/                              # Compilation artifacts
│   ├── individual_docs/                # Individual chapter/appendix PDFs
│   └── *.aux, *.log, *.out files
├── meta/                               # Metadata
│   └── manifest.yaml                   # Chapter/appendix status tracking
├── static/                             # Web assets (JS, CSS)
├── history/                            # Historical document versions
├── .claude/                            # Claude AI configuration
├── .vscode/                            # VS Code settings
├── doc_visualizer.py                   # Flask web application
├── requirements.txt                    # Python dependencies (Flask==3.0.0)
└── Various markdown guides             # TESTING_GUIDE.md, TUTORIAL.md, etc.
```

---

## Development Workflows

### Adding/Modifying Chapters

1. **Edit chapter file** in `/FAT/src/chapters/chapterN_*.tex`
2. **Maintain consistent formatting** with existing chapters
3. **Use `\label{}` for all sections, equations, figures, tables**
4. **Use `\ref{}` or `\CEref{}` for cross-references**
5. **Compile 3 times** to ensure all references resolve
6. **Test compilation** with `python3 FAT/scripts/test_pdf_compilation.py`

### Adding New Chapters

1. Create new chapter file: `/FAT/src/chapters/chapterN_new.tex`
2. Add `\input{src/chapters/chapterN_new.tex}` to `haplotype_v6_complete_FIXED.tex` in appropriate Part section
3. Update `/FAT/meta/manifest.yaml` with new chapter entry
4. Compile 3 times to update ToC and resolve cross-references

### Modifying Templates

1. Edit template files in `/templates/`
2. Test with relevant chapter compilation
3. Re-generate tutorials: `python3 FAT/scripts/generate_tutorials.py`
4. Commit changes (tutorials will auto-update via GitHub Actions)

### Working with Placeholder Chapters (16-20)

**⚠️ CRITICAL:** Chapters 16-20 have known formatting errors due to linter conflicts.

**Known Issues:**
- Missing backslashes: `\textit{` becomes `extit{`
- Missing backslashes: `\textbf{` becomes `extbf{`
- Table commands: `\toprule` becomes `oprule`

**When editing:**
1. Disable auto-formatter/linter before editing
2. Verify backslashes are present in all LaTeX commands
3. Test compilation after changes
4. Re-enable linter only after confirming clean compilation

**Current status:** Excluded from compilation (lines 537-540, 551-553 commented out in master document)

---

## GitHub Actions CI/CD

### Workflow 1: `compile-pdf.yml` - Main PDF Build

**Purpose:** Compiles complete textbook and creates GitHub release

**Triggers:**
- Push to `main`/`master` (when `.tex`, `src/`, `templates/`, `compile.sh`, or workflow files change)
- Pull requests
- Manual dispatch

**Process:**
1. Install TeX Live (`texlive-latex-recommended`, `texlive-latex-extra`, `texlive-fonts-recommended`, `texlive-fonts-extra`, `texlive-science`, `latexmk`)
2. Run 3 compilation passes
3. Validate PDF creation with size reporting
4. Upload artifact (90-day retention)
5. Update "latest" GitHub release with commit metadata

**Output:** `SMS_Haplotype_Framework_Textbook.pdf` in release + artifact

**Release Details:**
- Tag: `latest`
- Body: Commit SHA, message, timestamp, author, links to workflow and commit

### Workflow 2: `compile-individual-docs.yml` - Individual Documents

**Purpose:** Compiles each chapter and appendix as standalone PDFs

**Triggers:**
- Changes to `src/chapters/`, `src/appendices/`, `meta/manifest.yaml`
- Manual dispatch

**Process:**
1. Install Python (pyyaml), TeX Live
2. Run `test_individual_docs.py` for validation
3. Execute `compile_individual_docs.py` to generate individual PDFs
4. List and count generated PDFs
5. Upload all PDFs as artifact
6. Create "individual-docs-latest" release with chapter/appendix listing

**Output:** Multiple PDFs (one per chapter/appendix) in `/FAT/build/individual_docs/`

**Retention:** 90 days

### Workflow 3: `build-pdf.yml` - Alternative Build

**Purpose:** Simple PDF compilation using external latex-action

**Triggers:**
- Push to `main`
- Pull requests
- Manual dispatch

**Process:**
1. Checkout repository
2. Use `xu-cheng/latex-action@v2` for compilation
3. Upload artifact

**Note:** Simpler than `compile-pdf.yml`, uses external action vs. manual TeX Live installation

### Workflow 4: `generate-tutorials.yml` - Tutorial Generation

**Purpose:** Auto-generates tutorial PDFs from template examples

**Triggers:**
- Changes to `templates/`, `FAT/scripts/generate_tutorials.py`, workflow file
- Manual dispatch

**Permissions:** `contents: write` (for git commits)

**Process:**
1. Install Python, TeX Live
2. Run `test_tutorials.py` for validation
3. Execute `generate_tutorials.py` to create tutorial PDFs
4. Check for changes in `FAT/tutorials/` directory
5. **Auto-commit and push** if modifications detected (push events only)
6. Upload artifacts for PR validation (30-day retention)
7. Post PR comment with list of generated PDFs (using GitHub script)

**Output:** Tutorial PDFs in `/FAT/tutorials/output/`

**Note:** Only auto-commits on push events, not PRs

---

## Custom LaTeX Features

### Core Equation Reference System

This document uses a custom equation referencing system for the 15 core equations (CE#1-15):

**Define an equation anchor:**
```latex
\CEanchor{1}
\begin{equation}
P(h|r) = \frac{P(r|h)P(h)}{P(r)}
\label{eq:posterior-basic}
\end{equation}
```

**Reference the equation in text:**
```latex
As shown in \CEref{1}, the posterior probability...
```

This creates hyperlinked references like "CE.1" that jump to the corresponding equation.

### Custom Environments

**Protocol environment:**
```latex
\begin{protocol}[Optional Title]
Step-by-step procedure...
\end{protocol}
```

**Tutorial equation box (eqbox):**
```latex
\begin{eqbox}{Tutorial: Computing Posteriors}
Detailed walkthrough with worked examples...
\end{eqbox}
```

**Standard theorem environments:**
```latex
\begin{definition}[Name]
Definition content...
\end{definition}

\begin{theorem}[Name]
Theorem statement...
\end{theorem}

\begin{example}[Title]
Example content...
\end{example}

\begin{remark}[Note]
Remark content...
\end{remark}
```

### Forthcoming Chapter Notice

For placeholder chapters:
```latex
\ChapterForthcomingNotice{
    Description of chapter content
}{
    \item First planned section
    \item Second planned section
    \item Third planned section
}{
    Estimated 15-20 pages
}
```

### Color Scheme

Professional dark theme with charcoal/slate colors:

```latex
\definecolor{primarydark}{RGB}{45,45,48}       % Deep charcoal
\definecolor{secondarydark}{RGB}{65,65,70}     % Lighter charcoal
\definecolor{slateaccent}{RGB}{85,90,95}       % Warm slate gray
```

Links and chapter titles use `primarydark` for consistency.

### Cross-Referencing Conventions

Always use labels with consistent prefixes:

```latex
% Sections
\section{Important Section}
\label{sec:important}
See Section~\ref{sec:important} for details.

% Chapters
\chapter{My Chapter}
\label{chap:my-chapter}
As discussed in Chapter~\ref{chap:my-chapter}...

% Equations
\begin{equation}
E = mc^2
\label{eq:einstein}
\end{equation}
See Equation~\ref{eq:einstein}...

% Figures
\begin{figure}
...
\label{fig:diagram}
\end{figure}
Figure~\ref{fig:diagram} shows...

% Tables
\begin{table}
...
\label{tab:results}
\end{table}
Table~\ref{tab:results} presents...
```

---

## Testing Infrastructure

### Test Scripts Overview

| Script | Purpose | Lines | Usage |
|--------|---------|-------|-------|
| `test_pdf_compilation.py` | Main PDF validation | 222 | `python3 FAT/scripts/test_pdf_compilation.py` |
| `test_individual_docs.py` | Individual docs validation | 172 | `python3 FAT/scripts/test_individual_docs.py` |
| `test_tutorials.py` | Tutorial structure validation | 135 | `python3 FAT/scripts/test_tutorials.py` |
| `validate_latex_structure.py` | LaTeX structure validation | 194 | `python3 FAT/scripts/validate_latex_structure.py` |
| `validate_workflow.py` | GitHub workflow validation | 291 | `python3 FAT/scripts/validate_workflow.py` |

### test_pdf_compilation.py

**What it does:**
- Validates LaTeX installation (checks for pdflatex)
- Verifies main LaTeX file exists
- Compiles PDF with 3 passes
- Validates PDF was created successfully
- Checks PDF file properties (size, format)
- Analyzes compilation log for errors and warnings
- Cleans up old compilation artifacts

**Expected output:**
```
======================================================================
SMS Haplotype Framework - PDF Compilation Test
======================================================================

Checking prerequisites...
✓ pdflatex is installed
✓ Main LaTeX file exists: haplotype_v6_complete_FIXED.tex

Compiling PDF...
✓ PDF compiled successfully

Validating PDF...
✓ PDF is valid (1,163,456 bytes)

Checking compilation log...
✓ No LaTeX errors found

======================================================================
✓ All PDF compilation tests passed!
======================================================================
```

### test_individual_docs.py

**What it does:**
- Validates manifest.yaml structure
- Checks that all source files in manifest exist
- Verifies file paths are correct
- Tests LaTeX structure of individual documents
- Validates compilation setup

**Used by:** `compile-individual-docs.yml` workflow

### test_tutorials.py

**What it does:**
- Validates tutorial structure and templates
- Checks tutorial output directory exists
- Tests PDF generation pipeline
- Ensures template files are present

**Used by:** `generate-tutorials.yml` workflow

### LaTeX Test Files

24 test wrapper files in `/FAT/tests/` with naming pattern `_test_chapter*_*.tex`

These wrap individual chapters in minimal LaTeX preamble for standalone testing.

---

## Python Automation Scripts

### compile_individual_docs.py (409 lines)

**Purpose:** Generates standalone PDFs for each chapter and appendix

**How it works:**
1. Reads `/FAT/meta/manifest.yaml` to identify all chapters/appendices
2. Wraps each document in minimal LaTeX preamble
3. Compiles each as standalone PDF
4. Outputs to `/FAT/build/individual_docs/`

**Usage:**
```bash
# Compile all documents
python3 FAT/scripts/compile_individual_docs.py

# Compile specific document
python3 FAT/scripts/compile_individual_docs.py --document src/chapters/chapter1_expanded.tex

# Specify output directory
python3 FAT/scripts/compile_individual_docs.py --output-dir /path/to/output
```

**Output naming:** Matches source file (e.g., `chapter1_expanded.pdf`)

### generate_tutorials.py (581 lines)

**Purpose:** Creates tutorial/example PDF pages demonstrating template usage

**How it works:**
1. Reads template files (eqbox, table examples)
2. Extracts example content
3. Generates standalone PDF pages showing template transformations
4. Outputs to `/FAT/tutorials/output/`

**Generated tutorials:**
- eqboxV5 tutorial - Equation box styling examples
- Table tutorial - Table template variations
- Formatting examples

**Usage:**
```bash
python3 FAT/scripts/generate_tutorials.py
```

**Note:** Automatically triggered by GitHub Actions on template changes

### validate_latex_structure.py (194 lines)

**Purpose:** Structural validation of LaTeX documents

**Validates:**
- Document classes correct
- Required packages present
- Environments properly opened/closed
- Include/input statements valid
- Cross-references integrity

**Usage:**
```bash
python3 FAT/scripts/validate_latex_structure.py
```

### validate_workflow.py (291 lines)

**Purpose:** Validates GitHub Actions workflow YAML files

**Validates:**
- Workflow syntax correct
- Triggers properly configured
- Job configurations valid
- Step sequences logical
- Path filtering rules correct

**Usage:**
```bash
python3 FAT/scripts/validate_workflow.py
```

### doc_visualizer.py (367 lines)

**Purpose:** Flask web application for document exploration

**Features:**
- Browse textbook structure
- View document metadata
- Display statistics
- Navigate chapters/appendices

**Usage:**
```bash
python3 FAT/doc_visualizer.py
# Opens at http://localhost:5000
```

**Dependencies:** Flask==3.0.0 (in `/FAT/requirements.txt`)

---

## Common Tasks

### Compiling the Full PDF

```bash
# Using compilation scripts (recommended)
./compile.sh                    # Mac/Linux
compile.bat                      # Windows

# Manual compilation
pdflatex -interaction=nonstopmode -jobname=SMS_Haplotype_Framework_Textbook haplotype_v6_complete_FIXED.tex
pdflatex -interaction=nonstopmode -jobname=SMS_Haplotype_Framework_Textbook haplotype_v6_complete_FIXED.tex
pdflatex -interaction=nonstopmode -jobname=SMS_Haplotype_Framework_Textbook haplotype_v6_complete_FIXED.tex
```

### Testing Compilation

```bash
# Comprehensive PDF test
python3 FAT/scripts/test_pdf_compilation.py

# Individual docs test
python3 FAT/scripts/test_individual_docs.py

# Tutorial structure test
python3 FAT/scripts/test_tutorials.py

# LaTeX structure validation
python3 FAT/scripts/validate_latex_structure.py

# Workflow validation
python3 FAT/scripts/validate_workflow.py
```

### Compiling Individual Chapters

```bash
# All chapters/appendices
python3 FAT/scripts/compile_individual_docs.py

# Specific chapter
python3 FAT/scripts/compile_individual_docs.py --document src/chapters/chapter4_populated.tex

# Custom output directory
python3 FAT/scripts/compile_individual_docs.py --output-dir /custom/path
```

### Generating Tutorials

```bash
python3 FAT/scripts/generate_tutorials.py
```

### Running the Web Visualizer

```bash
# Install dependencies
pip install -r FAT/requirements.txt

# Run visualizer
python3 FAT/doc_visualizer.py

# Access at http://localhost:5000
```

### Viewing Documentation

```bash
# Main documentation
cat README.md

# Compilation tutorial
cat FAT/docs/COMPILATION_TUTORIAL.md

# Testing guide
cat FAT/TESTING_GUIDE.md

# Complete tutorial overview
cat FAT/TUTORIAL.md

# File locations reference
cat FILE_LOCATIONS.md
```

### Checking File Status

```bash
# View manifest (chapter/appendix status)
cat FAT/meta/manifest.yaml

# View reorganization summary
cat REORGANIZATION_SUMMARY.md
```

### Triggering GitHub Actions Manually

1. Go to [Actions page](../../actions)
2. Select workflow (e.g., "Compile LaTeX to PDF")
3. Click "Run workflow"
4. Select branch
5. Click "Run workflow" button

### Downloading Compiled PDFs

**From Releases:**
1. [Releases page](../../releases)
2. Click "latest" or "individual-docs-latest"
3. Download PDF(s) from Assets section

**From Workflow Artifacts:**
1. [Actions page](../../actions)
2. Click on specific workflow run
3. Scroll to Artifacts section
4. Download artifact (90-day retention)

---

## File Status & Organization

### Chapter Status (from manifest.yaml)

**Expanded Chapters (3):**
- chapter1_expanded.tex - Pharmacogenomics and Adverse Drug Reactions
- chapter2_expanded.tex - Genomic Complexity at Pharmacogene Loci
- chapter3_expanded.tex - Single-Molecule Sequencing Technologies

**Complete/Populated Chapters (12):**
- chapter4_populated.tex - Haplotype Classification Model
- chapter5_populated.tex - Purity Theory
- chapter6_populated.tex - Posterior Computation
- chapter7_populated.tex - Experimental Design
- chapter8_populated.tex - Plasmid Standards
- chapter9_populated.tex - Targeted Enrichment
- chapter10_populated.tex - Haplotype Mixtures
- chapter11_populated.tex - Basecaller Quality Models
- chapter12_populated.tex - Noisy Label Learning
- chapter13_populated.tex - Basecaller Fine-Tuning
- chapter14_populated.tex - Library Preparation
- chapter15_populated.tex - End-to-End Workflow

**Placeholder Chapters (5):**
- chapter16_placeholder.tex - Bacterial Strain Typing
- chapter17_placeholder.tex - CYP2D6 Validation
- chapter18_placeholder.tex - 75-Patient Cohort
- chapter19_placeholder.tex - Standard Operating Procedures
- chapter20_placeholder.tex - Economic Analysis

**Additional/Unused:**
- chapter4_enhancements.tex - Alternative version (unused, in FAT)

### Appendix Status

**Complete Appendices (4):**
- appendixB_populated.tex - Core Equations Reference
- appendixC_populated.tex - Quality Control Gates
- appendixD_populated.tex - Computational Protocols
- appendixE_populated.tex - Version History

**Partial Appendices:**
- appendix_appendix.tex - Generic appendix template (partial)
- appendix_b_algorithms_extract.tex - Algorithm extracts (partial, unused)

### Document Inclusion in Master File

The master document (`haplotype_v6_complete_FIXED.tex`) includes chapters via:
```latex
\input{src/chapters/chapter1_expanded.tex}
\input{src/chapters/chapter2_expanded.tex}
...
```

**Note:** Chapters 16-20 are currently **commented out** (lines 537-540, 551-553) due to formatting errors.

### File Locations Reference

See `FILE_LOCATIONS.md` for quick reference guide on finding files after repository reorganization.

---

## Troubleshooting

### Issue: "pdflatex not found"

**Cause:** LaTeX distribution not installed or not in PATH

**Solution:**
- **Windows:** Install MiKTeX (https://miktex.org/)
- **Mac:** Install MacTeX (https://tug.org/mactex/)
- **Linux:** `sudo apt-get install texlive-full`
- Update PATH or modify `compile.bat` (Windows) to point to correct pdflatex location

### Issue: Missing package errors

**Cause:** Required LaTeX packages not installed

**Solution:**
- **MiKTeX:** Packages should auto-install. If not, use MiKTeX Console → Packages
- **TeX Live:** `sudo tlmgr install [package-name]`
- **Full TeX Live:** `sudo apt-get install texlive-full` (Linux)

### Issue: Undefined references after compilation

**Cause:** Cross-references not resolved (single pass compilation)

**Solution:** Run compilation **3 times**. References need multiple passes to resolve.

### Issue: Chapters 16-20 compilation errors

**Cause:** Known formatting issues due to linter/auto-formatter conflicts

**Current Status:** These chapters are excluded from compilation (commented out in master document)

**When to fix:**
1. Disable auto-formatter/linter before editing
2. Verify all LaTeX commands have backslashes
3. Test compilation after changes
4. Don't uncomment in master until errors resolved

### Issue: PDF created but warnings present

**Cause:** Non-fatal LaTeX warnings (overfull boxes, missing references, etc.)

**Solution:**
- Check `SMS_Haplotype_Framework_Textbook.log` for details
- Look for patterns: `LaTeX Warning:`, `Overfull \hbox`, `Underfull \hbox`
- Most warnings can be safely ignored if PDF looks correct
- Critical warnings: "Reference undefined", "Citation undefined"

### Issue: Compilation hangs

**Cause:** Infinite loops in custom commands, missing `\end{}`, or interaction mode

**Solution:**
- Check for matching `\begin{}` and `\end{}`
- Verify custom commands don't have infinite recursion
- Ensure `-interaction=nonstopmode` flag is used
- Kill process and check log file for last processed line

### Issue: GitHub Actions workflow fails

**Cause:** TeX Live packages missing, path errors, or source file issues

**Solution:**
1. Check workflow run logs in [Actions page](../../actions)
2. Look for specific error messages
3. Verify all referenced files exist
4. Ensure workflow YAML syntax is correct
5. Test locally before pushing

### Issue: Individual docs compilation fails

**Cause:** manifest.yaml errors, missing source files, or path issues

**Solution:**
1. Validate manifest.yaml syntax
2. Check all files in manifest exist
3. Run `python3 FAT/scripts/test_individual_docs.py`
4. Check paths relative to repository root

### Issue: Tutorial generation fails

**Cause:** Template files missing, LaTeX errors in templates, or output directory issues

**Solution:**
1. Run `python3 FAT/scripts/test_tutorials.py`
2. Check template files in `/templates/` exist
3. Verify tutorial output directory `/FAT/tutorials/output/` exists
4. Review template LaTeX syntax

---

## Best Practices for AI Assistants

### 1. Always Compile with 3 Passes

When making changes to LaTeX files, **always compile 3 times** to ensure cross-references resolve:

```bash
./compile.sh    # Automatically runs 3 passes
```

### 2. Use Test Scripts Before Committing

Before committing changes:
```bash
python3 FAT/scripts/test_pdf_compilation.py
```

This validates:
- LaTeX installation
- PDF compilation success
- No fatal errors in log

### 3. Maintain Consistent Label Prefixes

Use these prefixes for labels:
- Chapters: `chap:`
- Sections: `sec:`
- Equations: `eq:`
- Figures: `fig:`
- Tables: `tab:`

Example:
```latex
\chapter{New Chapter}
\label{chap:new-chapter}

\section{Important Section}
\label{sec:important}

\begin{equation}
E = mc^2
\label{eq:einstein}
\end{equation}
```

### 4. Update manifest.yaml When Adding Chapters

When adding new chapters or appendices, update `/FAT/meta/manifest.yaml`:

```yaml
chapters:
  - file: src/chapters/chapter21_new.tex
    status: complete  # or: expanded, placeholder, enhancements, partial
```

### 5. Don't Edit Placeholder Chapters Without Preparation

Chapters 16-20 have formatting issues. Before editing:
1. Disable auto-formatter/linter
2. Verify backslashes in LaTeX commands
3. Test compilation thoroughly
4. Don't uncomment in master until verified

### 6. Use Core vs FAT Organization

**When to put files in Core (root):**
- Essential for PDF compilation
- Required by master document
- Source files (chapters/appendices)
- Essential templates

**When to put files in FAT:**
- Development tools
- Testing infrastructure
- Documentation
- Build artifacts
- Historical versions
- Web applications

### 7. Leverage GitHub Actions

Don't compile locally for every small change. Push to a branch and let GitHub Actions compile:
- Saves local resources
- Validates in clean environment
- Generates artifacts automatically
- Creates releases

### 8. Reference Existing Documentation

Before creating new documentation, check if it already exists:
- Main docs: `/FAT/docs/`
- Root docs: `README.md`, `FILE_LOCATIONS.md`, `REORGANIZATION_SUMMARY.md`
- FAT root docs: `TESTING_GUIDE.md`, `TUTORIAL.md`

### 9. Use Descriptive Commit Messages

Follow this format:
```
[Component] Brief description

Detailed explanation if needed

Changes:
- Change 1
- Change 2
```

Example:
```
[Chapter 5] Add tutorial section on purity computation

Added comprehensive tutorial with worked examples demonstrating
purity theory calculations for common scenarios.

Changes:
- Added eqbox environment with 3 worked examples
- Updated cross-references in Chapter 6
- Added figure illustrating purity degradation
```

### 10. Test Individual Docs After Chapter Changes

When modifying chapters:
```bash
# Test individual compilation
python3 FAT/scripts/compile_individual_docs.py --document src/chapters/chapterN_*.tex

# Test all individual docs
python3 FAT/scripts/test_individual_docs.py
```

### 11. Keep Master Document Clean

The master document (`haplotype_v6_complete_FIXED.tex`) should:
- Only include chapter/appendix files
- Not contain chapter content directly
- Maintain consistent structure
- Use `\input{}` for includes (not `\include{}`)

### 12. Validate Workflows Before Pushing

Before modifying GitHub Actions workflows:
```bash
python3 FAT/scripts/validate_workflow.py
```

This catches YAML syntax errors and configuration issues.

### 13. Monitor Artifact Retention

GitHub Actions artifacts are retained for **90 days** (PDFs) or **30 days** (tutorials in PRs).

For long-term storage, use:
- GitHub Releases (unlimited retention)
- Local compilation
- External storage

### 14. Use Web Visualizer for Exploration

When exploring document structure:
```bash
python3 FAT/doc_visualizer.py
# Access at http://localhost:5000
```

Provides visual interface for browsing chapters, appendices, and metadata.

### 15. Follow LaTeX Best Practices

**DO:**
- Use `~` for non-breaking spaces: `Section~\ref{sec:intro}`
- Use `\label{}` immediately after `\begin{}` or `\chapter{}`/`\section{}`
- Use semantic commands: `\emph{}` instead of `\textit{}`
- Keep lines under 120 characters for readability

**DON'T:**
- Hard-code section/equation numbers
- Use absolute paths in `\input{}`
- Nest environments incorrectly
- Use deprecated commands

---

## Additional Resources

### Documentation Files

**Root Level:**
- `README.md` - Main project overview
- `FILE_LOCATIONS.md` - File location reference
- `REORGANIZATION_SUMMARY.md` - Reorganization details

**FAT Level:**
- `TESTING_GUIDE.md` - Comprehensive testing instructions
- `TUTORIAL.md` - Complete topic overview
- `PDF_TESTING.md` - PDF validation procedures

**FAT/docs/**
- `COMPILATION_TUTORIAL.md` - Detailed compilation guide
- `EQBOX_AUTHORING_GUIDE.md` - Equation box styling guide
- `GITHUB_ACTIONS.md` - Workflow documentation
- `FILE_INVENTORY.md` - Complete file manifest
- `PROJECT_SUMMARY.md` - High-level overview
- [20+ additional documentation files]

### External Resources

- **MiKTeX:** https://miktex.org/ (Windows LaTeX distribution)
- **MacTeX:** https://tug.org/mactex/ (Mac LaTeX distribution)
- **TeX Live:** https://tug.org/texlive/ (Linux LaTeX distribution)
- **LaTeX Documentation:** https://www.latex-project.org/help/documentation/
- **GitHub Actions Docs:** https://docs.github.com/en/actions

### Repository Links

- **Main Repository:** https://github.com/gregfar/SMS_textbook
- **Issues:** https://github.com/gregfar/SMS_textbook/issues
- **Actions:** https://github.com/gregfar/SMS_textbook/actions
- **Releases:** https://github.com/gregfar/SMS_textbook/releases

---

## Version History

### v1.1 (2025-11-14)
- Created comprehensive CLAUDE.md at repository root
- Supersedes FAT/docs/CLAUDE.md (legacy)
- Includes complete CI/CD workflow documentation
- Added Python automation script details
- Enhanced troubleshooting section
- Added best practices for AI assistants

### v1.0 (2025-10-17)
- Initial production release
- Chapters 1-15 complete
- Repository reorganization (Core vs FAT)
- GitHub Actions workflows operational
- Comprehensive testing infrastructure

---

## Support & Contact

For issues or questions:
1. Check this CLAUDE.md file
2. Review `README.md` for quick start
3. Check `FILE_LOCATIONS.md` for file references
4. Review `FAT/TESTING_GUIDE.md` for testing
5. Check workflow logs in [Actions page](../../actions)
6. Check compilation logs in `build/` directory
7. Open issue on GitHub

**Maintained by:** gregfar
**Last Updated:** 2025-11-14

---

**Note:** This CLAUDE.md file supersedes the legacy `/FAT/docs/CLAUDE.md`. The legacy file remains for historical reference but this root-level CLAUDE.md is the authoritative guide.
