# Manuscript Submission Tracker

## Overview

| Target | Format | Status | Link |
|--------|--------|--------|------|
| Zenodo | Data deposit | 🟡 Ready | - |
| bioRxiv | Preprint | 🟡 Ready | - |
| Scientific Data | Data Descriptor | 🟡 Ready | - |

## Zenodo Data Deposit

**Purpose**: Archive dataset and obtain DOI for citation

### Checklist
- [ ] Create Zenodo account
- [ ] Upload files:
  - [ ] `experiments.yaml` (primary)
  - [ ] `experiments.json`
  - [ ] `experiments.csv`
  - [ ] `registry_statistics.json`
  - [ ] `data_dictionary.csv`
  - [ ] `README.md`
- [ ] Fill metadata from `.zenodo.json`
- [ ] Add ORCID for all authors
- [ ] Select MIT license
- [ ] Publish and obtain DOI
- [ ] Update manuscripts with DOI

### Files to Upload
```
zenodo/
├── experiments.yaml     # Copy from ~/.ont-registry/
├── experiments.json     # ✓ Generated
├── experiments.csv      # ✓ Generated
├── registry_statistics.json  # ✓ Generated
├── data_dictionary.csv  # ✓ Created
└── README.md           # ✓ Created
```

---

## bioRxiv Preprint

**Purpose**: Establish priority, get community feedback

### Checklist
- [ ] Review `main_biorxiv.pdf` (10 pages)
- [ ] Replace placeholder author names
- [ ] Add ORCID for all authors
- [ ] Update Zenodo DOI in manuscript
- [ ] Submit to bioRxiv
  - [ ] Select subject: Bioinformatics
  - [ ] Upload PDF
  - [ ] Select CC-BY license
- [ ] Obtain bioRxiv DOI
- [ ] Update Scientific Data submission

### Submission URL
https://www.biorxiv.org/submit-a-manuscript

---

## Scientific Data

**Purpose**: Peer-reviewed publication as Data Descriptor

### Checklist
- [ ] Review `main_sdata.pdf`
- [ ] Replace placeholder author names
- [ ] Add ORCID for all authors
- [ ] Update Zenodo DOI
- [ ] Update bioRxiv DOI (if submitted)
- [ ] Prepare submission
  - [ ] Cover letter (`cover_letter_sdata.pdf`)
  - [ ] Main manuscript
  - [ ] Figures (3 PDFs)
- [ ] Submit via SNAPP system

### Submission URL
https://mts-sdata.nature.com/

### Requirements
- [x] Title ≤110 characters
- [x] Abstract ≤170 words
- [x] Data Descriptor format
- [x] ≤8 figures
- [x] Data deposited in repository (Zenodo)
- [ ] DOI for data citation

---

## Timeline

| Date | Action | Status |
|------|--------|--------|
| | Deposit data on Zenodo | Pending |
| | Submit to bioRxiv | Pending |
| | Submit to Scientific Data | Pending |
| | Address reviewer comments | - |
| | Publication | - |

---

## Author Information

Replace `[Author One]`, `[Author Two]`, `[Author Three]` in all files:

### Files requiring author updates:
- [ ] `main_manuscript.tex`
- [ ] `scientific_data/main_sdata.tex`
- [ ] `scientific_data/cover_letter_sdata.tex`
- [ ] `biorxiv/main_biorxiv.tex`
- [ ] `zenodo/.zenodo.json`
- [ ] `cover_letter.tex`

### Author template:
```
Author One: [Full Name], ORCID: 0000-0000-0000-0000
Author Two: [Full Name], ORCID: 0000-0000-0000-0000
Author Three: [Full Name], ORCID: 0000-0000-0000-0000
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-29 | Initial manuscript package |
