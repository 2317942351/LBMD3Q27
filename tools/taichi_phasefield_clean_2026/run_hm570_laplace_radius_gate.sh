#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_ROOT="${RUN_ROOT:-/mnt/usb1t/RUNS/runs/stage18_full_phasefield_laplace_radius_20260704}"
CONDA_ENV="${CONDA_ENV:-taichi-lbm-py311}"
GPU_ID="${GPU_ID:-1}"
PYTHON_BIN="/home/yuan/miniforge3/envs/$CONDA_ENV/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing Python env: $PYTHON_BIN" >&2
  exit 2
fi

mkdir -p "$RUN_ROOT"
cp "$SCRIPT_DIR/phasefield_full_solver.py" "$RUN_ROOT/"
cp "$SCRIPT_DIR/summarize_bulk_laplace.py" "$RUN_ROOT/"

export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES="$GPU_ID"
export TI_DEVICE_MEMORY_GB=6

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

BASE_ARGS=(
  --arch cuda
  --device-memory-gb 6
  --nx 32 --ny 32 --nz 32
  --steps 3000
  --output-period 300
  --rho-l 1.0 --rho-g 0.1
  --nu-l 0.1 --nu-g 0.1
  --width 4
  --omega-h 1.0
  --beta 0.01 --kappa 0.01
  --phase-equation-mode 2
  --phase-source-scale-mode 3
  --phase-mobility -1
  --phase-bound-mode 2
  --wetting-mode 0
  --phase-wall-mode 0
  --force-mode 0
  --force-closure-mode 1
  --force-insertion-mode 1
  --pressure-model 2
  --pressure-reference 0.3333333333333333
  --momentum-mode 1
  --momentum-density-mode 1
  --velocity-density-mode 0
  --momentum-rho-ref 1.0
  --rho-force-floor 1e-12
  --mass-tol 1e-8
  --umax-tol 0.001
)

run_case() {
  local radius="$1"
  local name="radius${radius}_ratio10_3000"
  mkdir -p "$RUN_ROOT/$name"
  set +e
  "$PYTHON_BIN" "$RUN_ROOT/phasefield_full_solver.py" \
    "${BASE_ARGS[@]}" \
    --radius "$radius" \
    --out "$RUN_ROOT/$name/output" \
    > "$RUN_ROOT/$name/run.log" 2> "$RUN_ROOT/$name/run.stderr"
  local rc=$?
  set -e
  echo "RC=$rc" > "$RUN_ROOT/$name/run.status"
}

run_case 5
run_case 6
run_case 7

"$PYTHON_BIN" "$RUN_ROOT/summarize_bulk_laplace.py" "$RUN_ROOT" --kind laplace

echo "DONE $(date -Is)" > "$RUN_ROOT/done.status"
echo "$RUN_ROOT"
