#!/usr/bin/env python3
"""
Generate Interactive HTML Montage for Nanopore Experiments
Uses Chart.js for visualizations - no matplotlib/numpy required.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = "/nfs/turbo/umms-atheylab/nanopore_experiments.db"
OUTPUT_DIR = "/nfs/turbo/umms-atheylab/experiment_montage"

def get_data_from_db():
    """Get experiment data from SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get experiment summaries with stats
    cursor.execute('''
        SELECT
            e.id,
            e.sample_id,
            e.protocol_group_id,
            e.flow_cell_id,
            e.instrument,
            e.started,
            r.total_reads,
            r.total_bases,
            r.mean_qscore,
            r.n50,
            r.mean_read_length,
            r.max_read_length,
            e.data_root
        FROM experiments e
        LEFT JOIN read_statistics r ON e.id = r.experiment_id
        WHERE r.total_reads > 0
        ORDER BY r.total_reads DESC
    ''')
    experiments = cursor.fetchall()

    # Get aggregate end reasons
    cursor.execute('''
        SELECT end_reason, SUM(count) as total_count
        FROM end_reason_distribution
        GROUP BY end_reason
        ORDER BY total_count DESC
    ''')
    end_reasons = cursor.fetchall()

    # Get summary stats
    cursor.execute("SELECT COUNT(*) FROM experiments")
    total_experiments = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(total_reads), SUM(total_bases) FROM read_statistics")
    totals = cursor.fetchone()
    total_reads = totals[0] or 0
    total_bases = totals[1] or 0

    conn.close()

    return {
        'experiments': experiments,
        'end_reasons': end_reasons,
        'total_experiments': total_experiments,
        'total_reads': total_reads,
        'total_bases': total_bases
    }

def generate_html(data):
    """Generate HTML montage with Chart.js visualizations."""

    experiments = data['experiments']
    end_reasons = data['end_reasons']

    # Prepare end reason data for pie chart
    end_reason_labels = [er[0] for er in end_reasons]
    end_reason_values = [er[1] for er in end_reasons]
    total_end = sum(end_reason_values)
    end_reason_percentages = [round(v/total_end*100, 2) for v in end_reason_values]

    # Prepare experiment data for charts (top 30)
    top_experiments = experiments[:30]
    exp_labels = [f"{e[1] or 'N/A'}"[:20] for e in top_experiments]
    exp_reads = [e[6] or 0 for e in top_experiments]
    exp_bases = [(e[7] or 0) / 1e9 for e in top_experiments]  # In Gb
    exp_qscores = [e[8] or 0 for e in top_experiments]
    exp_n50s = [(e[9] or 0) / 1000 for e in top_experiments]  # In kb

    # Generate colors for end reasons
    colors = [
        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
        '#9966FF', '#FF9F40', '#E7E9ED', '#7C4DFF'
    ]

    # Pre-generate table rows
    table_rows = []
    for e in experiments:
        reads_str = f"{e[6]:,}" if e[6] else "0"
        bases_str = f"{(e[7] or 0)/1e9:.2f}"
        qscore_str = f"{e[8]:.1f}" if e[8] else "N/A"
        n50_str = f"{e[9]/1000:.1f}" if e[9] else "N/A"
        max_read_str = f"{e[11]/1000:.1f}" if e[11] else "N/A"
        table_rows.append(f'''<tr>
            <td>{e[1] or 'N/A'}</td>
            <td>{e[2] or 'N/A'}</td>
            <td>{e[3] or 'N/A'}</td>
            <td>{e[4] or 'N/A'}</td>
            <td class="read-count">{reads_str}</td>
            <td class="bases-count">{bases_str}</td>
            <td class="qscore">{qscore_str}</td>
            <td>{n50_str}</td>
            <td>{max_read_str}</td>
        </tr>''')
    table_html = '\n'.join(table_rows)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nanopore Experiments Montage - Athey Lab</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1800px; margin: 0 auto; }}
        h1 {{
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #00d4ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .subtitle {{
            text-align: center;
            color: #888;
            margin-bottom: 30px;
            font-size: 1.1em;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            background: linear-gradient(90deg, #00d4ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .stat-label {{ color: #888; margin-top: 5px; }}
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .chart-container {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .chart-title {{
            font-size: 1.2em;
            margin-bottom: 15px;
            color: #00d4ff;
        }}
        canvas {{ max-width: 100%; }}
        .table-container {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
            overflow-x: auto;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        th {{
            background: rgba(0,212,255,0.2);
            font-weight: 600;
        }}
        tr:hover {{ background: rgba(255,255,255,0.05); }}
        .read-count {{ color: #00ff88; font-weight: bold; }}
        .bases-count {{ color: #00d4ff; }}
        .qscore {{ color: #ffce56; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Nanopore Experiments Montage</h1>
        <p class="subtitle">Athey Lab - University of Michigan | Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{data['total_experiments']}</div>
                <div class="stat-label">Total Experiments</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{data['total_reads']:,}</div>
                <div class="stat-label">Total Reads</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{data['total_bases']/1e9:.1f} Gb</div>
                <div class="stat-label">Total Bases</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len([e for e in experiments if (e[8] or 0) >= 20])}</div>
                <div class="stat-label">High Quality (Q≥20)</div>
            </div>
        </div>

        <div class="charts-grid">
            <div class="chart-container">
                <div class="chart-title">End Reason Distribution</div>
                <canvas id="endReasonChart"></canvas>
            </div>
            <div class="chart-container">
                <div class="chart-title">Top 30 Experiments by Read Count</div>
                <canvas id="readsChart"></canvas>
            </div>
            <div class="chart-container">
                <div class="chart-title">Quality Score Distribution (Top 30)</div>
                <canvas id="qscoreChart"></canvas>
            </div>
            <div class="chart-container">
                <div class="chart-title">Total Bases per Experiment (Top 30, Gb)</div>
                <canvas id="basesChart"></canvas>
            </div>
        </div>

        <div class="table-container">
            <div class="chart-title">All Experiments ({len(experiments)} with data)</div>
            <table>
                <thead>
                    <tr>
                        <th>Sample ID</th>
                        <th>Protocol Group</th>
                        <th>Flow Cell</th>
                        <th>Instrument</th>
                        <th>Reads</th>
                        <th>Bases (Gb)</th>
                        <th>Mean Q</th>
                        <th>N50 (kb)</th>
                        <th>Max Read (kb)</th>
                    </tr>
                </thead>
                <tbody>
                    {table_html}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        // End Reason Pie Chart
        new Chart(document.getElementById('endReasonChart'), {{
            type: 'doughnut',
            data: {{
                labels: {end_reason_labels},
                datasets: [{{
                    data: {end_reason_percentages},
                    backgroundColor: {colors[:len(end_reasons)]},
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        position: 'right',
                        labels: {{ color: '#eee', font: {{ size: 11 }} }}
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return context.label + ': ' + context.parsed + '%';
                            }}
                        }}
                    }}
                }}
            }}
        }});

        // Reads Bar Chart
        new Chart(document.getElementById('readsChart'), {{
            type: 'bar',
            data: {{
                labels: {exp_labels},
                datasets: [{{
                    label: 'Reads (millions)',
                    data: {[round(r/1e6, 2) for r in exp_reads]},
                    backgroundColor: 'rgba(0, 255, 136, 0.6)',
                    borderColor: 'rgba(0, 255, 136, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                indexAxis: 'y',
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    x: {{
                        ticks: {{ color: '#888' }},
                        grid: {{ color: 'rgba(255,255,255,0.1)' }}
                    }},
                    y: {{
                        ticks: {{ color: '#888', font: {{ size: 10 }} }},
                        grid: {{ display: false }}
                    }}
                }}
            }}
        }});

        // Q-Score Bar Chart
        new Chart(document.getElementById('qscoreChart'), {{
            type: 'bar',
            data: {{
                labels: {exp_labels},
                datasets: [{{
                    label: 'Mean Q-Score',
                    data: {[round(q, 1) for q in exp_qscores]},
                    backgroundColor: {['rgba(255, 99, 132, 0.6)' if q < 15 else 'rgba(255, 206, 86, 0.6)' if q < 20 else 'rgba(0, 255, 136, 0.6)' for q in exp_qscores]},
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                indexAxis: 'y',
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    x: {{
                        ticks: {{ color: '#888' }},
                        grid: {{ color: 'rgba(255,255,255,0.1)' }},
                        min: 0,
                        max: 30
                    }},
                    y: {{
                        ticks: {{ color: '#888', font: {{ size: 10 }} }},
                        grid: {{ display: false }}
                    }}
                }}
            }}
        }});

        // Bases Bar Chart
        new Chart(document.getElementById('basesChart'), {{
            type: 'bar',
            data: {{
                labels: {exp_labels},
                datasets: [{{
                    label: 'Total Bases (Gb)',
                    data: {[round(b, 2) for b in exp_bases]},
                    backgroundColor: 'rgba(0, 212, 255, 0.6)',
                    borderColor: 'rgba(0, 212, 255, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                indexAxis: 'y',
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    x: {{
                        ticks: {{ color: '#888' }},
                        grid: {{ color: 'rgba(255,255,255,0.1)' }}
                    }},
                    y: {{
                        ticks: {{ color: '#888', font: {{ size: 10 }} }},
                        grid: {{ display: false }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
'''
    return html

def main():
    print("Generating Experiment Montage...")

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Get data from database
    data = get_data_from_db()
    print(f"Found {data['total_experiments']} experiments")
    print(f"Total reads: {data['total_reads']:,}")
    print(f"Total bases: {data['total_bases']/1e9:.2f} Gb")

    # Generate HTML
    html = generate_html(data)

    # Write output
    output_file = os.path.join(OUTPUT_DIR, "experiment_montage.html")
    with open(output_file, 'w') as f:
        f.write(html)

    print(f"\nMontage saved to: {output_file}")
    print("Open in a web browser to view the interactive visualizations.")

if __name__ == "__main__":
    main()
