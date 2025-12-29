# ONT Ecosystem Installer for Windows
# 
# Usage:
#   From cloned repo:  .\install.ps1
#   Remote install:    irm https://raw.githubusercontent.com/Single-Molecule-Sequencing/ont-ecosystem/main/install.ps1 | iex
#
# Options:
#   -Force    Overwrite existing installation

param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$InstallDir = if ($env:ONT_ECOSYSTEM_HOME) { $env:ONT_ECOSYSTEM_HOME } else { "$env:USERPROFILE\.ont-ecosystem" }
$RepoUrl = "https://github.com/Single-Molecule-Sequencing/ont-ecosystem"

Write-Host "🧬 Installing ONT Ecosystem..." -ForegroundColor Cyan
Write-Host "   Install directory: $InstallDir"

# Create install directories
$Dirs = @("bin", "config", "skills", "lib")
foreach ($dir in $Dirs) {
    $path = Join-Path $InstallDir $dir
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}

# Check if running from cloned repo or remote install
if (Test-Path "bin\ont_experiments.py") {
    Write-Host "📂 Installing from local repository..." -ForegroundColor Green
    
    # Copy bin scripts
    Copy-Item -Path "bin\*.py" -Destination "$InstallDir\bin\" -Force
    
    # Copy lib if exists
    if (Test-Path "lib") {
        Copy-Item -Path "lib\*" -Destination "$InstallDir\lib\" -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    # Copy skills if exists
    if (Test-Path "skills") {
        Copy-Item -Path "skills\*" -Destination "$InstallDir\skills\" -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    # Copy registry if exists
    if (Test-Path "registry") {
        Copy-Item -Path "registry" -Destination "$InstallDir\" -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    # Copy completions if exists
    if (Test-Path "completions") {
        Copy-Item -Path "completions" -Destination "$InstallDir\" -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    # Copy textbook if exists
    if (Test-Path "textbook") {
        Copy-Item -Path "textbook" -Destination "$InstallDir\" -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    # Copy data if exists
    if (Test-Path "data") {
        Copy-Item -Path "data" -Destination "$InstallDir\" -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    # Store source repo path
    $RepoPath = (Get-Location).Path
    "REPO_SOURCE=$RepoPath" | Out-File -FilePath "$InstallDir\config\source.conf" -Encoding UTF8
}
else {
    Write-Host "📥 Downloading from GitHub..." -ForegroundColor Yellow
    
    $Scripts = @(
        "ont_experiments.py", "ont_align.py", "ont_pipeline.py", "end_reason.py",
        "ont_monitor.py", "dorado_basecall.py", "calculate_resources.py",
        "ont_endreason_qc.py", "experiment_db.py", "ont_config.py", "ont_context.py",
        "ont_manuscript.py", "ont_stats.py", "ont_check.py", "ont_help.py",
        "ont_update.py", "ont_backup.py", "ont_doctor.py", "ont_report.py",
        "ont_hooks.py", "ont_version.py"
    )
    
    foreach ($script in $Scripts) {
        $url = "$RepoUrl/raw/main/bin/$script"
        $dest = "$InstallDir\bin\$script"
        try {
            Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing -ErrorAction SilentlyContinue
        }
        catch {
            # Silently skip missing files
        }
    }
}

# Create environment setup script for PowerShell
$EnvScript = @"
# ONT Ecosystem Environment for PowerShell
`$env:ONT_ECOSYSTEM_HOME = "$InstallDir"
`$env:PATH = "`$env:ONT_ECOSYSTEM_HOME\bin;`$env:PATH"
`$env:PYTHONPATH = "`$env:ONT_ECOSYSTEM_HOME;`$env:PYTHONPATH"
if (-not `$env:ONT_REGISTRY_DIR) { `$env:ONT_REGISTRY_DIR = "`$env:USERPROFILE\.ont-registry" }
if (-not `$env:ONT_REFERENCES_DIR) { `$env:ONT_REFERENCES_DIR = "`$env:USERPROFILE\.ont-references" }

# Helper function to run ONT tools
function ont { python "`$env:ONT_ECOSYSTEM_HOME\bin\ont_experiments.py" @args }
function ont-align { python "`$env:ONT_ECOSYSTEM_HOME\bin\ont_align.py" @args }
function ont-pipeline { python "`$env:ONT_ECOSYSTEM_HOME\bin\ont_pipeline.py" @args }
function ont-stats { python "`$env:ONT_ECOSYSTEM_HOME\bin\ont_stats.py" @args }
function ont-manuscript { python "`$env:ONT_ECOSYSTEM_HOME\bin\ont_manuscript.py" @args }
"@

$EnvScript | Out-File -FilePath "$InstallDir\env.ps1" -Encoding UTF8

# Create batch file wrapper for CMD users
$BatchEnv = @"
@echo off
REM ONT Ecosystem Environment for CMD
set ONT_ECOSYSTEM_HOME=$InstallDir
set PATH=%ONT_ECOSYSTEM_HOME%\bin;%PATH%
set PYTHONPATH=%ONT_ECOSYSTEM_HOME%;%PYTHONPATH%
if not defined ONT_REGISTRY_DIR set ONT_REGISTRY_DIR=%USERPROFILE%\.ont-registry
if not defined ONT_REFERENCES_DIR set ONT_REFERENCES_DIR=%USERPROFILE%\.ont-references
"@

$BatchEnv | Out-File -FilePath "$InstallDir\env.bat" -Encoding ASCII

# Check Python dependencies
Write-Host "📦 Checking Python dependencies..." -ForegroundColor Cyan
try {
    python -m pip install --quiet pyyaml 2>$null
}
catch {
    Write-Host "   Note: Install pyyaml manually if needed" -ForegroundColor Yellow
}

# Add to PowerShell profile
$ProfilePath = $PROFILE.CurrentUserAllHosts
$ProfileDir = Split-Path $ProfilePath -Parent

if (-not (Test-Path $ProfileDir)) {
    New-Item -ItemType Directory -Path $ProfileDir -Force | Out-Null
}

if (-not (Test-Path $ProfilePath)) {
    New-Item -ItemType File -Path $ProfilePath -Force | Out-Null
}

$ProfileContent = Get-Content $ProfilePath -Raw -ErrorAction SilentlyContinue
if ($ProfileContent -notmatch "ont-ecosystem") {
    Add-Content -Path $ProfilePath -Value "`n# ONT Ecosystem"
    Add-Content -Path $ProfilePath -Value ". `"$InstallDir\env.ps1`""
    Write-Host "   Added to PowerShell profile: $ProfilePath" -ForegroundColor Green
}

Write-Host ""
Write-Host "✅ ONT Ecosystem v3.0.0 installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "To activate now, run:" -ForegroundColor Cyan
Write-Host "   . `"$InstallDir\env.ps1`""
Write-Host ""
Write-Host "Quick start:" -ForegroundColor Cyan
Write-Host "   python `"$InstallDir\bin\ont_stats.py`" --brief"
Write-Host "   python `"$InstallDir\bin\ont_experiments.py`" init --git"
Write-Host "   python `"$InstallDir\bin\ont_experiments.py`" discover /path/to/data"
Write-Host ""
