#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/mnt/usb1t/RUNS/runs/stage14_B36_force_over_rho_cap_20260628}"
PY="${PY:-/usr/bin/python3}"
SCRIPT="${SCRIPT:-/home/yuan/stage14_s2_replay_smoke.py}"
ANALYZER="${ANALYZER:-/home/yuan/stage14_b17_onset_mask_argmax.py}"
GATE="${GATE:-/home/yuan/stage14_b36_force_cap_gate.py}"
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
  echo "stage=stage14_B36_force_over_rho_cap"
  echo "root=${ROOT}"
  echo "gpu=${GPU}"
  echo "binary=${BIN}"
  echo "iterations=${ITERATIONS}"
  echo "vtk_period=${VTK_PERIOD}"
  echo "vtk_field_set=b36cap"
  echo "density_h=1.0"
  echo "density_l=0.005"
  echo "pressure_closure_mode=1"
  echo "force_fixed_point_mode=2"
  echo "phase_advection_velocity_mode=2"
  echo "force_density_closure_mode=2"
  echo "fmu_stress_closure_mode=2"
  echo "claim_limit=default_off_force_over_rho_limiter_probe_not_contact_angle_validation"
} | tee "${ROOT}/run_config.txt"
sha256sum "${BIN}" | tee "${ROOT}/binary_sha256.txt"
nvidia-smi -L | tee "${ROOT}/nvidia_smi_L.txt"
df -h /mnt/usb1t /home 2>&1 | tee "${ROOT}/df_before.txt"

run_probe() {
  local tag="$1"
  local limiter_mode="$2"
  local cap="$3"
  local iterations="$4"
  local keep_vti="$5"
  local gate_required="$6"
  local probe_root="${ROOT}/${tag}"
  echo "RUN_B36 tag=${tag} limiter_mode=${limiter_mode} cap=${cap} iterations=${iterations}"
  set +e
  "${PY}" "${SCRIPT}" \
    --root "${probe_root}" \
    --binary "${BIN}" \
    --gpu "${GPU}" \
    --iterations "${iterations}" \
    --vtk-period "${VTK_PERIOD}" \
    --vtk-field-set b36cap \
    --log-period "${LOG_PERIOD}" \
    --timeout "${TIMEOUT}" \
    --cases wall_60to30_10 \
    --density-h 1.0 \
    --density-l 0.005 \
    --replay-mode 1 \
    --momentum-closure-diagnostics-mode 1 \
    --momentum-closure-probe-mode 1 \
    --phase-advection-velocity-mode 2 \
    --momentum-force-mode 0 \
    --fmu-stress-closure-mode 2 \
    --pressure-closure-mode 1 \
    --force-density-closure-mode 2 \
    --force-density-rho-floor 0.005 \
    --force-fixed-point-mode 2 \
    --force-fixed-iterator 2 \
    --force-fixed-tol 0 \
    --force-fixed-max-iter 2 \
    --b36-force-over-rho-limiter-mode "${limiter_mode}" \
    --b36-force-over-rho-cap "${cap}" \
    --force \
    --run \
    > "${probe_root}_driver_stdout.json" \
    2> "${probe_root}_driver_stderr.log"
  local driver_rc=$?
  echo "DRIVER_RC=${driver_rc}" > "${probe_root}_driver.status"

  "${PY}" "${ANALYZER}" "${probe_root}" --out-dir "${probe_root}" --prefix b36 \
    > "${probe_root}_analyzer_stdout.json" \
    2> "${probe_root}_analyzer_stderr.log"
  local analyzer_rc=$?
  echo "ANALYZER_RC=${analyzer_rc}" > "${probe_root}_analyzer.status"

  "${PY}" "${GATE}" "${probe_root}" \
    --out "${probe_root}/b36_force_cap_gate.json" \
    --csv "${probe_root}/b36_force_cap_gate_frames.csv" \
    > "${probe_root}_gate_stdout.json" \
    2> "${probe_root}_gate_stderr.log"
  local gate_rc=$?
  echo "GATE_RC=${gate_rc}" > "${probe_root}_gate.status"

  find "${probe_root}" -maxdepth 4 \( -name 'run.log' -o -name 'run.stderr' -o -name 'run.status' -o -name 'case.xml' -o -name 'case_metadata.json' -o -name '*.csv' -o -name '*.json' -o -name '*.status' -o -name '*.txt' \) \
    -print > "${probe_root}_light_artifact_manifest.txt"
  find "${probe_root}" \( -path '*/output/*.vti' -o -path '*/output/*.pvti' \) -type f | wc -l | awk '{print "VTK_COUNT="$1}' > "${probe_root}_vti_count.txt"
  if [[ "${keep_vti}" != "1" && "${KEEP_VTI}" != "1" ]]; then
    find "${probe_root}" \( -path '*/output/*.vti' -o -path '*/output/*.pvti' \) -type f -print -delete > "${probe_root}_deleted_vti_manifest.txt"
  fi
  set -e

  if [[ "${driver_rc}" -ne 0 || "${analyzer_rc}" -ne 0 ]]; then
    return 3
  fi
  if [[ "${gate_required}" == "1" && "${gate_rc}" -ne 0 ]]; then
    return 3
  fi
  return 0
}

overall_rc=0
run_probe S0_smoke_mode2_cap1e6 2 1000000 1 1 1 || overall_rc=3
run_probe M0_baseline 0 0 "${ITERATIONS}" 0 0 || overall_rc=3
run_probe M1_shadow_cap1e4 1 10000 "${ITERATIONS}" 0 0 || overall_rc=3
run_probe M2_write_cap1e4 2 10000 "${ITERATIONS}" 0 1 || overall_rc=3
run_probe M2_write_cap1e3 2 1000 "${ITERATIONS}" 0 1 || overall_rc=3

df -h /mnt/usb1t /home 2>&1 | tee "${ROOT}/df_after.txt"
echo "OVERALL_RC=${overall_rc}" | tee "${ROOT}/stage14_B36.status"
exit "${overall_rc}"
