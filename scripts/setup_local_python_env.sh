#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
venv_python="$repo_root/.venv/bin/python"

cd "$repo_root"

python3 -m venv .venv
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

echo "Local Python environment is ready. Activate it with: source .venv/bin/activate"
