#!/usr/bin/env bash
set -euo pipefail

PY="${PY:-/home/yuan/miniforge3/envs/taichi-lbm-py311/bin/python}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_ROOT="${RUN_ROOT:-/mnt/usb1t/RUNS/runs/stage18_flat_wall_closure_matrix_20260704}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-1}"
STEPS="${STEPS:-300}"
export CUDA_VISIBLE_DEVICES
export CUDA_DEVICE_ORDER=PCI_BUS_ID

mkdir -p "${RUN_ROOT}"
cp "${SCRIPT_DIR}/phasefield_full_solver.py" "${RUN_ROOT}/phasefield_full_solver.py"

run_case() {
  local name="$1"
  local theta="$2"
  local adv="$3"
  local gdist="$4"
  local gsign="$5"
  local case_dir="${RUN_ROOT}/${name}"
  mkdir -p "${case_dir}/output"
  {
    echo "case=${name}"
    echo "theta=${theta}"
    echo "phase_advection_mode=${adv}"
    echo "wetting_ghost_distance=${gdist}"
    echo "wetting_ghost_sign=${gsign}"
    echo "started=$(date -Is)"
  } > "${case_dir}/run.status"
  set +e
  "${PY}" "${RUN_ROOT}/phasefield_full_solver.py" \
    --arch cuda --device-memory-gb 6 \
    --nx 48 --ny 32 --nz 48 \
    --steps "${STEPS}" --output-period 100 \
    --geometry-mode 1 --theta-deg "${theta}" \
    --init-contact-angle-deg "${theta}" --wall-surface-y 0.5 \
    --rho-l 1.0 --rho-g 0.1 \
    --nu-l 0.1 --nu-g 0.1 \
    --radius 10 --width 4 \
    --omega-h 1.0 --beta 0.01 --kappa 0.01 \
    --phase-equation-mode 2 --phase-source-scale-mode 3 --phase-mobility -1 \
    --phase-bound-mode 2 \
    --wetting-mode 0 --phase-wall-mode 3 \
    --wetting-ghost-distance "${gdist}" --wetting-ghost-sign "${gsign}" \
    --force-mode 0 --force-closure-mode 1 --force-insertion-mode 1 \
    --pressure-model 2 --pressure-reference 0.3333333333333333 \
    --momentum-mode 1 --momentum-density-mode 1 --velocity-density-mode 0 \
    --momentum-rho-ref 1.0 --rho-force-floor 1e-12 \
    --phase-advection-mode "${adv}" \
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
run_case "theta90_adv0_gd1_signm1" 90 0 1.0 -1.0 || overall=1
run_case "theta90_adv1_gd1_signm1" 90 1 1.0 -1.0 || overall=1
run_case "theta90_adv1_gd05_signm1" 90 1 0.5 -1.0 || overall=1
run_case "theta90_adv1_gd05_signp1" 90 1 0.5 1.0 || overall=1
run_case "theta60_adv1_gd05_signm1" 60 1 0.5 -1.0 || overall=1
run_case "theta120_adv1_gd05_signm1" 120 1 0.5 -1.0 || overall=1

echo "overall_rc=${overall}" > "${RUN_ROOT}/done.status"
exit "${overall}"
