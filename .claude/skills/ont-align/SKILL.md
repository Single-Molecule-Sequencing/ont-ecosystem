---
name: ont-align
description: Oxford Nanopore alignment with minimap2/dorado, reference genome management, BAM QC, and Levenshtein edit distance computation using edlib. Use when aligning ONT reads to reference genomes, managing reference genome registries, computing alignment statistics, generating coverage metrics, performing BAM quality control, or computing edit distances between sequences. Integrates with ont-experiments for provenance tracking via Pattern B orchestration.
---

# ONT Align - Alignment & Edit Distance

Alignment toolkit for Oxford Nanopore data with reference management, QC, and sequence comparison.

## Quick Start

```bash
# Alignment
ont_align.py align reads.bam --reference GRCh38 --output aligned.bam

# Reference management
ont_align.py refs init
ont_align.py refs add GRCh38 /path/to/GRCh38.fa

# BAM QC
ont_align.py qc aligned.bam --json stats.json

# Edit distance
ont_align.py editdist "ACGTACGT" "ACGTTCGT" --cigar --normalize
```

## Commands

### Alignment

```bash
ont_align.py align <input> --reference <ref> --output <bam> [options]

Options:
  --reference REF    Reference name from registry or path to FASTA
  --output FILE      Output BAM file
  --preset PRESET    map-ont (default), lr:hq, splice, asm5, asm20
  --threads N        Number of threads (default: 8)
  --json FILE        Output alignment statistics JSON
```

### Reference Management

```bash
ont_align.py refs init                    # Initialize registry
ont_align.py refs add <name> <fasta>      # Add reference
ont_align.py refs list                    # List references
ont_align.py refs info <name>             # Show details
ont_align.py refs import grch38|t2t       # Import standard reference
```

### BAM QC

```bash
ont_align.py qc <bam> --json stats.json --plot coverage.png
```

### Edit Distance (Levenshtein)

Uses edlib for fast edit distance computation.

```bash
# Direct comparison
ont_align.py editdist "ACGTACGT" "ACGTTCGT"

# With options
ont_align.py editdist "seq1" "seq2" --mode NW --cigar --normalize

# File-based batch
ont_align.py editdist --query variants.fa --target reference.fa --output distances.tsv

# All-vs-all matrix
ont_align.py editdist --query seqs.fa --self --output pairwise.tsv --threads 8
```

**Modes:**
- `NW`: Global alignment (Needleman-Wunsch) - default
- `HW`: Semi-global (query fully aligned, target has free end gaps)
- `SHW`: Infix (find query as substring of target)

## Integration

Run through ont-experiments for provenance tracking:

```bash
ont_experiments.py run alignment exp-abc123 --reference GRCh38 --output aligned.bam
```

## Dependencies

```bash
pip install pysam edlib numpy
# System: minimap2, samtools
```
