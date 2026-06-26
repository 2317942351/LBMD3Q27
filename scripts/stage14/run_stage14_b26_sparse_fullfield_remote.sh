#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/mnt/usb1t/RUNS/runs/stage14_B26_sparse_fullfield_v2_20260627}"
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
FREE_THRESHOLD_KB="${FREE_THRESHOLD_KB:-52428800}"
KEEP_VTI="${KEEP_VTI:-0}"

mkdir -p "${ROOT}"

available_kb="$(df -Pk /mnt/usb1t | awk 'NR==2 {print $4}')"
if [[ "${available_kb}" -lt "${FREE_THRESHOLD_KB}" ]]; then
  find /mnt/usb1t/RUNS/runs -path '*/output/*.vti' -type f -print -delete \
    > "${ROOT}/cleanup_regenerable_vti_$(date +%Y%m%d_%H%M%S).log"
fi

{
  echo "stage=stage14_B26_sparse_fullfield"
  echo "root=${ROOT}"
  echo "gpu=${GPU}"
  echo "binary=${BIN}"
  echo "iterations=${ITERATIONS}"
  echo "vtk_period=${VTK_PERIOD}"
  echo "density_h=1.0"
  echo "density_l=0.005"
  echo "pressure_closure_mode=1"
  echo "force_fixed_point_mode=2"
  echo "phase_advection_velocity_mode=1"
  echo "probes=M0_FD0_full M0_FD1_full"
  echo "claim_limit=diagnostic_only_not_contact_angle_validation"
} | tee "${ROOT}/run_config.txt"
sha256sum "${BIN}" | tee "${ROOT}/binary_sha256.txt"
nvidia-smi -L | tee "${ROOT}/nvidia_smi_L.txt"
df -h /mnt/usb1t | tee "${ROOT}/df_usb1t_before.txt"

run_probe() {
  local tag="$1"
  local force_density_mode="$2"
  local probe_root="${ROOT}/${tag}"
  echo "RUN_B26 tag=${tag} ForceDensityClosureMode=${force_density_mode}"
  set +e
  "${PY}" "${SCRIPT}" \
    --root "${probe_root}" \
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

  "${PY}" "${ANALYZER}" "${probe_root}" --out-dir "${probe_root}" --prefix b26 \
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
run_probe M0_FD0_full 0 || overall_rc=3
run_probe M0_FD1_full 1 || overall_rc=3

set +e
"${PY}" "${DIGEST}" "${ROOT}" \
  --csv "${ROOT}/b26_sparse_digest.csv" \
  --json "${ROOT}/b26_sparse_digest.json" \
  > "${ROOT}/b26_sparse_digest_stdout.json" \
  2> "${ROOT}/b26_sparse_digest_stderr.log"
digest_rc=$?
set -e
echo "DIGEST_RC=${digest_rc}" > "${ROOT}/digest.status"
if [[ "${digest_rc}" -ne 0 ]]; then
  overall_rc=3
fi

df -h /mnt/usb1t | tee "${ROOT}/df_usb1t_after.txt"
echo "OVERALL_RC=${overall_rc}" | tee "${ROOT}/stage14_B26.status"
exit "${overall_rc}"
