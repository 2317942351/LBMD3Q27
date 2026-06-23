#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/mnt/usb1t/RUNS/runs/stage14_momentum_closure_probe_20260623}"
PY="${PY:-/usr/bin/python3}"
SCRIPT="${SCRIPT:-/home/yuan/stage14_s2_replay_smoke.py}"
BIN="${BIN:-/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main}"
GPU="${GPU:-1}"
ITERATIONS="${ITERATIONS:-6}"
VTK_PERIOD="${VTK_PERIOD:-1}"
LOG_PERIOD="${LOG_PERIOD:-1}"
TIMEOUT="${TIMEOUT:-600}"
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

for mode in 0 1 2 3 4; do
  case_root="${ROOT}/probe_A${mode}"
  echo "RUN MomentumClosureProbeMode=${mode} case_root=${case_root}"
  "${PY}" "${SCRIPT}" \
    --root "${case_root}" \
    --binary "${BIN}" \
    --gpu "${GPU}" \
    --iterations "${ITERATIONS}" \
    --vtk-period "${VTK_PERIOD}" \
    --log-period "${LOG_PERIOD}" \
    --timeout "${TIMEOUT}" \
    --cases wall_60to30_10 \
    --replay-mode 1 \
    --momentum-closure-diagnostics-mode 1 \
    --momentum-closure-probe-mode "${mode}" \
    --phase-advection-velocity-mode 1 \
    --momentum-force-mode 0 \
    --force-fixed-iterator 1 \
    --force \
    --run \
    --summarize \
    > "${case_root}_driver_stdout.json" \
    2> "${case_root}_driver_stderr.log" || true
done

df -h /mnt/usb1t | tee "${ROOT}/df_usb1t_after.txt"
echo "DONE ${ROOT}"
