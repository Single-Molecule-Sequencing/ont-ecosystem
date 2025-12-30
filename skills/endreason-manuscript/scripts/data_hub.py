#!/usr/bin/env python3
"""
Data Hub - Integration layer for end-reason manuscript.

Aggregates data from:
- Internal HPC experiments (via registry)
- Public ONT datasets (via ont_public_data.py)
- Physical size distributions (TapeStation/Bioanalyzer)

Part of: https://github.com/Single-Molecule-Sequencing/ont-ecosystem
"""

import os
import sys
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

# Add bin directory to path for imports
BIN_DIR = Path(__file__).parent.parent.parent.parent / "bin"
sys.path.insert(0, str(BIN_DIR))

# Optional imports
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# =============================================================================
# Configuration
# =============================================================================

REGISTRY_DIR = Path(os.environ.get("ONT_REGISTRY_DIR", Path.home() / ".ont-registry"))
PUBLIC_DATA_DIR = Path(os.environ.get("ONT_PUBLIC_DATA_DIR", Path.home() / "ont_public_analysis"))

# End-reason categories with expected ranges
END_REASON_EXPECTED = {
    "signal_positive": (75, 95),
    "unblock_mux_change": (0, 20),
    "data_service_unblock_mux_change": (0, 15),
    "mux_change": (0, 10),
    "signal_negative": (0, 5),
    "unknown": (0, 5),
}

# Quality grade thresholds
QUALITY_GRADES = {
    "A": {"signal_positive_min": 95, "unblock_max": 2},
    "B": {"signal_positive_min": 85, "unblock_max": 5},
    "C": {"signal_positive_min": 75, "unblock_max": 10},
    "D": {"signal_positive_min": 0, "unblock_max": 100},
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class EndReasonData:
    """End-reason data for a single experiment."""
    experiment_id: str
    source: str  # "internal", "public", "manual"
    total_reads: int = 0
    signal_positive: int = 0
    unblock_mux_change: int = 0
    data_service_unblock_mux_change: int = 0
    mux_change: int = 0
    signal_negative: int = 0
    unknown: int = 0
    other: int = 0

    # Computed properties
    @property
    def signal_positive_pct(self) -> float:
        return (self.signal_positive / self.total_reads * 100) if self.total_reads > 0 else 0

    @property
    def unblock_pct(self) -> float:
        return (self.unblock_mux_change / self.total_reads * 100) if self.total_reads > 0 else 0

    @property
    def data_service_pct(self) -> float:
        return (self.data_service_unblock_mux_change / self.total_reads * 100) if self.total_reads > 0 else 0

    @property
    def rejection_rate(self) -> float:
        """Combined rejection rate (unblock + data_service)."""
        return self.unblock_pct + self.data_service_pct

    @property
    def quality_grade(self) -> str:
        """Quality grade A/B/C/D based on thresholds."""
        sp = self.signal_positive_pct
        unblock = self.unblock_pct
        for grade, thresholds in QUALITY_GRADES.items():
            if sp >= thresholds["signal_positive_min"] and unblock <= thresholds["unblock_max"]:
                return grade
        return "D"

    @property
    def is_adaptive(self) -> bool:
        """Detect if adaptive sampling was used."""
        # If significant unblock or data_service, likely adaptive
        return self.rejection_rate > 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "source": self.source,
            "total_reads": self.total_reads,
            "signal_positive": self.signal_positive,
            "signal_positive_pct": round(self.signal_positive_pct, 2),
            "unblock_mux_change": self.unblock_mux_change,
            "unblock_pct": round(self.unblock_pct, 2),
            "data_service_unblock_mux_change": self.data_service_unblock_mux_change,
            "data_service_pct": round(self.data_service_pct, 2),
            "mux_change": self.mux_change,
            "signal_negative": self.signal_negative,
            "unknown": self.unknown,
            "other": self.other,
            "rejection_rate": round(self.rejection_rate, 2),
            "quality_grade": self.quality_grade,
            "is_adaptive": self.is_adaptive,
        }


@dataclass
class ExperimentMetadata:
    """Metadata for an experiment."""
    experiment_id: str
    name: str
    source: str  # "internal", "public"
    location: Optional[str] = None
    platform: Optional[str] = None
    flowcell: Optional[str] = None
    kit: Optional[str] = None
    sample_id: Optional[str] = None
    is_adaptive: bool = False
    chemistry: Optional[str] = None  # R10.4.1, R9.4.1, etc.
    tags: List[str] = field(default_factory=list)


@dataclass
class PhysicalSizeData:
    """Physical size distribution from TapeStation/Bioanalyzer."""
    sample_id: str
    source: str  # "tapestation", "bioanalyzer"
    file_path: Optional[str] = None
    mean: float = 0.0
    median: float = 0.0
    mode: float = 0.0
    percentile_10: float = 0.0
    percentile_90: float = 0.0
    peaks: List[Dict[str, float]] = field(default_factory=list)
    raw_sizes: List[float] = field(default_factory=list)
    raw_concentrations: List[float] = field(default_factory=list)
    experiment_id: Optional[str] = None  # Linked experiment


@dataclass
class MergedExperiment:
    """Combined data for an experiment."""
    metadata: ExperimentMetadata
    end_reasons: Optional[EndReasonData] = None
    physical_size: Optional[PhysicalSizeData] = None
    statistics: Optional[Dict[str, Any]] = None  # n50, mean_length, mean_qscore, etc.


# =============================================================================
# Data Loading Functions
# =============================================================================

def load_internal_experiments(
    registry_dir: Optional[Path] = None,
    filter_tags: Optional[List[str]] = None,
    filter_adaptive: Optional[bool] = None,
) -> List[MergedExperiment]:
    """
    Load experiments from the internal registry.

    Args:
        registry_dir: Path to registry directory (default: ~/.ont-registry/)
        filter_tags: Only include experiments with these tags
        filter_adaptive: Filter by adaptive sampling status

    Returns:
        List of MergedExperiment objects
    """
    registry_dir = registry_dir or REGISTRY_DIR
    experiments_file = registry_dir / "experiments.yaml"

    if not experiments_file.exists():
        print(f"Warning: Registry not found at {experiments_file}", file=sys.stderr)
        return []

    if not HAS_YAML:
        print("Warning: PyYAML not installed, cannot load registry", file=sys.stderr)
        return []

    with open(experiments_file) as f:
        data = yaml.safe_load(f) or {}

    experiments = []
    for exp_data in data.get("experiments", []):
        exp_id = exp_data.get("id", "")

        # Apply tag filter
        tags = exp_data.get("tags", [])
        if filter_tags and not any(t in tags for t in filter_tags):
            continue

        # Create metadata
        metadata = ExperimentMetadata(
            experiment_id=exp_id,
            name=exp_data.get("name", exp_id),
            source="internal",
            location=exp_data.get("location"),
            platform=exp_data.get("platform"),
            flowcell=exp_data.get("flowcell"),
            kit=exp_data.get("kit"),
            sample_id=exp_data.get("sample_id"),
            tags=tags,
        )

        # Load end-reason data from events
        end_reasons = None
        statistics = None
        events = exp_data.get("events", [])

        for event in reversed(events):  # Most recent first
            if event.get("analysis") == "end_reasons":
                results = event.get("results", {})
                end_reasons = EndReasonData(
                    experiment_id=exp_id,
                    source="internal",
                    total_reads=results.get("total_reads", 0),
                    signal_positive=results.get("signal_positive", 0),
                    unblock_mux_change=results.get("unblock_mux_change", 0),
                    data_service_unblock_mux_change=results.get("data_service_unblock_mux_change", 0),
                    mux_change=results.get("mux_change", 0),
                    signal_negative=results.get("signal_negative", 0),
                    unknown=results.get("unknown", 0),
                )

                # Also extract statistics if present
                statistics = {
                    "n50": results.get("n50"),
                    "mean_length": results.get("mean_length"),
                    "mean_qscore": results.get("mean_qscore"),
                }
                break

        # Apply adaptive filter
        if filter_adaptive is not None:
            is_adaptive = end_reasons.is_adaptive if end_reasons else False
            if is_adaptive != filter_adaptive:
                continue

        experiments.append(MergedExperiment(
            metadata=metadata,
            end_reasons=end_reasons,
            statistics=statistics,
        ))

    return experiments


def load_public_experiments(
    data_dir: Optional[Path] = None,
    datasets: Optional[List[str]] = None,
) -> List[MergedExperiment]:
    """
    Load experiments from public ONT data analysis outputs.

    Args:
        data_dir: Directory containing ont_public_data.py outputs
        datasets: Only include these datasets (e.g., ["giab_2025.01"])

    Returns:
        List of MergedExperiment objects
    """
    data_dir = data_dir or PUBLIC_DATA_DIR

    if not data_dir.exists():
        print(f"Warning: Public data directory not found at {data_dir}", file=sys.stderr)
        return []

    experiments = []

    # Look for summary JSON files
    summaries_dir = data_dir / "summaries"
    if summaries_dir.exists():
        for summary_file in summaries_dir.glob("*_summary.json"):
            try:
                with open(summary_file) as f:
                    data = json.load(f)

                exp_name = summary_file.stem.replace("_summary", "")
                dataset = data.get("dataset", "")

                # Apply dataset filter
                if datasets and dataset not in datasets:
                    continue

                # Extract end-reason data
                end_reason_counts = data.get("end_reasons", {})
                total_reads = data.get("total_reads", 0)

                end_reasons = EndReasonData(
                    experiment_id=exp_name,
                    source="public",
                    total_reads=total_reads,
                    signal_positive=end_reason_counts.get("signal_positive", 0),
                    unblock_mux_change=end_reason_counts.get("unblock_mux_change", 0),
                    data_service_unblock_mux_change=end_reason_counts.get("data_service_unblock_mux_change", 0),
                    mux_change=end_reason_counts.get("mux_change", 0),
                    signal_negative=end_reason_counts.get("signal_negative", 0),
                    unknown=end_reason_counts.get("unknown", 0),
                )

                metadata = ExperimentMetadata(
                    experiment_id=exp_name,
                    name=data.get("experiment_name", exp_name),
                    source="public",
                    is_adaptive=end_reasons.is_adaptive,
                    tags=[dataset, "public"],
                )

                statistics = {
                    "n50": data.get("n50"),
                    "mean_length": data.get("mean_length"),
                    "mean_qscore": data.get("mean_qscore"),
                    "median_qscore": data.get("median_qscore"),
                }

                experiments.append(MergedExperiment(
                    metadata=metadata,
                    end_reasons=end_reasons,
                    statistics=statistics,
                ))

            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Failed to parse {summary_file}: {e}", file=sys.stderr)
                continue

    return experiments


def load_physical_sizes(
    physical_dir: Path,
) -> Dict[str, PhysicalSizeData]:
    """
    Load physical size distributions from TapeStation/Bioanalyzer files.

    Args:
        physical_dir: Directory containing physical size data

    Returns:
        Dict mapping sample_id to PhysicalSizeData
    """
    # Placeholder - implement when physical data available
    if not physical_dir.exists():
        return {}

    # Look for size_distributions.yaml if it exists
    size_file = physical_dir / "size_distributions.yaml"
    if size_file.exists() and HAS_YAML:
        with open(size_file) as f:
            data = yaml.safe_load(f) or {}

        result = {}
        for sample_id, sample_data in data.get("samples", {}).items():
            result[sample_id] = PhysicalSizeData(
                sample_id=sample_id,
                source=sample_data.get("source", "unknown"),
                file_path=sample_data.get("file"),
                mean=sample_data.get("distribution", {}).get("mean", 0),
                median=sample_data.get("distribution", {}).get("median", 0),
                mode=sample_data.get("distribution", {}).get("mode", 0),
                percentile_10=sample_data.get("distribution", {}).get("percentile_10", 0),
                percentile_90=sample_data.get("distribution", {}).get("percentile_90", 0),
                peaks=sample_data.get("peaks", []),
                experiment_id=sample_data.get("experiment_id"),
            )
        return result

    return {}


# =============================================================================
# Data Merging and Comparison
# =============================================================================

def merge_data_sources(
    internal: List[MergedExperiment],
    public: List[MergedExperiment],
    physical: Optional[Dict[str, PhysicalSizeData]] = None,
) -> List[MergedExperiment]:
    """
    Merge data from all sources into unified list.

    Args:
        internal: Internal experiments
        public: Public experiments
        physical: Physical size data keyed by sample_id

    Returns:
        Combined list with physical data linked where possible
    """
    all_experiments = []

    # Add internal experiments
    for exp in internal:
        if physical and exp.metadata.sample_id:
            exp.physical_size = physical.get(exp.metadata.sample_id)
        all_experiments.append(exp)

    # Add public experiments
    for exp in public:
        if physical and exp.metadata.sample_id:
            exp.physical_size = physical.get(exp.metadata.sample_id)
        all_experiments.append(exp)

    return all_experiments


def compute_comparison_matrix(
    experiments: List[MergedExperiment],
) -> Dict[str, Any]:
    """
    Compute comparison matrix across all experiments.

    Returns dict with:
    - summary: Overall statistics
    - by_source: Breakdown by source (internal/public)
    - by_adaptive: Breakdown by adaptive status
    - experiments: List of per-experiment metrics
    """
    if not experiments:
        return {"summary": {}, "by_source": {}, "by_adaptive": {}, "experiments": []}

    # Collect metrics
    all_signal_positive = []
    all_unblock = []
    all_rejection = []

    by_source = {"internal": [], "public": []}
    by_adaptive = {"adaptive": [], "non_adaptive": []}
    exp_data = []

    for exp in experiments:
        if not exp.end_reasons:
            continue

        er = exp.end_reasons

        all_signal_positive.append(er.signal_positive_pct)
        all_unblock.append(er.unblock_pct)
        all_rejection.append(er.rejection_rate)

        # Group by source
        source = exp.metadata.source
        if source in by_source:
            by_source[source].append(er.signal_positive_pct)

        # Group by adaptive
        if er.is_adaptive:
            by_adaptive["adaptive"].append(er.signal_positive_pct)
        else:
            by_adaptive["non_adaptive"].append(er.signal_positive_pct)

        # Per-experiment data
        exp_data.append({
            "experiment_id": exp.metadata.experiment_id,
            "source": source,
            "is_adaptive": er.is_adaptive,
            "signal_positive_pct": round(er.signal_positive_pct, 2),
            "unblock_pct": round(er.unblock_pct, 2),
            "rejection_rate": round(er.rejection_rate, 2),
            "quality_grade": er.quality_grade,
            "total_reads": er.total_reads,
        })

    def _mean(lst):
        return sum(lst) / len(lst) if lst else 0

    return {
        "summary": {
            "n_experiments": len(experiments),
            "n_with_end_reasons": len(exp_data),
            "mean_signal_positive_pct": round(_mean(all_signal_positive), 2),
            "mean_unblock_pct": round(_mean(all_unblock), 2),
            "mean_rejection_rate": round(_mean(all_rejection), 2),
        },
        "by_source": {
            source: {
                "n": len(values),
                "mean_signal_positive_pct": round(_mean(values), 2),
            }
            for source, values in by_source.items()
            if values
        },
        "by_adaptive": {
            status: {
                "n": len(values),
                "mean_signal_positive_pct": round(_mean(values), 2),
            }
            for status, values in by_adaptive.items()
            if values
        },
        "experiments": exp_data,
    }


def classify_adaptive_status(
    experiments: List[MergedExperiment],
) -> Dict[str, List[MergedExperiment]]:
    """
    Classify experiments by adaptive sampling status.

    Returns dict with "adaptive" and "non_adaptive" lists.
    """
    result = {"adaptive": [], "non_adaptive": []}

    for exp in experiments:
        if exp.end_reasons and exp.end_reasons.is_adaptive:
            result["adaptive"].append(exp)
        else:
            result["non_adaptive"].append(exp)

    return result


# =============================================================================
# Data Export
# =============================================================================

def export_merged_data(
    experiments: List[MergedExperiment],
    output_path: Path,
    format: str = "json",
) -> Path:
    """
    Export merged experiment data.

    Args:
        experiments: List of MergedExperiment objects
        output_path: Output file path
        format: "json" or "yaml"

    Returns:
        Path to exported file
    """
    data = {
        "generated_at": datetime.now().isoformat(),
        "n_experiments": len(experiments),
        "experiments": [],
    }

    for exp in experiments:
        exp_data = {
            "metadata": asdict(exp.metadata),
            "end_reasons": exp.end_reasons.to_dict() if exp.end_reasons else None,
            "statistics": exp.statistics,
            "physical_size": asdict(exp.physical_size) if exp.physical_size else None,
        }
        data["experiments"].append(exp_data)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if format == "yaml" and HAS_YAML:
        with open(output_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    else:
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

    return output_path


# =============================================================================
# Main (for testing)
# =============================================================================

def main():
    """Test data hub functions."""
    print("Loading internal experiments...")
    internal = load_internal_experiments()
    print(f"  Found {len(internal)} internal experiments")

    print("\nLoading public experiments...")
    public = load_public_experiments()
    print(f"  Found {len(public)} public experiments")

    print("\nMerging data sources...")
    all_experiments = merge_data_sources(internal, public)
    print(f"  Total: {len(all_experiments)} experiments")

    print("\nComputing comparison matrix...")
    matrix = compute_comparison_matrix(all_experiments)
    print(json.dumps(matrix["summary"], indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
