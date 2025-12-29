#!/usr/bin/env python3
"""
Registry Validator and Fixer

Validates and fixes registry entries to ensure:
1. All experiments have proper source classification (local vs ont-open-data)
2. Metadata is in the correct nested structure
3. All extractable metadata is populated
4. URLs are generated for public data
5. Provenance tracking is maintained

Usage:
    python registry_validator.py audit          # Show audit report
    python registry_validator.py fix            # Fix all issues
    python registry_validator.py validate <id>  # Validate single experiment
    python registry_validator.py reanalyze <id> # Re-analyze from source
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

# Configuration
REGISTRY_PATH = Path.home() / ".ont-registry" / "experiments.yaml"
AUDIT_LOG_PATH = Path.home() / ".ont-registry" / "audit_log.yaml"

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

# Metadata extraction patterns
SAMPLE_PATTERNS = [
    (r'(HG\d{3})', 'GIAB'),           # HG001, HG002, etc.
    (r'(NA\d{5})', 'GIAB'),           # NA12878, etc.
    (r'(GM\d{5})', 'Coriell'),        # GM24385, etc.
    (r'(COLO\d+)', 'Cancer'),         # COLO829
    (r'(CHM\d+)', 'Reference'),       # CHM13
]

DEVICE_PATTERNS = [
    (r'promethion|prom|P2S|PCA\d+', 'PromethION'),
    (r'minion|min|MN\d+', 'MinION'),
    (r'flongle', 'Flongle'),
    (r'gridion', 'GridION'),
    (r'MD-\d+', 'Mk1D'),  # MD-XXXXXX devices are Mk1D (run MinION/Flongle flowcells)
]

CHEMISTRY_PATTERNS = [
    (r'R10\.4\.1|r10_4_1|R1041', 'R10.4.1'),
    (r'R10\.4|r10_4|R104', 'R10.4'),
    (r'R9\.4\.1|r9_4_1|R941', 'R9.4.1'),
    (r'E8\.2|e8_2', 'E8.2'),
]

MODEL_PATTERNS = [
    (r'sup(?:er)?(?:_|\.|\s|$)', 'sup'),
    (r'hac(?:_|\.|\s|$)', 'hac'),
    (r'fast(?:_|\.|\s|$)', 'fast'),
]

FLOWCELL_PATTERN = r'(PA[A-Z]\d{5}|F[A-Z]{2}\d{5})'


def load_registry() -> Dict:
    """Load the experiment registry."""
    if not REGISTRY_PATH.exists():
        return {"version": "3.0", "experiments": []}
    with open(REGISTRY_PATH) as f:
        return yaml.safe_load(f) or {"version": "3.0", "experiments": []}


def save_registry(data: Dict):
    """Save the experiment registry."""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["updated"] = datetime.now().isoformat()
    with open(REGISTRY_PATH, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def log_audit(action: str, exp_id: str, changes: Dict):
    """Log audit changes."""
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Load existing log
    if AUDIT_LOG_PATH.exists():
        with open(AUDIT_LOG_PATH) as f:
            log = yaml.safe_load(f) or {"entries": []}
    else:
        log = {"entries": []}

    # Add entry
    log["entries"].append({
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "experiment_id": exp_id,
        "changes": changes,
    })

    # Keep last 1000 entries
    log["entries"] = log["entries"][-1000:]

    with open(AUDIT_LOG_PATH, 'w') as f:
        yaml.dump(log, f, default_flow_style=False)


def extract_metadata_from_name(name: str) -> Dict[str, Any]:
    """Extract metadata from experiment name using patterns."""
    metadata = {}
    name_lower = name.lower()

    # Extract sample
    for pattern, category in SAMPLE_PATTERNS:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            metadata["sample"] = match.group(1).upper()
            metadata["sample_category"] = category
            break

    # Extract device
    for pattern, device in DEVICE_PATTERNS:
        if re.search(pattern, name_lower):
            metadata["device_type"] = device
            break

    # Extract chemistry
    for pattern, chemistry in CHEMISTRY_PATTERNS:
        if re.search(pattern, name, re.IGNORECASE):
            metadata["chemistry"] = chemistry
            break

    # Extract basecall model
    for pattern, model in MODEL_PATTERNS:
        if re.search(pattern, name_lower):
            metadata["basecall_model"] = model
            break

    # Extract flowcell ID
    match = re.search(FLOWCELL_PATTERN, name)
    if match:
        metadata["flowcell_id"] = match.group(1)

    # Extract date from name
    date_patterns = [
        r'(\d{8})',           # YYYYMMDD or MMDDYYYY
        r'(\d{2})(\d{2})(\d{4})',  # MMDDYYYY
    ]
    for pattern in date_patterns:
        match = re.search(pattern, name)
        if match:
            try:
                date_str = match.group(0)
                if len(date_str) == 8:
                    # Try MMDDYYYY first (common in lab naming)
                    try:
                        parsed = datetime.strptime(date_str, "%m%d%Y")
                        metadata["run_date"] = parsed.strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        pass
                    # Try YYYYMMDD
                    try:
                        parsed = datetime.strptime(date_str, "%Y%m%d")
                        metadata["run_date"] = parsed.strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        pass
            except Exception:
                pass

    return metadata


def extract_metadata_from_path(path: str) -> Dict[str, Any]:
    """Extract metadata from file path."""
    if not path:
        return {}

    metadata = {}
    path_lower = path.lower()

    # Check for ONT Open Data paths
    if "ont-open-data" in path_lower or "s3://" in path:
        metadata["source"] = "ont-open-data"

        # Extract dataset
        for dataset in DATASET_LANDING_PAGES.keys():
            if dataset in path_lower:
                metadata["dataset"] = dataset
                break

    # Extract from path components
    parts = path.replace("\\", "/").split("/")
    for part in parts:
        # Check for sample patterns
        for pattern, category in SAMPLE_PATTERNS:
            match = re.search(pattern, part, re.IGNORECASE)
            if match and "sample" not in metadata:
                metadata["sample"] = match.group(1).upper()
                break

        # Check for flowcell
        match = re.search(FLOWCELL_PATTERN, part)
        if match and "flowcell_id" not in metadata:
            metadata["flowcell_id"] = match.group(1)

    return metadata


def validate_experiment(exp: Dict) -> Tuple[bool, List[str], List[str]]:
    """
    Validate an experiment and return issues and suggestions.

    Returns: (is_valid, issues, suggestions)
    """
    issues = []
    suggestions = []

    # Required fields
    if not exp.get("id"):
        issues.append("Missing experiment ID")
    if not exp.get("name"):
        issues.append("Missing experiment name")

    # Source classification
    if not exp.get("source") or exp.get("source") == "unknown":
        issues.append("Missing or unknown source")
        suggestions.append("Set source to 'local' or 'ont-open-data'")

    # Metadata structure
    metadata = exp.get("metadata", {})

    # Check for top-level fields that should be in metadata
    top_level_meta_fields = ["platform", "device_id", "flowcell_id"]
    for field in top_level_meta_fields:
        if exp.get(field) and not metadata.get(field.replace("_id", "")):
            suggestions.append(f"Migrate '{field}' to metadata")

    # Check metadata completeness
    if not metadata.get("sample"):
        issues.append("Missing sample identifier")
    if not metadata.get("device_type") and not exp.get("platform"):
        issues.append("Missing device type")
    if not metadata.get("chemistry"):
        suggestions.append("Consider extracting chemistry from name/path")
    if not metadata.get("basecall_model"):
        suggestions.append("Consider extracting basecall model")

    # Check URLs for public data
    if exp.get("source") == "ont-open-data":
        urls = exp.get("urls", {})
        if not urls.get("https"):
            issues.append("Public experiment missing HTTPS URL")
        if not urls.get("browser"):
            issues.append("Public experiment missing browser URL")

    # Check read counts
    rc = exp.get("read_counts", {})
    if not rc.get("sampled") and not exp.get("total_reads"):
        issues.append("Missing read count data")

    # Check quality metrics
    if not exp.get("quality_metrics") and not exp.get("mean_quality"):
        suggestions.append("Missing quality metrics")

    # Check for analyses
    if not exp.get("analyses"):
        suggestions.append("No analyses recorded")

    is_valid = len(issues) == 0
    return is_valid, issues, suggestions


def fix_experiment(exp: Dict, dry_run: bool = False) -> Tuple[Dict, Dict]:
    """
    Fix an experiment's metadata structure and extract missing data.

    Returns: (fixed_experiment, changes_made)
    """
    changes = {}
    original = exp.copy()

    # Ensure metadata dict exists
    if "metadata" not in exp:
        exp["metadata"] = {}
        changes["created_metadata"] = True
    metadata = exp["metadata"]

    # Fix source
    if not exp.get("source") or exp.get("source") == "unknown":
        location = exp.get("location", "")
        s3_path = metadata.get("s3_path", "")

        if "ont-open-data" in location.lower() or "ont-open-data" in s3_path.lower():
            exp["source"] = "ont-open-data"
        else:
            exp["source"] = "local"
        changes["source"] = exp["source"]

    # Migrate top-level fields to metadata
    field_migrations = {
        "platform": "device_type",
        "device_id": "device_id",
        "flowcell_id": "flowcell_id",
    }

    for old_field, new_field in field_migrations.items():
        if exp.get(old_field) and not metadata.get(new_field):
            metadata[new_field] = exp[old_field]
            changes[f"migrated_{old_field}"] = exp[old_field]

    # Extract metadata from name
    name_meta = extract_metadata_from_name(exp.get("name", ""))
    for key, value in name_meta.items():
        if not metadata.get(key):
            metadata[key] = value
            changes[f"extracted_{key}_from_name"] = value

    # Extract metadata from path
    location = exp.get("location", "")
    path_meta = extract_metadata_from_path(location)
    for key, value in path_meta.items():
        if not metadata.get(key) and key != "source":
            metadata[key] = value
            changes[f"extracted_{key}_from_path"] = value

    # Build URLs for ont-open-data sources
    if exp.get("source") == "ont-open-data":
        s3_path = metadata.get("s3_path") or metadata.get("source_key", "")
        if s3_path and not exp.get("urls", {}).get("browser"):
            # Remove leading bucket name if present
            s3_path = s3_path.replace("ont-open-data/", "")

            path_parts = s3_path.split("/")
            parent_path = "/".join(path_parts[:-1]) if len(path_parts) > 1 else s3_path

            if "urls" not in exp:
                exp["urls"] = {}

            exp["urls"]["s3"] = f"{S3_BUCKET}/{s3_path}"
            exp["urls"]["https"] = f"{HTTPS_BASE}/{s3_path}"
            exp["urls"]["browser"] = f"{BROWSER_BASE}/{parent_path}"

            # Add landing page
            dataset = metadata.get("dataset", "")
            if dataset in DATASET_LANDING_PAGES:
                exp["urls"]["landing_page"] = DATASET_LANDING_PAGES[dataset]
            elif dataset:
                slug = dataset.replace("_", "-").replace(".", "-")
                exp["urls"]["landing_page"] = f"{LANDING_PAGE_BASE}/{slug}/"

            changes["generated_urls"] = True

    # Migrate legacy quality/length metrics to structured format
    if exp.get("mean_quality") and not exp.get("quality_metrics"):
        exp["quality_metrics"] = {
            "mean_qscore": exp["mean_quality"],
            "note": "Migrated from legacy mean_quality field"
        }
        changes["migrated_quality_metrics"] = True

    if exp.get("n50") and not exp.get("length_metrics"):
        exp["length_metrics"] = {
            "n50": exp["n50"],
        }
        if exp.get("total_bases") and exp.get("total_reads"):
            exp["length_metrics"]["mean_length"] = exp["total_bases"] / exp["total_reads"]
        changes["migrated_length_metrics"] = True

    # Ensure read_counts structure
    if not exp.get("read_counts") and exp.get("total_reads"):
        exp["read_counts"] = {
            "sampled": exp["total_reads"],
            "estimated_total": None,
            "counted_total": None,
            "count_source": "legacy",
            "description": "Migrated from legacy total_reads field"
        }
        changes["migrated_read_counts"] = True

    # Update provenance
    if "provenance" not in exp:
        exp["provenance"] = {}
    exp["provenance"]["schema_version"] = "2.0"
    exp["provenance"]["last_validated"] = datetime.now().isoformat()
    if changes:
        exp["provenance"]["last_fixed"] = datetime.now().isoformat()

    return exp, changes


def audit_registry(verbose: bool = False) -> Dict:
    """Perform a comprehensive audit of the registry."""
    data = load_registry()
    experiments = data.get("experiments", [])

    results = {
        "total": len(experiments),
        "valid": 0,
        "invalid": 0,
        "by_source": defaultdict(int),
        "by_status": defaultdict(int),
        "missing_fields": defaultdict(int),
        "issues": [],
        "suggestions": [],
    }

    for exp in experiments:
        is_valid, issues, suggestions = validate_experiment(exp)

        if is_valid:
            results["valid"] += 1
        else:
            results["invalid"] += 1
            results["issues"].extend([
                {"id": exp.get("id"), "issue": issue}
                for issue in issues
            ])

        results["suggestions"].extend([
            {"id": exp.get("id"), "suggestion": s}
            for s in suggestions
        ])

        # Count by source
        source = exp.get("source", "unknown")
        results["by_source"][source] += 1

        # Count by status
        status = exp.get("status", "unknown")
        results["by_status"][status] += 1

        # Count missing fields
        metadata = exp.get("metadata", {})
        for field in ["sample", "device_type", "chemistry", "basecall_model", "flowcell_id"]:
            if not metadata.get(field) and not exp.get(field.replace("_type", "")):
                results["missing_fields"][field] += 1

    return results


def fix_all_experiments(dry_run: bool = False) -> Dict:
    """Fix all experiments in the registry."""
    data = load_registry()
    experiments = data.get("experiments", [])

    stats = {
        "total": len(experiments),
        "fixed": 0,
        "unchanged": 0,
        "all_changes": [],
    }

    for i, exp in enumerate(experiments):
        fixed_exp, changes = fix_experiment(exp, dry_run)

        if changes:
            stats["fixed"] += 1
            stats["all_changes"].append({
                "id": exp.get("id"),
                "name": exp.get("name"),
                "changes": changes,
            })

            if not dry_run:
                experiments[i] = fixed_exp
                log_audit("fix", exp.get("id", "unknown"), changes)
        else:
            stats["unchanged"] += 1

    if not dry_run:
        data["experiments"] = experiments
        data["schema_version"] = "2.0"
        save_registry(data)

    return stats


def print_audit_report(results: Dict):
    """Print a formatted audit report."""
    print("=" * 70)
    print("REGISTRY AUDIT REPORT")
    print("=" * 70)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    print("SUMMARY:")
    print(f"  Total experiments: {results['total']}")
    print(f"  Valid: {results['valid']} ({results['valid']/results['total']*100:.1f}%)")
    print(f"  Invalid: {results['invalid']} ({results['invalid']/results['total']*100:.1f}%)")
    print()

    print("BY SOURCE:")
    for source, count in sorted(results["by_source"].items(), key=lambda x: -x[1]):
        print(f"  {source}: {count}")
    print()

    print("MISSING FIELDS:")
    for field, count in sorted(results["missing_fields"].items(), key=lambda x: -x[1]):
        pct = count / results["total"] * 100
        print(f"  {field}: {count} ({pct:.1f}%)")
    print()

    # Group issues by type
    issue_counts = defaultdict(int)
    for item in results["issues"]:
        issue_counts[item["issue"]] += 1

    print("ISSUES BY TYPE:")
    for issue, count in sorted(issue_counts.items(), key=lambda x: -x[1]):
        print(f"  {issue}: {count}")
    print()

    # Group suggestions by type
    suggestion_counts = defaultdict(int)
    for item in results["suggestions"]:
        suggestion_counts[item["suggestion"]] += 1

    print("SUGGESTIONS BY TYPE:")
    for suggestion, count in sorted(suggestion_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {suggestion}: {count}")


def print_fix_report(stats: Dict, verbose: bool = False):
    """Print a formatted fix report."""
    print("=" * 70)
    print("REGISTRY FIX REPORT")
    print("=" * 70)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    print("SUMMARY:")
    print(f"  Total experiments: {stats['total']}")
    print(f"  Fixed: {stats['fixed']}")
    print(f"  Unchanged: {stats['unchanged']}")
    print()

    # Count changes by type
    change_counts = defaultdict(int)
    for item in stats["all_changes"]:
        for change_type in item["changes"].keys():
            change_counts[change_type] += 1

    print("CHANGES BY TYPE:")
    for change_type, count in sorted(change_counts.items(), key=lambda x: -x[1]):
        print(f"  {change_type}: {count}")

    if verbose and stats["all_changes"]:
        print()
        print("DETAILED CHANGES:")
        for item in stats["all_changes"][:20]:
            print(f"\n  {item['id']} ({item['name'][:40]}...):")
            for k, v in item["changes"].items():
                print(f"    {k}: {v}")


def main():
    parser = argparse.ArgumentParser(description="Registry Validator and Fixer")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Audit command
    audit_parser = subparsers.add_parser("audit", help="Audit the registry")
    audit_parser.add_argument("-v", "--verbose", action="store_true")
    audit_parser.add_argument("--json", help="Output as JSON to file")

    # Fix command
    fix_parser = subparsers.add_parser("fix", help="Fix registry issues")
    fix_parser.add_argument("-n", "--dry-run", action="store_true",
                           help="Show what would be fixed without making changes")
    fix_parser.add_argument("-v", "--verbose", action="store_true")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate single experiment")
    validate_parser.add_argument("id", help="Experiment ID")

    args = parser.parse_args()

    if args.command == "audit":
        results = audit_registry(args.verbose)
        if args.json:
            # Convert defaultdicts to regular dicts for JSON
            results["by_source"] = dict(results["by_source"])
            results["by_status"] = dict(results["by_status"])
            results["missing_fields"] = dict(results["missing_fields"])
            with open(args.json, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"Audit results saved to: {args.json}")
        else:
            print_audit_report(results)

    elif args.command == "fix":
        if args.dry_run:
            print("DRY RUN - No changes will be made\n")
        stats = fix_all_experiments(dry_run=args.dry_run)
        print_fix_report(stats, args.verbose)
        if not args.dry_run:
            print(f"\nChanges logged to: {AUDIT_LOG_PATH}")

    elif args.command == "validate":
        data = load_registry()
        exp = next((e for e in data["experiments"] if e.get("id") == args.id), None)
        if not exp:
            print(f"Experiment not found: {args.id}")
            return 1

        is_valid, issues, suggestions = validate_experiment(exp)
        print(f"Experiment: {exp.get('name')}")
        print(f"ID: {exp.get('id')}")
        print(f"Valid: {is_valid}")
        if issues:
            print("\nIssues:")
            for issue in issues:
                print(f"  - {issue}")
        if suggestions:
            print("\nSuggestions:")
            for s in suggestions:
                print(f"  - {s}")

    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
