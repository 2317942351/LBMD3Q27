#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/mnt/usb1t/RUNS/runs/stage14_B27_branch_confirm_20260627}"
PY="${PY:-/usr/bin/python3}"
SCRIPT="${SCRIPT:-/home/yuan/stage14_s2_replay_smoke.py}"
ANALYZER="${ANALYZER:-/home/yuan/stage14_b17_onset_mask_argmax.py}"
DIGEST="${DIGEST:-/home/yuan/stage14_b23_b24_matrix_digest.py}"
BIN="${BIN:-/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main}"
GPU="${GPU:-1}"
BRANCH="${BRANCH:-denominator}"
ITERATIONS="${ITERATIONS:-14}"
VTK_PERIOD="${VTK_PERIOD:-1}"
LOG_PERIOD="${LOG_PERIOD:-1}"
TIMEOUT="${TIMEOUT:-2400}"
FREE_THRESHOLD_KB="${FREE_THRESHOLD_KB:-52428800}"
KEEP_VTI="${KEEP_VTI:-0}"

mkdir -p "${ROOT}"

available_kb="$(df -Pk /mnt/usb1t | awk 'NR==2 {print $4}')"
if [[ "${available_kb}" -lt "${FREE_THRESHOLD_KB}" ]]; then
  find /mnt/usb1t/RUNS/runs -path '*/output/*.vti' -type f -print -delete \
    > "${ROOT}/cleanup_regenerable_vti_$(date +%Y%m%d_%H%M%S).log"
fi

{
  echo "stage=stage14_B27_branch_confirm"
  echo "root=${ROOT}"
  echo "branch=${BRANCH}"
  echo "gpu=${GPU}"
  echo "binary=${BIN}"
  echo "iterations=${ITERATIONS}"
  echo "vtk_period=${VTK_PERIOD}"
  echo "density_h=1.0"
  echo "density_l=0.005"
  echo "claim_limit=diagnostic_only_not_contact_angle_validation"
} | tee "${ROOT}/run_config.txt"
sha256sum "${BIN}" | tee "${ROOT}/binary_sha256.txt"
nvidia-smi -L | tee "${ROOT}/nvidia_smi_L.txt"
df -h /mnt/usb1t | tee "${ROOT}/df_usb1t_before.txt"

run_probe() {
  local tag="$1"
  local momentum_force_mode="$2"
  local force_density_mode="$3"
  local b18_mode="$4"
  local b20_mode="$5"
  local vtk_field_set="$6"
  local probe_root="${ROOT}/${tag}"
  echo "RUN_B27 tag=${tag} MomentumForceMode=${momentum_force_mode} ForceDensityClosureMode=${force_density_mode} B18=${b18_mode} B20=${b20_mode}"
  set +e
  "${PY}" "${SCRIPT}" \
    --root "${probe_root}" \
    --binary "${BIN}" \
    --gpu "${GPU}" \
    --iterations "${ITERATIONS}" \
    --vtk-period "${VTK_PERIOD}" \
    --vtk-field-set "${vtk_field_set}" \
    --log-period "${LOG_PERIOD}" \
    --timeout "${TIMEOUT}" \
    --cases wall_60to30_10 \
    --density-h 1.0 \
    --density-l 0.005 \
    --replay-mode 1 \
    --momentum-closure-diagnostics-mode 1 \
    --b18-closure-diagnostics-mode "${b18_mode}" \
    --b18-velocity-bound 0.2 \
    --b20-hupdate-diagnostics-mode "${b20_mode}" \
    --b21-hpopulation-audit-mode 1 \
    --b22-velocity-producer-audit-mode 1 \
    --momentum-closure-probe-mode 1 \
    --phase-advection-velocity-mode 1 \
    --momentum-force-mode "${momentum_force_mode}" \
    --pressure-closure-mode 1 \
    --force-density-closure-mode "${force_density_mode}" \
    --force-density-rho-floor 0.005 \
    --force-fixed-point-mode 2 \
    --force-fixed-iterator 2 \
    --force-fixed-tol 0 \
    --force-fixed-max-iter 2 \
    --force \
    --run \
    --summarize \
    > "${probe_root}_driver_stdout.json" \
    2> "${probe_root}_driver_stderr.log"
  local driver_rc=$?
  echo "DRIVER_RC=${driver_rc}" > "${probe_root}_driver.status"

  "${PY}" "${ANALYZER}" "${probe_root}" --out-dir "${probe_root}" --prefix b27 \
    > "${probe_root}_analyzer_stdout.json" \
    2> "${probe_root}_analyzer_stderr.log"
  local analyzer_rc=$?
  echo "ANALYZER_RC=${analyzer_rc}" > "${probe_root}_analyzer.status"
  set -e

  find "${probe_root}" -maxdepth 4 \( -name 'run.log' -o -name 'run.stderr' -o -name 'run.status' -o -name 'case.xml' -o -name 'case_metadata.json' -o -name 's2_replay_smoke_summary.json' -o -name '*.csv' -o -name '*.json' -o -name '*.status' -o -name '*.txt' \) \
    -print > "${probe_root}_light_artifact_manifest.txt"
  find "${probe_root}" \( -path '*/output/*.vti' -o -path '*/output/*.pvti' \) -type f | wc -l | awk '{print "VTK_COUNT="$1}' > "${probe_root}_vti_count.txt"
  if [[ "${KEEP_VTI}" != "1" ]]; then
    find "${probe_root}" \( -path '*/output/*.vti' -o -path '*/output/*.pvti' \) -type f -print -delete > "${probe_root}_deleted_vti_manifest.txt"
    find "${probe_root}" -name '*argmax_trace.json' -type f -print -delete > "${probe_root}_deleted_argmax_trace_manifest.txt"
  fi

  if [[ "${driver_rc}" -ne 0 || "${analyzer_rc}" -ne 0 ]]; then
    return 3
  fi
  return 0
}

overall_rc=0
case "${BRANCH}" in
  denominator)
    run_probe D0_raw_rho 0 0 1 0 b22 || overall_rc=3
    run_probe D1_density_floor 0 1 1 0 b22 || overall_rc=3
    ;;
  numerator)
    run_probe N0_legacy_total 0 0 0 0 b22 || overall_rc=3
    run_probe N1_noFmu 1 0 0 0 b22 || overall_rc=3
    run_probe N2_noSurf 3 0 0 0 b22 || overall_rc=3
    run_probe N3_noPressure 2 0 0 0 b22 || overall_rc=3
    ;;
  stress)
    run_probe S0_legacy_stress 0 0 1 0 minimal || overall_rc=3
    run_probe S1_density_floor_stress 0 1 1 0 minimal || overall_rc=3
    run_probe S2_noFmu_stress 1 0 1 0 minimal || overall_rc=3
    run_probe S3_noSurf_stress 3 0 1 0 minimal || overall_rc=3
    run_probe S4_noMomentum_stress 4 0 1 0 minimal || overall_rc=3
    ;;
  phase)
    run_probe P0_legacy_h 0 0 1 1 minimal || overall_rc=3
    run_probe P1_density_floor_h 0 1 1 1 minimal || overall_rc=3
    ;;
  *)
    echo "Unknown BRANCH=${BRANCH}; expected denominator|numerator|stress|phase" | tee "${ROOT}/error.txt"
    exit 2
    ;;
esac

set +e
"${PY}" "${DIGEST}" "${ROOT}" \
  --csv "${ROOT}/b27_matrix_digest.csv" \
  --json "${ROOT}/b27_matrix_digest.json" \
  > "${ROOT}/b27_matrix_digest_stdout.json" \
  2> "${ROOT}/b27_matrix_digest_stderr.log"
digest_rc=$?
set -e
echo "DIGEST_RC=${digest_rc}" > "${ROOT}/digest.status"
if [[ "${digest_rc}" -ne 0 ]]; then
  overall_rc=3
fi

df -h /mnt/usb1t | tee "${ROOT}/df_usb1t_after.txt"
echo "OVERALL_RC=${overall_rc}" | tee "${ROOT}/stage14_B27.status"
exit "${overall_rc}"
