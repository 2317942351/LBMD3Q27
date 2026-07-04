#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/yuan/src/TCLB_lbm2026_compile_lane}"
MODEL_SRC="${MODEL_SRC:-/home/yuan/stage18_clean_phasefield_model/models/multiphase/d3q27_pf_velocity_clean_2026}"
TARGET="${TARGET:-d3q27_pf_velocity_clean_2026_q27_stage18split}"
LOG="${LOG:-/home/yuan/lbm2026_stage18_clean_split_mrt_compile_20260703.log}"
CUDA_BIN="${CUDA_BIN:-/usr/local/cuda-12.6/bin}"
CUDA_LIB="${CUDA_LIB:-/usr/local/cuda-12.6/lib64}"
JOBS="${JOBS:-8}"
SKELETON="${SKELETON:-/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric_b115runpersist}"

export PATH="${CUDA_BIN}:${PATH}"
export LD_LIBRARY_PATH="${CUDA_LIB}:${LD_LIBRARY_PATH:-}"

cd "${ROOT}"
if [[ "${SKIP_RT:-0}" != "1" ]]; then
  rm -rf models/multiphase/d3q27_pf_velocity
  mkdir -p models/multiphase
  cp -a "${MODEL_SRC}" models/multiphase/d3q27_pf_velocity
  sed -i '1s/^\xEF\xBB\xBF//' models/multiphase/d3q27_pf_velocity/Dynamics.R
  sed -i '1s/^\xEF\xBB\xBF//' models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt

  rm -rf "CLB/${TARGET}"
  mkdir -p "CLB/${TARGET}"
  cat > "CLB/${TARGET}/options.R" <<'EOF'
X_MOD = 0
CPU_LAYOUT = FALSE
MODEL="d3q27_pf_velocity_clean_2026"
Options=list(
  q27 = TRUE,
  OutFlow = FALSE,
  BGK = FALSE,
  thermo = FALSE,
  planarBenchmark = FALSE,
  autosym = 0,
  geometric = FALSE,
  staircaseimp = FALSE,
  isograd = FALSE,
  tprec = FALSE
)
EOF
fi

RT_OPTIONS="${PWD}/CLB/${TARGET}/options.R"
export RT_OPTIONS

rt_one() {
  local input="$1"
  local output="$2"
  local label="$3"
  tools/RT -b -q \
    -f "${input}" \
    -I tools,src,models/multiphase/d3q27_pf_velocity \
    -w "CLB/${TARGET}/" \
    -o "${output}" \
    -i "${RT_OPTIONS}"
  echo "${label}_RT_RC=0"
}

if [[ "${SKIP_RT:-0}" != "1" ]]; then
  {
    date -Is
    echo "ROOT=${PWD}"
    echo "MODEL_SRC=${MODEL_SRC}"
    echo "TARGET=${TARGET}"
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
    rt_one src/LatticeAccess.inc.cpp.Rt "CLB/${TARGET}/LatticeAccess.inc.cpp" LATTICE_ACCESS_INC
    rt_one src/LatticeContainer.h.Rt "CLB/${TARGET}/LatticeContainer.h" LATTICE_CONTAINER_H
    rt_one src/LatticeContainer.inc.cpp.Rt "CLB/${TARGET}/LatticeContainer.inc.cpp" LATTICE_CONTAINER_INC
    rt_one src/Solver.cpp.Rt "CLB/${TARGET}/Solver.cpp" SOLVER_CPP
    rt_one src/Solver.h.Rt "CLB/${TARGET}/Solver.h" SOLVER_H
    grep -q "Stage18_MomentumCollision" "CLB/${TARGET}/Dynamics.c"
    grep -q "Stage18_PhaseCollision" "CLB/${TARGET}/Dynamics.c"
    grep -q "stage18_phase_tmp1" "CLB/${TARGET}/Dynamics.c"
    grep -q "SETTINGS_MomentumMRTMode" "CLB/${TARGET}/Consts.h"
    grep -q "SETTINGS_MRTShearOmegaOverride" "CLB/${TARGET}/Consts.h"
    grep -q "SETTINGS_PhaseEquationMode" "CLB/${TARGET}/Consts.h"
    echo "STAGE18_SPLIT_SOURCE_AUDIT_OK=1"
  } > "${LOG}" 2>&1
else
  echo "$(date -Is) SKIP_RT=1 reuse generated source for ${TARGET}" >> "${LOG}"
fi

if [[ ! -f "CLB/${TARGET}/makefile" && -d "${SKELETON}" ]]; then
  tmp="$(mktemp -d)"
  cp -a "CLB/${TARGET}"/Consts.h "CLB/${TARGET}"/Dynamics.h "CLB/${TARGET}"/Dynamics.c \
    "CLB/${TARGET}"/Global.h "CLB/${TARGET}"/Global.cpp "CLB/${TARGET}"/Lists.cpp \
    "CLB/${TARGET}"/cuda.cu "CLB/${TARGET}"/Lattice.cu "CLB/${TARGET}"/Lattice.h \
    "CLB/${TARGET}"/LatticeAccess.inc.cpp "CLB/${TARGET}"/LatticeContainer.h \
    "CLB/${TARGET}"/LatticeContainer.inc.cpp "CLB/${TARGET}"/Solver.cpp \
    "CLB/${TARGET}"/Solver.h "CLB/${TARGET}"/SUMMARY "CLB/${TARGET}"/options.R "${tmp}/"
  rsync -a --delete "${SKELETON}/" "CLB/${TARGET}/"
  cp -a "${tmp}/"* "CLB/${TARGET}/"
  sed -i "s/MODEL=.*/MODEL=${TARGET}/" "CLB/${TARGET}/makefile"
  rm -rf "${tmp}"
fi

find "CLB/${TARGET}" -maxdepth 1 -name '*.o' -delete
rm -f "CLB/${TARGET}/main"
{
  date -Is
  make -C "CLB/${TARGET}" -f makefile -j "${JOBS}"
  echo "BUILD_RC=0"
  sha256sum "CLB/${TARGET}/main"
  date -Is
} >> "${LOG}" 2>&1
