#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/yuan/src/TCLB_lbm2026_compile_lane}"
TARGET="${TARGET:-d3q27_pf_velocity_q27_geometric}"
CUDA_BIN="${CUDA_BIN:-/usr/local/cuda-12.6/bin}"
CUDA_LIB="${CUDA_LIB:-/usr/local/cuda-12.6/lib64}"
LOG="${LOG:-/home/yuan/lbm2026_stage14_diag_full_build.log}"

export PATH="${CUDA_BIN}:${PATH}"
export LD_LIBRARY_PATH="${CUDA_LIB}:${LD_LIBRARY_PATH:-}"

cd "${ROOT}"

{
  date
  echo "ROOT=${PWD}"
  echo "TARGET=${TARGET}"
  echo "NVCC=$(command -v nvcc || true)"
  make "${TARGET}/source"
  echo "SOURCE_RC=0"
  make -C "CLB/${TARGET}" -j "${JOBS:-8}"
  echo "COMPILE_RC=0"
  sha256sum "CLB/${TARGET}/main"
  date
} 2>&1 | tee "${LOG}"
