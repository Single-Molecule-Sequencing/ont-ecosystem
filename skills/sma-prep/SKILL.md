---
name: sma-prep
description: SMA-seq library preparation and reference management. Create reference files, sample sheets, custom barcode schemes, and run Dorado demultiplexing with full metadata tracking. Supports Golden Gate library prep, size-based sequence classification, and integration with the central experiment database. Triggers on requests for SMA-seq setup, reference creation, sample sheets, barcode configuration, or experiment initialization.
---

# SMA-seq Preparation Skill

Complete workflow for preparing and running SMA-seq experiments with Oxford Nanopore sequencing.

## Quick Start

```bash
# Interactive setup wizard (recommended for new users)
python3 scripts/sma_prep.py wizard

# Create reference files for a new target
python3 scripts/sma_prep.py ref --name V04 --sequence "ACGT..." --length 222

# Generate sample sheet from barcode mapping
python3 scripts/sma_prep.py samplesheet --barcodes 2:WT,4:MUT,7:Control,9:Treatment

# Full experiment setup
python3 scripts/sma_prep.py init --exp-id exp-001 \
    --targets V04,V05,V06 \
    --barcodes 2,4,7,9 \
    --sample-map sample_info.csv
```

## Workflow Overview

### Step 1: Define Target Sequences

SMA-seq targets are plasmid constructs or amplicons with known sequences:

```bash
# Add a new target to the registry
python3 scripts/sma_prep.py target add \
    --name "V04" \
    --sequence "CTGTCCTGTACTTCGTTCAGTTACGTATTGCTAAGGTTAA..." \
    --description "V04 SMA plasmid construct" \
    --expected-size 222 \
    --barcode 2

# List registered targets
python3 scripts/sma_prep.py target list

# Import targets from FASTA
python3 scripts/sma_prep.py target import targets.fa
```

### Step 2: Create Sample Sheet

Map barcodes to samples with metadata:

```bash
# Quick barcode mapping
python3 scripts/sma_prep.py samplesheet \
    --barcodes "2:V04_WT,4:V04_MUT,7:V05_WT,9:V05_MUT" \
    --output samples.csv

# From CSV template
python3 scripts/sma_prep.py samplesheet \
    --from-csv sample_metadata.csv \
    --output samples.csv

# Interactive mode
python3 scripts/sma_prep.py samplesheet --interactive
```

Sample sheet format:
```csv
barcode,sample_id,target,condition,replicate,notes
2,V04_WT,V04,wildtype,1,
4,V04_MUT,V04,G>A_mut,1,
7,V05_WT,V05,wildtype,1,
9,V05_MUT,V05,deletion,1,
```

### Step 3: Create Barcode Configuration

Generate Dorado-compatible barcode files:

```bash
# Using preset
python3 scripts/sma_prep.py barcodes \
    --preset sma-single-ended \
    --sample-sheet samples.csv \
    --output-dir config/

# Custom flanking sequences
python3 scripts/sma_prep.py barcodes \
    --mask1-front "AAGGTTAA" \
    --mask1-rear "CAGCACCT" \
    --sample-sheet samples.csv \
    --output-dir config/
```

### Step 4: Generate Reference FASTA

Create reference file for alignment:

```bash
# From registered targets
python3 scripts/sma_prep.py ref \
    --targets V04,V05 \
    --output reference.fa

# Include barcode sequences in reference
python3 scripts/sma_prep.py ref \
    --targets V04,V05 \
    --include-barcodes \
    --output reference_with_bc.fa
```

### Step 5: Run Dorado

Execute basecalling and demultiplexing:

```bash
# Generate SLURM script
python3 scripts/sma_prep.py dorado \
    --pod5-dir /path/to/pod5 \
    --config-dir config/ \
    --reference reference.fa \
    --output-dir results/ \
    --slurm job.sbatch

# Direct execution (local)
python3 scripts/sma_prep.py dorado \
    --pod5-dir /path/to/pod5 \
    --config-dir config/ \
    --reference reference.fa \
    --output-dir results/ \
    --run
```

### Step 6: Register with Database

Store experiment metadata:

```bash
# Initialize experiment in registry
python3 scripts/sma_prep.py register \
    --exp-id exp-001 \
    --sample-sheet samples.csv \
    --config-dir config/ \
    --bam-dir results/

# Link to ont-experiments registry
ont_experiments.py link exp-001 --sma-prep-config config/
```

## Size-Based Sequence Classification

Map expected read lengths to target sequences for automatic classification:

```bash
# Define size ranges
python3 scripts/sma_prep.py sizes \
    --add "V04:200-250" \
    --add "V05:180-220" \
    --add "V06:250-300"

# View size mappings
python3 scripts/sma_prep.py sizes --list

# Classify reads by size
python3 scripts/sma_prep.py classify \
    --bam results/demuxed.bam \
    --sizes sizes.yaml \
    --output classified/
```

Size range configuration (`sizes.yaml`):
```yaml
targets:
  V04:
    expected_length: 222
    min_length: 200
    max_length: 250
    tolerance_pct: 15

  V05:
    expected_length: 198
    min_length: 175
    max_length: 225
    tolerance_pct: 15

  V06:
    expected_length: 275
    min_length: 250
    max_length: 310
    tolerance_pct: 15

# Overlapping sizes trigger alignment-based classification
overlap_resolution: alignment  # or 'strict' to reject
```

## Database Integration

### SQLite Schema

The skill creates/updates a local SQLite database:

```sql
-- Experiments table
CREATE TABLE experiments (
    exp_id TEXT PRIMARY KEY,
    created_at TIMESTAMP,
    sample_sheet_path TEXT,
    config_dir TEXT,
    targets TEXT,  -- JSON array
    barcodes TEXT, -- JSON array
    status TEXT,
    metadata TEXT  -- JSON blob
);

-- Targets table
CREATE TABLE targets (
    target_id TEXT PRIMARY KEY,
    name TEXT,
    sequence TEXT,
    length INTEGER,
    description TEXT,
    created_at TIMESTAMP,
    metadata TEXT
);

-- Samples table
CREATE TABLE samples (
    sample_id TEXT PRIMARY KEY,
    exp_id TEXT REFERENCES experiments(exp_id),
    barcode INTEGER,
    target_id TEXT REFERENCES targets(target_id),
    condition TEXT,
    replicate INTEGER,
    read_count INTEGER,
    mean_qscore REAL,
    metadata TEXT
);

-- Size mappings table
CREATE TABLE size_mappings (
    target_id TEXT REFERENCES targets(target_id),
    min_length INTEGER,
    max_length INTEGER,
    expected_length INTEGER,
    PRIMARY KEY (target_id)
);
```

### Query Examples

```python
import sqlite3
conn = sqlite3.connect('sma_experiments.db')

# Get all samples for experiment
cur.execute('''
    SELECT s.sample_id, s.barcode, t.name, s.condition
    FROM samples s
    JOIN targets t ON s.target_id = t.target_id
    WHERE s.exp_id = ?
''', ('exp-001',))

# Find target by size range
cur.execute('''
    SELECT target_id, expected_length
    FROM size_mappings
    WHERE min_length <= ? AND max_length >= ?
''', (215, 215))
```

## Golden Gate Library Prep Context

### BsaI-HF Digestion

SMA-seq uses Golden Gate assembly with BsaI-HF:

```
5'-GGTCTC(N)₁↓----3'    BsaI recognition
3'-CCAGAG(N)₅----↑5'    Creates 4bp overhang
```

The 4bp overhang sequence determines ligation specificity:

```yaml
# Standard SMA-seq overhangs
overhangs:
  insert_5prime: "AGGA"  # After CAGCACCT flank
  insert_3prime: "CTGT"  # Before AAGGTTAA flank

  # Must avoid these (form unwanted products)
  forbidden:
    - ACGA  # Complements adapter
    - GTTA  # Complements barcode
    - TCGT  # Backbone→adapter
    - TAAC  # Backbone→barcode
```

### Nick Design (Single-Ended)

Modified barcodes lack 5' phosphate on bottom strand:

```
Top:    5'-P-[flank]-[24bp BC]-[flank]-[4bp OH]-P-3'
Bottom: 3'---[flank]-[24bp BC]-[flank]----✗-----5'
                                         ↑
                                   NO phosphate → nick
```

Benefits:
1. Prevents barcode dimers
2. Single-ended detection (no rear barcode)
3. Simplified workflow

## Command Reference

| Command | Description |
|---------|-------------|
| `wizard` | Interactive setup guide |
| `target add` | Register new target sequence |
| `target list` | List registered targets |
| `target import` | Import targets from FASTA |
| `samplesheet` | Generate sample sheet |
| `barcodes` | Create Dorado barcode config |
| `ref` | Generate reference FASTA |
| `sizes` | Manage size-to-target mappings |
| `classify` | Classify reads by size/alignment |
| `dorado` | Run/generate Dorado commands |
| `register` | Store experiment in database |
| `validate` | Validate experiment setup |

## Integration with ONT Ecosystem

### Pattern B Orchestration

```bash
# Run through ont-experiments for provenance tracking
ont_experiments.py run sma-prep exp-001 \
    --targets V04,V05 \
    --barcodes 2,4,7,9 \
    --pod5-dir /path/to/pod5
```

### With dorado-bench

```bash
# Benchmark different models
python3 scripts/sma_prep.py dorado \
    --pod5-dir /path/to/pod5 \
    --models fast,hac,sup \
    --benchmark
```

### With manuscript skill

```bash
# Generate publication figures from SMA-seq results
ont_manuscript.py figure sma-qc --exp exp-001
```

## Files

- `scripts/sma_prep.py` - Main CLI tool
- `references/sma_targets.yaml` - Target sequence definitions
- `references/presets.yaml` - Barcode presets (from ont-custom-barcodes)
- `references/size_ranges.yaml` - Default size mappings

## Example: Complete Workflow

```bash
# 1. Set up new experiment
python3 scripts/sma_prep.py wizard
# Follow prompts to define targets, barcodes, samples

# 2. Validate setup
python3 scripts/sma_prep.py validate --exp-id exp-001

# 3. Generate all config files
python3 scripts/sma_prep.py init --exp-id exp-001 --output-dir exp-001/

# 4. Run on HPC
cd exp-001
sbatch dorado_job.sbatch

# 5. After completion, ingest into database
python3 scripts/sma_prep.py ingest \
    --exp-id exp-001 \
    --bam-dir results/ \
    --db sma_experiments.db
```
