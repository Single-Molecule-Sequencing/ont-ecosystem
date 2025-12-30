#!/bin/bash
# Diagnose HPC End Reason Analysis Jobs
# Run this on Great Lakes to identify what went wrong

echo "=============================================="
echo "HPC JOB DIAGNOSIS"
echo "=============================================="
echo ""

RESULTS_DIR="/nfs/turbo/umms-atheylab/end_reason_results"
LOGS_DIR="/nfs/turbo/umms-atheylab/logs/end_reason"
EXPERIMENT_LIST="$HOME/experiment_list.tsv"

# Count results
echo "=== RESULTS SUMMARY ==="
if [ -d "$RESULTS_DIR" ]; then
    TOTAL_JSON=$(ls -1 "$RESULTS_DIR"/*.json 2>/dev/null | wc -l)
    echo "JSON result files: $TOTAL_JSON"
    ls -la "$RESULTS_DIR"/*.json 2>/dev/null | head -5
else
    echo "Results directory not found: $RESULTS_DIR"
fi
echo ""

# Check logs
echo "=== LOG FILES ==="
if [ -d "$LOGS_DIR" ]; then
    TOTAL_OUT=$(ls -1 "$LOGS_DIR"/*.out 2>/dev/null | wc -l)
    TOTAL_ERR=$(ls -1 "$LOGS_DIR"/*.err 2>/dev/null | wc -l)
    echo "Output logs: $TOTAL_OUT"
    echo "Error logs: $TOTAL_ERR"

    # Check for errors in error logs
    echo ""
    echo "=== COMMON ERRORS ==="
    if [ $TOTAL_ERR -gt 0 ]; then
        echo "Scanning error logs..."
        grep -h "Error\|ERROR\|error\|Traceback\|ModuleNotFoundError\|FileNotFoundError\|No such file" "$LOGS_DIR"/*.err 2>/dev/null | sort | uniq -c | sort -rn | head -10
    fi
else
    echo "Logs directory not found: $LOGS_DIR"
fi
echo ""

# Check experiment list
echo "=== EXPERIMENT LIST ==="
if [ -f "$EXPERIMENT_LIST" ]; then
    TOTAL_EXPERIMENTS=$(wc -l < "$EXPERIMENT_LIST")
    echo "Total experiments in list: $TOTAL_EXPERIMENTS"
    echo ""
    echo "First 5 entries:"
    head -5 "$EXPERIMENT_LIST"
    echo ""

    # Check which directories exist
    echo "=== DIRECTORY VERIFICATION (first 10) ==="
    head -10 "$EXPERIMENT_LIST" | while IFS=$'\t' read -r exp_id pod5_dir; do
        if [ -d "$pod5_dir" ]; then
            pod5_count=$(ls -1 "$pod5_dir"/*.pod5 2>/dev/null | wc -l)
            echo "OK: $exp_id - $pod5_count POD5 files"
        else
            echo "MISSING: $exp_id - $pod5_dir"
        fi
    done
else
    echo "Experiment list not found: $EXPERIMENT_LIST"
fi
echo ""

# Check virtual environment
echo "=== PYTHON ENVIRONMENT ==="
VENV_DIR="/nfs/turbo/umms-atheylab/.venvs/end_reason_env"
if [ -d "$VENV_DIR" ]; then
    echo "Virtual env exists: $VENV_DIR"
    source "$VENV_DIR/bin/activate" 2>/dev/null
    echo "Python: $(which python)"
    python -c "import pod5; print(f'pod5 version: {pod5.__version__}')" 2>/dev/null || echo "pod5 NOT installed"
    python -c "import numpy; print(f'numpy version: {numpy.__version__}')" 2>/dev/null || echo "numpy NOT installed"
else
    echo "Virtual env NOT found: $VENV_DIR"
fi
echo ""

# Sample error log content
echo "=== SAMPLE ERROR LOG (most recent) ==="
LATEST_ERR=$(ls -t "$LOGS_DIR"/*.err 2>/dev/null | head -1)
if [ -n "$LATEST_ERR" ]; then
    echo "File: $LATEST_ERR"
    echo "---"
    tail -30 "$LATEST_ERR"
else
    echo "No error logs found"
fi
echo ""

# Sample output log
echo "=== SAMPLE OUTPUT LOG (most recent) ==="
LATEST_OUT=$(ls -t "$LOGS_DIR"/*.out 2>/dev/null | head -1)
if [ -n "$LATEST_OUT" ]; then
    echo "File: $LATEST_OUT"
    echo "---"
    tail -30 "$LATEST_OUT"
else
    echo "No output logs found"
fi
