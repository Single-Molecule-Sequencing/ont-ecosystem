---
name: ont-metadata
description: Extract metadata from Oxford Nanopore POD5 and Fast5 raw data files. Use when discovering experiments without summary files, parsing raw sequencing data metadata, detecting Fast5 file types (single/multi/bulk), or extracting run information from raw data. Supports pod5 library and ont_fast5_api for efficient parsing.
version: 1.0.0
author: Single Molecule Sequencing Lab
category: data-management
tags:
  - nanopore
  - pod5
  - fast5
  - metadata
  - discovery
---

# ONT Metadata Parser

Extract run-level metadata from Oxford Nanopore POD5 and Fast5 raw data files without requiring `final_summary.txt` files.

## When to Use

Use this skill when you need to:
- Extract metadata from experiments that only have raw data (no summary files)
- Parse POD5 files for run information (flow_cell_id, sample_id, protocol, etc.)
- Parse Fast5 files and detect file type (single-read, multi-read, bulk)
- Discover experiment directories by scanning for raw data files
- Get sequencing kit, basecall model, and protocol information from raw files

## Quick Start

```bash
# Parse a single POD5 file
/ont-metadata /path/to/file.pod5

# Parse an experiment directory
/ont-metadata /path/to/experiment --verbose

# Find all experiment directories in a path
/ont-metadata /path/to/data --find-experiments

# Output metadata as JSON
/ont-metadata /path/to/experiment --json metadata.json
```

## Metadata Extracted

### From POD5 Files
| Field | Description |
|-------|-------------|
| `flow_cell_id` | Flow cell identifier (e.g., FBD19495) |
| `sample_id` | Sample name |
| `acquisition_id` | Unique acquisition identifier |
| `protocol` | Full protocol string |
| `instrument` | Device hostname |
| `started` | Acquisition start time |
| `sequencing_kit` | Kit identifier (e.g., sqk-lsk114) |
| `experiment_name` | Experiment name |
| `protocol_group_id` | Protocol group |
| `context_tags` | Dict with basecall_model, experiment_type, etc. |
| `tracking_id` | Dict with device_id, run_id, guppy_version, etc. |

### From Fast5 Files
| Field | Description |
|-------|-------------|
| `fast5_format` | File type: single-read, multi-read, or bulk |
| `read_count` | Number of reads in file |
| `flow_cell_id` | Flow cell identifier |
| `sample_id` | Sample name |
| `run_id` | Run identifier |
| `device_id` | Device serial number |
| `exp_start_time` | Experiment start time |
| `tracking_id` | Full tracking metadata dict |
| `context_tags` | Experiment context dict |

## Fast5 File Types

| Type | Description |
|------|-------------|
| `single-read` | One read per file (legacy, deprecated) |
| `multi-read` | Multiple reads per file (4000 typical, current standard) |
| `bulk` | Raw channel data stream (special use case) |

## Options

| Option | Description |
|--------|-------------|
| `--format FORMAT` | Force format: pod5, fast5, or auto (default: auto) |
| `--json FILE` | Output metadata to JSON file |
| `--find-experiments` | Find all experiment directories in path |
| `--verbose, -v` | Show full metadata including tracking_id and context_tags |

## Example Output

```
Extracting metadata from: /data1/experiment/pod5/file.pod5
POD5 library: available
ont_fast5_api: available
h5py library: available

Extracted Metadata:
--------------------------------------------------
  flow_cell_id: FBD19495
  sample_id: sample_name
  acquisition_id: 905f220998358f97395fc01019bff9961aeafb0c
  protocol: sequencing/sequencing_MIN114_DNA_e8_2_400K:FLO-MIN114:SQK-LSK114:400
  instrument: rdlu0053
  started: 2025-07-14T04:54:43.011000+00:00
  sequencing_kit: sqk-lsk114
  experiment_name: WGS_LSK_human
  protocol_group_id: WGS_LSK_human
  pod5_count: 56
```

## Integration with Discovery

This skill powers the experiment discovery in `experiment-db` skill:

```bash
# Discovery finds experiments with OR without summary files
python3 greatlakes_discovery.py scan-local --include-raw-only \
    --output manifest.json /path/to/data

# Manifest shows metadata source
{
  "metadata_source": "pod5_raw",  # or "final_summary" or "fast5_raw"
  "summary_file": null,
  "flow_cell_id": "FBD19495",
  ...
}
```

## Dependencies

- **Required**: Python >= 3.8
- **For POD5**: `pip install pod5`
- **For Fast5**: `pip install ont-fast5-api` (preferred) or `pip install h5py` (fallback)

Install all:
```bash
pip install pod5 ont-fast5-api
```

## Library Priority

1. **POD5 files**: Uses `pod5` library
2. **Fast5 files**: Uses `ont_fast5_api` (preferred) → falls back to `h5py`

## References

- [POD5 File Format](https://github.com/nanoporetech/pod5-file-format)
- [ont_fast5_api](https://github.com/nanoporetech/ont_fast5_api)
- [POD5 Documentation](https://pod5-file-format.readthedocs.io/)
