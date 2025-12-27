#!/usr/bin/env python3
"""
Test suite for ONT End Reason QC v2.0
"""

import sys
import json
import tempfile
from pathlib import Path

# Add bin to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'bin'))

def test_imports():
    """Test that all dependencies are available"""
    try:
        import numpy as np
        print("✓ numpy available")
    except ImportError:
        print("✗ numpy NOT available")
        return False
    
    try:
        from scipy.ndimage import gaussian_filter1d
        print("✓ scipy available")
    except ImportError:
        print("! scipy NOT available (KDE smoothing limited)")
    
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        print("✓ matplotlib available")
    except ImportError:
        print("✗ matplotlib NOT available")
        return False
    
    return True

def create_mock_summary(tmpdir, exp_name, n_reads=1000):
    """Create a mock sequencing_summary.txt"""
    import random
    
    summary_file = tmpdir / exp_name / "sequencing_summary.txt"
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(summary_file, 'w') as f:
        f.write("read_id\tsequence_length_template\tend_reason\n")
        
        for i in range(n_reads):
            read_id = f"read_{i:06d}"
            
            # 90% signal_positive, 8% unblock, 2% other
            r = random.random()
            if r < 0.90:
                end_reason = "signal_positive"
                # Normal distribution around 2630bp
                length = int(random.gauss(2630, 150))
            elif r < 0.98:
                end_reason = "unblock_mux_change"
                # Wider distribution
                length = int(random.gauss(2000, 500))
            else:
                end_reason = "mux_change"
                length = int(random.gauss(2630, 200))
            
            length = max(50, length)  # Minimum length
            f.write(f"{read_id}\t{length}\t{end_reason}\n")
    
    return summary_file.parent

def test_analysis():
    """Test basic analysis functionality"""
    from ont_endreason_qc import analyze_experiment, ExperimentStats
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        exp_dir = create_mock_summary(tmpdir, "test_run", n_reads=500)
        
        stats = analyze_experiment(exp_dir, max_reads=500)
        
        assert stats.total_reads == 500, f"Expected 500 reads, got {stats.total_reads}"
        assert stats.signal_positive.count > 0, "No signal_positive reads found"
        assert stats.signal_positive.pct > 80, f"Signal positive {stats.signal_positive.pct}% < 80%"
        assert stats.quality_grade in ['A', 'B', 'C', 'D'], f"Invalid grade: {stats.quality_grade}"
        
        print(f"  Analysis: ✓ PASSED (grade={stats.quality_grade}, sp={stats.signal_positive.pct:.1f}%)")
        return True

def test_kde_plot():
    """Test KDE plot generation"""
    from ont_endreason_qc import analyze_experiment, plot_kde_comparison
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        exp_dir = create_mock_summary(tmpdir, "test_kde", n_reads=500)
        output_png = tmpdir / "test_kde.png"
        
        stats = analyze_experiment(exp_dir, max_reads=500)
        plot_kde_comparison(stats, output_png, dpi=100)
        
        assert output_png.exists(), "KDE plot not created"
        assert output_png.stat().st_size > 10000, "KDE plot too small"
        
        print(f"  KDE Plot: ✓ PASSED ({output_png.stat().st_size} bytes)")
        return True

def test_multizoom_plot():
    """Test multi-zoom plot generation"""
    from ont_endreason_qc import analyze_experiment, plot_multizoom
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        exp_dir = create_mock_summary(tmpdir, "test_zoom", n_reads=500)
        output_png = tmpdir / "test_zoom.png"
        
        stats = analyze_experiment(exp_dir, max_reads=500)
        plot_multizoom(stats, output_png, dpi=100)
        
        assert output_png.exists(), "Multizoom plot not created"
        assert output_png.stat().st_size > 20000, "Multizoom plot too small"
        
        print(f"  MultiZoom: ✓ PASSED ({output_png.stat().st_size} bytes)")
        return True

def test_json_output():
    """Test JSON statistics output"""
    from ont_endreason_qc import analyze_experiment
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        exp_dir = create_mock_summary(tmpdir, "test_json", n_reads=500)
        
        stats = analyze_experiment(exp_dir, max_reads=500)
        
        # Verify JSON-serializable structure
        output = {
            "name": stats.name,
            "total_reads": stats.total_reads,
            "quality_grade": stats.quality_grade,
            "signal_positive_pct": stats.signal_positive.pct,
            "unblock_pct": stats.unblock.pct,
        }
        
        json_str = json.dumps(output)
        parsed = json.loads(json_str)
        
        assert parsed["total_reads"] == 500
        assert "quality_grade" in parsed
        
        print(f"  JSON: ✓ PASSED")
        return True

def main():
    print("=" * 60)
    print("ONT END REASON QC v2.0 TESTS")
    print("=" * 60)
    
    if not test_imports():
        print("\n❌ Import tests failed")
        return 1
    
    print()
    passed = 0
    total = 4
    
    try:
        if test_analysis():
            passed += 1
    except Exception as e:
        print(f"  Analysis: ✗ FAILED - {e}")
    
    try:
        if test_kde_plot():
            passed += 1
    except Exception as e:
        print(f"  KDE Plot: ✗ FAILED - {e}")
    
    try:
        if test_multizoom_plot():
            passed += 1
    except Exception as e:
        print(f"  MultiZoom: ✗ FAILED - {e}")
    
    try:
        if test_json_output():
            passed += 1
    except Exception as e:
        print(f"  JSON: ✗ FAILED - {e}")
    
    print()
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 60)
    
    return 0 if passed == total else 1

if __name__ == '__main__':
    sys.exit(main())
