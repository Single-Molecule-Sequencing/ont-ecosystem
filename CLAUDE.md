# Claude Code Agent Instructions for ont-ecosystem

## Purpose
ont-ecosystem is the SMS Lab's analysis workflow system for Oxford Nanopore sequencing. It provides event-sourced experiment tracking and provenance-preserving analysis pipelines.

## Boot Ritual (ALWAYS do this first)

1. **Read Progress Log** (if exists)
   ```bash
   cat .agent-memory/progress.log 2>/dev/null | tail -50 || echo "No progress log"
   ```

2. **Check Current Experiments**
   ```bash
   ont_experiments.py status --json 2>/dev/null || ont_experiments.py list 2>/dev/null | head -20
   ```

3. **Read Feature Backlog** (if exists)
   ```bash
   cat .agent-memory/feature_backlog.yaml 2>/dev/null || echo "No backlog"
   ```

4. **Identify Next Task**
   - Find first feature with `status: pending` or `status: failing`
   - Check that all `dependencies` have `status: passing`
   - Pick ONE task to work on

## Key Commands

### Experiment Management
```bash
# List all experiments
ont_experiments.py list

# Show experiment details
ont_experiments.py show exp-001

# Check experiment status
ont_experiments.py status exp-001 --json

# View provenance chain
ont_experiments.py history exp-001

# Register new experiment
ont_experiments.py register exp-001 --flowcell FLO-PRO114M --kit SQK-LSK114
```

### Analysis (Pattern B - ALWAYS use for provenance)
```bash
# Basecalling
ont_experiments.py run basecall exp-001 --model sup

# Alignment
ont_experiments.py run align exp-001 --ref GRCh38

# End reason QC
ont_experiments.py run end_reasons exp-001

# Full pipeline
ont_experiments.py run pipeline exp-001
```

### Direct Tools (use sparingly - no provenance)
```bash
# Direct basecalling (only for testing)
dorado_basecall.py --input /path/to/pod5 --output /path/to/bam

# End reason analysis
end_reason.py --input exp-001.bam --output qc_report.json

# Monitoring
ont_monitor.py --experiment exp-001
```

## Work Protocol

### Before Making Changes
- Run `ont_experiments.py status` to understand current state
- Check registry: `cat ~/ont-registry/events.jsonl | tail -20`
- Run existing tests: `make test`

### During Implementation
- Make atomic commits for each logical change
- Use Pattern B: run analyses through `ont_experiments.py run` for provenance
- Tag events with pipeline stages: h, g, u, d, ℓ, σ, r, C, A

### After Implementation
1. Run tests: `make test`
2. Verify provenance: `ont_experiments.py history exp-001`
3. If using feature backlog:
   - Update feature status to `passing` or `failing`
   - Append to progress log:
   ```
   ## [TIMESTAMP] Session: [FEATURE_ID]
   - Task: [what you attempted]
   - Result: [passing/failing]
   - Notes: [observations]
   - Next: [suggested next step]
   ```

## Pipeline Stage Reference

| Stage | Symbol | Description | Key Analysis |
|-------|--------|-------------|--------------|
| h | Haplotype | Prior from population | Haplotype calling |
| g | Standards | Synthetic constructs | Reference validation |
| u | Capture | Target enrichment | On-target rate |
| d | Fragment | DNA fragmentation | N50 analysis |
| ℓ | Loading | Library prep | Pore occupancy |
| σ | Signal | Raw current | Signal QC |
| r | Reads | Basecalling | Q score analysis |
| C | Cas9 | Enrichment toggle | Enrichment metrics |
| A | Adaptive | Adaptive toggle | End reason QC |

## Quality Thresholds

| Metric | Threshold | Check Command |
|--------|-----------|---------------|
| Q20 accuracy | > 99% | `ont_experiments.py run qc exp-001` |
| Mapping rate | > 95% | Check alignment stats |
| Pore occupancy | > 50% | Check run summary |
| Adaptive enrichment | > 2:1 ratio | End reason analysis |

## Registry Structure

```
~/ont-registry/
├── events.jsonl          # Append-only event log
├── experiments/          # Experiment metadata
│   └── exp-001.yaml
└── checksums/            # Output file checksums
```

## Integration with SMS_core

This repository uses SMS_core for:
- Math definitions (registry/math/)
- Pipeline stage definitions
- Analysis skill specifications

## Common Patterns

### CYP2D6 Pharmacogenomics Workflow
```bash
ont_experiments.py register exp-cyp2d6-001 --enrichment cas9 --target CYP2D6
ont_experiments.py run basecall exp-cyp2d6-001 --model sup
ont_experiments.py run align exp-cyp2d6-001 --ref T2T
ont_experiments.py run phase exp-cyp2d6-001
ont_experiments.py run haplotype exp-cyp2d6-001
```

### Adaptive Sampling Analysis
```bash
ont_experiments.py run end_reasons exp-001
ont_experiments.py run adaptive_qc exp-001
```

## Troubleshooting

### No experiments found
```bash
ont_experiments.py discover /path/to/data --register
```

### Missing provenance
Check that analyses were run through `ont_experiments.py run`, not directly.

### Registry corruption
```bash
# Backup and rebuild
cp ~/ont-registry/events.jsonl ~/ont-registry/events.jsonl.bak
ont_experiments.py rebuild-registry
```
