# Environment Variables

This document describes all environment variables used by the ONT Ecosystem.

## Core Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ONT_ECOSYSTEM_HOME` | `~/.ont-ecosystem` | Installation directory |
| `ONT_REGISTRY_DIR` | `~/.ont-registry` | Experiment registry location |
| `ONT_REFERENCES_DIR` | `~/.ont-references` | Reference genome storage |

## Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `ONT_LOG_TO_FILE` | unset | If set, enables daily log files in `~/.ont-ecosystem/logs/` |
| `ONT_LOG_LEVEL` | `WARNING` | Default log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

## HPC / Cluster

| Variable | Default | Description |
|----------|---------|-------------|
| `DORADO_MODELS` | unset | Path to Dorado model cache |
| `ONT_REFERENCES` | unset | Path to reference genomes on HPC |
| `SLURM_JOB_ID` | unset | Auto-captured for provenance tracking |
| `SLURM_JOB_PARTITION` | unset | Auto-captured for provenance tracking |

## Analysis

| Variable | Default | Description |
|----------|---------|-------------|
| `ONT_THREADS` | CPU count | Default thread count for parallel operations |
| `ONT_MEMORY_LIMIT` | unset | Memory limit for operations (e.g., `32G`) |

## Development

| Variable | Default | Description |
|----------|---------|-------------|
| `ONT_DEV_MODE` | unset | If set, enables development features |
| `ONT_SKIP_VALIDATION` | unset | Skip schema validation (not recommended) |

## Setting Variables

### Temporary (current session)

```bash
export ONT_LOG_TO_FILE=1
export ONT_THREADS=8
```

### Permanent (add to shell profile)

```bash
# In ~/.bashrc or ~/.zshrc
export ONT_ECOSYSTEM_HOME="$HOME/.ont-ecosystem"
export ONT_LOG_TO_FILE=1
source "$ONT_ECOSYSTEM_HOME/env.sh"
```

### HPC Module Files

For HPC environments, create a module file:

```tcl
# /path/to/modulefiles/ont-ecosystem/3.0.0
#%Module1.0
proc ModulesHelp { } {
    puts stderr "ONT Ecosystem v3.0.0"
}
module-whatis "ONT Ecosystem for nanopore analysis"

set basedir /path/to/ont-ecosystem
setenv ONT_ECOSYSTEM_HOME $basedir
prepend-path PATH $basedir/bin
prepend-path PYTHONPATH $basedir
```

## Checking Configuration

```bash
# Show current environment
env | grep ONT

# Run health check
ont_check.py

# Show ecosystem stats
ont_stats.py --brief
```
