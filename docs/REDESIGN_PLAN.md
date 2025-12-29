# ONT-Ecosystem v3.0 Comprehensive Redesign Plan

**Date**: 2025-12-28
**Status**: Draft
**Goal**: Transform ont-ecosystem into an integrated AI-native bioinformatics platform with unified math registry, pipeline provenance, and multi-agent support.

---

## Executive Summary

This plan integrates three key components:
1. **Current ont-ecosystem** - Domain memory, experiment registry, skill-based analysis
2. **SMS_infrastructure patterns** - Pipeline stages (h,g,u,d,ℓ,σ,r,C,A), math registry, schema validation
3. **Lab math framework** (All_Math PDF) - Bayesian haplotype classification, error models, Phred scores

The result: A unified platform supporting Claude Code, Claude CLI, and GitHub Copilot agents with persistent domain knowledge.

---

## Phase 1: Math Registry Integration

### 1.1 Create Registry Structure
```
registry/
├── math/
│   ├── schema.json           # JSON schema for equation definitions
│   ├── core/
│   │   ├── phred.yaml        # Q = -10 log₁₀(P_error)
│   │   ├── error_rates.yaml  # Substitution, insertion, deletion
│   │   └── posterior.yaml    # P(h|R) Bayesian classification
│   ├── pipeline/
│   │   ├── haplotype_prior.yaml      # P(h) from population genetics
│   │   ├── signal_likelihood.yaml    # P(σ|h) signal model
│   │   └── basecall_likelihood.yaml  # P(r|σ) basecaller model
│   └── derived/
│       ├── confusion_matrix.yaml     # Empirical error estimates
│       ├── diplotype.yaml            # P(d₁,d₂|R) joint probability
│       └── haplotag.yaml             # Read-level assignment
├── pipeline/
│   ├── stages.yaml           # 9 pipeline stages from SMS_infrastructure
│   └── artifacts.yaml        # Output definitions per stage
└── schemas/
    ├── math_definition.json
    ├── pipeline_stage.json
    └── experiment.json
```

### 1.2 Core Math Definitions (from All_Math PDF)

| ID | Name | Formula | Pipeline Stage |
|----|------|---------|----------------|
| `phred_score` | Phred Quality | Q = -10 log₁₀(P_error) | r |
| `posterior_haplotype` | Bayesian Posterior | P(h\|R) = P(R\|h)P(h) / ΣP(R\|h')P(h') | A |
| `error_identity` | Error Identity | 1 - (S+I+D)/N | r |
| `confusion_matrix` | Empirical Errors | P(called=b \| true=a) | r |
| `diplotype_joint` | Diplotype Probability | P(d₁,d₂\|R) with symmetry constraint | A |
| `haplotag_posterior` | Haplotag Assignment | P(h\|r) for single read | A |
| `cost_decision` | Cost-Based Classification | argmin Σ L(h,ĥ)P(h\|R) | A |

### 1.3 Implementation Tasks

- [ ] Create `registry/math/schema.json` (adapt from new_sms)
- [ ] Create `bin/ont_math.py` - CLI for math registry queries
- [ ] Implement `list`, `get`, `validate`, `latex`, `python` subcommands
- [ ] Add tests for math registry operations
- [ ] Create initial YAML files for core equations

---

## Phase 2: Pipeline Stage Framework

### 2.1 Adopt 9-Stage Pipeline Model

From SMS_infrastructure `stages.yaml`:

| Stage | Symbol | Name | Probability Term |
|-------|--------|------|------------------|
| h | h | Haplotype Selection | P(h) |
| g | g | Standard Construction | P(g\|h) |
| u | u | Guide Design & Fragmentation | P(u\|g) |
| d | d | Post-Cas9 Fragmentation | P(d\|u,C) |
| ℓ | ℓ | Library Loading | P(ℓ\|d,C) |
| σ | σ | Signal Acquisition | P(σ\|ℓ,A) |
| r | r | Basecalling | P(r\|σ,A) |
| C | C | Cas9 Toggle | P(C) |
| A | A | Adaptive Sampling Toggle | P(A) |

### 2.2 Map Current Skills to Pipeline Stages

| Skill | Primary Stage(s) | Outputs |
|-------|------------------|---------|
| `end-reason` | σ, r | Read disposition analysis |
| `ont-align` | r, A | Alignment + edit distance |
| `dorado-bench` | r | Basecalling benchmarks |
| `ont-pipeline` | r, A | Multi-step workflows |
| `ont-monitor` | σ | Real-time run monitoring |

### 2.3 Implementation Tasks

- [ ] Copy `registry/pipeline/stages.yaml` from SMS_infrastructure
- [ ] Create `bin/ont_pipeline_stages.py` - pipeline stage queries
- [ ] Add `--stage` parameter to `ont_experiments.py run`
- [ ] Link skill outputs to pipeline stage artifacts
- [ ] Generate provenance chain showing stage→stage flow

---

## Phase 3: Enhanced Domain Memory

### 3.1 Current State (Already Implemented)

- Task/TaskList/BootupContext dataclasses
- `tasks.yaml` and `PROGRESS.md` per experiment
- CLI: `init-tasks`, `tasks`, `progress`, `next`
- `bootup_check()` function for standardized bootup

### 3.2 Enhancements

#### 3.2.1 Agent-Specific Context Files

```
~/.ont-registry/experiments/exp-abc123/
├── tasks.yaml           # Existing
├── PROGRESS.md          # Existing
├── CLAUDE.md            # Claude Code context
├── COPILOT.md           # GitHub Copilot context (simplified)
└── agent_sessions/
    ├── 2025-12-28_14:30_claude.log
    └── 2025-12-28_15:00_copilot.log
```

#### 3.2.2 Feature Backlog with Dependencies

```yaml
# tasks.yaml v2.0
version: "2.0"
experiment_id: "exp-abc123"
tasks:
  - id: "qc-raw"
    name: "Run raw signal QC"
    stage: "σ"
    status: "passing"
    test_command: "ont_experiments.py run end-reason exp-abc123"
    dependencies: []

  - id: "basecall-sup"
    name: "Basecall with SUP model"
    stage: "r"
    status: "pending"
    test_command: "ont_experiments.py run dorado-bench exp-abc123 --model sup"
    dependencies: ["qc-raw"]
```

#### 3.2.3 Math-Aware Progress Logging

```markdown
## 2025-12-28 14:30 Session: basecall-validation

- **Task**: Validate basecalling accuracy
- **Stage**: r (Basecalling)
- **Result**: PASSING
- **Metrics**:
  - Q20: 94.2% (threshold: 90%)
  - Identity: 99.1%
  - Math: phred_score, error_identity applied
- **Next**: Run haplotype classification (stage A)
```

### 3.3 Implementation Tasks

- [ ] Extend Task dataclass with `stage`, `dependencies`, `test_command`
- [ ] Add TaskList v2.0 with dependency resolution
- [ ] Create `ont_experiments.py run --auto` for dependency-aware execution
- [ ] Add agent session logging
- [ ] Link task outputs to math definitions

---

## Phase 4: CLI Consolidation

### 4.1 Unified Command Structure

```bash
# Core experiment management (existing)
ont_experiments.py init --git
ont_experiments.py discover /path --register
ont_experiments.py run <skill> <exp-id>
ont_experiments.py history <exp-id>

# Domain memory (existing)
ont_experiments.py tasks <exp-id>
ont_experiments.py progress <exp-id>
ont_experiments.py next <exp-id> [--json]
ont_experiments.py init-tasks <exp-id>

# New: Pipeline stage queries
ont_experiments.py stages                    # List all 9 stages
ont_experiments.py stage <stage-id>          # Show stage details
ont_experiments.py artifacts <exp-id>        # Show outputs by stage

# New: Math registry queries
ont_experiments.py math list                 # List all equations
ont_experiments.py math get <eq-id>          # Show equation details
ont_experiments.py math latex <eq-id>        # Output LaTeX
ont_experiments.py math python <eq-id>       # Output Python implementation
ont_experiments.py math validate             # Validate registry

# New: Agent bootup (enhanced)
ont_experiments.py bootup <exp-id> [--agent claude|copilot|generic]
```

### 4.2 Implementation Tasks

- [ ] Add `stages`, `stage`, `artifacts` subcommands
- [ ] Add `math` subcommand group
- [ ] Enhance `bootup` with agent-specific output formats
- [ ] Add `--json` output for all commands
- [ ] Create man-page style help for each command

---

## Phase 5: Schema Validation

### 5.1 JSON Schemas

Create validation schemas for:
- `math_definition.json` - Math registry entries
- `pipeline_stage.json` - Pipeline stage definitions
- `experiment.json` - Experiment metadata
- `task.json` - Task definitions

### 5.2 Validation Commands

```bash
# Validate all registry files
ont_experiments.py validate --all

# Validate specific types
ont_experiments.py validate --math
ont_experiments.py validate --pipeline
ont_experiments.py validate --experiments
```

### 5.3 Implementation Tasks

- [ ] Create JSON schemas in `registry/schemas/`
- [ ] Add `jsonschema` dependency
- [ ] Implement `validate` subcommand
- [ ] Add pre-commit hook for validation
- [ ] CI integration for schema validation

---

## Phase 6: AI Agent Integration

### 6.1 CLAUDE.md System Files

```
ont-ecosystem/
├── CLAUDE.md                    # Repository-level (existing)
└── skills/
    └── end-reason/
        └── CLAUDE.md            # Skill-level context

~/.ont-registry/
├── CLAUDE.md                    # Global ONT context
└── experiments/
    └── exp-abc123/
        └── CLAUDE.md            # Experiment-specific context
```

### 6.2 Hierarchical Context Loading

1. **Global** (`~/.ont-registry/CLAUDE.md`) - Lab-wide conventions
2. **Repository** (`ont-ecosystem/CLAUDE.md`) - Codebase patterns
3. **Skill** (`skills/end-reason/CLAUDE.md`) - Skill-specific context
4. **Experiment** (`experiments/exp-abc123/CLAUDE.md`) - Experiment state

### 6.3 Agent Bootup Protocol

```python
def agent_bootup(experiment_id: str, agent_type: str = "claude") -> AgentContext:
    """
    Standardized bootup for any AI agent.

    Returns context with:
    - Experiment metadata
    - Current tasks and their states
    - Pending/failing tasks
    - Relevant math definitions
    - Pipeline stage context
    - Recommendations
    """
```

### 6.4 Implementation Tasks

- [ ] Create skill-level CLAUDE.md templates
- [ ] Implement hierarchical context loading
- [ ] Create AgentContext dataclass
- [ ] Add `--agent` flag to bootup command
- [ ] Generate Copilot-compatible summaries

---

## Phase 7: Testing & Documentation

### 7.1 Test Coverage

| Component | Test File | Coverage Target |
|-----------|-----------|-----------------|
| Math Registry | `tests/test_math.py` | 90% |
| Pipeline Stages | `tests/test_pipeline.py` | 90% |
| Domain Memory | `tests/test_domain_memory.py` | 85% |
| Schema Validation | `tests/test_schemas.py` | 100% |
| CLI Commands | `tests/test_cli.py` | 80% |

### 7.2 Documentation

- [ ] Update `docs/QUICKSTART.md` with new features
- [ ] Create `docs/MATH_REGISTRY.md`
- [ ] Create `docs/PIPELINE_STAGES.md`
- [ ] Create `docs/AGENT_INTEGRATION.md`
- [ ] Update `CLAUDE.md` with comprehensive examples

---

## Implementation Order

### Milestone 1: Foundation
1. Registry structure (Phase 1.1)
2. Pipeline stages copy (Phase 2.1)
3. Core math definitions (Phase 1.2, 1.3)

### Milestone 2: CLI
4. Math CLI commands (Phase 4.1)
5. Pipeline stage commands (Phase 4.1)
6. Schema validation (Phase 5)

### Milestone 3: Domain Memory
7. Task dataclass enhancements (Phase 3.2)
8. Dependency resolution (Phase 3.2.2)
9. Agent session logging (Phase 3.2.1)

### Milestone 4: AI Integration
10. CLAUDE.md hierarchy (Phase 6.1, 6.2)
11. Agent bootup protocol (Phase 6.3)
12. Multi-agent support (Phase 6.4)

### Milestone 5: Testing & Polish
13. Test coverage (Phase 7.1)
14. Documentation (Phase 7.2)
15. CI/CD updates

---

## File Changes Summary

### New Files
```
registry/
├── math/
│   ├── schema.json
│   └── core/*.yaml (5-7 files)
├── pipeline/
│   ├── stages.yaml
│   └── artifacts.yaml
└── schemas/
    └── *.json (4 files)

docs/
├── MATH_REGISTRY.md
├── PIPELINE_STAGES.md
└── AGENT_INTEGRATION.md

tests/
├── test_math.py
├── test_pipeline.py
└── test_schemas.py
```

### Modified Files
```
bin/ont_experiments.py      # Add math, stage, bootup commands
lib/__init__.py             # Add math/pipeline modules
CLAUDE.md                   # Enhanced documentation
pyproject.toml              # Add jsonschema dependency
Makefile                    # Add validate target
```

---

## Success Criteria

1. **Math Registry**: All 7 core equations from All_Math PDF defined in YAML
2. **Pipeline Stages**: All 9 stages documented with artifact mappings
3. **Domain Memory**: Tasks link to stages and math definitions
4. **CLI**: All new commands documented with `--help`
5. **Validation**: `make validate` passes for all registry files
6. **Testing**: 85%+ coverage on new components
7. **AI Integration**: `bootup_check()` returns complete AgentContext
8. **Documentation**: All new features documented in CLAUDE.md

---

## Appendix: Core Equations Reference

### From All_Math PDF

**Phred Score**:
```
Q = -10 log₁₀(P_error)
```

**Bayesian Posterior**:
```
P(h|R) = P(R|h)P(h) / Σ_{h'∈H} P(R|h')P(h')
```

**Read Likelihood**:
```
P(R|h) = Π_{i=1}^{n} P(rᵢ|h)
```

**Error Identity**:
```
Identity = 1 - (S + I + D) / N
```

**Confusion Matrix**:
```
P(called = b | true = a) ≈ (# mismatches a→b) / (# true a positions)
```

**Cost-Based Decision**:
```
ĥ = argmin_{ĥ∈H} Σ_{h∈H} L(h, ĥ) P(h|R)
```

**Diplotype Joint**:
```
P(d₁, d₂ | R) with constraint P(d₁, d₂) = P(d₂, d₁)
```
