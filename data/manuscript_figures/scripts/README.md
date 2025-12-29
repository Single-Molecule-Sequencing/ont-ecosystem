# Manuscript Scripts

Utility scripts for managing the manuscript package.

## Scripts

### `build_all.sh`
Compile all LaTeX manuscripts in one command.

```bash
./scripts/build_all.sh
```

Builds:
- `main_manuscript.pdf` (27 pages)
- `supplementary_materials.pdf` (7 pages)
- `cover_letter.pdf`
- `scientific_data/main_sdata.pdf`
- `scientific_data/cover_letter_sdata.pdf`
- `biorxiv/main_biorxiv.pdf`

### `word_counts.sh`
Generate word counts for all manuscript versions.

```bash
./scripts/word_counts.sh
```

Reports:
- Word counts for each section
- Total word count
- PDF page counts
- Figure and table counts
- Reference counts

### `update_authors.py`
Replace author placeholders across all files.

```bash
python scripts/update_authors.py \
    --author1 "Jane Smith" \
    --author2 "John Doe" \
    --author3 "Alice Wong" \
    --orcid1 "0000-0001-2345-6789" \
    --orcid2 "0000-0002-3456-7890" \
    --orcid3 "0000-0003-4567-8901" \
    --email "jsmith@umich.edu"
```

Options:
- `--dry-run`: Preview changes without applying

## Quick Start

```bash
cd data/manuscript_figures

# 1. Update author information
python scripts/update_authors.py --author1 "..." --author2 "..." --author3 "..." --email "..."

# 2. Build all PDFs
./scripts/build_all.sh

# 3. Check word counts
./scripts/word_counts.sh

# 4. Commit changes
git add . && git commit -m "Update author information"
```
