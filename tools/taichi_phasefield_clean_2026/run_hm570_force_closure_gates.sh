#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_ROOT="${RUN_ROOT:-/mnt/usb1t/RUNS/runs/stage18_taichi_force_closure_20260704}"
CONDA_ENV="${CONDA_ENV:-taichi-lbm-py311}"
MAMBA_BIN="${MAMBA_BIN:-/home/yuan/miniforge3/bin/mamba}"
CONDA_BIN="${CONDA_BIN:-/home/yuan/miniforge3/bin/conda}"
GPU_ID="${GPU_ID:-1}"

mkdir -p "$RUN_ROOT"
cp "$SCRIPT_DIR/phasefield_full_solver.py" "$RUN_ROOT/"

if [[ -x "/home/yuan/miniforge3/envs/$CONDA_ENV/bin/python" ]]; then
  PYTHON_BIN="/home/yuan/miniforge3/envs/$CONDA_ENV/bin/python"
elif [[ -x "$MAMBA_BIN" ]]; then
  "$MAMBA_BIN" create -y -n "$CONDA_ENV" python=3.11 pip numpy taichi
  PYTHON_BIN="/home/yuan/miniforge3/envs/$CONDA_ENV/bin/python"
elif [[ -x "$CONDA_BIN" ]]; then
  "$CONDA_BIN" create -y -n "$CONDA_ENV" python=3.11 pip numpy taichi
  PYTHON_BIN="/home/yuan/miniforge3/envs/$CONDA_ENV/bin/python"
else
  echo "No conda/mamba Python environment available" >&2
  exit 2
fi

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
  --nx 24 --ny 24 --nz 24
  --steps 20
  --output-period 1
  --geometry-mode 0
  --rho-l 1.0 --rho-g 0.1
  --nu-l 0.1 --nu-g 0.1
  --radius 6 --width 4
  --omega-h 1.0
  --beta 0.01 --kappa 0.01
  --phase-bound-mode 1
  --wetting-mode 0
  --phase-wall-mode 0
  --mass-tol 1e-8
  --umax-tol 10
)

run_case() {
  local name="$1"
  local allow_fail="$2"
  shift 2
  mkdir -p "$RUN_ROOT/$name"
  set +e
  "$PYTHON_BIN" "$RUN_ROOT/phasefield_full_solver.py" \
    "${BASE_ARGS[@]}" \
    --out "$RUN_ROOT/$name/output" \
    "$@" \
    > "$RUN_ROOT/$name/run.log" 2> "$RUN_ROOT/$name/run.stderr"
  local rc=$?
  set -e
  echo "RC=$rc" > "$RUN_ROOT/$name/run.status"
  if [[ "$rc" -ne 0 && "$allow_fail" != "allow_fail" ]]; then
    exit "$rc"
  fi
}

run_case "F1_momentum_no_force" "allow_fail" \
  --force-closure-mode 0 --momentum-mode 1 --force-insertion-mode 0 --phase-advection-mode 0

run_case "F2_surface_shadow_no_injection" "allow_fail" \
  --force-closure-mode 1 --momentum-mode 1 --force-insertion-mode 0 --phase-advection-mode 0

run_case "F3_guo_surface_no_phase_adv" "allow_fail" \
  --force-closure-mode 1 --momentum-mode 1 --force-insertion-mode 1 --phase-advection-mode 0

run_case "F4_guo_surface_phase_adv" "allow_fail" \
  --force-closure-mode 1 --momentum-mode 1 --force-insertion-mode 1 --phase-advection-mode 1

run_case "F5_capped_surface_phase_adv" "allow_fail" \
  --force-closure-mode 1 --momentum-mode 1 --force-insertion-mode 1 --phase-advection-mode 1 --force-accel-cap 0.01

run_case "F6_pressure_only_shadow" "allow_fail" \
  --force-closure-mode 2 --momentum-mode 1 --force-insertion-mode 0 --phase-advection-mode 0

run_case "F7_pressure_plus_surface_guo" "allow_fail" \
  --force-closure-mode 3 --momentum-mode 1 --force-insertion-mode 1 --phase-advection-mode 0

run_case "F8_const_momentum_density_no_force" "allow_fail" \
  --force-closure-mode 0 --momentum-mode 1 --force-insertion-mode 0 --phase-advection-mode 0 \
  --momentum-density-mode 1 --momentum-rho-ref 1.0

run_case "F9_const_momentum_density_surface_guo" "allow_fail" \
  --force-closure-mode 1 --momentum-mode 1 --force-insertion-mode 1 --phase-advection-mode 0 \
  --momentum-density-mode 1 --momentum-rho-ref 1.0

echo "DONE $(date -Is)" > "$RUN_ROOT/done.status"
echo "$RUN_ROOT"
