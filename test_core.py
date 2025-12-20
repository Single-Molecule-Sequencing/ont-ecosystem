"""Basic tests for ONT Ecosystem"""

import sys
from pathlib import Path

# Add bin to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'bin'))


def test_ont_experiments_import():
    """Test ont_experiments module imports"""
    import ont_experiments
    assert hasattr(ont_experiments, 'ExperimentRegistry')


def test_ont_align_import():
    """Test ont_align module imports"""
    import ont_align
    assert hasattr(ont_align, 'compute_edit_distance')


def test_ont_pipeline_import():
    """Test ont_pipeline module imports"""
    import ont_pipeline
    assert hasattr(ont_pipeline, 'Pipeline')


def test_edit_distance_basic():
    """Test basic edit distance computation"""
    try:
        import edlib
        result = edlib.align("ACGT", "ACTT")
        assert result['editDistance'] == 2
    except ImportError:
        # edlib not installed, skip
        pass


def test_skill_files_exist():
    """Test that all skill SKILL.md files exist"""
    skills_dir = Path(__file__).parent.parent / 'skills'
    expected_skills = ['ont-align', 'ont-pipeline', 'ont-experiments-v2']
    
    for skill_name in expected_skills:
        skill_md = skills_dir / skill_name / 'SKILL.md'
        assert skill_md.exists(), f"Missing SKILL.md for {skill_name}"


def test_skill_frontmatter():
    """Test that skill files have valid frontmatter"""
    import yaml
    import re
    
    skills_dir = Path(__file__).parent.parent / 'skills'
    
    for skill_dir in skills_dir.iterdir():
        if skill_dir.is_dir() and not skill_dir.name.endswith('.skill'):
            skill_md = skill_dir / 'SKILL.md'
            if skill_md.exists():
                content = skill_md.read_text()
                match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
                assert match, f"{skill_dir.name}: No frontmatter"
                
                fm = yaml.safe_load(match.group(1))
                assert 'name' in fm, f"{skill_dir.name}: Missing name"
                assert 'description' in fm, f"{skill_dir.name}: Missing description"
