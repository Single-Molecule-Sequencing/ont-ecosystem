#!/usr/bin/env python3
"""
ONT Experiment Metadata Schema

Rigorous definitions for all metadata fields used in the experiment registry.
This schema ensures consistency and clarity across all experiments.

Version: 2.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# =============================================================================
# ENUMERATIONS
# =============================================================================

class DataSource(Enum):
    """Origin of the experiment data."""
    LOCAL = "local"                    # Data stored on local filesystem
    ONT_OPEN_DATA = "ont-open-data"    # ONT Open Data S3 bucket
    SRA = "sra"                        # NCBI Sequence Read Archive
    ENA = "ena"                        # European Nucleotide Archive


class ExperimentStatus(Enum):
    """Current analysis status of the experiment."""
    DISCOVERED = "discovered"      # Found but not yet analyzed
    REGISTERED = "registered"      # Added to registry with basic info
    ANALYZING = "analyzing"        # Analysis in progress
    ANALYZED = "analyzed"          # QC analysis complete
    ALIGNED = "aligned"            # Alignment complete
    COMPLETE = "complete"          # All analyses complete
    FAILED = "failed"              # Analysis failed


class DeviceType(Enum):
    """Oxford Nanopore sequencing device types."""
    PROMETHION = "PromethION"
    PROMETHION_2 = "PromethION 2"
    P2_SOLO = "P2 Solo"
    MINION = "MinION"
    MINION_MK1B = "MinION Mk1B"
    MINION_MK1C = "MinION Mk1C"
    GRIDION = "GridION"
    FLONGLE = "Flongle"
    UNKNOWN = "Unknown"


class Chemistry(Enum):
    """Flowcell chemistry versions."""
    R10_4_1 = "R10.4.1"
    R10_4 = "R10.4"
    R10_3 = "R10.3"
    R9_4_1 = "R9.4.1"
    R9_4 = "R9.4"
    E8_2 = "E8.2"            # Early access
    UNKNOWN = "Unknown"


class BasecallModel(Enum):
    """Basecalling model accuracy levels."""
    FAST = "fast"            # ~Q8-10, fastest
    HAC = "hac"              # ~Q12-15, high accuracy
    SUP = "sup"              # ~Q18-22, super high accuracy
    UNKNOWN = "unknown"


class Basecaller(Enum):
    """Basecaller software."""
    DORADO = "dorado"
    GUPPY = "guppy"
    BONITO = "bonito"
    UNKNOWN = "unknown"


class ArtifactType(Enum):
    """Types of analysis artifacts."""
    SUMMARY_JSON = "summary_json"     # JSON summary file
    SUMMARY_CSV = "summary_csv"       # CSV summary file
    PLOT_PNG = "plot_png"             # PNG plot
    PLOT_PDF = "plot_pdf"             # PDF plot
    REPORT_HTML = "report_html"       # HTML report
    REPORT_PDF = "report_pdf"         # PDF report
    BAM = "bam"                       # BAM alignment file
    FASTQ = "fastq"                   # FASTQ file
    POD5 = "pod5"                     # POD5 signal file
    VCF = "vcf"                       # Variant calls


# =============================================================================
# METADATA FIELD DEFINITIONS
# =============================================================================

METADATA_SCHEMA = {
    # -------------------------------------------------------------------------
    # IDENTIFICATION
    # -------------------------------------------------------------------------
    "id": {
        "type": "string",
        "required": True,
        "description": "Unique identifier for this experiment in the registry",
        "format": "exp-[8 hex chars]",
        "example": "exp-a1b2c3d4"
    },
    "name": {
        "type": "string",
        "required": True,
        "description": "Human-readable name for the experiment, typically derived from source filename or path",
        "example": "HG002_PAW12345_sup"
    },

    # -------------------------------------------------------------------------
    # DATA SOURCE & ACCESS
    # -------------------------------------------------------------------------
    "source": {
        "type": "enum",
        "enum": DataSource,
        "required": True,
        "description": "Origin of the experiment data (local, ont-open-data, sra, etc.)"
    },
    "status": {
        "type": "enum",
        "enum": ExperimentStatus,
        "required": True,
        "description": "Current analysis status of the experiment"
    },
    "urls": {
        "type": "object",
        "description": "URLs for accessing the experiment data online",
        "properties": {
            "s3": {
                "type": "string",
                "description": "S3 URI for direct access (requires AWS CLI)",
                "example": "s3://ont-open-data/giab_2023.05/analysis/..."
            },
            "https": {
                "type": "string",
                "description": "HTTPS URL for browser access or streaming",
                "example": "https://ont-open-data.s3.amazonaws.com/giab_2023.05/..."
            },
            "landing_page": {
                "type": "string",
                "description": "URL to dataset landing page or documentation",
                "example": "https://labs.epi2me.io/giab-2023.05/"
            }
        }
    },
    "local_path": {
        "type": "string",
        "description": "Local filesystem path to experiment data (if source=local)",
        "example": "/data/experiments/HG002_run1/"
    },

    # -------------------------------------------------------------------------
    # READ COUNTS - CRITICAL DISTINCTION
    # -------------------------------------------------------------------------
    "read_counts": {
        "type": "object",
        "description": "Read count metrics with clear provenance",
        "properties": {
            "sampled": {
                "type": "integer",
                "description": "Number of reads actually processed during streaming analysis. This is the sample size used to compute statistics like mean Q-score, N50, etc.",
                "provenance": "Direct count from streaming analysis",
                "example": 50000
            },
            "estimated_total": {
                "type": "integer",
                "description": "Estimated total reads in the experiment, extrapolated from file size and average read length from sample. Formula: (file_size_bytes / avg_bytes_per_read) * (sampled_reads / sampled_bytes)",
                "provenance": "Computed estimate",
                "example": 5000000
            },
            "counted_total": {
                "type": "integer",
                "description": "Actual total read count from full file enumeration (e.g., samtools view -c). Only populated if full count was performed.",
                "provenance": "Direct count from full file",
                "example": 4987234
            },
            "pass_reads": {
                "type": "integer",
                "description": "Reads passing quality filter (from sample or full count)",
                "provenance": "Depends on count_source"
            },
            "fail_reads": {
                "type": "integer",
                "description": "Reads failing quality filter (from sample or full count)",
                "provenance": "Depends on count_source"
            },
            "count_source": {
                "type": "string",
                "enum": ["sampled", "estimated", "counted"],
                "description": "Which count method was used for primary read_count display"
            }
        }
    },

    # -------------------------------------------------------------------------
    # BASE COUNTS & YIELD
    # -------------------------------------------------------------------------
    "base_counts": {
        "type": "object",
        "description": "Base count metrics with clear provenance",
        "properties": {
            "sampled_bases": {
                "type": "integer",
                "description": "Total bases in the sampled reads",
                "example": 747200000
            },
            "estimated_total_bases": {
                "type": "integer",
                "description": "Estimated total bases, extrapolated from sample",
                "example": 74720000000
            },
            "counted_total_bases": {
                "type": "integer",
                "description": "Actual total bases from full enumeration",
                "example": 74582347291
            }
        }
    },

    # -------------------------------------------------------------------------
    # QUALITY METRICS
    # -------------------------------------------------------------------------
    "quality_metrics": {
        "type": "object",
        "description": "Quality scores computed via probability space (not linear average)",
        "properties": {
            "mean_qscore": {
                "type": "float",
                "description": "Mean Q-score computed via probability space: -10*log10(mean(10^(-Q/10))). NEVER use arithmetic mean of Q-scores.",
                "range": [0, 60],
                "unit": "Phred",
                "example": 18.5
            },
            "median_qscore": {
                "type": "float",
                "description": "Median Q-score from sampled reads",
                "example": 19.2
            },
            "q10_percent": {
                "type": "float",
                "description": "Percentage of reads with Q >= 10",
                "example": 95.2
            },
            "q20_percent": {
                "type": "float",
                "description": "Percentage of reads with Q >= 20",
                "example": 72.8
            },
            "q30_percent": {
                "type": "float",
                "description": "Percentage of reads with Q >= 30",
                "example": 15.3
            },
            "computed_from_n_reads": {
                "type": "integer",
                "description": "Number of reads used to compute these statistics",
                "example": 50000
            }
        }
    },

    # -------------------------------------------------------------------------
    # READ LENGTH METRICS
    # -------------------------------------------------------------------------
    "length_metrics": {
        "type": "object",
        "description": "Read length distribution statistics",
        "properties": {
            "n50": {
                "type": "integer",
                "description": "N50 read length - 50% of total bases are in reads >= this length",
                "unit": "bp",
                "example": 28500
            },
            "n90": {
                "type": "integer",
                "description": "N90 read length - 90% of total bases are in reads >= this length",
                "unit": "bp"
            },
            "mean_length": {
                "type": "float",
                "description": "Mean read length",
                "unit": "bp",
                "example": 14943.5
            },
            "median_length": {
                "type": "integer",
                "description": "Median read length",
                "unit": "bp"
            },
            "max_length": {
                "type": "integer",
                "description": "Maximum read length observed",
                "unit": "bp",
                "example": 245678
            },
            "min_length": {
                "type": "integer",
                "description": "Minimum read length observed",
                "unit": "bp",
                "example": 200
            }
        }
    },

    # -------------------------------------------------------------------------
    # ALIGNMENT METRICS
    # -------------------------------------------------------------------------
    "alignment_metrics": {
        "type": "object",
        "description": "Alignment statistics (if aligned BAM)",
        "properties": {
            "mapped_reads": {
                "type": "integer",
                "description": "Number of reads with primary alignment"
            },
            "unmapped_reads": {
                "type": "integer",
                "description": "Number of unmapped reads"
            },
            "mapping_rate": {
                "type": "float",
                "description": "Percentage of reads that mapped",
                "unit": "percent",
                "example": 99.2
            },
            "mean_coverage": {
                "type": "float",
                "description": "Mean genome coverage (if reference provided)"
            },
            "reference_genome": {
                "type": "string",
                "description": "Reference genome used for alignment",
                "example": "GRCh38"
            }
        }
    },

    # -------------------------------------------------------------------------
    # SAMPLE & EXPERIMENT METADATA
    # -------------------------------------------------------------------------
    "sample": {
        "type": "object",
        "description": "Biological sample information",
        "properties": {
            "sample_id": {
                "type": "string",
                "description": "Sample identifier (e.g., GIAB ID, cell line)",
                "example": "HG002"
            },
            "sample_type": {
                "type": "string",
                "description": "Type of sample (cell_line, tissue, blood, etc.)"
            },
            "organism": {
                "type": "string",
                "description": "Species/organism",
                "example": "Homo sapiens"
            },
            "source_repository": {
                "type": "string",
                "description": "Repository where sample is available (GIAB, Coriell, ATCC)",
                "example": "GIAB"
            }
        }
    },

    # -------------------------------------------------------------------------
    # SEQUENCING METADATA
    # -------------------------------------------------------------------------
    "sequencing": {
        "type": "object",
        "description": "Sequencing run parameters",
        "properties": {
            "device_type": {
                "type": "enum",
                "enum": DeviceType,
                "description": "Sequencing device model"
            },
            "device_id": {
                "type": "string",
                "description": "Device serial number",
                "example": "MD-101527"
            },
            "flowcell_id": {
                "type": "string",
                "description": "Flowcell identifier",
                "example": "PAW12345"
            },
            "flowcell_type": {
                "type": "string",
                "description": "Flowcell product type",
                "example": "FLO-PRO114M"
            },
            "chemistry": {
                "type": "enum",
                "enum": Chemistry,
                "description": "Flowcell chemistry version"
            },
            "kit": {
                "type": "string",
                "description": "Library preparation kit",
                "example": "SQK-LSK114"
            },
            "run_id": {
                "type": "string",
                "description": "Unique run identifier (typically 8 hex chars)",
                "example": "a1b2c3d4"
            },
            "run_date": {
                "type": "string",
                "description": "Date of sequencing run (ISO 8601)",
                "format": "date"
            },
            "barcode": {
                "type": "string",
                "description": "Barcode/index if multiplexed",
                "example": "barcode01"
            }
        }
    },

    # -------------------------------------------------------------------------
    # BASECALLING METADATA
    # -------------------------------------------------------------------------
    "basecalling": {
        "type": "object",
        "description": "Basecalling configuration",
        "properties": {
            "basecaller": {
                "type": "enum",
                "enum": Basecaller,
                "description": "Basecalling software used"
            },
            "basecaller_version": {
                "type": "string",
                "description": "Version of basecaller",
                "example": "0.5.3"
            },
            "model": {
                "type": "string",
                "description": "Full model name",
                "example": "dna_r10.4.1_e8.2_400bps_sup@v4.3.0"
            },
            "model_accuracy": {
                "type": "enum",
                "enum": BasecallModel,
                "description": "Model accuracy level (fast/hac/sup)"
            },
            "modifications_called": {
                "type": "list",
                "description": "Base modifications called",
                "items": {"type": "string"},
                "example": ["5mCG", "5hmCG"]
            },
            "duplex": {
                "type": "boolean",
                "description": "Whether duplex basecalling was performed"
            }
        }
    },

    # -------------------------------------------------------------------------
    # ADAPTIVE SAMPLING
    # -------------------------------------------------------------------------
    "adaptive_sampling": {
        "type": "object",
        "description": "Adaptive sampling / ReadUntil configuration",
        "properties": {
            "enabled": {
                "type": "boolean",
                "description": "Whether adaptive sampling was used"
            },
            "software": {
                "type": "string",
                "description": "Software used (ReadFish, BOSS, etc.)"
            },
            "target_type": {
                "type": "string",
                "description": "Enrichment or depletion strategy"
            },
            "target_regions": {
                "type": "string",
                "description": "BED file or description of target regions"
            }
        }
    },

    # -------------------------------------------------------------------------
    # DATASET METADATA
    # -------------------------------------------------------------------------
    "dataset": {
        "type": "object",
        "description": "Dataset-level metadata for public data",
        "properties": {
            "dataset_name": {
                "type": "string",
                "description": "Name of the public dataset",
                "example": "giab_2023.05"
            },
            "dataset_date": {
                "type": "string",
                "description": "Dataset release date",
                "format": "YYYY-MM"
            },
            "dataset_version": {
                "type": "string",
                "description": "Version of the dataset"
            },
            "replicate": {
                "type": "integer",
                "description": "Replicate number within dataset"
            }
        }
    },

    # -------------------------------------------------------------------------
    # FILE INFORMATION
    # -------------------------------------------------------------------------
    "files": {
        "type": "object",
        "description": "Source file information",
        "properties": {
            "bam_files": {
                "type": "integer",
                "description": "Number of BAM files"
            },
            "pod5_files": {
                "type": "integer",
                "description": "Number of POD5 files"
            },
            "fastq_files": {
                "type": "integer",
                "description": "Number of FASTQ files"
            },
            "total_size_bytes": {
                "type": "integer",
                "description": "Total size of all files in bytes"
            },
            "total_size_gb": {
                "type": "float",
                "description": "Total size in gigabytes"
            },
            "primary_file": {
                "type": "string",
                "description": "Path/URL to primary data file used for analysis"
            }
        }
    },

    # -------------------------------------------------------------------------
    # PROVENANCE & TIMESTAMPS
    # -------------------------------------------------------------------------
    "provenance": {
        "type": "object",
        "description": "Data provenance and tracking",
        "properties": {
            "registered": {
                "type": "string",
                "description": "When experiment was added to registry",
                "format": "datetime"
            },
            "updated": {
                "type": "string",
                "description": "When experiment was last updated",
                "format": "datetime"
            },
            "analyzed": {
                "type": "string",
                "description": "When streaming analysis was performed",
                "format": "datetime"
            },
            "analysis_tool": {
                "type": "string",
                "description": "Tool used for analysis",
                "example": "registry-browser v1.1.0"
            },
            "analysis_host": {
                "type": "string",
                "description": "Hostname where analysis was run"
            }
        }
    }
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_field_definition(field_path: str) -> Optional[Dict]:
    """Get definition for a metadata field by dot-notation path."""
    parts = field_path.split('.')
    current = METADATA_SCHEMA

    for part in parts:
        if part in current:
            current = current[part]
        elif 'properties' in current and part in current['properties']:
            current = current['properties'][part]
        else:
            return None

    return current


def validate_experiment(experiment: Dict) -> List[str]:
    """Validate an experiment against the schema. Returns list of issues."""
    issues = []

    # Check required fields
    if not experiment.get('id'):
        issues.append("Missing required field: id")
    if not experiment.get('name'):
        issues.append("Missing required field: name")
    if not experiment.get('source'):
        issues.append("Missing required field: source")

    # Validate source enum
    source = experiment.get('source')
    if source and source not in [e.value for e in DataSource]:
        issues.append(f"Invalid source value: {source}")

    return issues


def format_read_count_description(experiment: Dict) -> str:
    """Generate human-readable description of read count with provenance."""
    rc = experiment.get('read_counts', {})

    if rc.get('counted_total'):
        return f"{rc['counted_total']:,} reads (counted from full file)"
    elif rc.get('estimated_total'):
        sampled = rc.get('sampled', 0)
        return f"~{rc['estimated_total']:,} reads (estimated from {sampled:,} sampled)"
    elif rc.get('sampled'):
        return f"{rc['sampled']:,} reads (sampled for analysis)"
    else:
        # Legacy format
        total = experiment.get('total_reads', 0)
        return f"{total:,} reads (legacy format - provenance unknown)"
