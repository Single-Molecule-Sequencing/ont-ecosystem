# Scientific Data Submission

Manuscript formatted for [Scientific Data](https://www.nature.com/sdata/) (Nature) as a **Data Descriptor**.

## Article Type

**Data Descriptor** - A peer-reviewed article describing a scientifically valuable dataset.

## Manuscript Structure

The Data Descriptor format includes these required sections:

| Section | Description | Word Limit |
|---------|-------------|------------|
| Title | Max 110 characters, no colons | 110 chars |
| Abstract | Summary of dataset | 170 words |
| Background & Summary | Context and significance | No limit |
| Methods | Data generation and processing | No limit |
| Data Records | Dataset description and access | Required |
| Technical Validation | Quality assurance | Required |
| Usage Notes | How to use the data | Required |
| Code Availability | Repository links | Required |

## Files

| File | Description |
|------|-------------|
| `main_sdata.tex` | Main manuscript (LaTeX) |
| `main_sdata.pdf` | Compiled manuscript |
| `references_sdata.bib` | Bibliography (Nature format) |

## Figures

Uses figures from parent directory:
- Figure 1: `fig_registry_overview.pdf` - Registry overview (6 panels)
- Figure 2: `fig_qc_distributions.pdf` - QC metrics (3 panels)
- Figure 3: `fig_temporal_analysis.pdf` - Temporal trends (4 panels)

## Compilation

```bash
cd data/manuscript_figures/scientific_data
pdflatex main_sdata
bibtex main_sdata
pdflatex main_sdata
pdflatex main_sdata
```

## Key Requirements

### Data Repository
- Dataset must be deposited in a public repository
- DOI required for data citation
- Suggested: Zenodo, Figshare, or institutional repository

### Data Citation
References to datasets should include:
- Author list
- Dataset title
- Repository name
- DOI/URL
- Year

### LLM Disclosure
Scientific Data requires disclosure of LLM use in Methods section.

## Checklist

- [x] Title ≤110 characters
- [x] Abstract ≤170 words
- [x] Background & Summary section
- [x] Methods section
- [x] Data Records section
- [x] Technical Validation section
- [x] Usage Notes section
- [x] Code Availability section
- [x] Author Contributions (CRediT format)
- [x] Competing Interests statement
- [x] ≤8 figures (using 3)
- [ ] Data deposited in repository
- [ ] DOI assigned to dataset
- [ ] ORCID for all authors
