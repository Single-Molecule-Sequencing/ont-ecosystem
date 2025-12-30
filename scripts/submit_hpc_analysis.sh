#!/bin/bash
HPC_DEST="gregfar@greatlakes.arc-ts.umich.edu"
SCRIPT_DIR="/home/farnum248/repos/ont-ecosystem/scripts"

echo "Copying files to Great Lakes..."

scp /tmp/experiment_list.tsv \
    ${SCRIPT_DIR}/hpc_end_reason_analysis.py \
    ${SCRIPT_DIR}/slurm_end_reason_array.sbatch \
    ${SCRIPT_DIR}/collect_end_reason_results.py \
    ${HPC_DEST}:~/

echo ""
echo "Done! Now SSH and submit:"
echo "  ssh ${HPC_DEST}"
echo "  mkdir -p /nfs/turbo/umms-atheylab/logs/end_reason && sbatch ~/slurm_end_reason_array.sbatch"
