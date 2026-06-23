#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/yuan/src/TCLB_lbm2026_compile_lane}"
MODEL_SRC="${MODEL_SRC:-/home/yuan/stage17B_diffuse_solid_shadow_model}"
TARGET="${TARGET:-d3q27_pf_velocity_q27_geometric}"
CUDA_BIN="${CUDA_BIN:-/usr/local/cuda-12.6/bin}"
CUDA_LIB="${CUDA_LIB:-/usr/local/cuda-12.6/lib64}"
LOG="${LOG:-/home/yuan/stage17B_shadow_build_20260624.log}"
JOBS="${JOBS:-8}"
CLEAN_TARGET="${CLEAN_TARGET:-1}"

export PATH="${CUDA_BIN}:${PATH}"
export LD_LIBRARY_PATH="${CUDA_LIB}:${LD_LIBRARY_PATH:-}"

cd "${ROOT}"

{
  date -Is
  echo "ROOT=${PWD}"
  echo "MODEL_SRC=${MODEL_SRC}"
  echo "TARGET=${TARGET}"
  echo "NVCC=$(command -v nvcc || true)"
  test -d "${MODEL_SRC}"
  rm -rf models/multiphase/d3q27_pf_velocity
  mkdir -p models/multiphase
  cp -a "${MODEL_SRC}" models/multiphase/d3q27_pf_velocity

  if [[ "${CLEAN_TARGET}" == "1" && -d "CLB/${TARGET}" ]]; then
    backup="CLB/${TARGET}.backup_stage17B_$(date +%Y%m%d_%H%M%S)"
    echo "backup_existing_target=${backup}"
    mv "CLB/${TARGET}" "${backup}"
  fi

  echo "make_source_full"
  make "${TARGET}/source"

  echo "RT_generate_Dynamics.c_explicit"
  tools/RT -b -q \
    -f models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt \
    -I tools,src,models/multiphase/d3q27_pf_velocity \
    -w "CLB/${TARGET}/" \
    -o "CLB/${TARGET}/Dynamics.c" \
    -i options.R

  echo "make_binary"
  make -C "CLB/${TARGET}" -j "${JOBS}"
  sha256sum "CLB/${TARGET}/main"
  date -Is
} 2>&1 | tee "${LOG}"
