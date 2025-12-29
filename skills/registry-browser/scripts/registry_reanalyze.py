#!/usr/bin/env python3
"""
Registry Re-analyzer

Re-analyzes experiments from their source data to:
1. Extract comprehensive metadata from BAM headers
2. Update quality metrics with proper probability-space averaging
3. Compute accurate read statistics
4. Validate existing data

Usage:
    python registry_reanalyze.py <exp_id>              # Re-analyze single experiment
    python registry_reanalyze.py --public-all          # Re-analyze all public experiments
    python registry_reanalyze.py --update-metadata     # Update metadata from paths/names
"""

import argparse
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

# Configuration
REGISTRY_PATH = Path.home() / ".ont-registry" / "experiments.yaml"
AUDIT_LOG_PATH = Path.home() / ".ont-registry" / "audit_log.yaml"
AWS_CMD = os.path.expanduser("~/.local/bin/aws")
MAX_SAMPLE_READS = 50000

# URL constants
S3_BUCKET = "s3://ont-open-data"
HTTPS_BASE = "https://ont-open-data.s3.amazonaws.com"
BROWSER_BASE = "https://42basepairs.com/browse/s3/ont-open-data"

# Enhanced metadata patterns
SAMPLE_PATTERNS = [
    # GIAB samples
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
    # Cancer cell lines
    (r'\b(COLO829)\b', 'COLO829', 'Cancer', None),
    (r'\b(HCC1395)\b', 'HCC1395', 'Cancer', None),
    (r'\b(HCC1937)\b', 'HCC1937', 'Cancer', None),
    # Reference genomes
    (r'\b(CHM13)\b', 'CHM13', 'Reference', None),
    # Cell lines
    (r'\b(jurkat)\b', 'Jurkat', 'Cell Line', None),
    (r'\b(293t|hek293)\b', 'HEK293T', 'Cell Line', None),
    (r'\b(hela)\b', 'HeLa', 'Cell Line', None),
    # Zymo
    (r'\bzymo\b', 'Zymo Mock', 'Microbial', None),
]

DEVICE_PATTERNS = [
    (r'promethion|PromethION|P2(?:\s+Solo)?|PCA\d+', 'PromethION'),
    (r'minion|MinION|MN\d+', 'MinION'),
    (r'flongle|Flongle', 'Flongle'),
    (r'gridion|GridION', 'GridION'),
    (r'MD-\d+', 'Mk1D'),  # MD-XXXXXX devices are Mk1D (run MinION/Flongle flowcells)
]

CHEMISTRY_PATTERNS = [
    (r'R10\.4\.1|r10_4_1|R1041|r1041|10\.4\.1', 'R10.4.1'),
    (r'R10\.4|r10_4|R104|r104(?!\.1)', 'R10.4'),
    (r'R9\.4\.1|r9_4_1|R941|r941', 'R9.4.1'),
    (r'E8\.2|e8_2|E82', 'E8.2'),
    (r'FLO-PRO114M', 'R10.4.1'),  # Flowcell type indicates chemistry
    (r'FLO-PRO002', 'R9.4.1'),
]

MODEL_PATTERNS = [
    (r'\bsup(?:er)?(?:_v?\d+(?:\.\d+)*)?(?:@|_|\.|\b)', 'sup'),
    (r'\bhac(?:_v?\d+(?:\.\d+)*)?(?:@|_|\.|\b)', 'hac'),
    (r'\bfast(?:_v?\d+(?:\.\d+)*)?(?:@|_|\.|\b)', 'fast'),
    (r'dna_r10\.4\.1_e8\.2_400bps_sup', 'sup'),
    (r'dna_r10\.4\.1_e8\.2_400bps_hac', 'hac'),
    (r'dna_r10\.4\.1_e8\.2_400bps_fast', 'fast'),
    (r'd052sup430', 'sup'),
    (r'd052hac430', 'hac'),
]

MODIFICATION_PATTERNS = [
    (r'5mCG_5hmCG|5mC_5hmC', ['5mCG', '5hmCG']),
    (r'5mCG(?!_5hmCG)|5mC(?!_5hmC)', ['5mCG']),
    (r'6mA', ['6mA']),
    (r'meth|methyl', ['methylation']),
]

KIT_PATTERNS = [
    (r'SQK-LSK114', 'SQK-LSK114'),
    (r'SQK-LSK109', 'SQK-LSK109'),
    (r'SQK-NBD114', 'SQK-NBD114'),
    (r'SQK-RBK114', 'SQK-RBK114'),
]


def load_registry() -> Dict:
    """Load the experiment registry."""
    if not REGISTRY_PATH.exists():
        return {"version": "3.0", "experiments": []}
    with open(REGISTRY_PATH) as f:
        return yaml.safe_load(f) or {"version": "3.0", "experiments": []}


def save_registry(data: Dict):
    """Save the experiment registry."""
    data["updated"] = datetime.now().isoformat()
    with open(REGISTRY_PATH, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def log_audit(action: str, exp_id: str, changes: Dict):
    """Log audit changes."""
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
    })

    log["entries"] = log["entries"][-1000:]

    with open(AUDIT_LOG_PATH, 'w') as f:
        yaml.dump(log, f, default_flow_style=False)


def _mean_qscore(qscores: List[float]) -> float:
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


def extract_enhanced_metadata(exp: Dict) -> Dict[str, Any]:
    """Extract metadata using all available information."""
    updates = {}
    metadata = exp.get("metadata", {})

    # Combine all text sources
    text_sources = [
        exp.get("name", ""),
        exp.get("location", ""),
        metadata.get("s3_path", ""),
        metadata.get("source_key", ""),
        str(exp.get("urls", {})),
    ]
    combined_text = " ".join(text_sources)

    # Extract sample
    if not metadata.get("sample"):
        for pattern, sample, category, alt_name in SAMPLE_PATTERNS:
            if re.search(pattern, combined_text, re.IGNORECASE):
                updates["sample"] = sample
                updates["sample_category"] = category
                if alt_name:
                    updates["sample_alt_name"] = alt_name
                break

    # Extract device type
    if not metadata.get("device_type"):
        # First check top-level platform field
        platform = exp.get("platform", "")
        if platform:
            for pattern, device in DEVICE_PATTERNS:
                if re.search(pattern, platform, re.IGNORECASE):
                    updates["device_type"] = device
                    break
        # Then check combined text
        if "device_type" not in updates:
            for pattern, device in DEVICE_PATTERNS:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    updates["device_type"] = device
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

    # Extract flowcell ID if not present
    if not metadata.get("flowcell_id") and not exp.get("flowcell_id"):
        match = re.search(r'(PA[A-Z]\d{5}|FB[A-Z]\d{5}|PB[A-Z]\d{5})', combined_text)
        if match:
            updates["flowcell_id"] = match.group(1)

    return updates


def stream_bam_header(bam_url: str) -> Optional[Dict]:
    """Stream just the BAM header to extract metadata."""
    try:
        cmd = f"samtools view -H {bam_url} 2>/dev/null | head -100"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            return None

        header = result.stdout
        metadata = {}

        # Parse @RG (read group) lines
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
                        # Description often contains basecaller info
                        desc = part[3:]
                        if 'dorado' in desc.lower():
                            metadata['basecaller'] = 'dorado'
                            # Extract version
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
                        # Command line often has model info
                        cmdline = part[3:]
                        for pattern, model in MODEL_PATTERNS:
                            if re.search(pattern, cmdline, re.IGNORECASE):
                                metadata['basecall_model'] = model
                                break

            elif line.startswith('@SQ'):
                # Reference info
                parts = line.split('\t')
                for part in parts[1:]:
                    if part.startswith('SN:'):
                        seq_name = part[3:]
                        if 'chr' in seq_name.lower():
                            if 'grch38' in header.lower() or 'hg38' in header.lower():
                                metadata['reference'] = 'GRCh38'
                            elif 'chm13' in header.lower() or 't2t' in header.lower():
                                metadata['reference'] = 'CHM13-T2T'

        return metadata if metadata else None

    except Exception as e:
        print(f"  Warning: Could not read BAM header: {e}")
        return None


def stream_bam_stats(bam_url: str, max_reads: int = MAX_SAMPLE_READS) -> Optional[Dict]:
    """Stream BAM file to compute statistics."""
    try:
        # Get file size first
        if bam_url.startswith("https://"):
            size_cmd = f"curl -sI {bam_url} | grep -i content-length | awk '{{print $2}}' | tr -d '\\r'"
            result = subprocess.run(size_cmd, shell=True, capture_output=True, text=True, timeout=30)
            file_size = int(result.stdout.strip()) if result.stdout.strip().isdigit() else None
        else:
            file_size = None

        # Stream reads
        cmd = f"samtools view {bam_url} 2>/dev/null | head -{max_reads}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)

        if result.returncode != 0 or not result.stdout.strip():
            return None

        # Parse reads
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

            # Calculate mean Q-score for this read
            if qual != '*':
                read_qscores = [ord(c) - 33 for c in qual]
                if read_qscores:
                    qscores.append(_mean_qscore(read_qscores))

            # Check mapping
            if flag & 4:  # Unmapped
                unmapped += 1
            else:
                mapped += 1

        if not lengths:
            return None

        sampled_reads = len(lengths)
        sampled_bases = sum(lengths)
        mean_length = sampled_bases / sampled_reads

        # Estimate total reads from file size
        estimated_total = None
        if file_size and sampled_reads > 0:
            bytes_per_read = file_size * (sampled_reads / len(lines)) / sampled_reads if len(lines) > 0 else None
            if bytes_per_read and bytes_per_read > 0:
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
                "estimated_total_bases": int(estimated_total * mean_length) if estimated_total else None,
            },
            "quality_metrics": {
                "mean_qscore": round(_mean_qscore(qscores), 2) if qscores else None,
                "median_qscore": round(sorted(qscores)[len(qscores)//2], 2) if qscores else None,
                "q10_percent": round(q10_count / len(qscores) * 100, 1) if qscores else None,
                "q20_percent": round(q20_count / len(qscores) * 100, 1) if qscores else None,
                "q30_percent": round(q30_count / len(qscores) * 100, 1) if qscores else None,
                "computed_from_n_reads": len(qscores),
                "note": "Q-scores computed via probability space averaging"
            },
            "length_metrics": {
                "n50": n50,
                "mean_length": round(mean_length, 1),
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


def reanalyze_experiment(exp: Dict, update_stats: bool = True) -> Tuple[Dict, Dict]:
    """Re-analyze an experiment from its source data."""
    changes = {}
    exp_id = exp.get("id", "unknown")
    name = exp.get("name", "unknown")

    print(f"\nRe-analyzing: {name}")
    print(f"  ID: {exp_id}")

    # Ensure metadata dict
    if "metadata" not in exp:
        exp["metadata"] = {}
        changes["created_metadata"] = True

    # Extract enhanced metadata from name/path
    meta_updates = extract_enhanced_metadata(exp)
    if meta_updates:
        for key, value in meta_updates.items():
            if not exp["metadata"].get(key):
                exp["metadata"][key] = value
                changes[f"extracted_{key}"] = value
                print(f"  Extracted {key}: {value}")

    # For public data, try to get BAM header and stats
    if exp.get("source") == "ont-open-data":
        urls = exp.get("urls", {})
        https_url = urls.get("https", "")

        if https_url and update_stats:
            print(f"  Streaming from: {https_url[:60]}...")

            # Get BAM header metadata
            header_meta = stream_bam_header(https_url)
            if header_meta:
                for key, value in header_meta.items():
                    if not exp["metadata"].get(key):
                        exp["metadata"][key] = value
                        changes[f"header_{key}"] = value
                        print(f"  From header - {key}: {value}")

            # Get statistics
            stats = stream_bam_stats(https_url)
            if stats:
                for category, values in stats.items():
                    if isinstance(values, dict):
                        if category not in exp or not exp[category]:
                            exp[category] = values
                            changes[f"computed_{category}"] = True
                            print(f"  Computed {category}")

    # Update provenance
    if "provenance" not in exp:
        exp["provenance"] = {}
    exp["provenance"]["last_reanalyzed"] = datetime.now().isoformat()
    exp["provenance"]["schema_version"] = "2.0"

    return exp, changes


def update_all_metadata(dry_run: bool = False) -> Dict:
    """Update metadata for all experiments using enhanced extraction."""
    data = load_registry()
    experiments = data.get("experiments", [])

    stats = {
        "total": len(experiments),
        "updated": 0,
        "unchanged": 0,
        "by_field": defaultdict(int),
    }

    for i, exp in enumerate(experiments):
        meta_updates = extract_enhanced_metadata(exp)

        if meta_updates:
            stats["updated"] += 1
            for key in meta_updates:
                stats["by_field"][key] += 1

            if not dry_run:
                if "metadata" not in exp:
                    exp["metadata"] = {}
                for key, value in meta_updates.items():
                    exp["metadata"][key] = value
                experiments[i] = exp
                log_audit("metadata_update", exp.get("id", "unknown"), meta_updates)
        else:
            stats["unchanged"] += 1

    if not dry_run:
        data["experiments"] = experiments
        save_registry(data)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Registry Re-analyzer")
    parser.add_argument("exp_id", nargs="?", help="Experiment ID to re-analyze")
    parser.add_argument("--public-all", action="store_true",
                       help="Re-analyze all public experiments")
    parser.add_argument("--update-metadata", action="store_true",
                       help="Update metadata for all experiments from names/paths")
    parser.add_argument("--no-stats", action="store_true",
                       help="Skip streaming statistics (faster)")
    parser.add_argument("-n", "--dry-run", action="store_true",
                       help="Show what would be done without making changes")

    args = parser.parse_args()

    if args.update_metadata:
        print("Updating metadata for all experiments...")
        if args.dry_run:
            print("(DRY RUN - no changes will be made)")

        stats = update_all_metadata(dry_run=args.dry_run)

        print(f"\nResults:")
        print(f"  Total: {stats['total']}")
        print(f"  Updated: {stats['updated']}")
        print(f"  Unchanged: {stats['unchanged']}")
        print(f"\nUpdates by field:")
        for field, count in sorted(stats["by_field"].items(), key=lambda x: -x[1]):
            print(f"  {field}: {count}")

    elif args.public_all:
        data = load_registry()
        public_exps = [e for e in data["experiments"] if e.get("source") == "ont-open-data"]
        print(f"Re-analyzing {len(public_exps)} public experiments...")

        for i, exp in enumerate(public_exps):
            exp, changes = reanalyze_experiment(exp, update_stats=not args.no_stats)

            if changes and not args.dry_run:
                # Update in registry
                for j, e in enumerate(data["experiments"]):
                    if e.get("id") == exp.get("id"):
                        data["experiments"][j] = exp
                        break
                log_audit("reanalyze", exp.get("id", "unknown"), changes)

        if not args.dry_run:
            save_registry(data)
            print(f"\nSaved changes to registry")

    elif args.exp_id:
        data = load_registry()
        exp = next((e for e in data["experiments"] if e.get("id") == args.exp_id), None)

        if not exp:
            print(f"Experiment not found: {args.exp_id}")
            return 1

        exp, changes = reanalyze_experiment(exp, update_stats=not args.no_stats)

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
            print("\nNo changes needed")

    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
