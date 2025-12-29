#!/usr/bin/env python3
"""
ONT Public Data - Wrapper for streaming analysis of public ONT datasets.

This is a wrapper that imports from skills/ont-public-data/scripts/ont_public_data.py
"""

import sys
from pathlib import Path

# Add skills path
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "ont-public-data" / "scripts"))

from ont_public_data import main

if __name__ == "__main__":
    sys.exit(main())
