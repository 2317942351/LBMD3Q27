#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/mnt/usb1t/RUNS/runs/stage14_B30_phase_velocity_candidate_20260627}"
PY="${PY:-/usr/bin/python3}"
SCRIPT="${SCRIPT:-/home/yuan/stage14_s2_replay_smoke.py}"
ANALYZER="${ANALYZER:-/home/yuan/stage14_b17_onset_mask_argmax.py}"
DIGEST="${DIGEST:-/home/yuan/stage14_b23_b24_matrix_digest.py}"
BIN="${BIN:-/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main}"
GPU="${GPU:-1}"
FMU_STRESS_MODE="${FMU_STRESS_MODE:-2}"
PHASE_ADV_MODE="${PHASE_ADV_MODE:-2}"
TIMEOUT="${TIMEOUT:-3600}"
KEEP_VTI="${KEEP_VTI:-0}"

mkdir -p "${ROOT}"

{
  echo "stage=stage14_B30_phase_velocity_candidate"
  echo "root=${ROOT}"
  echo "gpu=${GPU}"
  echo "binary=${BIN}"
  echo "fmu_stress_closure_mode=${FMU_STRESS_MODE}"
  echo "phase_advection_velocity_mode=${PHASE_ADV_MODE}"
  echo "density_h=1.0"
  echo "density_l=0.005"
  echo "claim_limit=phase_velocity_candidate_only_not_contact_angle_validation"
} | tee "${ROOT}/run_config.txt"
sha256sum "${BIN}" | tee "${ROOT}/binary_sha256.txt"
nvidia-smi -L | tee "${ROOT}/nvidia_smi_L.txt"
df -h /mnt/usb1t | tee "${ROOT}/df_usb1t_before.txt"

run_probe() {
  local tag="$1"
  local iterations="$2"
  local vtk_period="$3"
  local probe_root="${ROOT}/${tag}"
  echo "RUN_B30 tag=${tag} iterations=${iterations} FmuStressClosureMode=${FMU_STRESS_MODE} PhaseAdvectionVelocityMode=${PHASE_ADV_MODE}"
  set +e
  "${PY}" "${SCRIPT}" \
    --root "${probe_root}" \
    --binary "${BIN}" \
    --gpu "${GPU}" \
    --iterations "${iterations}" \
    --vtk-period "${vtk_period}" \
    --vtk-field-set b27stress \
    --log-period 1 \
    --timeout "${TIMEOUT}" \
    --cases wall_60to30_10 \
    --density-h 1.0 \
    --density-l 0.005 \
    --replay-mode 1 \
    --momentum-closure-diagnostics-mode 1 \
    --b18-closure-diagnostics-mode 1 \
    --b18-velocity-bound 0.2 \
    --b20-hupdate-diagnostics-mode 0 \
    --b21-hpopulation-audit-mode 1 \
    --b22-velocity-producer-audit-mode 1 \
    --momentum-closure-probe-mode 1 \
    --phase-advection-velocity-mode "${PHASE_ADV_MODE}" \
    --momentum-force-mode 0 \
    --fmu-stress-closure-mode "${FMU_STRESS_MODE}" \
    --pressure-closure-mode 1 \
    --force-density-closure-mode 0 \
    --force-density-rho-floor 0.005 \
    --force-fixed-point-mode 2 \
    --force-fixed-iterator 2 \
    --force-fixed-tol 0 \
    --force-fixed-max-iter 2 \
    --force \
    --run \
    > "${probe_root}_driver_stdout.json" \
    2> "${probe_root}_driver_stderr.log"
  local driver_rc=$?
  echo "DRIVER_RC=${driver_rc}" > "${probe_root}_driver.status"
  if [[ "${driver_rc}" -ne 0 ]]; then
    return 3
  fi

  "${PY}" "${ANALYZER}" "${probe_root}" --out-dir "${probe_root}" --prefix b30 \
    > "${probe_root}_analyzer_stdout.json" \
    2> "${probe_root}_analyzer_stderr.log"
  local analyzer_rc=$?
  echo "ANALYZER_RC=${analyzer_rc}" > "${probe_root}_analyzer.status"

  find "${probe_root}" -maxdepth 4 \( -name 'run.log' -o -name 'run.stderr' -o -name 'run.status' -o -name 'case.xml' -o -name 'case_metadata.json' -o -name '*.csv' -o -name '*.json' -o -name '*.status' -o -name '*.txt' \) \
    -print > "${probe_root}_light_artifact_manifest.txt"
  find "${probe_root}" \( -path '*/output/*.vti' -o -path '*/output/*.pvti' \) -type f | wc -l | awk '{print "VTK_COUNT="$1}' > "${probe_root}_vti_count.txt"
  if [[ "${KEEP_VTI}" != "1" ]]; then
    find "${probe_root}" \( -path '*/output/*.vti' -o -path '*/output/*.pvti' \) -type f -print -delete > "${probe_root}_deleted_vti_manifest.txt"
    find "${probe_root}" -name '*argmax_trace.json' -type f -print -delete > "${probe_root}_deleted_argmax_trace_manifest.txt"
  fi
  set -e

  if [[ "${analyzer_rc}" -ne 0 ]]; then
    return 3
  fi
  return 0
}

overall_rc=0
run_probe B30_020 20 1 || overall_rc=3
if [[ "${overall_rc}" -eq 0 ]]; then
  run_probe B30_100 100 5 || overall_rc=3
fi

set +e
"${PY}" "${DIGEST}" "${ROOT}" \
  --csv "${ROOT}/b30_matrix_digest.csv" \
  --json "${ROOT}/b30_matrix_digest.json" \
  > "${ROOT}/b30_matrix_digest_stdout.json" \
  2> "${ROOT}/b30_matrix_digest_stderr.log"
digest_rc=$?
set -e
echo "DIGEST_RC=${digest_rc}" > "${ROOT}/digest.status"
if [[ "${digest_rc}" -ne 0 ]]; then
  overall_rc=3
fi

df -h /mnt/usb1t | tee "${ROOT}/df_usb1t_after.txt"
echo "OVERALL_RC=${overall_rc}" | tee "${ROOT}/stage14_B30.status"
exit "${overall_rc}"
