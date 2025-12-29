#!/usr/bin/env python3
"""
Update author placeholders across all manuscript files.

Usage:
    python update_authors.py --author1 "Jane Smith" --orcid1 "0000-0001-2345-6789" \
                             --author2 "John Doe" --orcid2 "0000-0002-3456-7890" \
                             --author3 "Alice Wong" --orcid3 "0000-0003-4567-8901" \
                             --email "jsmith@umich.edu"
"""

import argparse
import os
import re
from pathlib import Path

# Files to update
FILES_TO_UPDATE = [
    'main_manuscript.tex',
    'cover_letter.tex',
    'scientific_data/main_sdata.tex',
    'scientific_data/cover_letter_sdata.tex',
    'scientific_data/references_sdata.bib',
    'biorxiv/main_biorxiv.tex',
    'zenodo/.zenodo.json',
    'zenodo/README.md',
    'SUBMISSION_TRACKER.md',
]

def update_file(filepath, replacements):
    """Update a single file with replacements."""
    if not os.path.exists(filepath):
        print(f"  Skipping (not found): {filepath}")
        return False

    with open(filepath, 'r') as f:
        content = f.read()

    original = content
    for old, new in replacements.items():
        content = content.replace(old, new)

    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  Updated: {filepath}")
        return True
    else:
        print(f"  No changes: {filepath}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Update author information in manuscript files')
    parser.add_argument('--author1', required=True, help='First author name')
    parser.add_argument('--author2', required=True, help='Second author name')
    parser.add_argument('--author3', required=True, help='Third author name')
    parser.add_argument('--orcid1', default='0000-0000-0000-0000', help='First author ORCID')
    parser.add_argument('--orcid2', default='0000-0000-0000-0000', help='Second author ORCID')
    parser.add_argument('--orcid3', default='0000-0000-0000-0000', help='Third author ORCID')
    parser.add_argument('--email', required=True, help='Corresponding author email')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without applying')

    args = parser.parse_args()

    # Build replacement dictionary
    replacements = {
        '[Author One]': args.author1,
        '[Author Two]': args.author2,
        '[Author Three]': args.author3,
        '[email]@umich.edu': args.email,
        '[email]': args.email.split('@')[0],
        '"orcid": "0000-0000-0000-0000"': f'"orcid": "{args.orcid1}"',  # First occurrence in JSON
    }

    # For LaTeX files, also handle different formats
    replacements['Author One'] = args.author1
    replacements['Author Two'] = args.author2
    replacements['Author Three'] = args.author3

    print("Author Update Script")
    print("=" * 50)
    print(f"Author 1: {args.author1} (ORCID: {args.orcid1})")
    print(f"Author 2: {args.author2} (ORCID: {args.orcid2})")
    print(f"Author 3: {args.author3} (ORCID: {args.orcid3})")
    print(f"Email: {args.email}")
    print("=" * 50)

    if args.dry_run:
        print("\n[DRY RUN - No changes will be made]\n")

    # Get base directory
    base_dir = Path(__file__).parent.parent

    print("\nUpdating files:")
    updated = 0
    for filepath in FILES_TO_UPDATE:
        full_path = base_dir / filepath
        if not args.dry_run:
            if update_file(str(full_path), replacements):
                updated += 1
        else:
            print(f"  Would update: {filepath}")
            updated += 1

    print(f"\nTotal files updated: {updated}/{len(FILES_TO_UPDATE)}")

    if not args.dry_run:
        print("\nRemember to:")
        print("  1. Review changes in each file")
        print("  2. Update ORCID in zenodo/.zenodo.json manually (multiple authors)")
        print("  3. Recompile all LaTeX documents")
        print("  4. Commit changes to git")

if __name__ == '__main__':
    main()
