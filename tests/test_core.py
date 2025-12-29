"""Comprehensive tests for ONT Ecosystem"""

import sys
from pathlib import Path

# Add bin to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'bin'))


def test_skill_files_exist():
    """Test that all skill directories exist with proper structure"""
    skills_dir = Path(__file__).parent.parent / 'skills'
    expected_skills = [
        'ont-align',
        'ont-pipeline',
        'ont-experiments-v2',
        'end-reason',
        'dorado-bench-v2',
        'ont-monitor',
        'experiment-db'
    ]

    for skill_name in expected_skills:
        skill_dir = skills_dir / skill_name
        assert skill_dir.exists(), f"Missing skill directory: {skill_name}"
        # Check for either SKILL.md or scripts directory
        has_skill_md = (skill_dir / 'SKILL.md').exists()
        has_scripts = (skill_dir / 'scripts').exists()
        assert has_skill_md or has_scripts, f"{skill_name}: Missing SKILL.md or scripts/"


def test_skill_frontmatter():
    """Test that skill files have valid frontmatter"""
    import yaml
    import re
    
    skills_dir = Path(__file__).parent.parent / 'skills'
    
    for skill_dir in skills_dir.iterdir():
        if skill_dir.is_dir():
            skill_md = skill_dir / 'SKILL.md'
            if skill_md.exists():
                content = skill_md.read_text()
                match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
                assert match, f"{skill_dir.name}: No frontmatter"
                
                fm = yaml.safe_load(match.group(1))
                assert 'name' in fm, f"{skill_dir.name}: Missing name"
                assert 'description' in fm, f"{skill_dir.name}: Missing description"


def test_bin_scripts_exist():
    """Test that all bin scripts exist

    Architecture:
    - Orchestration & infrastructure scripts are authoritative in bin/
    - Analysis scripts are wrappers that import from skills/
    """
    bin_dir = Path(__file__).parent.parent / 'bin'
    expected_scripts = [
        # Authoritative orchestration & infrastructure
        'ont_experiments.py',    # Core orchestrator (authoritative)
        'experiment_db.py',      # Database functions (authoritative)
        'ont_registry.py',       # Permanent registry
        'ont_dashboard.py',      # Web interface
        'ont_config.py',         # Configuration management
        'ont_context.py',        # Experiment context
        'ont_integrate.py',      # Git integration
        'ont_manuscript.py',     # Manuscript pipelines
        'ont_endreason_qc.py',   # Enhanced QC visualization
        'ont_textbook_export.py', # Textbook export
        # Wrappers (import from skills/)
        'end_reason.py',         # → skills/end-reason/scripts/
        'dorado_basecall.py',    # → skills/dorado-bench-v2/scripts/
        'ont_align.py',          # → skills/ont-align/scripts/
        'ont_monitor.py',        # → skills/ont-monitor/scripts/
        'ont_pipeline.py',       # → skills/ont-pipeline/scripts/
        'calculate_resources.py', # → skills/dorado-bench-v2/scripts/
        'make_sbatch_from_cmdtxt.py', # → skills/dorado-bench-v2/scripts/
    ]

    for script in expected_scripts:
        script_path = bin_dir / script
        assert script_path.exists(), f"Missing script: {script}"


def test_bin_scripts_syntax():
    """Test that all bin scripts have valid Python syntax"""
    import py_compile
    
    bin_dir = Path(__file__).parent.parent / 'bin'
    
    for script in bin_dir.glob('*.py'):
        try:
            py_compile.compile(str(script), doraise=True)
        except py_compile.PyCompileError as e:
            assert False, f"Syntax error in {script.name}: {e}"


def test_example_pipelines_exist():
    """Test that example pipelines exist"""
    examples_dir = Path(__file__).parent.parent / 'examples' / 'pipelines'
    expected_pipelines = [
        'pharmaco-clinical.yaml',
        'qc-fast.yaml',
        'research-full.yaml',
    ]
    
    for pipeline in expected_pipelines:
        pipeline_path = examples_dir / pipeline
        assert pipeline_path.exists(), f"Missing pipeline: {pipeline}"


def test_example_pipelines_valid_yaml():
    """Test that example pipelines are valid YAML"""
    import yaml
    
    examples_dir = Path(__file__).parent.parent / 'examples' / 'pipelines'
    
    for pipeline_file in examples_dir.glob('*.yaml'):
        with open(pipeline_file) as f:
            try:
                data = yaml.safe_load(f)
                assert 'name' in data, f"{pipeline_file.name}: Missing name"
                assert 'steps' in data, f"{pipeline_file.name}: Missing steps"
            except yaml.YAMLError as e:
                assert False, f"Invalid YAML in {pipeline_file.name}: {e}"


def test_hpc_configs_exist():
    """Test that HPC config examples exist"""
    configs_dir = Path(__file__).parent.parent / 'examples' / 'configs'
    expected_configs = [
        'greatlakes.yaml',
        'armis2.yaml',
        'local.yaml',
    ]
    
    for config in expected_configs:
        config_path = configs_dir / config
        assert config_path.exists(), f"Missing config: {config}"


def test_edit_distance_basic():
    """Test basic edit distance computation"""
    try:
        import edlib
        
        # Exact match
        result = edlib.align("HELLO", "HELLO")
        assert result['editDistance'] == 0
        
        # Single substitution (G→T at position 3)
        result = edlib.align("ACGT", "ACTT")
        assert result['editDistance'] == 1

        # Two substitutions
        result = edlib.align("ACGT", "TCAT")
        assert result['editDistance'] == 2
        
        # Single insertion
        result = edlib.align("ABC", "ABCD")
        assert result['editDistance'] == 1
        
        # Single deletion
        result = edlib.align("ABCD", "ABC")
        assert result['editDistance'] == 1
        
    except ImportError:
        # edlib not installed, skip
        pass


def test_version():
    """Test version info"""
    lib_dir = Path(__file__).parent.parent / 'lib'
    sys.path.insert(0, str(lib_dir))

    # Import version
    import importlib.util
    spec = importlib.util.spec_from_file_location("lib", lib_dir / "__init__.py")
    lib = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lib)

    assert lib.__version__ == "3.0.0"
    assert len(lib.SKILL_VERSIONS) == 8  # Added manuscript skill


def test_dashboards_exist():
    """Test that dashboard JSX files exist"""
    dashboards_dir = Path(__file__).parent.parent / 'dashboards'

    # Should have at least one dashboard
    jsx_files = list(dashboards_dir.glob('*.jsx'))
    assert len(jsx_files) >= 1, "No dashboard files found"


def test_experiment_db_scripts_syntax():
    """Test that experiment-db scripts have valid Python syntax"""
    import py_compile

    scripts_dir = Path(__file__).parent.parent / 'skills' / 'experiment-db' / 'scripts'

    for script in scripts_dir.glob('*.py'):
        try:
            py_compile.compile(str(script), doraise=True)
        except py_compile.PyCompileError as e:
            assert False, f"Syntax error in {script.name}: {e}"


def test_experiment_registry_exists():
    """Test that experiment registry JSON exists and is valid"""
    import json

    registry_path = Path(__file__).parent.parent / 'data' / 'experiment_registry.json'
    assert registry_path.exists(), "Missing experiment_registry.json"

    with open(registry_path) as f:
        data = json.load(f)

    assert 'total_experiments' in data, "Missing total_experiments"
    assert 'total_reads' in data, "Missing total_reads"
    assert 'total_bases' in data, "Missing total_bases"
    assert 'experiments' in data, "Missing experiments list"
    assert 'end_reason_distribution' in data, "Missing end_reason_distribution"

    # Verify we have experiments
    assert data['total_experiments'] > 0, "No experiments in registry"
    assert len(data['experiments']) > 0, "Empty experiments list"


def test_experiment_db_functions():
    """Test experiment database utility functions"""
    scripts_dir = Path(__file__).parent.parent / 'skills' / 'experiment-db' / 'scripts'
    sys.path.insert(0, str(scripts_dir))

    # Import the module
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "experiment_db",
        scripts_dir / "experiment_db.py"
    )
    exp_db = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exp_db)

    # Test N50 calculation
    assert exp_db.calculate_n50([]) == 0
    assert exp_db.calculate_n50([100, 100, 100]) == 100
    assert exp_db.calculate_n50([1000, 100, 100, 100]) == 1000

    # Test that key functions exist
    assert hasattr(exp_db, 'find_experiments'), "Should have find_experiments function"
    assert hasattr(exp_db, 'build_experiment_database'), "Should have build_experiment_database function"
    assert hasattr(exp_db, 'sync_event_to_database'), "Should have sync_event_to_database function"


# =============================================================================
# Domain Memory Tests
# =============================================================================

def test_task_dataclass():
    """Test Task dataclass creation and serialization"""
    from datetime import datetime, timezone

    bin_dir = Path(__file__).parent.parent / 'bin'
    sys.path.insert(0, str(bin_dir))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ont_experiments",
        bin_dir / "ont_experiments.py"
    )
    ont_exp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_exp)

    now = datetime.now(timezone.utc).isoformat()
    task = ont_exp.Task(
        name="end_reasons",
        status="pending",
        description="QC analysis",
        created=now,
        updated=now
    )

    assert task.name == "end_reasons"
    assert task.status == "pending"
    assert task.attempts == 0
    assert task.error is None

    # Test to_dict
    d = task.to_dict()
    assert d['name'] == "end_reasons"
    assert d['status'] == "pending"

    # Test from_dict
    task2 = ont_exp.Task.from_dict(d)
    assert task2.name == task.name
    assert task2.status == task.status


def test_tasklist_dataclass():
    """Test TaskList dataclass creation and serialization"""
    from datetime import datetime, timezone

    bin_dir = Path(__file__).parent.parent / 'bin'
    sys.path.insert(0, str(bin_dir))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ont_experiments",
        bin_dir / "ont_experiments.py"
    )
    ont_exp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_exp)

    now = datetime.now(timezone.utc).isoformat()
    tasks = [
        ont_exp.Task(name="end_reasons", status="pending",
                     description="QC", created=now, updated=now),
        ont_exp.Task(name="basecalling", status="pending",
                     description="Basecall", created=now, updated=now),
    ]

    task_list = ont_exp.TaskList(
        experiment_id="exp-test123",
        tasks=tasks
    )

    assert task_list.experiment_id == "exp-test123"
    assert len(task_list.tasks) == 2

    # Test get_task
    task = task_list.get_task("end_reasons")
    assert task is not None
    assert task.name == "end_reasons"

    task = task_list.get_task("nonexistent")
    assert task is None

    # Test update_task
    task_list.update_task("end_reasons", "passing")
    task = task_list.get_task("end_reasons")
    assert task.status == "passing"

    # Test to_dict / from_dict
    d = task_list.to_dict()
    assert d['experiment_id'] == "exp-test123"
    assert len(d['tasks']) == 2

    task_list2 = ont_exp.TaskList.from_dict(d)
    assert task_list2.experiment_id == task_list.experiment_id
    assert len(task_list2.tasks) == 2


def test_domain_memory_files_structure():
    """Test that domain memory creates proper directory structure"""
    import tempfile
    import shutil
    from datetime import datetime, timezone

    bin_dir = Path(__file__).parent.parent / 'bin'
    sys.path.insert(0, str(bin_dir))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ont_experiments",
        bin_dir / "ont_experiments.py"
    )
    ont_exp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_exp)

    # Create a temporary registry directory
    temp_dir = Path(tempfile.mkdtemp())
    try:
        # Override the EXPERIMENTS_DIR for testing
        original_experiments_dir = ont_exp.EXPERIMENTS_DIR
        ont_exp.EXPERIMENTS_DIR = temp_dir / "experiments"

        # Test get_experiment_dir creates directory
        exp_dir = ont_exp.get_experiment_dir("exp-test123")
        assert exp_dir.exists()
        assert exp_dir.is_dir()

        # Test initialize_tasks creates TaskList
        now = datetime.now(timezone.utc).isoformat()

        # Create mock experiment
        mock_exp = ont_exp.ExperimentMetadata(
            id="exp-test123",
            name="Test Experiment",
            location="/test/path"
        )

        task_list = ont_exp.initialize_tasks(mock_exp)
        assert task_list.experiment_id == "exp-test123"
        assert len(task_list.tasks) == 5  # v2.0: end_reasons, signal_qc, basecalling, alignment, haplotype_calling

        # Test save_tasks and load_tasks
        ont_exp.save_tasks(task_list)
        tasks_file = exp_dir / "tasks.yaml"
        assert tasks_file.exists()

        loaded_tasks = ont_exp.load_tasks("exp-test123")
        assert loaded_tasks is not None
        assert loaded_tasks.experiment_id == "exp-test123"
        assert len(loaded_tasks.tasks) == 5  # v2.0 task count

        # Test initialize_progress
        ont_exp.initialize_progress(mock_exp)
        progress_file = exp_dir / "PROGRESS.md"
        assert progress_file.exists()
        content = progress_file.read_text()
        assert "Test Experiment" in content
        assert "exp-test123" in content

        # Test append_progress
        ont_exp.append_progress("exp-test123", "- Test entry\n- Another line", "end_reasons")
        content = progress_file.read_text()
        assert "Test entry" in content
        assert "end_reasons" in content

        # Restore original
        ont_exp.EXPERIMENTS_DIR = original_experiments_dir

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


# =============================================================================
# Math Registry Tests
# =============================================================================

def test_load_math_registry():
    """Test loading the math equations registry"""
    bin_dir = Path(__file__).parent.parent / 'bin'
    sys.path.insert(0, str(bin_dir))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ont_experiments",
        bin_dir / "ont_experiments.py"
    )
    ont_exp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_exp)

    registry = ont_exp.load_math_registry()
    assert 'equations' in registry, "Registry should have 'equations' key"

    equations = registry.get('equations', {})
    # Should have equations from the full database
    assert len(equations) > 0, "Should have at least some equations"

    # Check for known equation
    if '5.1' in equations:
        eq = equations['5.1']
        assert 'title' in eq, "Equation should have title"
        assert 'latex' in eq, "Equation should have latex"


def test_load_variables_registry():
    """Test loading the variables registry"""
    bin_dir = Path(__file__).parent.parent / 'bin'
    sys.path.insert(0, str(bin_dir))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ont_experiments",
        bin_dir / "ont_experiments.py"
    )
    ont_exp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_exp)

    registry = ont_exp.load_variables_registry()
    assert 'variables' in registry, "Registry should have 'variables' key"

    variables = registry.get('variables', {})
    assert len(variables) > 0, "Should have at least some variables"

    # Check for known variable
    if 'pi' in variables:
        var = variables['pi']
        assert 'name' in var, "Variable should have name"
        assert 'domain' in var, "Variable should have domain"


def test_load_pipeline_stages():
    """Test loading the pipeline stages registry"""
    bin_dir = Path(__file__).parent.parent / 'bin'
    sys.path.insert(0, str(bin_dir))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ont_experiments",
        bin_dir / "ont_experiments.py"
    )
    ont_exp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_exp)

    data = ont_exp.load_pipeline_stages()
    assert 'stages' in data, "Should have 'stages' key"

    stages = data.get('stages', [])
    assert len(stages) == 9, "Should have 9 pipeline stages"

    # Check for known stages
    stage_symbols = [s.get('symbol') for s in stages]
    assert 'h' in stage_symbols, "Should have haplotype stage"
    assert 'r' in stage_symbols, "Should have basecalling stage"
    assert 'σ' in stage_symbols, "Should have signal stage"


def test_registry_path():
    """Test that registry path is correctly computed"""
    bin_dir = Path(__file__).parent.parent / 'bin'
    sys.path.insert(0, str(bin_dir))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ont_experiments",
        bin_dir / "ont_experiments.py"
    )
    ont_exp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_exp)

    registry_path = ont_exp.get_registry_path()
    assert registry_path.exists(), "Registry path should exist"
    assert (registry_path / "textbook").exists(), "Textbook registry should exist"
    assert (registry_path / "pipeline").exists(), "Pipeline registry should exist"


def test_load_schema():
    """Test that JSON schemas can be loaded"""
    import json
    bin_dir = Path(__file__).parent.parent / 'bin'
    sys.path.insert(0, str(bin_dir))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ont_experiments",
        bin_dir / "ont_experiments.py"
    )
    ont_exp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_exp)

    # Test loading each schema
    for schema_name in ['equation', 'pipeline_stage', 'experiment', 'task']:
        schema = ont_exp.load_schema(schema_name)
        assert schema is not None, f"Should load {schema_name} schema"
        assert '$schema' in schema, f"{schema_name} should have $schema"
        assert 'type' in schema, f"{schema_name} should have type"


def test_validate_equation():
    """Test equation validation against schema"""
    bin_dir = Path(__file__).parent.parent / 'bin'
    sys.path.insert(0, str(bin_dir))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ont_experiments",
        bin_dir / "ont_experiments.py"
    )
    ont_exp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_exp)

    # Valid equation
    valid_eq = {
        "name": "Test Equation",
        "latex": "E = mc^2",
        "description": "Energy-mass equivalence"
    }
    errors = ont_exp.validate_equation(valid_eq, "test_eq")
    assert len(errors) == 0, f"Valid equation should pass: {errors}"

    # Invalid equation (missing required field)
    invalid_eq = {
        "name": "Missing latex"
    }
    errors = ont_exp.validate_equation(invalid_eq, "test_invalid")
    assert len(errors) > 0, "Invalid equation should fail"


def test_validate_pipeline_stage():
    """Test pipeline stage validation against schema"""
    bin_dir = Path(__file__).parent.parent / 'bin'
    sys.path.insert(0, str(bin_dir))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ont_experiments",
        bin_dir / "ont_experiments.py"
    )
    ont_exp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_exp)

    # Valid stage
    valid_stage = {
        "id": "h",
        "name": "Haplotype Selection",
        "description": "Selection of haplotype hypotheses"
    }
    errors = ont_exp.validate_pipeline_stage(valid_stage, "h")
    assert len(errors) == 0, f"Valid stage should pass: {errors}"


def test_validate_registry():
    """Test full registry validation"""
    bin_dir = Path(__file__).parent.parent / 'bin'
    sys.path.insert(0, str(bin_dir))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ont_experiments",
        bin_dir / "ont_experiments.py"
    )
    ont_exp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_exp)

    # Validate equations
    results = ont_exp.validate_registry("equations")
    assert "equations" in results, "Should have equations results"

    # Validate stages
    results = ont_exp.validate_registry("stages")
    assert "stages" in results, "Should have stages results"


def test_schemas_directory_exists():
    """Test that schemas directory exists with all required files"""
    schemas_dir = Path(__file__).parent.parent / 'registry' / 'schemas'
    assert schemas_dir.exists(), "Schemas directory should exist"

    expected_schemas = ['equation.json', 'pipeline_stage.json', 'experiment.json', 'task.json', 'task_list.json']
    for schema_name in expected_schemas:
        schema_file = schemas_dir / schema_name
        assert schema_file.exists(), f"Missing schema: {schema_name}"


# =============================================================================
# Equation Execution Tests
# =============================================================================

def test_load_equations():
    """Test loading equations from textbook/equations.yaml"""
    bin_dir = Path(__file__).parent.parent / 'bin'
    sys.path.insert(0, str(bin_dir))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ont_context",
        bin_dir / "ont_context.py"
    )
    ont_context = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_context)

    equations = ont_context.load_equations()
    assert "equations" in equations, "Should have equations key"
    assert len(equations["equations"]) > 0, "Should have equations loaded"


def test_computable_equations_exist():
    """Test that QC equations with Python implementations exist"""
    bin_dir = Path(__file__).parent.parent / 'bin'
    sys.path.insert(0, str(bin_dir))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ont_context",
        bin_dir / "ont_context.py"
    )
    ont_context = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_context)

    equations = ont_context.load_equations()
    eq_dict = equations.get("equations", {})

    # Check for QC equations with Python implementations
    qc_equations = [eq_id for eq_id in eq_dict.keys() if eq_id.startswith("QC.")]
    assert len(qc_equations) >= 6, f"Should have at least 6 QC equations, found {len(qc_equations)}"

    # Check that they have Python implementations
    for eq_id in qc_equations:
        eq_data = eq_dict[eq_id]
        assert "python" in eq_data, f"QC equation {eq_id} should have Python implementation"


# =============================================================================
# Generator Tests
# =============================================================================

def test_figure_generators_exist():
    """Test that figure generator scripts exist"""
    generators_dir = Path(__file__).parent.parent / 'skills' / 'manuscript' / 'generators'
    assert generators_dir.exists(), "Generators directory should exist"

    expected_generators = [
        'gen_end_reason_kde.py',
        'gen_qc_summary_table.py',
        'gen_quality_distribution.py',
        'gen_read_length_distribution.py',
        'gen_comparison_plot.py',
        'gen_comparison_table.py',
        'gen_basecalling_table.py',
    ]

    for gen_name in expected_generators:
        gen_file = generators_dir / gen_name
        assert gen_file.exists(), f"Missing generator: {gen_name}"


def test_manuscript_registries():
    """Test that manuscript figure and table registries are populated"""
    bin_dir = Path(__file__).parent.parent / 'bin'
    sys.path.insert(0, str(bin_dir))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ont_manuscript",
        bin_dir / "ont_manuscript.py"
    )
    ont_manuscript = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ont_manuscript)

    # Check figure generators registry
    assert hasattr(ont_manuscript, 'FIGURE_GENERATORS'), "Should have FIGURE_GENERATORS"
    assert len(ont_manuscript.FIGURE_GENERATORS) >= 5, "Should have at least 5 figure types"

    # Check table generators registry
    assert hasattr(ont_manuscript, 'TABLE_GENERATORS'), "Should have TABLE_GENERATORS"
    assert len(ont_manuscript.TABLE_GENERATORS) >= 4, "Should have at least 4 table types"
