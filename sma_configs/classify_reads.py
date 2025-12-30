#!/usr/bin/env python3
"""
SMA-seq Read Classification by Size and Edit Distance

Classification Algorithm:
1. Filter by read length (min_read_length to max_read_length)
2. For each barcode, get the expected target from mapping
3. If read length falls within target's size range AND only that target -> direct assign
4. If multiple targets have overlapping ranges containing this length -> use edit distance
5. Assign to target with lowest Levenshtein edit distance

Usage:
    python classify_reads.py --barcode barcode16 --sequence ACGT... --experiment 10092025_IF_methyl_minus_SMA_seq
    python classify_reads.py --config size_sequence_mapping.yaml --test
"""

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: pyyaml required. Install with: pip install pyyaml")
    sys.exit(1)

try:
    import edlib
    HAS_EDLIB = True
except ImportError:
    HAS_EDLIB = False


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if HAS_EDLIB:
        # Use edlib for fast edit distance (supports alignment)
        result = edlib.align(s1.upper(), s2.upper(), mode="NW", task="distance")
        return result['editDistance']
    else:
        # Pure Python fallback (slower for long sequences)
        if len(s1) < len(s2):
            s1, s2 = s2, s1
        if len(s2) == 0:
            return len(s1)

        prev_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1.upper()):
            curr_row = [i + 1]
            for j, c2 in enumerate(s2.upper()):
                insertions = prev_row[j + 1] + 1
                deletions = curr_row[j] + 1
                substitutions = prev_row[j] + (c1 != c2)
                curr_row.append(min(insertions, deletions, substitutions))
            prev_row = curr_row
        return prev_row[-1]


def load_mapping(config_path: str) -> dict:
    """Load size-sequence mapping configuration."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_target_for_barcode(mapping: dict, experiment: str, barcode: str) -> dict | None:
    """Get target info for a barcode in an experiment."""
    if experiment not in mapping.get('experiments', {}):
        return None

    exp_config = mapping['experiments'][experiment]
    barcode_mapping = exp_config.get('barcode_mapping', {})

    if barcode not in barcode_mapping:
        return None

    target_id = barcode_mapping[barcode]['target']
    target_info = mapping['targets'].get(target_id)

    if target_info:
        return {
            'target_id': target_id,
            'alias': barcode_mapping[barcode].get('alias'),
            **target_info
        }
    return None


def get_candidates_by_size(mapping: dict, experiment: str, read_length: int) -> list[dict]:
    """Get all targets where read_length falls within their size range."""
    if experiment not in mapping.get('experiments', {}):
        return []

    exp_config = mapping['experiments'][experiment]
    barcode_mapping = exp_config.get('barcode_mapping', {})

    # Get unique targets in this experiment
    target_ids = set(bc['target'] for bc in barcode_mapping.values())

    candidates = []
    for target_id in target_ids:
        target = mapping['targets'].get(target_id)
        if target:
            size_range = target['size_range']
            if size_range['min'] <= read_length <= size_range['max']:
                candidates.append({
                    'target_id': target_id,
                    **target
                })

    return candidates


def classify_read(mapping: dict, experiment: str, barcode: str, sequence: str) -> dict:
    """
    Classify a read to its target based on size and edit distance.

    Returns:
        dict with keys:
            - target_id: assigned target
            - method: 'direct' (barcode only), 'size' (unique size match), 'edit_distance'
            - edit_distance: distance to assigned target (if computed)
            - candidates: list of candidate targets considered
            - confidence: 'high' (unique match), 'medium' (clear winner), 'low' (close call)
    """
    read_length = len(sequence)

    # Get expected target for this barcode
    expected = get_target_for_barcode(mapping, experiment, barcode)
    if not expected:
        return {
            'target_id': None,
            'method': 'unknown_barcode',
            'error': f"Unknown barcode {barcode} in experiment {experiment}"
        }

    # Check if read length is within valid range
    config = mapping.get('classification', {})
    min_len = config.get('min_read_length', 80)
    max_len = config.get('max_read_length', 200)

    if read_length < min_len or read_length > max_len:
        return {
            'target_id': None,
            'method': 'filtered',
            'reason': f"Read length {read_length} outside valid range [{min_len}, {max_len}]"
        }

    # Get all targets that match this size
    candidates = get_candidates_by_size(mapping, experiment, read_length)

    if len(candidates) == 0:
        return {
            'target_id': None,
            'method': 'no_size_match',
            'reason': f"No targets match read length {read_length}"
        }

    if len(candidates) == 1:
        # Unique size match - still verify it's the expected target
        matched = candidates[0]
        ed = levenshtein_distance(sequence, matched['sequence'])
        return {
            'target_id': matched['target_id'],
            'method': 'size',
            'edit_distance': ed,
            'expected_target': expected['target_id'],
            'confidence': 'high' if matched['target_id'] == expected['target_id'] else 'mismatch'
        }

    # Multiple candidates - use edit distance
    results = []
    for candidate in candidates:
        ed = levenshtein_distance(sequence, candidate['sequence'])
        results.append({
            'target_id': candidate['target_id'],
            'edit_distance': ed,
            'expected_length': candidate['expected_length']
        })

    # Sort by edit distance, then by sequence length (prefer shorter on tie)
    results.sort(key=lambda x: (x['edit_distance'], x['expected_length']))

    winner = results[0]
    runner_up = results[1] if len(results) > 1 else None

    # Determine confidence
    if runner_up is None:
        confidence = 'high'
    elif winner['edit_distance'] < runner_up['edit_distance'] * 0.8:
        confidence = 'high'
    elif winner['edit_distance'] < runner_up['edit_distance']:
        confidence = 'medium'
    else:
        confidence = 'low'  # Tie or very close

    return {
        'target_id': winner['target_id'],
        'method': 'edit_distance',
        'edit_distance': winner['edit_distance'],
        'expected_target': expected['target_id'],
        'candidates': results[:3],  # Top 3 candidates
        'confidence': confidence,
        'matches_expected': winner['target_id'] == expected['target_id']
    }


def classify_batch(mapping: dict, experiment: str, reads: list[tuple[str, str]]) -> list[dict]:
    """
    Classify a batch of reads.

    Args:
        mapping: loaded configuration
        experiment: experiment ID
        reads: list of (barcode, sequence) tuples

    Returns:
        list of classification results
    """
    return [classify_read(mapping, experiment, barcode, seq) for barcode, seq in reads]


def test_classification(mapping: dict):
    """Run test cases to verify classification works."""
    print("=== Classification Test ===\n")

    # Test with 10092025_IF_methyl_minus_SMA_seq experiment
    experiment = "10092025_IF_methyl_minus_SMA_seq"

    print(f"Experiment: {experiment}\n")

    # Get a sample target sequence for testing
    test_cases = [
        ("barcode16", mapping['targets']['V0-15']['sequence']),  # Exact match
        ("barcode17", mapping['targets']['V0-16']['sequence']),  # Exact match
        ("barcode19", mapping['targets']['V0-18']['sequence']),  # V0-18 in barcode19 slot
    ]

    for barcode, seq in test_cases:
        result = classify_read(mapping, experiment, barcode, seq)
        print(f"Barcode: {barcode}")
        print(f"  Sequence length: {len(seq)}")
        print(f"  Assigned target: {result.get('target_id')}")
        print(f"  Expected target: {result.get('expected_target')}")
        print(f"  Method: {result.get('method')}")
        print(f"  Edit distance: {result.get('edit_distance')}")
        print(f"  Confidence: {result.get('confidence')}")
        if 'candidates' in result:
            print(f"  Candidates: {[c['target_id'] for c in result['candidates']]}")
        print()

    # Test with a modified sequence (simulate sequencing errors)
    print("=== Error Tolerance Test ===\n")
    original = mapping['targets']['V0-15']['sequence']

    # Add some errors
    modified = original[:10] + 'N' + original[11:30] + 'A' + original[31:]  # 2 substitutions

    result = classify_read(mapping, experiment, "barcode16", modified)
    print(f"Original V0-15 with 2 errors:")
    print(f"  Assigned: {result.get('target_id')}")
    print(f"  Edit distance: {result.get('edit_distance')}")
    print(f"  Method: {result.get('method')}")
    print(f"  Confidence: {result.get('confidence')}")


def print_experiment_summary(mapping: dict, experiment: str):
    """Print summary of barcode-target mappings for an experiment."""
    if experiment not in mapping.get('experiments', {}):
        print(f"Unknown experiment: {experiment}")
        return

    exp = mapping['experiments'][experiment]
    print(f"\n=== {experiment} ===")
    print(f"Description: {exp.get('description', 'N/A')}")
    print(f"\nBarcode -> Target Mapping:")
    print("-" * 50)

    for barcode, info in sorted(exp['barcode_mapping'].items()):
        target = info['target']
        alias = info.get('alias', '')
        target_info = mapping['targets'].get(target, {})
        exp_len = target_info.get('expected_length', '?')
        print(f"  {barcode:12} -> {target:8} ({alias:8}) expected: {exp_len}bp")


def main():
    parser = argparse.ArgumentParser(description='SMA-seq Read Classification')
    parser.add_argument('--config', default='targets/size_sequence_mapping.yaml',
                       help='Path to mapping configuration')
    parser.add_argument('--experiment', help='Experiment ID')
    parser.add_argument('--barcode', help='Barcode ID (e.g., barcode16)')
    parser.add_argument('--sequence', help='Read sequence to classify')
    parser.add_argument('--test', action='store_true', help='Run test cases')
    parser.add_argument('--list-experiments', action='store_true',
                       help='List available experiments')
    parser.add_argument('--show-mapping', help='Show mapping for an experiment')

    args = parser.parse_args()

    # Find config file
    config_path = Path(args.config)
    if not config_path.exists():
        # Try relative to script location
        script_dir = Path(__file__).parent
        config_path = script_dir / args.config

    if not config_path.exists():
        print(f"Error: Config file not found: {args.config}")
        sys.exit(1)

    mapping = load_mapping(config_path)

    if args.list_experiments:
        print("Available experiments:")
        for exp in mapping.get('experiments', {}):
            print(f"  - {exp}")
        return

    if args.show_mapping:
        print_experiment_summary(mapping, args.show_mapping)
        return

    if args.test:
        test_classification(mapping)
        return

    if args.experiment and args.barcode and args.sequence:
        result = classify_read(mapping, args.experiment, args.barcode, args.sequence)
        print(yaml.dump(result, default_flow_style=False))
        return

    parser.print_help()


if __name__ == '__main__':
    main()
