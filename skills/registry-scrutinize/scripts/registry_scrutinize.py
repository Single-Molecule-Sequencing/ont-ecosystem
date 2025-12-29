#!/usr/bin/env python3
"""
Registry Scrutinize - Deep validation, enrichment, and re-analysis for ONT experiments.

Provides comprehensive scrutiny of registry entries including:
- Strict validation against metadata standards
- Metadata extraction from names, paths, and source data
- Re-analysis from source data (local or S3)
- Detailed audit logging of all changes

Usage:
    python registry_scrutinize.py audit [--json FILE] [--verbose]
    python registry_scrutinize.py fix <exp_id> [--dry-run] [--force-reanalyze]
    python registry_scrutinize.py enrich [--all | --incomplete] [--dry-run]
    python registry_scrutinize.py reanalyze <exp_id> [--max-reads N]
    python registry_scrutinize.py batch [options]
    python registry_scrutinize.py report [--output FILE]
"""

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# =============================================================================
# CONFIGURATION
# =============================================================================

REGISTRY_PATH = Path.home() / ".ont-registry" / "experiments.yaml"
AUDIT_LOG_PATH = Path.home() / ".ont-registry" / "audit_log.yaml"
UPDATE_LOG_PATH = Path.home() / ".ont-registry" / "update_log.yaml"
AWS_CMD = os.path.expanduser("~/.local/bin/aws")
MAX_SAMPLE_READS = 50000

# URL constants
S3_BUCKET = "s3://ont-open-data"
HTTPS_BASE = "https://ont-open-data.s3.amazonaws.com"
BROWSER_BASE = "https://42basepairs.com/browse/s3/ont-open-data"
LANDING_PAGE_BASE = "https://labs.epi2me.io"

# Dataset landing pages
DATASET_LANDING_PAGES = {
    "giab_2023.05": "https://labs.epi2me.io/giab-2023.05/",
    "giab_2025.01": "https://labs.epi2me.io/giab-2025.01/",
    "colo829_2024.03": "https://labs.epi2me.io/colo829-2024.03/",
    "hereditary_cancer_2025.09": "https://labs.epi2me.io/hereditary-cancer-2025/",
}

# =============================================================================
# METADATA EXTRACTION PATTERNS - COMPREHENSIVE
# =============================================================================

SAMPLE_PATTERNS = [
    # GIAB samples with alternate names
    (r'\b(HG001)\b', 'HG001', 'GIAB', 'NA12878'),
    (r'\b(HG002)\b', 'HG002', 'GIAB', 'NA24385'),
    (r'\b(HG003)\b', 'HG003', 'GIAB', 'NA24149'),
    (r'\b(HG004)\b', 'HG004', 'GIAB', 'NA24143'),
    (r'\b(HG005)\b', 'HG005', 'GIAB', 'NA24631'),
    (r'\b(HG006)\b', 'HG006', 'GIAB', 'NA24694'),
    (r'\b(HG007)\b', 'HG007', 'GIAB', 'NA24695'),
    (r'\bNA12878\b', 'HG001', 'GIAB', 'NA12878'),
    (r'\bNA24385\b', 'HG002', 'GIAB', 'NA24385'),
    (r'\bGM24385\b', 'HG002', 'GIAB', 'GM24385'),
    (r'\bNA24149\b', 'HG003', 'GIAB', 'NA24149'),
    (r'\bNA24143\b', 'HG004', 'GIAB', 'NA24143'),
    (r'\bNA24631\b', 'HG005', 'GIAB', 'NA24631'),
    # Cancer cell lines
    (r'\b(COLO829)\b', 'COLO829', 'Cancer', None),
    (r'\b(HCC1395)\b', 'HCC1395', 'Cancer', None),
    (r'\b(HCC1937)\b', 'HCC1937', 'Cancer', None),
    (r'\b(MCF7)\b', 'MCF7', 'Cancer', None),
    # Reference genomes
    (r'\b(CHM13)\b', 'CHM13', 'Reference', None),
    (r'\bT2T\b', 'CHM13', 'Reference', 'T2T'),
    # Cell lines
    (r'\b(jurkat)\b', 'Jurkat', 'Cell Line', None),
    (r'\b(293t|hek293)\b', 'HEK293T', 'Cell Line', None),
    (r'\b(hela)\b', 'HeLa', 'Cell Line', None),
    (r'\b(k562)\b', 'K562', 'Cell Line', None),
    # Microbial
    (r'\bzymo\b', 'Zymo Mock', 'Microbial', None),
    (r'\b[Ee]coli\b', 'E.coli', 'Microbial', None),
    (r'\bE[\._]coli\b', 'E.coli', 'Microbial', None),
    # Lab-specific samples/experiments (patterns without word boundaries for underscore-separated names)
    (r'SMA[_-]?seq', 'SMA-seq', 'Research', None),
    (r'(?:^|[_\-\s])CYP|pCYP', 'CYP', 'Plasmid', None),
    (r'(?:^|[_\-\s])human(?:[_\-\s]|$)', 'Human', 'Human', None),
    (r'(?:^|[_\-\s])WGS(?:[_\-\s]|$)', 'WGS', 'Human', None),
    (r'(?:^|[_\-\s])targeted(?:[_\-\s]|$)', 'Targeted', 'Research', None),
    (r'Cas9', 'Cas9', 'CRISPR', None),
    (r'gRNA', 'gRNA', 'CRISPR', None),
    (r'rRNA', 'rRNA', 'RNA', None),
    (r'promA', 'PromA Run', 'Lab Run', None),
    (r'(?:^|[_\-\s])PGx(?:[_\-\s]|$)', 'PGx', 'Pharmacogenomics', None),
    (r'Multiplex|8plex', 'Multiplex', 'Multiplex', None),
    (r'Flongle', 'Flongle', 'Flongle', None),
]

# Device types (sequencing hardware)
DEVICE_PATTERNS = [
    (r'MD-\d{5,6}', 'Mk1D'),           # Mk1D standalone basecaller
    (r'MN\d{5}', 'MinION'),             # MinION device
    (r'P2\s*Solo|P2_Solo|PCA\d+', 'P2 Solo'),  # P2 Solo device
    (r'PC\d+-PROTO', 'P2 Solo'),        # P2 Solo prototype
    (r'PromethION\s*2|Prom2', 'PromethION 2'),  # PromethION 2
    (r'PromethION\s*24|Prom24', 'PromethION 24'),  # PromethION 24
    (r'PromethION\s*48|Prom48', 'PromethION 48'),  # PromethION 48
    (r'gridion|GridION|GXB', 'GridION'),  # GridION device
]

# Flow cell types (consumables)
FLOWCELL_TYPE_PATTERNS = [
    (r'FLO-PRO\d+|promethion|prom', 'PromethION'),  # PromethION flow cells
    (r'FLO-MIN\d+', 'MinION'),                       # MinION flow cells
    (r'FLO-FLG\d+|flongle', 'Flongle'),              # Flongle flow cells
    (r'PA[A-Z]\d{5}', 'PromethION'),                 # PAW/PAO etc = PromethION
    (r'FA[A-Z]\d{5}', 'MinION'),                     # FAW etc = MinION
    (r'AE[A-Z]\d{5}', 'Flongle'),                    # Flongle adapter
]

CHEMISTRY_PATTERNS = [
    (r'R10\.4\.1|r10_4_1|R1041|r1041|10\.4\.1', 'R10.4.1'),
    (r'R10\.4(?!\.1)|r10_4(?!_1)|R104(?!1)', 'R10.4'),
    (r'R9\.4\.1|r9_4_1|R941|r941', 'R9.4.1'),
    (r'E8\.2|e8_2|E82', 'E8.2'),
    (r'FLO-PRO114M', 'R10.4.1'),
    (r'FLO-PRO002', 'R9.4.1'),
    (r'FLO-MIN114', 'R10.4.1'),
    (r'FLO-MIN106', 'R9.4.1'),
]

MODEL_PATTERNS = [
    (r'\bsup(?:er)?(?:_v?\d+(?:\.\d+)*)?(?:@|_|\.|\b)', 'sup'),
    (r'\bhac(?:_v?\d+(?:\.\d+)*)?(?:@|_|\.|\b)', 'hac'),
    (r'\bfast(?:_v?\d+(?:\.\d+)*)?(?:@|_|\.|\b)', 'fast'),
    (r'dna_r10\.4\.1_e8\.2_\d+bps_sup', 'sup'),
    (r'dna_r10\.4\.1_e8\.2_\d+bps_hac', 'hac'),
    (r'dna_r10\.4\.1_e8\.2_\d+bps_fast', 'fast'),
    (r'd\d+sup\d+', 'sup'),
    (r'd\d+hac\d+', 'hac'),
]

MODIFICATION_PATTERNS = [
    (r'5mCG_5hmCG|5mC_5hmC', ['5mCG', '5hmCG']),
    (r'5mCG(?!_5hmCG)|5mC(?!_5hmC)', ['5mCG']),
    (r'5hmCG(?!.*5mCG)', ['5hmCG']),
    (r'6mA', ['6mA']),
    (r'4mC', ['4mC']),
    (r'meth|methyl', ['methylation']),
]

KIT_PATTERNS = [
    (r'SQK-LSK114', 'SQK-LSK114'),
    (r'SQK-LSK109', 'SQK-LSK109'),
    (r'SQK-NBD114', 'SQK-NBD114'),
    (r'SQK-RBK114', 'SQK-RBK114'),
    (r'SQK-RAD114', 'SQK-RAD114'),
    (r'SQK-PCB114', 'SQK-PCB114'),
]

FLOWCELL_PATTERN = r'(PA[A-Z]\d{5}|PB[A-Z]\d{5}|FB[A-Z]\d{5}|FA[A-Z]\d{5})'
RUNID_PATTERN = r'([a-f0-9]{8})(?:[_-]|$)'
DATE_PATTERNS = [
    (r'(\d{4})-(\d{2})-(\d{2})', 'ISO'),  # YYYY-MM-DD
    (r'(\d{4})(\d{2})(\d{2})', 'YYYYMMDD'),  # YYYYMMDD
    (r'(\d{2})(\d{2})(\d{4})', 'MMDDYYYY'),  # MMDDYYYY
]

# =============================================================================
# VALIDATION WEIGHTS
# =============================================================================

VALIDATION_WEIGHTS = {
    'required': {
        'id': 10,
        'name': 10,
        'source': 10,
    },
    'important': {
        'sample': 15,
        'device_type': 8,
        'flowcell_type': 7,  # PromethION, MinION, or Flongle
        'chemistry': 10,
        'basecall_model': 10,
        'flowcell_id': 5,
    },
    'metrics': {
        'read_counts.sampled': 10,
        'quality_metrics.mean_qscore': 8,
        'length_metrics.n50': 7,
    }
}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def load_registry() -> Dict:
    """Load the experiment registry."""
    if not REGISTRY_PATH.exists():
        return {"version": "3.0", "experiments": []}
    with open(REGISTRY_PATH) as f:
        return yaml.safe_load(f) or {"version": "3.0", "experiments": []}


def save_registry(data: Dict):
    """Save the experiment registry with updated timestamp."""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["updated"] = datetime.now().isoformat()
    with open(REGISTRY_PATH, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def log_audit(action: str, exp_id: str, changes: Dict, user: str = "claude-code"):
    """Log audit entry for changes made."""
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    if AUDIT_LOG_PATH.exists():
        with open(AUDIT_LOG_PATH) as f:
            log = yaml.safe_load(f) or {"entries": []}
    else:
        log = {"entries": []}

    log["entries"].append({
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "experiment_id": exp_id,
        "changes": changes,
        "user": user,
    })

    # Keep last 2000 entries
    log["entries"] = log["entries"][-2000:]

    with open(AUDIT_LOG_PATH, 'w') as f:
        yaml.dump(log, f, default_flow_style=False)


def log_update(summary: Dict):
    """Log update summary for batch operations."""
    UPDATE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    if UPDATE_LOG_PATH.exists():
        with open(UPDATE_LOG_PATH) as f:
            log = yaml.safe_load(f) or {"updates": []}
    else:
        log = {"updates": []}

    summary["timestamp"] = datetime.now().isoformat()
    log["updates"].append(summary)
    log["updates"] = log["updates"][-100:]  # Keep last 100 batch updates

    with open(UPDATE_LOG_PATH, 'w') as f:
        yaml.dump(log, f, default_flow_style=False)


def mean_qscore(qscores: List[float]) -> float:
    """Calculate mean Q-score via probability space (correct method)."""
    if not qscores:
        return 0.0
    try:
        import numpy as np
        probs = np.power(10, -np.array(qscores) / 10)
        mean_prob = np.mean(probs)
    except ImportError:
        probs = [10 ** (-q / 10) for q in qscores]
        mean_prob = sum(probs) / len(probs)
    if mean_prob <= 0:
        return 60.0
    return -10 * math.log10(mean_prob)


def get_nested_value(d: Dict, path: str) -> Any:
    """Get value from nested dict using dot notation path."""
    parts = path.split('.')
    val = d
    for part in parts:
        if isinstance(val, dict):
            val = val.get(part)
        else:
            return None
    return val


# =============================================================================
# METADATA EXTRACTION
# =============================================================================

def extract_metadata_from_path(path: str) -> Dict[str, Any]:
    """Extract detailed metadata from local file paths.

    Common ONT path patterns:
    - /data1/experiment_name/sample/YYYYMMDD_HHMM_DeviceID_FlowcellID_runid/
    - /nfs/turbo/.../AGC/sample_id/YYYYMMDD_HHMM_position_FlowcellID_runid/
    """
    updates = {}
    if not path:
        return updates

    # Extract device ID from path
    device_match = re.search(r'(MD-\d{5,6}|MN\d{5}|PCA\d{5,6}|GXB\d+)', path)
    if device_match:
        device_id = device_match.group(1)
        updates['device_id'] = device_id
        # Determine device type
        if device_id.startswith('MD-'):
            updates['device_type'] = 'Mk1D'
        elif device_id.startswith('MN'):
            updates['device_type'] = 'MinION'
        elif device_id.startswith('PCA'):
            updates['device_type'] = 'P2 Solo'
        elif device_id.startswith('GXB'):
            updates['device_type'] = 'GridION'

    # Extract flowcell ID from path (various prefixes)
    # PromethION: PAW, PAO, PBE, PBC, etc.
    # MinION: FAW, FAO, FBB, FBD, etc.
    # Flongle: AEQ, etc.
    fc_match = re.search(r'(P[A-Z]{2}\d{5}|F[A-Z]{2}\d{5}|A[A-Z]{2}\d{5})', path)
    if fc_match:
        fc_id = fc_match.group(1)
        updates['flowcell_id'] = fc_id
        # Determine flowcell type
        if fc_id.startswith('P'):
            updates['flowcell_type'] = 'PromethION'
        elif fc_id.startswith('F'):
            updates['flowcell_type'] = 'MinION'
        elif fc_id.startswith('A'):
            updates['flowcell_type'] = 'Flongle'

    # Extract run date from path (YYYYMMDD_HHMM pattern)
    date_match = re.search(r'(\d{8})_\d{4}', path)
    if date_match:
        date_str = date_match.group(1)
        try:
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            if 2015 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                updates['run_date'] = f"{year:04d}-{month:02d}-{day:02d}"
        except (ValueError, IndexError):
            pass

    # Extract run_id from path (8-char hex after flowcell)
    runid_match = re.search(r'[A-Z]{3}\d{5}_([a-f0-9]{8})', path)
    if runid_match:
        updates['run_id'] = runid_match.group(1)

    # Extract position from path (1A, 2B, 2H, etc.)
    pos_match = re.search(r'_(\d[A-H])_', path)
    if pos_match:
        updates['position'] = pos_match.group(1)

    # Extract sample ID from path patterns
    # AGC/14400-CZ-4 format
    agc_match = re.search(r'/AGC/(\d+-[A-Z]+-\d+)/', path)
    if agc_match:
        updates['sample_id_agc'] = agc_match.group(1)

    return updates


def extract_all_metadata(exp: Dict) -> Dict[str, Any]:
    """Extract all possible metadata from experiment name, path, and existing fields."""
    updates = {}
    metadata = exp.get("metadata", {})

    # First extract from path (most reliable for local experiments)
    location = exp.get("location", "")
    if location:
        path_meta = extract_metadata_from_path(location)
        for key, value in path_meta.items():
            if not metadata.get(key):
                updates[key] = value

    # Combine all text sources for pattern matching
    text_sources = [
        exp.get("name", ""),
        location,
        metadata.get("s3_path", ""),
        metadata.get("source_key", ""),
        str(exp.get("urls", {})),
        exp.get("platform", ""),
        exp.get("device_id", ""),
        exp.get("flowcell_id", ""),
    ]
    combined_text = " ".join(str(s) for s in text_sources if s)

    # Extract sample
    if not metadata.get("sample"):
        for pattern, sample, category, alt_name in SAMPLE_PATTERNS:
            if re.search(pattern, combined_text, re.IGNORECASE):
                updates["sample"] = sample
                updates["sample_category"] = category
                if alt_name:
                    updates["sample_alt_name"] = alt_name
                break

    # Extract device type (sequencing hardware)
    if not metadata.get("device_type"):
        # First check device_id field for device type
        device_id = exp.get("device_id", "")
        if device_id:
            if device_id.startswith("MD-"):
                updates["device_type"] = "Mk1D"
            elif device_id.startswith("MN"):
                updates["device_type"] = "MinION"
            elif device_id.startswith("PCA") or device_id.startswith("PC"):
                updates["device_type"] = "P2 Solo"
            elif device_id.startswith("GXB"):
                updates["device_type"] = "GridION"

        # Then check patterns in text
        if "device_type" not in updates:
            for pattern, device in DEVICE_PATTERNS:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    updates["device_type"] = device
                    break

    # Extract flow cell type (consumable type)
    if not metadata.get("flowcell_type"):
        for pattern, fc_type in FLOWCELL_TYPE_PATTERNS:
            if re.search(pattern, combined_text, re.IGNORECASE):
                updates["flowcell_type"] = fc_type
                break

    # Extract chemistry
    if not metadata.get("chemistry"):
        for pattern, chemistry in CHEMISTRY_PATTERNS:
            if re.search(pattern, combined_text, re.IGNORECASE):
                updates["chemistry"] = chemistry
                break

    # Extract basecall model
    if not metadata.get("basecall_model"):
        for pattern, model in MODEL_PATTERNS:
            if re.search(pattern, combined_text, re.IGNORECASE):
                updates["basecall_model"] = model
                break

    # Extract modifications
    if not metadata.get("modifications"):
        for pattern, mods in MODIFICATION_PATTERNS:
            if re.search(pattern, combined_text, re.IGNORECASE):
                updates["modifications"] = mods
                break

    # Extract kit
    if not metadata.get("kit"):
        for pattern, kit in KIT_PATTERNS:
            if re.search(pattern, combined_text, re.IGNORECASE):
                updates["kit"] = kit
                break

    # Extract flowcell ID
    if not metadata.get("flowcell_id") and not exp.get("flowcell_id"):
        match = re.search(FLOWCELL_PATTERN, combined_text)
        if match:
            updates["flowcell_id"] = match.group(1)

    # Extract run ID
    if not metadata.get("run_id"):
        match = re.search(RUNID_PATTERN, combined_text)
        if match:
            updates["run_id"] = match.group(1)

    # Extract date
    if not metadata.get("run_date"):
        for pattern, fmt in DATE_PATTERNS:
            match = re.search(pattern, combined_text)
            if match:
                try:
                    groups = match.groups()
                    if fmt == 'ISO':
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    elif fmt == 'YYYYMMDD':
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    elif fmt == 'MMDDYYYY':
                        month, day, year = int(groups[0]), int(groups[1]), int(groups[2])

                    if 2015 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                        updates["run_date"] = f"{year:04d}-{month:02d}-{day:02d}"
                        break
                except (ValueError, IndexError):
                    pass

    return updates


# =============================================================================
# VALIDATION
# =============================================================================

def calculate_completeness(exp: Dict) -> Dict:
    """Calculate detailed completeness score with missing field tracking."""
    metadata = exp.get("metadata", {})

    score = 0
    max_score = 0
    missing = []
    present = []

    # Check required fields
    for field, weight in VALIDATION_WEIGHTS['required'].items():
        max_score += weight
        if exp.get(field):
            score += weight
            present.append(field)
        else:
            missing.append(field)

    # Check important metadata fields
    for field, weight in VALIDATION_WEIGHTS['important'].items():
        max_score += weight
        if metadata.get(field) or exp.get(field):
            score += weight
            present.append(f"metadata.{field}")
        else:
            missing.append(f"metadata.{field}")

    # Check metrics
    for field, weight in VALIDATION_WEIGHTS['metrics'].items():
        max_score += weight
        val = get_nested_value(exp, field)
        if val:
            score += weight
            present.append(field)
        else:
            missing.append(field)

    pct = round(score / max_score * 100) if max_score > 0 else 0

    return {
        "score": score,
        "max_score": max_score,
        "percentage": pct,
        "missing": missing,
        "present": present,
        "status": "good" if pct >= 80 else "warning" if pct >= 50 else "poor",
    }


def validate_experiment(exp: Dict) -> Tuple[bool, List[str], List[str]]:
    """
    Validate experiment against strict standards.

    Returns: (is_valid, errors, warnings)
    """
    errors = []
    warnings = []

    # Required field validation
    if not exp.get("id"):
        errors.append("Missing required field: id")
    elif not re.match(r'^exp-[a-f0-9]{8}$', exp.get("id", "")):
        warnings.append(f"ID format non-standard: {exp.get('id')}")

    if not exp.get("name"):
        errors.append("Missing required field: name")

    if not exp.get("source") or exp.get("source") == "unknown":
        errors.append("Missing or unknown source")
    elif exp.get("source") not in ["local", "ont-open-data", "sra", "ena"]:
        warnings.append(f"Non-standard source: {exp.get('source')}")

    # Metadata validation
    metadata = exp.get("metadata", {})

    if not metadata.get("sample") and not metadata.get("device_type"):
        warnings.append("Missing both sample and device_type metadata")

    # For ont-open-data, URLs should exist
    if exp.get("source") == "ont-open-data":
        urls = exp.get("urls", {})
        if not urls.get("https"):
            warnings.append("Public experiment missing HTTPS URL")
        if not urls.get("browser"):
            warnings.append("Public experiment missing browser URL")

    # Check for legacy fields that should be migrated
    legacy_fields = ["mean_quality", "total_reads", "n50"]
    has_legacy = any(exp.get(f) for f in legacy_fields)
    has_new = any(exp.get(f) for f in ["quality_metrics", "read_counts", "length_metrics"])

    if has_legacy and not has_new:
        warnings.append("Uses legacy field format, should migrate to structured metrics")

    # Provenance validation
    if not exp.get("provenance", {}).get("schema_version"):
        warnings.append("Missing schema version in provenance")

    is_valid = len(errors) == 0
    return is_valid, errors, warnings


# =============================================================================
# FIX AND ENRICH
# =============================================================================

def fix_experiment(exp: Dict, force_reanalyze: bool = False) -> Tuple[Dict, Dict]:
    """
    Fix and enrich an experiment entry.

    Returns: (fixed_experiment, changes_made)
    """
    changes = {}

    # Ensure metadata dict exists
    if "metadata" not in exp:
        exp["metadata"] = {}
        changes["created_metadata"] = True
    metadata = exp["metadata"]

    # Fix source
    if not exp.get("source") or exp.get("source") == "unknown":
        location = exp.get("location", "")
        s3_path = metadata.get("s3_path", "")
        source_key = metadata.get("source_key", "")

        if any("ont-open-data" in str(s).lower() for s in [location, s3_path, source_key]):
            exp["source"] = "ont-open-data"
        else:
            exp["source"] = "local"
        changes["fixed_source"] = exp["source"]

    # Migrate top-level fields to metadata
    field_migrations = [
        ("platform", "device_type"),
        ("device_id", "device_id"),
        ("flowcell_id", "flowcell_id"),
    ]

    for old_field, new_field in field_migrations:
        if exp.get(old_field) and not metadata.get(new_field):
            metadata[new_field] = exp[old_field]
            changes[f"migrated_{old_field}"] = exp[old_field]

    # Extract metadata from name/path
    extracted = extract_all_metadata(exp)
    for key, value in extracted.items():
        if not metadata.get(key):
            metadata[key] = value
            changes[f"extracted_{key}"] = value

    # Build URLs for ont-open-data sources
    if exp.get("source") == "ont-open-data":
        s3_path = metadata.get("s3_path") or metadata.get("source_key", "")
        if s3_path and not exp.get("urls", {}).get("browser"):
            # Clean up path
            s3_path = s3_path.replace("ont-open-data/", "")

            path_parts = s3_path.split("/")
            parent_path = "/".join(path_parts[:-1]) if len(path_parts) > 1 else s3_path

            if "urls" not in exp:
                exp["urls"] = {}

            if not exp["urls"].get("s3"):
                exp["urls"]["s3"] = f"{S3_BUCKET}/{s3_path}"
            if not exp["urls"].get("https"):
                exp["urls"]["https"] = f"{HTTPS_BASE}/{s3_path}"
            if not exp["urls"].get("browser"):
                exp["urls"]["browser"] = f"{BROWSER_BASE}/{parent_path}"

            # Add landing page
            dataset = metadata.get("dataset", "")
            if dataset in DATASET_LANDING_PAGES and not exp["urls"].get("landing_page"):
                exp["urls"]["landing_page"] = DATASET_LANDING_PAGES[dataset]
            elif dataset and not exp["urls"].get("landing_page"):
                slug = dataset.replace("_", "-").replace(".", "-")
                exp["urls"]["landing_page"] = f"{LANDING_PAGE_BASE}/{slug}/"

            changes["generated_urls"] = True

    # Migrate legacy metrics to structured format
    if exp.get("mean_quality") and not exp.get("quality_metrics"):
        exp["quality_metrics"] = {
            "mean_qscore": exp["mean_quality"],
            "note": "Migrated from legacy mean_quality field"
        }
        changes["migrated_quality_metrics"] = True

    if exp.get("n50") and not exp.get("length_metrics"):
        exp["length_metrics"] = {"n50": exp["n50"]}
        if exp.get("total_bases") and exp.get("total_reads") and exp["total_reads"] > 0:
            exp["length_metrics"]["mean_length"] = exp["total_bases"] / exp["total_reads"]
        changes["migrated_length_metrics"] = True

    if exp.get("total_reads") and not exp.get("read_counts"):
        exp["read_counts"] = {
            "sampled": exp["total_reads"],
            "estimated_total": None,
            "counted_total": None,
            "count_source": "legacy",
            "description": "Migrated from legacy total_reads field"
        }
        changes["migrated_read_counts"] = True

    if exp.get("total_bases") and not exp.get("base_counts"):
        exp["base_counts"] = {
            "sampled_bases": exp["total_bases"],
            "estimated_total_bases": None,
        }
        changes["migrated_base_counts"] = True

    # Update provenance
    if "provenance" not in exp:
        exp["provenance"] = {}
    exp["provenance"]["schema_version"] = "2.0"
    exp["provenance"]["updated"] = datetime.now().isoformat()
    if changes:
        exp["provenance"]["last_fixed"] = datetime.now().isoformat()

    return exp, changes


# =============================================================================
# STREAMING RE-ANALYSIS
# =============================================================================

def stream_bam_header(bam_url: str) -> Optional[Dict]:
    """Stream BAM header to extract metadata."""
    try:
        cmd = f"samtools view -H {bam_url} 2>/dev/null | head -200"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            return None

        header = result.stdout
        metadata = {}

        for line in header.split('\n'):
            if line.startswith('@RG'):
                parts = line.split('\t')
                for part in parts[1:]:
                    if part.startswith('SM:'):
                        metadata['sample'] = part[3:]
                    elif part.startswith('PL:'):
                        metadata['platform'] = part[3:]
                    elif part.startswith('PM:'):
                        metadata['model'] = part[3:]
                    elif part.startswith('DS:'):
                        desc = part[3:]
                        if 'dorado' in desc.lower():
                            metadata['basecaller'] = 'dorado'
                            ver_match = re.search(r'dorado[_\s]*([\d\.]+)', desc, re.IGNORECASE)
                            if ver_match:
                                metadata['basecaller_version'] = ver_match.group(1)

            elif line.startswith('@PG'):
                parts = line.split('\t')
                for part in parts[1:]:
                    if part.startswith('PN:'):
                        program = part[3:]
                        if 'dorado' in program.lower():
                            metadata['basecaller'] = 'dorado'
                    elif part.startswith('CL:'):
                        cmdline = part[3:]
                        for pattern, model in MODEL_PATTERNS:
                            if re.search(pattern, cmdline, re.IGNORECASE):
                                metadata['basecall_model'] = model
                                break

        return metadata if metadata else None

    except Exception as e:
        print(f"  Warning: Could not read BAM header: {e}")
        return None


def stream_bam_stats(bam_url: str, max_reads: int = MAX_SAMPLE_READS) -> Optional[Dict]:
    """Stream BAM file to compute statistics."""
    try:
        # Get file size first
        file_size = None
        if bam_url.startswith("https://"):
            size_cmd = f"curl -sI {bam_url} | grep -i content-length | awk '{{print $2}}' | tr -d '\\r'"
            result = subprocess.run(size_cmd, shell=True, capture_output=True, text=True, timeout=30)
            if result.stdout.strip().isdigit():
                file_size = int(result.stdout.strip())

        # Stream reads
        cmd = f"samtools view {bam_url} 2>/dev/null | head -{max_reads}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)

        if result.returncode != 0 or not result.stdout.strip():
            return None

        lines = result.stdout.strip().split('\n')
        lengths = []
        qscores = []
        mapped = 0
        unmapped = 0

        for line in lines:
            if not line.strip():
                continue
            fields = line.split('\t')
            if len(fields) < 11:
                continue

            flag = int(fields[1])
            seq = fields[9]
            qual = fields[10]

            lengths.append(len(seq))

            if qual != '*':
                read_qscores = [ord(c) - 33 for c in qual]
                if read_qscores:
                    qscores.append(mean_qscore(read_qscores))

            if flag & 4:
                unmapped += 1
            else:
                mapped += 1

        if not lengths:
            return None

        sampled_reads = len(lengths)
        sampled_bases = sum(lengths)
        avg_length = sampled_bases / sampled_reads

        # Estimate total reads
        estimated_total = None
        if file_size and sampled_reads > 1000:
            # Rough estimate based on compression
            bytes_per_read = file_size / (len(lines) * 10)  # Assume ~10x compression
            if bytes_per_read > 0:
                estimated_total = int(file_size / bytes_per_read)

        # Calculate N50
        sorted_lengths = sorted(lengths, reverse=True)
        cumsum = 0
        n50 = 0
        target = sampled_bases / 2
        for length in sorted_lengths:
            cumsum += length
            if cumsum >= target:
                n50 = length
                break

        # Q-score distribution
        q10_count = sum(1 for q in qscores if q >= 10)
        q20_count = sum(1 for q in qscores if q >= 20)
        q30_count = sum(1 for q in qscores if q >= 30)

        return {
            "read_counts": {
                "sampled": sampled_reads,
                "estimated_total": estimated_total,
                "counted_total": None,
                "count_source": "sampled",
                "description": f"Statistics from {sampled_reads:,} streamed reads"
            },
            "base_counts": {
                "sampled_bases": sampled_bases,
                "estimated_total_bases": int(estimated_total * avg_length) if estimated_total else None,
            },
            "quality_metrics": {
                "mean_qscore": round(mean_qscore(qscores), 2) if qscores else None,
                "median_qscore": round(sorted(qscores)[len(qscores)//2], 2) if qscores else None,
                "q10_percent": round(q10_count / len(qscores) * 100, 1) if qscores else None,
                "q20_percent": round(q20_count / len(qscores) * 100, 1) if qscores else None,
                "q30_percent": round(q30_count / len(qscores) * 100, 1) if qscores else None,
                "computed_from_n_reads": len(qscores),
                "note": "Q-scores computed via probability space averaging"
            },
            "length_metrics": {
                "n50": n50,
                "mean_length": round(avg_length, 1),
                "max_length": max(lengths),
                "min_length": min(lengths),
                "median_length": sorted_lengths[len(sorted_lengths)//2],
            },
            "alignment_metrics": {
                "mapped_reads": mapped,
                "unmapped_reads": unmapped,
                "mapping_rate": round(mapped / (mapped + unmapped) * 100, 1) if (mapped + unmapped) > 0 else None,
            }
        }

    except Exception as e:
        print(f"  Error streaming BAM: {e}")
        return None


def reanalyze_experiment(exp: Dict, max_reads: int = MAX_SAMPLE_READS) -> Tuple[Dict, Dict]:
    """Re-analyze experiment from source data."""
    changes = {}
    exp_id = exp.get("id", "unknown")

    # First fix basic issues
    exp, fix_changes = fix_experiment(exp)
    changes.update(fix_changes)

    # For public data, try streaming analysis
    if exp.get("source") == "ont-open-data":
        urls = exp.get("urls", {})
        https_url = urls.get("https", "")

        if https_url:
            print(f"  Streaming from: {https_url[:70]}...")

            # Get BAM header metadata
            header_meta = stream_bam_header(https_url)
            if header_meta:
                if "metadata" not in exp:
                    exp["metadata"] = {}
                for key, value in header_meta.items():
                    if not exp["metadata"].get(key):
                        exp["metadata"][key] = value
                        changes[f"header_{key}"] = value

            # Get statistics
            stats = stream_bam_stats(https_url, max_reads)
            if stats:
                for category, values in stats.items():
                    if isinstance(values, dict):
                        exp[category] = values
                        changes[f"computed_{category}"] = True

                # Also set top-level fields for compatibility
                if stats.get("read_counts", {}).get("sampled"):
                    exp["total_reads"] = stats["read_counts"]["sampled"]
                if stats.get("base_counts", {}).get("sampled_bases"):
                    exp["total_bases"] = stats["base_counts"]["sampled_bases"]
                if stats.get("quality_metrics", {}).get("mean_qscore"):
                    exp["mean_quality"] = stats["quality_metrics"]["mean_qscore"]
                if stats.get("length_metrics", {}).get("n50"):
                    exp["n50"] = stats["length_metrics"]["n50"]

                # Update status
                exp["status"] = "analyzed"

                # Add analysis record
                if "analyses" not in exp:
                    exp["analyses"] = []
                exp["analyses"].append({
                    "type": "streaming_qc",
                    "timestamp": datetime.now().isoformat(),
                    "results": {
                        "total_reads_sampled": stats.get("read_counts", {}).get("sampled"),
                        "total_bases": stats.get("base_counts", {}).get("sampled_bases"),
                        "mean_qscore": stats.get("quality_metrics", {}).get("mean_qscore"),
                        "n50": stats.get("length_metrics", {}).get("n50"),
                    }
                })
                changes["added_analysis"] = True

    # Update provenance
    if "provenance" not in exp:
        exp["provenance"] = {}
    exp["provenance"]["last_reanalyzed"] = datetime.now().isoformat()
    exp["provenance"]["schema_version"] = "2.0"

    return exp, changes


# =============================================================================
# AUDIT AND REPORTING
# =============================================================================

def audit_registry(verbose: bool = False) -> Dict:
    """Perform comprehensive registry audit."""
    data = load_registry()
    experiments = data.get("experiments", [])

    results = {
        "timestamp": datetime.now().isoformat(),
        "total": len(experiments),
        "valid": 0,
        "invalid": 0,
        "completeness": {"good": 0, "warning": 0, "poor": 0},
        "by_source": defaultdict(int),
        "by_status": defaultdict(int),
        "missing_fields": defaultdict(int),
        "errors": [],
        "warnings": [],
        "experiments_needing_attention": [],
    }

    for exp in experiments:
        # Validation
        is_valid, errors, warnings = validate_experiment(exp)

        if is_valid:
            results["valid"] += 1
        else:
            results["invalid"] += 1
            for error in errors:
                results["errors"].append({
                    "id": exp.get("id"),
                    "name": exp.get("name", "")[:40],
                    "error": error
                })

        for warning in warnings:
            results["warnings"].append({
                "id": exp.get("id"),
                "warning": warning
            })

        # Completeness
        comp = calculate_completeness(exp)
        results["completeness"][comp["status"]] += 1

        if comp["status"] in ["warning", "poor"]:
            results["experiments_needing_attention"].append({
                "id": exp.get("id"),
                "name": exp.get("name", "")[:40],
                "completeness": comp["percentage"],
                "status": comp["status"],
                "missing": comp["missing"][:5]  # First 5 missing fields
            })

        # Counts
        results["by_source"][exp.get("source", "unknown")] += 1
        results["by_status"][exp.get("status", "unknown")] += 1

        # Missing fields
        for field in comp["missing"]:
            results["missing_fields"][field] += 1

    # Sort experiments needing attention by completeness
    results["experiments_needing_attention"].sort(key=lambda x: x["completeness"])

    return results


def print_audit_report(results: Dict):
    """Print formatted audit report."""
    print("=" * 80)
    print("REGISTRY SCRUTINY AUDIT REPORT")
    print("=" * 80)
    print(f"Generated: {results['timestamp']}")
    print()

    print("VALIDATION SUMMARY:")
    print(f"  Total experiments: {results['total']}")
    print(f"  Valid: {results['valid']} ({results['valid']/results['total']*100:.1f}%)" if results['total'] > 0 else "  Valid: 0")
    print(f"  Invalid: {results['invalid']}")
    print()

    print("COMPLETENESS DISTRIBUTION:")
    for status in ["good", "warning", "poor"]:
        count = results["completeness"][status]
        pct = count / results["total"] * 100 if results["total"] > 0 else 0
        bar = "#" * int(pct / 2)
        print(f"  {status.upper():8} {count:4} ({pct:5.1f}%) {bar}")
    print()

    print("BY SOURCE:")
    for source, count in sorted(results["by_source"].items(), key=lambda x: -x[1]):
        print(f"  {source}: {count}")
    print()

    print("BY STATUS:")
    for status, count in sorted(results["by_status"].items(), key=lambda x: -x[1]):
        print(f"  {status}: {count}")
    print()

    print("MISSING FIELDS (top 10):")
    for field, count in sorted(results["missing_fields"].items(), key=lambda x: -x[1])[:10]:
        pct = count / results["total"] * 100 if results["total"] > 0 else 0
        print(f"  {field}: {count} ({pct:.1f}%)")
    print()

    if results["errors"]:
        print(f"VALIDATION ERRORS ({len(results['errors'])}):")
        for err in results["errors"][:10]:
            print(f"  [{err['id']}] {err['error']}")
        if len(results["errors"]) > 10:
            print(f"  ... and {len(results['errors']) - 10} more")
        print()

    if results["experiments_needing_attention"]:
        print(f"EXPERIMENTS NEEDING ATTENTION ({len(results['experiments_needing_attention'])}):")
        for exp in results["experiments_needing_attention"][:15]:
            print(f"  [{exp['id']}] {exp['completeness']}% - {exp['name']}")
            print(f"      Missing: {', '.join(exp['missing'])}")
        if len(results["experiments_needing_attention"]) > 15:
            print(f"  ... and {len(results['experiments_needing_attention']) - 15} more")


# =============================================================================
# BATCH OPERATIONS
# =============================================================================

def batch_process(
    incomplete_only: bool = False,
    unanalyzed_only: bool = False,
    public_only: bool = False,
    local_only: bool = False,
    apply_fixes: bool = False,
    reanalyze: bool = False,
    limit: int = None,
    dry_run: bool = True
) -> Dict:
    """Process multiple experiments in batch."""
    data = load_registry()
    experiments = data.get("experiments", [])

    stats = {
        "processed": 0,
        "fixed": 0,
        "reanalyzed": 0,
        "unchanged": 0,
        "errors": 0,
        "changes_by_type": defaultdict(int),
    }

    # Filter experiments
    filtered = []
    for exp in experiments:
        if incomplete_only:
            comp = calculate_completeness(exp)
            if comp["status"] == "good":
                continue

        if unanalyzed_only:
            if exp.get("analyses"):
                continue

        if public_only and exp.get("source") != "ont-open-data":
            continue

        if local_only and exp.get("source") != "local":
            continue

        filtered.append(exp)

    if limit:
        filtered = filtered[:limit]

    print(f"Processing {len(filtered)} experiments...")
    if dry_run:
        print("(DRY RUN - no changes will be saved)")
    print()

    for i, exp in enumerate(filtered):
        exp_id = exp.get("id", f"unknown-{i}")
        exp_name = exp.get("name", "unnamed")[:40]

        print(f"[{i+1}/{len(filtered)}] {exp_id}: {exp_name}")

        all_changes = {}

        try:
            if apply_fixes:
                exp, changes = fix_experiment(exp)
                all_changes.update(changes)

            if reanalyze and exp.get("source") == "ont-open-data":
                exp, changes = reanalyze_experiment(exp)
                all_changes.update(changes)

            if all_changes:
                stats["fixed"] += 1
                for change_type in all_changes:
                    stats["changes_by_type"][change_type] += 1

                if not dry_run:
                    # Update in registry
                    for j, e in enumerate(data["experiments"]):
                        if e.get("id") == exp_id:
                            data["experiments"][j] = exp
                            break
                    log_audit("batch_scrutinize", exp_id, all_changes)

                print(f"  Changes: {', '.join(all_changes.keys())}")
            else:
                stats["unchanged"] += 1
                print(f"  No changes needed")

        except Exception as e:
            stats["errors"] += 1
            print(f"  ERROR: {e}")

        stats["processed"] += 1

    if not dry_run and stats["fixed"] > 0:
        save_registry(data)
        log_update({
            "action": "batch_scrutinize",
            "processed": stats["processed"],
            "fixed": stats["fixed"],
            "changes_by_type": dict(stats["changes_by_type"]),
        })
        print(f"\nSaved {stats['fixed']} changes to registry")

    return stats


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Registry Scrutinize - Deep validation and enrichment for ONT experiments"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Audit command
    audit_parser = subparsers.add_parser("audit", help="Audit registry for issues")
    audit_parser.add_argument("-v", "--verbose", action="store_true")
    audit_parser.add_argument("--json", help="Output as JSON to file")

    # Fix command
    fix_parser = subparsers.add_parser("fix", help="Fix single experiment")
    fix_parser.add_argument("exp_id", help="Experiment ID")
    fix_parser.add_argument("-n", "--dry-run", action="store_true")
    fix_parser.add_argument("--force-reanalyze", action="store_true")

    # Enrich command
    enrich_parser = subparsers.add_parser("enrich", help="Enrich metadata for experiments")
    enrich_group = enrich_parser.add_mutually_exclusive_group()
    enrich_group.add_argument("--all", action="store_true", help="Process all experiments")
    enrich_group.add_argument("--incomplete", action="store_true", help="Process only incomplete")
    enrich_parser.add_argument("-n", "--dry-run", action="store_true")

    # Reanalyze command
    reanalyze_parser = subparsers.add_parser("reanalyze", help="Re-analyze from source")
    reanalyze_parser.add_argument("exp_id", help="Experiment ID")
    reanalyze_parser.add_argument("--max-reads", type=int, default=MAX_SAMPLE_READS)
    reanalyze_parser.add_argument("-n", "--dry-run", action="store_true")

    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Batch process experiments")
    batch_parser.add_argument("--incomplete", action="store_true", help="Only incomplete entries")
    batch_parser.add_argument("--unanalyzed", action="store_true", help="Only unanalyzed entries")
    batch_parser.add_argument("--public", action="store_true", help="Only public data")
    batch_parser.add_argument("--local", action="store_true", help="Only local data")
    batch_parser.add_argument("--fix", action="store_true", help="Apply fixes")
    batch_parser.add_argument("--reanalyze", action="store_true", help="Re-analyze from source")
    batch_parser.add_argument("--limit", type=int, help="Max experiments to process")
    batch_parser.add_argument("-n", "--dry-run", action="store_true", default=True)
    batch_parser.add_argument("--apply", action="store_true", help="Actually apply changes")

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate HTML report")
    report_parser.add_argument("--output", default="registry_health.html")

    args = parser.parse_args()

    if args.command == "audit":
        results = audit_registry(args.verbose)
        if args.json:
            results["by_source"] = dict(results["by_source"])
            results["by_status"] = dict(results["by_status"])
            results["missing_fields"] = dict(results["missing_fields"])
            with open(args.json, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"Audit results saved to: {args.json}")
        else:
            print_audit_report(results)

    elif args.command == "fix":
        data = load_registry()
        exp = next((e for e in data["experiments"] if e.get("id") == args.exp_id), None)

        if not exp:
            print(f"Experiment not found: {args.exp_id}")
            return 1

        if args.force_reanalyze:
            exp, changes = reanalyze_experiment(exp)
        else:
            exp, changes = fix_experiment(exp)

        if changes:
            print(f"Changes for {args.exp_id}:")
            for k, v in changes.items():
                print(f"  {k}: {v}")

            if not args.dry_run:
                for i, e in enumerate(data["experiments"]):
                    if e.get("id") == args.exp_id:
                        data["experiments"][i] = exp
                        break
                save_registry(data)
                log_audit("scrutinize_fix", args.exp_id, changes)
                print(f"\nSaved to registry")
            else:
                print("\n(dry-run, no changes saved)")
        else:
            print("No changes needed")

    elif args.command == "enrich":
        process_all = args.all
        incomplete_only = args.incomplete

        if not process_all and not incomplete_only:
            print("Specify --all or --incomplete")
            return 1

        stats = batch_process(
            incomplete_only=incomplete_only,
            apply_fixes=True,
            reanalyze=False,
            dry_run=args.dry_run,
        )

        print(f"\nEnrichment complete:")
        print(f"  Processed: {stats['processed']}")
        print(f"  Enriched: {stats['fixed']}")
        print(f"  Unchanged: {stats['unchanged']}")

    elif args.command == "reanalyze":
        data = load_registry()
        exp = next((e for e in data["experiments"] if e.get("id") == args.exp_id), None)

        if not exp:
            print(f"Experiment not found: {args.exp_id}")
            return 1

        print(f"Re-analyzing: {exp.get('name', args.exp_id)}")
        exp, changes = reanalyze_experiment(exp, args.max_reads)

        if changes:
            print(f"\nChanges made:")
            for k, v in changes.items():
                print(f"  {k}: {v}")

            if not args.dry_run:
                for i, e in enumerate(data["experiments"]):
                    if e.get("id") == args.exp_id:
                        data["experiments"][i] = exp
                        break
                save_registry(data)
                log_audit("reanalyze", args.exp_id, changes)
                print(f"\nSaved to registry")
        else:
            print("No changes from re-analysis")

    elif args.command == "batch":
        dry_run = not args.apply
        stats = batch_process(
            incomplete_only=args.incomplete,
            unanalyzed_only=args.unanalyzed,
            public_only=args.public,
            local_only=args.local,
            apply_fixes=args.fix,
            reanalyze=args.reanalyze,
            limit=args.limit,
            dry_run=dry_run,
        )

        print(f"\nBatch processing complete:")
        print(f"  Processed: {stats['processed']}")
        print(f"  Fixed: {stats['fixed']}")
        print(f"  Unchanged: {stats['unchanged']}")
        print(f"  Errors: {stats['errors']}")

        if stats["changes_by_type"]:
            print(f"\nChanges by type:")
            for change_type, count in sorted(stats["changes_by_type"].items(), key=lambda x: -x[1]):
                print(f"  {change_type}: {count}")

    elif args.command == "report":
        results = audit_registry(verbose=True)
        # For now, print the report - HTML generation can be added later
        print_audit_report(results)
        print(f"\nReport would be saved to: {args.output}")

    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
