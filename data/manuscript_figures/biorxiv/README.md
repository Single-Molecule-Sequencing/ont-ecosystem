# bioRxiv Preprint

Preprint version formatted for [bioRxiv](https://www.biorxiv.org/).

## Format

- Single-column layout
- Double-spaced with line numbers
- Standard article structure (Introduction/Methods/Results/Discussion)
- 10 pages, 3 figures

## Files

| File | Description |
|------|-------------|
| `main_biorxiv.tex` | LaTeX source |
| `main_biorxiv.pdf` | Compiled preprint (10 pages) |
| `references_biorxiv.bib` | Bibliography (9 references) |

## Compilation

```bash
cd data/manuscript_figures/biorxiv
pdflatex main_biorxiv
bibtex main_biorxiv
pdflatex main_biorxiv
pdflatex main_biorxiv
```

## bioRxiv Submission

1. Go to https://www.biorxiv.org/submit-a-manuscript
2. Select subject area: **Bioinformatics**
3. Upload `main_biorxiv.pdf`
4. Add author information and ORCID
5. Select license (CC-BY recommended)
6. Submit for screening

## Differences from Journal Version

| Aspect | bioRxiv | Scientific Data |
|--------|---------|-----------------|
| Sections | Traditional | Data Descriptor |
| Length | 10 pages | ~12 pages |
| References | 9 | 6 |
| Figures | 3 | 3 |
| Abstract | Structured (Background/Results/Conclusions) | Single paragraph |

## License

Recommend CC-BY 4.0 for maximum reuse.
