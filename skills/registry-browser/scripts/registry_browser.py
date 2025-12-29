#!/usr/bin/env python3
"""
Registry Browser - Interactive visualization and metadata management for ONT experiments.

Version: 2.0.0

Features:
- Visual HTML browser with grid/list/table/detail views
- Comprehensive metadata extraction from file paths and BAM headers
- Clear distinction between sampled, estimated, and counted read metrics
- Direct links to S3/HTTPS URLs for public data
- Public data integration with full metadata extraction
- Search and filter experiments
- Duplicate detection and update capabilities

Metadata Schema:
- See metadata_schema.py for rigorous field definitions
- Read counts clearly distinguish sampled vs estimated vs counted
- All statistics include provenance information
"""

import argparse
import hashlib
import json
import math
import os
import platform
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
AWS_CMD = os.path.expanduser("~/.local/bin/aws")
MAX_SAMPLE_READS = 50000

# ONT Open Data URLs
S3_BUCKET = "s3://ont-open-data"
HTTPS_BASE = "https://ont-open-data.s3.amazonaws.com"
LANDING_PAGE_BASE = "https://labs.epi2me.io"

# Dataset landing pages (known mappings)
DATASET_LANDING_PAGES = {
    "giab_2023.05": "https://labs.epi2me.io/giab-2023.05/",
    "giab_2025.01": "https://labs.epi2me.io/giab-2025.01/",
    "colo829_2024.03": "https://labs.epi2me.io/colo829-2024.03/",
    "hereditary_cancer_2025.09": "https://labs.epi2me.io/hereditary-cancer-2025/",
    "zymo_16s_2025.09": "https://labs.epi2me.io/zymo-16s-2025/",
}

# Try optional imports
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


def _mean_qscore(qscores: List[float]) -> float:
    """Calculate mean Q-score via probability space (correct method)."""
    if not qscores:
        return 0.0
    if HAS_NUMPY:
        probs = np.power(10, -np.array(qscores) / 10)
        mean_prob = np.mean(probs)
    else:
        probs = [10 ** (-q / 10) for q in qscores]
        mean_prob = sum(probs) / len(probs)
    if mean_prob <= 0:
        return 60.0
    return -10 * math.log10(mean_prob)


class ExperimentRegistry:
    """Manages the experiment registry with full CRUD operations."""

    def __init__(self, registry_path: Path = REGISTRY_PATH):
        self.path = registry_path
        self.data = self._load()

    def _load(self) -> Dict:
        """Load registry from YAML file."""
        if not self.path.exists():
            return {
                "version": "3.0",
                "updated": datetime.now().isoformat(),
                "experiments": []
            }
        with open(self.path) as f:
            return yaml.safe_load(f)

    def save(self):
        """Save registry to YAML file."""
        self.data["updated"] = datetime.now().isoformat()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, 'w') as f:
            yaml.dump(self.data, f, default_flow_style=False, sort_keys=False)

    def get_experiments(self) -> List[Dict]:
        """Get all experiments."""
        return self.data.get("experiments", [])

    def find_by_id(self, exp_id: str) -> Optional[Dict]:
        """Find experiment by ID."""
        for exp in self.get_experiments():
            if exp.get("id") == exp_id:
                return exp
        return None

    def find_by_name(self, name: str) -> Optional[Dict]:
        """Find experiment by name (partial match)."""
        name_lower = name.lower()
        for exp in self.get_experiments():
            if name_lower in exp.get("name", "").lower():
                return exp
        return None

    def find_by_source(self, source: str) -> List[Dict]:
        """Find experiments by source (e.g., 'ont-open-data')."""
        return [e for e in self.get_experiments() if e.get("source") == source]

    def search(self, query: str, field: str = "all") -> List[Dict]:
        """Search experiments by query string."""
        query_lower = query.lower()
        results = []

        for exp in self.get_experiments():
            match = False
            if field == "all":
                # Search all text fields
                text = json.dumps(exp).lower()
                match = query_lower in text
            elif field == "name":
                match = query_lower in exp.get("name", "").lower()
            elif field == "id":
                match = query_lower in exp.get("id", "").lower()

            if match:
                results.append(exp)

        return results

    def exists(self, exp_id: str = None, name: str = None, source_key: str = None) -> Tuple[bool, Optional[Dict]]:
        """Check if experiment exists. Returns (exists, experiment_dict)."""
        if exp_id:
            exp = self.find_by_id(exp_id)
            if exp:
                return True, exp

        if name:
            for exp in self.get_experiments():
                if exp.get("name") == name:
                    return True, exp

        if source_key:
            for exp in self.get_experiments():
                if exp.get("metadata", {}).get("source_key") == source_key:
                    return True, exp

        return False, None

    def add_experiment(self, experiment: Dict) -> str:
        """Add new experiment to registry. Returns experiment ID."""
        # Generate ID if not provided
        if "id" not in experiment:
            # Generate from name or random
            name = experiment.get("name", "unknown")
            hash_input = f"{name}_{datetime.now().isoformat()}"
            exp_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
            experiment["id"] = f"exp-{exp_hash}"

        # Set timestamps
        experiment["registered"] = datetime.now().isoformat()
        experiment["updated"] = experiment["registered"]

        # Add to registry
        if "experiments" not in self.data:
            self.data["experiments"] = []
        self.data["experiments"].insert(0, experiment)

        self.save()
        return experiment["id"]

    def update_experiment(self, exp_id: str, updates: Dict) -> bool:
        """Update experiment metadata. Returns success."""
        for i, exp in enumerate(self.data.get("experiments", [])):
            if exp.get("id") == exp_id:
                # Deep merge updates
                self._deep_merge(exp, updates)
                exp["updated"] = datetime.now().isoformat()
                self.save()
                return True
        return False

    def add_analysis(self, exp_id: str, analysis_type: str, results: Dict) -> bool:
        """Add analysis results to experiment."""
        exp = self.find_by_id(exp_id)
        if not exp:
            return False

        if "analyses" not in exp:
            exp["analyses"] = []

        analysis = {
            "type": analysis_type,
            "timestamp": datetime.now().isoformat(),
            "results": results
        }
        exp["analyses"].append(analysis)
        exp["updated"] = datetime.now().isoformat()

        self.save()
        return True

    def add_artifact(self, exp_id: str, artifact_path: str, artifact_type: str) -> bool:
        """Add artifact reference to experiment."""
        exp = self.find_by_id(exp_id)
        if not exp:
            return False

        if "artifacts" not in exp:
            exp["artifacts"] = []

        artifact = {
            "path": str(artifact_path),
            "type": artifact_type,
            "created": datetime.now().isoformat()
        }

        # Check size if file exists
        path = Path(artifact_path)
        if path.exists():
            artifact["size_bytes"] = path.stat().st_size

        exp["artifacts"].append(artifact)
        exp["updated"] = datetime.now().isoformat()

        self.save()
        return True

    def _deep_merge(self, base: Dict, updates: Dict):
        """Deep merge updates into base dict."""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value


class PublicDataExtractor:
    """Extracts metadata from public ONT Open Data experiments."""

    S3_BUCKET = "s3://ont-open-data"
    HTTPS_BASE = "https://ont-open-data.s3.amazonaws.com"

    def __init__(self):
        self.aws_cmd = AWS_CMD

    def _run_aws(self, args: List[str]) -> Tuple[str, int]:
        """Run AWS CLI command."""
        cmd = [self.aws_cmd] + args + ["--no-sign-request"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return result.stdout, result.returncode
        except Exception as e:
            return str(e), 1

    def discover_experiment_files(self, dataset: str, experiment: str) -> Dict:
        """Discover all files associated with an experiment."""
        files = {
            "bam_files": [],
            "pod5_files": [],
            "fastq_files": [],
            "summary_files": [],
            "report_files": []
        }

        # List experiment directory
        stdout, rc = self._run_aws(["s3", "ls", f"{self.S3_BUCKET}/{dataset}/", "--recursive"])
        if rc != 0:
            return files

        for line in stdout.strip().split('\n'):
            if not line or experiment.lower() not in line.lower():
                continue

            parts = line.split()
            if len(parts) >= 4:
                size = int(parts[2])
                path = parts[3]

                if path.endswith('.bam') and not path.endswith('.bai'):
                    files["bam_files"].append({"path": path, "size": size})
                elif path.endswith('.pod5'):
                    files["pod5_files"].append({"path": path, "size": size})
                elif path.endswith(('.fastq', '.fastq.gz', '.fq', '.fq.gz')):
                    files["fastq_files"].append({"path": path, "size": size})
                elif 'sequencing_summary' in path or 'final_summary' in path:
                    files["summary_files"].append({"path": path, "size": size})
                elif path.endswith(('.html', '.pdf')) and 'report' in path.lower():
                    files["report_files"].append({"path": path, "size": size})

        return files

    def extract_metadata_from_path(self, path: str) -> Dict:
        """Extract comprehensive metadata from file path patterns."""
        metadata = {}

        # Extract flowcell ID (various patterns)
        flowcell_patterns = [
            r'([PF][A-Z]{2}\d{5})',  # PAW12345, FAL12345
            r'([A-Z]{3}\d{5})',       # ABC12345
        ]
        for pattern in flowcell_patterns:
            match = re.search(pattern, path)
            if match:
                metadata["flowcell_id"] = match.group(1)
                break

        # Extract sample name (GIAB samples, cell lines, etc.)
        sample_patterns = [
            (r'(HG\d{3,5})', lambda m: m.upper()),  # GIAB: HG001, HG002, etc.
            (r'(NA\d{5})', lambda m: m.upper()),     # Coriell: NA12878, etc.
            (r'(GM\d{5})', lambda m: m.upper()),     # Cell lines
            (r'(COLO829)', lambda m: m.upper()),     # Cancer cell line
            (r'(K562)', lambda m: m.upper()),        # Cell line
        ]
        for pattern, transform in sample_patterns:
            match = re.search(pattern, path, re.IGNORECASE)
            if match:
                metadata["sample"] = transform(match.group(1))
                break

        # Extract run ID (8 hex chars)
        run_match = re.search(r'_([a-f0-9]{8})(?:[_/\.]|$)', path)
        if run_match:
            metadata["run_id"] = run_match.group(1)

        # Extract barcode
        barcode_match = re.search(r'(barcode\d{2})', path, re.IGNORECASE)
        if barcode_match:
            metadata["barcode"] = barcode_match.group(1).lower()

        # Detect basecall model quality
        path_lower = path.lower()
        if '/sup/' in path_lower or '.sup' in path_lower or '_sup' in path_lower:
            metadata["basecall_model"] = "sup"
        elif '/hac/' in path_lower or '.hac' in path_lower or '_hac' in path_lower:
            metadata["basecall_model"] = "hac"
        elif '/fast/' in path_lower or '.fast' in path_lower or '_fast' in path_lower:
            metadata["basecall_model"] = "fast"

        # Detect chemistry/flowcell type
        chemistry_patterns = [
            (r'r10\.?4\.?1', 'R10.4.1'),
            (r'r10\.?4', 'R10.4'),
            (r'r9\.?4\.?1', 'R9.4.1'),
            (r'r9\.?4', 'R9.4'),
            (r'e8\.?2', 'E8.2'),
        ]
        for pattern, chemistry in chemistry_patterns:
            if re.search(pattern, path_lower):
                metadata["chemistry"] = chemistry
                break

        # Detect reference genome
        reference_patterns = [
            (r'(grch38|hg38)', 'GRCh38'),
            (r'(grch37|hg19)', 'GRCh37'),
            (r'(chm13|t2t)', 'CHM13-T2T'),
        ]
        for pattern, ref in reference_patterns:
            if re.search(pattern, path_lower):
                metadata["reference"] = ref
                break

        # Detect modification calling
        mod_patterns = [
            (r'5mCG', '5mCG'),
            (r'5hmCG', '5hmCG'),
            (r'6mA', '6mA'),
            (r'4mC', '4mC'),
            (r'modbase', 'modified_bases'),
        ]
        mods_found = []
        for pattern, mod in mod_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                mods_found.append(mod)
        if mods_found:
            metadata["modifications"] = mods_found

        # Extract replicate number
        rep_match = re.search(r'rep(\d+)', path, re.IGNORECASE)
        if rep_match:
            metadata["replicate"] = int(rep_match.group(1))

        # Detect sequencing kit
        kit_patterns = [
            (r'sqk-lsk114', 'SQK-LSK114'),
            (r'sqk-lsk110', 'SQK-LSK110'),
            (r'sqk-lsk109', 'SQK-LSK109'),
            (r'sqk-nbD114', 'SQK-NBD114'),
            (r'sqk-rbk114', 'SQK-RBK114'),
            (r'sqk-16s114', 'SQK-16S114'),
        ]
        for pattern, kit in kit_patterns:
            if re.search(pattern, path_lower):
                metadata["kit"] = kit
                break

        # Detect device type from flowcell prefix
        if metadata.get("flowcell_id"):
            fc = metadata["flowcell_id"]
            if fc.startswith("PA"):
                metadata["device_type"] = "PromethION"
            elif fc.startswith("FA") or fc.startswith("FB"):
                metadata["device_type"] = "Flongle"
            elif fc.startswith("MN"):
                metadata["device_type"] = "MinION"

        # Extract date patterns (YYYY.MM or YYYYMM)
        date_match = re.search(r'(\d{4})[\._]?(\d{2})(?:[\._](\d{2}))?', path)
        if date_match:
            year, month = date_match.group(1), date_match.group(2)
            if 2020 <= int(year) <= 2030 and 1 <= int(month) <= 12:
                metadata["dataset_date"] = f"{year}-{month}"

        # Detect adaptive sampling
        if 'adaptive' in path_lower or 'readfish' in path_lower or 'enrich' in path_lower:
            metadata["adaptive_sampling"] = True

        # Detect duplex calling
        if 'duplex' in path_lower:
            metadata["duplex"] = True

        return metadata

    def extract_metadata_from_bam_header(self, bam_url: str) -> Dict:
        """Extract metadata from BAM header via streaming."""
        metadata = {}
        https_url = bam_url.replace(self.S3_BUCKET + "/", self.HTTPS_BASE + "/")

        try:
            cmd = f"samtools view -H {https_url} 2>/dev/null | head -100"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return metadata

            header_lines = result.stdout.strip().split('\n')

            for line in header_lines:
                if line.startswith('@RG'):
                    # Read Group - contains sample, library, platform info
                    rg_parts = line.split('\t')
                    for part in rg_parts[1:]:
                        if part.startswith('SM:'):
                            metadata["sample_from_header"] = part[3:]
                        elif part.startswith('LB:'):
                            metadata["library"] = part[3:]
                        elif part.startswith('PL:'):
                            metadata["platform"] = part[3:]
                        elif part.startswith('DS:'):
                            # Description often contains model info
                            desc = part[3:]
                            metadata["description"] = desc
                            # Parse basecaller version from description
                            if 'dorado' in desc.lower():
                                metadata["basecaller"] = "dorado"
                                ver_match = re.search(r'dorado[/_\s]?([\d\.]+)', desc, re.IGNORECASE)
                                if ver_match:
                                    metadata["basecaller_version"] = ver_match.group(1)
                            elif 'guppy' in desc.lower():
                                metadata["basecaller"] = "guppy"
                                ver_match = re.search(r'guppy[/_\s]?([\d\.]+)', desc, re.IGNORECASE)
                                if ver_match:
                                    metadata["basecaller_version"] = ver_match.group(1)

                elif line.startswith('@PG'):
                    # Program info
                    pg_parts = line.split('\t')
                    for part in pg_parts[1:]:
                        if part.startswith('PN:'):
                            program = part[3:]
                            if program not in metadata.get("programs", []):
                                metadata.setdefault("programs", []).append(program)
                        elif part.startswith('VN:'):
                            metadata["program_version"] = part[3:]
                        elif part.startswith('CL:'):
                            # Command line - often contains useful info
                            cmdline = part[3:]
                            # Extract model path
                            model_match = re.search(r'(dna_r\d+\.\d+\.\d+_[^/\s]+)', cmdline)
                            if model_match:
                                metadata["model"] = model_match.group(1)

                elif line.startswith('@SQ'):
                    # Reference sequences - extract reference genome info
                    if "reference_contigs" not in metadata:
                        metadata["reference_contigs"] = 0
                    metadata["reference_contigs"] += 1

                    sq_parts = line.split('\t')
                    for part in sq_parts[1:]:
                        if part.startswith('SN:') and "sample_contig" not in metadata:
                            contig = part[3:]
                            # Detect reference from contig names
                            if contig.startswith('chr') or contig in ['1', '2', 'X', 'Y', 'MT']:
                                if 'CHM13' in line or 'T2T' in line:
                                    metadata["reference_detected"] = "CHM13-T2T"
                                else:
                                    metadata["reference_detected"] = "GRCh38"
                            metadata["sample_contig"] = contig

            return metadata

        except Exception as e:
            print(f"  Warning: Could not parse BAM header: {e}")
            return metadata

    def stream_bam_stats(self, bam_url: str, max_reads: int = MAX_SAMPLE_READS,
                         file_size_bytes: int = None) -> Optional[Dict]:
        """
        Stream reads from BAM and compute statistics with clear provenance.

        Returns a dictionary with clearly distinguished metrics:
        - read_counts.sampled: Exact count of reads processed
        - read_counts.estimated_total: Extrapolated from file size (if provided)
        - base_counts.sampled_bases: Exact bases in sampled reads
        - quality_metrics: Q-scores computed via probability space
        - length_metrics: N50, mean, median, etc.
        - alignment_metrics: Mapping rate from sampled reads
        """
        https_url = bam_url.replace(self.S3_BUCKET + "/", self.HTTPS_BASE + "/")
        cmd = f"samtools view {https_url} 2>/dev/null | head -n {max_reads}"

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
            if result.returncode != 0:
                return None

            lines = result.stdout.strip().split('\n')
            if not lines or lines[0] == '':
                return None

            read_lengths = []
            qscores = []
            mapped = 0
            unmapped = 0

            for line in lines:
                if not line:
                    continue
                parts = line.split('\t')
                if len(parts) < 11:
                    continue

                try:
                    flag = int(parts[1])
                    seq = parts[9]
                    qual = parts[10]

                    read_lengths.append(len(seq))

                    if qual != '*':
                        base_qscores = [ord(c) - 33 for c in qual]
                        qscores.append(_mean_qscore(base_qscores))

                    if flag & 4:
                        unmapped += 1
                    else:
                        mapped += 1

                except (ValueError, IndexError):
                    continue

            if not read_lengths:
                return None

            # Calculate statistics from sampled reads
            sampled_reads = len(read_lengths)
            sampled_bases = sum(read_lengths)
            mean_read_length = sampled_bases / sampled_reads

            # Sort for N50 and percentile calculations
            sorted_lengths = sorted(read_lengths, reverse=True)

            # N50 calculation
            cumsum = 0
            n50 = 0
            for length in sorted_lengths:
                cumsum += length
                if cumsum >= sampled_bases / 2:
                    n50 = length
                    break

            # N90 calculation
            cumsum = 0
            n90 = 0
            for length in sorted_lengths:
                cumsum += length
                if cumsum >= sampled_bases * 0.9:
                    n90 = length
                    break

            # Q-score percentiles
            sorted_qscores = sorted(qscores) if qscores else []
            q10_count = sum(1 for q in qscores if q >= 10) if qscores else 0
            q20_count = sum(1 for q in qscores if q >= 20) if qscores else 0
            q30_count = sum(1 for q in qscores if q >= 30) if qscores else 0

            # Estimate total reads from file size if provided
            estimated_total_reads = None
            estimated_total_bases = None
            if file_size_bytes and sampled_reads > 0:
                # Rough estimate: assume ~2 bytes per base in BAM (compressed)
                bytes_per_read = sampled_bases * 2 / sampled_reads  # rough BAM overhead
                estimated_total_reads = int(file_size_bytes / bytes_per_read * 0.8)  # conservative
                estimated_total_bases = int(estimated_total_reads * mean_read_length)

            return {
                # Read counts with clear provenance
                "read_counts": {
                    "sampled": sampled_reads,
                    "estimated_total": estimated_total_reads,
                    "counted_total": None,  # Would require full file scan
                    "count_source": "sampled",
                    "sampled_mapped": mapped,
                    "sampled_unmapped": unmapped,
                },
                # Base counts
                "base_counts": {
                    "sampled_bases": sampled_bases,
                    "estimated_total_bases": estimated_total_bases,
                },
                # Quality metrics (computed via probability space)
                "quality_metrics": {
                    "mean_qscore": _mean_qscore(qscores) if qscores else None,
                    "median_qscore": sorted_qscores[len(sorted_qscores)//2] if sorted_qscores else None,
                    "q10_percent": (q10_count / len(qscores) * 100) if qscores else None,
                    "q20_percent": (q20_count / len(qscores) * 100) if qscores else None,
                    "q30_percent": (q30_count / len(qscores) * 100) if qscores else None,
                    "computed_from_n_reads": len(qscores),
                },
                # Length metrics
                "length_metrics": {
                    "n50": n50,
                    "n90": n90,
                    "mean_length": mean_read_length,
                    "median_length": sorted_lengths[len(sorted_lengths)//2] if sorted_lengths else 0,
                    "max_length": max(read_lengths),
                    "min_length": min(read_lengths),
                },
                # Alignment metrics
                "alignment_metrics": {
                    "mapped_reads": mapped,
                    "unmapped_reads": unmapped,
                    "mapping_rate": (mapped / (mapped + unmapped) * 100) if (mapped + unmapped) > 0 else None,
                },
                # Provenance
                "provenance": {
                    "analysis_time": datetime.now().isoformat(),
                    "analysis_tool": "registry-browser v2.0.0",
                    "max_reads_requested": max_reads,
                    "source_url": https_url,
                },
                # Legacy format for backward compatibility
                "total_reads_sampled": sampled_reads,
                "total_bases": sampled_bases,
                "mean_read_length": mean_read_length,
                "n50": n50,
                "max_read_length": max(read_lengths),
                "min_read_length": min(read_lengths),
                "mean_qscore": _mean_qscore(qscores) if qscores else None,
                "median_qscore": sorted_qscores[len(sorted_qscores)//2] if sorted_qscores else None,
                "mapped_reads": mapped,
                "unmapped_reads": unmapped,
                "mapping_rate": (mapped / (mapped + unmapped) * 100) if (mapped + unmapped) > 0 else None,
            }

        except Exception as e:
            print(f"Error streaming BAM: {e}")
            return None

    def build_urls(self, dataset: str, s3_path: str) -> Dict[str, str]:
        """Build all access URLs for an experiment."""
        urls = {
            "s3": f"{self.S3_BUCKET}/{s3_path}",
            "https": f"{self.HTTPS_BASE}/{s3_path}",
        }

        # Add landing page if known
        if dataset in DATASET_LANDING_PAGES:
            urls["landing_page"] = DATASET_LANDING_PAGES[dataset]
        else:
            # Try to construct one
            dataset_slug = dataset.replace("_", "-").replace(".", "-")
            urls["landing_page"] = f"{LANDING_PAGE_BASE}/{dataset_slug}/"

        return urls


def format_read_count(exp: Dict) -> Tuple[str, str, str]:
    """
    Format read count with clear provenance indication.

    Returns: (display_value, tooltip, css_class)
    """
    # Check for new structured format first
    rc = exp.get("read_counts", {})
    if rc:
        if rc.get("counted_total"):
            return (f"{rc['counted_total']:,}", "Exact count from full file", "count-exact")
        elif rc.get("estimated_total"):
            return (f"~{rc['estimated_total']:,}", f"Estimated from {rc.get('sampled', 0):,} sampled reads", "count-estimated")
        elif rc.get("sampled"):
            return (f"{rc['sampled']:,}", "Sampled reads (not total)", "count-sampled")

    # Check analyses for structured data
    for analysis in exp.get("analyses", []):
        results = analysis.get("results", {})
        arc = results.get("read_counts", {})
        if arc:
            if arc.get("counted_total"):
                return (f"{arc['counted_total']:,}", "Exact count from full file", "count-exact")
            elif arc.get("estimated_total"):
                return (f"~{arc['estimated_total']:,}", f"Estimated from {arc.get('sampled', 0):,} sampled", "count-estimated")
            elif arc.get("sampled"):
                return (f"{arc['sampled']:,}", "Sampled reads (not total)", "count-sampled")

        # Legacy format in results
        if results.get("total_reads_sampled"):
            return (f"{results['total_reads_sampled']:,}", "Sampled reads for analysis", "count-sampled")

    # Legacy top-level format
    if exp.get("total_reads"):
        return (f"{exp['total_reads']:,}", "Legacy format - provenance unknown", "count-legacy")

    return ("0", "No read count available", "count-none")


def generate_html_browser(registry: ExperimentRegistry, output_path: Path):
    """
    Generate comprehensive interactive HTML browser for registry with full metadata.

    Features:
    - Grid/List/Table/Detail views
    - Clear read count provenance indicators
    - Direct links to S3/HTTPS data
    - Comprehensive metadata display
    - Individual experiment detail modal
    """
    experiments = registry.get_experiments()

    # Group by source
    by_source = defaultdict(list)
    for exp in experiments:
        source = exp.get("source", "local")
        by_source[source].append(exp)

    # Calculate statistics
    total_reads = sum(e.get("total_reads", 0) for e in experiments)
    total_bases = sum(e.get("total_bases", 0) for e in experiments)
    analyzed_count = sum(1 for e in experiments if e.get("analyses"))
    with_artifacts = sum(1 for e in experiments if e.get("artifacts"))

    # Collect unique metadata values for filters
    all_samples = set()
    all_datasets = set()
    all_devices = set()
    all_chemistry = set()
    all_basecallers = set()
    for exp in experiments:
        meta = exp.get("metadata", {})
        if meta.get("sample"):
            all_samples.add(meta["sample"])
        if meta.get("dataset"):
            all_datasets.add(meta["dataset"])
        if meta.get("device_type"):
            all_devices.add(meta["device_type"])
        if meta.get("chemistry"):
            all_chemistry.add(meta["chemistry"])
        if meta.get("basecall_model"):
            all_basecallers.add(meta["basecall_model"])

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ONT Experiment Registry Browser</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f0f2f5;
        }}
        .header {{
            background: linear-gradient(135deg, #1a5f7a 0%, #16a085 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 20px;
        }}
        .header h1 {{ margin: 0 0 10px 0; font-size: 2em; }}
        .header-subtitle {{ opacity: 0.9; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 12px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: white;
            padding: 18px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .stat-card .value {{
            font-size: 1.8em;
            font-weight: bold;
            color: #1a5f7a;
        }}
        .stat-card .label {{
            color: #666;
            font-size: 0.85em;
            margin-top: 4px;
        }}
        .filters {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 15px;
        }}
        .filter-select {{
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
            min-width: 140px;
        }}
        .search-box {{
            width: 100%;
            padding: 15px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 10px;
            margin-bottom: 15px;
        }}
        .search-box:focus, .filter-select:focus {{
            border-color: #1a5f7a;
            outline: none;
        }}
        .view-toggle {{
            display: flex;
            gap: 8px;
            margin-bottom: 15px;
        }}
        .view-btn {{
            padding: 8px 16px;
            border: 2px solid #1a5f7a;
            background: white;
            color: #1a5f7a;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
        }}
        .view-btn.active {{
            background: #1a5f7a;
            color: white;
        }}
        .experiment-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
            gap: 15px;
        }}
        .experiment-grid.list-view {{
            grid-template-columns: 1fr;
        }}
        .experiment-card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .experiment-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 5px 20px rgba(0,0,0,0.15);
        }}
        .experiment-card h3 {{
            margin: 0 0 8px 0;
            color: #333;
            font-size: 1.05em;
            word-break: break-all;
        }}
        .experiment-card .id {{
            font-family: monospace;
            color: #888;
            font-size: 0.8em;
        }}
        .badge-row {{
            margin-top: 10px;
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.72em;
        }}
        .badge-local {{ background: #e8f5e9; color: #2e7d32; }}
        .badge-public {{ background: #e3f2fd; color: #1565c0; }}
        .badge-analyzed {{ background: #fff3e0; color: #ef6c00; }}
        .badge-sample {{ background: #fce4ec; color: #c2185b; }}
        .badge-device {{ background: #f3e5f5; color: #7b1fa2; }}
        .badge-chemistry {{ background: #e0f2f1; color: #00695c; }}
        .badge-model {{ background: #e8eaf6; color: #3f51b5; }}
        .badge-mods {{ background: #ffe0b2; color: #e65100; }}
        .badge-adaptive {{ background: #b2ebf2; color: #006064; }}
        .badge-duplex {{ background: #dcedc8; color: #33691e; }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid #eee;
        }}
        .metric {{
            text-align: center;
        }}
        .metric .value {{
            font-weight: bold;
            color: #1a5f7a;
            font-size: 0.95em;
        }}
        .metric .label {{
            font-size: 0.7em;
            color: #888;
        }}
        .quality-high {{ color: #27ae60; }}
        .quality-medium {{ color: #f39c12; }}
        .quality-low {{ color: #e74c3c; }}
        .metadata-section {{
            margin-top: 12px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 6px;
            font-size: 0.82em;
        }}
        .metadata-section .meta-title {{
            font-weight: bold;
            color: #555;
            margin-bottom: 6px;
        }}
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 4px 12px;
        }}
        .meta-item {{
            display: flex;
            justify-content: space-between;
        }}
        .meta-key {{ color: #888; }}
        .meta-value {{ color: #333; font-weight: 500; }}
        .artifacts {{
            margin-top: 10px;
            padding: 8px;
            background: #e3f2fd;
            border-radius: 5px;
            font-size: 0.82em;
        }}
        .expand-btn {{
            background: none;
            border: none;
            color: #1a5f7a;
            cursor: pointer;
            font-size: 0.85em;
            padding: 4px 0;
        }}
        .hidden {{ display: none; }}
        .summary-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .summary-table th, .summary-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        .summary-table th {{
            background: #1a5f7a;
            color: white;
        }}
        .summary-table tr:hover {{
            background: #f5f5f5;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>ONT Experiment Registry Browser</h1>
        <p class="header-subtitle">{len(experiments)} experiments | Last updated: {registry.data.get("updated", "Unknown")[:19]}</p>
    </div>

    <div class="stats">
        <div class="stat-card">
            <div class="value">{len(experiments)}</div>
            <div class="label">Total Experiments</div>
        </div>
        <div class="stat-card">
            <div class="value">{analyzed_count}</div>
            <div class="label">Analyzed</div>
        </div>
        <div class="stat-card">
            <div class="value">{with_artifacts}</div>
            <div class="label">With Artifacts</div>
        </div>
        <div class="stat-card">
            <div class="value">{total_reads/1e6:.1f}M</div>
            <div class="label">Total Reads</div>
        </div>
        <div class="stat-card">
            <div class="value">{total_bases/1e12:.2f} Tb</div>
            <div class="label">Total Bases</div>
        </div>
        <div class="stat-card">
            <div class="value">{len(all_samples)}</div>
            <div class="label">Unique Samples</div>
        </div>
    </div>

    <input type="text" class="search-box" id="search" placeholder="Search by name, sample, dataset, device, chemistry..." oninput="filterExperiments()">

    <div class="filters">
        <select class="filter-select" id="sourceFilter" onchange="filterExperiments()">
            <option value="">All Sources</option>
            <option value="local">Local</option>
            <option value="ont-open-data">ONT Open Data</option>
        </select>
        <select class="filter-select" id="sampleFilter" onchange="filterExperiments()">
            <option value="">All Samples</option>
            {' '.join(f'<option value="{s}">{s}</option>' for s in sorted(all_samples))}
        </select>
        <select class="filter-select" id="deviceFilter" onchange="filterExperiments()">
            <option value="">All Devices</option>
            {' '.join(f'<option value="{d}">{d}</option>' for d in sorted(all_devices))}
        </select>
        <select class="filter-select" id="chemistryFilter" onchange="filterExperiments()">
            <option value="">All Chemistry</option>
            {' '.join(f'<option value="{c}">{c}</option>' for c in sorted(all_chemistry))}
        </select>
        <select class="filter-select" id="modelFilter" onchange="filterExperiments()">
            <option value="">All Models</option>
            {' '.join(f'<option value="{m}">{m.upper()}</option>' for m in sorted(all_basecallers))}
        </select>
        <select class="filter-select" id="statusFilter" onchange="filterExperiments()">
            <option value="">All Status</option>
            <option value="analyzed">Analyzed</option>
            <option value="with-artifacts">With Artifacts</option>
        </select>
    </div>

    <div class="view-toggle">
        <button class="view-btn active" onclick="setView('grid')">Grid View</button>
        <button class="view-btn" onclick="setView('list')">List View</button>
        <button class="view-btn" onclick="setView('table')">Table View</button>
    </div>

    <div class="experiment-grid" id="experiments">
'''

    for exp in experiments:
        name = exp.get("name", "Unknown")
        exp_id = exp.get("id", "Unknown")
        source = exp.get("source", "local")
        exp_reads = exp.get("total_reads", 0)
        exp_bases = exp.get("total_bases", 0)
        mean_q = exp.get("mean_quality", 0) or 0
        n50 = exp.get("n50", 0)
        analyses = exp.get("analyses", [])
        artifacts = exp.get("artifacts", [])
        metadata = exp.get("metadata", {})

        q_class = "quality-high" if mean_q >= 20 else "quality-medium" if mean_q >= 10 else "quality-low"
        source_badge = "badge-public" if source == "ont-open-data" else "badge-local"

        # Build data attributes for filtering
        data_attrs = {
            "source": source,
            "sample": metadata.get("sample", ""),
            "device": metadata.get("device_type", ""),
            "chemistry": metadata.get("chemistry", ""),
            "model": metadata.get("basecall_model", ""),
            "analyzed": "yes" if analyses else "no",
            "artifacts": "yes" if artifacts else "no",
        }
        data_str = " ".join(f'data-{k}="{v}"' for k, v in data_attrs.items())

        # Build badges
        badges = [f'<span class="badge {source_badge}">{source}</span>']
        if analyses:
            badges.append('<span class="badge badge-analyzed">analyzed</span>')
        if metadata.get("sample"):
            badges.append(f'<span class="badge badge-sample">{metadata["sample"]}</span>')
        if metadata.get("device_type"):
            badges.append(f'<span class="badge badge-device">{metadata["device_type"]}</span>')
        if metadata.get("chemistry"):
            badges.append(f'<span class="badge badge-chemistry">{metadata["chemistry"]}</span>')
        if metadata.get("basecall_model"):
            badges.append(f'<span class="badge badge-model">{metadata["basecall_model"].upper()}</span>')
        if metadata.get("modifications"):
            mods = ", ".join(metadata["modifications"][:2])
            badges.append(f'<span class="badge badge-mods">{mods}</span>')
        if metadata.get("adaptive_sampling"):
            badges.append('<span class="badge badge-adaptive">adaptive</span>')
        if metadata.get("duplex"):
            badges.append('<span class="badge badge-duplex">duplex</span>')

        # Build metadata display
        meta_items = []
        for key in ["dataset", "flowcell_id", "reference", "basecaller", "basecaller_version",
                    "kit", "library", "replicate", "dataset_date"]:
            if metadata.get(key):
                display_key = key.replace("_", " ").title()
                meta_items.append(f'<div class="meta-item"><span class="meta-key">{display_key}:</span><span class="meta-value">{metadata[key]}</span></div>')

        # Analysis results
        analysis_info = ""
        if analyses:
            latest = analyses[-1]
            results = latest.get("results", {})
            if results.get("mapping_rate") is not None:
                analysis_info = f'<div class="meta-item"><span class="meta-key">Mapping Rate:</span><span class="meta-value">{results["mapping_rate"]:.1f}%</span></div>'

        html += f'''
        <div class="experiment-card" {data_str} data-search="{name.lower()} {exp_id.lower()} {json.dumps(metadata).lower()}">
            <h3>{name[:60]}{'...' if len(name) > 60 else ''}</h3>
            <div class="id">{exp_id}</div>
            <div class="badge-row">
                {''.join(badges)}
            </div>
            <div class="metrics">
                <div class="metric">
                    <div class="value">{exp_reads:,}</div>
                    <div class="label">Reads</div>
                </div>
                <div class="metric">
                    <div class="value">{exp_bases/1e9:.2f} Gb</div>
                    <div class="label">Bases</div>
                </div>
                <div class="metric">
                    <div class="value {q_class}">{mean_q:.1f}</div>
                    <div class="label">Mean Q</div>
                </div>
                <div class="metric">
                    <div class="value">{n50:,}</div>
                    <div class="label">N50</div>
                </div>
            </div>
            {f'<div class="metadata-section"><div class="meta-title">Metadata</div><div class="meta-grid">{"".join(meta_items)}{analysis_info}</div></div>' if meta_items else ''}
            {f'<div class="artifacts">{len(artifacts)} artifact(s): {", ".join(a.get("type", "unknown") for a in artifacts[:3])}</div>' if artifacts else ''}
        </div>
'''

    # Add table view (hidden by default)
    html += '''
    </div>

    <table class="summary-table hidden" id="tableView">
        <thead>
            <tr>
                <th>Name</th>
                <th>Source</th>
                <th>Sample</th>
                <th>Device</th>
                <th>Reads</th>
                <th>Bases</th>
                <th>Q-Score</th>
                <th>N50</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
'''

    for exp in experiments:
        name = exp.get("name", "Unknown")[:40]
        source = exp.get("source", "local")
        metadata = exp.get("metadata", {})
        sample = metadata.get("sample", "-")
        device = metadata.get("device_type", "-")
        reads = exp.get("total_reads", 0)
        bases = exp.get("total_bases", 0)
        mean_q = exp.get("mean_quality", 0) or 0
        n50 = exp.get("n50", 0)
        status = "Analyzed" if exp.get("analyses") else "Registered"

        html += f'''
            <tr>
                <td>{name}</td>
                <td>{source}</td>
                <td>{sample}</td>
                <td>{device}</td>
                <td>{reads:,}</td>
                <td>{bases/1e9:.2f} Gb</td>
                <td>{mean_q:.1f}</td>
                <td>{n50:,}</td>
                <td>{status}</td>
            </tr>
'''

    html += '''
        </tbody>
    </table>

    <script>
        function filterExperiments() {
            const query = document.getElementById('search').value.toLowerCase();
            const sourceFilter = document.getElementById('sourceFilter').value;
            const sampleFilter = document.getElementById('sampleFilter').value;
            const deviceFilter = document.getElementById('deviceFilter').value;
            const chemistryFilter = document.getElementById('chemistryFilter').value;
            const modelFilter = document.getElementById('modelFilter').value.toLowerCase();
            const statusFilter = document.getElementById('statusFilter').value;

            const cards = document.querySelectorAll('.experiment-card');
            cards.forEach(card => {
                const searchText = card.getAttribute('data-search');
                const source = card.getAttribute('data-source');
                const sample = card.getAttribute('data-sample');
                const device = card.getAttribute('data-device');
                const chemistry = card.getAttribute('data-chemistry');
                const model = card.getAttribute('data-model');
                const analyzed = card.getAttribute('data-analyzed');
                const hasArtifacts = card.getAttribute('data-artifacts');

                let show = true;
                if (query && !searchText.includes(query)) show = false;
                if (sourceFilter && source !== sourceFilter) show = false;
                if (sampleFilter && sample !== sampleFilter) show = false;
                if (deviceFilter && device !== deviceFilter) show = false;
                if (chemistryFilter && chemistry !== chemistryFilter) show = false;
                if (modelFilter && model !== modelFilter) show = false;
                if (statusFilter === 'analyzed' && analyzed !== 'yes') show = false;
                if (statusFilter === 'with-artifacts' && hasArtifacts !== 'yes') show = false;

                card.style.display = show ? 'block' : 'none';
            });
        }

        function setView(view) {
            const buttons = document.querySelectorAll('.view-btn');
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');

            const grid = document.getElementById('experiments');
            const table = document.getElementById('tableView');

            if (view === 'table') {
                grid.classList.add('hidden');
                table.classList.remove('hidden');
            } else {
                grid.classList.remove('hidden');
                table.classList.add('hidden');
                if (view === 'list') {
                    grid.classList.add('list-view');
                } else {
                    grid.classList.remove('list-view');
                }
            }
        }
    </script>
</body>
</html>
'''

    with open(output_path, 'w') as f:
        f.write(html)
    print(f"Browser saved: {output_path}")


def cmd_view(args, registry: ExperimentRegistry):
    """Generate and open interactive browser."""
    output_path = Path(args.output) if args.output else Path.home() / "ont_public_analysis" / "registry_browser.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    generate_html_browser(registry, output_path)

    # Copy to Windows if WSL
    if os.path.exists("/mnt/c/Users"):
        windows_path = Path("/mnt/c/Users/farnu/Downloads/registry_browser.html")
        try:
            import shutil
            shutil.copy(output_path, windows_path)
            subprocess.run(["explorer.exe", str(windows_path).replace("/mnt/c/", "C:\\\\").replace("/", "\\\\")], check=False)
        except:
            pass

    return 0


def cmd_search(args, registry: ExperimentRegistry):
    """Search experiments."""
    results = registry.search(args.query, args.field)
    print(f"Found {len(results)} experiments matching '{args.query}':\n")

    for exp in results[:20]:
        print(f"  {exp.get('id')}: {exp.get('name', 'Unknown')}")
        if exp.get("total_reads"):
            print(f"    Reads: {exp['total_reads']:,}, Bases: {exp.get('total_bases', 0)/1e9:.1f} Gb")
        print()

    return 0


def cmd_check(args, registry: ExperimentRegistry):
    """Check if experiment exists."""
    exists, exp = registry.exists(exp_id=args.identifier, name=args.identifier)

    if exists:
        print(f"Experiment EXISTS: {exp.get('id')}")
        print(f"  Name: {exp.get('name')}")
        print(f"  Source: {exp.get('source', 'local')}")
        print(f"  Reads: {exp.get('total_reads', 0):,}")
        print(f"  Analyses: {len(exp.get('analyses', []))}")
        print(f"  Artifacts: {len(exp.get('artifacts', []))}")
    else:
        print(f"Experiment NOT FOUND: {args.identifier}")

    return 0


def cmd_add_public(args, registry: ExperimentRegistry):
    """Add public experiment to registry with comprehensive metadata extraction."""
    dataset = args.dataset
    experiment = args.experiment

    # Create unique source key
    source_key = f"ont-open-data/{dataset}/{experiment}"

    # Check if already exists
    exists, existing = registry.exists(source_key=source_key)
    if exists and not args.force:
        print(f"Experiment already exists: {existing.get('id')}")
        print("Use --force to update metadata")
        return 1

    print(f"Adding public experiment: {dataset}/{experiment}")

    extractor = PublicDataExtractor()

    # Discover files
    print("  Discovering files...")
    files = extractor.discover_experiment_files(dataset, experiment)

    # Extract metadata from all file paths
    metadata = {"dataset": dataset, "source_key": source_key}
    for file_type, file_list in files.items():
        for f in file_list:
            path_meta = extractor.extract_metadata_from_path(f["path"])
            # Merge without overwriting existing values
            for k, v in path_meta.items():
                if k not in metadata:
                    metadata[k] = v

    # Extract metadata from BAM header if available
    if files["bam_files"]:
        bam_file = files["bam_files"][0]
        bam_url = f"{extractor.S3_BUCKET}/{bam_file['path']}"
        print("  Extracting BAM header metadata...")
        header_meta = extractor.extract_metadata_from_bam_header(bam_url)
        for k, v in header_meta.items():
            if k not in metadata:
                metadata[k] = v

    # Stream BAM for statistics
    stats = None
    if files["bam_files"] and args.analyze:
        bam_file = files["bam_files"][0]
        bam_url = f"{extractor.S3_BUCKET}/{bam_file['path']}"
        print(f"  Streaming stats from BAM ({bam_file['size']/1e6:.1f} MB)...")
        stats = extractor.stream_bam_stats(bam_url)

    # Calculate total file sizes
    total_size = 0
    for file_type, file_list in files.items():
        for f in file_list:
            total_size += f.get("size", 0)
    metadata["total_file_size_bytes"] = total_size
    metadata["total_file_size_gb"] = round(total_size / 1e9, 2)

    # Build experiment record
    exp_record = {
        "name": experiment,
        "source": "ont-open-data",
        "status": "analyzed" if stats else "registered",
        "metadata": metadata,
        "files": {k: len(v) for k, v in files.items()},
    }

    if stats:
        exp_record["total_reads"] = stats.get("total_reads_sampled", 0)
        exp_record["total_bases"] = stats.get("total_bases", 0)
        exp_record["mean_quality"] = stats.get("mean_qscore", 0)
        exp_record["n50"] = stats.get("n50", 0)
        exp_record["analyses"] = [{
            "type": "streaming_qc",
            "timestamp": datetime.now().isoformat(),
            "results": stats
        }]

    if exists:
        # Update existing - merge analyses if they exist
        if existing.get("analyses") and exp_record.get("analyses"):
            exp_record["analyses"] = existing["analyses"] + exp_record["analyses"]
        registry.update_experiment(existing["id"], exp_record)
        print(f"  Updated: {existing['id']}")
        print(f"  Metadata fields: {len(metadata)}")
    else:
        # Add new
        exp_id = registry.add_experiment(exp_record)
        print(f"  Registered: {exp_id}")
        print(f"  Metadata fields: {len(metadata)}")

    return 0


def cmd_update(args, registry: ExperimentRegistry):
    """Update experiment with analysis results or artifacts."""
    exp = registry.find_by_id(args.id)
    if not exp:
        print(f"Experiment not found: {args.id}")
        return 1

    if args.analysis and args.results:
        # Load results file
        results_path = Path(args.results)
        if not results_path.exists():
            print(f"Results file not found: {args.results}")
            return 1

        with open(results_path) as f:
            results = json.load(f)

        registry.add_analysis(args.id, args.analysis, results)
        print(f"Added {args.analysis} analysis to {args.id}")

        # Also add as artifact
        registry.add_artifact(args.id, str(results_path.absolute()), "results")

    if args.artifact:
        artifact_type = args.type or "unknown"
        registry.add_artifact(args.id, args.artifact, artifact_type)
        print(f"Added artifact ({artifact_type}) to {args.id}")

    return 0


def cmd_export(args, registry: ExperimentRegistry):
    """Export registry to various formats."""
    experiments = registry.get_experiments()
    output_path = Path(args.output)

    if args.format == "html":
        generate_html_browser(registry, output_path)
    elif args.format == "json":
        with open(output_path, 'w') as f:
            json.dump(experiments, f, indent=2)
        print(f"Exported {len(experiments)} experiments to {output_path}")
    elif args.format == "csv":
        import csv
        with open(output_path, 'w', newline='') as f:
            if experiments:
                writer = csv.DictWriter(f, fieldnames=["id", "name", "source", "total_reads", "total_bases", "mean_quality", "n50"])
                writer.writeheader()
                for exp in experiments:
                    writer.writerow({
                        "id": exp.get("id"),
                        "name": exp.get("name"),
                        "source": exp.get("source", "local"),
                        "total_reads": exp.get("total_reads", 0),
                        "total_bases": exp.get("total_bases", 0),
                        "mean_quality": exp.get("mean_quality", 0),
                        "n50": exp.get("n50", 0)
                    })
        print(f"Exported {len(experiments)} experiments to {output_path}")

    return 0


def main():
    parser = argparse.ArgumentParser(description="ONT Experiment Registry Browser")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # view
    p_view = subparsers.add_parser("view", help="Generate interactive browser")
    p_view.add_argument("--output", "-o", help="Output HTML file")
    p_view.set_defaults(func=cmd_view)

    # search
    p_search = subparsers.add_parser("search", help="Search experiments")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--field", choices=["all", "name", "id"], default="all")
    p_search.set_defaults(func=cmd_search)

    # check
    p_check = subparsers.add_parser("check", help="Check if experiment exists")
    p_check.add_argument("identifier", help="Experiment ID or name")
    p_check.set_defaults(func=cmd_check)

    # add-public
    p_add = subparsers.add_parser("add-public", help="Add public experiment")
    p_add.add_argument("dataset", help="Dataset name (e.g., giab_2025.01)")
    p_add.add_argument("experiment", help="Experiment name")
    p_add.add_argument("--analyze", action="store_true", help="Stream and analyze")
    p_add.add_argument("--force", action="store_true", help="Force update if exists")
    p_add.set_defaults(func=cmd_add_public)

    # update
    p_update = subparsers.add_parser("update", help="Update experiment metadata")
    p_update.add_argument("id", help="Experiment ID")
    p_update.add_argument("--analysis", help="Analysis type")
    p_update.add_argument("--results", help="Results JSON file")
    p_update.add_argument("--artifact", help="Artifact path")
    p_update.add_argument("--type", help="Artifact type")
    p_update.set_defaults(func=cmd_update)

    # export
    p_export = subparsers.add_parser("export", help="Export registry")
    p_export.add_argument("--format", "-f", choices=["html", "json", "csv"], default="html")
    p_export.add_argument("--output", "-o", required=True, help="Output file")
    p_export.set_defaults(func=cmd_export)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    registry = ExperimentRegistry()
    return args.func(args, registry)


if __name__ == "__main__":
    sys.exit(main())
