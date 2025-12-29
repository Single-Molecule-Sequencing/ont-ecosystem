#!/usr/bin/env python3
"""
visualize.py - HTML visualization for Great Lakes sync proposals

Generates publication-quality HTML reports with:
- Summary statistics cards
- Color-coded change indicators (new/updated/removed/unchanged)
- Interactive filtering and search
- Diff view for updated experiments
- Responsive grid/table layouts

Part of: https://github.com/Single-Molecule-Sequencing/ont-ecosystem
"""

import argparse
import html
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add script directory to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from proposal import Proposal, ExperimentEntry

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Great Lakes Discovery Proposal - {generated_date}</title>
    <style>
        :root {{
            --color-new: #2e7d32;
            --color-new-bg: #e8f5e9;
            --color-updated: #f57c00;
            --color-updated-bg: #fff3e0;
            --color-removed: #c62828;
            --color-removed-bg: #ffebee;
            --color-unchanged: #9e9e9e;
            --color-unchanged-bg: #f5f5f5;
            --border-radius: 8px;
            --shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #f8f9fa;
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        header {{
            background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
            color: white;
            padding: 30px;
            border-radius: var(--border-radius);
            margin-bottom: 20px;
            box-shadow: var(--shadow);
        }}

        header h1 {{
            font-size: 1.8rem;
            margin-bottom: 10px;
        }}

        .meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            font-size: 0.9rem;
            opacity: 0.9;
        }}

        .meta-item {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }}

        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            text-align: center;
            border-left: 4px solid #ccc;
        }}

        .summary-card.new {{ border-left-color: var(--color-new); }}
        .summary-card.updated {{ border-left-color: var(--color-updated); }}
        .summary-card.removed {{ border-left-color: var(--color-removed); }}
        .summary-card.unchanged {{ border-left-color: var(--color-unchanged); }}
        .summary-card.total {{ border-left-color: #1a237e; }}

        .summary-card .count {{
            font-size: 2.5rem;
            font-weight: 700;
            line-height: 1.2;
        }}

        .summary-card.new .count {{ color: var(--color-new); }}
        .summary-card.updated .count {{ color: var(--color-updated); }}
        .summary-card.removed .count {{ color: var(--color-removed); }}
        .summary-card.unchanged .count {{ color: var(--color-unchanged); }}
        .summary-card.total .count {{ color: #1a237e; }}

        .summary-card .label {{
            font-size: 0.85rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .controls {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 20px;
            padding: 15px;
            background: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
        }}

        .filter-btn {{
            padding: 8px 16px;
            border: 2px solid #ddd;
            border-radius: 20px;
            background: white;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.2s;
        }}

        .filter-btn:hover {{
            border-color: #999;
        }}

        .filter-btn.active {{
            background: #1a237e;
            color: white;
            border-color: #1a237e;
        }}

        .filter-btn.new.active {{ background: var(--color-new); border-color: var(--color-new); }}
        .filter-btn.updated.active {{ background: var(--color-updated); border-color: var(--color-updated); }}
        .filter-btn.removed.active {{ background: var(--color-removed); border-color: var(--color-removed); }}

        .search-box {{
            flex: 1;
            min-width: 200px;
            padding: 8px 16px;
            border: 2px solid #ddd;
            border-radius: 20px;
            font-size: 0.9rem;
        }}

        .search-box:focus {{
            outline: none;
            border-color: #1a237e;
        }}

        .experiments-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
            gap: 15px;
        }}

        .experiment-card {{
            background: white;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            overflow: hidden;
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .experiment-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}

        .experiment-card.new {{ border-left: 4px solid var(--color-new); }}
        .experiment-card.updated {{ border-left: 4px solid var(--color-updated); }}
        .experiment-card.removed {{ border-left: 4px solid var(--color-removed); }}
        .experiment-card.unchanged {{ border-left: 4px solid var(--color-unchanged); }}

        .card-header {{
            padding: 15px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 10px;
        }}

        .experiment-card.new .card-header {{ background: var(--color-new-bg); }}
        .experiment-card.updated .card-header {{ background: var(--color-updated-bg); }}
        .experiment-card.removed .card-header {{ background: var(--color-removed-bg); }}
        .experiment-card.unchanged .card-header {{ background: var(--color-unchanged-bg); }}

        .sample-id {{
            font-weight: 600;
            font-size: 1.1rem;
            word-break: break-all;
        }}

        .change-badge {{
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            white-space: nowrap;
        }}

        .change-badge.new {{ background: var(--color-new); color: white; }}
        .change-badge.updated {{ background: var(--color-updated); color: white; }}
        .change-badge.removed {{ background: var(--color-removed); color: white; }}
        .change-badge.unchanged {{ background: var(--color-unchanged); color: white; }}

        .card-body {{
            padding: 15px;
        }}

        .field {{
            display: flex;
            margin-bottom: 8px;
            font-size: 0.9rem;
        }}

        .field-label {{
            min-width: 100px;
            color: #666;
        }}

        .field-value {{
            flex: 1;
            word-break: break-all;
            font-family: 'SF Mono', 'Consolas', monospace;
            font-size: 0.85rem;
        }}

        .file-counts {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            padding: 10px 15px;
            background: #f8f9fa;
            border-top: 1px solid #eee;
        }}

        .file-count {{
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 0.85rem;
        }}

        .file-count .count {{
            font-weight: 600;
        }}

        .file-count.pod5 .count {{ color: #7b1fa2; }}
        .file-count.fast5 .count {{ color: #0277bd; }}
        .file-count.fastq .count {{ color: #00695c; }}
        .file-count.bam .count {{ color: #c62828; }}

        .changes-list {{
            padding: 10px 15px;
            background: #fff8e1;
            border-top: 1px solid #ffe082;
        }}

        .change-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.85rem;
            padding: 4px 0;
        }}

        .change-field {{
            font-weight: 600;
            min-width: 80px;
        }}

        .change-arrow {{
            color: #999;
        }}

        .change-old {{
            color: var(--color-removed);
            text-decoration: line-through;
        }}

        .change-new {{
            color: var(--color-new);
            font-weight: 600;
        }}

        .removal-reason {{
            padding: 10px 15px;
            background: var(--color-removed-bg);
            border-top: 1px solid #ef9a9a;
            font-size: 0.85rem;
            color: var(--color-removed);
        }}

        .section-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 30px 0 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #ddd;
        }}

        .section-title {{
            font-size: 1.3rem;
            font-weight: 600;
        }}

        .section-count {{
            background: #eee;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.9rem;
        }}

        .empty-state {{
            text-align: center;
            padding: 40px;
            color: #666;
            font-style: italic;
        }}

        .approval-banner {{
            padding: 20px;
            margin-bottom: 20px;
            border-radius: var(--border-radius);
            text-align: center;
        }}

        .approval-banner.pending {{
            background: #fff3e0;
            border: 2px solid var(--color-updated);
        }}

        .approval-banner.approved {{
            background: var(--color-new-bg);
            border: 2px solid var(--color-new);
        }}

        .approval-banner.applied {{
            background: #e3f2fd;
            border: 2px solid #1976d2;
        }}

        footer {{
            margin-top: 40px;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 0.85rem;
        }}

        @media (max-width: 600px) {{
            .experiments-grid {{
                grid-template-columns: 1fr;
            }}

            .summary-cards {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Great Lakes Discovery Proposal</h1>
            <div class="meta">
                <div class="meta-item">
                    <span>Generated:</span>
                    <strong>{generated_at}</strong>
                </div>
                {slurm_meta}
                {duration_meta}
            </div>
        </header>

        {approval_banner}

        <div class="summary-cards">
            <div class="summary-card total">
                <div class="count">{total_discovered}</div>
                <div class="label">Total Discovered</div>
            </div>
            <div class="summary-card new">
                <div class="count">{new_count}</div>
                <div class="label">New</div>
            </div>
            <div class="summary-card updated">
                <div class="count">{updated_count}</div>
                <div class="label">Updated</div>
            </div>
            <div class="summary-card removed">
                <div class="count">{removed_count}</div>
                <div class="label">Removed</div>
            </div>
            <div class="summary-card unchanged">
                <div class="count">{unchanged_count}</div>
                <div class="label">Unchanged</div>
            </div>
        </div>

        <div class="controls">
            <button class="filter-btn active" data-filter="all">All Changes</button>
            <button class="filter-btn new" data-filter="new">New ({new_count})</button>
            <button class="filter-btn updated" data-filter="updated">Updated ({updated_count})</button>
            <button class="filter-btn removed" data-filter="removed">Removed ({removed_count})</button>
            <input type="text" class="search-box" placeholder="Search by sample, flowcell, or path..." id="searchBox">
        </div>

        {sections_html}

        <footer>
            <p>Generated by greatlakes-sync v1.0.0</p>
            <p>ONT Ecosystem - Single Molecule Sequencing Lab</p>
        </footer>
    </div>

    <script>
        // Filter functionality
        document.querySelectorAll('.filter-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                const filter = btn.dataset.filter;

                // Update active button
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                // Filter cards
                document.querySelectorAll('.experiment-card').forEach(card => {{
                    if (filter === 'all' || card.classList.contains(filter)) {{
                        card.style.display = '';
                    }} else {{
                        card.style.display = 'none';
                    }}
                }});

                // Update section visibility
                document.querySelectorAll('.section-header').forEach(header => {{
                    const section = header.nextElementSibling;
                    const visibleCards = section.querySelectorAll('.experiment-card:not([style*="display: none"])');
                    header.style.display = visibleCards.length ? '' : 'none';
                    section.style.display = visibleCards.length ? '' : 'none';
                }});
            }});
        }});

        // Search functionality
        document.getElementById('searchBox').addEventListener('input', (e) => {{
            const query = e.target.value.toLowerCase();

            document.querySelectorAll('.experiment-card').forEach(card => {{
                const text = card.textContent.toLowerCase();
                card.style.display = text.includes(query) ? '' : 'none';
            }});
        }});
    </script>
</body>
</html>
"""


def escape(text: Any) -> str:
    """HTML escape text."""
    return html.escape(str(text) if text else '')


def render_experiment_card(exp: ExperimentEntry, change_type: str) -> str:
    """Render a single experiment card."""
    # Changes list for updated experiments
    changes_html = ""
    if exp.changes:
        changes_items = []
        for change in exp.changes:
            changes_items.append(f"""
                <div class="change-item">
                    <span class="change-field">{escape(change.field)}:</span>
                    <span class="change-old">{escape(change.old_value)}</span>
                    <span class="change-arrow">&rarr;</span>
                    <span class="change-new">{escape(change.new_value)}</span>
                </div>
            """)
        changes_html = f'<div class="changes-list">{"".join(changes_items)}</div>'

    # Removal reason for removed experiments
    removal_html = ""
    if exp.removal_reason:
        removal_html = f'<div class="removal-reason">Reason: {escape(exp.removal_reason)}</div>'

    return f"""
    <div class="experiment-card {change_type}" data-type="{change_type}">
        <div class="card-header">
            <span class="sample-id">{escape(exp.sample_id) or 'Unknown Sample'}</span>
            <span class="change-badge {change_type}">{change_type}</span>
        </div>
        <div class="card-body">
            <div class="field">
                <span class="field-label">Flow Cell:</span>
                <span class="field-value">{escape(exp.flow_cell_id) or 'N/A'}</span>
            </div>
            <div class="field">
                <span class="field-label">Instrument:</span>
                <span class="field-value">{escape(exp.instrument) or 'N/A'}</span>
            </div>
            <div class="field">
                <span class="field-label">Path:</span>
                <span class="field-value">{escape(exp.path)}</span>
            </div>
            <div class="field">
                <span class="field-label">Started:</span>
                <span class="field-value">{escape(exp.started) or 'N/A'}</span>
            </div>
        </div>
        <div class="file-counts">
            <div class="file-count pod5">
                <span>POD5:</span>
                <span class="count">{exp.pod5_files}</span>
            </div>
            <div class="file-count fast5">
                <span>Fast5:</span>
                <span class="count">{exp.fast5_files}</span>
            </div>
            <div class="file-count fastq">
                <span>FASTQ:</span>
                <span class="count">{exp.fastq_files}</span>
            </div>
            <div class="file-count bam">
                <span>BAM:</span>
                <span class="count">{exp.bam_files}</span>
            </div>
        </div>
        {changes_html}
        {removal_html}
    </div>
    """


def render_section(title: str, experiments: List[ExperimentEntry], change_type: str) -> str:
    """Render a section of experiments."""
    if not experiments:
        return ""

    cards_html = "\n".join(
        render_experiment_card(exp, change_type) for exp in experiments
    )

    return f"""
    <div class="section-header">
        <h2 class="section-title">{title}</h2>
        <span class="section-count">{len(experiments)}</span>
    </div>
    <div class="experiments-grid">
        {cards_html}
    </div>
    """


def generate_proposal_html(proposal: Proposal, output_path: Path) -> Path:
    """
    Generate HTML visualization for a proposal.

    Args:
        proposal: Proposal to visualize
        output_path: Path to write HTML file

    Returns:
        Path to generated HTML file
    """
    # Metadata
    generated_date = proposal.generated_at[:10] if proposal.generated_at else 'Unknown'

    slurm_meta = ""
    if proposal.slurm_job_id:
        slurm_meta = f"""
            <div class="meta-item">
                <span>SLURM Job:</span>
                <strong>{escape(proposal.slurm_job_id)}</strong>
            </div>
        """
        if proposal.slurm_node:
            slurm_meta += f"""
                <div class="meta-item">
                    <span>Node:</span>
                    <strong>{escape(proposal.slurm_node)}</strong>
                </div>
            """

    duration_meta = ""
    if proposal.scan_duration_seconds:
        minutes = int(proposal.scan_duration_seconds // 60)
        seconds = int(proposal.scan_duration_seconds % 60)
        duration_meta = f"""
            <div class="meta-item">
                <span>Duration:</span>
                <strong>{minutes}m {seconds}s</strong>
            </div>
        """

    # Approval banner
    approval_banner = ""
    if proposal.approval_status == 'pending':
        approval_banner = """
            <div class="approval-banner pending">
                <strong>Pending Approval</strong> - Review the changes below and run
                <code>greatlakes_sync.py apply --latest</code> to apply.
            </div>
        """
    elif proposal.approval_status == 'approved':
        approved_info = f"Approved by {proposal.approved_by}" if proposal.approved_by else "Approved"
        if proposal.approved_at:
            approved_info += f" on {proposal.approved_at[:10]}"
        approval_banner = f"""
            <div class="approval-banner approved">
                <strong>{approved_info}</strong>
            </div>
        """
    if proposal.applied_at:
        approval_banner = f"""
            <div class="approval-banner applied">
                <strong>Applied</strong> on {proposal.applied_at[:10]}
            </div>
        """

    # Sections
    sections = []
    sections.append(render_section("New Experiments", proposal.new, "new"))
    sections.append(render_section("Updated Experiments", proposal.updated, "updated"))
    sections.append(render_section("Removed Experiments", proposal.removed, "removed"))

    sections_html = "\n".join(s for s in sections if s)

    if not sections_html:
        sections_html = '<div class="empty-state">No changes detected</div>'

    # Render template
    html_content = HTML_TEMPLATE.format(
        generated_date=generated_date,
        generated_at=escape(proposal.generated_at),
        slurm_meta=slurm_meta,
        duration_meta=duration_meta,
        approval_banner=approval_banner,
        total_discovered=proposal.summary.total_discovered,
        new_count=proposal.summary.new_count,
        updated_count=proposal.summary.updated_count,
        removed_count=proposal.summary.removed_count,
        unchanged_count=proposal.summary.unchanged_count,
        sections_html=sections_html,
    )

    # Write file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(html_content)

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Generate HTML visualization for discovery proposal'
    )
    parser.add_argument('--proposal', '-p', required=True,
                        help='Path to proposal YAML file')
    parser.add_argument('--output', '-o',
                        help='Output HTML path (default: same as proposal with .html)')

    args = parser.parse_args()

    proposal_path = Path(args.proposal)
    if not proposal_path.exists():
        print(f"Error: Proposal not found: {proposal_path}")
        return 1

    output_path = Path(args.output) if args.output else proposal_path.with_suffix('.html')

    proposal = Proposal.load(proposal_path)
    generate_proposal_html(proposal, output_path)

    print(f"Generated HTML: {output_path}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
