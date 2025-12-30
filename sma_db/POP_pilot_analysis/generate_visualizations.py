#!/usr/bin/env python3
"""Generate visualizations for POP pilot analysis results."""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Load statistics
stats_file = Path(__file__).parent / "all_statistics.json"
with open(stats_file) as f:
    all_stats = json.load(f)

# Extract data for plotting
refs = list(all_stats.keys())
ref_lengths = [all_stats[r]['reference_length'] for r in refs]
mean_read_lengths = [all_stats[r]['mean_length'] for r in refs]
mean_edit_distances = [all_stats[r]['mean_edit_distance'] for r in refs]
min_edit_distances = [all_stats[r]['min_edit_distance'] for r in refs]
accuracy_pcts = [all_stats[r]['accuracy_pct'] for r in refs]
mean_pred_q = [all_stats[r]['mean_predicted_q'] for r in refs]
mean_emp_q = [all_stats[r]['mean_empirical_q'] for r in refs]
q_correct = [all_stats[r]['mean_q_correct'] for r in refs]
q_incorrect = [all_stats[r]['mean_q_incorrect'] for r in refs]
q_differences = [all_stats[r]['q_difference'] for r in refs]
hellinger_dists = [all_stats[r]['hellinger_distance'] for r in refs]

output_dir = Path(__file__).parent

# Figure 1: Summary bar charts (2x3 layout)
fig, axes = plt.subplots(2, 3, figsize=(14, 9))
fig.suptitle('POP Pilot Analysis: Q-Score Statistics by Reference\n(Note: Reference mismatch detected - reads ~2800bp vs refs ~100bp)', fontsize=12)

# Read length vs reference length
ax = axes[0, 0]
x = np.arange(len(refs))
width = 0.35
ax.bar(x - width/2, ref_lengths, width, label='Reference Length', color='steelblue')
ax.bar(x + width/2, mean_read_lengths, width, label='Mean Read Length', color='coral')
ax.set_xlabel('Reference')
ax.set_ylabel('Length (bp)')
ax.set_title('Length Comparison')
ax.set_xticks(x)
ax.set_xticklabels([r.replace('V0-', '') for r in refs], rotation=45, ha='right')
ax.legend(fontsize=8)
ax.set_yscale('log')

# Edit distance
ax = axes[0, 1]
ax.bar(x - width/2, mean_edit_distances, width, label='Mean ED', color='indianred')
ax.bar(x + width/2, min_edit_distances, width, label='Min ED', color='lightcoral')
ax.set_xlabel('Reference')
ax.set_ylabel('Edit Distance')
ax.set_title('Edit Distance')
ax.set_xticks(x)
ax.set_xticklabels([r.replace('V0-', '') for r in refs], rotation=45, ha='right')
ax.legend(fontsize=8)

# Accuracy
ax = axes[0, 2]
bars = ax.bar(x, accuracy_pcts, color='forestgreen', alpha=0.7)
ax.axhline(y=50, color='red', linestyle='--', label='50% baseline', alpha=0.5)
ax.set_xlabel('Reference')
ax.set_ylabel('Accuracy (%)')
ax.set_title('Alignment Accuracy')
ax.set_xticks(x)
ax.set_xticklabels([r.replace('V0-', '') for r in refs], rotation=45, ha='right')
ax.set_ylim(0, max(accuracy_pcts) * 1.2)
ax.legend(fontsize=8)

# Q-scores (predicted vs empirical)
ax = axes[1, 0]
ax.bar(x - width/2, mean_pred_q, width, label='Predicted Q', color='royalblue')
ax.bar(x + width/2, mean_emp_q, width, label='Empirical Q', color='darkorange')
ax.set_xlabel('Reference')
ax.set_ylabel('Q-score')
ax.set_title('Predicted vs Empirical Q')
ax.set_xticks(x)
ax.set_xticklabels([r.replace('V0-', '') for r in refs], rotation=45, ha='right')
ax.legend(fontsize=8)

# Q-scores (correct vs incorrect)
ax = axes[1, 1]
ax.bar(x - width/2, q_correct, width, label='Q (Correct)', color='seagreen')
ax.bar(x + width/2, q_incorrect, width, label='Q (Incorrect)', color='crimson')
ax.set_xlabel('Reference')
ax.set_ylabel('Q-score')
ax.set_title('Q: Correct vs Incorrect Basecalls')
ax.set_xticks(x)
ax.set_xticklabels([r.replace('V0-', '') for r in refs], rotation=45, ha='right')
ax.legend(fontsize=8)

# Q difference and Hellinger distance
ax = axes[1, 2]
colors = ['green' if d > 0 else 'red' for d in q_differences]
ax.bar(x, q_differences, color=colors, alpha=0.7)
ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
ax.set_xlabel('Reference')
ax.set_ylabel('ΔQ (Correct - Incorrect)')
ax.set_title('Q-Score Difference\n(Negative = problematic)')
ax.set_xticks(x)
ax.set_xticklabels([r.replace('V0-', '') for r in refs], rotation=45, ha='right')

plt.tight_layout()
plt.savefig(output_dir / 'summary_barcharts.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved: summary_barcharts.png")

# Figure 2: Summary table
fig, ax = plt.subplots(figsize=(14, 5))
ax.axis('off')

# Table data
headers = ['Reference', 'Ref Len', 'Mean Read', 'Mean ED', 'Min ED', 'Accuracy%',
           'Q(pred)', 'Q(emp)', 'Q(corr)', 'Q(incorr)', 'ΔQ', 'Hellinger']
table_data = []
for r in refs:
    s = all_stats[r]
    table_data.append([
        r,
        f"{s['reference_length']}",
        f"{s['mean_length']:.0f}",
        f"{s['mean_edit_distance']:.0f}",
        f"{s['min_edit_distance']}",
        f"{s['accuracy_pct']:.1f}",
        f"{s['mean_predicted_q']:.1f}",
        f"{s['mean_empirical_q']:.2f}",
        f"{s['mean_q_correct']:.1f}",
        f"{s['mean_q_incorrect']:.1f}",
        f"{s['q_difference']:.2f}",
        f"{s['hellinger_distance']:.3f}"
    ])

table = ax.table(cellText=table_data, colLabels=headers, loc='center', cellLoc='center')
table.auto_set_font_size(False)
table.set_fontsize(9)
table.scale(1.2, 1.5)

# Color negative Q differences red
for i, row in enumerate(table_data):
    q_diff = float(row[10])
    if q_diff < 0:
        table[(i+1, 10)].set_facecolor('#ffcccc')

ax.set_title('POP Pilot Analysis Summary\n(Red cells indicate Q(incorrect) > Q(correct) - problematic)',
             fontsize=12, pad=20)

plt.savefig(output_dir / 'summary_table.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved: summary_table.png")

# Figure 3: Length distribution comparison
fig, ax = plt.subplots(figsize=(10, 6))
positions = np.arange(len(refs))

# Create box plot style comparison
for i, r in enumerate(refs):
    s = all_stats[r]
    # Reference length (marker)
    ax.scatter(i, s['reference_length'], marker='s', s=100, c='blue', zorder=5, label='Reference' if i == 0 else '')
    # Mean read length (marker with error indication)
    ax.scatter(i, s['mean_length'], marker='o', s=100, c='red', zorder=5, label='Mean Read Length' if i == 0 else '')
    # Connect them
    ax.plot([i, i], [s['reference_length'], s['mean_length']], 'k--', alpha=0.3)

ax.set_xlabel('Reference')
ax.set_ylabel('Length (bp)')
ax.set_title('Length Mismatch: Reference vs Read Length\n(Large gap indicates reference sequences are incomplete)')
ax.set_xticks(positions)
ax.set_xticklabels([r.replace('V0-', '') for r in refs], rotation=45, ha='right')
ax.legend()
ax.set_yscale('log')
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(output_dir / 'length_mismatch.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved: length_mismatch.png")

# Figure 4: Q-score analysis
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# Q difference pattern
ax = axes[0]
bars = ax.bar(refs, q_differences, color=['green' if d > 0 else 'red' for d in q_differences])
ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
ax.set_xlabel('Reference')
ax.set_ylabel('ΔQ = Q(correct) - Q(incorrect)')
ax.set_title('Q-Score Discrimination\nPositive = basecaller correctly assigns higher Q to correct calls')
ax.set_xticklabels([r.replace('V0-', '') for r in refs], rotation=45, ha='right')
ax.grid(True, alpha=0.3, axis='y')

# Predicted vs Empirical Q
ax = axes[1]
ax.scatter(mean_pred_q, mean_emp_q, s=100, c='purple', alpha=0.7)
for i, r in enumerate(refs):
    ax.annotate(r.replace('V0-', ''), (mean_pred_q[i], mean_emp_q[i]),
                xytext=(5, 5), textcoords='offset points', fontsize=8)
ax.plot([0, 15], [0, 15], 'k--', alpha=0.5, label='y=x (ideal)')
ax.set_xlabel('Mean Predicted Q')
ax.set_ylabel('Mean Empirical Q')
ax.set_title('Predicted vs Empirical Q-Score\n(Points far below line = Q overestimates accuracy)')
ax.legend()
ax.grid(True, alpha=0.3)
ax.set_xlim(9, 12)
ax.set_ylim(0, 1)

plt.tight_layout()
plt.savefig(output_dir / 'qscore_analysis.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved: qscore_analysis.png")

# Generate summary report
report = """
# POP Pilot Analysis Summary

## Key Finding: Reference Mismatch Detected

The analysis reveals a significant issue with the reference sequences:
- **Read lengths**: ~2600-3400 bp (mean across references)
- **Reference lengths**: 88-115 bp (target insert sequences only)

This indicates the sequencing reads contain the **full plasmid** (backbone + adapters + target)
while the reference sequences are only the **target insert** regions.

## Statistics Summary

| Reference | Ref Len | Mean Read | Accuracy | ΔQ (Corr-Incorr) | Note |
|-----------|---------|-----------|----------|------------------|------|
"""

for r in refs:
    s = all_stats[r]
    note = "✗ Q inverted" if s['q_difference'] < 0 else "~"
    report += f"| {r} | {s['reference_length']} bp | {s['mean_length']:.0f} bp | {s['accuracy_pct']:.1f}% | {s['q_difference']:.2f} | {note} |\n"

report += """
## Interpretation

1. **100% no_size_match**: All reads were assigned via alignment because they don't match
   expected reference sizes (±15% tolerance).

2. **Low accuracy (2.8-4.1%)**: Expected when aligning ~2800bp reads to ~100bp references.
   Only the portion matching the target insert aligns correctly.

3. **Negative ΔQ values**: Most references show Q(incorrect) > Q(correct), which is unusual.
   This occurs because:
   - The "correct" basecalls are only where the short reference aligns
   - Most of the read (plasmid backbone) is marked as "incorrect" insertions
   - The backbone portions often have high Q-scores

## Recommendations

1. **Use full-length reference sequences** including:
   - Barcode/adapter sequences
   - Plasmid backbone
   - Full construct layout

2. **Or trim reads** to extract only the target insert region before analysis.

3. **Alternative**: Use the backbone sequence as a reference to assess overall read quality,
   then extract and analyze the target region separately.

## Files Generated

- `all_statistics.json` - Per-reference statistics
- `assignment_summary.json` - Read assignment breakdown
- `summary_barcharts.png` - Visual summary of key metrics
- `summary_table.png` - Tabular summary
- `length_mismatch.png` - Reference vs read length comparison
- `qscore_analysis.png` - Q-score discrimination analysis
"""

with open(output_dir / 'analysis_report.md', 'w') as f:
    f.write(report)
print(f"Saved: analysis_report.md")

print("\nVisualization complete!")
