#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/mnt/usb1t/RUNS/runs/stage14_B40_stress_construction_audit_20260628}"
PY="${PY:-/usr/bin/python3}"
SCRIPT="${SCRIPT:-/home/yuan/stage14_s2_replay_smoke.py}"
ANALYZER="${ANALYZER:-/home/yuan/stage14_b17_onset_mask_argmax.py}"
DIGEST="${DIGEST:-/home/yuan/stage14_b38_first_bad_ledger_digest.py}"
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
  echo "stage=stage14_B40_stress_construction_audit"
  echo "root=${ROOT}"
  echo "gpu=${GPU}"
  echo "binary=${BIN}"
  echo "iterations=${ITERATIONS}"
  echo "vtk_period=${VTK_PERIOD}"
  echo "vtk_field_set=b40stress"
  echo "density_h=1.0"
  echo "density_l=0.005"
  echo "pressure_closure_mode=1"
  echo "force_fixed_point_mode=2"
  echo "phase_advection_velocity_mode=2"
  echo "force_density_closure_mode=2"
  echo "force_density_rho_floor=0.005"
  echo "stage14_b18_closure_diagnostics_mode=1"
  echo "stage14_b40_stress_audit_mode=1"
  echo "claim_limit=stress_algebra_diagnostic_not_contact_angle_validation"
} | tee "${ROOT}/run_config.txt"

sha256sum "${BIN}" | tee "${ROOT}/binary_sha256.txt"
nvidia-smi -L | tee "${ROOT}/nvidia_smi_L.txt"
df -h /mnt/usb1t /home 2>&1 | tee "${ROOT}/df_before.txt"

set +e
"${PY}" "${SCRIPT}" \
  --root "${ROOT}/B40_stress_audit" \
  --binary "${BIN}" \
  --gpu "${GPU}" \
  --iterations "${ITERATIONS}" \
  --vtk-period "${VTK_PERIOD}" \
  --vtk-field-set b40stress \
  --log-period "${LOG_PERIOD}" \
  --timeout "${TIMEOUT}" \
  --cases wall_60to30_10 \
  --density-h 1.0 \
  --density-l 0.005 \
  --replay-mode 1 \
  --momentum-closure-diagnostics-mode 1 \
  --b18-closure-diagnostics-mode 1 \
  --b40-stress-audit-mode 1 \
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
  > "${ROOT}/b40_driver_stdout.json" \
  2> "${ROOT}/b40_driver_stderr.log"
driver_rc=$?
echo "DRIVER_RC=${driver_rc}" > "${ROOT}/b40_driver.status"

"${PY}" "${ANALYZER}" "${ROOT}/B40_stress_audit" --out-dir "${ROOT}/B40_stress_audit" --prefix b40 \
  > "${ROOT}/b40_analyzer_stdout.json" \
  2> "${ROOT}/b40_analyzer_stderr.log"
analyzer_rc=$?
echo "ANALYZER_RC=${analyzer_rc}" > "${ROOT}/b40_analyzer.status"

"${PY}" "${DIGEST}" "${ROOT}/B40_stress_audit" \
  --prefix b40 \
  --out-json "${ROOT}/B40_stress_audit/b40_stress_construction_digest.json" \
  --out-md "${ROOT}/B40_stress_audit/b40_stress_construction_digest.md" \
  > "${ROOT}/b40_digest_stdout.json" \
  2> "${ROOT}/b40_digest_stderr.log"
digest_rc=$?
echo "DIGEST_RC=${digest_rc}" > "${ROOT}/b40_digest.status"
set -e

find "${ROOT}" -maxdepth 5 \( -name 'run.log' -o -name 'run.stderr' -o -name 'run.status' -o -name 'case.xml' -o -name 'case_metadata.json' -o -name '*.csv' -o -name '*.json' -o -name '*.status' -o -name '*.txt' -o -name '*.md' \) \
  -print > "${ROOT}/light_artifact_manifest.txt"
find "${ROOT}" \( -path '*/output/*.vti' -o -path '*/output/*.pvti' \) -type f | wc -l | awk '{print "VTK_COUNT="$1}' > "${ROOT}/vti_count.txt"
if [[ "${KEEP_VTI}" != "1" ]]; then
  find "${ROOT}" \( -path '*/output/*.vti' -o -path '*/output/*.pvti' \) -type f -print -delete > "${ROOT}/deleted_vti_manifest.txt"
fi

df -h /mnt/usb1t /home 2>&1 | tee "${ROOT}/df_after.txt"

overall_rc=0
if [[ "${driver_rc}" -ne 0 || "${analyzer_rc}" -ne 0 || "${digest_rc}" -ne 0 ]]; then
  overall_rc=3
fi

{
  echo "OVERALL_RC=${overall_rc}"
  if [[ "${overall_rc}" -eq 0 ]]; then
    echo "VERDICT=b40_stress_construction_audit_complete"
  else
    echo "VERDICT=b40_stress_construction_audit_failed"
  fi
} | tee "${ROOT}/stage14_B40.status"

exit "${overall_rc}"
