#!/usr/bin/env bash
set -euo pipefail

# Run Stage8g z48 sphere shadow diagnostics.
# Status: runtime_sanity / exploratory_not_validation.
# Stage8OperatorMode=1 means shadow-only; no gradPhiVal write.

source "/media/yuan/新加卷1/RUNS/scripts/tclb_runs_env.sh"
RUN_ROOT="${1:-$TCLB_RUNS_ROOT/stage8/stage8g_cap_contract_revision_diag_20260613/sphere}"
LOCAL_CASE_STAGING="${LOCAL_CASE_STAGING:-/tmp/pre2025_sphere_stage8g_shadow_cases}"
BINARY="${BINARY:-/home/yuan/src/TCLB_stage8g_cap_contract_revision_diag_20260613/CLB/d3q27_pf_velocity_q27_geometric/main}"
FINITENESS="${FINITENESS:-/tmp/tclb_vti_finiteness_gate.py}"
ATTRIBUTION="${ATTRIBUTION:-/tmp/stage8g_shadow_attribution.py}"
DELETE_RAW_AFTER_ANALYSIS="${DELETE_RAW_AFTER_ANALYSIS:-1}"

FINITE_ARRAYS="${FINITE_ARRAYS:-PhaseField,U,P,Rho,WallStage8GradMode,WallStage8ActiveWeight,WallStage8NormalGradRaw,WallStage8NormalGradTarget,WallStage8ContactResidual,WallStage8TangentGradMag,WallStage8TargetCos,WallStage8GradWriteDeltaMag,WallStage8LimiterReason,WallStage8LocalWallAngle,WallStage8FluidWallAngle,WallStage8FluidWallDataCount,WallStage8GradCandidateUse,WallStage8NormalAgreement,WallStage8UsedGeomNormal,WallStage8TanCoeffLocal,WallStage8ThetaLocal,WallStage8PhaseC,WallStage8GradMagRaw,WallStage8TangentGradRaw,WallStage8TargetNormalGrad,WallStage8NormalDeltaRaw,WallStage8NormalDeltaLimited,WallStage8VectorDeltaRawMag,WallStage8VectorDeltaLimitedMag,WallStage8NormalLimiterHit,WallStage8VectorLimiterHit,WallStage8LimiterRatio,WallStage8RegionTag,WallStage8SphereRadialDot,WallStage8ContactBandTag,WallStage8eDnRaw,WallStage8eDnTry,WallStage8eDnLimited,WallStage8eAbsCap,WallStage8eRatioCap,WallStage8eEffectiveCap,WallStage8eCapSource,WallStage8eCapDemandRatio,WallStage8eNormalRawAbs,WallStage8eTargetNormalAbs,WallStage8eTargetMinusRawAbs,WallStage8eSmoothWeightC,WallStage8eSmoothWeightG,WallStage8eSmoothWeightT,WallStage8eSmoothWeightTotal,WallStage8eTanCoeffTimesTangent,WallStage8eLimiterClass,WallStage8eWallProfileConflict,WallStage8gMode,WallStage8gScaleRawNormal,WallStage8gScaleTarget,WallStage8gScaleTangent,WallStage8gScaleFloor,WallStage8gEffectiveScale,WallStage8gTanRaw,WallStage8gTanEff,WallStage8gRegularizationRatio,WallStage8gCapSource,WallStage8gCapDemandRatio,WallStage8gProfileTargetMismatch,WallStage8gProfileConflictSign,WallStage8gWriteAllowedFlag}"

cd /home/yuan/src/TCLB_stage8g_cap_contract_revision_diag_20260613
export PATH=/usr/local/cuda-12.6/bin:$PATH
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh

mkdir -p "$RUN_ROOT"
batch_log="$RUN_ROOT/batch_stage8g_sphere_shadow.log"
mapfile -t CASE_IDS < <(find "$LOCAL_CASE_STAGING" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)

{
  echo "BATCH_PREP $(date -Is)"
  echo "status=runtime_sanity"
  echo "purpose=stage8g_z48_sphere_shadow"
  echo "run_root=$RUN_ROOT"
  echo "case_staging=$LOCAL_CASE_STAGING"
  echo "binary=$BINARY"
  echo "delete_raw_after_analysis=$DELETE_RAW_AFTER_ANALYSIS"
} | tee -a "$batch_log"

if [[ ! -x "$BINARY" ]]; then echo "MISSING_BINARY $BINARY" | tee -a "$batch_log"; exit 3; fi
for helper in "$FINITENESS" "$ATTRIBUTION"; do
  if [[ ! -f "$helper" ]]; then echo "MISSING_HELPER $helper" | tee -a "$batch_log"; exit 4; fi
done

sha256sum "$BINARY" | tee "$RUN_ROOT/binary.sha256" | tee -a "$batch_log"
echo "$BINARY" > "$RUN_ROOT/binary.path"

for case_id in "${CASE_IDS[@]}"; do
  src_dir="$LOCAL_CASE_STAGING/$case_id"
  case_dir="$RUN_ROOT/$case_id"
  mkdir -p "$case_dir"
  cp -f "$src_dir/case.xml" "$case_dir/case.xml"
  cp -f "$src_dir/case_params.json" "$case_dir/case_params.json"
  rm -f "$case_dir"/run.done "$case_dir"/run.numerical_failure "$case_dir"/*.returncode
  rm -rf "$case_dir"/analysis_finiteness_gate "$case_dir"/analysis_stage8g_attribution

  echo "CASE_START $(date -Is) case=$case_id" | tee -a "$batch_log"
  set +e
  "$BINARY" "$case_dir/case.xml" > "$case_dir/run.log" 2> "$case_dir/run.stderr"
  rc=$?
  set -e
  printf '%s\n' "$rc" > "$case_dir/run.returncode"
  echo "CASE_END $(date -Is) case=$case_id rc=$rc" | tee -a "$batch_log"
  if [[ "$rc" -ne 0 ]]; then exit "$rc"; fi

  mkdir -p "$case_dir/analysis_finiteness_gate"
  python3 "$FINITENESS" --root "$case_dir" --out-dir "$case_dir/analysis_finiteness_gate" --arrays "$FINITE_ARRAYS" \
    > "$case_dir/analysis_finiteness_gate_stdout.log" 2> "$case_dir/analysis_finiteness_gate_stderr.log"
  printf '0\n' > "$case_dir/analysis_finiteness_gate.returncode"

  mkdir -p "$case_dir/analysis_stage8g_attribution"
  python3 "$ATTRIBUTION" --case-root "$case_dir" --out-dir "$case_dir/analysis_stage8g_attribution" \
    > "$case_dir/analysis_stage8g_attribution_stdout.log" 2> "$case_dir/analysis_stage8g_attribution_stderr.log"
  printf '0\n' > "$case_dir/analysis_stage8g_attribution.returncode"

  touch "$case_dir/run.done"
  if [[ "$DELETE_RAW_AFTER_ANALYSIS" != "0" ]]; then
    deleted=$(find "$case_dir" -type f \( -name "*.vti" -o -name "*.pvti" -o -name "*.pri" -o -name "*.vtk" \) -print -delete | wc -l)
    echo "RAW_DELETE $(date -Is) case=$case_id count=$deleted" | tee -a "$batch_log"
  fi
done

echo "BATCH_END $(date -Is)" | tee -a "$batch_log"
