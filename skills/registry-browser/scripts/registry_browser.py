#!/usr/bin/env python3
"""
Registry Browser - Interactive visualization and metadata management for ONT experiments.

Features:
- Visual HTML browser for experiment registry
- Metadata enrichment and artifact tracking
- Public data integration with full metadata extraction
- Search and filter experiments
- Duplicate detection and update capabilities
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
AWS_CMD = os.path.expanduser("~/.local/bin/aws")
MAX_SAMPLE_READS = 50000

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
        """Extract metadata from file path patterns."""
        metadata = {}

        # Extract flowcell ID (pattern: P[A-Z]{2}\d{5} or F[A-Z]{2}\d{5})
        flowcell_match = re.search(r'([PF][A-Z]{2}\d{5})', path)
        if flowcell_match:
            metadata["flowcell_id"] = flowcell_match.group(1)

        # Extract sample name (e.g., HG001, HG002, NA12878)
        sample_match = re.search(r'(HG\d{3,5}|NA\d{5}|GM\d{5})', path, re.IGNORECASE)
        if sample_match:
            metadata["sample"] = sample_match.group(1).upper()

        # Extract run ID (8 hex chars)
        run_match = re.search(r'_([a-f0-9]{8})(?:[_/\.]|$)', path)
        if run_match:
            metadata["run_id"] = run_match.group(1)

        # Extract barcode
        barcode_match = re.search(r'(barcode\d{2})', path, re.IGNORECASE)
        if barcode_match:
            metadata["barcode"] = barcode_match.group(1).lower()

        # Detect model quality
        if '/sup/' in path or '_sup' in path:
            metadata["basecall_model"] = "sup"
        elif '/hac/' in path or '_hac' in path:
            metadata["basecall_model"] = "hac"
        elif '/fast/' in path or '_fast' in path:
            metadata["basecall_model"] = "fast"

        return metadata

    def stream_bam_stats(self, bam_url: str, max_reads: int = MAX_SAMPLE_READS) -> Optional[Dict]:
        """Stream reads from BAM and compute statistics."""
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

            # Calculate statistics
            total_bases = sum(read_lengths)
            sorted_lengths = sorted(read_lengths, reverse=True)

            # N50
            cumsum = 0
            n50 = 0
            for l in sorted_lengths:
                cumsum += l
                if cumsum >= total_bases / 2:
                    n50 = l
                    break

            return {
                "total_reads_sampled": len(read_lengths),
                "total_bases": total_bases,
                "mean_read_length": total_bases / len(read_lengths),
                "n50": n50,
                "max_read_length": max(read_lengths),
                "min_read_length": min(read_lengths),
                "mean_qscore": _mean_qscore(qscores) if qscores else None,
                "median_qscore": sorted(qscores)[len(qscores)//2] if qscores else None,
                "mapped_reads": mapped,
                "unmapped_reads": unmapped,
                "mapping_rate": mapped / (mapped + unmapped) * 100 if (mapped + unmapped) > 0 else None
            }

        except Exception as e:
            print(f"Error streaming BAM: {e}")
            return None


def generate_html_browser(registry: ExperimentRegistry, output_path: Path):
    """Generate interactive HTML browser for registry."""
    experiments = registry.get_experiments()

    # Group by source
    by_source = defaultdict(list)
    for exp in experiments:
        source = exp.get("source", "local")
        by_source[source].append(exp)

    # Calculate statistics
    total_reads = sum(e.get("total_reads", 0) for e in experiments)
    total_bases = sum(e.get("total_bases", 0) for e in experiments)

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
        .header h1 {{ margin: 0 0 10px 0; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .stat-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #1a5f7a;
        }}
        .stat-card .label {{
            color: #666;
            font-size: 0.9em;
        }}
        .search-box {{
            width: 100%;
            padding: 15px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .search-box:focus {{
            border-color: #1a5f7a;
            outline: none;
        }}
        .experiment-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 15px;
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
            margin: 0 0 10px 0;
            color: #333;
            font-size: 1.1em;
            word-break: break-all;
        }}
        .experiment-card .id {{
            font-family: monospace;
            color: #666;
            font-size: 0.85em;
        }}
        .experiment-card .metrics {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #eee;
        }}
        .metric {{
            text-align: center;
        }}
        .metric .value {{
            font-weight: bold;
            color: #1a5f7a;
        }}
        .metric .label {{
            font-size: 0.75em;
            color: #888;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.75em;
            margin-right: 5px;
        }}
        .badge-local {{ background: #e8f5e9; color: #2e7d32; }}
        .badge-public {{ background: #e3f2fd; color: #1565c0; }}
        .badge-analyzed {{ background: #fff3e0; color: #ef6c00; }}
        .quality-high {{ color: #27ae60; }}
        .quality-medium {{ color: #f39c12; }}
        .quality-low {{ color: #e74c3c; }}
        .section {{
            margin-bottom: 30px;
        }}
        .section h2 {{
            color: #333;
            border-bottom: 2px solid #1a5f7a;
            padding-bottom: 10px;
        }}
        .artifacts {{
            margin-top: 10px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
            font-size: 0.85em;
        }}
        .artifact-link {{
            color: #1a5f7a;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>ONT Experiment Registry</h1>
        <p>Interactive browser for {len(experiments)} experiments</p>
        <p>Last updated: {registry.data.get("updated", "Unknown")}</p>
    </div>

    <div class="stats">
        <div class="stat-card">
            <div class="value">{len(experiments)}</div>
            <div class="label">Experiments</div>
        </div>
        <div class="stat-card">
            <div class="value">{total_reads:,}</div>
            <div class="label">Total Reads</div>
        </div>
        <div class="stat-card">
            <div class="value">{total_bases/1e12:.2f} Tb</div>
            <div class="label">Total Bases</div>
        </div>
        <div class="stat-card">
            <div class="value">{len(by_source)}</div>
            <div class="label">Sources</div>
        </div>
    </div>

    <input type="text" class="search-box" id="search" placeholder="Search experiments by name, ID, or metadata..." oninput="filterExperiments()">

    <div class="experiment-grid" id="experiments">
'''

    for exp in experiments[:100]:  # Limit to 100 for performance
        name = exp.get("name", "Unknown")
        exp_id = exp.get("id", "Unknown")
        source = exp.get("source", "local")
        total_reads = exp.get("total_reads", 0)
        total_bases = exp.get("total_bases", 0)
        mean_q = exp.get("mean_quality", 0)
        n50 = exp.get("n50", 0)
        analyses = exp.get("analyses", [])
        artifacts = exp.get("artifacts", [])

        q_class = "quality-high" if mean_q >= 20 else "quality-medium" if mean_q >= 10 else "quality-low"
        source_badge = "badge-public" if source == "ont-open-data" else "badge-local"

        html += f'''
        <div class="experiment-card" data-search="{name.lower()} {exp_id.lower()} {json.dumps(exp).lower()}">
            <h3>{name[:50]}{'...' if len(name) > 50 else ''}</h3>
            <div class="id">{exp_id}</div>
            <div style="margin-top: 10px;">
                <span class="badge {source_badge}">{source}</span>
                {'<span class="badge badge-analyzed">analyzed</span>' if analyses else ''}
            </div>
            <div class="metrics">
                <div class="metric">
                    <div class="value">{total_reads:,}</div>
                    <div class="label">Reads</div>
                </div>
                <div class="metric">
                    <div class="value">{total_bases/1e9:.1f} Gb</div>
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
            {'<div class="artifacts">' + f'{len(artifacts)} artifacts' + '</div>' if artifacts else ''}
        </div>
'''

    html += '''
    </div>

    <script>
        function filterExperiments() {
            const query = document.getElementById('search').value.toLowerCase();
            const cards = document.querySelectorAll('.experiment-card');
            cards.forEach(card => {
                const searchText = card.getAttribute('data-search');
                card.style.display = searchText.includes(query) ? 'block' : 'none';
            });
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
    """Add public experiment to registry with metadata extraction."""
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

    # Extract metadata from paths
    metadata = {"dataset": dataset, "source_key": source_key}
    for file_type, file_list in files.items():
        for f in file_list:
            path_meta = extractor.extract_metadata_from_path(f["path"])
            metadata.update(path_meta)

    # Stream BAM for statistics
    stats = None
    if files["bam_files"] and args.analyze:
        bam_file = files["bam_files"][0]
        bam_url = f"{extractor.S3_BUCKET}/{bam_file['path']}"
        print(f"  Streaming stats from BAM ({bam_file['size']/1e6:.1f} MB)...")
        stats = extractor.stream_bam_stats(bam_url)

    # Build experiment record
    exp_record = {
        "name": experiment,
        "source": "ont-open-data",
        "status": "registered",
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
        # Update existing
        registry.update_experiment(existing["id"], exp_record)
        print(f"  Updated: {existing['id']}")
    else:
        # Add new
        exp_id = registry.add_experiment(exp_record)
        print(f"  Registered: {exp_id}")

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
