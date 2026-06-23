#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/mnt/usb1t/RUNS/runs/stage14_dense_onset_probe_20260623}"
PY="${PY:-/usr/bin/python3}"
SCRIPT="${SCRIPT:-/home/yuan/stage14_s2_replay_smoke.py}"
ANALYZE="${ANALYZE:-/home/yuan/stage14_dense_onset_analyze.py}"
BIN="${BIN:-/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main}"
GPU="${GPU:-1}"
ITERATIONS="${ITERATIONS:-20}"
TIMEOUT="${TIMEOUT:-2400}"
FREE_THRESHOLD_KB="${FREE_THRESHOLD_KB:-52428800}"

mkdir -p "${ROOT}"

available_kb="$(df -Pk /mnt/usb1t | awk 'NR==2 {print $4}')"
if [[ "${available_kb}" -lt "${FREE_THRESHOLD_KB}" ]]; then
  find /mnt/usb1t/RUNS/runs -path '*/output/*.vti' -type f -print -delete \
    > "${ROOT}/cleanup_regenerable_vti_$(date +%Y%m%d_%H%M%S).log"
fi

echo "ROOT=${ROOT}"
echo "GPU=${GPU}"
echo "BIN=${BIN}"
sha256sum "${BIN}" | tee "${ROOT}/binary_sha256.txt"
nvidia-smi -L | tee "${ROOT}/nvidia_smi_L.txt"
df -h /mnt/usb1t | tee "${ROOT}/df_usb1t_before.txt"

case_root="${ROOT}/probe_R200_B1C2_pressure_physical_single_pass_dense20"
"${PY}" "${SCRIPT}" \
  --root "${case_root}" \
  --binary "${BIN}" \
  --gpu "${GPU}" \
  --iterations "${ITERATIONS}" \
  --vtk-period 1 \
  --log-period 1 \
  --timeout "${TIMEOUT}" \
  --cases wall_60to30_10 \
  --density-h 1.0 \
  --density-l 0.005 \
  --replay-mode 1 \
  --momentum-closure-diagnostics-mode 1 \
  --momentum-closure-probe-mode 1 \
  --phase-advection-velocity-mode 1 \
  --momentum-force-mode 0 \
  --force-fixed-iterator 2 \
  --force-fixed-tol 0 \
  --force-fixed-max-iter 2 \
  --pressure-closure-mode 1 \
  --force-density-closure-mode 0 \
  --force-fixed-point-mode 2 \
  --force \
  --run \
  --summarize \
  > "${ROOT}/probe_dense20_driver_stdout.json" \
  2> "${ROOT}/probe_dense20_driver_stderr.log" || true

"${PY}" "${ANALYZE}" "${case_root}/s2_replay_smoke_summary.json" \
  --frames-csv "${ROOT}/dense20_frames.csv" \
  --failures-json "${ROOT}/dense20_first_failures.json" \
  --failures-csv "${ROOT}/dense20_first_failures.csv" \
  > "${ROOT}/dense20_analysis_stdout.json"

df -h /mnt/usb1t | tee "${ROOT}/df_usb1t_after.txt"
echo "DONE ${ROOT}"
