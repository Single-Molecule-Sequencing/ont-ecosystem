#!/usr/bin/env python3
"""
ONT Align - Oxford Nanopore alignment with reference management and BAM QC.

Features:
- Dual aligner support: minimap2 and dorado aligner
- Reference genome registry with checksums
- Auto-detect optimal minimap2 preset from read quality
- Sorted/indexed BAM output
- Coverage BED/bedGraph generation
- Comprehensive alignment QC metrics
- Pattern B integration with ont-experiments

Usage:
  ont_align.py align input.bam --ref hg38 --output aligned.bam
  ont_align.py align input.fastq --ref hs1 --aligner minimap2 --preset lr:hq
  ont_align.py qc aligned.bam --json qc.json --coverage coverage.bed
  ont_align.py refs list
  ont_align.py refs add /path/to/reference.fa --name ecoli_k12
  
Integration with ont-experiments:
  ont_experiments.py run alignment exp-abc123 --ref hg38 --output aligned.bam
"""

import argparse
import json
import os
import sys
import subprocess
import hashlib
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

# Optional imports
try:
    import pysam
    HAS_PYSAM = True
except ImportError:
    HAS_PYSAM = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


# =============================================================================
# Configuration
# =============================================================================

REFS_REGISTRY_DIR = Path.home() / ".ont-references"
REFS_REGISTRY_FILE = REFS_REGISTRY_DIR / "references.yaml"

# Default reference locations on common HPC systems
DEFAULT_REF_PATHS = [
    Path("/nfs/turbo/umms-athey/references"),
    Path("/nfs/turbo/athey-lab/references"),
    Path("/scratch/references"),
    Path.home() / "references",
]

# Minimap2 presets for ONT data
MINIMAP2_PRESETS = {
    "map-ont": {
        "description": "Standard ONT reads (R9/R10, any model)",
        "options": "-ax map-ont",
        "recommended_for": ["fast", "hac"],
    },
    "lr:hq": {
        "description": "High-quality ONT reads (Q20+, SUP model)",
        "options": "-ax lr:hq",
        "recommended_for": ["sup"],
    },
    "splice": {
        "description": "ONT cDNA/RNA (spliced alignment)",
        "options": "-ax splice",
        "recommended_for": ["cdna", "rna"],
    },
    "splice:hq": {
        "description": "High-quality cDNA/RNA",
        "options": "-ax splice:hq",
        "recommended_for": ["cdna_sup", "rna_sup"],
    },
    "asm20": {
        "description": "Assembly-to-reference (high identity)",
        "options": "-ax asm20",
        "recommended_for": ["assembly"],
    },
}

# Built-in reference genome definitions
BUILTIN_REFERENCES = {
    "hg38": {
        "name": "GRCh38 Human Reference",
        "aliases": ["grch38", "human38"],
        "url": "https://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/000/001/405/GCA_000001405.15_GRCh38/seqs_for_alignment_pipelines.ucsc_ids/GCA_000001405.15_GRCh38_no_alt_analysis_set.fna.gz",
        "size_gb": 3.1,
    },
    "hs1": {
        "name": "T2T-CHM13 Human Reference (hs1)",
        "aliases": ["t2t", "chm13", "t2t-chm13"],
        "url": "https://s3-us-west-2.amazonaws.com/human-pangenomics/T2T/CHM13/assemblies/analysis_set/chm13v2.0.fa.gz",
        "size_gb": 3.1,
    },
    "hg19": {
        "name": "GRCh37/hg19 Human Reference",
        "aliases": ["grch37", "human37"],
        "url": "https://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/000/001/405/GCA_000001405.14_GRCh37.p13/seqs_for_alignment_pipelines.ucsc_ids/GCA_000001405.14_GRCh37.p13_full_analysis_set.fna.gz",
        "size_gb": 3.0,
    },
    "ecoli_k12": {
        "name": "E. coli K-12 MG1655",
        "aliases": ["ecoli", "k12"],
        "url": "https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/005/845/GCF_000005845.2_ASM584v2/GCF_000005845.2_ASM584v2_genomic.fna.gz",
        "size_gb": 0.005,
    },
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ReferenceGenome:
    """Reference genome metadata."""
    name: str
    path: str
    checksum: str = ""
    size_bytes: int = 0
    indexed: bool = False
    index_type: str = ""  # minimap2, bwa, etc.
    added_date: str = ""
    aliases: List[str] = field(default_factory=list)
    description: str = ""
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v}


@dataclass
class AlignmentStats:
    """Alignment statistics."""
    total_reads: int = 0
    mapped_reads: int = 0
    unmapped_reads: int = 0
    primary_alignments: int = 0
    secondary_alignments: int = 0
    supplementary_alignments: int = 0
    
    # Mapping quality
    mean_mapq: float = 0.0
    median_mapq: float = 0.0
    mapq_distribution: Dict[int, int] = field(default_factory=dict)
    
    # Read lengths
    mean_read_length: float = 0.0
    median_read_length: float = 0.0
    n50_read_length: int = 0
    
    # Alignment lengths
    mean_aligned_length: float = 0.0
    total_aligned_bases: int = 0
    
    # Quality
    mean_identity: float = 0.0
    mean_accuracy: float = 0.0
    
    @property
    def mapping_rate(self) -> float:
        return (self.mapped_reads / self.total_reads * 100) if self.total_reads else 0.0
    
    @property
    def primary_rate(self) -> float:
        return (self.primary_alignments / self.total_reads * 100) if self.total_reads else 0.0
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d["mapping_rate"] = round(self.mapping_rate, 2)
        d["primary_rate"] = round(self.primary_rate, 2)
        return d


@dataclass
class CoverageStats:
    """Coverage statistics."""
    reference_length: int = 0
    covered_bases: int = 0
    mean_coverage: float = 0.0
    median_coverage: float = 0.0
    min_coverage: int = 0
    max_coverage: int = 0
    std_coverage: float = 0.0
    
    # Coverage thresholds
    pct_1x: float = 0.0
    pct_5x: float = 0.0
    pct_10x: float = 0.0
    pct_20x: float = 0.0
    pct_30x: float = 0.0
    
    # Per-chromosome stats
    per_chrom: Dict[str, Dict] = field(default_factory=dict)
    
    @property
    def breadth(self) -> float:
        return (self.covered_bases / self.reference_length * 100) if self.reference_length else 0.0
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d["breadth"] = round(self.breadth, 2)
        return d


@dataclass 
class OnTargetStats:
    """On-target statistics for targeted sequencing."""
    target_regions: int = 0
    target_bases: int = 0
    reads_on_target: int = 0
    reads_off_target: int = 0
    bases_on_target: int = 0
    bases_off_target: int = 0
    mean_target_coverage: float = 0.0
    uniformity: float = 0.0  # % bases within 0.2x of mean
    
    @property
    def on_target_rate(self) -> float:
        total = self.reads_on_target + self.reads_off_target
        return (self.reads_on_target / total * 100) if total else 0.0
    
    @property
    def enrichment_fold(self) -> float:
        # Fold enrichment vs random distribution
        return 0.0  # Computed externally
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d["on_target_rate"] = round(self.on_target_rate, 2)
        return d


@dataclass
class AlignmentResult:
    """Complete alignment result."""
    input_file: str
    output_bam: str
    reference: str
    aligner: str
    preset: str
    
    alignment_stats: AlignmentStats
    coverage_stats: Optional[CoverageStats] = None
    on_target_stats: Optional[OnTargetStats] = None
    
    command: str = ""
    duration_seconds: float = 0.0
    timestamp: str = ""
    
    # Output files
    output_files: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        d = {
            "input_file": self.input_file,
            "output_bam": self.output_bam,
            "reference": self.reference,
            "aligner": self.aligner,
            "preset": self.preset,
            "command": self.command,
            "duration_seconds": round(self.duration_seconds, 2),
            "timestamp": self.timestamp,
            "alignment_stats": self.alignment_stats.to_dict(),
            "output_files": self.output_files,
        }
        if self.coverage_stats:
            d["coverage_stats"] = self.coverage_stats.to_dict()
        if self.on_target_stats:
            d["on_target_stats"] = self.on_target_stats.to_dict()
        return d


# =============================================================================
# Reference Management
# =============================================================================

class ReferenceRegistry:
    """Manage reference genome registry."""
    
    def __init__(self, registry_dir: Path = None):
        self.registry_dir = registry_dir or REFS_REGISTRY_DIR
        self.registry_file = self.registry_dir / "references.yaml"
        self.references: Dict[str, ReferenceGenome] = {}
        self._load()
    
    def _load(self):
        """Load registry from disk."""
        if not self.registry_file.exists():
            return
        
        try:
            if HAS_YAML:
                with open(self.registry_file) as f:
                    data = yaml.safe_load(f) or {}
            else:
                with open(self.registry_file) as f:
                    data = json.load(f)
            
            for name, ref_data in data.get("references", {}).items():
                self.references[name] = ReferenceGenome(
                    name=name,
                    path=ref_data.get("path", ""),
                    checksum=ref_data.get("checksum", ""),
                    size_bytes=ref_data.get("size_bytes", 0),
                    indexed=ref_data.get("indexed", False),
                    index_type=ref_data.get("index_type", ""),
                    added_date=ref_data.get("added_date", ""),
                    aliases=ref_data.get("aliases", []),
                    description=ref_data.get("description", ""),
                )
        except Exception as e:
            print(f"Warning: Could not load registry: {e}", file=sys.stderr)
    
    def _save(self):
        """Save registry to disk."""
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        
        data = {
            "version": "1.0",
            "references": {name: ref.to_dict() for name, ref in self.references.items()},
        }
        
        if HAS_YAML:
            with open(self.registry_file, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)
        else:
            with open(self.registry_file, 'w') as f:
                json.dump(data, f, indent=2)
    
    def init(self, scan_paths: bool = True):
        """Initialize registry, optionally scanning default paths."""
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        
        if scan_paths:
            for ref_path in DEFAULT_REF_PATHS:
                if ref_path.exists():
                    self._scan_directory(ref_path)
        
        self._save()
        print(f"Registry initialized at {self.registry_dir}")
        print(f"Found {len(self.references)} references")
    
    def _scan_directory(self, directory: Path):
        """Scan directory for reference genomes."""
        for ext in ["*.fa", "*.fasta", "*.fna", "*.fa.gz", "*.fasta.gz", "*.fna.gz"]:
            for ref_file in directory.glob(f"**/{ext}"):
                name = ref_file.stem.replace(".fa", "").replace(".fasta", "").replace(".fna", "")
                if name not in self.references:
                    self.add(str(ref_file), name=name, index=False)
    
    def add(self, path: str, name: str = None, description: str = "", 
            aliases: List[str] = None, index: bool = True) -> ReferenceGenome:
        """Add reference genome to registry."""
        ref_path = Path(path)
        if not ref_path.exists():
            raise FileNotFoundError(f"Reference file not found: {path}")
        
        name = name or ref_path.stem.replace(".fa", "").replace(".fasta", "").replace(".fna", "")
        
        # Compute checksum (first 1MB for speed)
        checksum = self._compute_checksum(ref_path)
        
        ref = ReferenceGenome(
            name=name,
            path=str(ref_path.absolute()),
            checksum=checksum,
            size_bytes=ref_path.stat().st_size,
            indexed=False,
            added_date=datetime.now(timezone.utc).isoformat(),
            aliases=aliases or [],
            description=description,
        )
        
        # Check for index
        if self._has_minimap2_index(ref_path):
            ref.indexed = True
            ref.index_type = "minimap2"
        
        # Create index if requested
        if index and not ref.indexed:
            self._create_minimap2_index(ref_path)
            ref.indexed = True
            ref.index_type = "minimap2"
        
        self.references[name] = ref
        self._save()
        
        return ref
    
    def _compute_checksum(self, path: Path, chunk_size: int = 1024 * 1024) -> str:
        """Compute MD5 checksum of first chunk."""
        hasher = hashlib.md5()
        with open(path, 'rb') as f:
            chunk = f.read(chunk_size)
            hasher.update(chunk)
        return hasher.hexdigest()
    
    def _has_minimap2_index(self, ref_path: Path) -> bool:
        """Check if minimap2 index exists."""
        index_path = ref_path.with_suffix(ref_path.suffix + ".mmi")
        return index_path.exists()
    
    def _create_minimap2_index(self, ref_path: Path):
        """Create minimap2 index."""
        index_path = ref_path.with_suffix(ref_path.suffix + ".mmi")
        cmd = ["minimap2", "-d", str(index_path), str(ref_path)]
        print(f"Creating minimap2 index: {index_path}")
        subprocess.run(cmd, check=True)
    
    def get(self, name: str) -> Optional[ReferenceGenome]:
        """Get reference by name or alias."""
        if name in self.references:
            return self.references[name]
        
        # Check aliases
        for ref in self.references.values():
            if name.lower() in [a.lower() for a in ref.aliases]:
                return ref
        
        # Check built-in references
        if name.lower() in BUILTIN_REFERENCES:
            print(f"Note: {name} is a known reference but not in registry. Use 'ont_align.py refs add' to add it.")
        
        return None
    
    def list(self) -> List[ReferenceGenome]:
        """List all references."""
        return list(self.references.values())
    
    def remove(self, name: str):
        """Remove reference from registry."""
        if name in self.references:
            del self.references[name]
            self._save()


# =============================================================================
# Alignment Engine
# =============================================================================

class Aligner:
    """Alignment engine supporting minimap2 and dorado aligner."""
    
    def __init__(self, ref_registry: ReferenceRegistry = None):
        self.ref_registry = ref_registry or ReferenceRegistry()
        self.minimap2_path = self._find_executable("minimap2")
        self.samtools_path = self._find_executable("samtools")
        self.dorado_path = self._find_executable("dorado")
    
    def _find_executable(self, name: str) -> Optional[str]:
        """Find executable in PATH."""
        return shutil.which(name)
    
    def _detect_input_type(self, input_path: Path) -> str:
        """Detect input file type."""
        suffix = input_path.suffix.lower()
        if suffix in [".bam", ".sam", ".cram"]:
            return "bam"
        elif suffix in [".fastq", ".fq"]:
            return "fastq"
        elif suffix == ".gz":
            if ".fastq" in input_path.name.lower() or ".fq" in input_path.name.lower():
                return "fastq"
        elif suffix == ".pod5":
            return "pod5"
        return "unknown"
    
    def _detect_preset(self, input_path: Path, input_type: str) -> str:
        """Auto-detect optimal minimap2 preset."""
        # Default to map-ont
        preset = "map-ont"
        
        if input_type == "bam" and HAS_PYSAM:
            try:
                # Sample reads to detect quality
                with pysam.AlignmentFile(str(input_path), "rb", check_sq=False) as bam:
                    qscores = []
                    for i, read in enumerate(bam.fetch(until_eof=True)):
                        if i >= 1000:
                            break
                        if read.query_qualities:
                            qscores.extend(read.query_qualities)
                    
                    if qscores:
                        mean_q = sum(qscores) / len(qscores)
                        if mean_q >= 20:
                            preset = "lr:hq"
                            print(f"Auto-detected high-quality reads (Q{mean_q:.1f}), using preset: lr:hq")
                        else:
                            print(f"Detected standard reads (Q{mean_q:.1f}), using preset: map-ont")
            except Exception:
                pass
        
        return preset
    
    def align_minimap2(self, input_path: Path, ref_path: Path, output_path: Path,
                       preset: str = "map-ont", threads: int = 4, 
                       extra_args: str = "") -> Tuple[str, int]:
        """Run minimap2 alignment."""
        if not self.minimap2_path:
            raise RuntimeError("minimap2 not found in PATH")
        if not self.samtools_path:
            raise RuntimeError("samtools not found in PATH")
        
        # Get preset options
        preset_opts = MINIMAP2_PRESETS.get(preset, {}).get("options", f"-ax {preset}")
        
        # Build command
        # minimap2 -> samtools sort -> output.bam
        cmd = (
            f"{self.minimap2_path} {preset_opts} -t {threads} {extra_args} "
            f"{ref_path} {input_path} | "
            f"{self.samtools_path} sort -@ {threads} -o {output_path} -"
        )
        
        print(f"Running: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Index BAM
            subprocess.run([self.samtools_path, "index", str(output_path)], check=True)
        
        return cmd, result.returncode
    
    def align_dorado(self, input_path: Path, ref_path: Path, output_path: Path,
                     threads: int = 4, extra_args: str = "") -> Tuple[str, int]:
        """Run dorado aligner."""
        if not self.dorado_path:
            raise RuntimeError("dorado not found in PATH")
        if not self.samtools_path:
            raise RuntimeError("samtools not found in PATH")
        
        # Dorado aligner command
        cmd = (
            f"{self.dorado_path} aligner {ref_path} {input_path} "
            f"-t {threads} {extra_args} | "
            f"{self.samtools_path} sort -@ {threads} -o {output_path} -"
        )
        
        print(f"Running: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Index BAM
            subprocess.run([self.samtools_path, "index", str(output_path)], check=True)
        
        return cmd, result.returncode
    
    def align(self, input_path: str, reference: str, output_path: str,
              aligner: str = "auto", preset: str = "auto",
              threads: int = 4, extra_args: str = "") -> AlignmentResult:
        """
        Main alignment entry point.
        
        Args:
            input_path: Input BAM/FASTQ/POD5 file
            reference: Reference name (from registry) or path
            output_path: Output BAM path
            aligner: "minimap2", "dorado", or "auto"
            preset: minimap2 preset or "auto"
            threads: Number of threads
            extra_args: Additional aligner arguments
        """
        input_p = Path(input_path)
        output_p = Path(output_path)
        
        if not input_p.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # Resolve reference
        ref = self.ref_registry.get(reference)
        if ref:
            ref_path = Path(ref.path)
        else:
            ref_path = Path(reference)
            if not ref_path.exists():
                raise FileNotFoundError(f"Reference not found: {reference}")
        
        # Detect input type
        input_type = self._detect_input_type(input_p)
        
        # Auto-select aligner
        if aligner == "auto":
            if input_type == "pod5" and self.dorado_path:
                aligner = "dorado"
            else:
                aligner = "minimap2"
        
        # Auto-detect preset
        if preset == "auto":
            preset = self._detect_preset(input_p, input_type)
        
        # Run alignment
        start_time = datetime.now(timezone.utc)
        
        if aligner == "minimap2":
            cmd, exit_code = self.align_minimap2(
                input_p, ref_path, output_p, preset, threads, extra_args
            )
        elif aligner == "dorado":
            cmd, exit_code = self.align_dorado(
                input_p, ref_path, output_p, threads, extra_args
            )
        else:
            raise ValueError(f"Unknown aligner: {aligner}")
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        if exit_code != 0:
            raise RuntimeError(f"Alignment failed with exit code {exit_code}")
        
        # Compute stats
        stats = self.compute_stats(output_p)
        
        result = AlignmentResult(
            input_file=str(input_p),
            output_bam=str(output_p),
            reference=reference,
            aligner=aligner,
            preset=preset,
            alignment_stats=stats,
            command=cmd,
            duration_seconds=duration,
            timestamp=start_time.isoformat(),
            output_files={"bam": str(output_p), "bai": str(output_p) + ".bai"},
        )
        
        return result
    
    def compute_stats(self, bam_path: Path) -> AlignmentStats:
        """Compute alignment statistics from BAM file."""
        stats = AlignmentStats()
        
        if not HAS_PYSAM:
            # Fall back to samtools flagstat
            return self._stats_from_flagstat(bam_path)
        
        mapqs = []
        read_lengths = []
        aligned_lengths = []
        
        try:
            with pysam.AlignmentFile(str(bam_path), "rb") as bam:
                for read in bam.fetch(until_eof=True):
                    stats.total_reads += 1
                    
                    if read.is_unmapped:
                        stats.unmapped_reads += 1
                    else:
                        stats.mapped_reads += 1
                        mapqs.append(read.mapping_quality)
                        aligned_lengths.append(read.query_alignment_length or 0)
                    
                    if read.is_secondary:
                        stats.secondary_alignments += 1
                    elif read.is_supplementary:
                        stats.supplementary_alignments += 1
                    else:
                        stats.primary_alignments += 1
                    
                    if read.query_length:
                        read_lengths.append(read.query_length)
        except Exception as e:
            print(f"Warning: Error reading BAM: {e}", file=sys.stderr)
            return self._stats_from_flagstat(bam_path)
        
        # Compute summary statistics
        if mapqs:
            stats.mean_mapq = sum(mapqs) / len(mapqs)
            sorted_mapqs = sorted(mapqs)
            stats.median_mapq = sorted_mapqs[len(sorted_mapqs) // 2]
            
            # MAPQ distribution
            for q in mapqs:
                bucket = (q // 10) * 10
                stats.mapq_distribution[bucket] = stats.mapq_distribution.get(bucket, 0) + 1
        
        if read_lengths:
            stats.mean_read_length = sum(read_lengths) / len(read_lengths)
            sorted_lengths = sorted(read_lengths, reverse=True)
            stats.median_read_length = sorted_lengths[len(sorted_lengths) // 2]
            
            # N50
            cumsum = 0
            half_total = sum(read_lengths) / 2
            for length in sorted_lengths:
                cumsum += length
                if cumsum >= half_total:
                    stats.n50_read_length = length
                    break
        
        if aligned_lengths:
            stats.mean_aligned_length = sum(aligned_lengths) / len(aligned_lengths)
            stats.total_aligned_bases = sum(aligned_lengths)
        
        return stats
    
    def _stats_from_flagstat(self, bam_path: Path) -> AlignmentStats:
        """Get stats using samtools flagstat."""
        stats = AlignmentStats()
        
        if not self.samtools_path:
            return stats
        
        try:
            result = subprocess.run(
                [self.samtools_path, "flagstat", str(bam_path)],
                capture_output=True, text=True, check=True
            )
            
            for line in result.stdout.split('\n'):
                if 'in total' in line:
                    stats.total_reads = int(line.split()[0])
                elif 'mapped (' in line and 'primary' not in line:
                    stats.mapped_reads = int(line.split()[0])
                elif 'secondary' in line:
                    stats.secondary_alignments = int(line.split()[0])
                elif 'supplementary' in line:
                    stats.supplementary_alignments = int(line.split()[0])
            
            stats.unmapped_reads = stats.total_reads - stats.mapped_reads
            stats.primary_alignments = stats.total_reads - stats.secondary_alignments - stats.supplementary_alignments
            
        except Exception as e:
            print(f"Warning: flagstat failed: {e}", file=sys.stderr)
        
        return stats
    
    def compute_coverage(self, bam_path: Path, output_bed: Path = None,
                        output_bedgraph: Path = None) -> CoverageStats:
        """Compute coverage statistics."""
        stats = CoverageStats()
        
        if not self.samtools_path:
            print("Warning: samtools not found, cannot compute coverage", file=sys.stderr)
            return stats
        
        # Use samtools depth
        try:
            result = subprocess.run(
                [self.samtools_path, "depth", "-a", str(bam_path)],
                capture_output=True, text=True, check=True
            )
            
            coverages = []
            chrom_coverages = defaultdict(list)
            
            for line in result.stdout.split('\n'):
                if not line:
                    continue
                parts = line.split('\t')
                if len(parts) >= 3:
                    chrom = parts[0]
                    cov = int(parts[2])
                    coverages.append(cov)
                    chrom_coverages[chrom].append(cov)
            
            if coverages:
                stats.reference_length = len(coverages)
                stats.covered_bases = sum(1 for c in coverages if c > 0)
                stats.mean_coverage = sum(coverages) / len(coverages)
                stats.min_coverage = min(coverages)
                stats.max_coverage = max(coverages)
                
                sorted_cov = sorted(coverages)
                stats.median_coverage = sorted_cov[len(sorted_cov) // 2]
                
                if HAS_NUMPY:
                    stats.std_coverage = float(np.std(coverages))
                
                # Coverage thresholds
                stats.pct_1x = sum(1 for c in coverages if c >= 1) / len(coverages) * 100
                stats.pct_5x = sum(1 for c in coverages if c >= 5) / len(coverages) * 100
                stats.pct_10x = sum(1 for c in coverages if c >= 10) / len(coverages) * 100
                stats.pct_20x = sum(1 for c in coverages if c >= 20) / len(coverages) * 100
                stats.pct_30x = sum(1 for c in coverages if c >= 30) / len(coverages) * 100
                
                # Per-chromosome
                for chrom, cov_list in chrom_coverages.items():
                    stats.per_chrom[chrom] = {
                        "length": len(cov_list),
                        "mean_coverage": sum(cov_list) / len(cov_list),
                        "covered_pct": sum(1 for c in cov_list if c > 0) / len(cov_list) * 100,
                    }
            
            # Write BED if requested
            if output_bed:
                self._write_coverage_bed(bam_path, output_bed)
            
            # Write bedGraph if requested
            if output_bedgraph:
                self._write_bedgraph(bam_path, output_bedgraph)
                
        except Exception as e:
            print(f"Warning: Coverage calculation failed: {e}", file=sys.stderr)
        
        return stats
    
    def _write_coverage_bed(self, bam_path: Path, output_path: Path):
        """Write coverage as BED file."""
        cmd = f"{self.samtools_path} depth -a {bam_path} | awk '{{print $1\"\\t\"$2-1\"\\t\"$2\"\\t\"$3}}' > {output_path}"
        subprocess.run(cmd, shell=True, check=True)
    
    def _write_bedgraph(self, bam_path: Path, output_path: Path):
        """Write coverage as bedGraph file."""
        # Use bedtools if available, otherwise samtools
        bedtools = shutil.which("bedtools")
        if bedtools:
            cmd = f"{bedtools} genomecov -ibam {bam_path} -bg > {output_path}"
        else:
            cmd = f"{self.samtools_path} depth {bam_path} | awk '{{print $1\"\\t\"$2-1\"\\t\"$2\"\\t\"$3}}' > {output_path}"
        subprocess.run(cmd, shell=True, check=True)


# =============================================================================
# CLI
# =============================================================================

def cmd_align(args):
    """Run alignment."""
    registry = ReferenceRegistry()
    aligner = Aligner(registry)
    
    result = aligner.align(
        input_path=args.input,
        reference=args.ref,
        output_path=args.output,
        aligner=args.aligner,
        preset=args.preset,
        threads=args.threads,
        extra_args=args.extra_args or "",
    )
    
    # Compute coverage if requested
    if args.coverage or args.bedgraph:
        cov_stats = aligner.compute_coverage(
            Path(args.output),
            output_bed=Path(args.coverage) if args.coverage else None,
            output_bedgraph=Path(args.bedgraph) if args.bedgraph else None,
        )
        result.coverage_stats = cov_stats
        if args.coverage:
            result.output_files["coverage_bed"] = args.coverage
        if args.bedgraph:
            result.output_files["bedgraph"] = args.bedgraph
    
    # Output JSON
    if args.json:
        with open(args.json, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
        result.output_files["json"] = args.json
        print(f"Results saved to: {args.json}")
    
    # Print summary
    if not args.quiet:
        print(f"\n{'='*50}")
        print(f"Alignment Complete")
        print(f"{'='*50}")
        print(f"Input:      {result.input_file}")
        print(f"Output:     {result.output_bam}")
        print(f"Reference:  {result.reference}")
        print(f"Aligner:    {result.aligner} (preset: {result.preset})")
        print(f"Duration:   {result.duration_seconds:.1f}s")
        print(f"\nAlignment Stats:")
        print(f"  Total reads:   {result.alignment_stats.total_reads:,}")
        print(f"  Mapped reads:  {result.alignment_stats.mapped_reads:,} ({result.alignment_stats.mapping_rate:.1f}%)")
        print(f"  Mean MAPQ:     {result.alignment_stats.mean_mapq:.1f}")
        print(f"  Mean length:   {result.alignment_stats.mean_read_length:.0f} bp")
        
        if result.coverage_stats and result.coverage_stats.reference_length > 0:
            print(f"\nCoverage Stats:")
            print(f"  Mean coverage: {result.coverage_stats.mean_coverage:.1f}x")
            print(f"  Breadth:       {result.coverage_stats.breadth:.1f}%")
            print(f"  ≥10x:          {result.coverage_stats.pct_10x:.1f}%")
            print(f"  ≥30x:          {result.coverage_stats.pct_30x:.1f}%")


def cmd_qc(args):
    """Run QC on existing BAM."""
    aligner = Aligner()
    
    bam_path = Path(args.bam)
    if not bam_path.exists():
        print(f"Error: BAM file not found: {args.bam}", file=sys.stderr)
        sys.exit(1)
    
    # Compute stats
    stats = aligner.compute_stats(bam_path)
    
    # Compute coverage
    cov_stats = None
    if args.coverage or args.bedgraph or args.full:
        cov_stats = aligner.compute_coverage(
            bam_path,
            output_bed=Path(args.coverage) if args.coverage else None,
            output_bedgraph=Path(args.bedgraph) if args.bedgraph else None,
        )
    
    result = {
        "bam_file": str(bam_path),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "alignment_stats": stats.to_dict(),
    }
    if cov_stats:
        result["coverage_stats"] = cov_stats.to_dict()
    
    # Output JSON
    if args.json:
        with open(args.json, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"QC results saved to: {args.json}")
    
    # Print summary
    if not args.quiet:
        print(f"\n{'='*50}")
        print(f"BAM QC: {bam_path.name}")
        print(f"{'='*50}")
        print(f"\nAlignment Stats:")
        print(f"  Total reads:   {stats.total_reads:,}")
        print(f"  Mapped:        {stats.mapped_reads:,} ({stats.mapping_rate:.1f}%)")
        print(f"  Unmapped:      {stats.unmapped_reads:,}")
        print(f"  Primary:       {stats.primary_alignments:,}")
        print(f"  Secondary:     {stats.secondary_alignments:,}")
        print(f"  Supplementary: {stats.supplementary_alignments:,}")
        print(f"  Mean MAPQ:     {stats.mean_mapq:.1f}")
        print(f"  Median MAPQ:   {stats.median_mapq:.1f}")
        print(f"  Mean length:   {stats.mean_read_length:.0f} bp")
        print(f"  N50 length:    {stats.n50_read_length:,} bp")
        
        if cov_stats and cov_stats.reference_length > 0:
            print(f"\nCoverage Stats:")
            print(f"  Reference:     {cov_stats.reference_length:,} bp")
            print(f"  Covered:       {cov_stats.covered_bases:,} bp ({cov_stats.breadth:.1f}%)")
            print(f"  Mean coverage: {cov_stats.mean_coverage:.1f}x")
            print(f"  Median:        {cov_stats.median_coverage:.1f}x")
            print(f"  ≥1x:           {cov_stats.pct_1x:.1f}%")
            print(f"  ≥10x:          {cov_stats.pct_10x:.1f}%")
            print(f"  ≥20x:          {cov_stats.pct_20x:.1f}%")
            print(f"  ≥30x:          {cov_stats.pct_30x:.1f}%")


def cmd_refs(args):
    """Reference management commands."""
    registry = ReferenceRegistry()
    
    if args.refs_cmd == "init":
        registry.init(scan_paths=not args.no_scan)
        
    elif args.refs_cmd == "list":
        refs = registry.list()
        if not refs:
            print("No references registered. Use 'ont_align.py refs init' or 'refs add'.")
            print("\nAvailable built-in references (need to be added):")
            for name, info in BUILTIN_REFERENCES.items():
                print(f"  {name}: {info['name']}")
            return
        
        print(f"\nRegistered References ({len(refs)}):")
        print("-" * 70)
        for ref in refs:
            indexed = "✓" if ref.indexed else "✗"
            size_mb = ref.size_bytes / 1e6
            print(f"  {ref.name:<20} {indexed} indexed  {size_mb:>8.1f} MB  {ref.path}")
        print("-" * 70)
        
    elif args.refs_cmd == "add":
        ref = registry.add(
            path=args.path,
            name=args.name,
            description=args.description or "",
            aliases=args.aliases.split(",") if args.aliases else [],
            index=not args.no_index,
        )
        print(f"Added reference: {ref.name}")
        print(f"  Path: {ref.path}")
        print(f"  Indexed: {ref.indexed}")
        
    elif args.refs_cmd == "remove":
        registry.remove(args.name)
        print(f"Removed reference: {args.name}")
        
    elif args.refs_cmd == "info":
        ref = registry.get(args.name)
        if not ref:
            print(f"Reference not found: {args.name}")
            sys.exit(1)
        
        print(f"\nReference: {ref.name}")
        print(f"  Path:        {ref.path}")
        print(f"  Size:        {ref.size_bytes / 1e6:.1f} MB")
        print(f"  Checksum:    {ref.checksum}")
        print(f"  Indexed:     {ref.indexed} ({ref.index_type})")
        print(f"  Added:       {ref.added_date}")
        if ref.aliases:
            print(f"  Aliases:     {', '.join(ref.aliases)}")
        if ref.description:
            print(f"  Description: {ref.description}")


def main():
    parser = argparse.ArgumentParser(
        description="ONT Align - Oxford Nanopore alignment with reference management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Align reads to reference
  ont_align.py align input.bam --ref hg38 --output aligned.bam
  
  # With coverage outputs
  ont_align.py align input.bam --ref hs1 --output aligned.bam \\
    --coverage cov.bed --bedgraph cov.bg --json stats.json
  
  # QC existing BAM
  ont_align.py qc aligned.bam --json qc.json --coverage cov.bed
  
  # Reference management
  ont_align.py refs init
  ont_align.py refs list
  ont_align.py refs add /path/to/ref.fa --name my_ref
  
  # Via ont-experiments (recommended)
  ont_experiments.py run alignment exp-abc123 --ref hg38 --output aligned.bam
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Align command
    align_parser = subparsers.add_parser("align", help="Align reads to reference")
    align_parser.add_argument("input", help="Input BAM/FASTQ file")
    align_parser.add_argument("--ref", "-r", required=True, help="Reference name or path")
    align_parser.add_argument("--output", "-o", required=True, help="Output BAM path")
    align_parser.add_argument("--aligner", choices=["minimap2", "dorado", "auto"], default="auto",
                             help="Aligner to use (default: auto)")
    align_parser.add_argument("--preset", default="auto",
                             help="Minimap2 preset (default: auto-detect)")
    align_parser.add_argument("--threads", "-t", type=int, default=4, help="Threads (default: 4)")
    align_parser.add_argument("--extra-args", help="Extra aligner arguments")
    align_parser.add_argument("--coverage", help="Output coverage BED file")
    align_parser.add_argument("--bedgraph", help="Output bedGraph file")
    align_parser.add_argument("--json", help="Output JSON stats file")
    align_parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode")
    
    # QC command
    qc_parser = subparsers.add_parser("qc", help="QC analysis of BAM file")
    qc_parser.add_argument("bam", help="Input BAM file")
    qc_parser.add_argument("--json", help="Output JSON file")
    qc_parser.add_argument("--coverage", help="Output coverage BED file")
    qc_parser.add_argument("--bedgraph", help="Output bedGraph file")
    qc_parser.add_argument("--full", action="store_true", help="Compute all metrics")
    qc_parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode")
    
    # Refs command
    refs_parser = subparsers.add_parser("refs", help="Reference genome management")
    refs_subparsers = refs_parser.add_subparsers(dest="refs_cmd", help="Reference commands")
    
    # refs init
    refs_init = refs_subparsers.add_parser("init", help="Initialize reference registry")
    refs_init.add_argument("--no-scan", action="store_true", help="Don't scan default paths")
    
    # refs list
    refs_subparsers.add_parser("list", help="List registered references")
    
    # refs add
    refs_add = refs_subparsers.add_parser("add", help="Add reference to registry")
    refs_add.add_argument("path", help="Path to reference FASTA")
    refs_add.add_argument("--name", help="Reference name (default: filename)")
    refs_add.add_argument("--description", help="Description")
    refs_add.add_argument("--aliases", help="Comma-separated aliases")
    refs_add.add_argument("--no-index", action="store_true", help="Don't create index")
    
    # refs remove
    refs_remove = refs_subparsers.add_parser("remove", help="Remove reference from registry")
    refs_remove.add_argument("name", help="Reference name to remove")
    
    # refs info
    refs_info = refs_subparsers.add_parser("info", help="Show reference details")
    refs_info.add_argument("name", help="Reference name")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "align":
        cmd_align(args)
    elif args.command == "qc":
        cmd_qc(args)
    elif args.command == "refs":
        if not args.refs_cmd:
            refs_parser.print_help()
            sys.exit(1)
        cmd_refs(args)


if __name__ == "__main__":
    main()
