#!/usr/bin/env python3
"""
endreason_manuscript.py - Wrapper for end-reason manuscript skill

This wrapper imports from the authoritative implementation in skills/.
See skills/endreason-manuscript/ for the source code.

Part of: https://github.com/Single-Molecule-Sequencing/ont-ecosystem
"""

import sys
from pathlib import Path

# Add skills directory to path
SKILLS_DIR = Path(__file__).parent.parent / 'skills' / 'endreason-manuscript' / 'scripts'
sys.path.insert(0, str(SKILLS_DIR))

from endreason_manuscript import main

if __name__ == '__main__':
    sys.exit(main())
