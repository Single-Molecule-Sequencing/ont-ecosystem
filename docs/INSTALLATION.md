# ONT Ecosystem Installation Guide

This guide covers installation of the ONT Ecosystem for both private and public repository access.

## Quick Start (Private Repository)

For lab members with SSH access to GitHub:

```bash
# 1. Clone via SSH
git clone git@github.com:Single-Molecule-Sequencing/ont-ecosystem.git

# 2. Run installer
cd ont-ecosystem
./install.sh

# 3. Activate environment
source ~/.ont-ecosystem/env.sh

# 4. Verify
ont_experiments.py --help
```

## Installation Methods

### Method 1: SSH Clone (Recommended for Private Repo)

This method works regardless of whether the repository is public or private.

**Prerequisites:**
- SSH key added to GitHub account
- Git installed

```bash
# Clone repository
git clone git@github.com:Single-Molecule-Sequencing/ont-ecosystem.git
cd ont-ecosystem

# Run installer
./install.sh

# For HPC clusters (Great Lakes, ARMIS2)
./install.sh --hpc

# Activate
source ~/.ont-ecosystem/env.sh
```

### Method 2: HTTPS with Token (Private Repo)

If SSH is not available, use a GitHub Personal Access Token:

```bash
# Clone with token (replace <TOKEN> with your PAT)
git clone https://<TOKEN>@github.com/Single-Molecule-Sequencing/ont-ecosystem.git
cd ont-ecosystem
./install.sh
```

To create a Personal Access Token:
1. Go to GitHub Settings > Developer settings > Personal access tokens
2. Generate new token with `repo` scope
3. Copy the token and use in the clone command

### Method 3: Curl Install (Public Repo Only)

Only works when the repository is public:

```bash
curl -sSL https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/install.sh | bash
source ~/.ont-ecosystem/env.sh
```

If the repo is private, this will fail with a 401 error.

## Configuration

### Initialize Configuration

```bash
# Create default config (auto-detects HPC cluster)
ont_config.py init

# View current config
ont_config.py show
```

### Configuration File

Located at `~/.ont-ecosystem/config.yaml`:

```yaml
version: "1.0.0"
github:
  enabled: false          # Set to true if repo becomes public
  token: null             # Optional: GitHub PAT
  ssh_url: git@github.com:Single-Molecule-Sequencing/ont-ecosystem.git
hpc:
  cluster: greatlakes     # Auto-detected
  gpu_partition: spgpu
  dorado_models: /nfs/turbo/umms-athey/dorado_models
paths:
  ecosystem_home: ~/.ont-ecosystem
  registry_dir: ~/.ont-registry
  manuscript_dir: ~/.ont-manuscript
  textbook_dir: /mnt/d/repos/SMS_textbook
```

### Set Configuration Values

```bash
# Enable GitHub sync (if repo is public)
ont_config.py set github.enabled true

# Set textbook path
ont_config.py set paths.textbook_dir /path/to/SMS_textbook

# Set custom dorado models path
ont_config.py set hpc.dorado_models /custom/path/to/models
```

## HPC Installation

### Great Lakes (University of Michigan)

```bash
# Load required modules
module load python/3.10

# Clone and install
git clone git@github.com:Single-Molecule-Sequencing/ont-ecosystem.git
cd ont-ecosystem
./install.sh --hpc

# Activate
source ~/.ont-ecosystem/env.sh

# Verify HPC detection
ont_config.py show
# Should show: cluster: greatlakes
```

### ARMIS2 (University of Michigan)

```bash
module load python/3.10

git clone git@github.com:Single-Molecule-Sequencing/ont-ecosystem.git
cd ont-ecosystem
./install.sh --hpc

source ~/.ont-ecosystem/env.sh
```

## Updating

### From Cloned Repository

```bash
cd /path/to/ont-ecosystem
git pull
./install.sh
```

### Manual Update

If source repo path is saved:

```bash
# Check source path
cat ~/.ont-ecosystem/config/source.conf

# Pull and reinstall
cd $(grep REPO_SOURCE ~/.ont-ecosystem/config/source.conf | cut -d= -f2)
git pull
./install.sh
```

## Directory Structure

After installation:

```
~/.ont-ecosystem/
├── bin/                    # Executable scripts
│   ├── ont_experiments.py
│   ├── ont_manuscript.py
│   └── ...
├── config/
│   └── source.conf        # Source repo path
├── config.yaml            # User configuration
├── env.sh                 # Environment variables
├── lib/                   # Python libraries
├── registry/              # Textbook/equation registry
└── skills/                # Skill packages

~/.ont-registry/           # Experiment registry
├── experiments.yaml       # Main registry file
├── events/               # Event logs
└── tasks/                # Domain memory tasks

~/.ont-manuscript/         # Manuscript artifacts
├── artifacts/            # Generated figures/tables
└── exports/              # Manuscript exports
```

## Troubleshooting

### SSH Key Issues

```bash
# Test SSH connection
ssh -T git@github.com

# If it fails, add SSH key to agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_rsa
```

### Permission Denied on Scripts

```bash
chmod +x ~/.ont-ecosystem/bin/*.py
```

### Missing Python Dependencies

```bash
pip install pyyaml jsonschema
```

### HPC Module Issues

```bash
# Great Lakes
module load python/3.10 cuda/12.1

# ARMIS2
module load python/3.10 cuda/11.8
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ONT_ECOSYSTEM_HOME` | `~/.ont-ecosystem` | Installation directory |
| `ONT_REGISTRY_DIR` | `~/.ont-registry` | Registry location |
| `ONT_MANUSCRIPT_DIR` | `~/.ont-manuscript` | Manuscript artifacts |
| `ONT_GITHUB_SYNC` | `0` | Enable GitHub sync (1/0) |
| `GITHUB_TOKEN` | - | GitHub PAT for API access |
| `DORADO_MODELS` | HPC-specific | Dorado model cache |
| `ONT_REFERENCES` | HPC-specific | Reference genomes |

## Next Steps

After installation:

1. Initialize the experiment registry:
   ```bash
   ont_experiments.py init --git
   ```

2. Discover experiments:
   ```bash
   ont_experiments.py discover /path/to/data --register
   ```

3. Run QC analysis:
   ```bash
   ont_experiments.py run end_reasons <experiment_id>
   ```

See [TUTORIALS.md](TUTORIALS.md) for detailed workflows.
