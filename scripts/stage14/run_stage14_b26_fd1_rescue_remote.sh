#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/mnt/usb1t/RUNS/runs/stage14_B26_sparse_fullfield_v2_20260627}"
PROBE_ROOT="${PROBE_ROOT:-${ROOT}/M0_FD1_full}"
PY="${PY:-/usr/bin/python3}"
SCRIPT="${SCRIPT:-/home/yuan/stage14_s2_replay_smoke.py}"
ANALYZER="${ANALYZER:-/home/yuan/stage14_b17_onset_mask_argmax.py}"
DIGEST="${DIGEST:-/home/yuan/stage14_b26_sparse_digest.py}"
BIN="${BIN:-/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main}"
GPU="${GPU:-1}"
ITERATIONS="${ITERATIONS:-12}"
VTK_PERIOD="${VTK_PERIOD:-1}"
LOG_PERIOD="${LOG_PERIOD:-1}"
TIMEOUT="${TIMEOUT:-2400}"

mkdir -p "${ROOT}"
rm -rf "${PROBE_ROOT}"

{
  echo "stage=stage14_B26_fd1_rescue"
  echo "root=${ROOT}"
  echo "probe_root=${PROBE_ROOT}"
  echo "gpu=${GPU}"
  echo "binary=${BIN}"
  echo "iterations=${ITERATIONS}"
  echo "vtk_period=${VTK_PERIOD}"
  echo "claim_limit=diagnostic_only_not_contact_angle_validation"
} | tee "${ROOT}/fd1_rescue_config.txt"

set +e
"${PY}" "${SCRIPT}" \
  --root "${PROBE_ROOT}" \
  --binary "${BIN}" \
  --gpu "${GPU}" \
  --iterations "${ITERATIONS}" \
  --vtk-period "${VTK_PERIOD}" \
  --vtk-field-set b26 \
  --log-period "${LOG_PERIOD}" \
  --timeout "${TIMEOUT}" \
  --cases wall_60to30_10 \
  --density-h 1.0 \
  --density-l 0.005 \
  --replay-mode 1 \
  --momentum-closure-diagnostics-mode 1 \
  --b18-closure-diagnostics-mode 1 \
  --b18-velocity-bound 0.2 \
  --b20-hupdate-diagnostics-mode 1 \
  --b21-hpopulation-audit-mode 1 \
  --b22-velocity-producer-audit-mode 1 \
  --momentum-closure-probe-mode 1 \
  --phase-advection-velocity-mode 1 \
  --momentum-force-mode 0 \
  --pressure-closure-mode 1 \
  --force-density-closure-mode 1 \
  --force-density-rho-floor 0.005 \
  --force-fixed-point-mode 2 \
  --force-fixed-iterator 2 \
  --force-fixed-tol 0 \
  --force-fixed-max-iter 2 \
  --force \
  --run \
  > "${ROOT}/M0_FD1_full_rescue_driver_stdout.json" \
  2> "${ROOT}/M0_FD1_full_rescue_driver_stderr.log"
driver_rc=$?
set -e
echo "DRIVER_RC=${driver_rc}" | tee "${ROOT}/M0_FD1_full_rescue_driver.status"

set +e
"${PY}" "${ANALYZER}" "${PROBE_ROOT}" --out-dir "${PROBE_ROOT}" --prefix b26 \
  > "${ROOT}/M0_FD1_full_rescue_analyzer_stdout.json" \
  2> "${ROOT}/M0_FD1_full_rescue_analyzer_stderr.log"
analyzer_rc=$?
set -e
echo "ANALYZER_RC=${analyzer_rc}" | tee "${ROOT}/M0_FD1_full_rescue_analyzer.status"

find "${PROBE_ROOT}" -maxdepth 4 \( -name 'run.log' -o -name 'run.stderr' -o -name 'run.status' -o -name 'case.xml' -o -name 'case_metadata.json' -o -name '*.csv' -o -name '*.json' -o -name '*.txt' \) \
  -print > "${ROOT}/M0_FD1_full_rescue_light_artifact_manifest.txt"
find "${PROBE_ROOT}" \( -path '*/output/*.vti' -o -path '*/output/*.pvti' \) -type f | wc -l | awk '{print "VTK_COUNT="$1}' \
  > "${ROOT}/M0_FD1_full_rescue_vti_count.txt"
find "${PROBE_ROOT}" -name '*argmax_trace.json' -type f -print -delete \
  > "${ROOT}/M0_FD1_full_rescue_deleted_argmax_trace_manifest.txt"

if [[ "${driver_rc}" -eq 0 && "${analyzer_rc}" -eq 0 ]]; then
  find "${PROBE_ROOT}" \( -path '*/output/*.vti' -o -path '*/output/*.pvti' \) -type f -print -delete \
    > "${ROOT}/M0_FD1_full_rescue_deleted_vti_manifest.txt"
fi

set +e
"${PY}" "${DIGEST}" "${ROOT}" \
  --csv "${ROOT}/b26_sparse_digest.csv" \
  --json "${ROOT}/b26_sparse_digest.json" \
  > "${ROOT}/b26_sparse_digest_stdout.json" \
  2> "${ROOT}/b26_sparse_digest_stderr.log"
digest_rc=$?
set -e
echo "DIGEST_RC=${digest_rc}" | tee "${ROOT}/digest.status"

overall_rc=0
if [[ "${driver_rc}" -ne 0 || "${analyzer_rc}" -ne 0 || "${digest_rc}" -ne 0 ]]; then
  overall_rc=3
fi
echo "OVERALL_RC=${overall_rc}" | tee "${ROOT}/stage14_B26.status"
exit "${overall_rc}"
