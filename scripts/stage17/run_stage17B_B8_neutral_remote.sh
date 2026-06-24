#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/mnt/usb1t/RUNS/runs/stage17B_B8_neutral_20260625_600}"
CASE_SRC="${CASE_SRC:-/home/yuan/stage17B_B8_neutral_cases}"
B5_ANALYZE="${B5_ANALYZE:-/home/yuan/stage17B_B5_consumption_analyze.py}"
B6_ANALYZE="${B6_ANALYZE:-/home/yuan/stage17B_B6_contactline_lag_analyze.py}"
B8_ANALYZE="${B8_ANALYZE:-/home/yuan/stage17B_B8_neutral_analyze.py}"
SHADOW_ANALYZE="${SHADOW_ANALYZE:-/home/yuan/stage17B_shadow_analyze.py}"
BIN="${BIN:-/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main}"
GPU="${GPU:-1}"
TIMEOUT="${TIMEOUT:-3600}"
FREE_THRESHOLD_KB="${FREE_THRESHOLD_KB:-52428800}"
EXPECTED_FINAL_STEP="${EXPECTED_FINAL_STEP:-600}"
PURPOSE="${PURPOSE:-stage17B_B8_neutral_drift_isolation}"
CASE_NAMES="${CASE_NAMES:-cylinder_init090_neutral_A_legacy_baseline cylinder_init090_neutral_B_shadow_only cylinder_init090_neutral_C_controlled_psi cylinder_init090_neutral_D_controlled_legacy}"

export CUDA_VISIBLE_DEVICES="${GPU}"
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh

mkdir -p "${ROOT}"

available_kb="$(df -Pk /mnt/usb1t | awk 'NR==2 {print $4}')"
if [[ "${available_kb}" -lt "${FREE_THRESHOLD_KB}" ]]; then
  find /mnt/usb1t/RUNS/runs -path '*/output/*.vti' -type f -print -delete \
    > "${ROOT}/cleanup_regenerable_vti_$(date +%Y%m%d_%H%M%S).log"
fi

{
  echo "date=$(date -Is)"
  echo "purpose=${PURPOSE}"
  echo "ROOT=${ROOT}"
  echo "CASE_SRC=${CASE_SRC}"
  echo "BIN=${BIN}"
  echo "GPU=${GPU}"
  echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES}"
  echo "EXPECTED_FINAL_STEP=${EXPECTED_FINAL_STEP}"
  echo "claim_limit=B8 neutral drift root-cause diagnostic only; not contact-angle validation"
} | tee "${ROOT}/run_manifest.txt"

nvidia-smi -L | tee "${ROOT}/nvidia_smi_L.txt"
df -h /mnt/usb1t | tee "${ROOT}/df_usb1t_before.txt"
sha256sum "${BIN}" | tee "${ROOT}/binary_sha256.txt"

run_one() {
  local case_name="$1"
  local src="${CASE_SRC}/${case_name}"
  local dst="${ROOT}/${case_name}"
  mkdir -p "${dst}"
  cp -f "${src}/case.xml" "${dst}/case.xml"
  if [[ -f "${src}/case_metadata.json" ]]; then
    cp -f "${src}/case_metadata.json" "${dst}/case_metadata.json"
  fi
  (
    cd "${dst}"
    echo "START ${case_name} $(date -Is)" | tee run.status
    timeout "${TIMEOUT}" "${BIN}" case.xml > run.log 2> run.stderr
    rc=$?
    echo "RC=${rc}" | tee -a run.status
    echo "END ${case_name} $(date -Is)" | tee -a run.status
    exit "${rc}"
  )
}

overall_rc=0
for case_name in ${CASE_NAMES}; do
  if ! run_one "${case_name}"; then
    overall_rc=1
  fi
done

if [[ -f "${SHADOW_ANALYZE}" ]]; then
  python3 "${SHADOW_ANALYZE}" "${ROOT}" \
    --out-json "${ROOT}/stage17B_shadow_analysis.json" \
    --out-csv "${ROOT}/stage17B_shadow_frames.csv" \
    --expected-final-step "${EXPECTED_FINAL_STEP}" \
    > "${ROOT}/stage17B_shadow_analysis_stdout.json" || true
fi

if [[ -f "${B5_ANALYZE}" ]]; then
  python3 "${B5_ANALYZE}" "${ROOT}" \
    --out-json "${ROOT}/stage17B_B5_consumption_analysis.json" \
    --out-csv "${ROOT}/stage17B_B5_consumption_frames.csv" \
    --expected-final-step "${EXPECTED_FINAL_STEP}" \
    > "${ROOT}/stage17B_B5_consumption_analysis_stdout.json" || true
else
  echo "missing B5 analyzer: ${B5_ANALYZE}" | tee "${ROOT}/b5_analysis_missing.txt"
fi

if [[ -f "${B6_ANALYZE}" ]]; then
  python3 "${B6_ANALYZE}" "${ROOT}" \
    --out-dir "${ROOT}/post/B6_contactline_lag" \
    --expected-final-step "${EXPECTED_FINAL_STEP}" \
    > "${ROOT}/stage17B_B6_contactline_lag_stdout.json" || overall_rc=1
else
  echo "missing B6 analyzer: ${B6_ANALYZE}" | tee "${ROOT}/b6_analysis_missing.txt"
  overall_rc=1
fi

if [[ -f "${B8_ANALYZE}" ]]; then
  python3 "${B8_ANALYZE}" "${ROOT}" \
    --out-json "${ROOT}/stage17B_B8_neutral_analysis.json" \
    --out-csv "${ROOT}/stage17B_B8_neutral_summary.csv" \
    > "${ROOT}/stage17B_B8_neutral_analysis_stdout.json" || overall_rc=1
else
  echo "missing B8 analyzer: ${B8_ANALYZE}" | tee "${ROOT}/b8_analysis_missing.txt"
  overall_rc=1
fi

df -h /mnt/usb1t | tee "${ROOT}/df_usb1t_after.txt"
echo "DONE ${ROOT} rc=${overall_rc}" | tee "${ROOT}/done.status"
exit "${overall_rc}"
