# Deploy ONT Ecosystem to GitHub

## Quick Deployment

### Step 1: Extract the package
```bash
tar -xzf ont-ecosystem-v2.1.tar.gz
cd ont-ecosystem-complete
```

### Step 2: Create GitHub repository
Go to: https://github.com/organizations/Single-Molecule-Sequencing/repositories/new

Settings:
- **Name**: `ont-ecosystem`
- **Description**: `Oxford Nanopore experiment management with provenance tracking`
- **Visibility**: Public
- **DO NOT** initialize with README, .gitignore, or license

### Step 3: Push to GitHub
```bash
git remote add origin https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git
git push -u origin main
```

Or if repository already exists:
```bash
git remote set-url origin https://github.com/Single-Molecule-Sequencing/ont-ecosystem.git
git push -u origin main --force
```

### Step 4: Verify
Visit: https://github.com/Single-Molecule-Sequencing/ont-ecosystem

GitHub Actions CI will run automatically.

---

## Package Contents

| Component | Count | Description |
|-----------|-------|-------------|
| Skills | 6 | Claude AI skills for ONT analysis |
| Scripts | 10 | Python CLI tools |
| Dashboards | 4 | React visualization components |
| Pipelines | 3 | Example workflow YAML files |
| HPC Configs | 3 | Great Lakes, ARMIS2, local |

## Install Command (after GitHub push)

```bash
curl -sSL https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/install.sh | bash
source ~/.ont-ecosystem/env.sh
```

## Skills for Claude Projects

Upload these `.skill` files to Claude Projects:
1. `ont-experiments-v2.skill` - Core registry & orchestration
2. `ont-align.skill` - Alignment + edit distance
3. `ont-pipeline.skill` - Multi-step workflows
4. `end-reason.skill` - Read end reason QC
5. `dorado-bench-v2.skill` - GPU basecalling
6. `ont-monitor.skill` - Run monitoring
