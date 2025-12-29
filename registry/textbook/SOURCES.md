# Textbook Registry Sources

This registry was extracted from multiple sources related to the SMS Haplotype Framework Textbook.

## Source Hierarchy (Priority Order)

1. **All_Math PDF/TeX** - Canonical mathematical definitions
2. **SMS_textbook Repository** - Comprehensive equation/variable databases
3. **Extracted PDFs/LaTeX** - Supplementary content

## Primary Mathematical Source

### All_Math (CANONICAL for equations)
- **PDF**: `C:\Users\farnu\Downloads\All_Math (4).pdf`
- **TeX Source**: `C:\Users\farnu\Downloads\All_Math\main.tex`
- **Author**: Pranjal Srivastava (November 2025)
- **Registry file**: `all_math_authoritative.yaml`
- **Content**:
  - Error Quantification (Phred, edit distance, quality metrics)
  - Single-Molecule Sequencing and Basecalling Model
  - Confusion Matrix and Empirical Error Models
  - Haplotype Classification (Bayesian posterior)
  - Diplotypes, Polyploidy, Cost-Based Decisions
  - Read-Level Haplotagging
  - Plasmid Replication and Purity Bounds
  - Dual Cas9 Cutting Probability

**When equations conflict between sources, All_Math takes precedence.**

## Comprehensive Database Source

### SMS_textbook Repository (PRIMARY SOURCE)
- **Path**: `D:\repos\SMS_textbook` (WSL: `/mnt/d/repos/SMS_textbook`)
- **Type**: Git repository with LaTeX source and YAML databases
- **Files copied to registry**:
  - `equations_full.yaml` (4087 lines) - Complete equation database
  - `variables_full.yaml` (3532 lines) - Complete variable database
  - `database_schema.yaml` (311 lines) - Schema documentation
- **Additional resources**:
  - `CLAUDE.md` (36KB) - Comprehensive AI agent guidance
  - `src/chapters/` - LaTeX chapter sources
  - `src/appendices/` - LaTeX appendix sources
  - Build scripts for PDF compilation

**This is the canonical source for all equations and variables. When updating the registry, sync from this repository.**

## Secondary Sources (Extracted/Derived)

### 1. Full Textbook PDF
- **Path**: `/mnt/c/Users/farnu/Downloads/SMS_Haplotype_Framework_Textbook 96.pdf`
- **Size**: 2.2 MB (26,560 lines extracted via pdftotext)
- **Version**: 6.0 (Complete Edition, November 2025)
- **Completion**: 75% (14/20 chapters complete)
- **Extraction method**: `pdftotext -layout`

### 2. Math Reference PDF
- **Path**: `/mnt/c/Users/farnu/Downloads/All_Math (4).pdf`
- **Content**: 19 pages of core mathematical models
- **Sections covered**:
  - Error Quantification (Phred scores)
  - Basecalling Model
  - Confusion Matrix
  - Haplotype Classification
  - Diplotypes and Polyploidy
  - Haplotagging
  - Plasmid Replication/Purity
  - Dual Cas9 Cutting

### 3. Extracted Figures and Tables
- **Path**: `/mnt/c/Users/farnu/Downloads/extracted-figures-tables-main/`
- **Content**:
  - 15 figures (LaTeX TikZ)
  - 145 tables (LaTeX tabular)
  - `metadata.json` with structured extraction data
- **Key tables used**:
  - `chapter4_enhancements_table01.tex` - Variable definitions
  - `appendixC_populated_table01.tex` - QC gates
  - `chapter6_populated_table01.tex` - Bayes factor scale

### 4. Individual Chapter PDFs
- **Path**: `/mnt/c/Users/farnu/Downloads/individual-documents-claude-enhance-math-content-011JeeaG42AKf8aKy4WP6Kd7/`
- **Content**: 29 individual chapter/appendix PDFs
- **Key files used**:
  - `appendixB_populated.pdf` - Core equations (18 pages)
  - `appendixC_populated.pdf` - QC gates
  - `chapter4_populated.pdf` - Classification model
  - `chapter5_populated.pdf` - Purity theory
  - `chapter6_populated.pdf` - Posterior computation
  - `chapter11_populated.pdf` - SMA-seq protocol

## Registry Files Created

| File | Content | Lines |
|------|---------|-------|
| `chapters.yaml` | Chapter index, reading paths | ~100 |
| `definitions.yaml` | 9 definitions, 8 theorems | ~200 |
| `equations.yaml` | 18 core equations with LaTeX/Python | ~350 |
| `frameworks.yaml` | SMA-SEER, Pipeline Factorization | ~250 |
| `variables.yaml` | 50+ variable definitions | ~400 |
| `qc_gates.yaml` | 15 QC gates with thresholds | ~250 |

## Extraction Pipeline

```bash
# 1. Extract full textbook
pdftotext -layout "SMS_Haplotype_Framework_Textbook 96.pdf" /tmp/textbook.txt

# 2. Parse structure
grep -n "^Chapter\|^Part\|Definition\|Theorem" /tmp/textbook.txt

# 3. Extract equations
grep -n "P(h\|P(r\|Phred\|posterior" /tmp/textbook.txt

# 4. Read LaTeX tables from extracted directory
cat extracted/tables/chapter4_enhancements_table01.tex

# 5. Create structured YAML registries
# (manual curation into registry/textbook/*.yaml)
```

## Future Updates

When the textbook is updated:
1. Re-run pdftotext on new PDF
2. Compare chapter structure to `chapters.yaml`
3. Update equation references in `equations.yaml`
4. Verify QC thresholds in `qc_gates.yaml`
5. Update `last_extracted` date in all files

## Cross-References

- Registry equations link to textbook via `chapter` field
- Variables link to definitions via `chapter` and `latex` fields
- QC gates link to skills via `skill_mapping` section
- Frameworks link to pipeline stages via `pipeline_stages` field
