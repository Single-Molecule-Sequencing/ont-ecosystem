# Metric Interpretation Guide

Reference for understanding ONT run monitoring metrics and diagnosing issues.

## Expected Ranges by Device

### MinION / GridION

| Metric | Good | Acceptable | Poor |
|--------|------|------------|------|
| Yield/48h | > 15 Gb | 10-15 Gb | < 10 Gb |
| Mean Q-score | > 12 | 10-12 | < 10 |
| N50 | > 10 kb | 5-10 kb | < 5 kb |
| Active pores | > 60% | 40-60% | < 40% |
| Pass rate | > 85% | 75-85% | < 75% |
| Throughput | > 1 Gb/h | 0.5-1 Gb/h | < 0.5 Gb/h |

### PromethION

| Metric | Good | Acceptable | Poor |
|--------|------|------------|------|
| Yield/72h | > 100 Gb | 50-100 Gb | < 50 Gb |
| Mean Q-score | > 12 | 10-12 | < 10 |
| N50 | > 10 kb | 5-10 kb | < 5 kb |
| Active pores | > 70% | 50-70% | < 50% |
| Pass rate | > 85% | 75-85% | < 75% |
| Throughput | > 5 Gb/h | 2-5 Gb/h | < 2 Gb/h |

## Basecalling Model Impact

| Model Tier | Expected Q-score | Speed | Use Case |
|------------|------------------|-------|----------|
| fast | 8-12 | Fastest | Quick preview |
| hac | 10-14 | Medium | Standard analysis |
| sup | 12-18 | Slowest | Variant calling, methylation |

## Troubleshooting Guide

### Low Yield

**Symptoms**: Total bases significantly below expected

**Common causes**:
1. **Pore depletion**: Check active pore percentage over time
2. **Library issues**: Low molarity, degraded DNA
3. **Flow cell quality**: Check initial pore count
4. **Blockages**: High adapter/unclassified states

**Diagnosis**:
```bash
# Check pore activity trend
ont_monitor.py /path/to/run --csv pore_history.csv
```

### Low Quality (Q-score)

**Symptoms**: Mean Q-score < 10

**Common causes**:
1. **Old flow cell**: Pore degradation
2. **Library contamination**: Salts, detergents
3. **Wrong chemistry**: Mismatched kit/flow cell
4. **Temperature issues**: Check run environment

**Actions**:
- Compare Q-score trend over time
- Check for sudden drops (indicates contamination)
- Verify kit compatibility

### Short Reads (Low N50)

**Symptoms**: N50 significantly below input DNA length

**Common causes**:
1. **DNA fragmentation**: Sample handling, extraction method
2. **Over-transposition**: Too much transposase
3. **Library prep issues**: Excessive pipetting

**Diagnosis**:
- Check read length distribution shape
- Bimodal = specific fragmentation event
- Right-skewed tail = normal, some long fragments remain

### High Fail Rate

**Symptoms**: Pass rate < 75%

**Common causes**:
1. **Low signal quality**: Pore issues
2. **Contamination**: Non-target sequences
3. **Basecalling issues**: Wrong model

**Actions**:
- Check end_reason distribution (use end-reason skill)
- Verify basecalling model matches chemistry

### Decreasing Throughput

**Symptoms**: Reads/hour declining over run

**Normal behavior**: Moderate decline expected as pores deplete

**Abnormal decline causes**:
1. **Bubbles**: Air in flow cell
2. **Protein aggregation**: Library buildup
3. **Temperature fluctuation**: Check environment
4. **Power issues**: Unstable supply

## Metric Correlations

### Healthy Run Pattern
```
✓ Yield increasing steadily
✓ Q-score stable or slight decline
✓ N50 consistent
✓ Active pores declining slowly
✓ Throughput declining slowly
```

### Problem Run Pattern
```
✗ Yield plateaus early
✗ Q-score drops suddenly
✗ N50 varies wildly
✗ Active pores drop sharply
✗ Throughput drops to near-zero
```

## Alert Priority

| Priority | Alerts | Action |
|----------|--------|--------|
| Critical | Active pores < 20% | Consider stopping run |
| Critical | Throughput near zero | Investigate immediately |
| Warning | Q-score < 10 | Monitor, may recover |
| Warning | N50 < 1 kb | Check library |
| Info | Metrics declining | Normal over long runs |

## Reference Values

### Chemistry-Specific

**R10.4.1 (current)**
- Expected Q: 12-18 (SUP model)
- Raw accuracy: ~99%

**R9.4.1 (legacy)**
- Expected Q: 10-14 (SUP model)
- Raw accuracy: ~95-97%

### Application-Specific

**Whole Genome Sequencing**
- Target coverage: 30-60x
- N50 goal: > 10 kb
- Yield goal: Sample genome size × coverage

**Targeted Sequencing (Adaptive Sampling)**
- On-target enrichment: 5-50x
- Expect lower overall throughput
- Higher unblock_mux_change end reasons (normal)

**cDNA / RNA**
- Typically shorter reads
- N50: 1-5 kb typical
- Higher variability in lengths
