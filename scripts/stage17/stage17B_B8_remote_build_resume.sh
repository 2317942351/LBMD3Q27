#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/yuan/src/TCLB_lbm2026_compile_lane}"
TARGET="${TARGET:-d3q27_pf_velocity_q27_geometric}"
CUDA_BIN="${CUDA_BIN:-/usr/local/cuda-12.6/bin}"
CUDA_LIB="${CUDA_LIB:-/usr/local/cuda-12.6/lib64}"
JOBS="${JOBS:-8}"

export PATH="${CUDA_BIN}:/usr/local/bin:/usr/bin:/bin:${PATH:-}"
export LD_LIBRARY_PATH="${CUDA_LIB}:${LD_LIBRARY_PATH:-}"

cd "${ROOT}"

date -Is
echo "ROOT=${PWD}"
echo "TARGET=${TARGET}"
echo "PATH=${PATH}"
echo "R=$(command -v R || true)"
echo "make=$(command -v make || true)"
echo "nvcc=$(command -v nvcc || true)"

echo "make_source_resume"
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

echo "binary_sha256"
sha256sum "CLB/${TARGET}/main"
date -Is
