#!/usr/bin/env python3
"""
ONT Ecosystem Web Dashboard
A Flask-based web interface for viewing and managing experiments.

Usage:
    ont_dashboard.py                    # Start on default port 5000
    ont_dashboard.py --port 8080        # Custom port
    ont_dashboard.py --host 0.0.0.0     # Listen on all interfaces
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))

try:
    from flask import Flask, render_template_string, jsonify, request, send_file
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False
    print("Flask not installed. Install with: pip install flask")
    sys.exit(1)

try:
    from ont_core import Registry, get_registry_dir, format_bytes
except ImportError:
    # Inline minimal implementation
    class Registry:
        def __init__(self, *args, **kwargs):
            pass
        def list(self, **kwargs):
            return []
        def get(self, id):
            return None
        def get_stats(self):
            return {}
        @property
        def count(self):
            return 0

app = Flask(__name__)

# =============================================================================
# HTML Templates
# =============================================================================

BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ONT Ecosystem - {{ title }}</title>
    <style>
        :root {
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #ef4444;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text: #1e293b;
            --text-muted: #64748b;
            --border: #e2e8f0;
        }
        
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }
        
        .container { max-width: 1400px; margin: 0 auto; padding: 0 20px; }
        
        header {
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            padding: 20px 0;
            margin-bottom: 30px;
        }
        
        header h1 { font-size: 1.8rem; font-weight: 600; }
        header p { opacity: 0.9; margin-top: 5px; }
        
        nav {
            background: var(--card-bg);
            border-bottom: 1px solid var(--border);
            padding: 10px 0;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        nav a {
            color: var(--text);
            text-decoration: none;
            padding: 10px 20px;
            display: inline-block;
            border-radius: 6px;
            transition: background 0.2s;
        }
        
        nav a:hover, nav a.active {
            background: var(--bg);
            color: var(--primary);
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: var(--card-bg);
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .stat-card .value {
            font-size: 2rem;
            font-weight: 700;
            color: var(--primary);
        }
        
        .stat-card .label {
            color: var(--text-muted);
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .card {
            background: var(--card-bg);
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            overflow: hidden;
        }
        
        .card-header {
            padding: 15px 20px;
            border-bottom: 1px solid var(--border);
            font-weight: 600;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .card-body { padding: 20px; }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }
        
        th {
            background: var(--bg);
            font-weight: 600;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
        }
        
        tr:hover { background: var(--bg); }
        
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        
        .badge-success { background: #dcfce7; color: #166534; }
        .badge-warning { background: #fef3c7; color: #92400e; }
        .badge-info { background: #dbeafe; color: #1e40af; }
        .badge-default { background: #f1f5f9; color: #475569; }
        
        .tag {
            display: inline-block;
            padding: 2px 8px;
            background: var(--bg);
            border-radius: 4px;
            font-size: 0.75rem;
            margin-right: 4px;
            margin-bottom: 4px;
        }
        
        .search-box {
            width: 100%;
            padding: 12px 15px;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 1rem;
            margin-bottom: 20px;
        }
        
        .search-box:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }
        
        .btn {
            display: inline-block;
            padding: 10px 20px;
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            text-decoration: none;
            font-size: 0.875rem;
            font-weight: 500;
            transition: background 0.2s;
        }
        
        .btn:hover { background: var(--primary-dark); }
        .btn-secondary { background: var(--text-muted); }
        .btn-sm { padding: 6px 12px; font-size: 0.75rem; }
        
        .timeline {
            position: relative;
            padding-left: 30px;
        }
        
        .timeline::before {
            content: '';
            position: absolute;
            left: 10px;
            top: 0;
            bottom: 0;
            width: 2px;
            background: var(--border);
        }
        
        .timeline-item {
            position: relative;
            padding-bottom: 20px;
        }
        
        .timeline-item::before {
            content: '';
            position: absolute;
            left: -24px;
            top: 5px;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--primary);
            border: 2px solid white;
        }
        
        .timeline-item.success::before { background: var(--success); }
        .timeline-item.warning::before { background: var(--warning); }
        .timeline-item.error::before { background: var(--danger); }
        
        .chart-container {
            height: 300px;
            position: relative;
        }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: var(--text-muted);
        }
        
        .empty-state h3 { margin-bottom: 10px; color: var(--text); }
        
        footer {
            text-align: center;
            padding: 40px 0;
            color: var(--text-muted);
            font-size: 0.875rem;
        }
        
        @media (max-width: 768px) {
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            th, td { padding: 8px 10px; font-size: 0.875rem; }
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>🧬 ONT Ecosystem</h1>
            <p>Oxford Nanopore Experiment Management</p>
        </div>
    </header>
    
    <nav>
        <div class="container">
            <a href="/" class="{{ 'active' if active_page == 'dashboard' else '' }}">Dashboard</a>
            <a href="/experiments" class="{{ 'active' if active_page == 'experiments' else '' }}">Experiments</a>
            <a href="/public" class="{{ 'active' if active_page == 'public' else '' }}">Public Data</a>
            <a href="/api" class="{{ 'active' if active_page == 'api' else '' }}">API</a>
        </div>
    </nav>
    
    <main class="container">
        {% block content %}{% endblock %}
    </main>
    
    <footer>
        <div class="container">
            ONT Ecosystem v2.1 • Single Molecule Sequencing Lab, University of Michigan
        </div>
    </footer>
    
    <script>
        // Simple client-side filtering
        function filterTable(inputId, tableId) {
            const input = document.getElementById(inputId);
            const table = document.getElementById(tableId);
            const rows = table.getElementsByTagName('tr');
            
            input.addEventListener('keyup', function() {
                const filter = this.value.toLowerCase();
                
                for (let i = 1; i < rows.length; i++) {
                    const row = rows[i];
                    const text = row.textContent.toLowerCase();
                    row.style.display = text.includes(filter) ? '' : 'none';
                }
            });
        }
    </script>
</body>
</html>
'''

DASHBOARD_TEMPLATE = '''
{% extends "base" %}
{% block content %}
<h2 style="margin-bottom: 20px;">Dashboard</h2>

<div class="stats-grid">
    <div class="stat-card">
        <div class="value">{{ stats.total_experiments }}</div>
        <div class="label">Total Experiments</div>
    </div>
    <div class="stat-card">
        <div class="value">{{ stats.total_analyses }}</div>
        <div class="label">Total Analyses</div>
    </div>
    <div class="stat-card">
        <div class="value">{{ "%.1f"|format(stats.total_size_gb) }} GB</div>
        <div class="label">Total Data</div>
    </div>
    <div class="stat-card">
        <div class="value">{{ stats.total_reads|default(0)|int }}</div>
        <div class="label">Total Reads</div>
    </div>
</div>

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px;">
    <div class="card">
        <div class="card-header">By Status</div>
        <div class="card-body">
            {% for status, count in stats.by_status.items() %}
            <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid var(--border);">
                <span>{{ status }}</span>
                <span class="badge badge-info">{{ count }}</span>
            </div>
            {% else %}
            <p class="empty-state">No experiments yet</p>
            {% endfor %}
        </div>
    </div>
    
    <div class="card">
        <div class="card-header">By Platform</div>
        <div class="card-body">
            {% for platform, count in stats.by_platform.items() %}
            <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid var(--border);">
                <span>{{ platform }}</span>
                <span class="badge badge-default">{{ count }}</span>
            </div>
            {% else %}
            <p style="color: var(--text-muted);">No platform data</p>
            {% endfor %}
        </div>
    </div>
    
    <div class="card">
        <div class="card-header">Popular Tags</div>
        <div class="card-body">
            {% for tag, count in stats.tags.items()|sort(attribute='1', reverse=True)|list[:10] %}
            <span class="tag">{{ tag }} ({{ count }})</span>
            {% else %}
            <p style="color: var(--text-muted);">No tags yet</p>
            {% endfor %}
        </div>
    </div>
    
    <div class="card">
        <div class="card-header">Recent Experiments</div>
        <div class="card-body">
            {% for exp in recent %}
            <div style="padding: 10px 0; border-bottom: 1px solid var(--border);">
                <a href="/experiment/{{ exp.id }}" style="color: var(--primary); text-decoration: none; font-weight: 500;">
                    {{ exp.name or exp.id }}
                </a>
                <div style="font-size: 0.875rem; color: var(--text-muted);">
                    {{ exp.platform }} • {{ exp.status }}
                </div>
            </div>
            {% else %}
            <p style="color: var(--text-muted);">No recent experiments</p>
            {% endfor %}
        </div>
    </div>
</div>
{% endblock %}
'''

EXPERIMENTS_TEMPLATE = '''
{% extends "base" %}
{% block content %}
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
    <h2>Experiments</h2>
    <div>
        <a href="/api/experiments/export?format=csv" class="btn btn-secondary btn-sm">Export CSV</a>
        <a href="/api/experiments/export?format=json" class="btn btn-secondary btn-sm">Export JSON</a>
    </div>
</div>

<input type="text" id="search" class="search-box" placeholder="Search experiments by name, ID, sample, or tags...">

<div class="card">
    <table id="experiments-table">
        <thead>
            <tr>
                <th>Name</th>
                <th>ID</th>
                <th>Status</th>
                <th>Platform</th>
                <th>Sample</th>
                <th>Reads</th>
                <th>Tags</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for exp in experiments %}
            <tr>
                <td><a href="/experiment/{{ exp.id }}" style="color: var(--primary); text-decoration: none;">{{ exp.name or exp.id }}</a></td>
                <td style="font-family: monospace; font-size: 0.875rem;">{{ exp.id[:16] }}</td>
                <td>
                    <span class="badge {% if exp.status == 'complete' %}badge-success{% elif exp.status == 'analyzing' %}badge-warning{% else %}badge-default{% endif %}">
                        {{ exp.status }}
                    </span>
                </td>
                <td>{{ exp.platform or '-' }}</td>
                <td>{{ exp.sample_id or '-' }}</td>
                <td>{{ "{:,}".format(exp.total_reads) if exp.total_reads else '-' }}</td>
                <td>
                    {% for tag in exp.tags[:3] %}
                    <span class="tag">{{ tag }}</span>
                    {% endfor %}
                    {% if exp.tags|length > 3 %}
                    <span class="tag">+{{ exp.tags|length - 3 }}</span>
                    {% endif %}
                </td>
                <td>
                    <a href="/experiment/{{ exp.id }}" class="btn btn-sm">View</a>
                </td>
            </tr>
            {% else %}
            <tr>
                <td colspan="8" class="empty-state">
                    <h3>No experiments found</h3>
                    <p>Run <code>ont_experiments.py discover /path</code> to find experiments</p>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<script>filterTable('search', 'experiments-table');</script>
{% endblock %}
'''

EXPERIMENT_DETAIL_TEMPLATE = '''
{% extends "base" %}
{% block content %}
<div style="margin-bottom: 20px;">
    <a href="/experiments" style="color: var(--text-muted); text-decoration: none;">← Back to Experiments</a>
</div>

<div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 20px;">
    <div>
        <h2>{{ exp.name or exp.id }}</h2>
        <p style="color: var(--text-muted); font-family: monospace;">{{ exp.id }}</p>
    </div>
    <span class="badge {% if exp.status == 'complete' %}badge-success{% elif exp.status == 'analyzing' %}badge-warning{% else %}badge-default{% endif %}" style="font-size: 1rem;">
        {{ exp.status }}
    </span>
</div>

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 20px;">
    <div class="card">
        <div class="card-header">Run Information</div>
        <div class="card-body">
            <table style="font-size: 0.875rem;">
                <tr><td style="color: var(--text-muted);">Platform</td><td>{{ exp.platform or '-' }}</td></tr>
                <tr><td style="color: var(--text-muted);">Chemistry</td><td>{{ exp.chemistry or '-' }}</td></tr>
                <tr><td style="color: var(--text-muted);">Flow Cell</td><td>{{ exp.flowcell_id or '-' }}</td></tr>
                <tr><td style="color: var(--text-muted);">Kit</td><td>{{ exp.kit or '-' }}</td></tr>
                <tr><td style="color: var(--text-muted);">Sample ID</td><td>{{ exp.sample_id or '-' }}</td></tr>
                <tr><td style="color: var(--text-muted);">Location</td><td style="word-break: break-all;">{{ exp.location }}</td></tr>
            </table>
        </div>
    </div>
    
    <div class="card">
        <div class="card-header">Statistics</div>
        <div class="card-body">
            <table style="font-size: 0.875rem;">
                <tr><td style="color: var(--text-muted);">Total Reads</td><td>{{ "{:,}".format(exp.total_reads) if exp.total_reads else '-' }}</td></tr>
                <tr><td style="color: var(--text-muted);">Total Bases</td><td>{{ "{:,}".format(exp.total_bases) if exp.total_bases else '-' }}</td></tr>
                <tr><td style="color: var(--text-muted);">N50</td><td>{{ "{:,}".format(exp.n50) if exp.n50 else '-' }} bp</td></tr>
                <tr><td style="color: var(--text-muted);">Mean Quality</td><td>{{ "%.1f"|format(exp.mean_quality) if exp.mean_quality else '-' }}</td></tr>
                <tr><td style="color: var(--text-muted);">Data Size</td><td>{{ "%.2f"|format(exp.total_size_gb) if exp.total_size_gb else '-' }} GB</td></tr>
                <tr><td style="color: var(--text-muted);">Format</td><td>{{ exp.data_format or '-' }}</td></tr>
            </table>
        </div>
    </div>
</div>

<div class="card">
    <div class="card-header">
        Tags
        <span class="badge badge-default">{{ exp.tags|length }}</span>
    </div>
    <div class="card-body">
        {% for tag in exp.tags %}
        <span class="tag">{{ tag }}</span>
        {% else %}
        <p style="color: var(--text-muted);">No tags</p>
        {% endfor %}
    </div>
</div>

<div class="card">
    <div class="card-header">
        Event History
        <span class="badge badge-default">{{ exp.events|length }}</span>
    </div>
    <div class="card-body">
        <div class="timeline">
            {% for event in exp.events|reverse %}
            <div class="timeline-item {% if event.exit_code == 0 %}success{% elif event.exit_code %}error{% else %}{% endif %}">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <strong>{{ event.type }}{% if event.analysis %}: {{ event.analysis }}{% endif %}</strong>
                    <span style="color: var(--text-muted); font-size: 0.875rem;">{{ event.timestamp[:19] }}</span>
                </div>
                {% if event.command %}
                <code style="display: block; background: var(--bg); padding: 8px; border-radius: 4px; font-size: 0.75rem; overflow-x: auto; margin: 10px 0;">{{ event.command }}</code>
                {% endif %}
                {% if event.results %}
                <div style="font-size: 0.875rem; color: var(--text-muted);">
                    Results: {{ event.results }}
                </div>
                {% endif %}
                {% if event.duration_seconds %}
                <div style="font-size: 0.875rem; color: var(--text-muted);">
                    Duration: {{ "%.1f"|format(event.duration_seconds) }}s
                    {% if event.exit_code is not none %}
                    • Exit: {{ event.exit_code }}
                    {% endif %}
                </div>
                {% endif %}
            </div>
            {% else %}
            <p style="color: var(--text-muted);">No events recorded</p>
            {% endfor %}
        </div>
    </div>
</div>

{% if exp.notes %}
<div class="card">
    <div class="card-header">Notes</div>
    <div class="card-body">{{ exp.notes }}</div>
</div>
{% endif %}
{% endblock %}
'''

PUBLIC_DATA_TEMPLATE = '''
{% extends "base" %}
{% block content %}
<h2 style="margin-bottom: 20px;">Public Datasets</h2>
<p style="margin-bottom: 20px; color: var(--text-muted);">
    Access ONT Open Data datasets. Browse online at 
    <a href="https://42basepairs.com/browse/s3/ont-open-data" target="_blank">42basepairs.com</a>.
</p>

{% for category, info in datasets.items() %}
<div class="card">
    <div class="card-header">{{ info.name }}</div>
    <div class="card-body">
        <table>
            <thead>
                <tr>
                    <th>Dataset</th>
                    <th>Description</th>
                    <th>Size</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for id, dataset in info.datasets.items() %}
                <tr>
                    <td>
                        <strong>{{ dataset.name }}</strong>
                        {% if dataset.featured %}<span class="badge badge-warning">Featured</span>{% endif %}
                    </td>
                    <td>{{ dataset.description }}</td>
                    <td>{{ dataset.size }}</td>
                    <td>
                        <a href="https://42basepairs.com/browse/s3/ont-open-data/{{ dataset.s3_path }}" 
                           target="_blank" class="btn btn-sm">Browse</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endfor %}
{% endblock %}
'''

API_DOCS_TEMPLATE = '''
{% extends "base" %}
{% block content %}
<h2 style="margin-bottom: 20px;">API Reference</h2>

<div class="card">
    <div class="card-header">Endpoints</div>
    <div class="card-body">
        <table>
            <thead>
                <tr><th>Method</th><th>Endpoint</th><th>Description</th></tr>
            </thead>
            <tbody>
                <tr><td><span class="badge badge-success">GET</span></td><td><code>/api/experiments</code></td><td>List all experiments</td></tr>
                <tr><td><span class="badge badge-success">GET</span></td><td><code>/api/experiments/{id}</code></td><td>Get experiment details</td></tr>
                <tr><td><span class="badge badge-success">GET</span></td><td><code>/api/experiments/search?q={query}</code></td><td>Search experiments</td></tr>
                <tr><td><span class="badge badge-success">GET</span></td><td><code>/api/experiments/export?format=csv|json</code></td><td>Export all experiments</td></tr>
                <tr><td><span class="badge badge-success">GET</span></td><td><code>/api/stats</code></td><td>Get registry statistics</td></tr>
                <tr><td><span class="badge badge-success">GET</span></td><td><code>/api/public</code></td><td>List public datasets</td></tr>
            </tbody>
        </table>
    </div>
</div>

<div class="card">
    <div class="card-header">Example: List Experiments</div>
    <div class="card-body">
        <code style="display: block; background: var(--bg); padding: 15px; border-radius: 4px; overflow-x: auto;">
curl {{ request.host_url }}api/experiments
        </code>
    </div>
</div>

<div class="card">
    <div class="card-header">Example: Get Experiment</div>
    <div class="card-body">
        <code style="display: block; background: var(--bg); padding: 15px; border-radius: 4px; overflow-x: auto;">
curl {{ request.host_url }}api/experiments/exp-abc123
        </code>
    </div>
</div>
{% endblock %}
'''

# =============================================================================
# Routes
# =============================================================================

@app.route('/')
def dashboard():
    registry = Registry()
    stats = registry.get_stats()
    recent = registry.list(limit=5)
    
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', DASHBOARD_TEMPLATE),
        title='Dashboard',
        active_page='dashboard',
        stats=stats,
        recent=recent
    )

@app.route('/experiments')
def experiments_list():
    registry = Registry()
    experiments = registry.list()
    
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', EXPERIMENTS_TEMPLATE),
        title='Experiments',
        active_page='experiments',
        experiments=experiments
    )

@app.route('/experiment/<exp_id>')
def experiment_detail(exp_id):
    registry = Registry()
    exp = registry.get(exp_id)
    
    if not exp:
        return "Experiment not found", 404
    
    # Convert events to dicts for template
    exp_dict = exp.to_dict()
    
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', EXPERIMENT_DETAIL_TEMPLATE),
        title=exp.name or exp.id,
        active_page='experiments',
        exp=type('Exp', (), exp_dict)()  # Convert dict to object for template
    )

@app.route('/public')
def public_data():
    from ont_core import load_config
    datasets = load_config('public_datasets').get('categories', {})
    
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', PUBLIC_DATA_TEMPLATE),
        title='Public Data',
        active_page='public',
        datasets=datasets
    )

@app.route('/api')
def api_docs():
    return render_template_string(
        BASE_TEMPLATE.replace('{% block content %}{% endblock %}', API_DOCS_TEMPLATE),
        title='API',
        active_page='api'
    )

# =============================================================================
# API Endpoints
# =============================================================================

@app.route('/api/experiments')
def api_experiments():
    registry = Registry()
    
    # Parse filters
    tags = request.args.get('tags', '').split(',') if request.args.get('tags') else None
    status = request.args.get('status')
    limit = request.args.get('limit', type=int)
    
    experiments = registry.list(tags=tags, status=status, limit=limit)
    
    return jsonify({
        'count': len(experiments),
        'experiments': [e.to_dict() for e in experiments]
    })

@app.route('/api/experiments/<exp_id>')
def api_experiment(exp_id):
    registry = Registry()
    exp = registry.get(exp_id)
    
    if not exp:
        return jsonify({'error': 'Experiment not found'}), 404
    
    return jsonify(exp.to_dict())

@app.route('/api/experiments/search')
def api_search():
    registry = Registry()
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({'error': 'Query parameter q is required'}), 400
    
    experiments = registry.search(query)
    
    return jsonify({
        'query': query,
        'count': len(experiments),
        'experiments': [e.to_dict() for e in experiments]
    })

@app.route('/api/experiments/export')
def api_export():
    from ont_core import export_registry_csv
    
    registry = Registry()
    format = request.args.get('format', 'json')
    
    if format == 'csv':
        csv_data = export_registry_csv(registry)
        return csv_data, 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': 'attachment; filename=experiments.csv'
        }
    else:
        experiments = [e.to_dict() for e in registry.iter_all()]
        return jsonify({'experiments': experiments})

@app.route('/api/stats')
def api_stats():
    registry = Registry()
    return jsonify(registry.get_stats())

@app.route('/api/public')
def api_public():
    from ont_core import load_config
    datasets = load_config('public_datasets')
    return jsonify(datasets)

# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='ONT Ecosystem Web Dashboard')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to listen on')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║           ONT Ecosystem Web Dashboard                    ║
╠══════════════════════════════════════════════════════════╣
║  URL: http://{args.host}:{args.port}                          
║                                                          ║
║  Press Ctrl+C to stop                                    ║
╚══════════════════════════════════════════════════════════╝
""")
    
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == '__main__':
    main()
