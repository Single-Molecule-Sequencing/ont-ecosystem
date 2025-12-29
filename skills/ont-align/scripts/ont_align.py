#!/usr/bin/env python3
"""
ONT Align - Alignment & Edit Distance Toolkit

Alignment, reference management, BAM QC, and Levenshtein edit distance computation
for Oxford Nanopore sequencing data.

Usage:
  ont_align.py align <input> --reference <ref> --output <bam>
  ont_align.py refs list
  ont_align.py qc <bam> --json stats.json
  ont_align.py editdist <seq1> <seq2>
  ont_align.py editdist --query file.fa --target ref.fa --output distances.tsv
"""

import argparse
import json
import os
import sys
import subprocess
import hashlib
import gzip
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple, Iterator, Union
from collections import defaultdict
import re
import time

# Optional imports with graceful fallback
try:
    import edlib
    HAS_EDLIB = True
except ImportError:
    HAS_EDLIB = False

try:
    import pysam
    HAS_PYSAM = True
except ImportError:
    HAS_PYSAM = False

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
    HAS_CONCURRENT = True
except ImportError:
    HAS_CONCURRENT = False


# =============================================================================
# Configuration
# =============================================================================

REGISTRY_DIR = Path.home() / ".ont-registry"
REFERENCES_FILE = REGISTRY_DIR / "references.yaml"
REFERENCES_VERSION = "1.0"

# Standard reference downloads
STANDARD_REFERENCES = {
    "grch38": {
        "name": "GRCh38",
        "url": "https://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/000/001/405/GCA_000001405.15_GRCh38/seqs_for_alignment_pipelines.ucsc_ids/GCA_000001405.15_GRCh38_no_alt_analysis_set.fna.gz",
        "description": "Human reference genome GRCh38 (no alt)",
        "species": "Homo sapiens",
    },
    "grch37": {
        "name": "GRCh37",
        "url": "https://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/000/001/405/GCA_000001405.14_GRCh37.p13/seqs_for_alignment_pipelines.ucsc_ids/GCA_000001405.14_GRCh37.p13_no_alt_analysis_set.fna.gz",
        "description": "Human reference genome GRCh37/hg19 (no alt)",
        "species": "Homo sapiens",
    },
    "t2t": {
        "name": "T2T-CHM13",
        "url": "https://s3-us-west-2.amazonaws.com/human-pangenomics/T2T/CHM13/assemblies/analysis_set/chm13v2.0.fa.gz",
        "description": "Telomere-to-Telomere CHM13 v2.0",
        "species": "Homo sapiens",
    },
}

# Minimap2 presets
MINIMAP2_PRESETS = {
    "map-ont": "Standard ONT reads",
    "lr:hq": "High-quality long reads (Q20+)",
    "splice": "Spliced alignment (direct RNA)",
    "splice:hq": "Spliced alignment, high-quality",
    "asm5": "Assembly-to-reference (<5% divergence)",
    "asm20": "Assembly-to-reference (<20% divergence)",
    "map-hifi": "PacBio HiFi reads",
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ReferenceGenome:
    """Reference genome metadata"""
    name: str
    path: str
    description: str = ""
    species: str = ""
    size_bp: int = 0
    contigs: int = 0
    added: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    indices: Dict[str, str] = field(default_factory=dict)
    checksum: Optional[str] = None
    region: Optional[str] = None  # For targeted references like CYP2D6
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v}
    
    @classmethod
    def from_dict(cls, name: str, data: Dict) -> 'ReferenceGenome':
        return cls(name=name, **{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class AlignmentStats:
    """Alignment statistics"""
    input_file: str
    reference: str
    total_reads: int = 0
    mapped_reads: int = 0
    unmapped_reads: int = 0
    mapped_pct: float = 0.0
    primary_alignments: int = 0
    secondary_alignments: int = 0
    supplementary_alignments: int = 0
    mean_mapq: float = 0.0
    median_mapq: float = 0.0
    mean_read_length: float = 0.0
    median_read_length: float = 0.0
    n50_read_length: int = 0
    total_bases_aligned: int = 0
    mean_coverage: float = 0.0
    median_coverage: float = 0.0
    coverage_uniformity: float = 0.0
    pct_genome_covered_1x: float = 0.0
    pct_genome_covered_10x: float = 0.0
    pct_genome_covered_30x: float = 0.0
    mean_identity: float = 0.0
    insertions_per_read: float = 0.0
    deletions_per_read: float = 0.0
    mismatches_per_read: float = 0.0
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class EditDistanceResult:
    """Result of edit distance computation"""
    query_name: str
    target_name: str
    query_length: int
    target_length: int
    edit_distance: int
    normalized_distance: float = 0.0
    cigar: Optional[str] = None
    locations: Optional[List[Tuple[int, int]]] = None
    alignment_score: Optional[int] = None
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        # Remove None values
        return {k: v for k, v in d.items() if v is not None}


# =============================================================================
# Reference Registry
# =============================================================================

def load_references() -> Dict[str, ReferenceGenome]:
    """Load reference registry"""
    if not REFERENCES_FILE.exists():
        return {}
    
    with open(REFERENCES_FILE, 'r') as f:
        if HAS_YAML:
            data = yaml.safe_load(f) or {}
        else:
            data = json.load(f)
    
    refs = {}
    for name, ref_data in data.get('references', {}).items():
        refs[name] = ReferenceGenome.from_dict(name, ref_data)
    
    return refs


def save_references(refs: Dict[str, ReferenceGenome]):
    """Save reference registry"""
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    
    data = {
        'version': REFERENCES_VERSION,
        'references': {name: ref.to_dict() for name, ref in refs.items()}
    }
    
    with open(REFERENCES_FILE, 'w') as f:
        if HAS_YAML:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        else:
            json.dump(data, f, indent=2)


def get_fasta_stats(fasta_path: Path) -> Tuple[int, int]:
    """Get total bases and contig count from FASTA"""
    total_bp = 0
    contigs = 0
    
    open_func = gzip.open if str(fasta_path).endswith('.gz') else open
    mode = 'rt' if str(fasta_path).endswith('.gz') else 'r'
    
    with open_func(fasta_path, mode) as f:
        for line in f:
            if line.startswith('>'):
                contigs += 1
            else:
                total_bp += len(line.strip())
    
    return total_bp, contigs


def compute_file_checksum(filepath: Path, algorithm: str = 'sha256') -> str:
    """Compute file checksum"""
    h = hashlib.new(algorithm)
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return f"{algorithm}:{h.hexdigest()}"


def index_reference(ref: ReferenceGenome, aligner: str = 'minimap2') -> Optional[str]:
    """Index reference genome"""
    fasta_path = Path(ref.path)
    
    if aligner == 'minimap2':
        index_path = fasta_path.with_suffix('.mmi')
        cmd = ['minimap2', '-d', str(index_path), str(fasta_path)]
    elif aligner == 'dorado':
        index_path = fasta_path.with_suffix('.idx')
        cmd = ['dorado', 'index', str(fasta_path)]
    else:
        return None
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return str(index_path)
    except subprocess.CalledProcessError as e:
        print(f"Error indexing reference: {e.stderr.decode()}")
        return None
    except FileNotFoundError:
        print(f"Error: {aligner} not found in PATH")
        return None


# =============================================================================
# Edit Distance (Levenshtein) using edlib
# =============================================================================

def compute_edit_distance(
    query: str,
    target: str,
    mode: str = 'NW',
    task: str = 'distance',
    max_distance: Optional[int] = None,
) -> EditDistanceResult:
    """
    Compute edit distance between two sequences using edlib.
    
    Args:
        query: Query sequence
        target: Target sequence
        mode: Alignment mode - 'NW' (global), 'HW' (semi-global), 'SHW' (infix)
        task: Task type - 'distance', 'locations', 'path'
        max_distance: Early termination threshold (-1 for unlimited)
    
    Returns:
        EditDistanceResult with distance and optional alignment info
    """
    if not HAS_EDLIB:
        raise ImportError("edlib is required for edit distance computation. Install with: pip install edlib")
    
    # Map mode strings to edlib constants
    mode_map = {
        'NW': 'NW',      # Global alignment (Needleman-Wunsch)
        'HW': 'HW',      # Semi-global (query aligned fully, target can have gaps at ends)
        'SHW': 'SHW',    # Infix alignment (query as infix of target)
    }
    
    task_map = {
        'distance': 'distance',
        'locations': 'locations',
        'path': 'path',
    }
    
    edlib_mode = mode_map.get(mode.upper(), 'NW')
    edlib_task = task_map.get(task.lower(), 'distance')
    
    # Set k (max distance) - edlib uses -1 for unlimited
    k = max_distance if max_distance is not None else -1
    
    # Run edlib alignment
    result = edlib.align(
        query,
        target,
        mode=edlib_mode,
        task=edlib_task,
        k=k,
    )
    
    # Build result object
    edit_result = EditDistanceResult(
        query_name="query",
        target_name="target",
        query_length=len(query),
        target_length=len(target),
        edit_distance=result['editDistance'],
    )
    
    # Compute normalized distance
    max_len = max(len(query), len(target))
    if max_len > 0 and result['editDistance'] >= 0:
        edit_result.normalized_distance = result['editDistance'] / max_len
    
    # Extract CIGAR if path was computed
    if edlib_task == 'path' and result.get('cigar'):
        edit_result.cigar = result['cigar']
    
    # Extract locations if computed
    if edlib_task in ('locations', 'path') and result.get('locations'):
        edit_result.locations = result['locations']
    
    return edit_result


def parse_fasta(filepath: Union[str, Path]) -> Iterator[Tuple[str, str]]:
    """Parse FASTA/FASTQ file, yielding (name, sequence) tuples"""
    filepath = Path(filepath)
    
    open_func = gzip.open if str(filepath).endswith('.gz') else open
    mode = 'rt' if str(filepath).endswith('.gz') else 'r'
    
    # Detect format from first character
    with open_func(filepath, mode) as f:
        first_char = f.read(1)
    
    is_fastq = first_char == '@'
    
    with open_func(filepath, mode) as f:
        if is_fastq:
            # FASTQ format
            while True:
                header = f.readline().strip()
                if not header:
                    break
                seq = f.readline().strip()
                f.readline()  # + line
                f.readline()  # quality
                name = header[1:].split()[0]
                yield name, seq
        else:
            # FASTA format
            name = None
            seq_parts = []
            
            for line in f:
                line = line.strip()
                if line.startswith('>'):
                    if name is not None:
                        yield name, ''.join(seq_parts)
                    name = line[1:].split()[0]
                    seq_parts = []
                else:
                    seq_parts.append(line)
            
            if name is not None:
                yield name, ''.join(seq_parts)


def compute_edit_distances_batch(
    query_seqs: List[Tuple[str, str]],
    target_seqs: List[Tuple[str, str]],
    mode: str = 'NW',
    task: str = 'distance',
    max_distance: Optional[int] = None,
    all_vs_all: bool = False,
    threads: int = 1,
) -> List[EditDistanceResult]:
    """
    Compute edit distances for multiple sequence pairs.
    
    Args:
        query_seqs: List of (name, sequence) tuples for queries
        target_seqs: List of (name, sequence) tuples for targets
        mode: Alignment mode
        task: Task type
        max_distance: Early termination threshold
        all_vs_all: If True, compare all queries to all targets
        threads: Number of parallel threads
    
    Returns:
        List of EditDistanceResult objects
    """
    results = []
    
    if all_vs_all:
        # All-vs-all comparison
        pairs = [(q, t) for q in query_seqs for t in target_seqs]
    else:
        # Pairwise comparison (zip queries and targets)
        pairs = list(zip(query_seqs, target_seqs))
    
    def compute_pair(pair):
        (q_name, q_seq), (t_name, t_seq) = pair
        result = compute_edit_distance(
            q_seq, t_seq,
            mode=mode,
            task=task,
            max_distance=max_distance,
        )
        result.query_name = q_name
        result.target_name = t_name
        return result
    
    if threads > 1 and HAS_CONCURRENT and len(pairs) > 10:
        with ThreadPoolExecutor(max_workers=threads) as executor:
            results = list(executor.map(compute_pair, pairs))
    else:
        results = [compute_pair(p) for p in pairs]
    
    return results


# =============================================================================
# Alignment Functions
# =============================================================================

def run_minimap2(
    input_file: str,
    reference: str,
    output_file: str,
    preset: str = 'map-ont',
    threads: int = 8,
    secondary: bool = False,
    md_tag: bool = True,
    cs_tag: bool = False,
    sam_output: bool = False,
) -> Tuple[int, str]:
    """Run minimap2 alignment"""
    
    # Build minimap2 command
    cmd = ['minimap2', '-ax', preset, '-t', str(threads)]
    
    if not secondary:
        cmd.append('--secondary=no')
    
    if md_tag:
        cmd.append('--MD')
    
    if cs_tag:
        cmd.append('--cs')
    
    cmd.extend([reference, input_file])
    
    # Pipe to samtools for BAM conversion and sorting
    if not sam_output:
        sort_cmd = ['samtools', 'sort', '-@', str(threads), '-o', output_file]
        
        mm2_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        sort_proc = subprocess.Popen(sort_cmd, stdin=mm2_proc.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        mm2_proc.stdout.close()
        _, sort_stderr = sort_proc.communicate()
        _, mm2_stderr = mm2_proc.communicate()
        
        # Index the BAM
        subprocess.run(['samtools', 'index', output_file], check=True)
        
        return sort_proc.returncode, (mm2_stderr.decode() + sort_stderr.decode())
    else:
        # Direct SAM output
        with open(output_file, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE)
        return result.returncode, result.stderr.decode()


def compute_bam_stats(bam_path: str, reference: str, min_mapq: int = 20) -> AlignmentStats:
    """Compute alignment statistics from BAM file"""
    if not HAS_PYSAM:
        raise ImportError("pysam is required for BAM QC. Install with: pip install pysam")
    
    stats = AlignmentStats(input_file=bam_path, reference=reference)
    
    mapq_values = []
    read_lengths = []
    total_insertions = 0
    total_deletions = 0
    total_mismatches = 0
    aligned_bases = 0
    
    with pysam.AlignmentFile(bam_path, "rb") as bam:
        for read in bam.fetch(until_eof=True):
            stats.total_reads += 1
            
            if read.is_unmapped:
                stats.unmapped_reads += 1
                continue
            
            stats.mapped_reads += 1
            read_lengths.append(read.query_length)
            
            if read.is_secondary:
                stats.secondary_alignments += 1
            elif read.is_supplementary:
                stats.supplementary_alignments += 1
            else:
                stats.primary_alignments += 1
                mapq_values.append(read.mapping_quality)
            
            # Count CIGAR operations
            if read.cigartuples:
                for op, length in read.cigartuples:
                    if op == 0:  # M (match/mismatch)
                        aligned_bases += length
                    elif op == 1:  # I (insertion)
                        total_insertions += length
                    elif op == 2:  # D (deletion)
                        total_deletions += length
            
            # Count mismatches from NM tag if available
            if read.has_tag('NM'):
                total_mismatches += read.get_tag('NM')
    
    # Compute summary statistics
    if stats.total_reads > 0:
        stats.mapped_pct = 100.0 * stats.mapped_reads / stats.total_reads
    
    if mapq_values:
        if HAS_NUMPY:
            stats.mean_mapq = float(np.mean(mapq_values))
            stats.median_mapq = float(np.median(mapq_values))
        else:
            stats.mean_mapq = sum(mapq_values) / len(mapq_values)
            sorted_mapq = sorted(mapq_values)
            mid = len(sorted_mapq) // 2
            stats.median_mapq = sorted_mapq[mid]
    
    if read_lengths:
        if HAS_NUMPY:
            stats.mean_read_length = float(np.mean(read_lengths))
            stats.median_read_length = float(np.median(read_lengths))
        else:
            stats.mean_read_length = sum(read_lengths) / len(read_lengths)
            sorted_lengths = sorted(read_lengths)
            mid = len(sorted_lengths) // 2
            stats.median_read_length = sorted_lengths[mid]
        
        # Compute N50
        sorted_lengths = sorted(read_lengths, reverse=True)
        total_bases = sum(sorted_lengths)
        cumsum = 0
        for length in sorted_lengths:
            cumsum += length
            if cumsum >= total_bases / 2:
                stats.n50_read_length = length
                break
    
    stats.total_bases_aligned = aligned_bases
    
    if stats.mapped_reads > 0:
        stats.insertions_per_read = total_insertions / stats.mapped_reads
        stats.deletions_per_read = total_deletions / stats.mapped_reads
        stats.mismatches_per_read = total_mismatches / stats.mapped_reads
    
    return stats


# =============================================================================
# CLI Commands
# =============================================================================

def cmd_refs_init(args):
    """Initialize reference registry"""
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    
    if REFERENCES_FILE.exists() and not args.force:
        print(f"Registry already exists: {REFERENCES_FILE}")
        print("Use --force to reinitialize")
        return 1
    
    save_references({})
    print(f"Initialized reference registry: {REFERENCES_FILE}")
    return 0


def cmd_refs_add(args):
    """Add reference to registry"""
    refs = load_references()
    
    if args.name in refs and not args.force:
        print(f"Reference '{args.name}' already exists. Use --force to overwrite.")
        return 1
    
    fasta_path = Path(args.fasta).resolve()
    if not fasta_path.exists():
        print(f"Error: File not found: {fasta_path}")
        return 1
    
    print(f"Adding reference: {args.name}")
    print(f"  Path: {fasta_path}")
    
    # Get FASTA statistics
    print("  Computing statistics...")
    size_bp, contigs = get_fasta_stats(fasta_path)
    
    # Compute checksum
    print("  Computing checksum...")
    checksum = compute_file_checksum(fasta_path)
    
    ref = ReferenceGenome(
        name=args.name,
        path=str(fasta_path),
        description=args.description or "",
        species=args.species or "",
        size_bp=size_bp,
        contigs=contigs,
        checksum=checksum,
    )
    
    # Index reference
    if not args.no_index:
        print("  Indexing with minimap2...")
        index_path = index_reference(ref, 'minimap2')
        if index_path:
            ref.indices['minimap2'] = index_path
    
    refs[args.name] = ref
    save_references(refs)
    
    print(f"\n  ✓ Added: {args.name}")
    print(f"    Size: {size_bp:,} bp")
    print(f"    Contigs: {contigs}")
    
    return 0


def cmd_refs_list(args):
    """List registered references"""
    refs = load_references()
    
    if not refs:
        print("\n  No references registered.")
        print("  Use 'ont_align.py refs add <name> <fasta>' to add one.")
        return 0
    
    print(f"\n  Registered References")
    print(f"  {'═' * 60}")
    
    for name, ref in refs.items():
        size_gb = ref.size_bp / 1e9 if ref.size_bp else 0
        indices = ', '.join(ref.indices.keys()) if ref.indices else 'none'
        
        print(f"\n  {name}")
        print(f"    Path: {ref.path}")
        if ref.description:
            print(f"    Description: {ref.description}")
        print(f"    Size: {size_gb:.2f} Gb ({ref.contigs} contigs)")
        print(f"    Indices: {indices}")
    
    return 0


def cmd_refs_info(args):
    """Show reference details"""
    refs = load_references()
    
    if args.name not in refs:
        print(f"Error: Reference '{args.name}' not found")
        return 1
    
    ref = refs[args.name]
    
    if args.json:
        print(json.dumps(ref.to_dict(), indent=2))
    else:
        print(f"\n  Reference: {ref.name}")
        print(f"  {'═' * 50}")
        print(f"  Path: {ref.path}")
        print(f"  Description: {ref.description}")
        print(f"  Species: {ref.species}")
        print(f"  Size: {ref.size_bp:,} bp")
        print(f"  Contigs: {ref.contigs}")
        print(f"  Added: {ref.added}")
        print(f"  Checksum: {ref.checksum}")
        
        if ref.indices:
            print(f"\n  Indices:")
            for aligner, path in ref.indices.items():
                print(f"    {aligner}: {path}")
    
    return 0


def cmd_align(args):
    """Run alignment"""
    refs = load_references()
    
    # Resolve reference
    if args.reference in refs:
        ref = refs[args.reference]
        # Use index if available
        if 'minimap2' in ref.indices:
            reference_path = ref.indices['minimap2']
        else:
            reference_path = ref.path
    else:
        # Assume it's a direct path
        reference_path = args.reference
    
    if not Path(reference_path).exists():
        print(f"Error: Reference not found: {reference_path}")
        return 1
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return 1
    
    print(f"\n  Alignment")
    print(f"  {'─' * 50}")
    print(f"  Input: {args.input}")
    print(f"  Reference: {args.reference}")
    print(f"  Output: {args.output}")
    print(f"  Preset: {args.preset}")
    print(f"  Threads: {args.threads}")
    
    start_time = time.time()
    
    exit_code, stderr = run_minimap2(
        input_file=str(input_path),
        reference=reference_path,
        output_file=args.output,
        preset=args.preset,
        threads=args.threads,
        secondary=args.secondary,
        md_tag=args.md,
        cs_tag=args.cs,
        sam_output=args.sam,
    )
    
    duration = time.time() - start_time
    
    if exit_code != 0:
        print(f"\n  ✗ Alignment failed")
        print(f"  {stderr}")
        return 1
    
    print(f"\n  ✓ Alignment complete ({duration:.1f}s)")
    
    # Generate stats if requested
    if args.json:
        print(f"  Computing statistics...")
        stats = compute_bam_stats(args.output, args.reference)
        
        with open(args.json, 'w') as f:
            json.dump(stats.to_dict(), f, indent=2)
        print(f"  Stats saved: {args.json}")
    
    return 0


def cmd_qc(args):
    """BAM QC analysis"""
    if not Path(args.bam).exists():
        print(f"Error: BAM file not found: {args.bam}")
        return 1
    
    print(f"\n  BAM QC Analysis")
    print(f"  {'─' * 50}")
    print(f"  Input: {args.bam}")
    
    stats = compute_bam_stats(args.bam, args.reference or "unknown", min_mapq=args.min_mapq)
    
    # Print summary
    print(f"\n  Summary")
    print(f"  {'─' * 40}")
    print(f"  Total reads:      {stats.total_reads:,}")
    print(f"  Mapped reads:     {stats.mapped_reads:,} ({stats.mapped_pct:.1f}%)")
    print(f"  Primary:          {stats.primary_alignments:,}")
    print(f"  Secondary:        {stats.secondary_alignments:,}")
    print(f"  Supplementary:    {stats.supplementary_alignments:,}")
    print(f"  Mean MAPQ:        {stats.mean_mapq:.1f}")
    print(f"  Mean read length: {stats.mean_read_length:.0f}")
    print(f"  N50:              {stats.n50_read_length:,}")
    
    # Save JSON if requested
    if args.json:
        with open(args.json, 'w') as f:
            json.dump(stats.to_dict(), f, indent=2)
        print(f"\n  Stats saved: {args.json}")
    
    return 0


def cmd_editdist(args):
    """Compute edit distance"""
    if not HAS_EDLIB:
        print("Error: edlib is required for edit distance computation")
        print("Install with: pip install edlib")
        return 1
    
    # Determine mode
    if args.query and args.target:
        # File-based comparison
        print(f"\n  Edit Distance Computation")
        print(f"  {'─' * 50}")
        print(f"  Query file: {args.query}")
        print(f"  Target file: {args.target}")
        print(f"  Mode: {args.mode}")
        
        # Load sequences
        query_seqs = list(parse_fasta(args.query))
        target_seqs = list(parse_fasta(args.target))
        
        if args.self_comparison:
            # Self-comparison mode
            target_seqs = query_seqs
            args.all_vs_all = True
        
        print(f"  Query sequences: {len(query_seqs)}")
        print(f"  Target sequences: {len(target_seqs)}")
        
        # Determine task based on options
        task = 'distance'
        if args.cigar:
            task = 'path'
        elif args.mode in ('HW', 'SHW'):
            task = 'locations'
        
        # Compute distances
        results = compute_edit_distances_batch(
            query_seqs=query_seqs,
            target_seqs=target_seqs,
            mode=args.mode,
            task=task,
            max_distance=args.max_distance,
            all_vs_all=args.all_vs_all,
            threads=args.threads,
        )
        
        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                # TSV header
                header = ['query', 'target', 'query_len', 'target_len', 'edit_distance']
                if args.normalize:
                    header.append('normalized')
                if args.cigar:
                    header.append('cigar')
                f.write('\t'.join(header) + '\n')
                
                for r in results:
                    row = [r.query_name, r.target_name, str(r.query_length), 
                           str(r.target_length), str(r.edit_distance)]
                    if args.normalize:
                        row.append(f"{r.normalized_distance:.6f}")
                    if args.cigar and r.cigar:
                        row.append(r.cigar)
                    f.write('\t'.join(row) + '\n')
            
            print(f"\n  ✓ Results saved: {args.output}")
            print(f"  Comparisons: {len(results)}")
        
        elif args.json_output:
            output_data = [r.to_dict() for r in results]
            with open(args.json_output, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"\n  ✓ Results saved: {args.json_output}")
        
        else:
            # Print to stdout
            print(f"\n  Results:")
            for r in results[:20]:  # Limit output
                dist_str = f"{r.edit_distance}"
                if args.normalize:
                    dist_str += f" (norm: {r.normalized_distance:.4f})"
                print(f"  {r.query_name} vs {r.target_name}: {dist_str}")
            
            if len(results) > 20:
                print(f"  ... and {len(results) - 20} more")
    
    elif args.seq1 and args.seq2:
        # Direct sequence comparison
        seq1 = args.seq1.upper()
        seq2 = args.seq2.upper()
        
        task = 'path' if args.cigar else 'distance'
        if args.mode in ('HW', 'SHW'):
            task = 'locations' if not args.cigar else 'path'
        
        result = compute_edit_distance(
            seq1, seq2,
            mode=args.mode,
            task=task,
            max_distance=args.max_distance,
        )
        
        print(f"\n  Edit Distance: {result.edit_distance}")
        print(f"  Query length:  {result.query_length}")
        print(f"  Target length: {result.target_length}")
        
        if args.normalize:
            print(f"  Normalized:    {result.normalized_distance:.6f}")
        
        if args.cigar and result.cigar:
            print(f"  CIGAR:         {result.cigar}")
        
        if result.locations:
            print(f"  Locations:     {result.locations}")
    
    else:
        print("Error: Provide either two sequences or --query and --target files")
        return 1
    
    return 0


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='ONT Align - Alignment & Edit Distance Toolkit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # refs subcommand group
    refs_parser = subparsers.add_parser('refs', help='Reference management')
    refs_sub = refs_parser.add_subparsers(dest='refs_command')
    
    # refs init
    refs_init = refs_sub.add_parser('init', help='Initialize reference registry')
    refs_init.add_argument('--force', '-f', action='store_true', help='Reinitialize')
    
    # refs add
    refs_add = refs_sub.add_parser('add', help='Add reference')
    refs_add.add_argument('name', help='Reference name')
    refs_add.add_argument('fasta', help='Path to FASTA file')
    refs_add.add_argument('--description', '-d', help='Description')
    refs_add.add_argument('--species', '-s', help='Species name')
    refs_add.add_argument('--no-index', action='store_true', help='Skip indexing')
    refs_add.add_argument('--force', '-f', action='store_true', help='Overwrite existing')
    
    # refs list
    refs_list = refs_sub.add_parser('list', help='List references')
    
    # refs info
    refs_info = refs_sub.add_parser('info', help='Show reference details')
    refs_info.add_argument('name', help='Reference name')
    refs_info.add_argument('--json', action='store_true', help='Output JSON')
    
    # align
    align_parser = subparsers.add_parser('align', help='Align reads to reference')
    align_parser.add_argument('input', help='Input BAM/FASTQ file')
    align_parser.add_argument('--reference', '-r', required=True, help='Reference name or path')
    align_parser.add_argument('--output', '-o', required=True, help='Output BAM file')
    align_parser.add_argument('--preset', '-x', default='map-ont', 
                              choices=list(MINIMAP2_PRESETS.keys()), help='Alignment preset')
    align_parser.add_argument('--threads', '-t', type=int, default=8, help='Number of threads')
    align_parser.add_argument('--secondary', action='store_true', help='Include secondary alignments')
    align_parser.add_argument('--md', action='store_true', default=True, help='Add MD tag')
    align_parser.add_argument('--cs', action='store_true', help='Add cs tag')
    align_parser.add_argument('--sam', action='store_true', help='Output SAM instead of BAM')
    align_parser.add_argument('--json', help='Output statistics JSON')
    
    # qc
    qc_parser = subparsers.add_parser('qc', help='BAM QC analysis')
    qc_parser.add_argument('bam', help='Input BAM file')
    qc_parser.add_argument('--reference', '-r', help='Reference name (for annotation)')
    qc_parser.add_argument('--json', help='Output JSON statistics')
    qc_parser.add_argument('--csv', help='Output per-read CSV')
    qc_parser.add_argument('--plot', help='Output coverage plot')
    qc_parser.add_argument('--regions', help='Target regions BED file')
    qc_parser.add_argument('--min-mapq', type=int, default=20, help='Minimum mapping quality')
    qc_parser.add_argument('--threads', '-t', type=int, default=4, help='Number of threads')
    
    # editdist
    edit_parser = subparsers.add_parser('editdist', help='Compute edit distance (Levenshtein)')
    edit_parser.add_argument('seq1', nargs='?', help='First sequence (direct input)')
    edit_parser.add_argument('seq2', nargs='?', help='Second sequence (direct input)')
    edit_parser.add_argument('--query', '-q', help='Query sequences file (FASTA/FASTQ)')
    edit_parser.add_argument('--target', '-t', help='Target sequences file (FASTA/FASTQ)')
    edit_parser.add_argument('--output', '-o', help='Output TSV file')
    edit_parser.add_argument('--json-output', help='Output JSON file')
    edit_parser.add_argument('--mode', '-m', default='NW', choices=['NW', 'HW', 'SHW'],
                             help='Alignment mode: NW (global), HW (semi-global), SHW (infix)')
    edit_parser.add_argument('--max-distance', '-k', type=int, 
                             help='Early termination if distance exceeds this')
    edit_parser.add_argument('--cigar', '-c', action='store_true', help='Output CIGAR string')
    edit_parser.add_argument('--normalize', '-n', action='store_true', 
                             help='Output normalized distance (0-1)')
    edit_parser.add_argument('--all-vs-all', '-a', action='store_true',
                             help='Compare all queries vs all targets')
    edit_parser.add_argument('--self', dest='self_comparison', action='store_true',
                             help='Self-comparison (all-vs-all within query file)')
    edit_parser.add_argument('--threads', type=int, default=1, help='Parallel threads')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    # Route to command handlers
    if args.command == 'refs':
        if args.refs_command == 'init':
            return cmd_refs_init(args)
        elif args.refs_command == 'add':
            return cmd_refs_add(args)
        elif args.refs_command == 'list':
            return cmd_refs_list(args)
        elif args.refs_command == 'info':
            return cmd_refs_info(args)
        else:
            refs_parser.print_help()
            return 0
    
    elif args.command == 'align':
        return cmd_align(args)
    
    elif args.command == 'qc':
        return cmd_qc(args)
    
    elif args.command == 'editdist':
        return cmd_editdist(args)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
