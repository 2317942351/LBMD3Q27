#!/usr/bin/env bash
set -euo pipefail

export ROOT="${ROOT:-/home/yuan/src/TCLB_lbm2026_compile_lane}"
export LOG="${LOG:-/home/yuan/lbm2026_stage14_B22_compile_20260626.log}"
export JOBS="${JOBS:-8}"

rm -f "${LOG}" "${LOG}.status"
bash /home/yuan/compile_stage14_b18_after_source_remote.sh
rc=$?
echo "RC=${rc}" > "${LOG}.status"
exit "${rc}"
