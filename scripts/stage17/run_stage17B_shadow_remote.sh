#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/mnt/usb1t/RUNS/runs/stage17B_shadow_cylinder_20260624}"
CASE_SRC="${CASE_SRC:-/home/yuan/stage17B_cylinder_shadow_cases}"
ANALYZE="${ANALYZE:-/home/yuan/stage17B_shadow_analyze.py}"
BIN="${BIN:-/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main}"
GPU="${GPU:-1}"
TIMEOUT="${TIMEOUT:-1800}"
FREE_THRESHOLD_KB="${FREE_THRESHOLD_KB:-52428800}"

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
  echo "purpose=stage17B_cylinder_diffuse_solid_shadow_only"
  echo "ROOT=${ROOT}"
  echo "CASE_SRC=${CASE_SRC}"
  echo "BIN=${BIN}"
  echo "GPU=${GPU}"
  echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES}"
  echo "claim_limit=shadow diagnostics only; not contact-angle validation"
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
for case_name in \
  cylinder_theta060_shadow \
  cylinder_theta090_shadow \
  cylinder_theta120_shadow
do
  if ! run_one "${case_name}"; then
    overall_rc=1
  fi
done

if [[ -f "${ANALYZE}" ]]; then
  python3 "${ANALYZE}" "${ROOT}" \
    --out-json "${ROOT}/stage17B_shadow_analysis.json" \
    --out-csv "${ROOT}/stage17B_shadow_frames.csv" \
    > "${ROOT}/stage17B_shadow_analysis_stdout.json" || overall_rc=1
else
  echo "missing analyzer: ${ANALYZE}" | tee "${ROOT}/analysis_missing.txt"
  overall_rc=1
fi

df -h /mnt/usb1t | tee "${ROOT}/df_usb1t_after.txt"
echo "DONE ${ROOT} rc=${overall_rc}" | tee "${ROOT}/done.status"
exit "${overall_rc}"
