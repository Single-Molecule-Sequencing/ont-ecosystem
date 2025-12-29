#!/usr/bin/env python3
"""
Extract Equations from LaTeX Source Files
==========================================

Scans chapter files to extract equations with metadata for the equation database.

This script:
1. Parses LaTeX files to find equation environments
2. Extracts equation content, labels, and surrounding context
3. Identifies variables used in each equation
4. Generates initial database entries in YAML format

Usage:
    python3 extract_equations.py                    # Extract from all chapters
    python3 extract_equations.py --chapter 4        # Extract from Chapter 4 only
    python3 extract_equations.py --output out.yaml  # Specify output file
"""

import re
import argparse
import yaml
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import sys


@dataclass
class Equation:
    """Represents an equation with metadata."""
    id: str
    old_label: Optional[str]
    chapter: int
    section: Optional[str]
    number: Optional[str]
    name: str
    latex: str
    description: str
    category: str
    variables: List[str]
    first_defined: str
    related_equations: List[str]
    applications: List[str]
    examples: List[str]
    interactive: bool
    visualization: Optional[str]
    importance: str
    tags: List[str]
    notes: str
    line_number: int  # For reference
    context_before: str  # Text before equation
    context_after: str  # Text after equation


class EquationExtractor:
    """Extracts equations from LaTeX source files."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.src_dir = repo_root / "src" / "chapters"
        self.equations: List[Equation] = []

        # Regex patterns
        self.equation_patterns = [
            (r'\\begin\{equation\}(.*?)\\end\{equation\}', 'equation'),
            (r'\\begin\{align\}(.*?)\\end\{align\}', 'align'),
            (r'\\begin\{align\*\}(.*?)\\end\{align\*\}', 'align*'),
            (r'\\begin\{gather\}(.*?)\\end\{gather\}', 'gather'),
            (r'\\begin\{multline\}(.*?)\\end\{multline\}', 'multline'),
        ]

        self.label_pattern = r'\\label\{([^}]+)\}'
        self.ceanchor_pattern = r'\\CEanchor\{(\d+)\}'

    def extract_from_chapter(self, chapter_num: int) -> List[Equation]:
        """Extract all equations from a specific chapter."""
        chapter_files = list(self.src_dir.glob(f"chapter{chapter_num}_*.tex"))

        if not chapter_files:
            print(f"Warning: No files found for Chapter {chapter_num}")
            return []

        # Use the most recent/populated version
        chapter_file = sorted(chapter_files)[-1]
        print(f"Extracting from: {chapter_file.name}")

        with open(chapter_file, 'r', encoding='utf-8') as f:
            content = f.read()

        equations = self._parse_equations(content, chapter_num, chapter_file.name)
        return equations

    def _parse_equations(self, content: str, chapter_num: int, filename: str) -> List[Equation]:
        """Parse LaTeX content to extract equations."""
        equations = []
        lines = content.split('\n')

        for env_pattern, env_type in self.equation_patterns:
            # Find all equations of this type
            for match in re.finditer(env_pattern, content, re.DOTALL):
                eq_content = match.group(1).strip()
                start_pos = match.start()
                end_pos = match.end()

                # Find line number
                line_num = content[:start_pos].count('\n') + 1

                # Extract label if present
                label_match = re.search(self.label_pattern, eq_content)
                old_label = label_match.group(1) if label_match else None

                # Check for CEanchor
                ceanchor_match = re.search(self.ceanchor_pattern, content[max(0, start_pos-200):start_pos])
                is_core_eq = ceanchor_match is not None

                # Get context (3 lines before and after)
                context_start = max(0, start_pos - 300)
                context_end = min(len(content), end_pos + 300)
                context_before = content[context_start:start_pos]
                context_after = content[end_pos:context_end]

                # Extract name from context (look for section titles, comments, etc.)
                name = self._extract_equation_name(context_before, context_after, old_label)

                # Extract description from context
                description = self._extract_description(context_before, context_after)

                # Identify variables used in equation
                variables = self._extract_variables(eq_content)

                # Determine category based on chapter and context
                category = self._determine_category(chapter_num, context_before)

                # Create equation entry
                eq = Equation(
                    id=f"eq_{chapter_num}_{len(equations) + 1}",  # Temporary ID
                    old_label=old_label,
                    chapter=chapter_num,
                    section=None,  # To be filled in
                    number=None,  # To be assigned during renumbering
                    name=name,
                    latex=eq_content,
                    description=description,
                    category=category,
                    variables=variables,
                    first_defined=f"Chapter {chapter_num}",
                    related_equations=[],  # To be filled manually
                    applications=[],  # To be filled manually
                    examples=[],  # To be filled manually
                    interactive=False,
                    visualization=None,
                    importance="supporting" if not is_core_eq else "core",
                    tags=[],  # To be filled manually
                    notes=f"Extracted from {filename}",
                    line_number=line_num,
                    context_before=context_before[-200:],  # Last 200 chars
                    context_after=context_after[:200]  # First 200 chars
                )

                equations.append(eq)

        return equations

    def _extract_equation_name(self, context_before: str, context_after: str, label: Optional[str]) -> str:
        """Extract a descriptive name for the equation."""
        # Try to find from label
        if label:
            # Convert label to readable name
            name = label.replace('eq:', '').replace('-', ' ').replace('_', ' ')
            name = ' '.join(word.capitalize() for word in name.split())
            if name:
                return name

        # Look for section/subsection titles nearby
        section_match = re.search(r'\\(?:sub)?section\{([^}]+)\}', context_before[-500:])
        if section_match:
            return section_match.group(1)

        # Look for theorem/definition environments
        theorem_match = re.search(r'\\begin\{(?:theorem|definition|lemma)\}(?:\[([^\]]+)\])?', context_before[-300:])
        if theorem_match and theorem_match.group(1):
            return theorem_match.group(1)

        return "Unnamed Equation"

    def _extract_description(self, context_before: str, context_after: str) -> str:
        """Extract description from surrounding text."""
        # Look for explanatory text after equation
        # Remove LaTeX commands for cleaner text
        clean_after = re.sub(r'\\[a-zA-Z]+\{?', '', context_after)
        clean_after = re.sub(r'[{}]', '', clean_after)

        # Get first sentence
        sentences = re.split(r'[.!?]\s+', clean_after)
        if sentences and len(sentences[0]) > 10:
            return sentences[0].strip()[:200]

        return "Description to be added"

    def _extract_variables(self, latex: str) -> List[str]:
        """Extract variable symbols from LaTeX equation."""
        # This is a simplified approach - looks for common variable patterns
        variables = set()

        # Single letter variables
        single_vars = re.findall(r'(?<![a-zA-Z])([a-zA-Z])(?![a-zA-Z])', latex)
        variables.update(single_vars)

        # Greek letters
        greek = re.findall(r'\\(alpha|beta|gamma|delta|epsilon|pi|sigma|lambda|mu|nu|rho|tau|omega|Gamma|Delta|Theta|Lambda|Sigma|Omega)', latex)
        variables.update([f'\\{g}' for g in greek])

        # Common multi-letter variables
        prob_vars = re.findall(r'\\Prob|\\mathbb\{[EP]\}', latex)
        variables.update(prob_vars)

        # Text subscripts
        text_vars = re.findall(r'([A-Za-z])_\{\\text\{([^}]+)\}\}', latex)
        variables.update([f'{v[0]}_{{\\text{{{v[1]}}}}}' for v in text_vars])

        return sorted(list(variables))[:10]  # Limit to top 10

    def _determine_category(self, chapter: int, context: str) -> str:
        """Determine equation category based on chapter and context."""
        categories = {
            4: "Pipeline Foundations",
            5: "Purity Theory",
            6: "Posterior Computation",
            7: "Experimental Design",
            8: "Reference Standards",
            9: "Targeted Enrichment",
            10: "Haplotype Mixtures",
            11: "Basecaller Quality Models",
            12: "Noisy Label Learning",
            13: "Basecaller Fine-Tuning",
            14: "Quality Control",
            15: "End-to-End Workflow",
        }
        return categories.get(chapter, f"Chapter {chapter}")

    def extract_all_chapters(self, chapters: Optional[List[int]] = None) -> List[Equation]:
        """Extract equations from all specified chapters."""
        if chapters is None:
            chapters = range(1, 21)  # All 20 chapters

        all_equations = []
        for chapter_num in chapters:
            print(f"\n{'='*60}")
            print(f"Extracting Chapter {chapter_num}")
            print(f"{'='*60}")

            equations = self.extract_from_chapter(chapter_num)
            all_equations.extend(equations)

            print(f"Found {len(equations)} equation(s)")

        return all_equations

    def save_to_yaml(self, equations: List[Equation], output_file: Path):
        """Save extracted equations to YAML database."""
        # Convert to dict format
        data = {
            'metadata': {
                'version': '1.0.0',
                'created': '2024-11-18',
                'last_updated': '2024-11-18',
                'total_equations': len(equations),
                'description': 'Extracted equations from SMS Haplotype Framework chapters'
            },
            'equations': []
        }

        for eq in equations:
            eq_dict = {
                'id': eq.id,
                'old_label': eq.old_label,
                'chapter': eq.chapter,
                'section': eq.section,
                'number': eq.number,
                'name': eq.name,
                'latex': eq.latex,
                'description': eq.description,
                'category': eq.category,
                'variables': eq.variables,
                'first_defined': eq.first_defined,
                'related_equations': eq.related_equations,
                'applications': eq.applications,
                'examples': eq.examples,
                'interactive': eq.interactive,
                'visualization': eq.visualization,
                'importance': eq.importance,
                'tags': eq.tags,
                'notes': eq.notes,
            }

            # Remove None values
            eq_dict = {k: v for k, v in eq_dict.items() if v is not None and v != [] and v != ''}

            data['equations'].append(eq_dict)

        # Save to YAML
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        print(f"\n✓ Saved {len(equations)} equations to {output_file}")

    def print_summary(self, equations: List[Equation]):
        """Print summary statistics."""
        print(f"\n{'='*60}")
        print("EXTRACTION SUMMARY")
        print(f"{'='*60}")
        print(f"Total equations extracted: {len(equations)}")

        # By chapter
        by_chapter = {}
        for eq in equations:
            by_chapter[eq.chapter] = by_chapter.get(eq.chapter, 0) + 1

        print(f"\nBy Chapter:")
        for ch in sorted(by_chapter.keys()):
            print(f"  Chapter {ch:2d}: {by_chapter[ch]:3d} equations")

        # By category
        by_category = {}
        for eq in equations:
            by_category[eq.category] = by_category.get(eq.category, 0) + 1

        print(f"\nBy Category:")
        for cat in sorted(by_category.keys()):
            print(f"  {cat}: {by_category[cat]} equations")

        # Labeled vs unlabeled
        labeled = sum(1 for eq in equations if eq.old_label)
        print(f"\nLabeled equations: {labeled}/{len(equations)} ({100*labeled/len(equations):.1f}%)")


def main():
    parser = argparse.ArgumentParser(
        description="Extract equations from LaTeX chapter files",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--chapter', '-c',
        type=int,
        help='Extract from specific chapter only'
    )

    parser.add_argument(
        '--chapters',
        type=str,
        help='Extract from multiple chapters (comma-separated, e.g., "4,5,6")'
    )

    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=Path('FAT/data/equations_db.yaml'),
        help='Output YAML file (default: FAT/data/equations_db.yaml)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    # Determine repository root
    repo_root = Path(__file__).parent.parent.parent

    # Create extractor
    extractor = EquationExtractor(repo_root)

    # Determine which chapters to extract
    if args.chapter:
        chapters = [args.chapter]
    elif args.chapters:
        chapters = [int(c.strip()) for c in args.chapters.split(',')]
    else:
        chapters = None  # All chapters

    # Extract equations
    print("Starting equation extraction...")
    equations = extractor.extract_all_chapters(chapters)

    # Print summary
    extractor.print_summary(equations)

    # Save to YAML
    output_path = repo_root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    extractor.save_to_yaml(equations, output_path)

    print(f"\n✓ Extraction complete!")
    print(f"\nNext steps:")
    print(f"1. Review {output_path}")
    print(f"2. Manually curate metadata (descriptions, applications, etc.)")
    print(f"3. Run renumbering script to assign sequential numbers")


if __name__ == "__main__":
    main()
