# Windows PowerShell equivalent of scripts/setup_local_python_env.sh.
# Run from the repository root:  .\scripts\setup_local_python_env.ps1
# If script execution is blocked:  Set-ExecutionPolicy -Scope Process Bypass
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 -m venv .venv
} else {
    python -m venv .venv
}
if ($LASTEXITCODE -ne 0) { throw "could not create .venv" }

$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }
& $venvPython -m pip install -r requirements.txt -c constraints-python312.txt
if ($LASTEXITCODE -ne 0) { throw "dependency install failed" }
& $venvPython -m pip check
if ($LASTEXITCODE -ne 0) { throw "pip check failed" }
& $venvPython -c "import numpy, scipy, statsmodels; print('NumPy', numpy.__version__); print('SciPy', scipy.__version__); print('statsmodels', statsmodels.__version__)"
if ($LASTEXITCODE -ne 0) { throw "scientific stack import failed" }

Write-Output "Local Python environment is ready. Activate it with: .venv\Scripts\Activate.ps1"
