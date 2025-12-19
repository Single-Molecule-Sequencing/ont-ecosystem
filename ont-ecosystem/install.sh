#!/usr/bin/env bash
#
# ONT Ecosystem Installer
# Automated setup for Oxford Nanopore experiment management
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/install.sh | bash
#   # or
#   ./install.sh [--prefix /custom/path] [--no-deps] [--hpc]
#
set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

VERSION="2.1.0"
REPO_URL="https://github.com/Single-Molecule-Sequencing/ont-ecosystem"
DEFAULT_PREFIX="${HOME}/.ont-ecosystem"
REGISTRY_DIR="${HOME}/.ont-registry"
REFS_DIR="${HOME}/.ont-references"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        log_success "$1 found: $(command -v $1)"
        return 0
    else
        log_warn "$1 not found"
        return 1
    fi
}

detect_platform() {
    if [[ -n "${SLURM_JOB_ID:-}" ]]; then
        echo "slurm"
    elif [[ -n "${PBS_JOBID:-}" ]]; then
        echo "pbs"
    elif [[ -f /etc/os-release ]]; then
        source /etc/os-release
        echo "${ID:-linux}"
    elif [[ "$(uname)" == "Darwin" ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

detect_hpc_system() {
    # Detect specific HPC environments
    if [[ -d "/nfs/turbo/umms-athey" ]] || [[ -d "/nfs/turbo/athey-lab" ]]; then
        echo "umich-greatlakes"
    elif [[ -d "/scratch" ]] && [[ -f "/etc/slurm/slurm.conf" ]]; then
        echo "generic-slurm"
    else
        echo "local"
    fi
}

install_python_deps() {
    local pip_cmd="pip3"
    local pip_args=""
    
    # Check if we're in a virtual environment
    if [[ -z "${VIRTUAL_ENV:-}" ]]; then
        pip_args="--user"
        # On some systems, need --break-system-packages
        if $pip_cmd install --help 2>&1 | grep -q "break-system-packages"; then
            pip_args="$pip_args --break-system-packages"
        fi
    fi
    
    log_info "Installing Python dependencies..."
    
    $pip_cmd install $pip_args \
        pyyaml>=6.0 \
        numpy>=1.20 \
        pandas>=1.3 \
        matplotlib>=3.5 \
        || log_warn "Some Python packages failed to install"
    
    # Optional but recommended
    $pip_cmd install $pip_args \
        pysam>=0.19.0 \
        pod5>=0.3.0 \
        h5py>=3.0.0 \
        flask>=2.0 \
        2>/dev/null || log_warn "Optional packages not installed (pysam, pod5, h5py, flask)"
    
    log_success "Python dependencies installed"
}

setup_directories() {
    log_info "Creating directories..."
    
    mkdir -p "${PREFIX}/bin"
    mkdir -p "${PREFIX}/lib"
    mkdir -p "${PREFIX}/config"
    mkdir -p "${PREFIX}/share/ont-ecosystem"
    mkdir -p "${REGISTRY_DIR}"
    mkdir -p "${REFS_DIR}"
    
    log_success "Directories created"
}

install_scripts() {
    log_info "Installing scripts..."
    
    # Copy main scripts
    for script in ont_experiments.py ont_monitor.py ont_align.py end_reason.py dorado_basecall.py; do
        if [[ -f "${SCRIPT_DIR}/bin/${script}" ]]; then
            cp "${SCRIPT_DIR}/bin/${script}" "${PREFIX}/bin/"
            chmod +x "${PREFIX}/bin/${script}"
        fi
    done
    
    # Copy library modules
    if [[ -d "${SCRIPT_DIR}/lib" ]]; then
        cp -r "${SCRIPT_DIR}/lib/"* "${PREFIX}/lib/" 2>/dev/null || true
    fi
    
    # Copy config templates
    if [[ -d "${SCRIPT_DIR}/config" ]]; then
        cp -r "${SCRIPT_DIR}/config/"* "${PREFIX}/config/" 2>/dev/null || true
    fi
    
    log_success "Scripts installed to ${PREFIX}/bin"
}

configure_shell() {
    log_info "Configuring shell environment..."
    
    local shell_rc=""
    local shell_name=$(basename "$SHELL")
    
    case "$shell_name" in
        bash)
            shell_rc="${HOME}/.bashrc"
            ;;
        zsh)
            shell_rc="${HOME}/.zshrc"
            ;;
        *)
            shell_rc="${HOME}/.profile"
            ;;
    esac
    
    # Create the environment setup file
    cat > "${PREFIX}/env.sh" << EOF
# ONT Ecosystem Environment
# Source this file or add to your shell rc file

export ONT_ECOSYSTEM_HOME="${PREFIX}"
export ONT_REGISTRY_DIR="${REGISTRY_DIR}"
export ONT_REFERENCES_DIR="${REFS_DIR}"
export ONT_SKILL_PATH="${PREFIX}/bin"

# Add to PATH if not already there
if [[ ":\$PATH:" != *":\${ONT_ECOSYSTEM_HOME}/bin:"* ]]; then
    export PATH="\${ONT_ECOSYSTEM_HOME}/bin:\$PATH"
fi

# Add lib to PYTHONPATH
if [[ ":\$PYTHONPATH:" != *":\${ONT_ECOSYSTEM_HOME}/lib:"* ]]; then
    export PYTHONPATH="\${ONT_ECOSYSTEM_HOME}/lib:\${PYTHONPATH:-}"
fi

# Aliases for convenience
alias ont='ont_experiments.py'
alias ont-list='ont_experiments.py list'
alias ont-discover='ont_experiments.py discover'
alias ont-history='ont_experiments.py history'
alias ont-public='ont_experiments.py public'
EOF

    # Add source line to shell rc if not present
    local source_line="source \"${PREFIX}/env.sh\""
    if ! grep -qF "${PREFIX}/env.sh" "$shell_rc" 2>/dev/null; then
        echo "" >> "$shell_rc"
        echo "# ONT Ecosystem" >> "$shell_rc"
        echo "$source_line" >> "$shell_rc"
        log_success "Added to $shell_rc"
    else
        log_info "Shell configuration already present in $shell_rc"
    fi
}

initialize_registries() {
    log_info "Initializing registries..."
    
    # Initialize experiment registry
    if [[ ! -f "${REGISTRY_DIR}/experiments.yaml" ]]; then
        cat > "${REGISTRY_DIR}/experiments.yaml" << EOF
# ONT Experiment Registry
# Created: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Version: ${VERSION}

version: "2.0"
updated: "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
experiments: []
EOF
        log_success "Experiment registry initialized"
    fi
    
    # Initialize reference registry
    if [[ ! -f "${REFS_DIR}/references.yaml" ]]; then
        cat > "${REFS_DIR}/references.yaml" << EOF
# ONT Reference Genome Registry
# Created: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

version: "1.0"
references: {}
EOF
        log_success "Reference registry initialized"
    fi
    
    # Initialize git for registry (optional)
    if command -v git &> /dev/null && [[ ! -d "${REGISTRY_DIR}/.git" ]]; then
        (cd "${REGISTRY_DIR}" && git init -q && git add -A && git commit -q -m "Initial registry")
        log_success "Git initialized for registry"
    fi
}

configure_hpc() {
    local hpc_system="$1"
    
    log_info "Configuring for HPC: ${hpc_system}"
    
    case "$hpc_system" in
        umich-greatlakes)
            cat > "${PREFIX}/config/hpc.yaml" << EOF
# University of Michigan Great Lakes / ARMIS2 Configuration
hpc:
  system: greatlakes
  scheduler: slurm
  
  partitions:
    gpu:
      - standard
      - gpu
      - spgpu
      - sigbio-a40
    cpu:
      - standard
      - largemem
      
  default_partition: standard
  default_gpu_partition: gpu
  
  storage:
    turbo:
      - /nfs/turbo/umms-athey
      - /nfs/turbo/athey-lab
    scratch: /scratch
    
  modules:
    dorado: "dorado/0.5.0"
    minimap2: "minimap2/2.26"
    samtools: "samtools/1.17"
    python: "python/3.10"
    
  reference_paths:
    - /nfs/turbo/umms-athey/references
    - /nfs/turbo/athey-lab/references
    
  model_paths:
    - /nfs/turbo/umms-athey/dorado_models
    - /nfs/turbo/athey-lab/models
EOF
            log_success "Great Lakes configuration created"
            ;;
        *)
            cat > "${PREFIX}/config/hpc.yaml" << EOF
# Generic HPC Configuration
hpc:
  system: generic
  scheduler: ${SLURM_JOB_ID:+slurm}${PBS_JOBID:+pbs}
  
  partitions:
    gpu: []
    cpu: []
    
  default_partition: ""
  
  storage:
    scratch: /scratch
    
  modules: {}
  reference_paths: []
  model_paths: []
EOF
            log_info "Generic HPC configuration created - customize ${PREFIX}/config/hpc.yaml"
            ;;
    esac
}

setup_public_datasets() {
    log_info "Setting up public dataset catalog..."
    
    cat > "${PREFIX}/config/public_datasets.yaml" << 'EOF'
# ONT Open Data Catalog
# Last updated: 2024-01-15
# Source: https://labs.epi2me.io/dataindex/

version: "1.0"
base_url: "s3://ont-open-data"
browser_url: "https://42basepairs.com/browse/s3/ont-open-data"

categories:
  human_reference:
    name: "Human Reference"
    datasets:
      gm24385_2023.12:
        name: "GM24385 R10.4.1 Latest"
        description: "Human reference GM24385, R10.4.1 chemistry, POD5 format"
        s3_path: "gm24385_2023.12/"
        size: "~300GB"
        chemistry: "R10.4.1"
        featured: true
        
      lc2024_t2t:
        name: "T2T Consortium Data"
        description: "Telomere-to-Telomere consortium sequencing data"
        s3_path: "lc2024_t2t/"
        size: "~200GB"
        
  giab:
    name: "GIAB Benchmarks"
    datasets:
      giab_2025.01:
        name: "GIAB Latest"
        description: "Latest GIAB reference materials"
        s3_path: "giab_2025.01/"
        size: "~400GB"
        featured: true
        
      giab_2023.05:
        name: "GIAB May 2023"
        description: "HG002/HG003/HG004 samples"
        s3_path: "giab_2023.05/"
        size: "~400GB"
        
  clinical:
    name: "Cancer/Clinical"
    datasets:
      hereditary_cancer_2025.09:
        name: "Hereditary Cancer Panel"
        description: "Cancer panel sequencing data"
        s3_path: "hereditary_cancer_2025.09/"
        size: "~100GB"
        featured: true
        
      colo829_2024.03:
        name: "COLO829 Melanoma"
        description: "Melanoma cell line reference"
        s3_path: "colo829_2024.03/"
        size: "~150GB"
        
  microbial:
    name: "Microbial"
    datasets:
      zymo_d6331_2024.04:
        name: "ZymoBIOMICS D6331"
        description: "Microbial community standard"
        s3_path: "zymo_d6331_2024.04/"
        size: "~50GB"
        
      zymo_16s_2025.09:
        name: "Zymo 16S Mock"
        description: "16S rRNA mock community"
        s3_path: "zymo_16s_2025.09/"
        size: "~20GB"

  rna:
    name: "RNA/cDNA"
    datasets:
      rna_sirv_2023.11:
        name: "SIRV RNA Controls"
        description: "Spike-in RNA variant controls"
        s3_path: "rna_sirv_2023.11/"
        size: "~10GB"
EOF
    
    log_success "Public dataset catalog created"
}

print_summary() {
    echo ""
    echo "============================================================"
    echo -e "${GREEN}ONT Ecosystem ${VERSION} Installation Complete${NC}"
    echo "============================================================"
    echo ""
    echo "Installation directory: ${PREFIX}"
    echo "Registry directory:     ${REGISTRY_DIR}"
    echo "References directory:   ${REFS_DIR}"
    echo ""
    echo "To activate, run:"
    echo -e "  ${BLUE}source ${PREFIX}/env.sh${NC}"
    echo ""
    echo "Or start a new shell session."
    echo ""
    echo "Quick start:"
    echo "  ont_experiments.py init              # Initialize registry"
    echo "  ont_experiments.py discover /path    # Find experiments"
    echo "  ont_experiments.py list              # List experiments"
    echo "  ont_experiments.py public            # Browse public data"
    echo ""
    echo "Dashboard (if Flask installed):"
    echo "  ont_dashboard.py                     # Start web UI"
    echo ""
    echo "Documentation: ${REPO_URL}"
    echo "============================================================"
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo ""
    echo "============================================================"
    echo "ONT Ecosystem Installer v${VERSION}"
    echo "============================================================"
    echo ""
    
    # Parse arguments
    PREFIX="${DEFAULT_PREFIX}"
    INSTALL_DEPS=true
    HPC_MODE=false
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --prefix)
                PREFIX="$2"
                shift 2
                ;;
            --no-deps)
                INSTALL_DEPS=false
                shift
                ;;
            --hpc)
                HPC_MODE=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [options]"
                echo ""
                echo "Options:"
                echo "  --prefix PATH   Install to PATH (default: ~/.ont-ecosystem)"
                echo "  --no-deps       Skip Python dependency installation"
                echo "  --hpc           Configure for HPC environment"
                echo "  --help          Show this help"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Detect where we're running from
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Detect platform
    PLATFORM=$(detect_platform)
    HPC_SYSTEM=$(detect_hpc_system)
    
    log_info "Platform: ${PLATFORM}"
    log_info "HPC System: ${HPC_SYSTEM}"
    log_info "Install prefix: ${PREFIX}"
    echo ""
    
    # Check prerequisites
    log_info "Checking prerequisites..."
    check_command python3 || { log_error "Python 3 is required"; exit 1; }
    check_command pip3 || check_command pip || { log_error "pip is required"; exit 1; }
    check_command git || log_warn "git not found - registry versioning disabled"
    echo ""
    
    # Check for external tools
    log_info "Checking optional tools..."
    check_command minimap2 || log_warn "minimap2 not found - alignment disabled"
    check_command samtools || log_warn "samtools not found - BAM processing disabled"
    check_command dorado || log_warn "dorado not found - basecalling disabled"
    echo ""
    
    # Install
    setup_directories
    
    if [[ "${INSTALL_DEPS}" == "true" ]]; then
        install_python_deps
    fi
    
    install_scripts
    configure_shell
    initialize_registries
    setup_public_datasets
    
    # HPC configuration
    if [[ "${HPC_MODE}" == "true" ]] || [[ "${HPC_SYSTEM}" != "local" ]]; then
        configure_hpc "${HPC_SYSTEM}"
    fi
    
    print_summary
}

main "$@"
