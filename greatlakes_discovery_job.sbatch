#!/bin/bash
#SBATCH --job-name=ont_discovery
#SBATCH --account=bleu99
#SBATCH --partition=standard
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=08:00:00
#SBATCH --output=/nfs/turbo/umms-atheylab/logs/discovery_%j.out
#SBATCH --error=/nfs/turbo/umms-atheylab/logs/discovery_%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=gregfar@umich.edu

# ============================================
# ONT Experiment Discovery Job - Great Lakes
# Generated: 2025-12-29
# ============================================
#
# Usage: sbatch greatlakes_discovery_job.sbatch
#
# This job will:
# 1. Scan all turbo directories for experiments
# 2. Compare against the current registry
# 3. Generate a proposal YAML and HTML visualization
# 4. Save results for user review
#
# After completion, review the proposal:
#   cat /nfs/turbo/umms-atheylab/.ont-sync/proposals/proposal_latest.yaml
#   # Copy HTML to local machine for viewing
#
# To apply changes, run from your local machine:
#   python3 greatlakes_sync.py apply --latest --commit --push

set -euo pipefail

echo "======================================"
echo "ONT Experiment Discovery Job"
echo "======================================"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "Start Time: $(date)"
echo ""

# Configuration
TURBO_BASE="/nfs/turbo/umms-atheylab"
SYNC_DIR="$TURBO_BASE/.ont-sync"
PROPOSALS_DIR="$SYNC_DIR/proposals"
LOGS_DIR="$TURBO_BASE/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PROPOSAL_PATH="$PROPOSALS_DIR/proposal_$TIMESTAMP.yaml"
HTML_PATH="$PROPOSALS_DIR/proposal_$TIMESTAMP.html"

# Directories to scan
SCAN_DIRS=(
    "/nfs/turbo/umms-atheylab/sequencing_data"
    "/nfs/turbo/umms-atheylab/miamon"
    "/nfs/turbo/umms-atheylab/backup_from_desktop"
    "/nfs/turbo/umms-atheylab/sequencing_data/data_from_linux_desktop_lab"
    "/nfs/turbo/umms-atheylab/sequencing_data/AGC"
)

# Create directories
mkdir -p "$PROPOSALS_DIR"
mkdir -p "$LOGS_DIR"

# Load Python
module load python/3.10 2>/dev/null || module load python3 2>/dev/null || true

# Check Python
python3 --version

# Track timing
START_TIME=$(date +%s)

echo ""
echo "Scanning directories:"
for dir in "${SCAN_DIRS[@]}"; do
    echo "  - $dir"
done
echo ""

# Run discovery
python3 << 'PYTHON_SCRIPT'
import glob
import hashlib
import json
import os
import sys
import html
from datetime import datetime, timezone
from pathlib import Path

# Configuration
SCAN_DIRS = [
    "/nfs/turbo/umms-atheylab/sequencing_data",
    "/nfs/turbo/umms-atheylab/miamon",
    "/nfs/turbo/umms-atheylab/backup_from_desktop",
    "/nfs/turbo/umms-atheylab/sequencing_data/data_from_linux_desktop_lab",
    "/nfs/turbo/umms-atheylab/sequencing_data/AGC",
]

TIMESTAMP = os.environ.get('TIMESTAMP', datetime.now().strftime('%Y%m%d_%H%M%S'))
PROPOSALS_DIR = os.environ.get('PROPOSALS_DIR', '/nfs/turbo/umms-atheylab/.ont-sync/proposals')
PROPOSAL_PATH = f"{PROPOSALS_DIR}/proposal_{TIMESTAMP}.yaml"
HTML_PATH = f"{PROPOSALS_DIR}/proposal_{TIMESTAMP}.html"

# Try to load current registry from GitHub
REGISTRY_URL = "https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/registry/experiments.yaml"

def parse_final_summary(filepath):
    """Parse final_summary.txt file."""
    data = {}
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line:
                    key, value = line.split('=', 1)
                    data[key] = value
    except Exception:
        pass
    return data

def load_registry():
    """Load current registry from GitHub or local copy."""
    experiments = {}

    # Try to fetch from GitHub
    try:
        import urllib.request
        import yaml

        print(f"Fetching registry from GitHub...")
        req = urllib.request.Request(REGISTRY_URL)
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode('utf-8')
            registry = yaml.safe_load(content)

            for exp in registry.get('experiments', []):
                path = exp.get('location') or exp.get('path', '')
                if path:
                    experiments[path] = {
                        'path': path,
                        'sample_id': exp.get('name', ''),
                        'flow_cell_id': exp.get('flowcell_id', ''),
                        'pod5_files': exp.get('pod5_files', 0) or 0,
                        'fast5_files': exp.get('fast5_files', 0) or 0,
                        'fastq_files': exp.get('fastq_files', 0) or 0,
                        'bam_files': exp.get('bam_files', 0) or 0,
                    }
            print(f"Loaded {len(experiments)} experiments from GitHub registry")

    except Exception as e:
        print(f"Warning: Could not load GitHub registry: {e}")
        print("Will treat all discovered experiments as new")

    return experiments

def discover_experiments():
    """Scan directories for experiments."""
    experiments = []
    seen = set()

    for scan_dir in SCAN_DIRS:
        if not os.path.isdir(scan_dir):
            print(f"Skipping non-existent: {scan_dir}")
            continue

        print(f"\nScanning: {scan_dir}")

        # Find final_summary files
        pattern = os.path.join(scan_dir, '**', 'final_summary*.txt')
        summaries = glob.glob(pattern, recursive=True)
        print(f"  Found {len(summaries)} summary files")

        for summary_path in summaries:
            exp_dir = os.path.dirname(summary_path)
            if exp_dir in seen:
                continue
            seen.add(exp_dir)

            metadata = parse_final_summary(Path(summary_path))

            # Count files
            pod5_count = len(glob.glob(os.path.join(exp_dir, '**', '*.pod5'), recursive=True))
            fast5_count = len(glob.glob(os.path.join(exp_dir, '**', '*.fast5'), recursive=True))
            fastq_count = len(glob.glob(os.path.join(exp_dir, '**', '*.fastq*'), recursive=True))
            bam_count = len(glob.glob(os.path.join(exp_dir, '**', '*.bam'), recursive=True))

            exp_id = hashlib.md5(exp_dir.encode()).hexdigest()[:12]

            experiments.append({
                'id': exp_id,
                'path': exp_dir,
                'sample_id': metadata.get('sample_id', ''),
                'flow_cell_id': metadata.get('flow_cell_id', ''),
                'protocol_group_id': metadata.get('protocol_group_id', ''),
                'protocol': metadata.get('protocol', ''),
                'instrument': metadata.get('instrument', ''),
                'started': metadata.get('started', ''),
                'acquisition_stopped': metadata.get('acquisition_stopped', ''),
                'pod5_files': pod5_count,
                'fast5_files': fast5_count,
                'fastq_files': fastq_count,
                'bam_files': bam_count,
                'discovered_at': datetime.now(timezone.utc).isoformat(),
            })

            sample = metadata.get('sample_id', 'unknown')
            if len(sample) > 30:
                sample = sample[:27] + '...'
            print(f"    {sample} ({metadata.get('flow_cell_id', 'N/A')})")

    return experiments

def compare_experiments(discovered, current):
    """Compare discovered vs current registry."""
    new_exps = []
    updated_exps = []
    unchanged_exps = []

    for exp in discovered:
        path = exp['path']
        if path not in current:
            new_exps.append(exp)
        else:
            curr = current[path]
            changes = []
            for field in ['pod5_files', 'fastq_files', 'bam_files']:
                old_val = curr.get(field, 0) or 0
                new_val = exp.get(field, 0) or 0
                if old_val != new_val:
                    changes.append({
                        'field': field,
                        'old_value': old_val,
                        'new_value': new_val,
                    })
            if changes:
                exp['changes'] = changes
                updated_exps.append(exp)
            else:
                unchanged_exps.append(exp)

    # Check for removed
    removed_exps = []
    discovered_paths = set(e['path'] for e in discovered)
    for path, curr in current.items():
        if path not in discovered_paths:
            if not os.path.isdir(path):
                removed_exps.append({
                    'path': path,
                    'sample_id': curr.get('sample_id', ''),
                    'removal_reason': 'directory_not_found',
                })

    return new_exps, updated_exps, removed_exps, unchanged_exps

def generate_html(proposal):
    """Generate HTML visualization."""
    def escape(text):
        return html.escape(str(text) if text else '')

    def render_card(exp, change_type):
        sample = exp.get('sample_id') or exp.get('protocol_group_id') or 'Unknown'
        changes_html = ""
        if exp.get('changes'):
            changes_items = []
            for c in exp['changes']:
                changes_items.append(f'''
                    <div class="change-item">
                        <span class="change-field">{escape(c["field"])}:</span>
                        <span class="change-old">{c["old_value"]}</span>
                        <span>→</span>
                        <span class="change-new">{c["new_value"]}</span>
                    </div>
                ''')
            changes_html = f'<div class="changes-list">{"".join(changes_items)}</div>'

        removal_html = ""
        if exp.get('removal_reason'):
            removal_html = f'<div class="removal-reason">Reason: {escape(exp["removal_reason"])}</div>'

        return f'''
        <div class="experiment-card {change_type}">
            <div class="card-header">
                <span class="sample-id">{escape(sample)}</span>
                <span class="change-badge {change_type}">{change_type.upper()}</span>
            </div>
            <div class="card-body">
                <div class="field"><span class="field-label">Flow Cell:</span><span class="field-value">{escape(exp.get("flow_cell_id", "N/A"))}</span></div>
                <div class="field"><span class="field-label">Instrument:</span><span class="field-value">{escape(exp.get("instrument", "N/A"))}</span></div>
                <div class="field"><span class="field-label">Path:</span><span class="field-value">{escape(exp.get("path", ""))}</span></div>
                <div class="field"><span class="field-label">Started:</span><span class="field-value">{escape(exp.get("started", "N/A"))}</span></div>
            </div>
            <div class="file-counts">
                <div class="file-count pod5">POD5: <strong>{exp.get("pod5_files", 0)}</strong></div>
                <div class="file-count fast5">Fast5: <strong>{exp.get("fast5_files", 0)}</strong></div>
                <div class="file-count fastq">FASTQ: <strong>{exp.get("fastq_files", 0)}</strong></div>
                <div class="file-count bam">BAM: <strong>{exp.get("bam_files", 0)}</strong></div>
            </div>
            {changes_html}
            {removal_html}
        </div>
        '''

    new_cards = ''.join(render_card(e, 'new') for e in proposal['changes']['new'])
    updated_cards = ''.join(render_card(e, 'updated') for e in proposal['changes']['updated'])
    removed_cards = ''.join(render_card(e, 'removed') for e in proposal['changes']['removed'])

    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Great Lakes Discovery - {proposal["generated_at"][:10]}</title>
    <style>
        :root {{
            --color-new: #2e7d32; --color-new-bg: #e8f5e9;
            --color-updated: #f57c00; --color-updated-bg: #fff3e0;
            --color-removed: #c62828; --color-removed-bg: #ffebee;
            --color-unchanged: #9e9e9e;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8f9fa; color: #333; line-height: 1.6; padding: 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        header {{ background: linear-gradient(135deg, #1a237e 0%, #283593 100%); color: white; padding: 30px; border-radius: 8px; margin-bottom: 20px; }}
        header h1 {{ font-size: 1.8rem; margin-bottom: 10px; }}
        .meta {{ display: flex; flex-wrap: wrap; gap: 20px; font-size: 0.9rem; opacity: 0.9; }}
        .summary-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 25px; }}
        .summary-card {{ background: white; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 4px solid #ccc; }}
        .summary-card.new {{ border-left-color: var(--color-new); }}
        .summary-card.updated {{ border-left-color: var(--color-updated); }}
        .summary-card.removed {{ border-left-color: var(--color-removed); }}
        .summary-card.total {{ border-left-color: #1a237e; }}
        .summary-card .count {{ font-size: 2.5rem; font-weight: 700; line-height: 1.2; }}
        .summary-card.new .count {{ color: var(--color-new); }}
        .summary-card.updated .count {{ color: var(--color-updated); }}
        .summary-card.removed .count {{ color: var(--color-removed); }}
        .summary-card.total .count {{ color: #1a237e; }}
        .summary-card .label {{ font-size: 0.85rem; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }}
        .controls {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; padding: 15px; background: white; border-radius: 8px; }}
        .filter-btn {{ padding: 8px 16px; border: 2px solid #ddd; border-radius: 20px; background: white; cursor: pointer; font-size: 0.9rem; }}
        .filter-btn:hover {{ border-color: #999; }}
        .filter-btn.active {{ background: #1a237e; color: white; border-color: #1a237e; }}
        .filter-btn.new.active {{ background: var(--color-new); border-color: var(--color-new); }}
        .filter-btn.updated.active {{ background: var(--color-updated); border-color: var(--color-updated); }}
        .filter-btn.removed.active {{ background: var(--color-removed); border-color: var(--color-removed); }}
        .search-box {{ flex: 1; min-width: 200px; padding: 8px 16px; border: 2px solid #ddd; border-radius: 20px; font-size: 0.9rem; }}
        .search-box:focus {{ outline: none; border-color: #1a237e; }}
        .experiments-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 15px; }}
        .experiment-card {{ background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow: hidden; transition: transform 0.2s; }}
        .experiment-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
        .experiment-card.new {{ border-left: 4px solid var(--color-new); }}
        .experiment-card.updated {{ border-left: 4px solid var(--color-updated); }}
        .experiment-card.removed {{ border-left: 4px solid var(--color-removed); }}
        .card-header {{ padding: 15px; display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }}
        .experiment-card.new .card-header {{ background: var(--color-new-bg); }}
        .experiment-card.updated .card-header {{ background: var(--color-updated-bg); }}
        .experiment-card.removed .card-header {{ background: var(--color-removed-bg); }}
        .sample-id {{ font-weight: 600; font-size: 1.1rem; word-break: break-all; }}
        .change-badge {{ padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; white-space: nowrap; }}
        .change-badge.new {{ background: var(--color-new); color: white; }}
        .change-badge.updated {{ background: var(--color-updated); color: white; }}
        .change-badge.removed {{ background: var(--color-removed); color: white; }}
        .card-body {{ padding: 15px; }}
        .field {{ display: flex; margin-bottom: 8px; font-size: 0.9rem; }}
        .field-label {{ min-width: 100px; color: #666; }}
        .field-value {{ flex: 1; word-break: break-all; font-family: 'SF Mono', 'Consolas', monospace; font-size: 0.85rem; }}
        .file-counts {{ display: flex; gap: 15px; flex-wrap: wrap; padding: 10px 15px; background: #f8f9fa; border-top: 1px solid #eee; }}
        .file-count {{ display: flex; align-items: center; gap: 5px; font-size: 0.85rem; }}
        .file-count.pod5 strong {{ color: #7b1fa2; }}
        .file-count.fast5 strong {{ color: #0277bd; }}
        .file-count.fastq strong {{ color: #00695c; }}
        .file-count.bam strong {{ color: #c62828; }}
        .changes-list {{ padding: 10px 15px; background: #fff8e1; border-top: 1px solid #ffe082; }}
        .change-item {{ display: flex; align-items: center; gap: 8px; font-size: 0.85rem; padding: 4px 0; }}
        .change-field {{ font-weight: 600; min-width: 80px; }}
        .change-old {{ color: var(--color-removed); text-decoration: line-through; }}
        .change-new {{ color: var(--color-new); font-weight: 600; }}
        .removal-reason {{ padding: 10px 15px; background: var(--color-removed-bg); border-top: 1px solid #ef9a9a; font-size: 0.85rem; color: var(--color-removed); }}
        .section-header {{ display: flex; align-items: center; gap: 10px; margin: 30px 0 15px; padding-bottom: 10px; border-bottom: 2px solid #ddd; }}
        .section-title {{ font-size: 1.3rem; font-weight: 600; }}
        .section-count {{ background: #eee; padding: 4px 12px; border-radius: 12px; font-size: 0.9rem; }}
        .approval-banner {{ padding: 20px; margin-bottom: 20px; border-radius: 8px; text-align: center; background: #fff3e0; border: 2px solid var(--color-updated); }}
        footer {{ margin-top: 40px; padding: 20px; text-align: center; color: #666; font-size: 0.85rem; }}
        @media (max-width: 600px) {{ .experiments-grid {{ grid-template-columns: 1fr; }} .summary-cards {{ grid-template-columns: repeat(2, 1fr); }} }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Great Lakes Discovery Proposal</h1>
            <div class="meta">
                <div><span>Generated:</span> <strong>{escape(proposal["generated_at"])}</strong></div>
                <div><span>SLURM Job:</span> <strong>{escape(proposal["slurm_job_id"])}</strong></div>
                <div><span>Node:</span> <strong>{escape(proposal["slurm_node"])}</strong></div>
                <div><span>Duration:</span> <strong>{proposal["scan_duration_seconds"]:.1f}s</strong></div>
            </div>
        </header>

        <div class="approval-banner">
            <strong>Pending Approval</strong> - Review the changes below and run
            <code>greatlakes_sync.py apply --latest</code> to apply.
        </div>

        <div class="summary-cards">
            <div class="summary-card total"><div class="count">{proposal["summary"]["total_discovered"]}</div><div class="label">Total Discovered</div></div>
            <div class="summary-card new"><div class="count">{proposal["summary"]["new_count"]}</div><div class="label">New</div></div>
            <div class="summary-card updated"><div class="count">{proposal["summary"]["updated_count"]}</div><div class="label">Updated</div></div>
            <div class="summary-card removed"><div class="count">{proposal["summary"]["removed_count"]}</div><div class="label">Removed</div></div>
        </div>

        <div class="controls">
            <button class="filter-btn active" onclick="filterCards('all')">All Changes</button>
            <button class="filter-btn new" onclick="filterCards('new')">New ({proposal["summary"]["new_count"]})</button>
            <button class="filter-btn updated" onclick="filterCards('updated')">Updated ({proposal["summary"]["updated_count"]})</button>
            <button class="filter-btn removed" onclick="filterCards('removed')">Removed ({proposal["summary"]["removed_count"]})</button>
            <input type="text" class="search-box" placeholder="Search by sample, flowcell, or path..." onkeyup="searchCards(this.value)">
        </div>

        <div class="section-header" data-section="new"><h2 class="section-title">New Experiments</h2><span class="section-count">{proposal["summary"]["new_count"]}</span></div>
        <div class="experiments-grid">{new_cards if new_cards else '<p style="color:#666;padding:20px;">No new experiments</p>'}</div>

        <div class="section-header" data-section="updated"><h2 class="section-title">Updated Experiments</h2><span class="section-count">{proposal["summary"]["updated_count"]}</span></div>
        <div class="experiments-grid">{updated_cards if updated_cards else '<p style="color:#666;padding:20px;">No updated experiments</p>'}</div>

        <div class="section-header" data-section="removed"><h2 class="section-title">Removed Experiments</h2><span class="section-count">{proposal["summary"]["removed_count"]}</span></div>
        <div class="experiments-grid">{removed_cards if removed_cards else '<p style="color:#666;padding:20px;">No removed experiments</p>'}</div>

        <footer>
            <p>Generated by greatlakes-sync v1.0.0</p>
            <p>ONT Ecosystem - Single Molecule Sequencing Lab</p>
        </footer>
    </div>

    <script>
        function filterCards(type) {{
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');
            document.querySelectorAll('.experiment-card').forEach(card => {{
                card.style.display = (type === 'all' || card.classList.contains(type)) ? '' : 'none';
            }});
        }}
        function searchCards(query) {{
            query = query.toLowerCase();
            document.querySelectorAll('.experiment-card').forEach(card => {{
                card.style.display = card.textContent.toLowerCase().includes(query) ? '' : 'none';
            }});
        }}
    </script>
</body>
</html>'''

    return html_content

# Main execution
print("=" * 60)
print("ONT Experiment Discovery")
print("=" * 60)
print(f"Time: {datetime.now(timezone.utc).isoformat()}")
print(f"SLURM Job: {os.environ.get('SLURM_JOB_ID', 'N/A')}")
print(f"Node: {os.environ.get('SLURM_NODELIST', 'N/A')}")
print()

# Load current registry
current_registry = load_registry()

# Discover experiments
start_time = datetime.now()
experiments = discover_experiments()
end_time = datetime.now()
scan_duration = (end_time - start_time).total_seconds()

print(f"\n{'=' * 60}")
print(f"Discovery Complete")
print(f"{'=' * 60}")
print(f"Discovered: {len(experiments)} experiments")
print(f"Duration: {scan_duration:.1f}s")

# Compare
new_exps, updated_exps, removed_exps, unchanged_exps = compare_experiments(experiments, current_registry)

print(f"\nChanges:")
print(f"  New:       {len(new_exps)}")
print(f"  Updated:   {len(updated_exps)}")
print(f"  Removed:   {len(removed_exps)}")
print(f"  Unchanged: {len(unchanged_exps)}")

# Create proposal
proposal = {
    'version': '1.0',
    'generated_at': datetime.now(timezone.utc).isoformat(),
    'slurm_job_id': os.environ.get('SLURM_JOB_ID', ''),
    'slurm_node': os.environ.get('SLURM_NODELIST', ''),
    'scan_duration_seconds': scan_duration,
    'scan_paths': SCAN_DIRS,
    'summary': {
        'total_discovered': len(experiments),
        'current_in_registry': len(current_registry),
        'new_count': len(new_exps),
        'updated_count': len(updated_exps),
        'removed_count': len(removed_exps),
        'unchanged_count': len(unchanged_exps),
    },
    'changes': {
        'new': new_exps,
        'updated': updated_exps,
        'removed': removed_exps,
    },
    'approval_status': 'pending',
}

# Save proposal YAML
try:
    import yaml
    os.makedirs(os.path.dirname(PROPOSAL_PATH), exist_ok=True)
    with open(PROPOSAL_PATH, 'w') as f:
        yaml.dump(proposal, f, default_flow_style=False, sort_keys=False)
    print(f"\nProposal saved: {PROPOSAL_PATH}")
except Exception as e:
    print(f"Warning: Could not save YAML: {e}")
    # Fallback to JSON
    import json
    json_path = PROPOSAL_PATH.replace('.yaml', '.json')
    with open(json_path, 'w') as f:
        json.dump(proposal, f, indent=2)
    print(f"Proposal saved as JSON: {json_path}")

# Save HTML
html_content = generate_html(proposal)
with open(HTML_PATH, 'w') as f:
    f.write(html_content)
print(f"HTML report: {HTML_PATH}")

# Create latest symlink
latest_yaml = os.path.join(os.path.dirname(PROPOSAL_PATH), 'proposal_latest.yaml')
latest_html = os.path.join(os.path.dirname(HTML_PATH), 'proposal_latest.html')
try:
    if os.path.exists(latest_yaml):
        os.unlink(latest_yaml)
    os.symlink(os.path.basename(PROPOSAL_PATH), latest_yaml)
    if os.path.exists(latest_html):
        os.unlink(latest_html)
    os.symlink(os.path.basename(HTML_PATH), latest_html)
    print(f"Latest symlinks updated")
except Exception as e:
    print(f"Note: Could not create symlinks: {e}")

print()
print("=" * 60)
print("NEXT STEPS")
print("=" * 60)
print("1. Review the proposal:")
print(f"   cat {PROPOSAL_PATH}")
print()
print("2. Copy HTML to local machine:")
print(f"   scp greatlakes:{HTML_PATH} .")
print()
print("3. To apply changes:")
print("   python3 greatlakes_sync.py apply --latest --commit --push")
PYTHON_SCRIPT

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "======================================"
echo "Job Complete"
echo "======================================"
echo "Total Duration: ${DURATION}s"
echo "End Time: $(date)"
