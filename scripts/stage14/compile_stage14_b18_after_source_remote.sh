#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/yuan/src/TCLB_lbm2026_compile_lane}"
TARGET="${TARGET:-d3q27_pf_velocity_q27_geometric}"
LOG="${LOG:-/home/yuan/lbm2026_stage14_B18_compile_20260625.log}"
CUDA_BIN="${CUDA_BIN:-/usr/local/cuda-12.6/bin}"
CUDA_LIB="${CUDA_LIB:-/usr/local/cuda-12.6/lib64}"

export PATH="${CUDA_BIN}:${PATH}"
export LD_LIBRARY_PATH="${CUDA_LIB}:${LD_LIBRARY_PATH:-}"

cd "${ROOT}"

{
  date
  tools/RT -b -q \
    -f src/SUMMARY.Rt \
    -I tools,src,models/multiphase/d3q27_pf_velocity \
    -w "CLB/${TARGET}/" \
    -o "CLB/${TARGET}/SUMMARY" \
    -i options.R
  echo "SUMMARY_RT_RC=0"
  tools/RT -b -q \
    -f src/Consts.h.Rt \
    -I tools,src,models/multiphase/d3q27_pf_velocity \
    -w "CLB/${TARGET}/" \
    -o "CLB/${TARGET}/Consts.h" \
    -i options.R
  echo "CONSTS_H_RT_RC=0"
  tools/RT -b -q \
    -f src/Dynamics.h.Rt \
    -I tools,src,models/multiphase/d3q27_pf_velocity \
    -w "CLB/${TARGET}/" \
    -o "CLB/${TARGET}/Dynamics.h" \
    -i options.R
  echo "DYNAMICS_H_RT_RC=0"
  tools/RT -b -q \
    -f models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt \
    -I tools,src,models/multiphase/d3q27_pf_velocity \
    -w "CLB/${TARGET}/" \
    -o "CLB/${TARGET}/Dynamics.c" \
    -i options.R
  echo "RT_RC=0"
  tools/RT -b -q \
    -f src/Global.h.Rt \
    -I tools,src,models/multiphase/d3q27_pf_velocity \
    -w "CLB/${TARGET}/" \
    -o "CLB/${TARGET}/Global.h" \
    -i options.R
  echo "GLOBAL_H_RT_RC=0"
  tools/RT -b -q \
    -f src/Global.cpp.Rt \
    -I tools,src,models/multiphase/d3q27_pf_velocity \
    -w "CLB/${TARGET}/" \
    -o "CLB/${TARGET}/Global.cpp" \
    -i options.R
  echo "GLOBAL_CPP_RT_RC=0"
  tools/RT -b -q \
    -f src/Lists.cpp.Rt \
    -I tools,src,models/multiphase/d3q27_pf_velocity \
    -w "CLB/${TARGET}/" \
    -o "CLB/${TARGET}/Lists.cpp" \
    -i options.R
  echo "LISTS_CPP_RT_RC=0"
  tools/RT -b -q \
    -f src/cuda.cu.Rt \
    -I tools,src,models/multiphase/d3q27_pf_velocity \
    -w "CLB/${TARGET}/" \
    -o "CLB/${TARGET}/cuda.cu" \
    -i options.R
  echo "CUDA_RT_RC=0"
  tools/RT -b -q \
    -f src/Lattice.cu.Rt \
    -I tools,src,models/multiphase/d3q27_pf_velocity \
    -w "CLB/${TARGET}/" \
    -o "CLB/${TARGET}/Lattice.cu" \
    -i options.R
  echo "LATTICE_CU_RT_RC=0"
  tools/RT -b -q \
    -f src/Lattice.h.Rt \
    -I tools,src,models/multiphase/d3q27_pf_velocity \
    -w "CLB/${TARGET}/" \
    -o "CLB/${TARGET}/Lattice.h" \
    -i options.R
  echo "LATTICE_H_RT_RC=0"
  tools/RT -b -q \
    -f src/LatticeAccess.inc.cpp.Rt \
    -I tools,src,models/multiphase/d3q27_pf_velocity \
    -w "CLB/${TARGET}/" \
    -o "CLB/${TARGET}/LatticeAccess.inc.cpp" \
    -i options.R
  echo "LATTICE_ACCESS_RT_RC=0"
  tools/RT -b -q \
    -f src/LatticeContainer.h.Rt \
    -I tools,src,models/multiphase/d3q27_pf_velocity \
    -w "CLB/${TARGET}/" \
    -o "CLB/${TARGET}/LatticeContainer.h" \
    -i options.R
  echo "LATTICE_CONTAINER_H_RT_RC=0"
  tools/RT -b -q \
    -f src/LatticeContainer.inc.cpp.Rt \
    -I tools,src,models/multiphase/d3q27_pf_velocity \
    -w "CLB/${TARGET}/" \
    -o "CLB/${TARGET}/LatticeContainer.inc.cpp" \
    -i options.R
  echo "LATTICE_CONTAINER_INC_RT_RC=0"
  tools/RT -b -q \
    -f src/Solver.cpp.Rt \
    -I tools,src,models/multiphase/d3q27_pf_velocity \
    -w "CLB/${TARGET}/" \
    -o "CLB/${TARGET}/Solver.cpp" \
    -i options.R
  echo "SOLVER_CPP_RT_RC=0"
  tools/RT -b -q \
    -f src/Solver.h.Rt \
    -I tools,src,models/multiphase/d3q27_pf_velocity \
    -w "CLB/${TARGET}/" \
    -o "CLB/${TARGET}/Solver.h" \
    -i options.R
  echo "SOLVER_H_RT_RC=0"
  grep -q "CudaConstantMemory real_t Stage14B18ClosureDiagnosticsMode" "CLB/${TARGET}/cuda.cu"
  grep -q "#define B18FmuLegacyX" "CLB/${TARGET}/cuda.cu"
  grep -q "CudaConstantMemory real_t Stage14B20HUpdateDiagnosticsMode" "CLB/${TARGET}/cuda.cu"
  grep -q "#define B20HPostActiveMaxAbs" "CLB/${TARGET}/cuda.cu"
  grep -q "CudaConstantMemory real_t Stage14B21HPopulationAuditMode" "CLB/${TARGET}/cuda.cu"
  grep -q "#define B21HPostSumMinusFormula" "CLB/${TARGET}/cuda.cu"
  grep -q "CudaConstantMemory real_t Stage14B22VelocityProducerAuditMode" "CLB/${TARGET}/cuda.cu"
  grep -q "#define B22HeqFromM0MaxAbs" "CLB/${TARGET}/cuda.cu"
  grep -q "CudaConstantMemory real_t FmuStressClosureMode" "CLB/${TARGET}/cuda.cu"
  grep -q "#define ReplayFmuStressClosureMode" "CLB/${TARGET}/cuda.cu"
  grep -q "ForceDensityClosureMode > 1.5" "CLB/${TARGET}/Dynamics.c"
  grep -q "real_t B21HPostSumMinusFormula" "CLB/${TARGET}/Dynamics.h"
  grep -q "real_t B22HeqFromM0MaxAbs" "CLB/${TARGET}/Dynamics.h"
  grep -q "real_t ReplayFmuStressClosureMode" "CLB/${TARGET}/Dynamics.h"
  grep -q "SETTINGS_Stage14B21HPopulationAuditMode" "CLB/${TARGET}/Consts.h"
  grep -q "SETTINGS_Stage14B22VelocityProducerAuditMode" "CLB/${TARGET}/Consts.h"
  grep -q "SETTINGS_FmuStressClosureMode" "CLB/${TARGET}/Consts.h"
  grep -q '"Stage14B21HPopulationAuditMode"' "CLB/${TARGET}/Lists.cpp"
  grep -q '"Stage14B22VelocityProducerAuditMode"' "CLB/${TARGET}/Lists.cpp"
  grep -q '"FmuStressClosureMode"' "CLB/${TARGET}/Lists.cpp"
  grep -q "GetB22ProbeActive" "CLB/${TARGET}/Lattice.cu"
  grep -q "GetReplayFmuStressClosureMode" "CLB/${TARGET}/Lattice.cu"
  grep -q "load_B22ProbeActive" "CLB/${TARGET}/LatticeAccess.inc.cpp"
  grep -q "load_ReplayFmuStressClosureMode" "CLB/${TARGET}/LatticeAccess.inc.cpp"
  grep -q "GetB22ProbeActive" "CLB/${TARGET}/Solver.cpp"
  grep -q "GetReplayFmuStressClosureMode" "CLB/${TARGET}/Solver.cpp"
  echo "CUDA_B18_B20_B21_B22_ACCESSORS_OK=1"
  find "CLB/${TARGET}" -maxdepth 1 -name '*.o' -delete
  make -C "CLB/${TARGET}" -j "${JOBS:-8}"
  echo "BUILD_RC=0"
  sha256sum "CLB/${TARGET}/main"
  date
} > "${LOG}" 2>&1
