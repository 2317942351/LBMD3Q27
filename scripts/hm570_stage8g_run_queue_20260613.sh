#!/usr/bin/env bash
set -euo pipefail

# Run a subset of Stage8g cases on one fixed GPU.
# Status: runtime_sanity / exploratory_not_validation.

QUEUE_NAME="${QUEUE_NAME:-queue}"
GPU_ID="${GPU_ID:?GPU_ID required}"
RUN_ROOT="${RUN_ROOT:?RUN_ROOT required}"
CASE_STAGING="${CASE_STAGING:?CASE_STAGING required}"
CASE_LIST="${CASE_LIST:?CASE_LIST required}"
CASE_KIND="${CASE_KIND:-flat}"
BINARY="${BINARY:-/home/yuan/src/TCLB_stage8g_cap_contract_revision_diag_20260613/CLB/d3q27_pf_velocity_q27_geometric/main}"
FINITENESS="${FINITENESS:-/tmp/tclb_vti_finiteness_gate.py}"
CAP_POST="${CAP_POST:-/tmp/flat_wall_cap_gate_postprocess.py}"
ATTRIBUTION="${ATTRIBUTION:-/tmp/stage8g_shadow_attribution.py}"
DELETE_RAW_AFTER_ANALYSIS="${DELETE_RAW_AFTER_ANALYSIS:-1}"

FINITE_ARRAYS="${FINITE_ARRAYS:-PhaseField,U,P,Rho,BOUNDARY,WallStage8GradMode,WallStage8ActiveWeight,WallStage8NormalGradRaw,WallStage8NormalGradTarget,WallStage8ContactResidual,WallStage8TangentGradMag,WallStage8TargetCos,WallStage8GradWriteDeltaMag,WallStage8LimiterReason,WallStage8LocalWallAngle,WallStage8FluidWallAngle,WallStage8FluidWallDataCount,WallStage8GradCandidateUse,WallStage8NormalAgreement,WallStage8UsedGeomNormal,WallStage8TanCoeffLocal,WallStage8ThetaLocal,WallStage8PhaseC,WallStage8GradMagRaw,WallStage8TangentGradRaw,WallStage8TargetNormalGrad,WallStage8NormalDeltaRaw,WallStage8NormalDeltaLimited,WallStage8VectorDeltaRawMag,WallStage8VectorDeltaLimitedMag,WallStage8NormalLimiterHit,WallStage8VectorLimiterHit,WallStage8LimiterRatio,WallStage8RegionTag,WallStage8SphereRadialDot,WallStage8ContactBandTag,WallStage8eDnRaw,WallStage8eDnTry,WallStage8eDnLimited,WallStage8eAbsCap,WallStage8eRatioCap,WallStage8eEffectiveCap,WallStage8eCapSource,WallStage8eCapDemandRatio,WallStage8eNormalRawAbs,WallStage8eTargetNormalAbs,WallStage8eTargetMinusRawAbs,WallStage8eSmoothWeightC,WallStage8eSmoothWeightG,WallStage8eSmoothWeightT,WallStage8eSmoothWeightTotal,WallStage8eTanCoeffTimesTangent,WallStage8eLimiterClass,WallStage8eWallProfileConflict,WallStage8gMode,WallStage8gScaleRawNormal,WallStage8gScaleTarget,WallStage8gScaleTangent,WallStage8gScaleFloor,WallStage8gEffectiveScale,WallStage8gTanRaw,WallStage8gTanEff,WallStage8gRegularizationRatio,WallStage8gCapSource,WallStage8gCapDemandRatio,WallStage8gProfileTargetMismatch,WallStage8gProfileConflictSign,WallStage8gWriteAllowedFlag}"

cd /home/yuan/src/TCLB_stage8g_cap_contract_revision_diag_20260613
export PATH=/usr/local/cuda-12.6/bin:$PATH
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES="$GPU_ID"
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh

mkdir -p "$RUN_ROOT"
batch_log="$RUN_ROOT/batch_stage8g_${CASE_KIND}_${QUEUE_NAME}_gpu${GPU_ID}.log"
{
  echo "QUEUE_START $(date -Is) queue=$QUEUE_NAME gpu=$GPU_ID kind=$CASE_KIND"
  echo "status=runtime_sanity"
  echo "claim_limit=exploratory_not_validation"
  echo "run_root=$RUN_ROOT"
  echo "case_staging=$CASE_STAGING"
  echo "case_list=$CASE_LIST"
  echo "binary=$BINARY"
  echo "cuda_device_order=$CUDA_DEVICE_ORDER"
  echo "cuda_visible_devices=$CUDA_VISIBLE_DEVICES"
  sha256sum "$BINARY"
} | tee -a "$batch_log"

while IFS= read -r case_id; do
  [[ -z "$case_id" ]] && continue
  src_dir="$CASE_STAGING/$case_id"
  case_dir="$RUN_ROOT/$case_id"
  lock_dir="$case_dir/.stage8g.lock"

  if [[ -f "$case_dir/run.done" ]]; then
    echo "SKIP_DONE $(date -Is) queue=$QUEUE_NAME gpu=$GPU_ID case=$case_id" | tee -a "$batch_log"
    continue
  fi
  mkdir -p "$case_dir"
  if ! mkdir "$lock_dir" 2>/dev/null; then
    echo "SKIP_LOCKED $(date -Is) queue=$QUEUE_NAME gpu=$GPU_ID case=$case_id" | tee -a "$batch_log"
    continue
  fi
  trap 'rm -rf "$lock_dir"' EXIT

  cp -f "$src_dir/case.xml" "$case_dir/case.xml"
  cp -f "$src_dir/case_params.json" "$case_dir/case_params.json"
  rm -f "$case_dir"/run.done "$case_dir"/run.numerical_failure "$case_dir"/*.returncode
  rm -rf "$case_dir"/analysis_finiteness_gate "$case_dir"/analysis_flat_cap_gate "$case_dir"/analysis_stage8g_attribution

  echo "CASE_START $(date -Is) queue=$QUEUE_NAME gpu=$GPU_ID case=$case_id" | tee -a "$batch_log"
  set +e
  "$BINARY" "$case_dir/case.xml" > "$case_dir/run.log" 2> "$case_dir/run.stderr"
  rc=$?
  set -e
  printf '%s\n' "$rc" > "$case_dir/run.returncode"
  echo "CASE_END $(date -Is) queue=$QUEUE_NAME gpu=$GPU_ID case=$case_id rc=$rc" | tee -a "$batch_log"
  if [[ "$rc" -ne 0 ]]; then
    rm -rf "$lock_dir"
    exit "$rc"
  fi

  mkdir -p "$case_dir/analysis_finiteness_gate"
  python3 "$FINITENESS" --root "$case_dir" --out-dir "$case_dir/analysis_finiteness_gate" --arrays "$FINITE_ARRAYS" \
    > "$case_dir/analysis_finiteness_gate_stdout.log" 2> "$case_dir/analysis_finiteness_gate_stderr.log"
  printf '0\n' > "$case_dir/analysis_finiteness_gate.returncode"

  if [[ "$CASE_KIND" == "flat" ]]; then
    mkdir -p "$case_dir/analysis_flat_cap_gate"
    python3 "$CAP_POST" --run-root "$RUN_ROOT" --case-root "$case_dir" --out-dir "$case_dir/analysis_flat_cap_gate" \
      > "$case_dir/analysis_flat_cap_gate_stdout.log" 2> "$case_dir/analysis_flat_cap_gate_stderr.log" || true
  fi

  mkdir -p "$case_dir/analysis_stage8g_attribution"
  python3 "$ATTRIBUTION" --case-root "$case_dir" --out-dir "$case_dir/analysis_stage8g_attribution" \
    > "$case_dir/analysis_stage8g_attribution_stdout.log" 2> "$case_dir/analysis_stage8g_attribution_stderr.log"
  printf '0\n' > "$case_dir/analysis_stage8g_attribution.returncode"

  touch "$case_dir/run.done"
  if [[ "$DELETE_RAW_AFTER_ANALYSIS" != "0" ]]; then
    deleted=$(find "$case_dir" -type f \( -name "*.vti" -o -name "*.pvti" -o -name "*.pri" -o -name "*.vtk" \) -print -delete | wc -l)
    echo "RAW_DELETE $(date -Is) queue=$QUEUE_NAME gpu=$GPU_ID case=$case_id count=$deleted" | tee -a "$batch_log"
  fi
  rm -rf "$lock_dir"
  trap - EXIT
done < "$CASE_LIST"

echo "QUEUE_END $(date -Is) queue=$QUEUE_NAME gpu=$GPU_ID kind=$CASE_KIND" | tee -a "$batch_log"
