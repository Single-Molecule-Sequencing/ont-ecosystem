#!/usr/bin/env python3
"""
Create comprehensive reference figure showing expected molecular products
and their size ranges for all SMA-seq experiments.

This is a definitive reference showing:
1. Library structure with exact element sizes
2. All possible molecular products
3. Expected peak locations
4. Experiment-specific product predictions
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Rectangle, ConnectionPatch
import matplotlib.gridspec as gridspec
import numpy as np

# =============================================================================
# LIBRARY ELEMENT DEFINITIONS
# =============================================================================

LIBRARY_ELEMENTS = {
    "PREFIX": {"seq": "CCTGTACTTCGTT", "length": 13, "color": "#3498db"},
    "ADAPTER": {"seq": "CAGTTACGTATTGCT", "length": 15, "color": "#9b59b6"},
    "FLANK_F": {"seq": "AAGGTTAA", "length": 8, "color": "#95a5a6"},
    "BARCODE": {"length_range": (22, 24), "color": "#e74c3c"},
    "FLANK_R": {"seq": "CAGCACCT", "length": 8, "color": "#95a5a6"},
    "OVERHANG": {"length": 4, "color": "#f39c12"},
}

# Target sequences and their lengths
TARGETS = {
    "V0-4.1": {"length": 168, "overhang_5p": "TTCG", "overhang_3p": "AGGA"},
    "V0-4.2": {"length": 165, "overhang_5p": "AGGA", "overhang_3p": "AGAG"},
    "V0-4.3": {"length": 188, "overhang_5p": "AGAG", "overhang_3p": "TGGT"},
    "V0-4.4": {"length": 160, "overhang_5p": "TGGT", "overhang_3p": "CTGA"},
    "V0-39": {"length": 106, "overhang_5p": "CTGA", "overhang_3p": "TCAG"},
    "V0-40": {"length": 98, "overhang_5p": "CAAA", "overhang_3p": "AGTA"},
    "V0-41": {"length": 88, "overhang_5p": "AGTA", "overhang_3p": "TGTT"},
    "V0-42": {"length": 100, "overhang_5p": "TGTT", "overhang_3p": "AAAC"},
    "V0-43": {"length": 110, "overhang_5p": "AAAC", "overhang_3p": "ACCT"},
    "V0-44": {"length": 91, "overhang_5p": "ACCT", "overhang_3p": "CCGT"},
    "V0-45": {"length": 107, "overhang_5p": "CCGT", "overhang_3p": "CAGC"},
    "V0-46": {"length": 84, "overhang_5p": "CAGC", "overhang_3p": "TAAG"},
    "V0-47": {"length": 109, "overhang_5p": "TAAG", "overhang_3p": "TAGT"},
    "V0-4.14": {"length": 173, "overhang_5p": "TAGT", "overhang_3p": "TCTG"},
    "V0-4.15": {"length": 174, "overhang_5p": "TCTG", "overhang_3p": "CATC"},
    "V0-4.16": {"length": 164, "overhang_5p": "CATC", "overhang_3p": "CTGT"},
    "V0-4.17": {"length": 176, "overhang_5p": "CTGT", "overhang_3p": "GCTT"},
}

# Backbone length (from plasmid)
BACKBONE_LENGTH = 2000  # Approximate

# Barcodes
BARCODES = {
    "NB01": {"length": 24, "target": "V0-4.1"},
    "NB02": {"length": 24, "target": "V0-4.2"},
    "NB03": {"length": 24, "target": "V0-4.3"},
    "NB04": {"length": 23, "target": "V0-4.4"},
    "NB05": {"length": 23, "target": "V0-39"},
}

# Experiments and their targets
EXPERIMENTS = {
    "12282025_IF_DoubleBC": {
        "targets": ["V0-4.2", "V0-4.4"],
        "status": "clean",
        "color": "#27ae60",
        "observed_n50": 149,
    },
    "12232025_IF_DoubleBC": {
        "targets": ["V0-4.1", "V0-4.2", "V0-4.3", "V0-4.4", "V0-39"],
        "status": "daisy_chains",
        "color": "#f39c12",
        "observed_n50": 2613,
    },
    "11242025_IF_Part4": {
        "targets": ["V0-4.1", "V0-4.2", "V0-4.3", "V0-4.4", "V0-39", "V0-40", "V0-41",
                   "V0-42", "V0-43", "V0-44", "V0-45", "V0-46", "V0-47",
                   "V0-4.14", "V0-4.15", "V0-4.16", "V0-4.17"],
        "status": "daisy_chains",
        "color": "#f39c12",
        "observed_n50": 2639,
    },
    "12082025_IF_NewBCPart4": {
        "targets": ["V0-4.1", "V0-4.2", "V0-4.3", "V0-4.4", "V0-39"],
        "status": "severe",
        "color": "#e74c3c",
        "observed_n50": 5400,
    },
    "12182025_Ex1": {
        "targets": ["V0-4.1", "V0-4.2", "V0-4.3", "V0-4.4", "V0-39"],
        "status": "anomalous",
        "color": "#8e44ad",
        "observed_n50": 116800,
    },
}


def calculate_clean_product_size(target_name, barcode_length=23):
    """Calculate expected size of a clean product."""
    target = TARGETS.get(target_name, {"length": 150})

    size = (
        LIBRARY_ELEMENTS["PREFIX"]["length"] +      # 13
        LIBRARY_ELEMENTS["ADAPTER"]["length"] +     # 15
        LIBRARY_ELEMENTS["FLANK_F"]["length"] +     # 8
        barcode_length +                             # 22-24
        LIBRARY_ELEMENTS["FLANK_R"]["length"] +     # 8
        LIBRARY_ELEMENTS["OVERHANG"]["length"] +    # 4
        target["length"]                             # 84-188
    )
    return size


def calculate_daisy_chain_size(target1, target2, backbone=BACKBONE_LENGTH):
    """Calculate expected size of a daisy chain product."""
    t1 = TARGETS.get(target1, {"length": 150})
    t2 = TARGETS.get(target2, {"length": 150})

    # Daisy chain: BC + TARGET_A + BACKBONE + TARGET_B + BC
    size = (
        48 +  # Prefix + adapter + flanks + barcode (approximate)
        t1["length"] +
        backbone +
        t2["length"] +
        48   # Second barcode assembly
    )
    return size


def create_reference_figure():
    """Create the comprehensive reference figure."""

    fig = plt.figure(figsize=(24, 20))
    gs = fig.add_gridspec(5, 3, height_ratios=[1.2, 1.5, 1.2, 1.5, 1],
                          width_ratios=[1, 1, 1], hspace=0.35, wspace=0.25)

    # =========================================================================
    # PANEL A: Library Structure Detail (top, spanning all columns)
    # =========================================================================
    ax_struct = fig.add_subplot(gs[0, :])
    ax_struct.set_xlim(0, 100)
    ax_struct.set_ylim(0, 100)
    ax_struct.axis('off')
    ax_struct.set_title('A. SMA-seq Library Structure', fontsize=14, fontweight='bold', loc='left')

    # Draw library elements
    y = 70
    elements = [
        ("PREFIX", 13, "#3498db", "CCTGTACTTCGTT"),
        ("ADAPTER", 15, "#9b59b6", "CAGTTACGTATTGCT"),
        ("FLANK_F", 8, "#7f8c8d", "AAGGTTAA"),
        ("BARCODE", 23, "#e74c3c", "22-24 nt custom"),
        ("FLANK_R", 8, "#7f8c8d", "CAGCACCT"),
        ("OVERHANG", 4, "#f39c12", "4 nt"),
        ("TARGET", 150, "#27ae60", "84-188 bp CYP2D6"),
    ]

    x = 2
    scale = 0.38
    for name, length, color, seq in elements:
        width = max(length * scale, 4)
        rect = FancyBboxPatch((x, y-8), width, 16,
                              boxstyle="round,pad=0.02",
                              facecolor=color, edgecolor='black', linewidth=1.5)
        ax_struct.add_patch(rect)

        # Label above
        ax_struct.text(x + width/2, y + 12, f'{name}\n({length} bp)',
                      ha='center', va='bottom', fontsize=9, fontweight='bold')

        # Sequence below (if short enough)
        if len(seq) <= 16:
            ax_struct.text(x + width/2, y - 12, seq,
                          ha='center', va='top', fontsize=7, fontfamily='monospace')

        x += width + 0.5

    # Direction arrow
    ax_struct.annotate('', xy=(x + 2, y), xytext=(2, y),
                      arrowprops=dict(arrowstyle='->', color='black', lw=2))
    ax_struct.text(x/2, y + 25, "5' ────────────────────────────────────────────────────────────────→ 3'",
                  ha='center', fontsize=11, fontfamily='monospace')

    # Size calculation box
    calc_text = """
CLEAN PRODUCT SIZE CALCULATION:
PREFIX (13) + ADAPTER (15) + FLANK_F (8) + BARCODE (22-24) + FLANK_R (8) + OVERHANG (4) + TARGET (84-188)
= 154-260 bp (depending on target and barcode)
"""
    ax_struct.text(50, 25, calc_text, ha='center', va='top', fontsize=10,
                  fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='#ecf0f1', edgecolor='#bdc3c7'))

    # =========================================================================
    # PANEL B: Expected Clean Product Sizes by Target
    # =========================================================================
    ax_clean = fig.add_subplot(gs[1, 0])

    target_names = list(TARGETS.keys())
    clean_sizes = [calculate_clean_product_size(t) for t in target_names]

    colors = ['#27ae60' if t in ["V0-4.2", "V0-4.4"] else '#3498db' for t in target_names]

    bars = ax_clean.barh(range(len(target_names)), clean_sizes, color=colors,
                         edgecolor='black', linewidth=0.5)
    ax_clean.set_yticks(range(len(target_names)))
    ax_clean.set_yticklabels(target_names, fontsize=8)
    ax_clean.set_xlabel('Expected Size (bp)')
    ax_clean.set_title('B. Clean Product Sizes by Target', fontsize=12, fontweight='bold')
    ax_clean.set_xlim(0, 300)

    # Add size labels
    for i, (bar, size) in enumerate(zip(bars, clean_sizes)):
        ax_clean.text(size + 5, i, f'{size}bp', va='center', fontsize=8)

    # Highlight even-numbered (used in Dec 28)
    ax_clean.axhline(1.5, color='#27ae60', linestyle='--', alpha=0.5)
    ax_clean.axhline(3.5, color='#27ae60', linestyle='--', alpha=0.5)
    ax_clean.text(280, 2.5, 'Dec 28\n(clean)', ha='center', fontsize=8, color='#27ae60', fontweight='bold')

    # =========================================================================
    # PANEL C: Daisy Chain Formation Diagram
    # =========================================================================
    ax_daisy = fig.add_subplot(gs[1, 1])
    ax_daisy.set_xlim(0, 100)
    ax_daisy.set_ylim(0, 100)
    ax_daisy.axis('off')
    ax_daisy.set_title('C. Daisy Chain Formation', fontsize=12, fontweight='bold')

    # Adjacent plasmids
    y = 85
    ax_daisy.text(5, y+5, '1. Adjacent plasmids have compatible overhangs:', fontsize=9, fontweight='bold')

    # V0-4.1
    ax_daisy.add_patch(FancyBboxPatch((10, y-15), 30, 10, facecolor='#3498db', edgecolor='black'))
    ax_daisy.text(25, y-10, 'V0-4.1', ha='center', va='center', fontsize=8, color='white', fontweight='bold')
    ax_daisy.text(42, y-10, '—AGGA', fontsize=8, fontfamily='monospace', color='#e74c3c')

    # V0-4.2
    ax_daisy.text(8, y-30, 'AGGA—', fontsize=8, fontfamily='monospace', color='#e74c3c')
    ax_daisy.add_patch(FancyBboxPatch((25, y-38), 30, 10, facecolor='#27ae60', edgecolor='black'))
    ax_daisy.text(40, y-33, 'V0-4.2', ha='center', va='center', fontsize=8, color='white', fontweight='bold')

    # Arrow showing ligation
    ax_daisy.annotate('', xy=(35, y-28), xytext=(35, y-18),
                     arrowprops=dict(arrowstyle='->', color='red', lw=2))
    ax_daisy.text(50, y-23, 'Backbone\nligates!', fontsize=8, color='red', fontweight='bold')

    # Result
    y = 30
    ax_daisy.text(5, y+5, '2. Result: Concatenated product (~2,600 bp):', fontsize=9, fontweight='bold')

    chain = [("BC", 10, "#9b59b6"), ("T_A", 15, "#3498db"),
             ("BACKBONE\n(~2kb)", 35, "#e74c3c"), ("T_B", 15, "#27ae60"), ("BC", 10, "#9b59b6")]
    x = 5
    for name, width, color in chain:
        ax_daisy.add_patch(FancyBboxPatch((x, y-12), width, 10, facecolor=color, edgecolor='black'))
        ax_daisy.text(x + width/2, y-7, name, ha='center', va='center', fontsize=7, color='white', fontweight='bold')
        x += width + 1

    # =========================================================================
    # PANEL D: All Possible Products
    # =========================================================================
    ax_products = fig.add_subplot(gs[1, 2])
    ax_products.set_xlim(0, 100)
    ax_products.set_ylim(0, 100)
    ax_products.axis('off')
    ax_products.set_title('D. All Possible Products', fontsize=12, fontweight='bold')

    products = [
        ("Clean Product", "100-260 bp", "#27ae60", "Single target with barcode"),
        ("Single Daisy Chain", "2.3-3.0 kb", "#e74c3c", "TARGET + BACKBONE + TARGET"),
        ("Double Daisy Chain", "4.5-5.5 kb", "#c0392b", "T + BB + T + BB + T"),
        ("Triple+ Chain", "7-10 kb", "#922b21", "Multiple concatenations"),
        ("Circular Plasmid", "4-8 kb", "#f39c12", "Undigested/religated"),
        ("High MW Artifacts", ">100 kb", "#8e44ad", "gDNA / concatemers"),
    ]

    y = 90
    for name, size_range, color, description in products:
        # Color box
        ax_products.add_patch(FancyBboxPatch((2, y-5), 8, 8, facecolor=color, edgecolor='black'))
        # Name
        ax_products.text(12, y, name, va='center', fontsize=9, fontweight='bold')
        # Size range
        ax_products.text(55, y, size_range, va='center', fontsize=9, fontweight='bold', color=color)
        # Description
        ax_products.text(75, y, description, va='center', fontsize=8, color='gray')
        y -= 14

    # =========================================================================
    # PANEL E: Peak Location Reference Chart
    # =========================================================================
    ax_peaks = fig.add_subplot(gs[2, :])

    # Create log-scale x-axis
    ax_peaks.set_xscale('log')
    ax_peaks.set_xlim(50, 500000)
    ax_peaks.set_ylim(0, 10)

    # Draw peak regions
    regions = [
        (100, 260, "#27ae60", "Clean Products\n(expected)", 0.9),
        (2300, 3000, "#e74c3c", "Single Daisy Chain\n(artifact)", 0.7),
        (4500, 6000, "#c0392b", "Double Daisy Chain\n(artifact)", 0.5),
        (7000, 12000, "#922b21", "Triple+ Chain\n(artifact)", 0.3),
        (100000, 400000, "#8e44ad", "High MW\n(failed)", 0.5),
    ]

    for xmin, xmax, color, label, alpha in regions:
        ax_peaks.axvspan(xmin, xmax, alpha=alpha, color=color, label=label)
        ax_peaks.text(np.sqrt(xmin * xmax), 8, label, ha='center', va='center',
                     fontsize=9, fontweight='bold', color='black')

    # Add N50 markers for each experiment
    experiments_markers = [
        (149, "Dec 28", "#27ae60", 2),
        (2613, "Dec 23", "#f39c12", 3),
        (2639, "Nov 24", "#f39c12", 4),
        (5400, "Dec 8", "#e74c3c", 5),
        (116800, "Dec 18\nEx1", "#8e44ad", 6),
        (332500, "Dec 18\nEx2", "#8e44ad", 7),
    ]

    for n50, label, color, y_pos in experiments_markers:
        ax_peaks.axvline(n50, color=color, linestyle='--', linewidth=2, alpha=0.8)
        ax_peaks.plot(n50, y_pos, 'v', color=color, markersize=10)
        ax_peaks.text(n50, y_pos - 0.8, label, ha='center', va='top', fontsize=8,
                     fontweight='bold', color=color)

    ax_peaks.set_xlabel('Read Length (bp, log scale)', fontsize=11)
    ax_peaks.set_yticks([])
    ax_peaks.set_title('E. Peak Location Reference Chart with Observed N50 Values',
                      fontsize=12, fontweight='bold')

    # =========================================================================
    # PANEL F: Experiment-Specific Expected Products
    # =========================================================================
    ax_exp = fig.add_subplot(gs[3, :])
    ax_exp.axis('off')
    ax_exp.set_title('F. Experiment-Specific Expected Products', fontsize=12, fontweight='bold')

    # Table data
    table_data = [
        ['Experiment', 'Targets', 'Expected Clean\nProducts (bp)', 'Adjacent Pairs\n(Daisy Chain Risk)',
         'Predicted\nPeaks', 'Observed\nN50', 'Status']
    ]

    exp_details = [
        ("Dec 28\n12282025", "V0-4.2, V0-4.4", "209, 203", "None\n(even only)",
         "~200bp only", "149bp", "✓ Clean"),
        ("Dec 23\n12232025", "V0-4.1 to V0-4.4,\nV0-39", "212, 209, 232,\n203, 148",
         "4.1→4.2, 4.2→4.3,\n4.3→4.4, 4.4→39", "~200bp +\n~2.6kb", "2,613bp", "⚠ Daisy"),
        ("Nov 24\n11242025", "V0-4.1 to V0-4.17\n(17 targets)", "148-232bp\n(range)",
         "All adjacent\npairs present", "~200bp +\n~2.6kb", "2,639bp", "⚠ Daisy"),
        ("Dec 8\n12082025", "V0-4.1 to V0-4.4,\nV0-39", "148-232bp",
         "All adjacent\npairs present", "~200bp +\nmulti-kb", "5,400bp", "⚠ Severe"),
        ("Dec 18\n12182025", "V0-4.1 to V0-4.4,\nV0-39", "148-232bp",
         "All adjacent\npairs present", "~200bp +\n>100kb", ">100kb", "✗ Anomalous"),
    ]

    for row in exp_details:
        table_data.append(list(row))

    table = ax_exp.table(
        cellText=table_data[1:],
        colLabels=table_data[0],
        cellLoc='center',
        loc='upper center',
        colWidths=[0.12, 0.15, 0.13, 0.18, 0.12, 0.10, 0.10]
    )

    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2.2)

    # Style header
    for j in range(len(table_data[0])):
        table[(0, j)].set_facecolor('#2c3e50')
        table[(0, j)].set_text_props(color='white', fontweight='bold')

    # Style status column
    status_colors = ['#d5f5e3', '#fdebd0', '#fdebd0', '#fadbd8', '#fadbd8']
    for i, color in enumerate(status_colors):
        table[(i+1, 6)].set_facecolor(color)

    # =========================================================================
    # PANEL G: Key for Interpretation
    # =========================================================================
    ax_key = fig.add_subplot(gs[4, :])
    ax_key.axis('off')
    ax_key.set_title('G. Interpretation Guide', fontsize=12, fontweight='bold')

    guide_text = """
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  HOW TO INTERPRET YOUR LENGTH DISTRIBUTION:                                                                                          │
│                                                                                                                                      │
│  ✓ CLEAN LIBRARY:        Single peak at 150-260bp matching expected target+barcode size                                              │
│                          N50 should be ~150-200bp, Mean Q > 10                                                                       │
│                                                                                                                                      │
│  ⚠ DAISY CHAINING:       Bimodal distribution with peaks at ~200bp AND ~2.6kb                                                        │
│                          Caused by adjacent Level 0 plasmid backbones providing compatible overhangs                                 │
│                          FIX: Use only ODD or EVEN numbered plasmids                                                                 │
│                                                                                                                                      │
│  ⚠ SEVERE ARTIFACTS:     Multiple peaks extending to 5-10kb                                                                          │
│                          Indicates multi-chain concatenation                                                                         │
│                                                                                                                                      │
│  ✗ ANOMALOUS/FAILED:     N50 > 100kb with low quality (Q < 7)                                                                        │
│                          Likely causes: gDNA contamination, incomplete BsaI digestion, plasmid concatemers                          │
│                                                                                                                                      │
│  ODD PLASMIDS:  V0-4.1, V0-4.3, V0-39, V0-41, V0-43, V0-45, V0-47                                                                    │
│  EVEN PLASMIDS: V0-4.2, V0-4.4, V0-40, V0-42, V0-44, V0-46                                                                           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
"""
    ax_key.text(0.5, 0.5, guide_text, transform=ax_key.transAxes, fontsize=10,
               verticalalignment='center', horizontalalignment='center',
               fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='#f8f9fa', edgecolor='#2c3e50', linewidth=2))

    plt.suptitle('SMA-seq Expected Molecular Products Reference', fontsize=18, fontweight='bold', y=0.98)

    return fig


if __name__ == "__main__":
    print("Creating comprehensive reference figure...")

    fig = create_reference_figure()
    output_path = '/data2/repos/ont-ecosystem/sma_configs/figures/molecular_products_reference.png'
    fig.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"  Saved: {output_path}")

    plt.close(fig)
    print("Done!")
