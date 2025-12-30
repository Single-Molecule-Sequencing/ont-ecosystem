#!/usr/bin/env python3
"""
Comprehensive visualization of peaks and molecular products for ALL SMA-seq experiments.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np

# All experiment data from analysis
EXPERIMENTS = [
    {
        "name": "12282025_IF_DoubleBC",
        "short": "Dec 28\nDouble BC",
        "date": "2025-12-28",
        "status": "clean",
        "n50": 149,
        "mean_q": 11.9,
        "reads": 1445165,
        "bases_mb": 173.9,
        "targets": ["V0-4.2", "V0-4.4"],
        "protocol": "Odd/even fix\n(even only)",
        "color": "#27ae60",
        "peaks": [(149, 0.95, "Clean")],
    },
    {
        "name": "12232025_IF_DoubleBC",
        "short": "Dec 23\nDouble BC",
        "date": "2025-12-23",
        "status": "daisy_chains",
        "n50": 2613,
        "mean_q": 14.1,
        "reads": 12074175,
        "bases_mb": 24645.7,
        "targets": ["V0-4.1", "V0-4.2", "V0-4.3", "V0-4.4", "V0-39"],
        "protocol": "Cleavage-ligation\ncycling",
        "color": "#f39c12",
        "peaks": [(150, 0.30, "Clean"), (2600, 0.60, "Daisy"), (5200, 0.10, "Multi")],
    },
    {
        "name": "11242025_IF_Part4",
        "short": "Nov 24\nPart4",
        "date": "2025-11-24",
        "status": "daisy_chains",
        "n50": 2639,
        "mean_q": 15.6,
        "reads": 20062441,
        "bases_mb": 30370.5,
        "targets": ["V0-4.1-4.4", "V0-39-47", "V0-4.14-17"],
        "protocol": "Standard\n5-step",
        "color": "#f39c12",
        "peaks": [(150, 0.30, "Clean"), (2600, 0.60, "Daisy"), (5200, 0.10, "Multi")],
    },
    {
        "name": "12082025_IF_NewBCPart4",
        "short": "Dec 8\nNew BC",
        "date": "2025-12-08",
        "status": "severe",
        "n50": 5400,
        "mean_q": 12.2,
        "reads": 4688237,
        "bases_mb": 18807.3,
        "targets": ["V0-4.1", "V0-4.2", "V0-4.3", "V0-4.4", "V0-39"],
        "protocol": "New barcode\n3-step",
        "color": "#e74c3c",
        "peaks": [(150, 0.15, "Clean"), (2800, 0.35, "Daisy"), (5400, 0.35, "Multi"), (8000, 0.15, "Triple")],
    },
    {
        "name": "12182025_Ex1",
        "short": "Dec 18\nEx1",
        "date": "2025-12-18",
        "status": "anomalous",
        "n50": 116800,
        "mean_q": 6.7,
        "reads": 3228363,
        "bases_mb": 1829.9,
        "targets": ["V0-4.1-4.4", "V0-39"],
        "protocol": "Hi-T4\nLigase",
        "color": "#8e44ad",
        "peaks": [(200, 0.05, "Clean"), (5000, 0.15, "Plasmid"), (100000, 0.80, "HMW")],
    },
    {
        "name": "12182025_Ex2",
        "short": "Dec 18\nEx2",
        "date": "2025-12-18",
        "status": "anomalous",
        "n50": 332500,
        "mean_q": 6.3,
        "reads": 1784271,
        "bases_mb": 2547.9,
        "targets": ["V0-4.1-4.4", "V0-39"],
        "protocol": "Immobilized\nT4 Ligase",
        "color": "#8e44ad",
        "peaks": [(200, 0.05, "Clean"), (5000, 0.10, "Plasmid"), (150000, 0.85, "HMW")],
    },
    {
        "name": "12182025_Ex3",
        "short": "Dec 18\nEx3",
        "date": "2025-12-18",
        "status": "anomalous",
        "n50": 140100,
        "mean_q": 7.0,
        "reads": 2200586,
        "bases_mb": 3852.8,
        "targets": ["V0-4.1-4.4", "V0-39"],
        "protocol": "Separate\ntubes pooled",
        "color": "#8e44ad",
        "peaks": [(200, 0.05, "Clean"), (5000, 0.15, "Plasmid"), (120000, 0.80, "HMW")],
    },
    {
        "name": "11242025_CIP",
        "short": "Nov 24\nCIP",
        "date": "2025-11-24",
        "status": "failed",
        "n50": 0,
        "mean_q": 0,
        "reads": 0,
        "bases_mb": 0,
        "targets": ["V0-4.1-4.4", "V0-39-47"],
        "protocol": "CIP-treated\nadapter",
        "color": "#7f8c8d",
        "peaks": [],
    },
]

# Product definitions
PRODUCTS = {
    "Clean": {
        "range": "100-260 bp",
        "structure": "PREFIX + ADAPTER + FLANK + BARCODE + FLANK + TARGET",
        "color": "#27ae60",
        "status": "Expected"
    },
    "Daisy": {
        "range": "2.3-3.0 kb",
        "structure": "TARGET_A + BACKBONE (~2kb) + TARGET_B",
        "color": "#e74c3c",
        "status": "Artifact"
    },
    "Multi": {
        "range": "4.5-8.0 kb",
        "structure": "T + BB + T + BB + T...",
        "color": "#c0392b",
        "status": "Artifact"
    },
    "Triple": {
        "range": "8-12 kb",
        "structure": "Multiple concatenations",
        "color": "#922b21",
        "status": "Artifact"
    },
    "Plasmid": {
        "range": "4-10 kb",
        "structure": "Circular/linear plasmid",
        "color": "#f39c12",
        "status": "Contamination"
    },
    "HMW": {
        "range": ">100 kb",
        "structure": "Genomic DNA / concatemers",
        "color": "#8e44ad",
        "status": "Failed"
    },
}


def create_comprehensive_figure():
    """Create comprehensive multi-panel figure."""
    fig = plt.figure(figsize=(20, 16))

    # Grid layout
    gs = fig.add_gridspec(4, 3, height_ratios=[1.5, 1.5, 1, 0.8],
                          width_ratios=[1, 1, 1], hspace=0.35, wspace=0.3)

    # =========================================================================
    # Row 1: Individual experiment distributions (simulated based on peaks)
    # =========================================================================

    x = np.linspace(10, 500000, 2000)
    x_log = np.log10(x)

    for idx, exp in enumerate(EXPERIMENTS[:3]):
        ax = fig.add_subplot(gs[0, idx])

        # Generate distribution from peaks
        y = np.zeros_like(x)
        for peak_center, peak_frac, peak_type in exp["peaks"]:
            sigma = peak_center * 0.15  # 15% width
            y += peak_frac * np.exp(-((x - peak_center)**2) / (2 * sigma**2))

        ax.fill_between(x, y, alpha=0.6, color=exp["color"])
        ax.plot(x, y, color=exp["color"], linewidth=2)

        # Mark N50
        ax.axvline(exp["n50"], color='black', linestyle='--', linewidth=1.5, label=f'N50={exp["n50"]:,}bp')

        ax.set_xscale('log')
        ax.set_xlim(50, 300000)
        ax.set_ylim(0, max(y) * 1.2 if len(y) > 0 and max(y) > 0 else 1)
        ax.set_xlabel('Read Length (bp)')
        ax.set_ylabel('Density')
        ax.set_title(f'{exp["short"]}\nN50={exp["n50"]:,}bp, Q{exp["mean_q"]}',
                    fontsize=11, fontweight='bold', color=exp["color"])
        ax.legend(loc='upper right', fontsize=8)

        # Add peak labels
        for peak_center, peak_frac, peak_type in exp["peaks"]:
            if peak_frac >= 0.1:
                ax.annotate(f'{peak_type}\n({peak_frac*100:.0f}%)',
                           xy=(peak_center, peak_frac * 0.8),
                           fontsize=8, ha='center')

    # Row 1 continued: More experiments
    for idx, exp in enumerate(EXPERIMENTS[3:6]):
        ax = fig.add_subplot(gs[1, idx])

        y = np.zeros_like(x)
        for peak_center, peak_frac, peak_type in exp["peaks"]:
            sigma = peak_center * 0.15
            y += peak_frac * np.exp(-((x - peak_center)**2) / (2 * sigma**2))

        ax.fill_between(x, y, alpha=0.6, color=exp["color"])
        ax.plot(x, y, color=exp["color"], linewidth=2)

        if exp["n50"] > 0:
            ax.axvline(exp["n50"], color='black', linestyle='--', linewidth=1.5)

        ax.set_xscale('log')
        ax.set_xlim(50, 500000)
        ax.set_ylim(0, max(y) * 1.2 if len(y) > 0 and max(y) > 0 else 1)
        ax.set_xlabel('Read Length (bp)')
        ax.set_ylabel('Density')

        n50_str = f'{exp["n50"]/1000:.1f}K' if exp["n50"] >= 1000 else f'{exp["n50"]}'
        ax.set_title(f'{exp["short"]}\nN50={n50_str}bp, Q{exp["mean_q"]}',
                    fontsize=11, fontweight='bold', color=exp["color"])

    # =========================================================================
    # Row 3: Summary comparison and molecular products
    # =========================================================================

    # Panel: N50 bar chart
    ax = fig.add_subplot(gs[2, 0])

    names = [e["short"].replace("\n", " ") for e in EXPERIMENTS if e["n50"] > 0]
    n50s = [e["n50"] for e in EXPERIMENTS if e["n50"] > 0]
    colors = [e["color"] for e in EXPERIMENTS if e["n50"] > 0]

    bars = ax.barh(range(len(n50s)), n50s, color=colors, edgecolor='black', linewidth=0.5)
    ax.set_xscale('log')
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel('N50 (bp, log scale)')
    ax.set_title('N50 Comparison', fontsize=11, fontweight='bold')

    # Reference lines
    ax.axvline(200, color='#27ae60', linestyle='--', alpha=0.7, linewidth=2)
    ax.axvline(2600, color='#e74c3c', linestyle='--', alpha=0.7, linewidth=2)
    ax.text(200, -0.7, 'Expected\n(~200bp)', ha='center', fontsize=8, color='#27ae60')
    ax.text(2600, -0.7, 'Daisy chain\n(~2.6kb)', ha='center', fontsize=8, color='#e74c3c')

    # Value labels
    for i, (bar, val) in enumerate(zip(bars, n50s)):
        if val >= 1000:
            label = f'{val/1000:.1f}K'
        else:
            label = f'{val}'
        ax.text(val * 1.1, i, label, va='center', fontsize=8, fontweight='bold')

    ax.set_xlim(50, 600000)

    # Panel: Molecular products diagram
    ax = fig.add_subplot(gs[2, 1:])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')
    ax.set_title('Molecular Products by Peak', fontsize=11, fontweight='bold')

    y_pos = 90
    for i, (prod_name, prod_info) in enumerate(PRODUCTS.items()):
        # Product bar
        bar_width = 15
        rect = FancyBboxPatch((5, y_pos-5), bar_width, 10,
                              boxstyle="round,pad=0.02",
                              facecolor=prod_info["color"],
                              edgecolor='black', linewidth=1)
        ax.add_patch(rect)
        ax.text(5 + bar_width/2, y_pos, prod_name, ha='center', va='center',
               fontsize=9, color='white', fontweight='bold')

        # Range
        ax.text(25, y_pos, prod_info["range"], va='center', fontsize=9, fontweight='bold')

        # Structure
        ax.text(42, y_pos, prod_info["structure"], va='center', fontsize=8)

        # Status
        status_color = '#27ae60' if prod_info["status"] == "Expected" else '#e74c3c'
        ax.text(90, y_pos, prod_info["status"], va='center', fontsize=9,
               color=status_color, fontweight='bold')

        y_pos -= 15

    # Column headers
    ax.text(12, 98, 'Type', ha='center', fontsize=10, fontweight='bold')
    ax.text(25, 98, 'Range', ha='left', fontsize=10, fontweight='bold')
    ax.text(42, 98, 'Structure', ha='left', fontsize=10, fontweight='bold')
    ax.text(90, 98, 'Status', ha='center', fontsize=10, fontweight='bold')

    # =========================================================================
    # Row 4: Summary table and key findings
    # =========================================================================

    ax = fig.add_subplot(gs[3, :])
    ax.axis('off')

    # Create summary table
    table_data = [
        ['Experiment', 'Date', 'Protocol', 'Targets', 'Reads', 'N50', 'Mean Q', 'Status'],
    ]

    for exp in EXPERIMENTS:
        n50_str = f'{exp["n50"]/1000:.1f}K' if exp["n50"] >= 1000 else str(exp["n50"]) if exp["n50"] > 0 else '-'
        q_str = f'Q{exp["mean_q"]}' if exp["mean_q"] > 0 else '-'
        reads_str = f'{exp["reads"]/1e6:.1f}M' if exp["reads"] > 0 else '-'
        targets_str = ', '.join(exp["targets"][:2]) + ('...' if len(exp["targets"]) > 2 else '')

        status_map = {
            'clean': '✓ Clean',
            'daisy_chains': '⚠ Daisy chains',
            'severe': '⚠ Severe',
            'anomalous': '✗ Anomalous',
            'failed': '✗ Failed'
        }

        table_data.append([
            exp["name"].split("_")[0],
            exp["date"],
            exp["protocol"].replace("\n", " "),
            targets_str,
            reads_str,
            n50_str,
            q_str,
            status_map.get(exp["status"], exp["status"])
        ])

    table = ax.table(
        cellText=table_data[1:],
        colLabels=table_data[0],
        cellLoc='center',
        loc='upper center',
        colWidths=[0.12, 0.10, 0.14, 0.16, 0.08, 0.08, 0.08, 0.12]
    )

    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.8)

    # Style header row
    for j in range(len(table_data[0])):
        table[(0, j)].set_facecolor('#2c3e50')
        table[(0, j)].set_text_props(color='white', fontweight='bold')

    # Style status column
    for i in range(1, len(table_data)):
        status = EXPERIMENTS[i-1]["status"]
        if status == "clean":
            table[(i, 7)].set_facecolor('#d5f5e3')
        elif status in ["daisy_chains", "severe"]:
            table[(i, 7)].set_facecolor('#fdebd0')
        else:
            table[(i, 7)].set_facecolor('#fadbd8')

    # Key findings text
    findings = """
KEY FINDINGS:
• Dec 28 (V0-4.2 + V0-4.4 only): N50=149bp - CLEAN library, odd/even plasmid fix validated
• Nov 24, Dec 23: N50~2.6kb - Daisy chains from adjacent plasmid backbone overhangs
• Dec 8: N50=5.4kb - Severe daisy chaining with new 3-step protocol
• Dec 18 (all 3 replicates): N50>100kb, Q<7 - Anomalous, likely gDNA contamination
• Nov 24 CIP: No data - CIP treatment killed helicase activity
"""
    ax.text(0.02, -0.15, findings, transform=ax.transAxes, fontsize=9,
           verticalalignment='top', fontfamily='monospace',
           bbox=dict(boxstyle='round', facecolor='#f8f9fa', edgecolor='#dee2e6'))

    plt.suptitle('SMA-seq Experiment Analysis: Peaks and Molecular Products',
                fontsize=16, fontweight='bold', y=0.98)

    return fig


if __name__ == "__main__":
    print("Generating comprehensive experiment visualization...")

    fig = create_comprehensive_figure()
    fig.savefig('/data2/repos/ont-ecosystem/sma_configs/figures/all_experiments_peaks.png',
               dpi=150, bbox_inches='tight', facecolor='white')
    print("  Saved: figures/all_experiments_peaks.png")

    plt.close(fig)
    print("Done!")
