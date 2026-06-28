#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/mnt/usb1t/RUNS/runs/stage14_B39_fmu_stress_mode_matrix_20260628}"
PY="${PY:-/usr/bin/python3}"
SCRIPT="${SCRIPT:-/home/yuan/stage14_s2_replay_smoke.py}"
ANALYZER="${ANALYZER:-/home/yuan/stage14_b17_onset_mask_argmax.py}"
DIGEST="${DIGEST:-/home/yuan/stage14_b38_first_bad_ledger_digest.py}"
MATRIX_DIGEST="${MATRIX_DIGEST:-/home/yuan/stage14_b23_b24_matrix_digest.py}"
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
  echo "stage=stage14_B39_fmu_stress_mode_matrix"
  echo "root=${ROOT}"
  echo "gpu=${GPU}"
  echo "binary=${BIN}"
  echo "iterations=${ITERATIONS}"
  echo "vtk_period=${VTK_PERIOD}"
  echo "vtk_field_set=b33ledger"
  echo "density_h=1.0"
  echo "density_l=0.005"
  echo "pressure_closure_mode=1"
  echo "force_fixed_point_mode=2"
  echo "phase_advection_velocity_mode=2"
  echo "force_density_closure_mode=2"
  echo "force_density_rho_floor=0.005"
  echo "stage14_b18_closure_diagnostics_mode=1"
  echo "matrix=M0_FmuStressClosureMode0,M1_FmuStressClosureMode1,M2_FmuStressClosureMode2"
  echo "claim_limit=diagnostic_mode_matrix_not_contact_angle_validation"
} | tee "${ROOT}/run_config.txt"

sha256sum "${BIN}" | tee "${ROOT}/binary_sha256.txt"
nvidia-smi -L | tee "${ROOT}/nvidia_smi_L.txt"
df -h /mnt/usb1t /home 2>&1 | tee "${ROOT}/df_before.txt"

run_mode() {
  local tag="$1"
  local fmu_mode="$2"
  local probe_root="${ROOT}/${tag}"
  echo "RUN_B39 tag=${tag} FmuStressClosureMode=${fmu_mode}"
  set +e
  "${PY}" "${SCRIPT}" \
    --root "${probe_root}" \
    --binary "${BIN}" \
    --gpu "${GPU}" \
    --iterations "${ITERATIONS}" \
    --vtk-period "${VTK_PERIOD}" \
    --vtk-field-set b33ledger \
    --log-period "${LOG_PERIOD}" \
    --timeout "${TIMEOUT}" \
    --cases wall_60to30_10 \
    --density-h 1.0 \
    --density-l 0.005 \
    --replay-mode 1 \
    --momentum-closure-diagnostics-mode 1 \
    --b18-closure-diagnostics-mode 1 \
    --momentum-closure-probe-mode 1 \
    --phase-advection-velocity-mode 2 \
    --momentum-force-mode 0 \
    --fmu-stress-closure-mode "${fmu_mode}" \
    --pressure-closure-mode 1 \
    --force-density-closure-mode 2 \
    --force-density-rho-floor 0.005 \
    --force-fixed-point-mode 2 \
    --force-fixed-iterator 2 \
    --force-fixed-tol 0 \
    --force-fixed-max-iter 2 \
    --force \
    --run \
    > "${ROOT}/${tag}_driver_stdout.json" \
    2> "${ROOT}/${tag}_driver_stderr.log"
  local driver_rc=$?
  echo "DRIVER_RC=${driver_rc}" > "${ROOT}/${tag}_driver.status"

  "${PY}" "${ANALYZER}" "${probe_root}" --out-dir "${probe_root}" --prefix b39 \
    > "${ROOT}/${tag}_analyzer_stdout.json" \
    2> "${ROOT}/${tag}_analyzer_stderr.log"
  local analyzer_rc=$?
  echo "ANALYZER_RC=${analyzer_rc}" > "${ROOT}/${tag}_analyzer.status"

  "${PY}" "${DIGEST}" "${probe_root}" \
    --prefix b39 \
    --out-json "${probe_root}/b39_first_bad_ledger_digest.json" \
    --out-md "${probe_root}/b39_first_bad_ledger_digest.md" \
    > "${ROOT}/${tag}_digest_stdout.json" \
    2> "${ROOT}/${tag}_digest_stderr.log"
  local digest_rc=$?
  echo "DIGEST_RC=${digest_rc}" > "${ROOT}/${tag}_digest.status"

  find "${probe_root}" -maxdepth 4 \( -name 'run.log' -o -name 'run.stderr' -o -name 'run.status' -o -name 'case.xml' -o -name 'case_metadata.json' -o -name '*.csv' -o -name '*.json' -o -name '*.status' -o -name '*.txt' -o -name '*.md' \) \
    -print > "${ROOT}/${tag}_light_artifact_manifest.txt"
  find "${probe_root}" \( -path '*/output/*.vti' -o -path '*/output/*.pvti' \) -type f | wc -l | awk '{print "VTK_COUNT="$1}' > "${ROOT}/${tag}_vti_count.txt"
  if [[ "${KEEP_VTI}" != "1" ]]; then
    find "${probe_root}" \( -path '*/output/*.vti' -o -path '*/output/*.pvti' \) -type f -print -delete > "${ROOT}/${tag}_deleted_vti_manifest.txt"
  fi
  set -e

  if [[ "${driver_rc}" -ne 0 || "${analyzer_rc}" -ne 0 || "${digest_rc}" -ne 0 ]]; then
    return 3
  fi
  return 0
}

overall_rc=0
run_mode M0_legacy_stress 0 || overall_rc=3
run_mode M1_freeze_iter1 1 || overall_rc=3
run_mode M2_incoming_neq 2 || overall_rc=3

set +e
"${PY}" "${MATRIX_DIGEST}" "${ROOT}" \
  --csv "${ROOT}/b39_matrix_digest.csv" \
  --json "${ROOT}/b39_matrix_digest.json" \
  > "${ROOT}/b39_matrix_digest_stdout.json" \
  2> "${ROOT}/b39_matrix_digest_stderr.log"
matrix_digest_rc=$?
set -e
echo "MATRIX_DIGEST_RC=${matrix_digest_rc}" > "${ROOT}/matrix_digest.status"
if [[ "${matrix_digest_rc}" -ne 0 ]]; then
  overall_rc=3
fi

df -h /mnt/usb1t /home 2>&1 | tee "${ROOT}/df_after.txt"
{
  echo "OVERALL_RC=${overall_rc}"
  if [[ "${overall_rc}" -eq 0 ]]; then
    echo "VERDICT=b39_fmu_stress_mode_matrix_complete"
  else
    echo "VERDICT=b39_fmu_stress_mode_matrix_failed"
  fi
} | tee "${ROOT}/stage14_B39.status"
exit "${overall_rc}"
