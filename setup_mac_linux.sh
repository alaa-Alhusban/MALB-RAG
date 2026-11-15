#!/usr/bin/env bash
# One-time setup for macOS / Linux. Run from the folder that contains run_all.py:
#     bash setup_mac_linux.sh
set -e
[ -f run_all.py ] || { echo "run_all.py not found - cd into the project folder first"; exit 1; }
PY=""
for v in python3.12 python3.11 python3.10; do PY=$(command -v $v || true); [ -n "$PY" ] && break; done
[ -n "$PY" ] || { echo "Python 3.10-3.12 is required. Install one (e.g. python3.12), then re-run."; exit 1; }
echo "Using $PY"
[ -x .venv/bin/python ] || "$PY" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install torch
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q tests
.venv/bin/python -c "import torch; print('CUDA available:', torch.cuda.is_available(), '| GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else '-')"
echo "Setup finished. Next: bash run_mac_linux.sh smoke   (or multi-smoke)"
