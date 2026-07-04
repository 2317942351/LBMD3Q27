#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_ROOT="${RUN_ROOT:-/mnt/usb1t/RUNS/runs/stage18_taichi_pressure_wall_20260704}"
CONDA_ENV="${CONDA_ENV:-taichi-lbm-py311}"
GPU_ID="${GPU_ID:-1}"
PYTHON_BIN="/home/yuan/miniforge3/envs/$CONDA_ENV/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing Python env: $PYTHON_BIN" >&2
  exit 2
fi

mkdir -p "$RUN_ROOT"
cp "$SCRIPT_DIR/phasefield_full_solver.py" "$RUN_ROOT/"

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
  --output-period 1
  --rho-l 1.0 --rho-g 0.1
  --nu-l 0.1 --nu-g 0.1
  --radius 6 --width 4
  --omega-h 1.0
  --beta 0.01 --kappa 0.01
  --phase-bound-mode 1
  --wetting-mode 0
  --force-mode 0
  --momentum-mode 1
  --momentum-density-mode 1
  --momentum-rho-ref 1.0
  --force-insertion-mode 1
  --rho-force-floor 1e-12
  --mass-tol 1e-8
  --umax-tol 10
)

run_case() {
  local name="$1"
  shift
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
}

run_case "P1_bulk_no_force_20" \
  --steps 20 --geometry-mode 0 --force-closure-mode 0 --phase-advection-mode 0

run_case "P2_bulk_surface_guo_no_phase_adv_20" \
  --steps 20 --geometry-mode 0 --force-closure-mode 1 --phase-advection-mode 0

run_case "P3_bulk_surface_guo_phase_adv_20" \
  --steps 20 --geometry-mode 0 --force-closure-mode 1 --phase-advection-mode 1

run_case "P4_bulk_surface_guo_phase_adv_100" \
  --steps 100 --geometry-mode 0 --force-closure-mode 1 --phase-advection-mode 1 --output-period 10

run_case "W1_flat_wall_no_force_none_20" \
  --steps 20 --geometry-mode 1 --theta-deg 90 --force-closure-mode 0 --phase-advection-mode 0 --phase-wall-mode 0

run_case "W2_flat_wall_no_force_perlink_20" \
  --steps 20 --geometry-mode 1 --theta-deg 90 --force-closure-mode 0 --phase-advection-mode 0 --phase-wall-mode 2

run_case "W3_flat_wall_surface_perlink_20" \
  --steps 20 --geometry-mode 1 --theta-deg 90 --force-closure-mode 1 --phase-advection-mode 0 --phase-wall-mode 2

run_case "W4_flat_wall_no_force_perlink_100" \
  --steps 100 --geometry-mode 1 --theta-deg 90 --force-closure-mode 0 --phase-advection-mode 0 --phase-wall-mode 2 --output-period 10

run_case "W5_flat_wall_surface_perlink_phase_adv_100" \
  --steps 100 --geometry-mode 1 --theta-deg 90 --force-closure-mode 1 --phase-advection-mode 1 --phase-wall-mode 2 --output-period 10

run_case "W6_flat_wall_no_force_perlink_1000" \
  --steps 1000 --geometry-mode 1 --theta-deg 90 --force-closure-mode 0 --phase-advection-mode 0 --phase-wall-mode 2 --output-period 100

echo "DONE $(date -Is)" > "$RUN_ROOT/done.status"
echo "$RUN_ROOT"
