#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/yuan/src/TCLB_lbm2026_compile_lane}"
TARGET="${TARGET:-d3q27_pf_velocity_q27_geometric}"
LOG="${LOG:-/home/yuan/lbm2026_stage14_B36_force_cap_compile_20260628.log}"
CUDA_BIN="${CUDA_BIN:-/usr/local/cuda-12.6/bin}"
CUDA_LIB="${CUDA_LIB:-/usr/local/cuda-12.6/lib64}"

export PATH="${CUDA_BIN}:${PATH}"
export LD_LIBRARY_PATH="${CUDA_LIB}:${LD_LIBRARY_PATH:-}"

cd "${ROOT}"

rt_one() {
  local input="$1"
  local output="$2"
  local label="$3"
  tools/RT -b -q \
    -f "${input}" \
    -I tools,src,models/multiphase/d3q27_pf_velocity \
    -w "CLB/${TARGET}/" \
    -o "${output}" \
    -i options.R
  echo "${label}_RT_RC=0"
}

{
  date
  rt_one src/SUMMARY.Rt "CLB/${TARGET}/SUMMARY" SUMMARY
  rt_one src/Consts.h.Rt "CLB/${TARGET}/Consts.h" CONSTS_H
  rt_one src/Dynamics.h.Rt "CLB/${TARGET}/Dynamics.h" DYNAMICS_H
  rt_one models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt "CLB/${TARGET}/Dynamics.c" DYNAMICS_C
  rt_one src/Global.h.Rt "CLB/${TARGET}/Global.h" GLOBAL_H
  rt_one src/Global.cpp.Rt "CLB/${TARGET}/Global.cpp" GLOBAL_CPP
  rt_one src/Lists.cpp.Rt "CLB/${TARGET}/Lists.cpp" LISTS_CPP
  rt_one src/cuda.cu.Rt "CLB/${TARGET}/cuda.cu" CUDA
  rt_one src/Lattice.cu.Rt "CLB/${TARGET}/Lattice.cu" LATTICE_CU
  rt_one src/Lattice.h.Rt "CLB/${TARGET}/Lattice.h" LATTICE_H
  rt_one src/LatticeAccess.inc.cpp.Rt "CLB/${TARGET}/LatticeAccess.inc.cpp" LATTICE_ACCESS
  rt_one src/LatticeContainer.h.Rt "CLB/${TARGET}/LatticeContainer.h" LATTICE_CONTAINER_H
  rt_one src/LatticeContainer.inc.cpp.Rt "CLB/${TARGET}/LatticeContainer.inc.cpp" LATTICE_CONTAINER_INC
  rt_one src/Solver.cpp.Rt "CLB/${TARGET}/Solver.cpp" SOLVER_CPP
  rt_one src/Solver.h.Rt "CLB/${TARGET}/Solver.h" SOLVER_H

  grep -q "CudaConstantMemory real_t Stage14B36ForceOverRhoLimiterMode" "CLB/${TARGET}/cuda.cu"
  grep -q "CudaConstantMemory real_t Stage14B36ForceOverRhoCap" "CLB/${TARGET}/cuda.cu"
  grep -q "#define B36ForceOverRhoPreCapX" "CLB/${TARGET}/cuda.cu"
  grep -q "#define B36ForceOverRhoPostCapX" "CLB/${TARGET}/cuda.cu"
  grep -q "stage14_b36_apply_force_over_rho_limiter" "CLB/${TARGET}/Dynamics.c"
  grep -q "Stage14B36ForceOverRhoLimiterMode > 1.5" "CLB/${TARGET}/Dynamics.c"
  grep -q "CudaDeviceFunction vector_t getB36ForceOverRhoPreCap" "CLB/${TARGET}/Dynamics.c"
  grep -q "CudaDeviceFunction vector_t getB36ForceOverRhoPostCap" "CLB/${TARGET}/Dynamics.c"
  grep -q "real_t B36ForceOverRhoPreCapX" "CLB/${TARGET}/Dynamics.h"
  grep -q "real_t B36ForceOverRhoPostCapMag" "CLB/${TARGET}/Dynamics.h"
  grep -q "SETTINGS_Stage14B36ForceOverRhoLimiterMode" "CLB/${TARGET}/Consts.h"
  grep -q "SETTINGS_Stage14B36ForceOverRhoCap" "CLB/${TARGET}/Consts.h"
  grep -q '"B36ForceOverRhoPreCap"' "CLB/${TARGET}/Lists.cpp"
  grep -q '"B36ForceOverRhoPostCap"' "CLB/${TARGET}/Lists.cpp"
  grep -q "GetB36ForceOverRhoPreCap" "CLB/${TARGET}/Lattice.cu"
  grep -q "GetB36ForceOverRhoPostCap" "CLB/${TARGET}/Solver.cpp"
  grep -q "load_B36ForceOverRhoPreCapX" "CLB/${TARGET}/LatticeAccess.inc.cpp"
  grep -q "load_B36ForceOverRhoPostCapMag" "CLB/${TARGET}/LatticeAccess.inc.cpp"
  echo "CUDA_B36_FORCE_CAP_ACCESSORS_OK=1"

  find "CLB/${TARGET}" -maxdepth 1 -name '*.o' -delete
  make -C "CLB/${TARGET}" -j "${JOBS:-8}"
  echo "BUILD_RC=0"
  sha256sum "CLB/${TARGET}/main"
  date
} > "${LOG}" 2>&1
