#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/mnt/usb1t/RUNS/runs/stage14_B45_phase_boundedness_20260628}"
PY="${PY:-/usr/bin/python3}"
SCRIPT="${SCRIPT:-/home/yuan/stage14_s2_replay_smoke.py}"
RANKER="${RANKER:-/home/yuan/stage14_b45_phase_boundedness_rank.py}"
BIN="${BIN:-/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main}"
GPU="${GPU:-1}"
ITERATIONS="${ITERATIONS:-20}"
VTK_PERIOD="${VTK_PERIOD:-1}"
LOG_PERIOD="${LOG_PERIOD:-1}"
TIMEOUT="${TIMEOUT:-2400}"
KEEP_VTI="${KEEP_VTI:-0}"
FREE_THRESHOLD_KB="${FREE_THRESHOLD_KB:-52428800}"

mkdir -p "${ROOT}"

available_kb="$(df -Pk /mnt/usb1t | awk 'NR==2 {print $4}')"
if [[ "${available_kb}" -lt "${FREE_THRESHOLD_KB}" ]]; then
  find /mnt/usb1t/RUNS/runs -path '*/output/*.vti' -type f -print -delete \
    > "${ROOT}/cleanup_regenerable_vti_$(date +%Y%m%d_%H%M%S).log"
fi

{
  echo "stage=stage14_B45_phase_boundedness"
  echo "root=${ROOT}"
  echo "gpu=${GPU}"
  echo "binary=${BIN}"
  echo "iterations=${ITERATIONS}"
  echo "vtk_period=${VTK_PERIOD}"
  echo "vtk_field_set=b45phase"
  echo "claim_limit=phase_boundedness_postprocess_not_solver_repair"
} | tee "${ROOT}/run_config.txt"

sha256sum "${BIN}" | tee "${ROOT}/binary_sha256.txt"
nvidia-smi -L | tee "${ROOT}/nvidia_smi_L.txt"
df -h /mnt/usb1t /home 2>&1 | tee "${ROOT}/df_before.txt"

set +e
"${PY}" "${SCRIPT}" \
  --root "${ROOT}/B45_phase_boundedness" \
  --binary "${BIN}" \
  --gpu "${GPU}" \
  --iterations "${ITERATIONS}" \
  --vtk-period "${VTK_PERIOD}" \
  --vtk-field-set b45phase \
  --log-period "${LOG_PERIOD}" \
  --timeout "${TIMEOUT}" \
  --cases wall_60to30_10 \
  --density-h 1.0 \
  --density-l 0.005 \
  --replay-mode 1 \
  --momentum-closure-diagnostics-mode 1 \
  --b21-hpopulation-audit-mode 1 \
  --b22-velocity-producer-audit-mode 1 \
  --momentum-closure-probe-mode 1 \
  --phase-advection-velocity-mode 2 \
  --momentum-force-mode 0 \
  --fmu-stress-closure-mode 0 \
  --pressure-closure-mode 1 \
  --force-density-closure-mode 2 \
  --force-density-rho-floor 0.005 \
  --force-fixed-point-mode 2 \
  --force-fixed-iterator 2 \
  --force-fixed-tol 0 \
  --force-fixed-max-iter 2 \
  --force \
  --run \
  > "${ROOT}/b45_driver_stdout.json" \
  2> "${ROOT}/b45_driver_stderr.log"
driver_rc=$?
echo "DRIVER_RC=${driver_rc}" > "${ROOT}/b45_driver.status"

"${PY}" "${RANKER}" "${ROOT}/B45_phase_boundedness" \
  --out-dir "${ROOT}/B45_phase_boundedness" \
  --prefix b45 \
  > "${ROOT}/b45_ranker_stdout.json" \
  2> "${ROOT}/b45_ranker_stderr.log"
ranker_rc=$?
echo "RANKER_RC=${ranker_rc}" > "${ROOT}/b45_ranker.status"
set -e

find "${ROOT}" -maxdepth 5 \( -name 'run.log' -o -name 'run.stderr' -o -name 'run.status' -o -name 'case.xml' -o -name 'case_metadata.json' -o -name '*.csv' -o -name '*.json' -o -name '*.status' -o -name '*.txt' -o -name '*.md' \) \
  -print > "${ROOT}/light_artifact_manifest.txt"
find "${ROOT}" \( -path '*/output/*.vti' -o -path '*/output/*.pvti' \) -type f | wc -l | awk '{print "VTK_COUNT="$1}' > "${ROOT}/vti_count.txt"
if [[ "${KEEP_VTI}" != "1" ]]; then
  find "${ROOT}" \( -path '*/output/*.vti' -o -path '*/output/*.pvti' \) -type f -print -delete > "${ROOT}/deleted_vti_manifest.txt"
fi

df -h /mnt/usb1t /home 2>&1 | tee "${ROOT}/df_after.txt"

overall_rc=0
if [[ "${driver_rc}" -ne 0 || "${ranker_rc}" -ne 0 ]]; then
  overall_rc=3
fi

{
  echo "OVERALL_RC=${overall_rc}"
  if [[ "${overall_rc}" -eq 0 ]]; then
    echo "VERDICT=b45_phase_boundedness_complete"
  else
    echo "VERDICT=b45_phase_boundedness_failed"
  fi
} | tee "${ROOT}/stage14_B45.status"

exit "${overall_rc}"
