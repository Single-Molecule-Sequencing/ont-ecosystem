---
description: Oxford Nanopore alignment with minimap2/dorado, reference genome management, and Levenshtein edit distance. Use when aligning ONT reads, managing reference genomes, computing BAM QC statistics, or calculating edit distances.
---

# /ont-align

Oxford Nanopore alignment with minimap2/dorado, reference genome management, and edit distance computation.

## Usage

Align reads and compute sequence distances:

$ARGUMENTS

## Quick Start

```bash
# Alignment
ont_align.py align reads.bam --reference GRCh38 --output aligned.bam

# Reference management
ont_align.py refs init
ont_align.py refs add GRCh38 /path/to/GRCh38.fa
ont_align.py refs list

# BAM QC
ont_align.py qc aligned.bam --json stats.json

# Edit distance
ont_align.py editdist "ACGTACGT" "ACGTTCGT" --cigar --normalize
```

## Commands

### Alignment
```bash
ont_align.py align <input> --reference <ref> --output <bam>

Options:
  --reference REF    Reference name or FASTA path
  --preset PRESET    map-ont, lr:hq, splice, asm5
  --threads N        Number of threads (default: 8)
  --json FILE        Output alignment stats
```

### Reference Management
```bash
ont_align.py refs init                    # Initialize registry
ont_align.py refs add <name> <fasta>      # Add reference
ont_align.py refs list                    # List references
ont_align.py refs import grch38|t2t       # Import standard
```

### Edit Distance (Levenshtein)
```bash
# Direct comparison
ont_align.py editdist "seq1" "seq2" --mode NW --cigar

# File-based batch
ont_align.py editdist --query variants.fa --target reference.fa --output distances.tsv

# All-vs-all matrix
ont_align.py editdist --query seqs.fa --self --output pairwise.tsv --threads 8
```

**Modes:**
- `NW`: Global alignment (Needleman-Wunsch)
- `HW`: Semi-global
- `SHW`: Infix (substring)

## Integration

```bash
# With provenance tracking
ont_experiments.py run alignment exp-abc123 --reference GRCh38 --output aligned.bam
```

## Dependencies

- pysam
- edlib
- numpy
- minimap2 (system)
- samtools (system)
