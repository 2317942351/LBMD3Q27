#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/mnt/usb1t/RUNS/runs/stage17B_B13_initial_stencil_split_20260625}"
CASE_SRC="${CASE_SRC:-/home/yuan/stage17B_B13_initial_stencil_split_cases}"
CASE_NAME="${CASE_NAME:-cylinder_init090_b13_initial_stencil_split_s0001}"
BIN="${BIN:-/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main}"
GPU="${GPU:-1}"
TIMEOUT="${TIMEOUT:-600}"
PURPOSE="${PURPOSE:-stage17B_B13_initial_stencil_split_probe}"

export CUDA_VISIBLE_DEVICES="${GPU}"
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh

mkdir -p "${ROOT}"

{
  echo "date=$(date -Is)"
  echo "purpose=${PURPOSE}"
  echo "ROOT=${ROOT}"
  echo "CASE_SRC=${CASE_SRC}"
  echo "CASE_NAME=${CASE_NAME}"
  echo "BIN=${BIN}"
  echo "GPU=${GPU}"
  echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES}"
  echo "claim_limit=B13 initial stencil split diagnostic only; not contact-angle validation"
} | tee "${ROOT}/run_manifest.txt"

nvidia-smi -L | tee "${ROOT}/nvidia_smi_L.txt"
df -h /mnt/usb1t | tee "${ROOT}/df_usb1t_before.txt"
sha256sum "${BIN}" | tee "${ROOT}/binary_sha256.txt"

src="${CASE_SRC}/${CASE_NAME}"
dst="${ROOT}/${CASE_NAME}"
mkdir -p "${dst}"
cp -f "${src}/case.xml" "${dst}/case.xml"
if [[ -f "${src}/case_metadata.json" ]]; then
  cp -f "${src}/case_metadata.json" "${dst}/case_metadata.json"
fi

(
  cd "${dst}"
  echo "START ${CASE_NAME} $(date -Is)" | tee run.status
  timeout "${TIMEOUT}" "${BIN}" case.xml > run.log 2> run.stderr
  rc=$?
  echo "RC=${rc}" | tee -a run.status
  echo "END ${CASE_NAME} $(date -Is)" | tee -a run.status
  exit "${rc}"
)

df -h /mnt/usb1t | tee "${ROOT}/df_usb1t_after.txt"
echo "DONE ${ROOT} rc=0" | tee "${ROOT}/done.status"
