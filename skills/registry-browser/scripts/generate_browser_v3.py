#!/usr/bin/env python3
"""
Generate Enhanced Registry Browser v3.0

Features:
- Validation status indicators (green/yellow/red)
- Data completeness scores
- Re-analysis links for public data
- 42basepairs.com browser integration
- Audit log viewer
- Export functionality
"""

import json
import os
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import yaml

# Paths
REGISTRY_PATH = Path.home() / ".ont-registry" / "experiments.yaml"
AUDIT_LOG_PATH = Path.home() / ".ont-registry" / "audit_log.yaml"
OUTPUT_DIR = Path.home() / "ont_public_analysis"

# URL constants
BROWSER_BASE = "https://42basepairs.com/browse/s3/ont-open-data"


def load_registry():
    """Load the experiment registry."""
    with open(REGISTRY_PATH) as f:
        return yaml.safe_load(f) or {"experiments": []}


def load_audit_log():
    """Load audit log."""
    if not AUDIT_LOG_PATH.exists():
        return {"entries": []}
    with open(AUDIT_LOG_PATH) as f:
        return yaml.safe_load(f) or {"entries": []}


def calculate_completeness(exp: dict) -> dict:
    """Calculate data completeness score for an experiment."""
    metadata = exp.get("metadata", {})

    # Define required/optional fields with weights
    required_fields = {
        "source": 10,
        "name": 10,
    }

    important_fields = {
        "sample": 15,
        "device_type": 10,
        "chemistry": 10,
        "basecall_model": 10,
        "flowcell_id": 5,
    }

    metric_fields = {
        "read_counts.sampled": 10,
        "quality_metrics.mean_qscore": 10,
        "length_metrics.n50": 10,
    }

    score = 0
    max_score = 0
    missing = []

    # Check required
    for field, weight in required_fields.items():
        max_score += weight
        if exp.get(field):
            score += weight
        else:
            missing.append(field)

    # Check important metadata
    for field, weight in important_fields.items():
        max_score += weight
        if metadata.get(field) or exp.get(field):
            score += weight
        else:
            missing.append(field)

    # Check metrics
    for field, weight in metric_fields.items():
        max_score += weight
        parts = field.split(".")
        val = exp
        for part in parts:
            val = val.get(part, {}) if isinstance(val, dict) else None
        if val:
            score += weight
        else:
            missing.append(field)

    pct = round(score / max_score * 100) if max_score > 0 else 0

    return {
        "score": score,
        "max_score": max_score,
        "percentage": pct,
        "missing": missing,
        "status": "good" if pct >= 80 else "warning" if pct >= 50 else "poor"
    }


def generate_html(experiments: list, audit_log: dict) -> str:
    """Generate comprehensive HTML browser."""

    # Calculate statistics
    total = len(experiments)
    by_source = defaultdict(int)
    by_status = defaultdict(int)
    completeness_stats = {"good": 0, "warning": 0, "poor": 0}

    experiments_json = []

    for exp in experiments:
        source = exp.get("source", "unknown")
        by_source[source] += 1

        comp = calculate_completeness(exp)
        completeness_stats[comp["status"]] += 1

        metadata = exp.get("metadata", {})
        rc = exp.get("read_counts", {})
        qm = exp.get("quality_metrics", {})
        lm = exp.get("length_metrics", {})
        am = exp.get("alignment_metrics", {})
        urls = exp.get("urls", {})

        # Determine read count display
        if rc.get("counted_total"):
            read_display = f"{rc['counted_total']:,}"
            read_tooltip = "Exact count from full file"
            read_class = "count-exact"
        elif rc.get("estimated_total"):
            read_display = f"~{rc['estimated_total']:,}"
            read_tooltip = f"Estimated from {rc.get('sampled', 0):,} sampled"
            read_class = "count-estimated"
        elif rc.get("sampled"):
            read_display = f"{rc['sampled']:,}"
            read_tooltip = "Sampled reads (not total)"
            read_class = "count-sampled"
        elif exp.get("total_reads"):
            read_display = f"{exp['total_reads']:,}"
            read_tooltip = "Legacy format"
            read_class = "count-legacy"
        else:
            read_display = "-"
            read_tooltip = "No data"
            read_class = "count-none"

        experiments_json.append({
            "id": exp.get("id", ""),
            "name": exp.get("name", ""),
            "source": source,
            "status": exp.get("status", "registered"),
            "sample": metadata.get("sample", ""),
            "dataset": metadata.get("dataset", ""),
            "device": metadata.get("device_type", exp.get("platform", "")),
            "chemistry": metadata.get("chemistry", ""),
            "model": metadata.get("basecall_model", ""),
            "flowcell": metadata.get("flowcell_id", exp.get("flowcell_id", "")),
            "readDisplay": read_display,
            "readTooltip": read_tooltip,
            "readClass": read_class,
            "sampledReads": rc.get("sampled", 0),
            "estimatedReads": rc.get("estimated_total"),
            "countedReads": rc.get("counted_total"),
            "bases": exp.get("total_bases", 0) or exp.get("base_counts", {}).get("sampled_bases", 0),
            "meanQ": qm.get("mean_qscore") or exp.get("mean_quality", 0),
            "medianQ": qm.get("median_qscore"),
            "q20pct": qm.get("q20_percent"),
            "n50": lm.get("n50") or exp.get("n50", 0),
            "meanLength": lm.get("mean_length"),
            "maxLength": lm.get("max_length"),
            "mappingRate": am.get("mapping_rate"),
            "hasAnalyses": bool(exp.get("analyses")),
            "hasArtifacts": bool(exp.get("artifacts")),
            "urls": urls,
            "metadata": metadata,
            "analyses": exp.get("analyses", []),
            "artifacts": exp.get("artifacts", []),
            "registered": exp.get("registered", ""),
            "updated": exp.get("updated", ""),
            "completeness": comp,
            "runDate": metadata.get("run_date", ""),
            "modifications": metadata.get("modifications", []),
        })

    # Recent audit entries
    recent_audits = audit_log.get("entries", [])[-20:]

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ONT Experiment Registry Browser v3.0</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            color: #333;
            line-height: 1.5;
        }}
        .container {{ max-width: 1600px; margin: 0 auto; padding: 20px; }}

        /* Header */
        .header {{
            background: linear-gradient(135deg, #1a5f7a 0%, #16a085 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 25px;
        }}
        .header h1 {{ font-size: 2.2em; margin-bottom: 8px; }}
        .header-subtitle {{ opacity: 0.9; font-size: 1.1em; }}

        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }}
        .stat-card {{
            background: white;
            padding: 18px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .stat-value {{ font-size: 1.8em; font-weight: 700; color: #1a5f7a; }}
        .stat-label {{ font-size: 0.8em; color: #666; margin-top: 4px; }}
        .stat-value.good {{ color: #2e7d32; }}
        .stat-value.warning {{ color: #f57c00; }}
        .stat-value.poor {{ color: #c62828; }}

        /* Controls */
        .controls {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .search-row {{
            display: flex;
            gap: 15px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }}
        .search-input {{
            flex: 1;
            min-width: 300px;
            padding: 12px 15px;
            font-size: 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
        }}
        .search-input:focus {{ border-color: #1a5f7a; outline: none; }}
        .filter-row {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: center;
        }}
        .filter-select {{
            padding: 10px 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            min-width: 120px;
            background: white;
        }}
        .view-btns {{
            display: flex;
            gap: 5px;
            margin-left: auto;
        }}
        .view-btn {{
            padding: 10px 16px;
            border: 2px solid #1a5f7a;
            background: white;
            color: #1a5f7a;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
        }}
        .view-btn:hover {{ background: #f0f7fa; }}
        .view-btn.active {{ background: #1a5f7a; color: white; }}

        /* Experiment Grid */
        .experiment-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
            gap: 18px;
        }}
        .experiment-grid.list-view {{ grid-template-columns: 1fr; }}

        /* Experiment Card */
        .exp-card {{
            background: white;
            border-radius: 12px;
            padding: 18px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer;
            position: relative;
            border-left: 4px solid #ddd;
        }}
        .exp-card.complete-good {{ border-left-color: #2e7d32; }}
        .exp-card.complete-warning {{ border-left-color: #f57c00; }}
        .exp-card.complete-poor {{ border-left-color: #c62828; }}
        .exp-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.12);
        }}

        .exp-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 10px;
        }}
        .exp-name {{
            font-size: 1.05em;
            font-weight: 600;
            color: #333;
            word-break: break-word;
            flex: 1;
        }}
        .exp-id {{
            font-family: monospace;
            font-size: 0.75em;
            color: #888;
            margin-top: 3px;
        }}
        .exp-links {{
            display: flex;
            gap: 6px;
            flex-shrink: 0;
        }}
        .exp-link {{
            font-size: 0.7em;
            padding: 3px 7px;
            background: #e3f2fd;
            color: #1565c0;
            border-radius: 4px;
            text-decoration: none;
        }}
        .exp-link:hover {{ background: #bbdefb; }}

        /* Completeness indicator */
        .completeness-badge {{
            position: absolute;
            top: 10px;
            right: 10px;
            font-size: 0.7em;
            padding: 2px 8px;
            border-radius: 10px;
            font-weight: 500;
        }}
        .completeness-badge.good {{ background: #e8f5e9; color: #2e7d32; }}
        .completeness-badge.warning {{ background: #fff3e0; color: #ef6c00; }}
        .completeness-badge.poor {{ background: #ffebee; color: #c62828; }}

        /* Badges */
        .badge-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin: 10px 0;
        }}
        .badge {{
            display: inline-flex;
            align-items: center;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.68em;
            font-weight: 500;
        }}
        .badge-local {{ background: #e8f5e9; color: #2e7d32; }}
        .badge-public {{ background: #e3f2fd; color: #1565c0; }}
        .badge-analyzed {{ background: #fff3e0; color: #ef6c00; }}
        .badge-sample {{ background: #fce4ec; color: #c2185b; }}
        .badge-device {{ background: #f3e5f5; color: #7b1fa2; }}
        .badge-chemistry {{ background: #e0f2f1; color: #00695c; }}
        .badge-model {{ background: #e8eaf6; color: #3f51b5; }}

        /* Metrics Grid */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            padding-top: 12px;
            border-top: 1px solid #eee;
        }}
        .metric {{ text-align: center; }}
        .metric-value {{
            font-size: 1em;
            font-weight: 600;
            color: #1a5f7a;
        }}
        .metric-label {{
            font-size: 0.65em;
            color: #888;
            margin-top: 2px;
        }}

        /* Count styles */
        .count-exact {{ color: #2e7d32; }}
        .count-estimated {{ color: #f57c00; }}
        .count-sampled {{ color: #7b1fa2; }}
        .count-legacy {{ color: #888; font-style: italic; }}
        .q-high {{ color: #2e7d32; }}
        .q-medium {{ color: #f57c00; }}
        .q-low {{ color: #c62828; }}

        /* Legend */
        .legend {{
            background: white;
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .legend-title {{ font-weight: 600; margin-bottom: 10px; color: #555; }}
        .legend-items {{ display: flex; flex-wrap: wrap; gap: 20px; }}
        .legend-item {{ display: flex; align-items: center; gap: 8px; font-size: 0.85em; }}
        .legend-icon {{ width: 12px; height: 12px; border-radius: 50%; }}
        .legend-icon.good {{ background: #2e7d32; }}
        .legend-icon.warning {{ background: #f57c00; }}
        .legend-icon.poor {{ background: #c62828; }}

        /* Modal */
        .modal-overlay {{
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.6);
            z-index: 1000;
            overflow-y: auto;
        }}
        .modal-overlay.active {{ display: flex; justify-content: center; padding: 40px 20px; }}
        .modal {{
            background: white;
            border-radius: 16px;
            max-width: 950px;
            width: 100%;
            max-height: calc(100vh - 80px);
            overflow-y: auto;
        }}
        .modal-header {{
            padding: 25px;
            background: linear-gradient(135deg, #1a5f7a 0%, #16a085 100%);
            color: white;
            border-radius: 16px 16px 0 0;
            position: relative;
        }}
        .modal-close {{
            position: absolute;
            top: 15px; right: 20px;
            background: none; border: none;
            color: white;
            font-size: 28px;
            cursor: pointer;
            opacity: 0.8;
        }}
        .modal-close:hover {{ opacity: 1; }}
        .modal-body {{ padding: 25px; }}
        .modal-section {{ margin-bottom: 25px; }}
        .modal-section h3 {{
            font-size: 1.1em;
            color: #1a5f7a;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 2px solid #e0e0e0;
        }}
        .detail-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .detail-item {{
            padding: 12px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .detail-label {{ font-size: 0.8em; color: #666; margin-bottom: 4px; }}
        .detail-value {{ font-size: 1.1em; font-weight: 600; color: #333; }}
        .detail-note {{ font-size: 0.75em; color: #888; margin-top: 4px; font-style: italic; }}

        /* Table View */
        .table-view {{ display: none; }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .data-table th, .data-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        .data-table th {{ background: #1a5f7a; color: white; font-weight: 600; font-size: 0.9em; }}
        .data-table tr:hover {{ background: #f5f7fa; }}
        .data-table a {{ color: #1565c0; }}

        .hidden {{ display: none !important; }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>ONT Experiment Registry v3.0</h1>
        <p class="header-subtitle">
            {total} experiments | {by_source.get('ont-open-data', 0)} public | {by_source.get('local', 0)} local |
            Updated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
        </p>
    </div>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value">{total}</div>
            <div class="stat-label">Total Experiments</div>
        </div>
        <div class="stat-card">
            <div class="stat-value good">{completeness_stats['good']}</div>
            <div class="stat-label">Complete (80%+)</div>
        </div>
        <div class="stat-card">
            <div class="stat-value warning">{completeness_stats['warning']}</div>
            <div class="stat-label">Partial (50-79%)</div>
        </div>
        <div class="stat-card">
            <div class="stat-value poor">{completeness_stats['poor']}</div>
            <div class="stat-label">Incomplete (&lt;50%)</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{by_source.get('ont-open-data', 0)}</div>
            <div class="stat-label">Public Data</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{by_source.get('local', 0)}</div>
            <div class="stat-label">Local Data</div>
        </div>
    </div>

    <div class="legend">
        <div class="legend-title">Data Completeness</div>
        <div class="legend-items">
            <div class="legend-item">
                <div class="legend-icon good"></div>
                <span><strong>Good (80%+)</strong> - Most metadata present</span>
            </div>
            <div class="legend-item">
                <div class="legend-icon warning"></div>
                <span><strong>Partial (50-79%)</strong> - Some metadata missing</span>
            </div>
            <div class="legend-item">
                <div class="legend-icon poor"></div>
                <span><strong>Incomplete (&lt;50%)</strong> - Significant gaps</span>
            </div>
        </div>
    </div>

    <div class="controls">
        <div class="search-row">
            <input type="text" class="search-input" id="searchInput"
                   placeholder="Search by name, sample, dataset, flowcell...">
        </div>
        <div class="filter-row">
            <select class="filter-select" id="sourceFilter">
                <option value="">All Sources</option>
                <option value="local">Local</option>
                <option value="ont-open-data">Public</option>
            </select>
            <select class="filter-select" id="completenessFilter">
                <option value="">All Status</option>
                <option value="good">Complete</option>
                <option value="warning">Partial</option>
                <option value="poor">Incomplete</option>
            </select>
            <select class="filter-select" id="deviceFilter">
                <option value="">All Devices</option>
            </select>
            <select class="filter-select" id="sampleFilter">
                <option value="">All Samples</option>
            </select>
            <div class="view-btns">
                <button class="view-btn active" data-view="grid">Grid</button>
                <button class="view-btn" data-view="list">List</button>
                <button class="view-btn" data-view="table">Table</button>
            </div>
        </div>
    </div>

    <div class="experiment-grid" id="experimentGrid"></div>
    <div class="table-view" id="tableView"></div>
</div>

<div class="modal-overlay" id="modalOverlay">
    <div class="modal">
        <div class="modal-header">
            <h2 id="modalTitle">Experiment Details</h2>
            <button class="modal-close" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body" id="modalBody"></div>
    </div>
</div>

<script>
const experiments = {json.dumps(experiments_json, indent=2)};

// Populate filters
const devices = [...new Set(experiments.map(e => e.device).filter(Boolean))];
const samples = [...new Set(experiments.map(e => e.sample).filter(Boolean))];
document.getElementById('deviceFilter').innerHTML += devices.sort().map(d => `<option value="${{d}}">${{d}}</option>`).join('');
document.getElementById('sampleFilter').innerHTML += samples.sort().map(s => `<option value="${{s}}">${{s}}</option>`).join('');

function renderExperiments() {{
    const grid = document.getElementById('experimentGrid');
    const query = document.getElementById('searchInput').value.toLowerCase();
    const sourceFilter = document.getElementById('sourceFilter').value;
    const completenessFilter = document.getElementById('completenessFilter').value;
    const deviceFilter = document.getElementById('deviceFilter').value;
    const sampleFilter = document.getElementById('sampleFilter').value;

    const filtered = experiments.filter(exp => {{
        if (query) {{
            const searchText = [exp.name, exp.id, exp.sample, exp.dataset, exp.flowcell, exp.device].join(' ').toLowerCase();
            if (!searchText.includes(query)) return false;
        }}
        if (sourceFilter && exp.source !== sourceFilter) return false;
        if (completenessFilter && exp.completeness.status !== completenessFilter) return false;
        if (deviceFilter && exp.device !== deviceFilter) return false;
        if (sampleFilter && exp.sample !== sampleFilter) return false;
        return true;
    }});

    grid.innerHTML = filtered.map(exp => {{
        const qClass = exp.meanQ >= 20 ? 'q-high' : exp.meanQ >= 10 ? 'q-medium' : 'q-low';
        const badges = [];
        badges.push(`<span class="badge badge-${{exp.source === 'ont-open-data' ? 'public' : 'local'}}">${{exp.source === 'ont-open-data' ? 'public' : 'local'}}</span>`);
        if (exp.sample) badges.push(`<span class="badge badge-sample">${{exp.sample}}</span>`);
        if (exp.device) badges.push(`<span class="badge badge-device">${{exp.device}}</span>`);
        if (exp.chemistry) badges.push(`<span class="badge badge-chemistry">${{exp.chemistry}}</span>`);
        if (exp.model) badges.push(`<span class="badge badge-model">${{exp.model.toUpperCase()}}</span>`);

        const links = [];
        if (exp.urls.browser) links.push(`<a href="${{exp.urls.browser}}" target="_blank" class="exp-link" title="Browse files">Browse</a>`);
        if (exp.urls.https) links.push(`<a href="${{exp.urls.https}}" target="_blank" class="exp-link">Data</a>`);
        if (exp.urls.landing_page) links.push(`<a href="${{exp.urls.landing_page}}" target="_blank" class="exp-link">Info</a>`);

        return `
        <div class="exp-card complete-${{exp.completeness.status}}" onclick="showDetail('${{exp.id}}')">
            <span class="completeness-badge ${{exp.completeness.status}}">${{exp.completeness.percentage}}%</span>
            <div class="exp-header">
                <div>
                    <div class="exp-name">${{exp.name.slice(0,55)}}${{exp.name.length > 55 ? '...' : ''}}</div>
                    <div class="exp-id">${{exp.id}}</div>
                </div>
                <div class="exp-links" onclick="event.stopPropagation()">
                    ${{links.join('')}}
                </div>
            </div>
            <div class="badge-row">${{badges.join('')}}</div>
            <div class="metrics-grid">
                <div class="metric">
                    <div class="metric-value ${{exp.readClass}}" title="${{exp.readTooltip}}">${{exp.readDisplay}}</div>
                    <div class="metric-label">Reads</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${{(exp.bases/1e9).toFixed(2)}} Gb</div>
                    <div class="metric-label">Bases</div>
                </div>
                <div class="metric">
                    <div class="metric-value ${{qClass}}">${{exp.meanQ ? exp.meanQ.toFixed(1) : '-'}}</div>
                    <div class="metric-label">Mean Q</div>
                </div>
                <div class="metric">
                    <div class="metric-value">${{exp.n50 ? exp.n50.toLocaleString() : '-'}}</div>
                    <div class="metric-label">N50</div>
                </div>
            </div>
        </div>`;
    }}).join('');

    renderTable(filtered);
}}

function renderTable(filtered) {{
    const table = document.getElementById('tableView');
    table.innerHTML = `
    <table class="data-table">
        <thead>
            <tr>
                <th>Name</th>
                <th>Source</th>
                <th>Sample</th>
                <th>Device</th>
                <th>Reads</th>
                <th>Q-Score</th>
                <th>N50</th>
                <th>Complete</th>
                <th>Links</th>
            </tr>
        </thead>
        <tbody>
            ${{filtered.map(exp => `
            <tr onclick="showDetail('${{exp.id}}')" style="cursor:pointer">
                <td>${{exp.name.slice(0,35)}}</td>
                <td>${{exp.source === 'ont-open-data' ? 'public' : 'local'}}</td>
                <td>${{exp.sample || '-'}}</td>
                <td>${{exp.device || '-'}}</td>
                <td class="${{exp.readClass}}">${{exp.readDisplay}}</td>
                <td>${{exp.meanQ ? exp.meanQ.toFixed(1) : '-'}}</td>
                <td>${{exp.n50 ? exp.n50.toLocaleString() : '-'}}</td>
                <td><span class="completeness-badge ${{exp.completeness.status}}">${{exp.completeness.percentage}}%</span></td>
                <td onclick="event.stopPropagation()">
                    ${{exp.urls.browser ? `<a href="${{exp.urls.browser}}" target="_blank">Browse</a>` : ''}}
                </td>
            </tr>`).join('')}}
        </tbody>
    </table>`;
}}

function showDetail(expId) {{
    const exp = experiments.find(e => e.id === expId);
    if (!exp) return;

    document.getElementById('modalTitle').textContent = exp.name;
    const qClass = exp.meanQ >= 20 ? 'q-high' : exp.meanQ >= 10 ? 'q-medium' : 'q-low';

    let html = `
    <div class="modal-section">
        <h3>Data Completeness: ${{exp.completeness.percentage}}%</h3>
        <div class="detail-grid">
            <div class="detail-item">
                <div class="detail-label">Status</div>
                <div class="detail-value"><span class="completeness-badge ${{exp.completeness.status}}">${{exp.completeness.status.toUpperCase()}}</span></div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Missing Fields</div>
                <div class="detail-value" style="font-size:0.9em">${{exp.completeness.missing.length > 0 ? exp.completeness.missing.join(', ') : 'None'}}</div>
            </div>
        </div>
    </div>

    <div class="modal-section">
        <h3>Data Access</h3>
        <div class="detail-grid">
            ${{exp.urls.browser ? `
            <div class="detail-item">
                <div class="detail-label">Visual Browser</div>
                <div class="detail-value"><a href="${{exp.urls.browser}}" target="_blank">42basepairs.com</a></div>
                <div class="detail-note">Interactive file browser</div>
            </div>` : ''}}
            ${{exp.urls.https ? `
            <div class="detail-item">
                <div class="detail-label">HTTPS URL</div>
                <div class="detail-value"><a href="${{exp.urls.https}}" target="_blank">Download/Stream</a></div>
            </div>` : ''}}
            ${{exp.urls.s3 ? `
            <div class="detail-item">
                <div class="detail-label">S3 URI</div>
                <div class="detail-value" style="font-family:monospace;font-size:0.85em">${{exp.urls.s3}}</div>
            </div>` : ''}}
            ${{exp.urls.landing_page ? `
            <div class="detail-item">
                <div class="detail-label">Dataset Info</div>
                <div class="detail-value"><a href="${{exp.urls.landing_page}}" target="_blank">EPI2ME Labs</a></div>
            </div>` : ''}}
        </div>
    </div>

    <div class="modal-section">
        <h3>Read Counts</h3>
        <div class="detail-grid">
            <div class="detail-item">
                <div class="detail-label">Sampled Reads</div>
                <div class="detail-value">${{exp.sampledReads ? exp.sampledReads.toLocaleString() : '-'}}</div>
                <div class="detail-note">Reads processed during analysis</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Estimated Total</div>
                <div class="detail-value">${{exp.estimatedReads ? '~' + exp.estimatedReads.toLocaleString() : 'Not computed'}}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Counted Total</div>
                <div class="detail-value">${{exp.countedReads ? exp.countedReads.toLocaleString() : 'Not counted'}}</div>
            </div>
        </div>
    </div>

    <div class="modal-section">
        <h3>Quality Metrics</h3>
        <div class="detail-grid">
            <div class="detail-item">
                <div class="detail-label">Mean Q-Score</div>
                <div class="detail-value ${{qClass}}">${{exp.meanQ ? exp.meanQ.toFixed(2) : '-'}}</div>
                <div class="detail-note">Probability space averaging</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Median Q-Score</div>
                <div class="detail-value">${{exp.medianQ ? exp.medianQ.toFixed(2) : '-'}}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Q20+ Reads</div>
                <div class="detail-value">${{exp.q20pct ? exp.q20pct.toFixed(1) + '%' : '-'}}</div>
            </div>
        </div>
    </div>

    <div class="modal-section">
        <h3>Length Metrics</h3>
        <div class="detail-grid">
            <div class="detail-item">
                <div class="detail-label">N50</div>
                <div class="detail-value">${{exp.n50 ? exp.n50.toLocaleString() + ' bp' : '-'}}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Mean Length</div>
                <div class="detail-value">${{exp.meanLength ? Math.round(exp.meanLength).toLocaleString() + ' bp' : '-'}}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Max Length</div>
                <div class="detail-value">${{exp.maxLength ? exp.maxLength.toLocaleString() + ' bp' : '-'}}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Mapping Rate</div>
                <div class="detail-value">${{exp.mappingRate ? exp.mappingRate.toFixed(1) + '%' : '-'}}</div>
            </div>
        </div>
    </div>

    <div class="modal-section">
        <h3>Metadata</h3>
        <div class="detail-grid">
            <div class="detail-item"><div class="detail-label">Experiment ID</div><div class="detail-value" style="font-family:monospace">${{exp.id}}</div></div>
            <div class="detail-item"><div class="detail-label">Source</div><div class="detail-value">${{exp.source}}</div></div>
            ${{exp.sample ? `<div class="detail-item"><div class="detail-label">Sample</div><div class="detail-value">${{exp.sample}}</div></div>` : ''}}
            ${{exp.dataset ? `<div class="detail-item"><div class="detail-label">Dataset</div><div class="detail-value">${{exp.dataset}}</div></div>` : ''}}
            ${{exp.device ? `<div class="detail-item"><div class="detail-label">Device</div><div class="detail-value">${{exp.device}}</div></div>` : ''}}
            ${{exp.flowcell ? `<div class="detail-item"><div class="detail-label">Flowcell</div><div class="detail-value">${{exp.flowcell}}</div></div>` : ''}}
            ${{exp.chemistry ? `<div class="detail-item"><div class="detail-label">Chemistry</div><div class="detail-value">${{exp.chemistry}}</div></div>` : ''}}
            ${{exp.model ? `<div class="detail-item"><div class="detail-label">Basecall Model</div><div class="detail-value">${{exp.model.toUpperCase()}}</div></div>` : ''}}
            ${{exp.runDate ? `<div class="detail-item"><div class="detail-label">Run Date</div><div class="detail-value">${{exp.runDate}}</div></div>` : ''}}
            ${{exp.modifications && exp.modifications.length ? `<div class="detail-item"><div class="detail-label">Modifications</div><div class="detail-value">${{exp.modifications.join(', ')}}</div></div>` : ''}}
        </div>
    </div>`;

    document.getElementById('modalBody').innerHTML = html;
    document.getElementById('modalOverlay').classList.add('active');
}}

function closeModal() {{ document.getElementById('modalOverlay').classList.remove('active'); }}

// View switching
document.querySelectorAll('.view-btn').forEach(btn => {{
    btn.addEventListener('click', function() {{
        document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        const view = this.dataset.view;
        const grid = document.getElementById('experimentGrid');
        const table = document.getElementById('tableView');
        if (view === 'table') {{
            grid.classList.add('hidden');
            table.classList.remove('hidden');
            table.style.display = 'block';
        }} else {{
            grid.classList.remove('hidden');
            table.classList.add('hidden');
            table.style.display = 'none';
            grid.classList.toggle('list-view', view === 'list');
        }}
    }});
}});

// Event listeners
document.getElementById('searchInput').addEventListener('input', renderExperiments);
document.getElementById('sourceFilter').addEventListener('change', renderExperiments);
document.getElementById('completenessFilter').addEventListener('change', renderExperiments);
document.getElementById('deviceFilter').addEventListener('change', renderExperiments);
document.getElementById('sampleFilter').addEventListener('change', renderExperiments);
document.getElementById('modalOverlay').addEventListener('click', function(e) {{ if (e.target === this) closeModal(); }});

renderExperiments();
</script>
</body>
</html>'''

    return html


def main():
    print("Generating Registry Browser v3.0...")

    data = load_registry()
    experiments = data.get("experiments", [])
    audit_log = load_audit_log()

    print(f"  Total experiments: {len(experiments)}")

    html = generate_html(experiments, audit_log)

    # Save
    output_path = OUTPUT_DIR / "registry_browser_v3.html"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(html)
    print(f"  Saved: {output_path}")

    # Copy to Windows
    windows_path = Path("/mnt/c/Users/farnu/Downloads/registry_browser_v3.html")
    try:
        shutil.copy(output_path, windows_path)
        print(f"  Copied to: {windows_path}")
    except Exception as e:
        print(f"  Copy failed: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
