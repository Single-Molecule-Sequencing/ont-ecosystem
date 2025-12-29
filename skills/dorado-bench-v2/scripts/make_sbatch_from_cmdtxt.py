#!/usr/bin/env python3
"""
Generate SLURM batch files from dorado command text files

Usage:
    python3 make_sbatch_from_cmdtxt.py -i dorado_basecaller_sup_cmd.txt -o Sbatch/sup --account bleu1
"""

import argparse
from pathlib import Path


SLURM_TEMPLATE = """#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --account={account}
#SBATCH --partition={partition}
#SBATCH --gres={gres}
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task={cpus}
#SBATCH --mem={memory}
#SBATCH --time={time}
#SBATCH --output=Logs/%x_%j.out
#SBATCH --error=Logs/%x_%j.err
{mail_directives}

# Job information
echo "======================================"
echo "SLURM Job Information"
echo "======================================"
echo "Job ID: $SLURM_JOB_ID"
echo "Job Name: $SLURM_JOB_NAME"
echo "Node: $SLURM_NODELIST"
echo "Start Time: $(date)"
echo "Working Directory: $(pwd)"
echo ""

# Set error handling
set -euo pipefail

# GPU information
if command -v nvidia-smi &> /dev/null; then
    echo "GPU Information:"
    nvidia-smi
    echo ""
fi

# Create log file
LOG_FILE="Logs/dorado_${{SLURM_JOB_ID}}.log"

# Function to log messages
log_message() {{
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${{LOG_FILE}}"
}}

# Start basecalling
log_message "Starting basecalling"
log_message "Command: {command}"

# Execute command
{command} 2>&1 | tee -a "${{LOG_FILE}}"

# Check exit status
if [ ${{PIPESTATUS[0]}} -eq 0 ]; then
    log_message "✅ Basecalling completed successfully"
    
    # Generate BAM statistics if output is BAM
    OUTPUT_FILE=$(echo "{command}" | grep -oP '> \\K[^ ]+')
    if [[ "$OUTPUT_FILE" == *.bam ]]; then
        if command -v samtools &> /dev/null; then
            log_message "Generating BAM statistics..."
            samtools index "$OUTPUT_FILE"
            samtools flagstat "$OUTPUT_FILE" > "${{OUTPUT_FILE%.bam}}_flagstat.txt"
            samtools stats "$OUTPUT_FILE" > "${{OUTPUT_FILE%.bam}}_stats.txt"
            log_message "Statistics generated"
        fi
    fi
else
    log_message "❌ Basecalling failed with exit code ${{PIPESTATUS[0]}}"
    exit 1
fi

# Job summary
echo ""
echo "======================================"
echo "Job Summary"
echo "======================================"
echo "End Time: $(date)"
echo "Total Runtime: $SECONDS seconds"
echo "Exit Status: $?"
echo "Log File: ${{LOG_FILE}}"
"""


def parse_job_name_from_command(command):
    """Extract a job name from the dorado command"""
    # Try to extract sample ID and model info from command
    parts = command.split()
    
    # Find model name
    model = 'unknown'
    for part in parts:
        if 'dna_r10' in part:
            model = part.split('/')[-1]
            break
    
    # Find input directory to extract sample
    sample = 'unknown'
    for i, part in enumerate(parts):
        if 'AGC_data' in part or 'pod5' in part:
            path_parts = part.split('/')
            if len(path_parts) >= 2:
                sample = path_parts[-3] if len(path_parts) >= 3 else path_parts[-2]
            break
    
    # Build job name
    job_name = f"dorado_{sample}_{model}"
    # Truncate if too long
    if len(job_name) > 40:
        job_name = job_name[:40]
    
    return job_name


def create_sbatch_file(command, output_path, args):
    """Create a SLURM batch file for a single command"""
    
    # Parse job name from command
    job_name = parse_job_name_from_command(command)
    
    # Build mail directives
    mail_directives = ""
    if args.email:
        mail_directives = f"#SBATCH --mail-user={args.email}\n"
        mail_directives += f"#SBATCH --mail-type={args.mail_type}"
    
    # Fill template
    script = SLURM_TEMPLATE.format(
        job_name=job_name,
        account=args.account,
        partition=args.partition,
        gres=args.gres,
        cpus=args.cpus,
        memory=args.mem,
        time=args.time,
        mail_directives=mail_directives,
        command=command
    )
    
    # Write file
    output_file = output_path / f"{job_name}.sbatch"
    with open(output_file, 'w') as f:
        f.write(script)
    
    return output_file


def main():
    parser = argparse.ArgumentParser(description='Generate SLURM batch files from command file')
    parser.add_argument('-i', '--input', required=True,
                       help='Input command file (e.g., dorado_basecaller_sup_cmd.txt)')
    parser.add_argument('-o', '--output', required=True,
                       help='Output directory for batch files')
    parser.add_argument('--account', required=True,
                       help='SLURM account')
    parser.add_argument('--partition', default='gpu',
                       help='SLURM partition (default: gpu)')
    parser.add_argument('--gres', default='gpu:1',
                       help='GPU resource string (default: gpu:1)')
    parser.add_argument('--cpus', type=int, default=8,
                       help='CPUs per task (default: 8)')
    parser.add_argument('--mem', default='64G',
                       help='Memory allocation (default: 64G)')
    parser.add_argument('--time', default='24:00:00',
                       help='Time limit (default: 24:00:00)')
    parser.add_argument('--email', default='',
                       help='Email for notifications')
    parser.add_argument('--mail-type', default='BEGIN,END,FAIL',
                       help='Mail type (default: BEGIN,END,FAIL)')
    
    args = parser.parse_args()
    
    # Read commands
    input_file = Path(args.input)
    if not input_file.exists():
        print(f"❌ Error: Input file not found: {input_file}")
        return 1
    
    with open(input_file, 'r') as f:
        commands = [line.strip() for line in f if line.strip()]
    
    # Create output directory
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create Logs directory
    logs_dir = Path('Logs')
    logs_dir.mkdir(exist_ok=True)
    
    # Generate batch files
    print(f"Generating SLURM batch files...")
    print(f"  Input: {input_file}")
    print(f"  Output: {output_path}")
    print(f"  Account: {args.account}")
    print(f"  Partition: {args.partition}")
    print(f"  Commands: {len(commands)}")
    print()
    
    batch_files = []
    for i, command in enumerate(commands, 1):
        output_file = create_sbatch_file(command, output_path, args)
        batch_files.append(output_file)
        print(f"  [{i:3d}/{len(commands)}] Created {output_file.name}")
    
    # Create submission script
    submit_script = output_path.parent / 'sbatch_all.sh'
    with open(submit_script, 'w') as f:
        f.write('#!/bin/bash\n')
        f.write('# Submit all SLURM batch files\n\n')
        f.write('echo "Submitting batch files from {}"\\n'.format(output_path))
        f.write('SUBMITTED=0\n')
        f.write('FAILED=0\n\n')
        for batch_file in batch_files:
            f.write(f'if sbatch {batch_file}; then\n')
            f.write('    ((SUBMITTED++))\n')
            f.write('    sleep 2  # Brief delay between submissions\n')
            f.write('else\n')
            f.write('    ((FAILED++))\n')
            f.write(f'    echo "Failed to submit {batch_file}"\n')
            f.write('fi\n\n')
        f.write('echo ""\n')
        f.write('echo "Submission complete:"\n')
        f.write('echo "  Submitted: $SUBMITTED"\n')
        f.write('echo "  Failed: $FAILED"\n')
    
    submit_script.chmod(0o755)
    
    print()
    print(f"✅ Generated {len(batch_files)} SLURM batch files")
    print(f"✅ Created submission script: {submit_script}")
    print()
    print("Next steps:")
    print(f"  1. Review batch files in: {output_path}")
    print(f"  2. Submit all jobs: bash {submit_script}")
    print(f"  3. Monitor progress: squeue -u $USER")
    
    return 0


if __name__ == '__main__':
    exit(main())
