#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/mnt/usb1t/RUNS/runs/stage17B_B8_neutral_20260625_600}"
EXPECTED_FINAL_STEP="${EXPECTED_FINAL_STEP:-600}"
B5_ANALYZE="${B5_ANALYZE:-/home/yuan/stage17B_B5_consumption_analyze.py}"
B6_ANALYZE="${B6_ANALYZE:-/home/yuan/stage17B_B6_contactline_lag_analyze.py}"
B8_ANALYZE="${B8_ANALYZE:-/home/yuan/stage17B_B8_neutral_analyze.py}"

overall_rc=0

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
