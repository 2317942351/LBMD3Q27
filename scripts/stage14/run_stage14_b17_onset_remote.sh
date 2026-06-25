#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/mnt/usb1t/RUNS/runs/stage14_B17_onset_mask_argmax_20260625}"
PY="${PY:-/usr/bin/python3}"
SMOKE_SCRIPT="${SMOKE_SCRIPT:-/home/yuan/stage14_s2_replay_smoke.py}"
B17_ANALYZER="${B17_ANALYZER:-/home/yuan/stage14_b17_onset_mask_argmax.py}"
BIN="${BIN:-/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main}"
GPU="${GPU:-1}"
ITERATIONS="${ITERATIONS:-20}"
TIMEOUT="${TIMEOUT:-2400}"
FREE_THRESHOLD_KB="${FREE_THRESHOLD_KB:-52428800}"

mkdir -p "${ROOT}"

available_kb="$(df -Pk /mnt/usb1t | awk 'NR==2 {print $4}')"
if [[ "${available_kb}" -lt "${FREE_THRESHOLD_KB}" ]]; then
  find /mnt/usb1t/RUNS/runs \
    -path "${ROOT}/*" -prune -o \
    -path '*/output/*.vti' -type f -print -delete \
    > "${ROOT}/cleanup_regenerable_vti_$(date +%Y%m%d_%H%M%S).log"
fi

echo "ROOT=${ROOT}" | tee "${ROOT}/run_config.txt"
echo "GPU=${GPU}" | tee -a "${ROOT}/run_config.txt"
echo "BIN=${BIN}" | tee -a "${ROOT}/run_config.txt"
echo "ITERATIONS=${ITERATIONS}" | tee -a "${ROOT}/run_config.txt"
sha256sum "${BIN}" | tee "${ROOT}/binary_sha256.txt"
nvidia-smi -L | tee "${ROOT}/nvidia_smi_L.txt"
df -h /mnt/usb1t | tee "${ROOT}/df_usb1t_before.txt"

case_root="${ROOT}/probe_wall_60to30_R200_step${ITERATIONS}"
rm -rf "${case_root}"

set +e
"${PY}" "${SMOKE_SCRIPT}" \
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
  > "${ROOT}/b17_driver_stdout.json" \
  2> "${ROOT}/b17_driver_stderr.log"
driver_rc="$?"
set -e
echo "DRIVER_RC=${driver_rc}" | tee "${ROOT}/driver.status"

set +e
"${PY}" "${B17_ANALYZER}" "${case_root}" \
  --out-dir "${ROOT}" \
  > "${ROOT}/b17_analyzer_stdout.json" \
  2> "${ROOT}/b17_analyzer_stderr.log"
analyzer_rc="$?"
set -e
echo "ANALYZER_RC=${analyzer_rc}" | tee "${ROOT}/analyzer.status"

find "${case_root}" -maxdepth 3 \( -name 'run.log' -o -name 'run.stderr' -o -name 'run.status' -o -name 'case.xml' -o -name 'case_metadata.json' -o -name 's2_replay_smoke_summary.json' \) \
  -print > "${ROOT}/light_artifact_manifest.txt"
find "${case_root}" -path '*/output/*.vti' -type f | wc -l | awk '{print "VTI_COUNT="$1}' | tee "${ROOT}/vti_count.txt"
df -h /mnt/usb1t | tee "${ROOT}/df_usb1t_after.txt"

if [[ "${analyzer_rc}" -ne 0 ]]; then
  exit "${analyzer_rc}"
fi
exit 0
