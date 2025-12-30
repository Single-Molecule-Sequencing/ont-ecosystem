# SMA-seq Library Structure and Processing

## Overview

SMA-seq (Single Molecule Amplicon sequencing) uses Golden Gate cloning with custom barcodes to sequence both strands of CYP2D6 pharmacogene target regions.

## Library Structure

All reads are sequenced **5'→3' from the Native Adapter**. Each molecule has identical structure:

```
5'─[PREFIX]─[ADAPTER]─[FLANK_F]─[BARCODE]─[FLANK_R]─[TARGET]─3'
   (13bp)    (15bp)     (8bp)    (22-24bp)   (8bp)   (157-161bp)
```

### Library Elements

| Element | Sequence | Length | Description |
|---------|----------|--------|-------------|
| PREFIX | `CCTGTACTTCGTT` | 13bp | Prefix before adapter |
| ADAPTER | `CAGTTACGTATTGCT` | 15bp | Native Adapter end |
| FLANK_F | `AAGGTTAA` | 8bp | Front flank |
| FLANK_R | `CAGCACCT` | 8bp | Rear flank |

### Barcode Sequences

| Barcode | Sequence | Length |
|---------|----------|--------|
| BC02 | `ACAGACGACTACAAACGGAATCGA` | 24bp |
| BC04 | `TAGCAAACACGATAGAATCCGAA` | 23bp |
| BC07 | `GGATTCATTCCCACGGTAACAC` | 22bp |
| BC09 | `AACCAAGACTCGCTGTGCCTAGTT` | 24bp |

## Target Orientation by Barcode

The 4bp 5' overhang at each end of the double-stranded target determines which barcode ligates. This creates two populations:

| Barcode | Target | Description |
|---------|--------|-------------|
| BC02 | V0-4.2_forward | CYP2D6 pos 7108-7268 (161bp) |
| BC07 | V0-4.2_reverse | RC of above |
| BC04 | V0-4.4_reverse | RC of CYP2D6 pos 7453-7608 |
| BC09 | V0-4.4_forward | CYP2D6 pos 7453-7608 (157bp) |

**Note:** Target sequences have the last 4bp removed (not part of the nicked reference).

## Full Reference Sequences

### BC02 (229bp)
```
PREFIX:   CCTGTACTTCGTT
ADAPTER:  CAGTTACGTATTGCT
FLANK_F:  AAGGTTAA
BARCODE:  ACAGACGACTACAAACGGAATCGA
FLANK_R:  CAGCACCT
TARGET:   AGGATTTGCATAGATGGGTTTGGGAAAGGACATTCCAGGAGATCCCACTGTAAGAAGGGCCTGGAGGAGGAGGGGACATCTCAGACATGGTCGTGGGAGAGGTGTGCCCGGGTCAGGGGGCACCAGGAGAGGCCAAGGACTCTGTACCTCCTATCCACGTC
```

### BC07 (227bp)
```
PREFIX:   CCTGTACTTCGTT
ADAPTER:  CAGTTACGTATTGCT
FLANK_F:  AAGGTTAA
BARCODE:  GGATTCATTCCCACGGTAACAC
FLANK_R:  CAGCACCT
TARGET:   GACGTGGATAGGAGGTACAGAGTCCTTGGCCTCTCCTGGTGCCCCCTGACCCGGGCACACCTCTCCCACGACCATGTCTGAGATGTCCCCTCCTCCTCCAGGCCCTTCTTACAGTGGGATCTCCTGGAATGTCCTTTCCCAAACCCATCTATGCAAATCCT
```

### BC04 (224bp)
```
PREFIX:   CCTGTACTTCGTT
ADAPTER:  CAGTTACGTATTGCT
FLANK_F:  AAGGTTAA
BARCODE:  TAGCAAACACGATAGAATCCGAA
FLANK_R:  CAGCACCT
TARGET:   GTCAGATCTCGGGGGGGCTGGGCTGGGTCCCAGGTCATCCTGTGCTCAGTTAGCAGCTCATCCAGCTGGGTCAGGAAAGCCTTTTGGAAGCGTAGGACCTTGCCAGCCAGCGCTGGGATATGCAGGAGGACGGGGACAGCATTCAGCACCTACACCA
```

### BC09 (225bp)
```
PREFIX:   CCTGTACTTCGTT
ADAPTER:  CAGTTACGTATTGCT
FLANK_F:  AAGGTTAA
BARCODE:  AACCAAGACTCGCTGTGCCTAGTT
FLANK_R:  CAGCACCT
TARGET:   TGGTGTAGGTGCTGAATGCTGTCCCCGTCCTCCTGCATATCCCAGCGCTGGCTGGCAAGGTCCTACGCTTCCAAAAGGCTTTCCTGACCCAGCTGGATGAGCTGCTAACTGAGCACAGGATGACCTGGGACCCAGCCCAGCCCCCCCGAGATCTGAC
```

## Dorado Demultiplexing

Demux runs in 3 passes (one per barcode length):

1. **SMA_24bp** (BC02, BC09): `config/SMA_24bp.toml` + `config/SMA_24bp_sequences.fasta`
2. **SMA_23bp** (BC04): `config/SMA_23bp.toml` + `config/SMA_23bp_sequences.fasta`
3. **SMA_22bp** (BC07): `config/SMA_22bp.toml` + `config/SMA_22bp_sequences.fasta`

### TOML Configuration

Each TOML uses mask patterns to locate the barcode:
```toml
mask1_front = "ATTGCTAAGGTTAA"   # Last 6bp of ADAPTER + FLANK_F
mask1_rear = "CAGCACCT"          # FLANK_R
```

## Processing Pipeline

1. **Demux**: `run_demux.sh` - Separates reads by barcode
2. **Tag**: `tag_demuxed_reads.py` - Adds QC tags (ED, Q-score, size)
3. **Analyze**: `analyze_reads.py` - Generates distribution plots

## QC Metrics

Each read is tagged with:
- `eq:f` - Mean Q-score (probability-space average)
- `ed:i` - Edit distance to full reference sequence
- `sz:Z` - Size status (in_range/short/long)
- `bc:Z` - Barcode assignment

## Size Ranges

| Barcode | Expected Size | Target |
|---------|---------------|--------|
| BC02 | 200-260bp | V0-4.2 (161bp target) |
| BC07 | 200-260bp | V0-4.2 (161bp target) |
| BC04 | 195-255bp | V0-4.4 (157bp target) |
| BC09 | 195-255bp | V0-4.4 (157bp target) |

## Files

- `sma_seq_config.yaml` - Machine-readable configuration
- `reference.fa` - Target sequences (FASTA)
- `config/*.toml` - Dorado demux arrangements
- `config/*_sequences.fasta` - Custom barcode sequences
