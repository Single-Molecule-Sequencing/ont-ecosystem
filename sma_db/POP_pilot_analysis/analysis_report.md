
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
| V0-15 | 99 bp | 2831 bp | 3.5% | -0.49 | ✗ Q inverted |
| V0-16 | 112 bp | 3419 bp | 3.3% | 0.01 | ~ |
| V0-17 | 90 bp | 3246 bp | 2.8% | -0.28 | ✗ Q inverted |
| V0-18 | 115 bp | 2799 bp | 4.1% | -0.78 | ✗ Q inverted |
| V0-19 | 115 bp | 2834 bp | 4.0% | -0.66 | ✗ Q inverted |
| V0-20 | 88 bp | 2843 bp | 3.1% | -1.03 | ✗ Q inverted |
| V0-21 | 106 bp | 2850 bp | 3.7% | -0.81 | ✗ Q inverted |
| V0-22 | 100 bp | 2657 bp | 3.8% | -0.77 | ✗ Q inverted |
| V0-23 | 101 bp | 2811 bp | 3.6% | -0.65 | ✗ Q inverted |

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
