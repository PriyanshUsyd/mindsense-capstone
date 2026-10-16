#!/usr/bin/env bash
# macOS/Linux, or Git Bash on Windows. Native Windows PowerShell:
# scripts/setup_local_python_env.ps1.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$repo_root"

if command -v python3 >/dev/null 2>&1; then
  python3 -m venv .venv
else
  python -m venv .venv
fi

# A Windows venv puts the interpreter in Scripts/, not bin/.
if [ -x "$repo_root/.venv/Scripts/python.exe" ]; then
  venv_python="$repo_root/.venv/Scripts/python.exe"
  activate_hint="source .venv/Scripts/activate"
else
  venv_python="$repo_root/.venv/bin/python"
  activate_hint="source .venv/bin/activate"
fi

"$venv_python" -m pip install --upgrade pip
"$venv_python" -m pip install -r requirements.txt -c constraints-python312.txt
"$venv_python" -m pip check
"$venv_python" - <<'PY'
import numpy
import scipy
import statsmodels

print(f"NumPy {numpy.__version__}")
print(f"SciPy {scipy.__version__}")
print(f"statsmodels {statsmodels.__version__}")
PY

echo "Local Python environment is ready. Activate it with: $activate_hint"
