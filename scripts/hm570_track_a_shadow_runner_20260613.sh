#!/usr/bin/env bash
set -euo pipefail

# Run Track A shadow cases on one fixed HM570 GPU.
# Status: runtime_sanity / exploratory_not_validation.

QUEUE_NAME="${QUEUE_NAME:-track_a}"
GPU_ID="${GPU_ID:?GPU_ID required}"
RUN_ROOT="${RUN_ROOT:?RUN_ROOT required}"
CASE_LIST="${CASE_LIST:?CASE_LIST required}"
BINARY="${BINARY:-/home/yuan/src/TCLB_stage8g_cap_contract_revision_diag_20260613/CLB/d3q27_pf_velocity_q27_geometric/main}"
FINITENESS="${FINITENESS:-/tmp/tclb_vti_finiteness_gate.py}"
FLAT_POST="${FLAT_POST:-/tmp/flat_wall_cap_gate_postprocess.py}"
ATTRIBUTION="${ATTRIBUTION:-/tmp/stage8g_shadow_attribution.py}"
DELETE_RAW_AFTER_ANALYSIS="${DELETE_RAW_AFTER_ANALYSIS:-1}"

FINITE_ARRAYS="PhaseField,U,P,Rho,BOUNDARY,WallBCPath"
FINITE_ARRAYS+=",WallStage8GradMode,WallStage8ActiveWeight,WallStage8NormalGradRaw,WallStage8NormalGradTarget"
FINITE_ARRAYS+=",WallStage8ContactResidual,WallStage8TangentGradMag,WallStage8TargetCos,WallStage8GradWriteDeltaMag"
FINITE_ARRAYS+=",WallStage8LimiterReason,WallStage8LocalWallAngle,WallStage8LocalWallNormal"
FINITE_ARRAYS+=",WallStage8FluidWallAngle,WallStage8FluidWallNormal,WallStage8FluidWallDataCount"
FINITE_ARRAYS+=",WallStage8GradCandidate,WallStage8GradCandidateUse,WallStage8NormalAgreement,WallStage8UsedGeomNormal"
FINITE_ARRAYS+=",WallStage8TanCoeffLocal,WallStage8ThetaLocal,WallStage8PhaseC,WallStage8GradMagRaw"
FINITE_ARRAYS+=",WallStage8TangentGradRaw,WallStage8TargetNormalGrad,WallStage8NormalDeltaRaw,WallStage8NormalDeltaLimited"
FINITE_ARRAYS+=",WallStage8VectorDeltaRawMag,WallStage8VectorDeltaLimitedMag,WallStage8NormalLimiterHit,WallStage8VectorLimiterHit"
FINITE_ARRAYS+=",WallStage8LimiterRatio,WallStage8RegionTag,WallStage8SphereRadialDot,WallStage8ContactBandTag"
FINITE_ARRAYS+=",WallStage8eDnRaw,WallStage8eDnTry,WallStage8eDnLimited,WallStage8eAbsCap,WallStage8eRatioCap"
FINITE_ARRAYS+=",WallStage8eEffectiveCap,WallStage8eCapSource,WallStage8eCapDemandRatio,WallStage8eNormalRawAbs"
FINITE_ARRAYS+=",WallStage8eTargetNormalAbs,WallStage8eTargetMinusRawAbs,WallStage8eSmoothWeightC,WallStage8eSmoothWeightG"
FINITE_ARRAYS+=",WallStage8eSmoothWeightT,WallStage8eSmoothWeightTotal,WallStage8eTanCoeffTimesTangent"
FINITE_ARRAYS+=",WallStage8eLimiterClass,WallStage8eWallProfileConflict"
FINITE_ARRAYS+=",WallStage8gMode,WallStage8gScaleRawNormal,WallStage8gScaleTarget,WallStage8gScaleTangent"
FINITE_ARRAYS+=",WallStage8gScaleFloor,WallStage8gEffectiveScale,WallStage8gTanRaw,WallStage8gTanEff"
FINITE_ARRAYS+=",WallStage8gRegularizationRatio,WallStage8gCapSource,WallStage8gCapDemandRatio"
FINITE_ARRAYS+=",WallStage8gProfileTargetMismatch,WallStage8gProfileConflictSign,WallStage8gWriteAllowedFlag"

cd /home/yuan/src/TCLB_stage8g_cap_contract_revision_diag_20260613
export PATH=/usr/local/cuda-12.6/bin:$PATH
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES="$GPU_ID"
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh

mkdir -p "$RUN_ROOT"
batch_log="$RUN_ROOT/batch_track_a_${QUEUE_NAME}_gpu${GPU_ID}.log"
{
  echo "QUEUE_START $(date -Is) queue=$QUEUE_NAME gpu=$GPU_ID"
  echo "status=runtime_sanity"
  echo "claim_limit=exploratory_not_validation"
  echo "run_root=$RUN_ROOT"
  echo "case_list=$CASE_LIST"
  echo "binary=$BINARY"
  sha256sum "$BINARY"
} | tee -a "$batch_log"

while IFS= read -r case_id; do
  case_id="${case_id//$'\r'/}"
  [[ -z "$case_id" ]] && continue
  case_dir="$RUN_ROOT/$case_id"
  xml="$case_dir/case.xml"
  if [[ ! -f "$xml" ]]; then
    echo "CASE_MISSING_XML $(date -Is) case=$case_id" | tee -a "$batch_log"
    continue
  fi
  if [[ -f "$case_dir/run.done" ]]; then
    echo "SKIP_DONE $(date -Is) case=$case_id" | tee -a "$batch_log"
    continue
  fi
  lock_dir="$case_dir/.track_a.lock"
  if ! mkdir "$lock_dir" 2>/dev/null; then
    echo "SKIP_LOCKED $(date -Is) case=$case_id" | tee -a "$batch_log"
    continue
  fi
  trap 'rm -rf "$lock_dir"' EXIT
  rm -f "$case_dir/run.done" "$case_dir/run.numerical_failure"
  rm -rf "$case_dir/analysis_finiteness_gate" "$case_dir/analysis_flat_cap_gate" "$case_dir/analysis_stage8g_attribution"
  echo "CASE_START $(date -Is) queue=$QUEUE_NAME gpu=$GPU_ID case=$case_id" | tee -a "$batch_log"
  set +e
  "$BINARY" "$xml" > "$case_dir/run.log" 2> "$case_dir/run.stderr"
  rc=$?
  set -e
  printf '%s\n' "$rc" > "$case_dir/run.returncode"
  echo "CASE_END $(date -Is) queue=$QUEUE_NAME gpu=$GPU_ID case=$case_id rc=$rc" | tee -a "$batch_log"
  if [[ "$rc" -ne 0 ]]; then
    python3 - "$case_dir" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
rc = (p / "run.returncode").read_text().strip() if (p / "run.returncode").exists() else "unknown"
(p / "track_a_metrics.json").write_text(json.dumps({
  "status": "runtime_sanity",
  "claim_limit": "runtime_sanity / exploratory_not_validation only",
  "solver_returncode": rc,
  "postprocess_returncode": "unknown",
  "case_id": p.name,
}, indent=2), encoding="utf-8")
PY
    rm -rf "$lock_dir"
    trap - EXIT
    continue
  fi
  touch "$case_dir/run.solver_done"

  mkdir -p "$case_dir/analysis_finiteness_gate"
  set +e
  python3 "$FINITENESS" --root "$case_dir" --out-dir "$case_dir/analysis_finiteness_gate" --arrays "$FINITE_ARRAYS" \
    > "$case_dir/analysis_finiteness_gate_stdout.log" 2> "$case_dir/analysis_finiteness_gate_stderr.log"
  fin_rc=$?
  set -e
  printf '%s\n' "$fin_rc" > "$case_dir/analysis_finiteness_gate.returncode"

  if [[ "$case_id" == track_a_plane_* ]]; then
    mkdir -p "$case_dir/analysis_flat_cap_gate"
    set +e
    python3 "$FLAT_POST" --run-root "$RUN_ROOT" --case-root "$case_dir" --out-dir "$case_dir/analysis_flat_cap_gate" \
      > "$case_dir/analysis_flat_cap_gate_stdout.log" 2> "$case_dir/analysis_flat_cap_gate_stderr.log"
    flat_rc=$?
    set -e
    printf '%s\n' "$flat_rc" > "$case_dir/analysis_flat_cap_gate.returncode"
  else
    flat_rc=0
  fi

  mkdir -p "$case_dir/analysis_stage8g_attribution"
  set +e
  python3 "$ATTRIBUTION" --case-root "$case_dir" --out-dir "$case_dir/analysis_stage8g_attribution" \
    > "$case_dir/analysis_stage8g_attribution_stdout.log" 2> "$case_dir/analysis_stage8g_attribution_stderr.log"
  attr_rc=$?
  set -e
  printf '%s\n' "$attr_rc" > "$case_dir/analysis_stage8g_attribution.returncode"

python3 - "$case_dir" "$fin_rc" "$flat_rc" "$attr_rc" <<'PY'
import json, math, pathlib, sys
p = pathlib.Path(sys.argv[1])
fin_rc, flat_rc, attr_rc = sys.argv[2:5]
case_id = p.name
def finite_or_none(value):
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value
def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return finite_or_none(value)
metrics = {
    "status": "runtime_sanity",
    "claim_limit": "runtime_sanity / exploratory_not_validation only",
    "case_id": case_id,
    "solver_returncode": int((p / "run.returncode").read_text().strip()),
    "postprocess_returncode": 0 if fin_rc == "0" and flat_rc == "0" and attr_rc == "0" else 1,
}
attr = p / "analysis_stage8g_attribution" / "stage8g_shadow_attribution_summary.json"
if attr.exists():
    payload = json.loads(attr.read_text(encoding="utf-8"))
    frames = payload.get("frames", [])
    last = frames[-1] if frames else {}
    dec = payload.get("decision", {})
    lr = last.get("limiter_ratio_active", {})
    na = last.get("normal_agreement_active", {})
    pm = last.get("stage8g_profile_target_mismatch_active", {})
    fwa = last.get("stage8g_tan_eff_active", {})
    metrics.update({
        "nonfinite_total": last.get("nonfinite_total"),
        "max_mach": last.get("max_mach"),
        "normal_limiter_fraction": last.get("normal_limiter_fraction"),
        "vector_limiter_fraction": last.get("limiter_fraction"),
        "outer90_limiter_count": last.get("outer90_limiter_count"),
        "fallback_angle_limiter_count": last.get("fallback_angle_limiter_count"),
        "active_count": last.get("active_count"),
        "limiter_count": last.get("limiter_count"),
        "candidate_demand_p50": last.get("cap_demand_ratio_active", {}).get("p50"),
        "candidate_demand_p95": last.get("cap_demand_ratio_active", {}).get("p95"),
        "candidate_demand_p99": last.get("cap_demand_ratio_active", {}).get("p99"),
        "stage8_normal_agreement_p50": na.get("p50"),
        "stage8_normal_agreement_p95": na.get("p95"),
        "profile_target_mismatch_p50": pm.get("p50"),
        "profile_target_mismatch_p95": pm.get("p95"),
        "profile_target_mismatch_p99": pm.get("p99"),
        "stage8_fluid_wall_angle_p50": last.get("WallStage8FluidWallAngle_p50", None),
        "stage8_fluid_wall_angle_p95": last.get("WallStage8FluidWallAngle_p95", None),
        "limiter_ratio_p50": lr.get("p50"),
        "shadow_gate_passed_for_planning": dec.get("shadow_gate_passed_for_planning"),
    })
flat = p / "analysis_flat_cap_gate" / f"{case_id}_flat_gate_summary.json"
if flat.exists():
    payload = json.loads(flat.read_text(encoding="utf-8"))
    last = payload.get("last", {})
    metrics.update({
        "theta_fit_deg": last.get("angle_apparent_deg"),
        "theta_fit_error_deg": last.get("angle_error_vs_init_deg"),
        "fitted_apparent_contact_angle_deg": last.get("angle_apparent_deg"),
    })
(p / "track_a_metrics.json").write_text(json.dumps(clean(metrics), indent=2, allow_nan=False), encoding="utf-8")
PY

  touch "$case_dir/run.done"
  if [[ "$DELETE_RAW_AFTER_ANALYSIS" != "0" ]]; then
    deleted=$(find "$case_dir" -type f \( -name "*.vti" -o -name "*.pvti" -o -name "*.pri" -o -name "*.vtk" \) -print -delete | wc -l)
    echo "RAW_DELETE $(date -Is) queue=$QUEUE_NAME gpu=$GPU_ID case=$case_id count=$deleted" | tee -a "$batch_log"
  fi
  rm -rf "$lock_dir"
  trap - EXIT
done < "$CASE_LIST"

echo "QUEUE_END $(date -Is) queue=$QUEUE_NAME gpu=$GPU_ID" | tee -a "$batch_log"
