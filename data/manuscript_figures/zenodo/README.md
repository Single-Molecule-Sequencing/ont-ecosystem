# ONT Experiment Registry Dataset

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)

## Description

A comprehensive registry of 165 Oxford Nanopore sequencing experiments conducted at the University of Michigan between August 2020 and December 2025.

## Dataset Contents

| File | Format | Description |
|------|--------|-------------|
| `experiments.yaml` | YAML | Primary registry (authoritative) |
| `experiments.json` | JSON | Machine-readable export |
| `experiments.csv` | CSV | Tabular export for spreadsheets |
| `registry_statistics.json` | JSON | Aggregate statistics |
| `data_dictionary.csv` | CSV | Field definitions and valid values |
| `CHANGELOG.md` | Markdown | Version history |

## Quick Start

### Python
```python
import yaml

with open('experiments.yaml') as f:
    registry = yaml.safe_load(f)

# Get all R10.4.1 experiments
r10_exps = [exp for exp_id, exp in registry.items()
            if exp.get('chemistry', {}).get('version') == 'R10.4.1']
print(f"R10.4.1 experiments: {len(r10_exps)}")
```

### R
```r
library(jsonlite)
registry <- fromJSON("experiments.json")
```

### Command Line
```bash
# Count experiments by category
jq -r '.[].sample.category' experiments.json | sort | uniq -c
```

## Key Statistics

| Metric | Value |
|--------|-------|
| Total experiments | 165 |
| Temporal range | Aug 2020 – Dec 2025 |
| R10.4.1 chemistry | 95.2% |
| Dorado basecaller | 82.4% |
| HAC model | 89.7% |
| Median Q-score | 14.0 |
| Median N50 | 4,828 bp |

## Schema Overview

```yaml
experiment_id:
  name: string
  date: YYYY-MM-DD
  sample:
    category: [plasmid|human|bacterial|research|pharmacogenomics|standard|cell_line|other]
    name: string
  chemistry:
    flowcell_type: string (e.g., FLO-MIN114)
    kit: string (e.g., SQK-LSK114)
    version: [R10.4.1|R10.4]
  basecalling:
    software: [dorado|guppy|bonito]
    model: [fast|hac|sup]
  device:
    type: [MinION|MinION_Mk1D|PromethION|P2_Solo|Flongle]
  qc:
    total_reads: integer
    mean_qscore: float
    n50: integer
```

## Citation

If you use this dataset, please cite:

```bibtex
@misc{ont_registry_2025,
  author = {[Author One] and [Author Two] and [Author Three]},
  title = {{ONT} Experiment Registry: Metadata and Quality Metrics for 165 Oxford Nanopore Sequencing Experiments},
  year = {2025},
  publisher = {Zenodo},
  doi = {10.5281/zenodo.XXXXXXX},
  url = {https://doi.org/10.5281/zenodo.XXXXXXX}
}
```

## Related Resources

- **Code Repository**: https://github.com/Single-Molecule-Sequencing/ont-ecosystem
- **Manuscript**: [Scientific Data article link]

## License

This dataset is released under the [MIT License](LICENSE).

## Contact

For questions or issues, please open a GitHub issue or contact [email]@umich.edu.
