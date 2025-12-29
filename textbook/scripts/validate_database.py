#!/usr/bin/env python3
"""
Database Validation Script
Performs comprehensive quality checks on equation and variable databases
"""

import yaml
import sys
from collections import defaultdict
from typing import Dict, List, Set, Tuple


class DatabaseValidator:
    def __init__(self, eq_file='equations.yaml', var_file='variables.yaml'):
        """Load databases"""
        self.eq_file = eq_file
        self.var_file = var_file

        with open(eq_file, 'r') as f:
            self.eq_data = yaml.safe_load(f)
        with open(var_file, 'r') as f:
            self.var_data = yaml.safe_load(f)

        self.equations = self.eq_data['equations']
        self.variables = self.var_data['variables']

        self.errors = []
        self.warnings = []
        self.info = []

    def log_error(self, message: str):
        """Log an error"""
        self.errors.append(f"❌ ERROR: {message}")

    def log_warning(self, message: str):
        """Log a warning"""
        self.warnings.append(f"⚠️  WARNING: {message}")

    def log_info(self, message: str):
        """Log an info message"""
        self.info.append(f"ℹ️  INFO: {message}")

    def validate_yaml_structure(self) -> bool:
        """Validate basic YAML structure"""
        print("\n" + "="*70)
        print("VALIDATING YAML STRUCTURE")
        print("="*70)

        try:
            # Check equations.yaml structure
            if 'equations' not in self.eq_data:
                self.log_error("equations.yaml missing 'equations' key")
                return False

            if not isinstance(self.eq_data['equations'], dict):
                self.log_error("'equations' must be a dictionary")
                return False

            # Check variables.yaml structure
            if 'variables' not in self.var_data:
                self.log_error("variables.yaml missing 'variables' key")
                return False

            if not isinstance(self.var_data['variables'], dict):
                self.log_error("'variables' must be a dictionary")
                return False

            print("✅ YAML structure valid")
            return True

        except Exception as e:
            self.log_error(f"YAML parsing error: {e}")
            return False

    def validate_equation_fields(self) -> bool:
        """Validate required fields in equations"""
        print("\n" + "="*70)
        print("VALIDATING EQUATION FIELDS")
        print("="*70)

        required_fields = {
            'id', 'chapter', 'index', 'title', 'latex', 'latex_full',
            'type', 'category', 'description', 'physical_meaning',
            'assumptions', 'variables', 'related_equations', 'examples',
            'importance', 'difficulty', 'tags'
        }

        all_valid = True

        for eq_id, eq_data in self.equations.items():
            missing = required_fields - set(eq_data.keys())
            if missing:
                self.log_error(f"Equation {eq_id} missing fields: {missing}")
                all_valid = False

            # Validate ID matches key
            if eq_data.get('id') != eq_id:
                self.log_error(f"Equation {eq_id}: ID mismatch (key={eq_id}, id field={eq_data.get('id')})")
                all_valid = False

            # Validate chapter is integer
            if not isinstance(eq_data.get('chapter'), int):
                self.log_error(f"Equation {eq_id}: chapter must be integer")
                all_valid = False

            # Validate latex_full exists and is non-empty
            if not eq_data.get('latex_full'):
                self.log_error(f"Equation {eq_id}: latex_full is empty")
                all_valid = False

        if all_valid:
            print(f"✅ All {len(self.equations)} equations have required fields")

        return all_valid

    def validate_variable_fields(self) -> bool:
        """Validate required fields in variables"""
        print("\n" + "="*70)
        print("VALIDATING VARIABLE FIELDS")
        print("="*70)

        required_fields = {
            'symbol', 'symbol_display', 'name', 'description',
            'physical_meaning', 'units', 'domain', 'typical_range',
            'measurement_methods', 'determination', 'examples',
            'related_variables', 'appears_in_equations', 'importance',
            'difficulty', 'first_chapter', 'tags'
        }

        all_valid = True

        for var_id, var_data in self.variables.items():
            missing = required_fields - set(var_data.keys())
            if missing:
                self.log_error(f"Variable {var_id} missing fields: {missing}")
                all_valid = False

            # Validate symbol matches key
            if var_data.get('symbol') != var_id:
                self.log_error(f"Variable {var_id}: symbol mismatch (key={var_id}, symbol field={var_data.get('symbol')})")
                all_valid = False

        if all_valid:
            print(f"✅ All {len(self.variables)} variables have required fields")

        return all_valid

    def validate_cross_references(self) -> bool:
        """Validate cross-references between equations"""
        print("\n" + "="*70)
        print("VALIDATING EQUATION CROSS-REFERENCES")
        print("="*70)

        all_valid = True

        for eq_id, eq_data in self.equations.items():
            related = eq_data.get('related_equations', [])
            for related_id in related:
                if related_id not in self.equations:
                    self.log_error(f"Equation {eq_id} references non-existent equation {related_id}")
                    all_valid = False

        if all_valid:
            print("✅ All equation cross-references are valid")
        else:
            print(f"❌ Found {len([e for e in self.errors if 'references non-existent equation' in e])} invalid references")

        return all_valid

    def validate_variable_references(self) -> bool:
        """Validate variable references in equations"""
        print("\n" + "="*70)
        print("VALIDATING VARIABLE REFERENCES")
        print("="*70)

        all_valid = True
        undefined_vars = set()

        for eq_id, eq_data in self.equations.items():
            vars_used = eq_data.get('variables', [])
            for var in vars_used:
                if var not in self.variables:
                    undefined_vars.add(var)
                    self.log_warning(f"Equation {eq_id} references undefined variable '{var}'")
                    all_valid = False

        if undefined_vars:
            print(f"\n⚠️  Found {len(undefined_vars)} undefined variables:")
            for var in sorted(undefined_vars):
                print(f"    - {var}")
            self.log_info(f"These may be intentional (e.g., generic symbols) or need definition")

        if all_valid:
            print("✅ All variable references are defined")

        return all_valid

    def validate_equation_usage(self) -> bool:
        """Validate that appears_in_equations is accurate"""
        print("\n" + "="*70)
        print("VALIDATING VARIABLE USAGE CLAIMS")
        print("="*70)

        all_valid = True

        # Build actual usage from equations
        actual_usage = defaultdict(set)
        for eq_id, eq_data in self.equations.items():
            for var in eq_data.get('variables', []):
                actual_usage[var].add(eq_id)

        # Check claimed usage
        for var_id, var_data in self.variables.items():
            # Handle both string list and dict list formats
            appears_in = var_data.get('appears_in_equations', [])
            if appears_in and isinstance(appears_in[0], dict):
                # Extract eq_id from dict format
                claimed = set(item['eq_id'] for item in appears_in if isinstance(item, dict))
            else:
                # Simple string list
                claimed = set(appears_in)

            actual = actual_usage.get(var_id, set())

            missing = actual - claimed
            extra = claimed - actual

            if missing:
                self.log_warning(f"Variable {var_id} used in {missing} but not listed in appears_in_equations")
                all_valid = False

            if extra:
                self.log_warning(f"Variable {var_id} claims to appear in {extra} but doesn't")
                all_valid = False

        if all_valid:
            print("✅ All variable usage claims are accurate")

        return all_valid

    def check_orphaned_variables(self):
        """Check for variables not used in any equation"""
        print("\n" + "="*70)
        print("CHECKING FOR ORPHANED VARIABLES")
        print("="*70)

        used_vars = set()
        for eq_data in self.equations.values():
            used_vars.update(eq_data.get('variables', []))

        orphaned = set(self.variables.keys()) - used_vars

        if orphaned:
            print(f"\n⚠️  Found {len(orphaned)} variables not used in any equation:")
            for var in sorted(orphaned):
                var_name = self.variables[var].get('name', 'Unknown')
                print(f"    - {var} ({var_name})")
            self.log_info("These may be defined for future use")
        else:
            print("✅ All variables are used in at least one equation")

    def check_isolated_equations(self):
        """Check for equations with no related equations"""
        print("\n" + "="*70)
        print("CHECKING FOR ISOLATED EQUATIONS")
        print("="*70)

        isolated = []
        for eq_id, eq_data in self.equations.items():
            related = eq_data.get('related_equations', [])

            # Also check if any other equation references this one
            referenced_by = [
                other_id for other_id, other_data in self.equations.items()
                if eq_id in other_data.get('related_equations', [])
            ]

            if not related and not referenced_by:
                isolated.append(eq_id)

        if isolated:
            print(f"\nℹ️  Found {len(isolated)} isolated equations (no cross-references):")
            for eq_id in sorted(isolated):
                eq_title = self.equations[eq_id].get('title', 'Untitled')
                print(f"    - {eq_id}: {eq_title}")
            self.log_info("Isolated equations may be self-contained or need linking")
        else:
            print("✅ All equations have at least one cross-reference")

    def check_difficulty_distribution(self):
        """Check distribution of difficulty levels"""
        print("\n" + "="*70)
        print("DIFFICULTY DISTRIBUTION ANALYSIS")
        print("="*70)

        eq_difficulty = defaultdict(int)
        var_difficulty = defaultdict(int)

        for eq_data in self.equations.values():
            diff = eq_data.get('difficulty', 'unknown')
            eq_difficulty[diff] += 1

        for var_data in self.variables.values():
            diff = var_data.get('difficulty', 'unknown')
            var_difficulty[diff] += 1

        print("\nEquations by difficulty:")
        for diff in ['basic', 'intermediate', 'advanced', 'hard', 'unknown']:
            count = eq_difficulty.get(diff, 0)
            if count > 0:
                pct = 100 * count / len(self.equations)
                print(f"    {diff:15s}: {count:3d} ({pct:5.1f}%)")

        print("\nVariables by difficulty:")
        for diff in ['basic', 'intermediate', 'advanced', 'hard', 'unknown']:
            count = var_difficulty.get(diff, 0)
            if count > 0:
                pct = 100 * count / len(self.variables)
                print(f"    {diff:15s}: {count:3d} ({pct:5.1f}%)")

    def check_importance_distribution(self):
        """Check distribution of importance levels"""
        print("\n" + "="*70)
        print("IMPORTANCE DISTRIBUTION ANALYSIS")
        print("="*70)

        eq_importance = defaultdict(int)
        var_importance = defaultdict(int)

        for eq_data in self.equations.values():
            imp = eq_data.get('importance', 'unknown')
            eq_importance[imp] += 1

        for var_data in self.variables.values():
            imp = var_data.get('importance', 'unknown')
            var_importance[imp] += 1

        print("\nEquations by importance:")
        for imp in ['critical', 'high', 'medium', 'low', 'unknown']:
            count = eq_importance.get(imp, 0)
            if count > 0:
                pct = 100 * count / len(self.equations)
                print(f"    {imp:15s}: {count:3d} ({pct:5.1f}%)")

        print("\nVariables by importance:")
        for imp in ['critical', 'high', 'medium', 'low', 'unknown']:
            count = var_importance.get(imp, 0)
            if count > 0:
                pct = 100 * count / len(self.variables)
                print(f"    {imp:15s}: {count:3d} ({pct:5.1f}%)")

    def generate_report(self):
        """Generate final validation report"""
        print("\n" + "="*70)
        print("VALIDATION REPORT SUMMARY")
        print("="*70)

        print(f"\nDatabase files:")
        print(f"  Equations: {self.eq_file} ({len(self.equations)} entries)")
        print(f"  Variables: {self.var_file} ({len(self.variables)} entries)")

        print(f"\nValidation results:")
        print(f"  Errors:   {len(self.errors)}")
        print(f"  Warnings: {len(self.warnings)}")
        print(f"  Info:     {len(self.info)}")

        if self.errors:
            print("\n" + "="*70)
            print("ERRORS FOUND")
            print("="*70)
            for error in self.errors:
                print(error)

        if self.warnings:
            print("\n" + "="*70)
            print("WARNINGS")
            print("="*70)
            for warning in self.warnings:
                print(warning)

        if self.info:
            print("\n" + "="*70)
            print("INFORMATION")
            print("="*70)
            for info in self.info:
                print(info)

        print("\n" + "="*70)
        if len(self.errors) == 0:
            print("✅ VALIDATION PASSED - Database is valid")
            print("="*70)
            return True
        else:
            print("❌ VALIDATION FAILED - Please fix errors above")
            print("="*70)
            return False

    def run_all_validations(self) -> bool:
        """Run all validation checks"""
        checks = [
            self.validate_yaml_structure(),
            self.validate_equation_fields(),
            self.validate_variable_fields(),
            self.validate_cross_references(),
            self.validate_variable_references(),
            self.validate_equation_usage(),
        ]

        # Additional analysis (non-blocking)
        self.check_orphaned_variables()
        self.check_isolated_equations()
        self.check_difficulty_distribution()
        self.check_importance_distribution()

        # Generate report
        return self.generate_report()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Validate equation and variable databases',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--equations', default='equations.yaml',
                       help='Path to equations.yaml (default: equations.yaml)')
    parser.add_argument('--variables', default='variables.yaml',
                       help='Path to variables.yaml (default: variables.yaml)')
    parser.add_argument('--strict', action='store_true',
                       help='Treat warnings as errors')

    args = parser.parse_args()

    validator = DatabaseValidator(args.equations, args.variables)
    passed = validator.run_all_validations()

    if args.strict and len(validator.warnings) > 0:
        print("\n⚠️  Strict mode: Warnings treated as errors")
        sys.exit(1)

    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
