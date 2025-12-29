# Math-Skills Integration Guide

This document maps the authoritative mathematical content (All_Math.tex) to
the computational skills in the ont-ecosystem for seamless analysis workflows.

**Version:** 1.0.0
**Source:** `data/math/All_Math.tex` (1180 lines, authoritative)
**Date:** 2025-12-28

---

## Mathematical Framework Overview

The SMS Haplotype Framework defines a comprehensive mathematical model spanning:

1. **Error Quantification** - Phred scores, edit distance, quality metrics
2. **Basecalling Model** - Signal processing, read generation
3. **Confusion Matrix** - Sequence classification, error models
4. **Haplotype Classification** - Bayesian inference, likelihood computation
5. **Diplotypes & Polyploidy** - Multi-allelic classification
6. **Haplotagging** - Read-to-molecule assignment
7. **Plasmid Replication** - Purity bounds, mutation accumulation
8. **Cas9 Enrichment** - Targeted sequencing probability

---

## Skill-to-Math Mapping

### end-reason (QC Analysis)

**Mathematical Foundation:**
- Section 2: Error Quantification
- Weighted edit distance: `E_α(s,r) = α·M(s,r) + (1-α)·I(s,r)`
- Per-read quality: `Q^read_ijk = -10·log₁₀(p̂^read_ijk)`

**Key Equations:**
```latex
% Normalized weighted edit distance
\tilde{d}_\alpha(s,r) = \frac{E_\alpha(s,r)}{L(s)}

% Per-read empirical quality
\hat{p}^{\text{read}}_{ijk} = \min\{1, \max(L(s_{ij})^{-2}, \tilde{d}_\alpha)\}
Q^{\text{read}}_{ijk} = -10 \log_{10} \hat{p}^{\text{read}}_{ijk}
```

**Skill Implementation:**
- `bin/end_reason.py` - End reason distribution analysis
- `bin/ont_endreason_qc.py` - QC metrics and visualization
- Uses `signal_positive_pct` to assess adaptive sampling quality

---

### ont-align (Alignment & Edit Distance)

**Mathematical Foundation:**
- Section 2.1: Levenshtein edit distance
- Section 6: Alignment-based quality metric

**Key Equations:**
```latex
% Levenshtein edit distance
d(s,r) \in \mathbb{N}_0

% Alignment quality score
s_i = \begin{cases}
    1 - p_i, & g_i = b_i \\
    p_i, & g_i \neq b_i \\
    0, & \text{gap}
\end{cases}

% Mean correctness and Phred quality
M = \frac{1}{N} \sum_{i=1}^N s_i
Q_{\text{new}} = -10 \log_{10}(1-M)
```

**Skill Implementation:**
- `bin/ont_align.py` - Uses edlib for edit distance computation
- `editdist` subcommand for Levenshtein distance
- Supports NW (global), HW (semi-global), SHW (infix) modes

---

### dorado-bench-v2 (Basecalling)

**Mathematical Foundation:**
- Section 3: Single-Molecule Sequencing and Basecalling Model
- Section 4: Sequence Counts and Confusion Matrix

**Key Equations:**
```latex
% Basecalling transformation
r_{ik} = f(\mathbf{t}^{(i)})

% Per-base Phred quality
Q_{ikl} = -10 \log_{10}(p_{ikl})

% Basecaller-implied error probability
\hat{p}^{\text{bc}}_{ik} = \frac{1}{L(r_{ik})} \sum_{\ell=1}^{L(r_{ik})} 10^{-Q_{ik\ell}/10}
```

**Skill Implementation:**
- `bin/dorado_basecall.py` - Basecalling workflow generation
- Model management (fast, hac, sup)
- SLURM job generation for HPC

---

### ont-experiments-v2 (Registry & Orchestration)

**Mathematical Foundation:**
- Section 4: Experiments and global sequence index
- Confusion matrix construction from standards

**Key Equations:**
```latex
% Experiment set
\mathcal{E} = \{e_1, \dots, e_N\}

% Count vector per experiment
c^{(e)}_j = |\{r_{ek} \in R : r_{ek} = u_j\}|

% Total reads
N_e = \sum_{j=1}^{U_e} c^{(e)}_j
```

**Skill Implementation:**
- `bin/ont_experiments.py` - Core registry and orchestration
- Pattern B provenance tracking
- Event-sourced experiment history

---

### ont-pipeline (Workflow Orchestration)

**Mathematical Foundation:**
- Pipeline Factorization Theorem: `P(h,g,u,d,ℓ,σ,r)`
- 9 pipeline stages

**Pipeline Stages:**
| Stage | Symbol | Description | Math Section |
|-------|--------|-------------|--------------|
| Haplotype | h | Prior selection | Section 8.1 |
| Genome | g | Molecule set | Section 8.2 |
| Unique | u | Mutation accumulation | Section 8.2 |
| DNA fragments | d | Fragmentation | Section 8.3 |
| Labeled | ℓ | Library prep | Section 8.3 |
| Signal | σ | Sequencing | Section 3 |
| Reads | r | Basecalling | Section 3 |
| Confusion | C | Error model | Section 4.3 |
| Alignment | A | Mapping | Section 2 |

**Skill Implementation:**
- `bin/ont_pipeline.py` - Multi-step workflow execution
- Stage-aware provenance tracking
- Unified QC integration

---

### Haplotype Classification (textbook/equations.yaml)

**Mathematical Foundation:**
- Section 8: Haplotype Classification
- Section 9: Diplotypes and Polyploidy

**Core Equations:**
```latex
% Haplotype likelihood (marginalizing over stages)
P(r|h_i) = \sum_{u} \sum_{d} \sum_{\ell}
    P(r|\ell,\theta_{seq}) P(\ell|d,\theta_{lab})
    P(d|u,\theta_{frag}) P(u|h_i,\mu,n_{div},L)

% Posterior probability
P(h_i|R) = \frac{P(R|h_i) P(h_i)}{\sum_{j=1}^p P(R|h_j) P(h_j)}

% Likelihood ratio decision
\text{LR}_i(R) = \frac{P(h_i|R)}{1 - P(h_i|R)}
```

**Skill Implementation:**
- Equations 4.1-4.15 in `textbook/equations.yaml`
- Core equations CE#1-15 in textbook framework

---

## Equation Database Statistics

| Source | Equations | Chapters | Variables |
|--------|-----------|----------|-----------|
| All_Math.tex | 50+ | 12 sections | ~80 defined |
| equations.yaml | 87 | 11 chapters | ~120 referenced |
| Total unique | ~100 | - | ~150 |

---

## Computational Implementation Patterns

### Pattern A: Direct Python Implementation

```python
# From All_Math.tex Section 2
def weighted_edit_distance(s, r, alpha=0.5):
    """Compute weighted edit distance (Eq. 2.3-2.4)"""
    import edlib
    result = edlib.align(s, r, task='path')
    cigar = result['cigar']
    M = count_mismatches(cigar)
    I = count_indels(cigar)
    E_alpha = alpha * M + (1 - alpha) * I
    return E_alpha / len(s)

# From All_Math.tex Section 3
def phred_to_prob(Q):
    """Convert Phred score to error probability (Eq. 3.4)"""
    return 10 ** (-Q / 10)

def prob_to_phred(p):
    """Convert error probability to Phred score (Eq. 3.4)"""
    import math
    return -10 * math.log10(max(p, 1e-10))
```

### Pattern B: Vectorized NumPy Implementation

```python
import numpy as np

# Basecaller-implied error probability (Eq. 3.6)
def mean_basecaller_quality(q_scores):
    """Compute mean basecaller quality for a read"""
    probs = 10 ** (-np.array(q_scores) / 10)
    p_hat_bc = np.mean(probs)
    Q_bc = -10 * np.log10(p_hat_bc)
    return Q_bc

# Alignment quality score (Eq. 6.2)
def alignment_quality_score(matches, errors, q_scores):
    """Compute alignment-based quality metric"""
    probs = 10 ** (-np.array(q_scores) / 10)
    scores = np.where(matches, 1 - probs, probs)
    M = np.mean(scores)
    Q_new = -10 * np.log10(1 - M)
    return M, Q_new
```

---

## Cross-Reference Index

### From All_Math.tex to Skills

| Section | Equation | Skill | Function |
|---------|----------|-------|----------|
| 2.1 | d(s,r) | ont-align | `editdist` |
| 2.2 | E_α(s,r) | ont-align | weighted_edit |
| 2.3 | Q^read | end-reason | quality_metrics |
| 3.2 | Q_ikl | dorado-bench | basecall |
| 4.3 | C_ij | ont-experiments | confusion_matrix |
| 5 | Q ≥ -10log₁₀(p) | ont-pipeline | quality_check |
| 8.4 | P(h_i\|R) | textbook | classification |
| 9 | C(γ,N) | textbook | cost_optimization |
| 10 | LR_j(r) | textbook | haplotagging |
| 11 | P_pure(k) | textbook | purity_bounds |
| 12 | p_dual(G) | textbook | cas9_probability |

### From Skills to All_Math.tex

| Skill Command | Math Section | Key Equations |
|--------------|--------------|---------------|
| `end_reason.py analyze` | 2, 3 | 2.3, 3.4 |
| `ont_align.py editdist` | 2.1 | 2.1 |
| `ont_align.py align` | 6 | 6.1-6.3 |
| `dorado_basecall.py` | 3 | 3.1-3.5 |
| `ont_experiments.py run` | 4 | 4.1-4.5 |
| `ont_pipeline.py` | All | Factorization theorem |

---

## Usage Examples

### Computing Quality Metrics from End Reason Analysis

```bash
# Run end reason analysis
ont_experiments.py run end_reasons exp-abc123 --json results.json

# The skill computes:
# - signal_positive_pct (from Eq. 2.3)
# - mean_quality (from Eq. 3.6)
# - read_length distributions
```

### Edit Distance Computation

```bash
# Direct Levenshtein distance
ont_align.py editdist "ATGCATGC" "ATGGATGC"
# → Edit distance: 1 (one substitution)

# With CIGAR and normalization (Eq. 2.4)
ont_align.py editdist "ATGCATGC" "ATGGATGC" --cigar --normalize
# → Edit distance: 1, CIGAR: 3=1X4=, Normalized: 0.125
```

### Confusion Matrix from Standards

```bash
# Build confusion matrix from high-purity standards
ont_experiments.py run confusion_matrix --standards exp-std1,exp-std2

# Outputs C_ij matrix (Eq. 4.7-4.9)
# - True positive rates per sequence
# - Misclassification probabilities
```

---

## Authoritative Sources

1. **Primary Math Reference:** `data/math/All_Math.tex` (1180 lines)
   - Comprehensive, harmonized mathematical definitions
   - All variable notation defined locally per section
   - Includes proofs and derivations

2. **Equation Database:** `textbook/equations.yaml` (87 equations)
   - Chapter-organized equation index
   - Includes worked examples and interpretations
   - Links to textbook sections

3. **Variable Database:** `textbook/variables.yaml` (~120 variables)
   - Complete variable definitions
   - Physical meanings and units
   - Cross-references

4. **Extracted Content:** `textbook/extracted/`
   - 15 figures (LaTeX source)
   - 145 tables (LaTeX source)
   - Metadata index (JSON)

---

## Integration Checklist

- [x] All_Math.tex source integrated into data/math/
- [x] Equations.yaml covers chapters 4-14
- [x] Variables.yaml complete
- [x] Extracted figures/tables synced
- [x] Skills implement core mathematical operations
- [x] Provenance tracking captures computational parameters
- [ ] Automated equation validation against All_Math.tex
- [ ] Interactive equation viewer in dashboard

---

## Future Enhancements

1. **Equation Execution Engine** - Python implementations of all equations
2. **Symbolic Verification** - SymPy validation of equation relationships
3. **Interactive Notebooks** - Jupyter integration for equation exploration
4. **Visualization Library** - Plot generators for all key equations
