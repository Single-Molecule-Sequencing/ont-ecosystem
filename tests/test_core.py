"""Comprehensive tests for ONT Ecosystem"""

import sys
from pathlib import Path

# Add bin to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'bin'))


def test_skill_files_exist():
    """Test that all skill SKILL.md files exist"""
    skills_dir = Path(__file__).parent.parent / 'skills'
    expected_skills = [
        'ont-align', 
        'ont-pipeline', 
        'ont-experiments-v2',
        'end-reason',
        'dorado-bench-v2',
        'ont-monitor'
    ]
    
    for skill_name in expected_skills:
        skill_md = skills_dir / skill_name / 'SKILL.md'
        assert skill_md.exists(), f"Missing SKILL.md for {skill_name}"


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
    """Test that all bin scripts exist"""
    bin_dir = Path(__file__).parent.parent / 'bin'
    expected_scripts = [
        'ont_experiments.py',
        'ont_align.py',
        'ont_pipeline.py',
        'end_reason.py',
        'ont_monitor.py',
        'dorado_basecall.py',
        'ont_registry.py',
        'ont_dashboard.py',
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
        
        # Single substitution
        result = edlib.align("ACGT", "ACTT")
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
    
    assert lib.__version__ == "2.1.0"
    assert len(lib.SKILL_VERSIONS) == 6


def test_dashboards_exist():
    """Test that dashboard JSX files exist"""
    dashboards_dir = Path(__file__).parent.parent / 'dashboards'
    
    # Should have at least one dashboard
    jsx_files = list(dashboards_dir.glob('*.jsx'))
    assert len(jsx_files) >= 1, "No dashboard files found"
