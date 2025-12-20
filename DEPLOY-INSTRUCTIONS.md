# ONT Ecosystem v2.1 - Deployment Instructions

## What's New in v2.1

### High-Resolution Read Length Analysis
- **BP-level precision**: Every observed read length stored and plotted at exact position
- **300 DPI default**: Publication-quality PNG output
- **Zoomable detail**: When zoomed, peaks resolve to individual base pairs
- **Multi-panel view**: Linear, log, short reads (0-5kb), long reads (>10kb)

## Deployment Steps

### Option 1: Direct GitHub Push

```bash
# Extract the package
tar -xzf ont-ecosystem-v2.1.tar.gz
cd ont-ecosystem

# Push to GitHub
./push-to-github.sh
```

If push fails, authenticate first:
```bash
gh auth login
# Then retry push
git push -u origin main
```

### Option 2: Manual Steps

```bash
# Extract
tar -xzf ont-ecosystem-v2.1.tar.gz
cd ont-ecosystem

# Set remote
git remote set-url origin https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git

# Push
git push -u origin main
```

### Option 3: Force Update (if repo has different history)

```bash
git push -u origin main --force
```

## After Deployment

### Verify Installation
```bash
curl -sSL https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/install.sh | bash
source ~/.ont-ecosystem/env.sh
ont_readlen_v2.py --help
```

### Test High-Resolution Plotting
```bash
# Generate test plot
ont_readlen_v2.py /path/to/run --plot test.png --dpi 300

# Detailed multi-panel plot
ont_readlen_v2.py /path/to/run --plot detailed.png --detailed
```

## Files in This Package

| File | Description |
|------|-------------|
| `ont-ecosystem-v2.1.tar.gz` | Complete package with git history |
| `ont_readlen_v2.py` | Standalone high-res analysis script |
| `ont_readlen_v2_SKILL.md` | Claude AI skill documentation |
| `test_ont_readlen_v2.py` | Unit tests |

## Integration with Existing Skills

The new `ont_readlen_v2.py` integrates with the Pattern B orchestration system.
Other ONT tools in the ecosystem will automatically work with the read length data.

Add to your ont-experiments Pattern B config:
```python
"readlen": {
    "script": "ont_readlen_v2.py",
    "description": "High-resolution read length distribution analysis",
    "result_fields": ["total_reads", "n50", "mean_length", "pct_gt_10kb"],
    "input_mode": "location",
}
```

## Example Usage

```bash
# Basic analysis
ont_readlen_v2.py /path/to/run --plot dist.png --json stats.json

# Compare multiple experiments
ont_readlen_v2.py exp1/ exp2/ exp3/ --plot comparison.png

# 600 DPI for publication
ont_readlen_v2.py /path/to/run --plot figure.png --dpi 600

# Quick preview
ont_readlen_v2.py /path/to/run --max-reads 100000 --plot preview.png
```
