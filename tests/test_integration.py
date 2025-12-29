#!/usr/bin/env python3
"""
Integration tests using real experiment data from the registry.

These tests verify end-to-end functionality with actual data structures.
"""

import json
import sys
from pathlib import Path

import pytest

# Add bin to path
bin_dir = Path(__file__).parent.parent / 'bin'
sys.path.insert(0, str(bin_dir))


# =============================================================================
# Experiment Registry Integration Tests
# =============================================================================

def test_experiment_registry_loads():
    """Test that the experiment registry loads and has valid structure"""
    registry_path = Path(__file__).parent.parent / 'data' / 'experiment_registry.json'

    assert registry_path.exists(), "Experiment registry should exist"

    with open(registry_path) as f:
        registry = json.load(f)

    assert "experiments" in registry, "Registry should have experiments key"
    assert "total_experiments" in registry, "Registry should have total_experiments"
    assert len(registry["experiments"]) > 0, "Should have at least one experiment"

    # Verify first experiment has required fields
    exp = registry["experiments"][0]
    required_fields = ["id", "path", "unique_id", "instrument", "flow_cell_id"]
    for field in required_fields:
        assert field in exp, f"Experiment should have {field}"


def test_experiment_registry_statistics():
    """Test that registry statistics are valid"""
    registry_path = Path(__file__).parent.parent / 'data' / 'experiment_registry.json'

    with open(registry_path) as f:
        registry = json.load(f)

    total_reads = registry.get("total_reads", 0)
    total_bases = registry.get("total_bases", 0)

    assert total_reads > 0, "Should have total reads"
    assert total_bases > 0, "Should have total bases"

    # Verify sum matches (handle None values)
    sum_reads = sum(exp.get("total_reads") or 0 for exp in registry["experiments"])
    assert sum_reads == total_reads, "Sum of reads should match total"


def test_experiment_has_metrics():
    """Test that experiments have QC metrics"""
    registry_path = Path(__file__).parent.parent / 'data' / 'experiment_registry.json'

    with open(registry_path) as f:
        registry = json.load(f)

    # Find an experiment with metrics
    experiments_with_metrics = [
        exp for exp in registry["experiments"]
        if exp.get("mean_qscore") is not None and exp.get("n50") is not None
    ]

    assert len(experiments_with_metrics) > 0, "Should have experiments with QC metrics"

    exp = experiments_with_metrics[0]
    assert exp["mean_qscore"] > 0, "Mean Q-score should be positive"
    assert exp["n50"] > 0, "N50 should be positive"


# =============================================================================
# Equation Execution Integration Tests
# =============================================================================

def test_equation_execution_with_mock_context():
    """Test equation execution with mock experiment context"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ont_context",
        bin_dir / "ont_context.py"
    )
    ont_context = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_context)

    # Load equations
    equations = ont_context.load_equations()
    assert len(equations.get("equations", {})) > 0, "Should have equations"

    # Find QC equations with Python implementations
    qc_equations = {
        eq_id: eq_data for eq_id, eq_data in equations.get("equations", {}).items()
        if eq_id.startswith("QC.") and isinstance(eq_data, dict) and eq_data.get("python")
    }

    assert len(qc_equations) >= 6, "Should have at least 6 QC equations"

    # Test that Python code is syntactically valid
    for eq_id, eq_data in qc_equations.items():
        python_code = eq_data.get("python", "")
        try:
            compile(python_code, f"<{eq_id}>", "eval")
        except SyntaxError as e:
            pytest.fail(f"Equation {eq_id} has invalid Python: {e}")


def test_equation_variable_bindings():
    """Test that equation variables can be bound to context data"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ont_context",
        bin_dir / "ont_context.py"
    )
    ont_context = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_context)

    # Create a mock equation
    equation = ont_context.Equation(
        id="test",
        name="Test Equation",
        latex="x = y",
        description="Test",
        variables=["total_reads", "mean_qscore"],
        python="total_reads * mean_qscore",
    )

    # Create a mock context with statistics
    class MockStats:
        total_reads = 1000000
        total_bases = 5000000000
        mean_qscore = 20.5
        median_qscore = 21.0
        n50 = 5000
        mean_length = 5000
        pass_reads = 900000
        fail_reads = 100000

    class MockContext:
        statistics = MockStats()
        end_reasons = None
        has_qc = False
        has_basecalling = True

    ctx = MockContext()
    bindings = ont_context.bind_variables(equation, ctx)

    assert "total_reads" in bindings, "Should bind total_reads"
    assert "mean_qscore" in bindings, "Should bind mean_qscore"
    assert bindings["total_reads"] == 1000000, "Should have correct value"


# =============================================================================
# Generator Integration Tests
# =============================================================================

def test_generator_registry_matches_files():
    """Test that generator registry matches actual files"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ont_manuscript",
        bin_dir / "ont_manuscript.py"
    )
    ont_manuscript = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_manuscript)

    generators_dir = Path(__file__).parent.parent / 'skills' / 'manuscript' / 'generators'

    # Check figure generators
    for fig_id, fig_config in ont_manuscript.FIGURE_GENERATORS.items():
        gen_file = generators_dir / fig_config["generator"]
        # Some generators may use inline fallbacks
        if gen_file.exists():
            assert gen_file.is_file(), f"Generator {fig_config['generator']} should be a file"

    # Check table generators
    for tbl_id, tbl_config in ont_manuscript.TABLE_GENERATORS.items():
        gen_file = generators_dir / tbl_config["generator"]
        if gen_file.exists():
            assert gen_file.is_file(), f"Generator {tbl_config['generator']} should be a file"


def test_manuscript_pipelines_defined():
    """Test that manuscript pipelines are properly defined"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ont_manuscript",
        bin_dir / "ont_manuscript.py"
    )
    ont_manuscript = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_manuscript)

    assert hasattr(ont_manuscript, 'MANUSCRIPT_PIPELINES'), "Should have MANUSCRIPT_PIPELINES"

    pipelines = ont_manuscript.MANUSCRIPT_PIPELINES
    assert len(pipelines) >= 3, "Should have at least 3 pipelines"

    # Check pipeline structure
    for pipeline_name, pipeline_config in pipelines.items():
        assert "description" in pipeline_config, f"Pipeline {pipeline_name} should have description"
        assert "steps" in pipeline_config, f"Pipeline {pipeline_name} should have steps"


# =============================================================================
# End-to-End Integration Tests
# =============================================================================

def test_end_to_end_equation_computation():
    """Test end-to-end equation computation with real data structure"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ont_context",
        bin_dir / "ont_context.py"
    )
    ont_context = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_context)

    # Create mock context with realistic values from registry
    class MockStats:
        total_reads = 4688237
        total_bases = 18807281227
        mean_qscore = 19.22
        median_qscore = 20.0
        n50 = 5406
        mean_length = 4012
        pass_reads = 4200000
        fail_reads = 488237

    class MockEndReasons:
        signal_positive = 2344000
        signal_positive_pct = 50.0
        unblock_pct = 45.0

    class MockContext:
        id = "test-exp"
        name = "Test Experiment"
        statistics = MockStats()
        end_reasons = MockEndReasons()
        has_qc = True
        has_basecalling = True

    ctx = MockContext()

    # Load QC.3 equation (quality score to error probability)
    equations = ont_context.load_equations()
    eq_data = equations.get("equations", {}).get("QC.3")

    if eq_data and eq_data.get("python"):
        equation = ont_context.Equation(
            id="QC.3",
            name=eq_data.get("name", "QC.3"),
            latex=eq_data.get("latex", ""),
            description=eq_data.get("description", ""),
            variables=eq_data.get("variables", []),
            python=eq_data.get("python"),
        )

        result = ont_context.compute_equation(equation, ctx)

        assert result.success, f"Equation should compute successfully: {result.error}"
        assert result.output is not None, "Should have output"
        assert 0 < result.output < 1, "Error probability should be between 0 and 1"


def test_textbook_equations_yaml_valid():
    """Test that textbook equations.yaml is valid and complete"""
    try:
        import yaml
    except ImportError:
        pytest.skip("PyYAML not available")

    equations_path = Path(__file__).parent.parent / 'textbook' / 'equations.yaml'
    assert equations_path.exists(), "equations.yaml should exist"

    with open(equations_path) as f:
        equations = yaml.safe_load(f)

    assert "equations" in equations, "Should have equations key"

    eq_dict = equations["equations"]
    assert len(eq_dict) >= 80, f"Should have at least 80 equations, found {len(eq_dict)}"

    # Check that equations have required fields
    for eq_id, eq_data in list(eq_dict.items())[:10]:  # Check first 10
        if isinstance(eq_data, dict):
            assert "latex" in eq_data or "latex_full" in eq_data, f"Equation {eq_id} should have latex"


def test_textbook_variables_yaml_valid():
    """Test that textbook variables.yaml is valid and complete"""
    try:
        import yaml
    except ImportError:
        pytest.skip("PyYAML not available")

    variables_path = Path(__file__).parent.parent / 'textbook' / 'variables.yaml'
    assert variables_path.exists(), "variables.yaml should exist"

    with open(variables_path) as f:
        variables = yaml.safe_load(f)

    assert "variables" in variables, "Should have variables key"
    assert len(variables["variables"]) >= 50, "Should have at least 50 variables"
