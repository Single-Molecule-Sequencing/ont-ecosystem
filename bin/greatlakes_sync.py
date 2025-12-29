#!/usr/bin/env python3
"""
greatlakes_sync.py - Wrapper for Great Lakes sync skill

This wrapper imports from the authoritative implementation in skills/.

Usage:
    greatlakes_sync.py discover --submit --notify user@umich.edu
    greatlakes_sync.py review --latest --browser
    greatlakes_sync.py apply --latest --commit --push
    greatlakes_sync.py schedule install --weekly

Part of: https://github.com/Single-Molecule-Sequencing/ont-ecosystem
"""

import sys
from pathlib import Path

# Add skills directory to path
SKILLS_DIR = Path(__file__).parent.parent / 'skills' / 'greatlakes-sync' / 'scripts'
sys.path.insert(0, str(SKILLS_DIR))

from greatlakes_sync import main

if __name__ == '__main__':
    sys.exit(main())
