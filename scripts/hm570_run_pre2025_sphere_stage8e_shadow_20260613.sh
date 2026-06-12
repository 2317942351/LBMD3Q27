#!/usr/bin/env bash
set -euo pipefail

# Run Stage8e z48 sphere shadow and initializer-attribution diagnostics.
# Status: runtime_sanity / exploratory_not_validation.
# Stage8OperatorMode=1 means shadow-only; no gradPhiVal write.

RUN_ROOT="${1:-/mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_stage8e_shadow_20260613}"
LOCAL_CASE_STAGING="${LOCAL_CASE_STAGING:-/tmp/pre2025_sphere_stage8e_shadow_cases}"
BINARY="${BINARY:-/home/yuan/src/TCLB_stage8e_normal_residual_only_wetting_candidate_20260613/CLB/d3q27_pf_velocity_q27_geometric/main}"
FINITENESS="${FINITENESS:-/tmp/tclb_vti_finiteness_gate.py}"
ATTRIBUTION="${ATTRIBUTION:-/tmp/pre2025_sphere_stage8e_normal_residual_attribution.py}"
CASE_IDS=(theta030_free_sphere_shadow theta030_cap_on_sphere_shadow)
if [[ -n "${CASE_IDS_CSV:-}" ]]; then
  IFS=',' read -r -a CASE_IDS <<< "$CASE_IDS_CSV"
fi
FINITE_ARRAYS="${FINITE_ARRAYS:-PhaseField,U,P,Rho,WallStage8GradMode,WallStage8ActiveWeight,WallStage8NormalGradRaw,WallStage8NormalGradTarget,WallStage8ContactResidual,WallStage8TangentGradMag,WallStage8TargetCos,WallStage8GradWriteDeltaMag,WallStage8LimiterReason,WallStage8LocalWallAngle,WallStage8FluidWallAngle,WallStage8FluidWallDataCount,WallStage8GradCandidateUse,WallStage8NormalAgreement,WallStage8UsedGeomNormal,WallStage8TanCoeffLocal,WallStage8ThetaLocal,WallStage8PhaseC,WallStage8GradMagRaw,WallStage8TangentGradRaw,WallStage8TargetNormalGrad,WallStage8NormalDeltaRaw,WallStage8NormalDeltaLimited,WallStage8VectorDeltaRawMag,WallStage8VectorDeltaLimitedMag,WallStage8NormalLimiterHit,WallStage8VectorLimiterHit,WallStage8LimiterRatio,WallStage8RegionTag,WallStage8SphereRadialDot,WallStage8ContactBandTag}"

cd /home/yuan/src/TCLB_stage8e_normal_residual_only_wetting_candidate_20260613
export PATH=/usr/local/cuda-12.6/bin:$PATH
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh

mkdir -p "$RUN_ROOT"
batch_log="$RUN_ROOT/batch_stage8e_sphere_shadow.log"

{
  echo "BATCH_PREP $(date -Is)"
  echo "status=runtime_sanity"
  echo "purpose=stage8e_z48_sphere_shadow_normal_residual"
  echo "run_root=$RUN_ROOT"
  echo "case_staging=$LOCAL_CASE_STAGING"
  echo "binary=$BINARY"
  echo "raw_policy=remote_only"
  echo "finite_arrays=$FINITE_ARRAYS"
} | tee -a "$batch_log"

if [[ ! -x "$BINARY" ]]; then
  echo "MISSING_BINARY $BINARY" | tee -a "$batch_log"
  exit 3
fi
for helper in "$FINITENESS" "$ATTRIBUTION"; do
  if [[ ! -f "$helper" ]]; then
    echo "MISSING_HELPER $helper" | tee -a "$batch_log"
    exit 4
  fi
done

echo "$BINARY" > "$RUN_ROOT/binary.path"
sha256sum "$BINARY" | tee "$RUN_ROOT/binary.sha256" | tee -a "$batch_log"

for case_id in "${CASE_IDS[@]}"; do
  src_dir="$LOCAL_CASE_STAGING/$case_id"
  xml="$src_dir/case.xml"
  params="$src_dir/case_params.json"
  if [[ ! -f "$xml" || ! -f "$params" ]]; then
    echo "MISSING_CASE_INPUT case=$case_id xml=$xml params=$params" | tee -a "$batch_log"
    exit 5
  fi

  case_dir="$RUN_ROOT/$case_id"
  mkdir -p "$case_dir"
  cp -f "$xml" "$case_dir/case.xml"
  cp -f "$params" "$case_dir/case_params.json"
  rm -f "$case_dir"/run.done "$case_dir"/run.numerical_failure "$case_dir"/*.returncode
  rm -rf "$case_dir"/analysis_finiteness_gate "$case_dir"/analysis_stage8e_normal_residual_attribution

  echo "CASE_START $(date -Is) case=$case_id" | tee -a "$batch_log"
  set +e
  "$BINARY" "$case_dir/case.xml" > "$case_dir/run.log" 2> "$case_dir/run.stderr"
  rc=$?
  set -e
  printf '%s\n' "$rc" > "$case_dir/run.returncode"
  echo "CASE_END $(date -Is) case=$case_id rc=$rc" | tee -a "$batch_log"

  if grep -Eiq '(^|[^A-Za-z])nan([^A-Za-z]|$)|(^|[^A-Za-z])inf([^A-Za-z]|$)|Stopping due to NaN|discovered NaN|NaN value|Checking .*discovered|error[[:space:]]*!' "$case_dir/run.log" "$case_dir/run.stderr"; then
    touch "$case_dir/run.numerical_failure"
    echo "CASE_NUMERICAL_FAILURE_TEXT $(date -Is) case=$case_id" | tee -a "$batch_log"
    exit 6
  fi
  if [[ "$rc" -ne 0 ]]; then
    exit "$rc"
  fi

  mkdir -p "$case_dir/analysis_finiteness_gate"
  set +e
  python3 "$FINITENESS" --root "$case_dir" --out-dir "$case_dir/analysis_finiteness_gate" --arrays "$FINITE_ARRAYS" \
    > "$case_dir/analysis_finiteness_gate_stdout.log" \
    2> "$case_dir/analysis_finiteness_gate_stderr.log"
  finite_rc=$?
  set -e
  printf '%s\n' "$finite_rc" > "$case_dir/analysis_finiteness_gate.returncode"
  echo "FINITENESS_END $(date -Is) case=$case_id rc=$finite_rc" | tee -a "$batch_log"
  if [[ "$finite_rc" -ne 0 ]]; then
    exit "$finite_rc"
  fi

  mkdir -p "$case_dir/analysis_stage8e_normal_residual_attribution"
  set +e
  python3 "$ATTRIBUTION" --case-root "$case_dir" --out-dir "$case_dir/analysis_stage8e_normal_residual_attribution" \
    > "$case_dir/analysis_stage8e_normal_residual_attribution_stdout.log" \
    2> "$case_dir/analysis_stage8e_normal_residual_attribution_stderr.log"
  attr_rc=$?
  set -e
  printf '%s\n' "$attr_rc" > "$case_dir/analysis_stage8e_normal_residual_attribution.returncode"
  echo "ATTRIBUTION_END $(date -Is) case=$case_id rc=$attr_rc" | tee -a "$batch_log"
  if [[ "$attr_rc" -ne 0 ]]; then
    exit "$attr_rc"
  fi

  touch "$case_dir/run.done"
done

echo "BATCH_END $(date -Is)" | tee -a "$batch_log"
