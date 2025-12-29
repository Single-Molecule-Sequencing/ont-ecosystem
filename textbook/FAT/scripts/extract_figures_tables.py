#!/usr/bin/env python3
"""
Figure and Table Extraction Script for SMS Haplotype Framework Textbook
========================================================================

Extracts figures and tables from LaTeX source files and organizes them
for easy reference and reuse.

Usage:
    python extract_figures_tables.py [--output-dir DIR] [--no-figures] [--no-tables]
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List
import json


# Repository root directory
REPO_ROOT = Path(__file__).parent.parent.parent
SRC_DIR = REPO_ROOT / "src"
OUTPUT_DIR = REPO_ROOT / "build" / "extracted"


class AssetExtractor:
    """Extracts figures and tables from LaTeX source files."""
    
    def __init__(self, output_dir: Path, extract_figures: bool = True, extract_tables: bool = True):
        self.output_dir = output_dir
        self.extract_figures = extract_figures
        self.extract_tables = extract_tables
        self.figures_dir = output_dir / "figures"
        self.tables_dir = output_dir / "tables"
        self.metadata: Dict = {"figures": [], "tables": []}
        
        # Create output directories
        if extract_figures:
            self.figures_dir.mkdir(parents=True, exist_ok=True)
        if extract_tables:
            self.tables_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_from_file(self, filepath: Path) -> None:
        """Extract assets from a single LaTeX file."""
        print(f"Processing: {filepath.name}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"  ⚠ Warning: Could not read {filepath}: {e}")
            return
        
        if self.extract_figures:
            self._extract_figures(content, filepath)
        
        if self.extract_tables:
            self._extract_tables(content, filepath)
    
    def _extract_figures(self, content: str, source_file: Path) -> None:
        """Extract figure environments from LaTeX content."""
        # Pattern to match \begin{figure}...\end{figure}
        figure_pattern = re.compile(
            r'\\begin\{figure\}(.*?)\\end\{figure\}',
            re.DOTALL
        )
        
        matches = figure_pattern.finditer(content)
        for idx, match in enumerate(matches, 1):
            figure_content = match.group(0)
            
            # Extract caption if present
            caption_match = re.search(r'\\caption\{(.*?)\}', figure_content, re.DOTALL)
            caption = caption_match.group(1) if caption_match else "No caption"
            
            # Extract label if present
            label_match = re.search(r'\\label\{(.*?)\}', figure_content)
            label = label_match.group(1) if label_match else f"figure_{source_file.stem}_{idx}"
            
            # Save figure content
            figure_filename = f"{source_file.stem}_fig{idx:02d}.tex"
            figure_path = self.figures_dir / figure_filename
            
            with open(figure_path, 'w', encoding='utf-8') as f:
                f.write(figure_content)
            
            # Add metadata
            self.metadata["figures"].append({
                "filename": figure_filename,
                "source_file": str(source_file.relative_to(REPO_ROOT)),
                "label": label,
                "caption": self._clean_latex_text(caption),
                "line_number": content[:match.start()].count('\n') + 1
            })
            
            print(f"  ✓ Extracted figure: {label}")
    
    def _extract_tables(self, content: str, source_file: Path) -> None:
        """Extract table environments from LaTeX content."""
        # Pattern to match \begin{table}...\end{table}
        table_pattern = re.compile(
            r'\\begin\{table\}(.*?)\\end\{table\}',
            re.DOTALL
        )
        
        matches = table_pattern.finditer(content)
        for idx, match in enumerate(matches, 1):
            table_content = match.group(0)
            
            # Extract caption if present
            caption_match = re.search(r'\\caption\{(.*?)\}', table_content, re.DOTALL)
            caption = caption_match.group(1) if caption_match else "No caption"
            
            # Extract label if present
            label_match = re.search(r'\\label\{(.*?)\}', table_content)
            label = label_match.group(1) if label_match else f"table_{source_file.stem}_{idx}"
            
            # Save table content
            table_filename = f"{source_file.stem}_table{idx:02d}.tex"
            table_path = self.tables_dir / table_filename
            
            with open(table_path, 'w', encoding='utf-8') as f:
                f.write(table_content)
            
            # Add metadata
            self.metadata["tables"].append({
                "filename": table_filename,
                "source_file": str(source_file.relative_to(REPO_ROOT)),
                "label": label,
                "caption": self._clean_latex_text(caption),
                "line_number": content[:match.start()].count('\n') + 1
            })
            
            print(f"  ✓ Extracted table: {label}")
    
    def _clean_latex_text(self, text: str) -> str:
        """Remove LaTeX commands from text for cleaner metadata."""
        # Remove common LaTeX commands
        text = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', text)
        text = re.sub(r'\\[a-zA-Z]+', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def save_metadata(self) -> None:
        """Save extraction metadata to JSON file."""
        metadata_file = self.output_dir / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2)
        print(f"\n✓ Metadata saved to {metadata_file}")
    
    def print_summary(self) -> None:
        """Print extraction summary."""
        print("\n" + "=" * 70)
        print("EXTRACTION SUMMARY")
        print("=" * 70)
        print(f"Figures extracted: {len(self.metadata['figures'])}")
        print(f"Tables extracted:  {len(self.metadata['tables'])}")
        print(f"Output directory:  {self.output_dir}")
        print("=" * 70)


def find_latex_files() -> List[Path]:
    """Find all LaTeX source files in the repository."""
    latex_files = []
    
    # Main document
    main_doc = REPO_ROOT / "haplotype_v6_complete_FIXED.tex"
    if main_doc.exists():
        latex_files.append(main_doc)
    
    # Chapters
    chapters_dir = SRC_DIR / "chapters"
    if chapters_dir.exists():
        latex_files.extend(sorted(chapters_dir.glob("*.tex")))
    
    # Appendices
    appendices_dir = SRC_DIR / "appendices"
    if appendices_dir.exists():
        latex_files.extend(sorted(appendices_dir.glob("*.tex")))
    
    return latex_files


def main():
    parser = argparse.ArgumentParser(
        description="Extract figures and tables from LaTeX source files"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory for extracted assets (default: build/extracted)"
    )
    parser.add_argument(
        "--no-figures",
        action="store_true",
        help="Skip figure extraction"
    )
    parser.add_argument(
        "--no-tables",
        action="store_true",
        help="Skip table extraction"
    )
    
    args = parser.parse_args()
    
    # Initialize extractor
    extractor = AssetExtractor(
        output_dir=args.output_dir,
        extract_figures=not args.no_figures,
        extract_tables=not args.no_tables
    )
    
    # Find and process LaTeX files
    latex_files = find_latex_files()
    
    if not latex_files:
        print("Error: No LaTeX files found")
        return 1
    
    print(f"Found {len(latex_files)} LaTeX files to process\n")
    
    for filepath in latex_files:
        extractor.extract_from_file(filepath)
    
    # Save metadata and print summary
    extractor.save_metadata()
    extractor.print_summary()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
