#!/usr/bin/env python3
"""
Dorado Basecall - ONT Basecalling with Provenance Tracking

Designed for Pattern B integration with ont-experiments:
  ont_experiments.py run basecalling <exp_id> --model sup --output calls.bam

Can also run standalone:
  dorado_basecall.py /path/to/pod5 --model sup --output calls.bam

Output fields (captured by ont-experiments):
  - total_reads, pass_reads
  - mean_qscore, median_qscore
  - bases_called, n50
  - model, model_path, model_tier, model_version
"""

import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


# =============================================================================
# Q-score Utilities (Phred scale)
# =============================================================================

def qscore_to_error_prob(q: float) -> float:
    """Convert Q-score to error probability: P = 10^(-Q/10)"""
    return 10 ** (-q / 10)

def error_prob_to_qscore(p: float) -> float:
    """Convert error probability to Q-score: Q = -10 * log10(P)"""
    if p <= 0:
        return 60.0  # Cap at Q60 for zero probability
    return -10 * math.log10(p)

def mean_qscore_from_quals(quals: List[int]) -> float:
    """
    Calculate mean Q-score correctly via probability space.

    Q-scores are logarithmic, so we must:
    1. Convert each Q to error probability
    2. Average the probabilities
    3. Convert back to Q-score
    """
    if not quals:
        return 0.0
    probs = [qscore_to_error_prob(q) for q in quals]
    mean_prob = sum(probs) / len(probs)
    return error_prob_to_qscore(mean_prob)

# Optional imports
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import pod5
    HAS_POD5 = True
except ImportError:
    HAS_POD5 = False

try:
    import pysam
    HAS_PYSAM = True
except ImportError:
    HAS_PYSAM = False


# =============================================================================
# Cluster Configurations
# =============================================================================

CLUSTER_CONFIGS = {
    'armis2': {
        'name': 'ARMIS2',
        'partition': 'sigbio-a40',
        'account': 'bleu1',
        'gres': 'gpu:a40:1',
        'dorado_path': '/nfs/turbo/umms-bleu-secure/programs/dorado-1.1.1-linux-x64/bin/dorado',
        'model_dir': '/nfs/turbo/umms-bleu-secure/programs/dorado_models',
        'output_dir': '/nfs/turbo/umms-bleu-secure/basecalled_AGC_data',
        'gpu_type': 'A40',
        'gpu_vram_gb': 48,
    },
    'greatlakes': {
        'name': 'Great Lakes',
        'partition': 'gpu_mig40',
        'account': 'bleu99',
        'gres': 'gpu:nvidia_a100_80gb_pcie_3g.40gb:1',
        'dorado_path': '/nfs/turbo/umms-atheylab/dorado-bench/dorado-1.1.1-linux-x64/bin/dorado',
        'model_dir': '/nfs/turbo/umms-atheylab/dorado-bench/Models/Simplex',
        'output_dir': '/nfs/turbo/umms-atheylab/dorado-bench/Output',
        'gpu_type': 'A100_MIG',
        'gpu_vram_gb': 40,
    },
}

MODEL_TIERS = {
    'fast': {
        'suffix': 'fast',
        'description': 'Fast model for real-time QC',
        'accuracy': '~95%',
        'speed_factor': 1.0,
        'armis2': {'batch_size': 4096, 'memory': '50G', 'cpus': 16, 'time': '24:00:00'},
        'greatlakes': {'batch_size': 2048, 'memory': '40G', 'cpus': 12, 'time': '36:00:00'},
    },
    'hac': {
        'suffix': 'hac',
        'description': 'High accuracy model for standard analysis',
        'accuracy': '~98%',
        'speed_factor': 0.5,
        'armis2': {'batch_size': 2048, 'memory': '75G', 'cpus': 20, 'time': '72:00:00'},
        'greatlakes': {'batch_size': 1024, 'memory': '60G', 'cpus': 16, 'time': '96:00:00'},
    },
    'sup': {
        'suffix': 'sup',
        'description': 'Super accuracy model for publication/clinical',
        'accuracy': '~99%',
        'speed_factor': 0.2,
        'armis2': {'batch_size': 1024, 'memory': '100G', 'cpus': 30, 'time': '144:00:00'},
        'greatlakes': {'batch_size': 512, 'memory': '80G', 'cpus': 24, 'time': '192:00:00'},
    },
}

CHEMISTRY_MODELS = {
    'r10.4.1': 'dna_r10.4.1_e8.2_400bps',
    'r9.4.1': 'dna_r9.4.1_e8',
    'rna004': 'rna004_130bps',
}

DEFAULT_VERSION = 'v5.0.0'


# =============================================================================
# Chemistry Detection
# =============================================================================

def detect_chemistry(pod5_path: Path) -> Optional[str]:
    """Detect chemistry from POD5 metadata"""
    if not HAS_POD5:
        return None
    
    try:
        pod5_files = [pod5_path] if pod5_path.suffix == '.pod5' else list(pod5_path.rglob('*.pod5'))
        if not pod5_files:
            return None
        
        with pod5.Reader(pod5_files[0]) as reader:
            for read in reader.reads():
                # Check context tags for chemistry info
                run_info = read.run_info
                
                # Flow cell product code indicates chemistry
                flowcell = run_info.flow_cell_product_code
                if flowcell:
                    if 'FLO-PRO114' in flowcell or 'FLO-MIN114' in flowcell:
                        return 'r10.4.1'
                    elif 'FLO-PRO002' in flowcell or 'FLO-MIN106' in flowcell:
                        return 'r9.4.1'
                    elif 'FLO-PRO004' in flowcell:
                        return 'rna004'
                
                # Try sequencing kit
                kit = run_info.sequencing_kit
                if kit:
                    if 'LSK114' in kit or 'NBD114' in kit:
                        return 'r10.4.1'
                    elif 'LSK109' in kit or 'NBD104' in kit:
                        return 'r9.4.1'
                
                break
    except Exception:
        pass
    
    return 'r10.4.1'  # Default to latest


def build_model_name(tier: str, version: str, chemistry: str) -> str:
    """Build full model name from components"""
    base = CHEMISTRY_MODELS.get(chemistry, 'dna_r10.4.1_e8.2_400bps')
    tier_suffix = MODEL_TIERS.get(tier, MODEL_TIERS['hac'])['suffix']
    
    # Handle version format
    if not version.startswith('v'):
        version = f'v{version}'
    
    return f"{base}_{tier_suffix}@{version}"


def parse_model_string(model_str: str) -> Dict[str, str]:
    """Parse model string into components"""
    result = {
        'full': model_str,
        'tier': 'hac',
        'version': DEFAULT_VERSION,
        'chemistry': 'r10.4.1',
    }
    
    # Check if it's a simple tier name
    if model_str.lower() in MODEL_TIERS:
        result['tier'] = model_str.lower()
        return result
    
    # Check for tier@version format
    if '@' in model_str:
        parts = model_str.split('@')
        if parts[0].lower() in MODEL_TIERS:
            result['tier'] = parts[0].lower()
            result['version'] = parts[1] if parts[1].startswith('v') else f'v{parts[1]}'
            return result
    
    # Full model name
    model_lower = model_str.lower()
    
    # Extract tier
    for tier in ['sup', 'hac', 'fast']:
        if f'_{tier}' in model_lower or f'_{tier}@' in model_lower:
            result['tier'] = tier
            break
    
    # Extract version
    version_match = re.search(r'@v?([\d.]+)', model_str)
    if version_match:
        result['version'] = f'v{version_match.group(1)}'
    
    # Extract chemistry
    if 'r10.4.1' in model_lower or 'e8.2' in model_lower:
        result['chemistry'] = 'r10.4.1'
    elif 'r9.4.1' in model_lower:
        result['chemistry'] = 'r9.4.1'
    elif 'rna' in model_lower:
        result['chemistry'] = 'rna004'
    
    result['full'] = model_str
    
    return result


# =============================================================================
# Resource Calculation
# =============================================================================

def calculate_resources(
    model_tier: str,
    cluster: str,
    modifications: Optional[List[str]] = None,
    estimated_reads: Optional[int] = None,
) -> Dict[str, Any]:
    """Calculate optimal resources for basecalling job"""
    
    tier_config = MODEL_TIERS.get(model_tier, MODEL_TIERS['hac'])
    cluster_key = cluster.lower().replace('-', '').replace('_', '')
    
    if cluster_key not in ['armis2', 'greatlakes']:
        cluster_key = 'armis2'
    
    resources = tier_config[cluster_key].copy()
    
    # Adjust for modifications
    if modifications:
        resources['batch_size'] = int(resources['batch_size'] * 0.7)
        
        # Parse memory
        mem = resources['memory']
        if mem.endswith('G'):
            mem_val = int(mem[:-1])
            resources['memory'] = f'{int(mem_val * 1.5)}G'
        
        # Parse time
        time_parts = resources['time'].split(':')
        hours = int(time_parts[0])
        resources['time'] = f'{int(hours * 1.2):02d}:{time_parts[1]}:{time_parts[2]}'
    
    return resources


# =============================================================================
# Basecalling
# =============================================================================

def find_dorado(cluster: str) -> Optional[str]:
    """Find dorado executable"""
    cluster_config = CLUSTER_CONFIGS.get(cluster.lower(), CLUSTER_CONFIGS['armis2'])
    dorado_path = cluster_config['dorado_path']
    
    if Path(dorado_path).exists():
        return dorado_path
    
    # Try to find in PATH
    try:
        result = subprocess.run(['which', 'dorado'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    
    return None


def find_model(model_name: str, cluster: str) -> Optional[str]:
    """Find model path"""
    cluster_config = CLUSTER_CONFIGS.get(cluster.lower(), CLUSTER_CONFIGS['armis2'])
    model_dir = Path(cluster_config['model_dir'])
    
    # Direct path
    model_path = model_dir / model_name
    if model_path.exists():
        return str(model_path)
    
    # Try without version
    base_name = model_name.split('@')[0] if '@' in model_name else model_name
    for p in model_dir.glob(f'{base_name}*'):
        if p.is_dir():
            return str(p)
    
    return None


def build_dorado_command(
    input_path: Path,
    output_path: Path,
    model: str,
    dorado_path: str,
    model_path: Optional[str] = None,
    device: str = 'cuda:0',
    batch_size: Optional[int] = None,
    emit_moves: bool = False,
    trim: bool = True,
    modifications: Optional[List[str]] = None,
) -> List[str]:
    """Build dorado basecaller command"""
    
    cmd = [dorado_path, 'basecaller']
    
    # Model
    if model_path:
        cmd.append(model_path)
    else:
        cmd.append(model)
    
    # Input
    cmd.append(str(input_path))
    
    # Device
    cmd.extend(['--device', device])
    
    # Batch size
    if batch_size:
        cmd.extend(['--batchsize', str(batch_size)])
    
    # Options
    if emit_moves:
        cmd.append('--emit-moves')
    
    if not trim:
        cmd.append('--no-trim')
    
    # Modifications
    if modifications:
        for mod in modifications:
            cmd.extend(['--modified-bases', mod])
    
    return cmd


def run_basecalling(
    input_path: Path,
    output_path: Path,
    model: str,
    cluster: str = 'armis2',
    device: str = 'cuda:0',
    batch_size: Optional[int] = None,
    emit_moves: bool = False,
    trim: bool = True,
    modifications: Optional[List[str]] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Run dorado basecalling and return results"""
    
    start_time = time.time()
    
    # Find dorado
    dorado_path = find_dorado(cluster)
    if not dorado_path:
        return {
            'success': False,
            'error': f'Dorado not found for cluster {cluster}',
            'exit_code': 1,
        }
    
    # Parse model
    model_info = parse_model_string(model)
    
    # Detect chemistry if needed
    if model_info['chemistry'] == 'r10.4.1':
        detected = detect_chemistry(input_path)
        if detected:
            model_info['chemistry'] = detected
    
    # Build full model name
    full_model = build_model_name(
        model_info['tier'],
        model_info['version'],
        model_info['chemistry']
    )
    
    # Find model path
    model_path = find_model(full_model, cluster)
    
    # Calculate resources if needed
    if batch_size is None:
        resources = calculate_resources(
            model_info['tier'],
            cluster,
            modifications
        )
        batch_size = resources['batch_size']
    
    # Build command
    cmd = build_dorado_command(
        input_path=input_path,
        output_path=output_path,
        model=full_model,
        dorado_path=dorado_path,
        model_path=model_path,
        device=device,
        batch_size=batch_size,
        emit_moves=emit_moves,
        trim=trim,
        modifications=modifications,
    )
    
    if verbose:
        print(f"  Command: {' '.join(cmd)}")
    
    # Run
    try:
        # Output to BAM file
        with open(output_path, 'wb') as f:
            result = subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                text=False,
            )
        
        duration = time.time() - start_time
        
        # Parse stderr for stats
        stderr = result.stderr.decode('utf-8', errors='replace') if result.stderr else ''
        stats = parse_dorado_output(stderr)
        
        # Get output file stats
        output_size = output_path.stat().st_size if output_path.exists() else 0
        
        # Try to get BAM stats
        bam_stats = get_bam_stats(output_path) if HAS_PYSAM and output_path.exists() else {}
        
        return {
            'success': result.returncode == 0,
            'exit_code': result.returncode,
            'command': ' '.join(cmd),
            'duration_seconds': round(duration, 2),
            'model': full_model,
            'model_path': model_path,
            'model_tier': model_info['tier'],
            'model_version': model_info['version'],
            'chemistry': model_info['chemistry'],
            'device': device,
            'batch_size': batch_size,
            'emit_moves': emit_moves,
            'trim': trim,
            'modifications': modifications,
            'output_path': str(output_path),
            'output_size_bytes': output_size,
            **stats,
            **bam_stats,
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'exit_code': -1,
            'duration_seconds': round(time.time() - start_time, 2),
        }


def parse_dorado_output(stderr: str) -> Dict[str, Any]:
    """Parse dorado stderr for statistics"""
    stats = {}
    
    # Look for summary lines
    for line in stderr.split('\n'):
        # Reads processed
        match = re.search(r'(\d+)\s+reads', line.lower())
        if match:
            stats['total_reads'] = int(match.group(1))
        
        # Bases
        match = re.search(r'(\d+(?:\.\d+)?)\s*(g|m|k)?bases', line.lower())
        if match:
            value = float(match.group(1))
            suffix = match.group(2) or ''
            multiplier = {'g': 1e9, 'm': 1e6, 'k': 1e3}.get(suffix, 1)
            stats['bases_called'] = int(value * multiplier)
        
        # Speed
        match = re.search(r'(\d+(?:\.\d+)?)\s*samples/s', line)
        if match:
            stats['samples_per_second'] = float(match.group(1))
    
    return stats


def get_bam_stats(bam_path: Path) -> Dict[str, Any]:
    """Get statistics from BAM file"""
    if not HAS_PYSAM:
        return {}
    
    stats = {
        'total_reads': 0,
        'pass_reads': 0,
        'total_bases': 0,
        'qualities': [],
        'lengths': [],
    }
    
    try:
        with pysam.AlignmentFile(str(bam_path), 'rb', check_sq=False) as bam:
            for read in bam.fetch(until_eof=True):
                stats['total_reads'] += 1
                stats['total_bases'] += read.query_length
                stats['lengths'].append(read.query_length)
                
                # Get mean quality (via probability space for correct averaging)
                if read.query_qualities:
                    mean_qual = mean_qscore_from_quals(list(read.query_qualities))
                    stats['qualities'].append(mean_qual)

                    if mean_qual >= 10:  # Q10 pass threshold
                        stats['pass_reads'] += 1
    except Exception:
        pass
    
    # Calculate summary stats (aggregate via probability space)
    if stats['qualities']:
        # Convert per-read mean Q-scores to probabilities, average, convert back
        probs = [qscore_to_error_prob(q) for q in stats['qualities']]
        mean_prob = sum(probs) / len(probs)
        stats['mean_qscore'] = round(error_prob_to_qscore(mean_prob), 2)
        sorted_q = sorted(stats['qualities'])
        stats['median_qscore'] = round(sorted_q[len(sorted_q) // 2], 2)
    
    if stats['lengths']:
        sorted_l = sorted(stats['lengths'], reverse=True)
        cumsum = 0
        total = sum(sorted_l)
        for length in sorted_l:
            cumsum += length
            if cumsum >= total / 2:
                stats['n50'] = length
                break
    
    # Clean up
    del stats['qualities']
    del stats['lengths']
    
    return stats


# =============================================================================
# SLURM Job Generation
# =============================================================================

def generate_slurm_script(
    input_path: Path,
    output_path: Path,
    model: str,
    cluster: str = 'armis2',
    job_name: Optional[str] = None,
    email: Optional[str] = None,
    modifications: Optional[List[str]] = None,
    emit_moves: bool = False,
    trim: bool = True,
) -> str:
    """Generate SLURM batch script"""
    
    cluster_config = CLUSTER_CONFIGS.get(cluster.lower(), CLUSTER_CONFIGS['armis2'])
    model_info = parse_model_string(model)
    resources = calculate_resources(model_info['tier'], cluster, modifications)
    
    full_model = build_model_name(
        model_info['tier'],
        model_info['version'],
        model_info['chemistry']
    )
    
    model_path = find_model(full_model, cluster)
    
    if not job_name:
        job_name = f"dorado_{model_info['tier']}_{input_path.name}"
    
    script = f"""#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --account={cluster_config['account']}
#SBATCH --partition={cluster_config['partition']}
#SBATCH --gres={cluster_config['gres']}
#SBATCH --cpus-per-task={resources['cpus']}
#SBATCH --mem={resources['memory']}
#SBATCH --time={resources['time']}
#SBATCH --output=%x_%j.out
#SBATCH --error=%x_%j.err
"""
    
    if email:
        script += f"""#SBATCH --mail-user={email}
#SBATCH --mail-type=BEGIN,END,FAIL
"""
    
    script += f"""
# Dorado Basecalling Job
# Generated: {datetime.now(timezone.utc).isoformat()}
# Cluster: {cluster_config['name']}
# Model: {full_model}

echo "Starting dorado basecalling"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURMD_NODENAME"
echo "Time: $(date)"

# Check GPU
nvidia-smi

# Set paths
DORADO="{cluster_config['dorado_path']}"
MODEL="{model_path or full_model}"
INPUT="{input_path}"
OUTPUT="{output_path}"

# Run dorado
$DORADO basecaller \\
    $MODEL \\
    $INPUT \\
    --device cuda:0 \\
    --batchsize {resources['batch_size']} \\
"""
    
    if emit_moves:
        script += "    --emit-moves \\\n"
    
    if not trim:
        script += "    --no-trim \\\n"
    
    if modifications:
        for mod in modifications:
            script += f"    --modified-bases {mod} \\\n"
    
    script += f"""    > $OUTPUT

echo "Completed: $(date)"
echo "Output size: $(ls -lh $OUTPUT)"
"""
    
    return script


# =============================================================================
# Output
# =============================================================================

def print_summary(results: Dict[str, Any]):
    """Print basecalling summary"""
    
    print(f"\n  Dorado Basecalling Results")
    print(f"  {'═' * 50}")
    
    if results.get('success'):
        print(f"\n  ✓ Success")
    else:
        print(f"\n  ✗ Failed")
        if results.get('error'):
            print(f"    Error: {results['error']}")
    
    print(f"\n  Model: {results.get('model', 'unknown')}")
    print(f"  Tier: {results.get('model_tier', 'unknown')}")
    print(f"  Version: {results.get('model_version', 'unknown')}")
    print(f"  Chemistry: {results.get('chemistry', 'unknown')}")
    
    print(f"\n  Configuration")
    print(f"  {'─' * 40}")
    print(f"  Device: {results.get('device', 'unknown')}")
    print(f"  Batch size: {results.get('batch_size', 'unknown')}")
    print(f"  Emit moves: {results.get('emit_moves', False)}")
    print(f"  Trim: {results.get('trim', True)}")
    
    if results.get('total_reads'):
        print(f"\n  Statistics")
        print(f"  {'─' * 40}")
        print(f"  Total reads: {results['total_reads']:,}")
        if results.get('pass_reads'):
            print(f"  Pass reads: {results['pass_reads']:,}")
        if results.get('total_bases'):
            print(f"  Total bases: {results['total_bases']:,}")
        if results.get('mean_qscore'):
            print(f"  Mean Q-score: {results['mean_qscore']:.1f}")
        if results.get('n50'):
            print(f"  N50: {results['n50']:,}")
    
    print(f"\n  Duration: {results.get('duration_seconds', 0):.1f}s")
    
    if results.get('output_path'):
        size_gb = results.get('output_size_bytes', 0) / (1024**3)
        print(f"  Output: {results['output_path']} ({size_gb:.2f} GB)")
    
    print()


def write_json(results: Dict[str, Any], filepath: Path):
    """Write results to JSON file"""
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"  JSON written: {filepath}")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Dorado Basecalling with Provenance Tracking',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s /path/to/pod5 --model sup --output calls.bam
  %(prog)s /path/to/pod5 --model hac@v5.0.0 --cluster armis2
  %(prog)s /path/to/pod5 --model sup --slurm job.sbatch

Integration with ont-experiments:
  ont_experiments.py run basecalling exp-abc123 --model sup --output calls.bam
'''
    )
    
    parser.add_argument('input', help='POD5 directory or file')
    
    # Model options
    model_group = parser.add_argument_group('Model Options')
    model_group.add_argument('--model', default='hac',
                            help='Model: fast, hac, sup, or full name (default: hac)')
    model_group.add_argument('--version', default=DEFAULT_VERSION,
                            help=f'Model version (default: {DEFAULT_VERSION})')
    model_group.add_argument('--chemistry', choices=['r10.4.1', 'r9.4.1', 'rna004'],
                            help='Chemistry (default: auto-detect)')
    
    # Cluster options
    cluster_group = parser.add_argument_group('Cluster Options')
    cluster_group.add_argument('--cluster', default='armis2',
                              choices=['armis2', 'greatlakes'],
                              help='HPC cluster (default: armis2)')
    cluster_group.add_argument('--device', default='cuda:0',
                              help='CUDA device (default: cuda:0)')
    cluster_group.add_argument('--batch-size', type=int,
                              help='Batch size (default: auto)')
    
    # Output options
    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument('--output', '-o', required=True,
                             help='Output BAM file')
    output_group.add_argument('--emit-moves', action='store_true',
                             help='Include move table')
    output_group.add_argument('--no-trim', action='store_true',
                             help='Disable adapter trimming')
    output_group.add_argument('--modifications', nargs='+',
                             help='Modified bases (e.g., 5mCG_5hmCG)')
    
    # Job options
    job_group = parser.add_argument_group('Job Options')
    job_group.add_argument('--slurm', metavar='FILE',
                          help='Generate SLURM script instead of running')
    job_group.add_argument('--job-name',
                          help='SLURM job name')
    job_group.add_argument('--email',
                          help='Email for SLURM notifications')
    
    # Other options
    parser.add_argument('--json', metavar='FILE',
                       help='Output JSON results')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    
    if not input_path.exists():
        print(f"Error: Input not found: {input_path}", file=sys.stderr)
        return 1
    
    # Build model string
    model = args.model
    if args.version and '@' not in model and model.lower() in MODEL_TIERS:
        model = f"{model}@{args.version}"
    
    # Generate SLURM script mode
    if args.slurm:
        script = generate_slurm_script(
            input_path=input_path,
            output_path=output_path,
            model=model,
            cluster=args.cluster,
            job_name=args.job_name,
            email=args.email,
            modifications=args.modifications,
            emit_moves=args.emit_moves,
            trim=not args.no_trim,
        )
        
        slurm_path = Path(args.slurm)
        with open(slurm_path, 'w') as f:
            f.write(script)
        
        print(f"  SLURM script written: {slurm_path}")
        print(f"  Submit with: sbatch {slurm_path}")
        return 0
    
    # Run basecalling
    print(f"\n  Input: {input_path}")
    print(f"  Output: {output_path}")
    print(f"  Model: {model}")
    print(f"  Cluster: {args.cluster}")
    
    results = run_basecalling(
        input_path=input_path,
        output_path=output_path,
        model=model,
        cluster=args.cluster,
        device=args.device,
        batch_size=args.batch_size,
        emit_moves=args.emit_moves,
        trim=not args.no_trim,
        modifications=args.modifications,
        verbose=args.verbose,
    )
    
    print_summary(results)
    
    if args.json:
        write_json(results, Path(args.json))
    
    return 0 if results.get('success') else 1


if __name__ == '__main__':
    sys.exit(main())
