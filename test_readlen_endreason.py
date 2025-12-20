#!/usr/bin/env python3
"""
Test suite for ont_readlen_endreason.py combined analysis tool.

Generates synthetic ONT sequencing data with realistic end reason distributions
and tests all visualization and statistics functions.
"""

import sys
import os
import tempfile
import json
import random
from pathlib import Path

# Add project to path
sys.path.insert(0, '/mnt/project')

import numpy as np

def generate_synthetic_sequencing_summary(
    output_path: Path,
    n_reads: int = 10000,
    library_type: str = 'standard_ligation',
    adaptive_sampling: bool = False,
    seed: int = 42
):
    """
    Generate synthetic sequencing_summary.txt with realistic distributions.
    
    Library types:
    - standard_ligation: N50 ~10kb, high signal_positive
    - rapid_kit: N50 ~5kb, high signal_positive  
    - adaptive_sampling: Variable, significant unblock reads
    - short_amplicon: N50 ~1kb, mostly signal_positive
    """
    random.seed(seed)
    np.random.seed(seed)
    
    # Define length distributions by library type
    length_params = {
        'standard_ligation': {'mean': 8000, 'std': 5000, 'min': 200, 'max': 100000},
        'rapid_kit': {'mean': 5000, 'std': 3000, 'min': 200, 'max': 50000},
        'adaptive_sampling': {'mean': 6000, 'std': 4000, 'min': 200, 'max': 80000},
        'short_amplicon': {'mean': 1500, 'std': 500, 'min': 200, 'max': 5000},
    }
    
    # Define end reason distributions
    if adaptive_sampling:
        end_reason_probs = {
            'signal_positive': 0.70,
            'unblock_mux_change': 0.20,
            'data_service_unblock_mux_change': 0.05,
            'mux_change': 0.03,
            'signal_negative': 0.02,
        }
        # Unblocked reads are shorter
        unblock_length_factor = 0.15  # Much shorter
    else:
        end_reason_probs = {
            'signal_positive': 0.90,
            'unblock_mux_change': 0.03,
            'data_service_unblock_mux_change': 0.02,
            'mux_change': 0.03,
            'signal_negative': 0.02,
        }
        unblock_length_factor = 0.3
    
    params = length_params.get(library_type, length_params['standard_ligation'])
    
    # Generate reads
    reads = []
    end_reasons = list(end_reason_probs.keys())
    probs = list(end_reason_probs.values())
    
    for i in range(n_reads):
        # Choose end reason
        end_reason = random.choices(end_reasons, weights=probs)[0]
        
        # Generate length based on end reason
        if end_reason in ['unblock_mux_change', 'data_service_unblock_mux_change']:
            # Unblocked reads are shorter
            length = int(np.random.exponential(params['mean'] * unblock_length_factor))
        else:
            # Normal distribution for other reads
            length = int(np.random.lognormal(
                mean=np.log(params['mean']), 
                sigma=0.6
            ))
        
        # Clamp to range
        length = max(params['min'], min(length, params['max']))
        
        reads.append((length, end_reason, f"read_{i:08d}"))
    
    # Write sequencing_summary.txt
    with open(output_path, 'w') as f:
        # Header
        f.write("read_id\tsequence_length_template\tend_reason\n")
        for length, end_reason, read_id in reads:
            f.write(f"{read_id}\t{length}\t{end_reason}\n")
    
    return len(reads)


def run_tests():
    """Run comprehensive test suite."""
    
    print("=" * 60)
    print("ONT Read Length + End Reason Combined Analysis Test Suite")
    print("=" * 60)
    
    # Import the module
    from ont_readlen_endreason import (
        analyze_experiment,
        plot_by_end_reason,
        plot_multi_experiment_summary,
        plot_detailed_4panel,
        CombinedStats,
        EndReasonStats,
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test experiments
        experiments = [
            ('Standard_Ligation', 'standard_ligation', False, 5000),
            ('Adaptive_Sampling', 'adaptive_sampling', True, 5000),
            ('Short_PCR_Amplicon', 'short_amplicon', False, 5000),
        ]
        
        exp_dirs = []
        for name, lib_type, adaptive, n_reads in experiments:
            exp_dir = tmpdir / name
            exp_dir.mkdir()
            summary_path = exp_dir / 'sequencing_summary.txt'
            
            print(f"\n[TEST] Generating synthetic data: {name}")
            n = generate_synthetic_sequencing_summary(
                summary_path, 
                n_reads=n_reads,
                library_type=lib_type,
                adaptive_sampling=adaptive,
                seed=hash(name) % 2**31
            )
            print(f"  Generated {n:,} reads")
            exp_dirs.append(exp_dir)
        
        # Test 1: Analyze single experiment
        print("\n" + "-" * 40)
        print("[TEST 1] Single experiment analysis")
        print("-" * 40)
        
        stats = analyze_experiment(exp_dirs[0])
        
        assert isinstance(stats, CombinedStats)
        assert stats.total_reads > 0
        assert 0 <= stats.signal_positive_pct <= 100
        assert stats.n50 > 0
        assert len(stats.end_reason_stats) > 0
        
        print(f"  ✓ Experiment: {stats.experiment_name}")
        print(f"  ✓ Total reads: {stats.total_reads:,}")
        print(f"  ✓ Mean length: {stats.mean_length:,.0f} bp")
        print(f"  ✓ N50: {stats.n50:,} bp")
        print(f"  ✓ Signal Positive: {stats.signal_positive_pct:.1f}%")
        print(f"  ✓ Quality Status: {stats.quality_status}")
        print(f"  ✓ End reasons found: {list(stats.end_reason_stats.keys())}")
        
        # Test 2: Per end-reason statistics
        print("\n" + "-" * 40)
        print("[TEST 2] Per end-reason statistics")
        print("-" * 40)
        
        for er_name, er_stats in stats.end_reason_stats.items():
            assert isinstance(er_stats, EndReasonStats)
            assert er_stats.count >= 0
            if er_stats.count > 0:
                assert er_stats.n50 > 0
                assert er_stats.mean_length > 0
            print(f"  ✓ {er_name}: n={er_stats.count:,}, N50={er_stats.n50:,}, mean={er_stats.mean_length:,.0f}")
        
        # Test 3: Plot by end reason (semi-transparent)
        print("\n" + "-" * 40)
        print("[TEST 3] Semi-transparent distribution plot")
        print("-" * 40)
        
        plot_path = tmpdir / "test_by_endreason.png"
        plot_by_end_reason(stats, plot_path, alpha=0.4, dpi=150)
        
        assert plot_path.exists()
        file_size = plot_path.stat().st_size
        print(f"  ✓ Generated: {plot_path.name} ({file_size:,} bytes)")
        
        # Test 4: Detailed 4-panel plot
        print("\n" + "-" * 40)
        print("[TEST 4] Detailed 4-panel plot")
        print("-" * 40)
        
        detailed_path = tmpdir / "test_detailed.png"
        plot_detailed_4panel(stats, detailed_path, dpi=150)
        
        assert detailed_path.exists()
        file_size = detailed_path.stat().st_size
        print(f"  ✓ Generated: {detailed_path.name} ({file_size:,} bytes)")
        
        # Test 5: Multi-experiment analysis
        print("\n" + "-" * 40)
        print("[TEST 5] Multi-experiment analysis")
        print("-" * 40)
        
        all_stats = []
        for exp_dir in exp_dirs:
            exp_stats = analyze_experiment(exp_dir)
            all_stats.append(exp_stats)
            print(f"  ✓ {exp_stats.experiment_name}: SP={exp_stats.signal_positive_pct:.1f}%, Mean={exp_stats.mean_length:,.0f}")
        
        # Test 6: Multi-experiment summary plot
        print("\n" + "-" * 40)
        print("[TEST 6] Multi-experiment summary plot")
        print("-" * 40)
        
        summary_path = tmpdir / "test_multi_summary.png"
        plot_multi_experiment_summary(all_stats, summary_path, dpi=150)
        
        assert summary_path.exists()
        file_size = summary_path.stat().st_size
        print(f"  ✓ Generated: {summary_path.name} ({file_size:,} bytes)")
        
        # Test 7: JSON output
        print("\n" + "-" * 40)
        print("[TEST 7] JSON serialization")
        print("-" * 40)
        
        json_data = stats.to_dict()
        assert 'experiment_id' in json_data
        assert 'end_reason_stats' in json_data
        assert 'signal_positive_pct' in json_data
        
        # Verify JSON is serializable
        json_str = json.dumps(json_data, indent=2)
        print(f"  ✓ JSON serialization successful ({len(json_str):,} chars)")
        
        # Test 8: Adaptive sampling detection
        print("\n" + "-" * 40)
        print("[TEST 8] Adaptive sampling detection")
        print("-" * 40)
        
        adaptive_stats = all_stats[1]  # Adaptive_Sampling experiment
        unblock_stats = adaptive_stats.end_reason_stats.get('unblock_mux_change')
        sp_stats = adaptive_stats.end_reason_stats.get('signal_positive')
        
        if unblock_stats and sp_stats and unblock_stats.count > 0:
            # Unblocked reads should be significantly shorter
            length_ratio = sp_stats.mean_length / unblock_stats.mean_length
            print(f"  ✓ Signal Positive mean: {sp_stats.mean_length:,.0f} bp")
            print(f"  ✓ Unblock mean: {unblock_stats.mean_length:,.0f} bp")
            print(f"  ✓ Length ratio: {length_ratio:.1f}x (unblock should be shorter)")
            
            # In adaptive sampling, unblock reads should be much shorter
            assert length_ratio > 2, "Unblocked reads should be significantly shorter"
            print(f"  ✓ Adaptive sampling pattern confirmed!")
        
        # Copy test outputs to accessible location
        print("\n" + "-" * 40)
        print("[OUTPUT] Copying test plots to /mnt/user-data/outputs/")
        print("-" * 40)
        
        import shutil
        output_dir = Path("/mnt/user-data/outputs")
        output_dir.mkdir(exist_ok=True)
        
        shutil.copy(plot_path, output_dir / "test_by_endreason.png")
        shutil.copy(detailed_path, output_dir / "test_detailed_4panel.png")
        shutil.copy(summary_path, output_dir / "test_multi_summary.png")
        
        print(f"  ✓ test_by_endreason.png")
        print(f"  ✓ test_detailed_4panel.png")
        print(f"  ✓ test_multi_summary.png")
        
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
    
    return True


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
