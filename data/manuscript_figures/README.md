# ONT Registry Manuscript

Publication-ready manuscript describing the Oxford Nanopore experiment registry.

## Compilation

```bash
cd data/manuscript_figures
pdflatex main_manuscript
bibtex main_manuscript
pdflatex main_manuscript
pdflatex main_manuscript
```

## File Structure

### Main Document
- `main_manuscript.tex` - Master document assembling all sections

### Text Sections
| File | Section | Words |
|------|---------|-------|
| `abstract_registry.tex` | Abstract | 261 |
| `introduction_registry.tex` | Introduction | 818 |
| `methods_registry.tex` | Methods | ~800 |
| `results_registry.tex` | Results | ~1,200 |
| `discussion_registry.tex` | Discussion | ~1,100 |

### Supporting Sections
- `acknowledgments.tex`
- `author_contributions.tex`
- `data_availability.tex`
- `competing_interests.tex`

### Figures (5)
| Figure | File | Description |
|--------|------|-------------|
| Fig. 1 | `fig_registry_overview.*` | 6-panel registry overview |
| Fig. 2 | `fig_qc_distributions.*` | QC metrics distributions |
| Fig. 3 | `fig_device_model_heatmap.*` | Device × model matrix |
| Fig. 4 | `fig_category_by_device.*` | Categories by device |
| Fig. 5 | `fig_temporal_analysis.*` | Temporal trends |

### Tables (3)
| Table | File | Description |
|-------|------|-------------|
| Table 1 | `tbl_registry_stats.tex` | Summary statistics |
| Table 2 | `tbl_registry_summary.tex` | Category breakdown |
| Table S1 | `tbl_supp_experiments.tex` | Experiment list |

### References
- `references_registry.bib` - BibTeX database (13 references)

## Key Statistics

- **165 experiments** with 100% completeness
- **Temporal span:** August 2020 - December 2025
- **Top application:** Plasmid sequencing (48.5%)
- **Chemistry:** 95.2% R10.4.1
- **Basecaller:** 82.4% dorado
- **Median Q-score:** 14.0
- **Median N50:** 4,828 bp

## Plain Text Versions

All text sections are available in `.txt` format for non-LaTeX use.
