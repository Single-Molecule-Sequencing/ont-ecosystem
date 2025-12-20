# ONT Ecosystem

[![CI](https://github.com/Single-Molecule-Sequencing/ont-ecosystem/actions/workflows/ci.yml/badge.svg)](https://github.com/Single-Molecule-Sequencing/ont-ecosystem/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive toolkit for Oxford Nanopore sequencing experiment management with **full provenance tracking**, **event-sourced registry**, and **integrated analysis workflows**.

> Part of the [Single-Molecule-Sequencing](https://github.com/Single-Molecule-Sequencing) toolkit suite.

## Related Repositories

This ecosystem integrates with other tools in the [Single-Molecule-Sequencing](https://github.com/Single-Molecule-Sequencing) organization:

| Repository | Description | Integration |
|------------|-------------|-------------|
| [dorado-bench](https://github.com/Single-Molecule-Sequencing/dorado-bench) | Dorado model benchmarking | Basecalling skill |
| [dorado-run](https://github.com/Single-Molecule-Sequencing/dorado-run) | Dorado execution tool | Basecalling backend |
| [End_Reason_nf](https://github.com/Single-Molecule-Sequencing/End_Reason_nf) | End reason Nextflow | QC analysis |
| [PGx-prep](https://github.com/Single-Molecule-Sequencing/PGx-prep) | PGx BAM preprocessing | Sample prep workflows |
| [ONT-SMA-seq](https://github.com/Single-Molecule-Sequencing/ONT-SMA-seq) | SMA-seq workflow | Analysis pipeline |

## Features

- ðŸ”¬ **Experiment Discovery**: Automatically find and catalog ONT sequencing runs
- ðŸ“Š **Provenance Tracking**: Event-sourced history of all analyses with full reproducibility
- ðŸ–¥ï¸ **HPC Integration**: Native SLURM/PBS support with GPU-aware job generation
- ðŸŒ **Public Data Access**: Curated catalog of 30+ ONT Open Data datasets
- ðŸ“ˆ **Web Dashboard**: Browser-based visualization and management
- ðŸ”„ **Pattern B Orchestration**: Centralized analysis workflow management

## Architecture

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                     ont-experiments (CORE)                       â”‚
â”‚  â€¢ Event-sourced registry (~/.ont-registry/)                     â”‚
â”‚  â€¢ Experiment discovery & metadata extraction                    â”‚
â”‚  â€¢ Pattern B orchestration (wraps analysis skills)               â”‚
â”‚  â€¢ Public dataset access (30+ datasets)                          â”‚
â”‚  â€¢ HPC/SLURM metadata capture                                    â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                              â”‚
    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
    â–¼             â–¼           â–¼           â–¼             â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚end-reasonâ”‚ â”‚dorado-  â”‚ â”‚ont-alignâ”‚ â”‚ont-     â”‚ â”‚ future  â”‚
â”‚(QC)     â”‚ â”‚bench    â”‚ â”‚(align)  â”‚ â”‚monitor  â”‚ â”‚(variant)â”‚
â”‚         â”‚ â”‚(basecall)â”‚ â”‚         â”‚ â”‚         â”‚ â”‚         â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Quick Install

```bash
# One-line install
curl -sSL https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/install.sh | bash

# Or clone and install
git clone https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git
cd ont-ecosystem
./install.sh
```

### HPC Installation (Great Lakes / ARMIS2)

```bash
# Load modules first
module load python/3.10

# Install with HPC configuration
./install.sh --hpc

# The installer auto-detects Great Lakes and configures paths
```

## Quick Start

```bash
# Initialize the registry
ont_experiments.py init --git

# Discover experiments in a directory
ont_experiments.py discover /path/to/sequencing/runs --register

# List all experiments
ont_experiments.py list

# View experiment details
ont_experiments.py info exp-abc123

# Run QC analysis (with automatic provenance tracking)
ont_experiments.py run end_reasons exp-abc123 --json qc.json

# Run alignment
ont_experiments.py run alignment exp-abc123 --ref hg38 --output aligned.bam

# Monitor active sequencing run
ont_experiments.py run monitoring exp-abc123 --live

# View full history
ont_experiments.py history exp-abc123

# Start web dashboard
ont_dashboard.py
```

## Analysis Skills

| Skill | Description | Key Features |
|-------|-------------|--------------|
| **end-reason** | Read end reason QC | Adaptive sampling analysis, quality thresholds |
| **dorado-bench** | Basecalling | Model management, SLURM job generation |
| **ont-align** | Alignment | minimap2/dorado, reference registry, coverage |
| **ont-monitor** | Run monitoring | Live dashboard, time-series, alerts |

### Running Analyses

All analyses are run through the central `ont_experiments.py run` command, which provides:
- Automatic provenance tracking
- HPC metadata capture
- Output file checksums
- Results summary in registry

```bash
# QC Analysis
ont_experiments.py run end_reasons exp-abc123 \
    --json results.json \
    --plot qc.png

# Basecalling on HPC
sbatch --partition=gpu --gres=gpu:1 --wrap="\
    ont_experiments.py run basecalling exp-abc123 \
        --model sup@v5.0.0 \
        --output /scratch/basecalled.bam"

# Alignment with coverage
ont_experiments.py run alignment exp-abc123 \
    --ref hs1 \
    --output aligned.bam \
    --coverage coverage.bed \
    --json alignment_stats.json
```

## Web Dashboard

Start the web interface for visual experiment management:

```bash
ont_dashboard.py --port 8080
```

Features:
- Experiment browser with search and filtering
- Detailed event history timeline
- Statistics and visualizations
- REST API for programmatic access

## Public Datasets

Access curated ONT Open Data:

```bash
# List available datasets
ont_experiments.py public

# Get browser URL for a dataset
ont_experiments.py public giab_2025.01 --url

# Download with automatic registration
ont_experiments.py fetch giab_2025.01 /data/public --register
```

### Available Categories

- **Human Reference**: GM24385, T2T consortium data
- **GIAB Benchmarks**: HG002, HG003, HG004 samples
- **Cancer/Clinical**: COLO829, hereditary cancer panels
- **Microbial**: ZymoBIOMICS, 16S mock communities
- **RNA/cDNA**: SIRV controls, direct RNA

## Registry Structure

```
~/.ont-registry/
â”œâ”€â”€ experiments.yaml     # Main registry (git-tracked)
â””â”€â”€ .git/                # Version history

~/.ont-references/
â””â”€â”€ references.yaml      # Reference genome registry
```

### Event Schema

Every action is recorded with full provenance:

```yaml
events:
  - timestamp: "2024-01-15T12:00:00Z"
    type: "analysis"
    analysis: "basecalling"
    command: "dorado basecaller sup /path/to/pod5"
    parameters:
      model: "dna_r10.4.1_e8.2_400bps_sup@v4.3.0"
    outputs:
      - path: "/path/to/calls.bam"
        checksum: "sha256:abc123..."
    results:
      total_reads: 15000000
      mean_qscore: 18.5
    duration_seconds: 3600
    exit_code: 0
    agent: "claude-code"
    hpc:
      scheduler: "slurm"
      job_id: "12345678"
      gpus: ["NVIDIA A100"]
```

## API

### REST Endpoints

```
GET /api/experiments           # List all experiments
GET /api/experiments/{id}      # Get experiment details
GET /api/experiments/search?q= # Search experiments
GET /api/experiments/export    # Export as CSV/JSON
GET /api/stats                 # Registry statistics
GET /api/public                # Public datasets catalog
```

### Python API

```python
from ont_core import Registry, Experiment

registry = Registry()

# List experiments
for exp in registry.list(tags=['cyp2d6']):
    print(f"{exp.id}: {exp.name}")

# Get experiment
exp = registry.get('exp-abc123')
print(exp.successful_analyses)

# Get statistics
stats = registry.get_stats()
print(f"Total: {stats['total_experiments']} experiments")
```

## Configuration

### Environment Variables

```bash
export ONT_ECOSYSTEM_HOME=~/.ont-ecosystem
export ONT_REGISTRY_DIR=~/.ont-registry
export ONT_REFERENCES_DIR=~/.ont-references
export ONT_SKILL_PATH=~/.ont-ecosystem/bin
```

### HPC Configuration

Edit `~/.ont-ecosystem/config/hpc.yaml`:

```yaml
hpc:
  system: greatlakes
  scheduler: slurm
  
  partitions:
    gpu: [standard, gpu, spgpu, sigbio-a40]
    cpu: [standard, largemem]
  
  reference_paths:
    - /nfs/turbo/umms-athey/references
    
  model_paths:
    - /nfs/turbo/umms-athey/dorado_models
```

## Dependencies

**Required:**
- Python 3.9+
- pyyaml

**Recommended:**
- numpy, pandas, matplotlib (for analysis)
- pysam (for BAM handling)
- pod5 (for POD5 files)
- flask (for web dashboard)

**External Tools:**
- minimap2 (alignment)
- samtools (BAM processing)
- dorado (basecalling)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Citation

If you use this software in your research, please cite:

```
ONT Ecosystem: Oxford Nanopore Experiment Management Toolkit
Single Molecule Sequencing Lab, Athey Lab, University of Michigan
https://github.com/Single-Molecule-Sequencing/ont-ecosystem
```

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/Single-Molecule-Sequencing/ont-ecosystem/issues)
- **Lab Website**: [Single Molecule Sequencing Lab, Athey Lab](https://github.com/Single-Molecule-Sequencing/)

---

## Combined Read Length + End Reason Analysis

The `ont_readlen_endreason.py` tool combines read length distribution analysis with end reason classification for comprehensive ONT QC.

### Quick Example

```bash
# Single experiment - semi-transparent distributions by end reason
python3 ont_readlen_endreason.py /path/to/run --plot-by-endreason dist.png

# Multi-experiment comparison 
python3 ont_readlen_endreason.py exp1/ exp2/ exp3/ --plot-summary summary.png

# Detailed 4-panel analysis
python3 ont_readlen_endreason.py /path/to/run --plot-detailed detailed.png
```

### Key Visualizations

1. **Semi-transparent overlay plot**: Read length histograms colored by end reason class
2. **Cross-experiment summary**: 4-panel comparison of end reason vs read length metrics
3. **Detailed 4-panel**: Linear/log distributions, pie chart, N50 by class

### Interpretation

| End Reason | Description | Expected % |
|------------|-------------|------------|
| signal_positive | Normal completion | 80-95% |
| unblock_mux_change | Adaptive sampling rejection | 0-15% |
| data_service_unblock | Basecall-triggered rejection | 0-10% |
| mux_change | Pore mux change | 1-5% |
| signal_negative | Signal lost | <5% |

See `ont_readlen_endreason_SKILL.md` for detailed documentation.
