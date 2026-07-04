#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_ROOT="${RUN_ROOT:-/home/yuan/taichi_lbm_runs/phasefield_bulk_kernel_20260704}"
VENV="${VENV:-/home/yuan/taichi_lbm_runs/taichi_venv_py312}"
CONDA_ENV="${CONDA_ENV:-taichi-lbm-py311}"
CONDA_BIN="${CONDA_BIN:-/home/yuan/miniforge3/bin/conda}"
MAMBA_BIN="${MAMBA_BIN:-/home/yuan/miniforge3/bin/mamba}"
GPU_ID="${GPU_ID:-1}"

mkdir -p "$RUN_ROOT"
cp "$SCRIPT_DIR/phasefield_bulk_lifecycle_taichi.py" "$RUN_ROOT/"

PYTHON_BIN=""
if [[ -x "$VENV/bin/python" ]] && "$VENV/bin/python" -m pip --version >/dev/null 2>&1; then
  PYTHON_BIN="$VENV/bin/python"
else
  if [[ -x "$MAMBA_BIN" ]]; then
    if ! "$MAMBA_BIN" env list | awk '{print $1}' | grep -qx "$CONDA_ENV"; then
      "$MAMBA_BIN" create -y -n "$CONDA_ENV" python=3.11 pip numpy
    fi
    PYTHON_BIN="/home/yuan/miniforge3/envs/$CONDA_ENV/bin/python"
  elif [[ -x "$CONDA_BIN" ]]; then
    if ! "$CONDA_BIN" env list | awk '{print $1}' | grep -qx "$CONDA_ENV"; then
      "$CONDA_BIN" create -y -n "$CONDA_ENV" python=3.11 pip numpy
    fi
    PYTHON_BIN="/home/yuan/miniforge3/envs/$CONDA_ENV/bin/python"
  else
    python3 -m venv "$VENV"
    PYTHON_BIN="$VENV/bin/python"
  fi
fi

"$PYTHON_BIN" -m pip install --upgrade pip wheel setuptools
"$PYTHON_BIN" -m pip install "numpy<2" taichi

export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES="$GPU_ID"
export TI_DEVICE_MEMORY_GB=4

{
  date -Is
  nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader || true
  "$PYTHON_BIN" - <<'PY'
import taichi as ti
import numpy as np
print("taichi", ti.__version__)
print("numpy", np.__version__)
PY
} > "$RUN_ROOT/env.log" 2>&1

"$PYTHON_BIN" "$RUN_ROOT/phasefield_bulk_lifecycle_taichi.py" \
  --arch cuda \
  --device-memory-gb 4 \
  --nx 24 --ny 24 --nz 24 \
  --steps 20 \
  --radius 6 \
  --width 4 \
  --omega 1 \
  --out "$RUN_ROOT/output" \
  > "$RUN_ROOT/run.log" 2> "$RUN_ROOT/run.stderr"

echo "DONE $(date -Is)" > "$RUN_ROOT/done.status"
echo "$RUN_ROOT"

