#!/usr/bin/env python3
"""
Visualize expected peaks and molecular products for all SMA-seq experiments.
Creates a comprehensive figure showing:
1. Peak locations by experiment
2. Molecular product structures
3. Analysis status comparison
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch
import numpy as np

# Set style
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.3

# Experiment data from analysis
EXPERIMENTS = {
    "12282025_IF_DoubleBC": {
        "date": "Dec 28",
        "status": "clean",
        "n50": 149,
        "mean_q": 11.9,
        "reads": 1.4e6,
        "peaks": [
            {"center": 149, "width": 50, "label": "Clean products", "fraction": 0.95, "color": "#27ae60"},
        ],
        "targets": ["V0-4.2", "V0-4.4"],
        "protocol": "Odd/even fix"
    },
    "12232025_IF_DoubleBC": {
        "date": "Dec 23",
        "status": "daisy_chains",
        "n50": 2613,
        "mean_q": 14.1,
        "reads": 12.1e6,
        "peaks": [
            {"center": 150, "width": 50, "label": "Clean", "fraction": 0.30, "color": "#27ae60"},
            {"center": 2600, "width": 400, "label": "Daisy chain", "fraction": 0.60, "color": "#e74c3c"},
            {"center": 5200, "width": 600, "label": "Double chain", "fraction": 0.10, "color": "#c0392b"},
        ],
        "targets": ["V0-4.1", "V0-4.2", "V0-4.3", "V0-4.4", "V0-39"],
        "protocol": "Double BC cycling"
    },
    "11242025_IF_Part4": {
        "date": "Nov 24",
        "status": "daisy_chains",
        "n50": 2639,
        "mean_q": 15.6,
        "reads": 20.1e6,
        "peaks": [
            {"center": 150, "width": 50, "label": "Clean", "fraction": 0.30, "color": "#27ae60"},
            {"center": 2600, "width": 400, "label": "Daisy chain", "fraction": 0.60, "color": "#e74c3c"},
            {"center": 5200, "width": 600, "label": "Double chain", "fraction": 0.10, "color": "#c0392b"},
        ],
        "targets": ["V0-4.1-4.4", "V0-39-47", "V0-4.14-17"],
        "protocol": "Standard 5-step"
    },
    "12082025_IF_NewBCPart4": {
        "date": "Dec 8",
        "status": "severe",
        "n50": 5400,
        "mean_q": 12.2,
        "reads": 4.7e6,
        "peaks": [
            {"center": 150, "width": 50, "label": "Clean", "fraction": 0.15, "color": "#27ae60"},
            {"center": 2800, "width": 500, "label": "Single chain", "fraction": 0.35, "color": "#e74c3c"},
            {"center": 5400, "width": 800, "label": "Double chain", "fraction": 0.35, "color": "#c0392b"},
            {"center": 8000, "width": 1000, "label": "Triple+", "fraction": 0.15, "color": "#922b21"},
        ],
        "targets": ["V0-4.1", "V0-4.2", "V0-4.3", "V0-4.4", "V0-39"],
        "protocol": "New 3-step"
    },
    "12182025_Ex1": {
        "date": "Dec 18",
        "status": "anomalous",
        "n50": 116800,
        "mean_q": 6.7,
        "reads": 3.2e6,
        "peaks": [
            {"center": 200, "width": 100, "label": "Clean", "fraction": 0.05, "color": "#27ae60"},
            {"center": 5000, "width": 2000, "label": "Plasmid", "fraction": 0.15, "color": "#f39c12"},
            {"center": 100000, "width": 50000, "label": "High MW", "fraction": 0.80, "color": "#8e44ad"},
        ],
        "targets": ["V0-4.1-4.4", "V0-39"],
        "protocol": "Hi-T4 ligase"
    },
    "12182025_Ex2": {
        "date": "Dec 18",
        "status": "anomalous",
        "n50": 332500,
        "mean_q": 6.3,
        "reads": 1.8e6,
        "peaks": [
            {"center": 200, "width": 100, "label": "Clean", "fraction": 0.05, "color": "#27ae60"},
            {"center": 5000, "width": 2000, "label": "Plasmid", "fraction": 0.10, "color": "#f39c12"},
            {"center": 150000, "width": 80000, "label": "High MW", "fraction": 0.85, "color": "#8e44ad"},
        ],
        "targets": ["V0-4.1-4.4", "V0-39"],
        "protocol": "Immob. T4"
    },
}

# Status colors
STATUS_COLORS = {
    "clean": "#27ae60",
    "daisy_chains": "#f39c12",
    "severe": "#e74c3c",
    "anomalous": "#8e44ad",
    "failed": "#7f8c8d"
}

def create_peak_comparison():
    """Create main peak comparison figure."""
    fig = plt.figure(figsize=(16, 12))

    # Create grid
    gs = fig.add_gridspec(3, 2, height_ratios=[2, 1.5, 1], hspace=0.3, wspace=0.25)

    # =========================================================================
    # Panel A: Peak Distribution Overview (top left)
    # =========================================================================
    ax1 = fig.add_subplot(gs[0, 0])

    exp_names = list(EXPERIMENTS.keys())
    y_positions = np.arange(len(exp_names))

    for i, (exp_name, data) in enumerate(EXPERIMENTS.items()):
        y = len(exp_names) - 1 - i

        # Draw peaks as colored bars
        for peak in data["peaks"]:
            center = peak["center"]
            width = peak["width"]
            fraction = peak["fraction"]
            color = peak["color"]

            # Use log scale for x position
            x_log = np.log10(max(center, 10))
            w_log = 0.15  # Fixed width in log space

            rect = plt.Rectangle(
                (x_log - w_log/2, y - 0.35),
                w_log, 0.7,
                facecolor=color,
                alpha=fraction,
                edgecolor='black',
                linewidth=0.5
            )
            ax1.add_patch(rect)

            # Label major peaks
            if fraction >= 0.3:
                ax1.annotate(
                    f'{center:,}bp',
                    (x_log, y + 0.4),
                    ha='center', va='bottom',
                    fontsize=7,
                    rotation=45
                )

        # Status indicator
        status = data["status"]
        ax1.scatter([-0.3], [y], c=STATUS_COLORS[status], s=200, marker='s', zorder=5)

        # Experiment label
        label = f"{data['date']}\n{exp_name.split('_')[0]}"
        ax1.text(-0.6, y, label, ha='right', va='center', fontsize=9)

    ax1.set_xlim(-0.8, 6)
    ax1.set_ylim(-0.5, len(exp_names) - 0.5)

    # Custom x-axis labels
    x_ticks = [1, 2, 3, 4, 5]  # log10 values
    x_labels = ['10', '100', '1K', '10K', '100K']
    ax1.set_xticks(x_ticks)
    ax1.set_xticklabels(x_labels)
    ax1.set_xlabel('Read Length (bp, log scale)')
    ax1.set_yticks([])
    ax1.set_title('A. Peak Distribution by Experiment', fontsize=12, fontweight='bold', loc='left')

    # Add N50 markers
    for i, (exp_name, data) in enumerate(EXPERIMENTS.items()):
        y = len(exp_names) - 1 - i
        n50_log = np.log10(max(data["n50"], 10))
        ax1.axvline(n50_log, ymin=(y)/(len(exp_names)), ymax=(y+0.8)/(len(exp_names)),
                   color='black', linestyle='--', linewidth=1, alpha=0.5)
        ax1.text(n50_log, y - 0.45, f'N50', ha='center', va='top', fontsize=7)

    # =========================================================================
    # Panel B: Molecular Product Structures (top right)
    # =========================================================================
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_xlim(0, 100)
    ax2.set_ylim(0, 100)
    ax2.axis('off')
    ax2.set_title('B. Molecular Product Structures', fontsize=12, fontweight='bold', loc='left')

    # Clean product structure
    y_pos = 85
    ax2.text(5, y_pos + 8, 'Clean Product (~150-200 bp)', fontsize=10, fontweight='bold', color='#27ae60')

    elements = [
        ("PREFIX", 13, "#3498db"),
        ("ADAPTER", 15, "#9b59b6"),
        ("FL", 8, "#95a5a6"),
        ("BARCODE", 23, "#e74c3c"),
        ("FL", 8, "#95a5a6"),
        ("TARGET", 100, "#27ae60"),
    ]

    x = 5
    scale = 0.35
    for name, length, color in elements:
        width = length * scale
        rect = FancyBboxPatch((x, y_pos - 5), width, 10,
                              boxstyle="round,pad=0.02",
                              facecolor=color, edgecolor='black', linewidth=0.5)
        ax2.add_patch(rect)
        if width > 8:
            ax2.text(x + width/2, y_pos, name, ha='center', va='center', fontsize=7, color='white')
        x += width
    ax2.text(x + 2, y_pos, '→ 5\'', fontsize=8)

    # Daisy chain structure
    y_pos = 60
    ax2.text(5, y_pos + 8, 'Single Daisy Chain (~2,600 bp)', fontsize=10, fontweight='bold', color='#e74c3c')

    chain_elements = [
        ("BC+TARGET_A", 20, "#27ae60"),
        ("BACKBONE (~2kb)", 50, "#e74c3c"),
        ("TARGET_B+BC", 20, "#27ae60"),
    ]

    x = 5
    for name, width, color in chain_elements:
        rect = FancyBboxPatch((x, y_pos - 5), width, 10,
                              boxstyle="round,pad=0.02",
                              facecolor=color, edgecolor='black', linewidth=0.5)
        ax2.add_patch(rect)
        ax2.text(x + width/2, y_pos, name, ha='center', va='center', fontsize=7, color='white')
        x += width

    # Multi daisy chain
    y_pos = 35
    ax2.text(5, y_pos + 8, 'Multi Daisy Chain (~5,000+ bp)', fontsize=10, fontweight='bold', color='#c0392b')

    multi_elements = [
        ("T_A", 8, "#27ae60"),
        ("BB", 20, "#e74c3c"),
        ("T_B", 8, "#27ae60"),
        ("BB", 20, "#e74c3c"),
        ("T_C", 8, "#27ae60"),
        ("...", 10, "#bdc3c7"),
    ]

    x = 5
    for name, width, color in multi_elements:
        rect = FancyBboxPatch((x, y_pos - 5), width, 10,
                              boxstyle="round,pad=0.02",
                              facecolor=color, edgecolor='black', linewidth=0.5)
        ax2.add_patch(rect)
        ax2.text(x + width/2, y_pos, name, ha='center', va='center', fontsize=7,
                color='white' if color != '#bdc3c7' else 'black')
        x += width

    # Anomalous products
    y_pos = 10
    ax2.text(5, y_pos + 8, 'Anomalous (>100K bp)', fontsize=10, fontweight='bold', color='#8e44ad')
    ax2.text(5, y_pos - 2, '• Genomic DNA contamination\n• Undigested circular plasmid\n• Plasmid concatemers',
             fontsize=8, va='top')

    # =========================================================================
    # Panel C: N50 Comparison Bar Chart (middle left)
    # =========================================================================
    ax3 = fig.add_subplot(gs[1, 0])

    exp_labels = []
    n50_values = []
    colors = []

    for exp_name, data in EXPERIMENTS.items():
        short_name = exp_name.replace("_IF_", "\n").replace("_SMA_seq", "").replace("DoubleBC", "DblBC").replace("NewBCPart4", "NewBC")
        exp_labels.append(f"{data['date']}")
        n50_values.append(data["n50"])
        colors.append(STATUS_COLORS[data["status"]])

    bars = ax3.bar(range(len(n50_values)), n50_values, color=colors, edgecolor='black', linewidth=0.5)
    ax3.set_yscale('log')
    ax3.set_ylabel('N50 (bp, log scale)')
    ax3.set_xticks(range(len(exp_labels)))
    ax3.set_xticklabels(exp_labels, rotation=45, ha='right')
    ax3.set_title('C. N50 Comparison', fontsize=12, fontweight='bold', loc='left')

    # Add value labels
    for i, (bar, val) in enumerate(zip(bars, n50_values)):
        if val < 1000:
            label = f'{val}bp'
        elif val < 1000000:
            label = f'{val/1000:.1f}K'
        else:
            label = f'{val/1000000:.1f}M'
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.1,
                label, ha='center', va='bottom', fontsize=8, fontweight='bold')

    # Reference lines
    ax3.axhline(200, color='#27ae60', linestyle='--', linewidth=1, alpha=0.7, label='Expected clean (~200bp)')
    ax3.axhline(2600, color='#e74c3c', linestyle='--', linewidth=1, alpha=0.7, label='Daisy chain (~2.6kb)')
    ax3.legend(loc='upper left', fontsize=8)

    ax3.set_ylim(50, 500000)

    # =========================================================================
    # Panel D: Quality vs N50 Scatter (middle right)
    # =========================================================================
    ax4 = fig.add_subplot(gs[1, 1])

    for exp_name, data in EXPERIMENTS.items():
        ax4.scatter(
            data["n50"], data["mean_q"],
            c=STATUS_COLORS[data["status"]],
            s=data["reads"]/50000,
            alpha=0.7,
            edgecolor='black',
            linewidth=0.5
        )
        ax4.annotate(
            data["date"],
            (data["n50"], data["mean_q"]),
            xytext=(5, 5), textcoords='offset points',
            fontsize=8
        )

    ax4.set_xscale('log')
    ax4.set_xlabel('N50 (bp)')
    ax4.set_ylabel('Mean Q-score')
    ax4.set_title('D. Quality vs N50 (size = read count)', fontsize=12, fontweight='bold', loc='left')

    # Add quadrant labels
    ax4.axvline(1000, color='gray', linestyle=':', alpha=0.5)
    ax4.axhline(10, color='gray', linestyle=':', alpha=0.5)
    ax4.text(200, 17, 'CLEAN\n(target)', ha='center', fontsize=9, color='#27ae60', fontweight='bold')
    ax4.text(50000, 17, 'ARTIFACTS\n(good Q)', ha='center', fontsize=9, color='#f39c12', fontweight='bold')
    ax4.text(50000, 5, 'FAILED\n(anomalous)', ha='center', fontsize=9, color='#8e44ad', fontweight='bold')

    # =========================================================================
    # Panel E: Legend and Summary (bottom)
    # =========================================================================
    ax5 = fig.add_subplot(gs[2, :])
    ax5.axis('off')

    # Status legend
    legend_elements = [
        mpatches.Patch(facecolor='#27ae60', edgecolor='black', label='Clean (N50 matches target)'),
        mpatches.Patch(facecolor='#f39c12', edgecolor='black', label='Daisy chains (N50 ~2.6kb)'),
        mpatches.Patch(facecolor='#e74c3c', edgecolor='black', label='Severe daisy chains (N50 >5kb)'),
        mpatches.Patch(facecolor='#8e44ad', edgecolor='black', label='Anomalous (N50 >100kb, low Q)'),
    ]
    ax5.legend(handles=legend_elements, loc='upper left', ncol=4, fontsize=9, frameon=True)

    # Summary text
    summary = """
KEY FINDINGS:
• Only Dec 28 experiment (V0-4.2 + V0-4.4 only) produced clean library with N50 = 149 bp matching expected amplicon size
• Daisy chaining occurs when adjacent Level 0 plasmids are present together (backbone overhangs match)
• FIX VALIDATED: Using only odd OR even numbered plasmids eliminates daisy chain formation
• All Dec 18 cycling protocol variants failed with extreme N50 (>100kb) and low quality (Q<7)

PRODUCT ASSIGNMENTS:
• 100-260 bp: Clean single-target amplicons (PREFIX + ADAPTER + BARCODE + TARGET)
• 2,300-3,000 bp: Single daisy chain (TARGET_A + BACKBONE + TARGET_B)
• 4,500-8,000 bp: Multiple concatenated daisy chains
• >100,000 bp: Anomalous (genomic DNA contamination or undigested plasmid)
"""
    ax5.text(0.02, 0.7, summary, transform=ax5.transAxes, fontsize=9,
             verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='#f8f9fa', edgecolor='#dee2e6'))

    plt.suptitle('SMA-seq Expected Peaks and Molecular Products', fontsize=14, fontweight='bold', y=0.98)

    return fig


def create_product_detail_figure():
    """Create detailed molecular product diagram."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Panel A: Library structure detail
    ax = axes[0, 0]
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')
    ax.set_title('A. Clean Product Structure Detail', fontsize=11, fontweight='bold', loc='left')

    y = 80
    elements = [
        ("PREFIX\n13bp", 8, "#3498db", "CCTGTACTTCGTT"),
        ("ADAPTER\n15bp", 10, "#9b59b6", "CAGTTACGTATTGCT"),
        ("FLANK_F\n8bp", 5, "#95a5a6", "AAGGTTAA"),
        ("BARCODE\n22-24bp", 15, "#e74c3c", "ACAGACGACTACAAACGGAATCGA"),
        ("FLANK_R\n8bp", 5, "#95a5a6", "CAGCACCT"),
        ("OVERHANG\n4bp", 3, "#f39c12", "AGGA"),
        ("TARGET\n84-188bp", 40, "#27ae60", "CYP2D6 sequence"),
    ]

    x = 2
    for i, (name, width, color, seq) in enumerate(elements):
        rect = FancyBboxPatch((x, y-8), width, 16,
                              boxstyle="round,pad=0.02",
                              facecolor=color, edgecolor='black', linewidth=1)
        ax.add_patch(rect)
        ax.text(x + width/2, y, name, ha='center', va='center', fontsize=8, color='white', fontweight='bold')

        # Sequence below
        if len(seq) < 20:
            ax.text(x + width/2, y-15, seq, ha='center', va='top', fontsize=6, fontfamily='monospace')
        x += width + 1

    ax.text(50, y + 20, '5\' ←―――――――――――――――――――――――――――――――――――――――――――――→ 3\'',
           ha='center', fontsize=10)
    ax.text(50, y - 25, 'Total: 150-260 bp depending on target', ha='center', fontsize=10, style='italic')

    # Panel B: Daisy chain mechanism
    ax = axes[0, 1]
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')
    ax.set_title('B. Daisy Chain Formation Mechanism', fontsize=11, fontweight='bold', loc='left')

    # Step 1: Adjacent plasmids
    ax.text(5, 95, '1. Adjacent Level 0 plasmids share compatible overhangs:', fontsize=9, fontweight='bold')

    # V0-4.1 and V0-4.2 example
    ax.text(10, 85, 'V0-4.1:', fontsize=8)
    ax.add_patch(FancyBboxPatch((25, 82), 25, 8, facecolor='#3498db', edgecolor='black'))
    ax.text(37.5, 86, 'TARGET', ha='center', va='center', fontsize=7, color='white')
    ax.text(52, 86, 'TTCG―', fontsize=8, fontfamily='monospace')
    ax.text(62, 86, '―AGGA', fontsize=8, fontfamily='monospace', color='#e74c3c')

    ax.text(10, 72, 'V0-4.2:', fontsize=8)
    ax.text(22, 76, 'AGGA―', fontsize=8, fontfamily='monospace', color='#e74c3c')
    ax.add_patch(FancyBboxPatch((35, 69), 25, 8, facecolor='#27ae60', edgecolor='black'))
    ax.text(47.5, 73, 'TARGET', ha='center', va='center', fontsize=7, color='white')
    ax.text(62, 76, '―AGAG', fontsize=8, fontfamily='monospace')

    # Arrow showing ligation
    ax.annotate('', xy=(48, 68), xytext=(48, 80),
               arrowprops=dict(arrowstyle='->', color='red', lw=2))
    ax.text(52, 74, 'Backbone\nligates!', fontsize=7, color='red')

    # Step 2: Result
    ax.text(5, 55, '2. Result: Concatenated products (~2,600 bp):', fontsize=9, fontweight='bold')

    chain = [
        ("BC", 8, "#9b59b6"),
        ("T_A", 12, "#3498db"),
        ("BACKBONE", 35, "#e74c3c"),
        ("T_B", 12, "#27ae60"),
        ("BC", 8, "#9b59b6"),
    ]
    x = 10
    for name, width, color in chain:
        ax.add_patch(FancyBboxPatch((x, 42), width, 10, facecolor=color, edgecolor='black'))
        ax.text(x + width/2, 47, name, ha='center', va='center', fontsize=7, color='white')
        x += width

    # Step 3: Fix
    ax.text(5, 30, '3. FIX: Use only ODD or EVEN plasmids:', fontsize=9, fontweight='bold', color='#27ae60')
    ax.text(10, 22, 'ODD:  V0-4.1, V0-4.3, V0-39, V0-41, V0-43, V0-45, V0-47', fontsize=8)
    ax.text(10, 14, 'EVEN: V0-4.2, V0-4.4, V0-40, V0-42, V0-44, V0-46', fontsize=8)
    ax.text(10, 5, '→ Adjacent backbone overhangs no longer present!', fontsize=8, color='#27ae60', fontweight='bold')

    # Panel C: Expected vs Observed peaks
    ax = axes[1, 0]

    # Create synthetic distributions
    x = np.linspace(0, 10000, 1000)

    # Clean (Dec 28)
    clean = 0.95 * np.exp(-((x - 149)**2) / (2 * 30**2))

    # Daisy chain (Dec 23)
    daisy = (0.30 * np.exp(-((x - 150)**2) / (2 * 30**2)) +
             0.60 * np.exp(-((x - 2600)**2) / (2 * 300**2)) +
             0.10 * np.exp(-((x - 5200)**2) / (2 * 500**2)))

    ax.fill_between(x, clean, alpha=0.5, color='#27ae60', label='Dec 28 (clean)')
    ax.fill_between(x, daisy, alpha=0.5, color='#e74c3c', label='Dec 23 (daisy chains)')

    ax.set_xlabel('Read Length (bp)')
    ax.set_ylabel('Density')
    ax.set_title('C. Expected Length Distributions', fontsize=11, fontweight='bold', loc='left')
    ax.legend(loc='upper right')
    ax.set_xlim(0, 8000)

    # Add peak labels
    ax.annotate('Clean\nproducts', xy=(149, 0.9), xytext=(500, 0.7),
               arrowprops=dict(arrowstyle='->', color='black'),
               fontsize=8, ha='center')
    ax.annotate('Single\ndaisy chain', xy=(2600, 0.55), xytext=(3500, 0.7),
               arrowprops=dict(arrowstyle='->', color='black'),
               fontsize=8, ha='center')

    # Panel D: Summary table
    ax = axes[1, 1]
    ax.axis('off')
    ax.set_title('D. Peak Assignment Summary', fontsize=11, fontweight='bold', loc='left')

    table_data = [
        ['Peak Range', 'Product Type', 'Components', 'Status'],
        ['100-260 bp', 'Clean product', 'PREFIX+ADAPTER+BC+TARGET', '✓ Expected'],
        ['2.3-3.0 kb', 'Single daisy chain', 'TARGET+BACKBONE+TARGET', '✗ Artifact'],
        ['4.5-8.0 kb', 'Multi daisy chain', 'T+BB+T+BB+T...', '✗ Artifact'],
        ['>100 kb', 'Anomalous', 'gDNA/undigested plasmid', '✗ Failed'],
    ]

    table = ax.table(
        cellText=table_data[1:],
        colLabels=table_data[0],
        cellLoc='center',
        loc='center',
        colWidths=[0.2, 0.25, 0.35, 0.2]
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.5)

    # Color cells
    for i in range(len(table_data)):
        for j in range(len(table_data[0])):
            cell = table[(i, j)]
            if i == 0:
                cell.set_facecolor('#2c3e50')
                cell.set_text_props(color='white', fontweight='bold')
            elif j == 3:
                if '✓' in table_data[i][j]:
                    cell.set_facecolor('#d5f5e3')
                else:
                    cell.set_facecolor('#fadbd8')

    plt.tight_layout()
    return fig


# Main execution
if __name__ == "__main__":
    print("Generating peak visualization figures...")

    # Figure 1: Overview
    fig1 = create_peak_comparison()
    fig1.savefig('/data2/repos/ont-ecosystem/sma_configs/figures/peak_overview.png',
                dpi=150, bbox_inches='tight', facecolor='white')
    print("  Saved: figures/peak_overview.png")

    # Figure 2: Product detail
    fig2 = create_product_detail_figure()
    fig2.savefig('/data2/repos/ont-ecosystem/sma_configs/figures/product_structures.png',
                dpi=150, bbox_inches='tight', facecolor='white')
    print("  Saved: figures/product_structures.png")

    print("\nDone!")
