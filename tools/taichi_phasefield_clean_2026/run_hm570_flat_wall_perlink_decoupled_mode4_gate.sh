#!/usr/bin/env bash
set -euo pipefail

PY="${PY:-/home/yuan/miniforge3/envs/taichi-lbm-py311/bin/python}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_ROOT="${RUN_ROOT:-/mnt/usb1t/RUNS/runs/stage18_flat_wall_perlink_decoupled_mode4_20260704}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-1}"
STEPS="${STEPS:-300}"
PHASE_WALL_WETTING_STRENGTH="${PHASE_WALL_WETTING_STRENGTH:-1.0}"
export CUDA_VISIBLE_DEVICES
export CUDA_DEVICE_ORDER=PCI_BUS_ID

mkdir -p "${RUN_ROOT}"
cp "${SCRIPT_DIR}/phasefield_full_solver.py" "${RUN_ROOT}/phasefield_full_solver.py"

run_case() {
  local init_theta="$1"
  local target_theta="$2"
  local case_dir="${RUN_ROOT}/init${init_theta}_target${target_theta}_${STEPS}"
  mkdir -p "${case_dir}/output"
  {
    echo "case=init${init_theta}_target${target_theta}_${STEPS}"
    echo "init_theta=${init_theta}"
    echo "target_theta=${target_theta}"
    echo "phase_wall_mode=4"
    echo "phase_wall_wetting_strength=${PHASE_WALL_WETTING_STRENGTH}"
    echo "grid=96x52x96"
    echo "radius=18"
    echo "width=4"
    echo "started=$(date -Is)"
  } > "${case_dir}/run.status"
  set +e
  "${PY}" "${RUN_ROOT}/phasefield_full_solver.py" \
    --arch cuda --device-memory-gb 8 \
    --nx 96 --ny 52 --nz 96 \
    --steps "${STEPS}" --output-period 100 \
    --geometry-mode 1 --theta-deg "${target_theta}" \
    --init-contact-angle-deg "${init_theta}" --wall-surface-y 0.5 \
    --rho-l 1.0 --rho-g 0.1 \
    --nu-l 0.1 --nu-g 0.1 \
    --radius 18 --width 4 \
    --omega-h 1.0 --beta 0.01 --kappa 0.01 \
    --phase-equation-mode 2 --phase-source-scale-mode 3 --phase-mobility -1 \
    --phase-bound-mode 2 \
    --wetting-mode 0 --phase-wall-mode 4 \
    --phase-wall-wetting-strength "${PHASE_WALL_WETTING_STRENGTH}" \
    --wetting-ghost-distance 1.0 --wetting-ghost-sign -1.0 \
    --force-mode 0 --force-closure-mode 1 --force-insertion-mode 1 \
    --pressure-model 2 --pressure-reference 0.3333333333333333 \
    --momentum-mode 1 --momentum-density-mode 1 --velocity-density-mode 0 \
    --momentum-rho-ref 1.0 --rho-force-floor 1e-12 \
    --phase-advection-mode 1 \
    --mass-tol 1e-8 --umax-tol 0.02 \
    --write-npz \
    --out "${case_dir}/output" > "${case_dir}/run.log" 2> "${case_dir}/run.stderr"
  local rc=$?
  set -e
  {
    echo "rc=${rc}"
    echo "finished=$(date -Is)"
  } >> "${case_dir}/run.status"
  return "${rc}"
}

overall=0
run_case 60 30 || overall=1
run_case 120 150 || overall=1

{
  echo "overall_rc=${overall}"
  echo "analysis=local_postprocess_required"
  echo "finished=$(date -Is)"
} > "${RUN_ROOT}/done.status"

exit "${overall}"
