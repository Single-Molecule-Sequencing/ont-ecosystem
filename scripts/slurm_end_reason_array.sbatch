#!/bin/bash
#SBATCH --job-name=end_reason_analysis
#SBATCH --account=bleu99
#SBATCH --partition=standard
#SBATCH --array=1-72
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=/nfs/turbo/umms-atheylab/logs/end_reason/end_reason_%A_%a.out
#SBATCH --error=/nfs/turbo/umms-atheylab/logs/end_reason/end_reason_%A_%a.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=gregfar@umich.edu

# ============================================
# End Reason Analysis - SLURM Array Job
# Generated: 2025-12-30
# ============================================
#
# This job analyzes 72 experiments for end_reason distribution.
# Each array task processes one experiment.
#
# Usage:
#   sbatch slurm_end_reason_array.sbatch
#
# Monitor:
#   squeue -u $USER
#   sacct -j <jobid>
#
# Results will be in:
#   /nfs/turbo/umms-atheylab/end_reason_results/

set -euo pipefail

echo "======================================"
echo "End Reason Analysis - Task $SLURM_ARRAY_TASK_ID"
echo "======================================"
echo "Job ID: $SLURM_JOB_ID"
echo "Array Task ID: $SLURM_ARRAY_TASK_ID"
echo "Node: $SLURM_NODELIST"
echo "Start Time: $(date)"
echo ""

# Configuration
TURBO_BASE="/nfs/turbo/umms-atheylab"
EXPERIMENT_LIST="$HOME/experiment_list.tsv"
RESULTS_DIR="$TURBO_BASE/end_reason_results"
LOGS_DIR="$TURBO_BASE/logs/end_reason"
SCRIPTS_DIR="$HOME"

# Create directories
mkdir -p "$RESULTS_DIR"
mkdir -p "$LOGS_DIR"

# Get experiment info for this array task
EXPERIMENT_ID=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$EXPERIMENT_LIST" | cut -f1)
POD5_DIR=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$EXPERIMENT_LIST" | cut -f2)

echo "Experiment ID: $EXPERIMENT_ID"
echo "POD5 Directory: $POD5_DIR"
echo ""

# Check if POD5 directory exists
if [ ! -d "$POD5_DIR" ]; then
    echo "ERROR: POD5 directory does not exist: $POD5_DIR"
    exit 1
fi

# Setup conda environment
echo "Setting up conda environment..."
module load python/3.10

# Create/activate virtual environment with required packages
VENV_DIR="$TURBO_BASE/.venvs/end_reason_env"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# Install required packages if not present
pip install --quiet pod5 numpy 2>/dev/null || true

echo "Python: $(which python)"
echo "pod5 version: $(python -c 'import pod5; print(pod5.__version__)' 2>/dev/null || echo 'checking...')"
echo ""

# Output file path
OUTPUT_JSON="$RESULTS_DIR/${EXPERIMENT_ID}_end_reason.json"

# Skip if already processed
if [ -f "$OUTPUT_JSON" ]; then
    echo "Results already exist: $OUTPUT_JSON"
    echo "Checking if valid..."
    if python -c "import json; json.load(open('$OUTPUT_JSON'))" 2>/dev/null; then
        echo "Valid JSON found, skipping analysis."
        exit 0
    else
        echo "Invalid JSON, re-running analysis..."
    fi
fi

# Run analysis
echo "Starting end_reason analysis..."
python3 "$SCRIPTS_DIR/hpc_end_reason_analysis.py" \
    "$POD5_DIR" \
    "$OUTPUT_JSON" \
    --experiment-id "$EXPERIMENT_ID"

# Verify output
if [ -f "$OUTPUT_JSON" ]; then
    echo ""
    echo "Analysis complete!"
    echo "Results saved to: $OUTPUT_JSON"

    # Print summary
    echo ""
    echo "Summary:"
    python3 -c "
import json
with open('$OUTPUT_JSON') as f:
    data = json.load(f)
print(f\"  Status: {data.get('status', 'unknown')}\")
print(f\"  Total reads: {data.get('total_reads', 0):,}\")
pcts = data.get('end_reason_percentages', {})
if pcts:
    print(f\"  signal_positive: {pcts.get('signal_positive', 0):.1f}%\")
    print(f\"  unblock_mux_change: {pcts.get('unblock_mux_change', 0):.1f}%\")
"
else
    echo "ERROR: Output file not created"
    exit 1
fi

echo ""
echo "End Time: $(date)"
echo "======================================"
