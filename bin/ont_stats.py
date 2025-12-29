#!/usr/bin/env python3
"""
ONT Ecosystem Statistics - Quick overview of the ecosystem state

Usage:
    ont_stats.py              # Full stats
    ont_stats.py --json       # JSON output
    ont_stats.py --brief      # One-line summary
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add paths
bin_dir = Path(__file__).parent
lib_dir = bin_dir.parent / 'lib'
sys.path.insert(0, str(bin_dir))
sys.path.insert(0, str(lib_dir.parent))

try:
    from lib import __version__, SKILL_VERSIONS
except ImportError:
    # Fallback: read version directly
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("lib", lib_dir / "__init__.py")
        lib = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lib)
        __version__ = lib.__version__
        SKILL_VERSIONS = lib.SKILL_VERSIONS
    except Exception:
        __version__ = "3.0.0"
        SKILL_VERSIONS = {}


def get_experiment_stats():
    """Get experiment registry statistics"""
    registry_path = bin_dir.parent / 'data' / 'experiment_registry.json'
    if not registry_path.exists():
        return None

    with open(registry_path) as f:
        registry = json.load(f)

    return {
        "total_experiments": registry.get("total_experiments", 0),
        "total_reads": registry.get("total_reads", 0),
        "total_bases": registry.get("total_bases", 0),
    }


def get_equation_stats():
    """Get equation statistics"""
    try:
        from ont_context import load_equations
        equations = load_equations()
        eq_dict = equations.get("equations", {})
        computable = [
            eq_id for eq_id, eq in eq_dict.items()
            if isinstance(eq, dict) and eq.get("python")
        ]
        return {
            "total_equations": len(eq_dict),
            "computable_equations": len(computable),
        }
    except Exception:
        return None


def get_generator_stats():
    """Get generator statistics"""
    generators_dir = bin_dir.parent / 'skills' / 'manuscript' / 'generators'
    if not generators_dir.exists():
        return None

    generators = list(generators_dir.glob('gen_*.py'))
    return {
        "total_generators": len(generators),
        "figure_generators": len([g for g in generators if 'table' not in g.name]),
        "table_generators": len([g for g in generators if 'table' in g.name]),
    }


def get_skill_stats():
    """Get skill statistics"""
    skills_dir = bin_dir.parent / 'skills'
    if not skills_dir.exists():
        return None

    skills = [d for d in skills_dir.iterdir() if d.is_dir() and (d / 'SKILL.md').exists()]
    return {
        "total_skills": len(skills),
        "skill_names": [s.name for s in skills],
    }


def get_test_stats():
    """Get test statistics"""
    tests_dir = bin_dir.parent / 'tests'
    if not tests_dir.exists():
        return None

    test_files = list(tests_dir.glob('test_*.py'))

    # Count test functions
    total_tests = 0
    for tf in test_files:
        content = tf.read_text()
        total_tests += content.count('def test_')

    return {
        "test_files": len(test_files),
        "total_tests": total_tests,
    }


def get_textbook_stats():
    """Get textbook statistics"""
    textbook_dir = bin_dir.parent / 'textbook'
    if not textbook_dir.exists():
        return None

    equations_yaml = textbook_dir / 'equations.yaml'
    variables_yaml = textbook_dir / 'variables.yaml'

    stats = {}
    if equations_yaml.exists():
        stats["equations_yaml_lines"] = len(equations_yaml.read_text().splitlines())
    if variables_yaml.exists():
        stats["variables_yaml_lines"] = len(variables_yaml.read_text().splitlines())

    chapters_dir = textbook_dir / 'src' / 'chapters'
    if chapters_dir.exists():
        stats["chapter_files"] = len(list(chapters_dir.glob('*.tex')))

    return stats if stats else None


def format_number(n):
    """Format large numbers with suffixes"""
    if n >= 1e12:
        return f"{n/1e12:.1f}T"
    elif n >= 1e9:
        return f"{n/1e9:.1f}G"
    elif n >= 1e6:
        return f"{n/1e6:.1f}M"
    elif n >= 1e3:
        return f"{n/1e3:.1f}K"
    return str(n)


def print_stats(stats, brief=False):
    """Print statistics in human-readable format"""
    if brief:
        exp = stats.get("experiments", {})
        eq = stats.get("equations", {})
        gen = stats.get("generators", {})
        tests = stats.get("tests", {})
        print(f"ONT Ecosystem v{stats['version']}: "
              f"{exp.get('total_experiments', 0)} experiments, "
              f"{format_number(exp.get('total_reads', 0))} reads, "
              f"{eq.get('total_equations', 0)} equations ({eq.get('computable_equations', 0)} computable), "
              f"{gen.get('total_generators', 0)} generators, "
              f"{tests.get('total_tests', 0)} tests")
        return

    print("=" * 60)
    print(f"  ONT Ecosystem v{stats['version']}")
    print("=" * 60)
    print()

    # Experiments
    exp = stats.get("experiments")
    if exp:
        print("EXPERIMENTS")
        print(f"  Total experiments:  {exp['total_experiments']:,}")
        print(f"  Total reads:        {format_number(exp['total_reads'])} ({exp['total_reads']:,})")
        print(f"  Total bases:        {format_number(exp['total_bases'])} ({exp['total_bases']:,})")
        print()

    # Equations
    eq = stats.get("equations")
    if eq:
        print("EQUATIONS")
        print(f"  Total equations:    {eq['total_equations']}")
        print(f"  Computable (Python): {eq['computable_equations']}")
        print()

    # Generators
    gen = stats.get("generators")
    if gen:
        print("GENERATORS")
        print(f"  Figure generators:  {gen['figure_generators']}")
        print(f"  Table generators:   {gen['table_generators']}")
        print(f"  Total:              {gen['total_generators']}")
        print()

    # Skills
    skills = stats.get("skills")
    if skills:
        print("SKILLS")
        print(f"  Total skills:       {skills['total_skills']}")
        print(f"  Names:              {', '.join(skills['skill_names'])}")
        print()

    # Tests
    tests = stats.get("tests")
    if tests:
        print("TESTS")
        print(f"  Test files:         {tests['test_files']}")
        print(f"  Total tests:        {tests['total_tests']}")
        print()

    # Textbook
    tb = stats.get("textbook")
    if tb:
        print("TEXTBOOK")
        if "equations_yaml_lines" in tb:
            print(f"  equations.yaml:     {tb['equations_yaml_lines']:,} lines")
        if "variables_yaml_lines" in tb:
            print(f"  variables.yaml:     {tb['variables_yaml_lines']:,} lines")
        if "chapter_files" in tb:
            print(f"  Chapter files:      {tb['chapter_files']}")
        print()

    print("=" * 60)
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="ONT Ecosystem Statistics",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--brief", action="store_true", help="One-line summary")
    args = parser.parse_args()

    # Collect all stats
    stats = {
        "version": __version__,
        "timestamp": datetime.now().isoformat(),
        "experiments": get_experiment_stats(),
        "equations": get_equation_stats(),
        "generators": get_generator_stats(),
        "skills": get_skill_stats(),
        "tests": get_test_stats(),
        "textbook": get_textbook_stats(),
    }

    if args.json:
        print(json.dumps(stats, indent=2))
    else:
        print_stats(stats, brief=args.brief)


if __name__ == "__main__":
    main()
