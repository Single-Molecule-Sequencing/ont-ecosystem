# ONT Registry Manuscript Package

Complete publication package for the Oxford Nanopore experiment registry manuscript.

## Quick Links

| Target | Main File | Cover Letter |
|--------|-----------|--------------|
| General | [main_manuscript.pdf](main_manuscript.pdf) | [cover_letter.pdf](cover_letter.pdf) |
| Scientific Data | [main_sdata.pdf](scientific_data/main_sdata.pdf) | [cover_letter_sdata.pdf](scientific_data/cover_letter_sdata.pdf) |
| bioRxiv | [main_biorxiv.pdf](biorxiv/main_biorxiv.pdf) | - |

## Package Structure

```
manuscript_figures/
│
├── INDEX.md                          # This file
├── SUBMISSION_TRACKER.md             # Submission checklist
│
├── Main Manuscript (General)
│   ├── main_manuscript.tex           # LaTeX source
│   ├── main_manuscript.pdf           # Compiled (27 pages)
│   ├── supplementary_materials.pdf   # Supplementary (7 pages)
│   ├── cover_letter.pdf              # Cover letter
│   ├── highlights.txt                # Key findings
│   └── graphical_abstract.pdf        # Visual summary
│
├── Text Sections
│   ├── abstract_registry.tex/.txt    # 261 words
│   ├── introduction_registry.tex/.txt # 818 words
│   ├── methods_registry.tex/.txt     # 622 words
│   ├── results_registry.tex/.txt     # 787 words
│   └── discussion_registry.tex/.txt  # 745 words
│
├── Figures (5)
│   ├── fig_registry_overview.pdf/png     # 6-panel overview
│   ├── fig_qc_distributions.pdf/png      # QC metrics
│   ├── fig_device_model_heatmap.pdf/png  # Device × model
│   ├── fig_category_by_device.pdf/png    # Categories
│   └── fig_temporal_analysis.pdf/png     # Temporal trends
│
├── Tables (3)
│   ├── tbl_registry_stats.tex        # Summary statistics
│   ├── tbl_registry_summary.tex      # Category breakdown
│   └── tbl_supp_experiments.tex      # Experiment list
│
├── References
│   └── references_registry.bib       # 13 citations
│
├── scientific_data/                  # Scientific Data format
│   ├── main_sdata.tex/.pdf           # Data Descriptor (11 pages)
│   ├── cover_letter_sdata.tex/.pdf
│   ├── references_sdata.bib          # 6 citations
│   └── README.md
│
├── biorxiv/                          # bioRxiv preprint
│   ├── main_biorxiv.tex/.pdf         # Preprint (10 pages)
│   ├── references_biorxiv.bib        # 9 citations
│   └── README.md
│
├── zenodo/                           # Data deposit
│   ├── experiments.yaml              # Primary registry (166 exp)
│   ├── experiments.json              # JSON export
│   ├── experiments.csv               # CSV export
│   ├── data_dictionary.csv           # Field definitions
│   ├── registry_statistics.json
│   ├── .zenodo.json                  # Deposit metadata
│   └── README.md
│
└── scripts/                          # Utilities
    ├── build_all.sh                  # Compile all LaTeX
    ├── word_counts.sh                # Statistics
    ├── update_authors.py             # Replace placeholders
    └── README.md
```

## Statistics

### Registry
- **165 experiments** (100% completeness)
- **August 2020 – December 2025**
- **95.2%** R10.4.1 chemistry
- **82.4%** Dorado basecaller
- **Median Q-score:** 14.0
- **Median N50:** 4,828 bp

### Manuscript
- **Main text:** 3,233 words
- **Figures:** 5 main + 1 graphical abstract
- **Tables:** 3 (+ supplementary)
- **References:** 13

### Versions
| Version | Pages | Words | Target |
|---------|-------|-------|--------|
| Main | 27 | 5,921 | General journals |
| Supplementary | 7 | 1,123 | All |
| Scientific Data | 11 | 2,257 | Nature |
| bioRxiv | 10 | 2,025 | Preprint |

## Submission Order

1. **Zenodo** → Deposit data, get DOI
2. **bioRxiv** → Submit preprint (optional)
3. **Scientific Data** → Submit Data Descriptor

## Before Submission

- [ ] Replace `[Author One/Two/Three]` placeholders
- [ ] Add ORCID identifiers
- [ ] Update Zenodo DOI in manuscripts
- [ ] Review all PDFs
- [ ] Run `./scripts/build_all.sh`

## Commands

```bash
# Navigate to package
cd data/manuscript_figures

# Update authors
python scripts/update_authors.py \
    --author1 "Name" --author2 "Name" --author3 "Name" \
    --email "email@umich.edu"

# Build all PDFs
./scripts/build_all.sh

# Check statistics
./scripts/word_counts.sh

# Open main manuscript
explorer.exe main_manuscript.pdf  # Windows
xdg-open main_manuscript.pdf      # Linux
```

## License

MIT License - See repository for details.

## Repository

https://github.com/Single-Molecule-Sequencing/ont-ecosystem
