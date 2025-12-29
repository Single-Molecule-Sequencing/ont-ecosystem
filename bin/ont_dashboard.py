#!/usr/bin/env python3
"""
ONT Ecosystem Web Dashboard

A Flask-based web interface for the ONT Ecosystem.

Usage:
    ont_dashboard.py [--port PORT] [--host HOST] [--debug]
    
Example:
    ont_dashboard.py --port 8080
    ont_dashboard.py --host 0.0.0.0 --port 5000
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from flask import Flask, jsonify, render_template_string, request
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

# Import registry
sys.path.insert(0, str(Path(__file__).parent))
try:
    from ont_registry import ExperimentRegistry
except ImportError:
    ExperimentRegistry = None


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>ONT Ecosystem Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a; color: #e2e8f0; padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { color: #10b981; margin-bottom: 10px; }
        .subtitle { color: #64748b; margin-bottom: 30px; }
        .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }
        .stat-card { background: #1e293b; border-radius: 8px; padding: 20px; }
        .stat-value { font-size: 2rem; font-weight: bold; color: #10b981; }
        .stat-label { color: #94a3b8; font-size: 0.9rem; }
        .section { background: #1e293b; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
        .section h2 { color: #f1f5f9; margin-bottom: 15px; font-size: 1.2rem; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #334155; }
        th { color: #94a3b8; font-weight: 500; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; }
        .badge-green { background: #064e3b; color: #34d399; }
        .badge-blue { background: #1e3a5f; color: #60a5fa; }
        .badge-purple { background: #3b0764; color: #c084fc; }
        .search { margin-bottom: 20px; }
        .search input { 
            width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #334155;
            background: #0f172a; color: #e2e8f0; font-size: 1rem;
        }
        .footer { text-align: center; color: #64748b; margin-top: 40px; font-size: 0.85rem; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧬 ONT Ecosystem Dashboard</h1>
        <p class="subtitle">Single Molecule Sequencing Lab • University of Michigan</p>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{{ stats.total_experiments }}</div>
                <div class="stat-label">Total Experiments</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.unique_flowcells }}</div>
                <div class="stat-label">Unique Flowcells</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.unique_devices }}</div>
                <div class="stat-label">Devices</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.with_qc_data }}</div>
                <div class="stat-label">With QC Data</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Recent Experiments</h2>
            <div class="search">
                <input type="text" id="search" placeholder="Search experiments..." onkeyup="filterTable()">
            </div>
            <table id="experiments-table">
                <thead>
                    <tr>
                        <th>Run ID</th>
                        <th>Experiment</th>
                        <th>Device</th>
                        <th>Flowcell</th>
                        <th>Date</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for exp in experiments %}
                    <tr>
                        <td><code>{{ exp.run_id }}</code></td>
                        <td>{{ exp.experiment or exp.harmonized_name or 'N/A' }}</td>
                        <td>{{ exp.device or 'N/A' }}</td>
                        <td>{{ exp.flowcell or 'N/A' }}</td>
                        <td>{{ exp.date or 'N/A' }}</td>
                        <td>
                            {% if exp.is_canonical %}
                            <span class="badge badge-green">Canonical</span>
                            {% elif exp.is_manuscript %}
                            <span class="badge badge-purple">Manuscript</span>
                            {% else %}
                            <span class="badge badge-blue">Complete</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <p class="footer">ONT Ecosystem v2.1 • <a href="/api/stats" style="color: #60a5fa;">API</a></p>
    </div>
    
    <script>
    function filterTable() {
        const input = document.getElementById('search').value.toLowerCase();
        const rows = document.querySelectorAll('#experiments-table tbody tr');
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(input) ? '' : 'none';
        });
    }
    </script>
</body>
</html>
"""

def create_app(registry_path=None):
    """Create Flask application"""
    app = Flask(__name__)
    
    # Initialize registry
    if ExperimentRegistry:
        registry = ExperimentRegistry(registry_path)
    else:
        registry = None
    
    @app.route('/')
    def index():
        if not registry:
            return "Registry not available", 500
        
        stats = registry.stats()
        experiments = list(registry.experiments.values())[:50]
        experiments.sort(key=lambda x: x.get('registered', ''), reverse=True)
        
        return render_template_string(HTML_TEMPLATE, stats=stats, experiments=experiments)
    
    @app.route('/api/stats')
    def api_stats():
        if not registry:
            return jsonify({"error": "Registry not available"}), 500
        return jsonify(registry.stats())
    
    @app.route('/api/experiments')
    def api_experiments():
        if not registry:
            return jsonify({"error": "Registry not available"}), 500
        
        limit = request.args.get('limit', 100, type=int)
        experiments = list(registry.experiments.values())[:limit]
        return jsonify({"experiments": experiments, "count": len(experiments)})
    
    @app.route('/api/experiments/<run_id>')
    def api_experiment(run_id):
        if not registry:
            return jsonify({"error": "Registry not available"}), 500
        
        exp = registry.get(run_id)
        if not exp:
            return jsonify({"error": "Not found"}), 404
        return jsonify(exp)
    
    @app.route('/api/devices')
    def api_devices():
        if not registry:
            return jsonify({"error": "Registry not available"}), 500
        
        devices = {dev: len(ids) for dev, ids in registry.index_device.items()}
        return jsonify({"devices": devices})
    
    return app


def main():
    parser = argparse.ArgumentParser(description='ONT Ecosystem Web Dashboard')
    parser.add_argument('--port', type=int, default=5000, help='Port to run on')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--registry', help='Path to registry file')
    args = parser.parse_args()
    
    if not HAS_FLASK:
        print("Error: Flask is required. Install with: pip install flask")
        sys.exit(1)
    
    app = create_app(args.registry)
    print(f"🧬 ONT Dashboard running at http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
