#!/usr/bin/env python3
"""
Extract Variables from LaTeX Source Files
==========================================

Scans chapter files to extract variable definitions and metadata.

This script:
1. Identifies variable symbols in equations
2. Extracts variable descriptions from surrounding text
3. Identifies units, ranges, and physical meanings
4. Generates initial variable database entries in YAML format

Usage:
    python3 extract_variables.py                    # Extract from all chapters
    python3 extract_variables.py --chapter 4        # Extract from Chapter 4 only
    python3 extract_variables.py --input equations_db.yaml  # Use existing equation DB
"""

import re
import argparse
import yaml
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from collections import Counter
import sys


@dataclass
class Variable:
    """Represents a variable with metadata."""
    id: str
    symbol: str
    symbol_plain: str
    name: str
    description: str
    units: Optional[str]
    typical_range: Optional[str]
    physical_meaning: Optional[str]
    mathematical_type: Optional[str]
    chapters: List[int]
    equations_used_in: List[str]
    first_defined: str
    importance: str
    category: str
    examples: List[Dict]


class VariableExtractor:
    """Extracts variables from LaTeX files and equation database."""

    def __init__(self, repo_root: Path, equations_db_path: Optional[Path] = None):
        self.repo_root = repo_root
        self.src_dir = repo_root / "src" / "chapters"
        self.variables: Dict[str, Variable] = {}
        self.equations_db = None

        # Load equations database if provided
        if equations_db_path and equations_db_path.exists():
            with open(equations_db_path) as f:
                self.equations_db = yaml.safe_load(f)

        # Common variable patterns
        self.variable_patterns = {
            # Probabilities
            r'P_?\{?\\text\{([^}]+)\}\}?': 'probability',
            r'\\Prob\(([^)]+)\)': 'probability',

            # Greek letters
            r'\\(pi|sigma|epsilon|lambda|mu|nu|rho|tau|alpha|beta|gamma|delta|omega)': 'greek',

            # Quality scores
            r'Q_?\{?\\text\{([^}]+)\}\}?': 'quality',

            # Counts/Numbers
            r'N_?\{?\\text\{([^}]+)\}\}?': 'count',

            # Rates/Errors
            r'\\epsilon_?\{?([^}]*)\}?': 'error_rate',

            # Haplotypes/Reads
            r'([hr])_?\{?([^}]*)\}?': 'sequence',
        }

        # Unit patterns in text
        self.unit_patterns = {
            r'base pairs?|bp': 'base pairs',
            r'probability|dimensionless': 'dimensionless',
            r'percentage?|%': 'percentage',
            r'count|number': 'count',
            r'reads?': 'reads',
        }

        # Common variable descriptions
        self.known_variables = {
            'h': {'name': 'Haplotype', 'type': 'sequence', 'units': 'Sequence'},
            'r': {'name': 'Read', 'type': 'sequence', 'units': 'Sequence'},
            'N': {'name': 'Sample Size', 'type': 'count', 'units': 'count'},
            'L': {'name': 'Read Length', 'type': 'count', 'units': 'base pairs'},
            '\\pi': {'name': 'Purity', 'type': 'probability', 'units': 'dimensionless'},
            '\\epsilon': {'name': 'Error Rate', 'type': 'rate', 'units': 'dimensionless'},
            'Q': {'name': 'Quality Score', 'type': 'score', 'units': 'Phred scale'},
            '\\lambda': {'name': 'Mixture Proportion', 'type': 'probability', 'units': 'dimensionless'},
        }

    def extract_from_equations_db(self) -> Dict[str, Set[str]]:
        """Extract variables from equation database."""
        if not self.equations_db:
            return {}

        var_to_equations = {}

        for eq in self.equations_db.get('equations', []):
            eq_id = eq.get('id', '')
            variables = eq.get('variables', [])

            for var in variables:
                if var not in var_to_equations:
                    var_to_equations[var] = set()
                var_to_equations[var].add(eq_id)

        return var_to_equations

    def extract_from_chapter(self, chapter_num: int) -> List[Variable]:
        """Extract variables from a specific chapter."""
        chapter_files = list(self.src_dir.glob(f"chapter{chapter_num}_*.tex"))

        if not chapter_files:
            print(f"Warning: No files found for Chapter {chapter_num}")
            return []

        chapter_file = sorted(chapter_files)[-1]
        print(f"Extracting from: {chapter_file.name}")

        with open(chapter_file, 'r', encoding='utf-8') as f:
            content = f.read()

        variables = self._parse_variables(content, chapter_num)
        return variables

    def _parse_variables(self, content: str, chapter_num: int) -> List[Variable]:
        """Parse chapter content to extract variable definitions."""
        variables = []

        # Look for explicit variable definitions
        # Pattern: "$symbol$ represents/denotes/is ..."
        definition_patterns = [
            r'\$([^$]+)\$\s+(?:represents?|denotes?|is|indicates?)\s+([^.]+)',
            r'(?:where|with)\s+\$([^$]+)\$\s+(?:is|denotes?)\s+([^.]+)',
        ]

        for pattern in definition_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                symbol = match.group(1).strip()
                description = match.group(2).strip()

                # Create variable ID
                var_id = self._create_variable_id(symbol)

                # Extract additional metadata from context
                context_start = max(0, match.start() - 500)
                context_end = min(len(content), match.end() + 500)
                context = content[context_start:context_end]

                units = self._extract_units(context)
                phys_meaning = self._extract_physical_meaning(context, description)
                math_type = self._determine_type(symbol, description)

                var = Variable(
                    id=var_id,
                    symbol=symbol,
                    symbol_plain=self._to_plain_text(symbol),
                    name=self._extract_name(symbol, description),
                    description=description[:200],
                    units=units,
                    typical_range=None,  # To be filled manually
                    physical_meaning=phys_meaning,
                    mathematical_type=math_type,
                    chapters=[chapter_num],
                    equations_used_in=[],  # Will be filled from equations DB
                    first_defined=f"Chapter {chapter_num}",
                    importance="supporting",
                    category=self._determine_category(chapter_num),
                    examples=[]
                )

                variables.append(var)

        return variables

    def _create_variable_id(self, symbol: str) -> str:
        """Create a unique ID for a variable."""
        # Simplify symbol to create ID
        var_id = symbol.replace('\\', '').replace('{', '').replace('}', '')
        var_id = var_id.replace('_', '_').replace('^', '_')
        var_id = re.sub(r'[^a-zA-Z0-9_]', '', var_id)
        return f"var_{var_id}"

    def _to_plain_text(self, latex_symbol: str) -> str:
        """Convert LaTeX symbol to plain text."""
        plain = latex_symbol.replace('\\', '')
        plain = plain.replace('{', '').replace('}', '')
        plain = plain.replace('_', '_').replace('^', '^')
        return plain

    def _extract_name(self, symbol: str, description: str) -> str:
        """Extract descriptive name from symbol and description."""
        # Check known variables first
        if symbol in self.known_variables:
            return self.known_variables[symbol]['name']

        # Try to extract from description
        # Look for capitalized words at start
        words = description.split()
        if words:
            # Take first few capitalized words
            name_words = []
            for word in words[:5]:
                if word[0].isupper():
                    name_words.append(word)
                else:
                    break
            if name_words:
                return ' '.join(name_words)

        return symbol

    def _extract_units(self, context: str) -> Optional[str]:
        """Extract units from context."""
        for pattern, unit in self.unit_patterns.items():
            if re.search(pattern, context, re.IGNORECASE):
                return unit
        return None

    def _extract_physical_meaning(self, context: str, description: str) -> Optional[str]:
        """Extract physical meaning from context."""
        # Look for explanatory sentences
        sentences = re.split(r'[.!?]\s+', context)
        for sentence in sentences:
            if any(word in sentence.lower() for word in ['represents', 'measures', 'quantifies', 'indicates']):
                return sentence.strip()[:200]

        return description[:200] if description else None

    def _determine_type(self, symbol: str, description: str) -> Optional[str]:
        """Determine mathematical type of variable."""
        # Check known types
        if symbol in self.known_variables:
            return self.known_variables[symbol]['type']

        # Infer from description
        if any(word in description.lower() for word in ['probability', 'likelihood', 'posterior']):
            return 'probability'
        elif any(word in description.lower() for word in ['count', 'number', 'size']):
            return 'count'
        elif any(word in description.lower() for word in ['rate', 'fraction', 'ratio']):
            return 'rate'
        elif any(word in description.lower() for word in ['score', 'quality']):
            return 'score'

        return None

    def _determine_category(self, chapter: int) -> str:
        """Determine variable category based on chapter."""
        categories = {
            4: "Pipeline Variables",
            5: "Purity Variables",
            6: "Bayesian Variables",
            7: "Experimental Design",
            8: "Reference Standards",
            9: "Enrichment Variables",
            10: "Mixture Variables",
            11: "Quality Variables",
            12: "Learning Variables",
            13: "Calibration Variables",
            14: "QC Variables",
            15: "Workflow Variables",
        }
        return categories.get(chapter, f"Chapter {chapter} Variables")

    def merge_with_equation_db(self):
        """Merge variable information from equation database."""
        if not self.equations_db:
            return

        var_to_eqs = self.extract_from_equations_db()

        # Update variables with equation references
        for var_id, var in self.variables.items():
            symbol = var.symbol
            if symbol in var_to_eqs:
                var.equations_used_in = sorted(list(var_to_eqs[symbol]))

    def save_to_yaml(self, output_file: Path):
        """Save extracted variables to YAML database."""
        data = {
            'metadata': {
                'version': '1.0.0',
                'created': '2024-11-18',
                'last_updated': '2024-11-18',
                'total_variables': len(self.variables),
                'description': 'Extracted variables from SMS Haplotype Framework'
            },
            'variables': []
        }

        for var in self.variables.values():
            var_dict = {
                'id': var.id,
                'symbol': var.symbol,
                'symbol_plain': var.symbol_plain,
                'name': var.name,
                'description': var.description,
                'units': var.units,
                'typical_range': var.typical_range,
                'physical_meaning': var.physical_meaning,
                'mathematical_type': var.mathematical_type,
                'chapters': var.chapters,
                'equations_used_in': var.equations_used_in,
                'first_defined': var.first_defined,
                'importance': var.importance,
                'category': var.category,
                'examples': var.examples
            }

            # Remove None/empty values
            var_dict = {k: v for k, v in var_dict.items() if v not in (None, [], '')}

            data['variables'].append(var_dict)

        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        print(f"\n✓ Saved {len(self.variables)} variables to {output_file}")

    def print_summary(self):
        """Print summary statistics."""
        print(f"\n{'='*60}")
        print("VARIABLE EXTRACTION SUMMARY")
        print(f"{'='*60}")
        print(f"Total variables extracted: {len(self.variables)}")

        # By type
        by_type = Counter(v.mathematical_type for v in self.variables.values() if v.mathematical_type)
        print(f"\nBy Type:")
        for typ in sorted(by_type.keys()):
            print(f"  {typ}: {by_type[typ]}")

        # By chapter
        chapter_counts = Counter()
        for var in self.variables.values():
            for ch in var.chapters:
                chapter_counts[ch] += 1

        print(f"\nBy Chapter:")
        for ch in sorted(chapter_counts.keys()):
            print(f"  Chapter {ch}: {chapter_counts[ch]}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract variables from LaTeX chapter files"
    )

    parser.add_argument(
        '--chapter', '-c',
        type=int,
        help='Extract from specific chapter only'
    )

    parser.add_argument(
        '--chapters',
        type=str,
        help='Extract from multiple chapters (comma-separated)'
    )

    parser.add_argument(
        '--input', '-i',
        type=Path,
        help='Input equations database YAML file'
    )

    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=Path('FAT/data/variables_db.yaml'),
        help='Output YAML file'
    )

    args = parser.parse_args()

    # Determine repository root
    repo_root = Path(__file__).parent.parent.parent

    # Create extractor
    equations_db = repo_root / args.input if args.input else None
    extractor = VariableExtractor(repo_root, equations_db)

    # Determine chapters
    if args.chapter:
        chapters = [args.chapter]
    elif args.chapters:
        chapters = [int(c.strip()) for c in args.chapters.split(',')]
    else:
        chapters = range(4, 7)  # Default to pilot chapters

    # Extract variables
    print("Starting variable extraction...")
    for ch in chapters:
        vars_ch = extractor.extract_from_chapter(ch)
        for var in vars_ch:
            if var.id not in extractor.variables:
                extractor.variables[var.id] = var
            else:
                # Merge chapter info
                if ch not in extractor.variables[var.id].chapters:
                    extractor.variables[var.id].chapters.append(ch)

    # Merge with equation DB if available
    if equations_db:
        print("Merging with equation database...")
        extractor.merge_with_equation_db()

    # Print summary
    extractor.print_summary()

    # Save
    output_path = repo_root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    extractor.save_to_yaml(output_path)

    print(f"\n✓ Variable extraction complete!")


if __name__ == "__main__":
    main()
