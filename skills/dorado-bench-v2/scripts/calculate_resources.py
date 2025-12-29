#!/usr/bin/env python3
"""
Calculate optimal resource allocation for dorado basecalling jobs

Usage:
    python3 calculate_resources.py --tier sup --cluster armis2 --samples 4
"""

import argparse


# Base resource requirements by model tier
BASE_RESOURCES = {
    'fast': {'gpu_ram': 4, 'cpu_ram': 16, 'cpus': 16, 'time_hours': 6},
    'hac':  {'gpu_ram': 6, 'cpu_ram': 32, 'cpus': 20, 'time_hours': 12},
    'sup':  {'gpu_ram': 12, 'cpu_ram': 64, 'cpus': 30, 'time_hours': 24}
}

# GPU specifications
GPU_SPECS = {
    'armis2': {'vram': 48, 'name': 'A40'},
    'greatlakes': {'vram': 40, 'name': 'A100 MIG'}
}


def calculate_batch_size(model_tier, cluster, modifications=False):
    """Calculate optimal batch size"""
    base_ram = BASE_RESOURCES[model_tier]['gpu_ram']
    gpu_vram = GPU_SPECS[cluster]['vram']
    
    # Adjust for modifications
    if modifications:
        base_ram *= 1.3
    
    # Calculate max batch size
    max_batch = int(gpu_vram * 1000 / base_ram)
    
    # Round to nearest power of 2
    batch_sizes = [128, 256, 512, 1024, 2048, 4096, 8192]
    for size in reversed(batch_sizes):
        if size <= max_batch:
            return size
    
    return 128


def format_time(hours):
    """Format hours into SLURM time string"""
    days = hours // 24
    remaining_hours = hours % 24
    if days > 0:
        return f"{days}-{remaining_hours:02d}:00:00"
    return f"{remaining_hours:02d}:00:00"


def calculate_resources(model_tier, cluster, num_samples=1, modifications=False):
    """Calculate optimal resource allocation"""
    
    base = BASE_RESOURCES[model_tier].copy()
    
    # Adjust for modifications
    if modifications:
        base['cpu_ram'] = int(base['cpu_ram'] * 1.5)
        base['time_hours'] = int(base['time_hours'] * 1.2)
    
    # Calculate batch size
    batch_size = calculate_batch_size(model_tier, cluster, modifications)
    
    # Format time
    time_str = format_time(base['time_hours'])
    
    resources = {
        'batch_size': batch_size,
        'memory': f"{base['cpu_ram']}G",
        'cpus': base['cpus'],
        'time': time_str,
        'gpu': GPU_SPECS[cluster]['name']
    }
    
    return resources


def main():
    parser = argparse.ArgumentParser(description='Calculate optimal dorado resources')
    parser.add_argument('--tier', required=True, choices=['fast', 'hac', 'sup'],
                       help='Model tier')
    parser.add_argument('--cluster', required=True, choices=['armis2', 'greatlakes'],
                       help='Target cluster')
    parser.add_argument('--samples', type=int, default=1,
                       help='Number of samples (for time estimation)')
    parser.add_argument('--modifications', action='store_true',
                       help='Enable modified base detection')
    
    args = parser.parse_args()
    
    # Calculate resources
    resources = calculate_resources(
        args.tier, args.cluster, args.samples, args.modifications
    )
    
    # Display results
    print(f"Recommended Resources for {args.tier.upper()} on {args.cluster.upper()}:")
    print(f"  GPU: {resources['gpu']}")
    print(f"  Batch Size: {resources['batch_size']}")
    print(f"  CPUs: {resources['cpus']}")
    print(f"  Memory: {resources['memory']}")
    print(f"  Time Limit: {resources['time']}")
    
    if args.modifications:
        print(f"  Note: Adjusted for modified base detection")
    
    print()
    print("Example SLURM command:")
    gres = 'gpu:a40:1' if args.cluster == 'armis2' else 'gpu:nvidia_a100_80gb_pcie_3g.40gb:1'
    print(f"  --cpus-per-task={resources['cpus']}")
    print(f"  --mem={resources['memory']}")
    print(f"  --time={resources['time']}")
    print(f"  --gres={gres}")


if __name__ == '__main__':
    main()
