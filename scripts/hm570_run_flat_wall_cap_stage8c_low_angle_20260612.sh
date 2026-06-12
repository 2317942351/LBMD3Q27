#!/usr/bin/env bash
set -euo pipefail

# Run Stage8c local wall-angle boundary-gradient low-angle flat-wall scan.
# Status: runtime_sanity / exploratory_not_validation.
# Raw VTI/PVTI/PRI stay on HM570; no archive is produced here.

RUN_ROOT="${1:-/mnt/8A0E24070E23EAC1/runs/tclb_flat_wall_cap_stage8c_low_angle_50k_light_20260612}"
LOCAL_CASE_STAGING="${LOCAL_CASE_STAGING:-/tmp/flat_wall_cap_stage8c_low_angle_50k_light_cases}"
BINARY="${BINARY:-/home/yuan/src/TCLB_stage8c_local_angle_boundary_gradient_candidate_20260612/CLB/d3q27_pf_velocity_q27_geometric/main}"
FINITENESS="${FINITENESS:-/tmp/tclb_vti_finiteness_gate.py}"
CAP_POST="${CAP_POST:-/tmp/flat_wall_cap_gate_postprocess.py}"
STOP_ON_NUMERICAL_FAILURE="${STOP_ON_NUMERICAL_FAILURE:-0}"
CAP_POST_PLOT="${CAP_POST_PLOT:-0}"

CASE_IDS=(
  cap_theta030_wall005
  cap_theta030_wall008
  cap_theta030_wall011
  cap_theta030_wall015
  cap_theta030_wall020
  cap_theta030_wall025
  cap_theta030_wall030
)
if [[ -n "${CASE_IDS_CSV:-}" ]]; then
  IFS=',' read -r -a CASE_IDS <<< "$CASE_IDS_CSV"
fi

FINITE_ARRAYS="${FINITE_ARRAYS:-PhaseField,U,P,Rho,WallStage8GradMode,WallStage8ActiveWeight,WallStage8NormalGradRaw,WallStage8NormalGradTarget,WallStage8ContactResidual,WallStage8TangentGradMag,WallStage8TargetCos,WallStage8GradWriteDeltaMag,WallStage8LimiterReason,WallStage8LocalWallAngle,WallStage8FluidWallAngle,WallStage8FluidWallDataCount,WallStage8GradCandidateUse,WallStage8NormalAgreement,WallStage8UsedGeomNormal}"

cd /home/yuan/src/TCLB_stage8c_local_angle_boundary_gradient_candidate_20260612
export PATH=/usr/local/cuda-12.6/bin:$PATH
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh

mkdir -p "$RUN_ROOT"
batch_log="$RUN_ROOT/batch_flat_wall_cap_stage8c_low_angle.log"
current_case_dir=""

mark_interrupted() {
  local rc=$?
  local sig="${1:-unknown}"
  {
    echo "BATCH_INTERRUPTED $(date -Is) signal=$sig rc=$rc current_case_dir=${current_case_dir:-none}"
    echo "status=runtime_sanity"
    echo "reason=stopped_or_interrupted"
  } | tee -a "$batch_log" >/dev/null || true
  if [[ -n "${current_case_dir:-}" && -d "$current_case_dir" ]]; then
    {
      echo "status=runtime_sanity"
      echo "reason=stopped_or_interrupted"
      echo "signal=$sig"
      echo "timestamp=$(date -Is)"
    } > "$current_case_dir/run.interrupted" || true
  fi
  exit 130
}

trap 'mark_interrupted SIGINT' INT
trap 'mark_interrupted SIGTERM' TERM

{
  echo "BATCH_PREP $(date -Is)"
  echo "status=runtime_sanity"
  echo "purpose=flat_wall_spherical_cap_gate_stage8c_low_angle"
  echo "run_root=$RUN_ROOT"
  echo "case_staging=$LOCAL_CASE_STAGING"
  echo "binary=$BINARY"
  echo "raw_policy=remote_only"
  echo "finite_arrays=$FINITE_ARRAYS"
  echo "cap_post_plot=$CAP_POST_PLOT"
} | tee -a "$batch_log"

if [[ ! -x "$BINARY" ]]; then
  echo "MISSING_BINARY $BINARY" | tee -a "$batch_log"
  exit 3
fi
for helper in "$FINITENESS" "$CAP_POST"; do
  if [[ ! -f "$helper" ]]; then
    echo "MISSING_HELPER $helper" | tee -a "$batch_log"
    exit 4
  fi
done

sha256sum "$BINARY" | tee "$RUN_ROOT/binary.sha256" | tee -a "$batch_log"
echo "$BINARY" > "$RUN_ROOT/binary.path"

for case_id in "${CASE_IDS[@]}"; do
  src_dir="$LOCAL_CASE_STAGING/$case_id"
  xml="$src_dir/case.xml"
  params="$src_dir/case_params.json"
  if [[ ! -f "$xml" || ! -f "$params" ]]; then
    echo "MISSING_CASE_INPUT $case_id xml=$xml params=$params" | tee -a "$batch_log"
    exit 5
  fi

  case_dir="$RUN_ROOT/$case_id"
  current_case_dir="$case_dir"
  mkdir -p "$case_dir"
  cp -f "$xml" "$case_dir/case.xml"
  cp -f "$params" "$case_dir/case_params.json"

  if [[ "${RESUME_SKIP_DONE:-1}" != "0" && -f "$case_dir/run.done" ]]; then
    echo "CASE_SKIP_DONE $(date -Is) case=$case_id" | tee -a "$batch_log"
    continue
  fi

  rm -f "$case_dir"/run.done "$case_dir"/run.interrupted "$case_dir"/run.numerical_failure
  rm -f "$case_dir"/*.returncode
  rm -rf "$case_dir"/analysis_finiteness_gate "$case_dir"/analysis_flat_cap_gate

  echo "CASE_START $(date -Is) case=$case_id" | tee -a "$batch_log"
  set +e
  "$BINARY" "$case_dir/case.xml" > "$case_dir/run.log" 2> "$case_dir/run.stderr"
  rc=$?
  set -e
  printf '%s\n' "$rc" > "$case_dir/run.returncode"
  echo "CASE_END $(date -Is) case=$case_id rc=$rc" | tee -a "$batch_log"

  numerical_failure=0
  if grep -Eiq '(^|[^A-Za-z])nan([^A-Za-z]|$)|(^|[^A-Za-z])inf([^A-Za-z]|$)|Stopping due to NaN|discovered NaN|NaN value|Checking .*discovered|error[[:space:]]*!' "$case_dir/run.log" "$case_dir/run.stderr"; then
    numerical_failure=1
    touch "$case_dir/run.numerical_failure"
    echo "CASE_NUMERICAL_FAILURE_TEXT $(date -Is) case=$case_id" | tee -a "$batch_log"
  fi
  if [[ "$rc" -ne 0 ]]; then
    exit "$rc"
  fi

  mkdir -p "$case_dir/analysis_finiteness_gate"
  set +e
  python3 "$FINITENESS" \
    --root "$case_dir" \
    --out-dir "$case_dir/analysis_finiteness_gate" \
    --arrays "$FINITE_ARRAYS" \
    > "$case_dir/analysis_finiteness_gate_stdout.log" \
    2> "$case_dir/analysis_finiteness_gate_stderr.log"
  finite_rc=$?
  set -e
  printf '%s\n' "$finite_rc" > "$case_dir/analysis_finiteness_gate.returncode"
  echo "FINITENESS_END $(date -Is) case=$case_id rc=$finite_rc" | tee -a "$batch_log"

  mkdir -p "$case_dir/analysis_flat_cap_gate"
  cap_post_args=(
    --run-root "$RUN_ROOT"
    --case-root "$case_dir"
    --out-dir "$case_dir/analysis_flat_cap_gate"
  )
  if [[ "$CAP_POST_PLOT" != "0" ]]; then
    cap_post_args+=(--plot)
  fi
  set +e
  python3 "$CAP_POST" "${cap_post_args[@]}" \
    > "$case_dir/analysis_flat_cap_gate_stdout.log" \
    2> "$case_dir/analysis_flat_cap_gate_stderr.log"
  post_rc=$?
  set -e
  printf '%s\n' "$post_rc" > "$case_dir/analysis_flat_cap_gate.returncode"
  echo "CAP_POST_END $(date -Is) case=$case_id rc=$post_rc" | tee -a "$batch_log"

  if [[ "$numerical_failure" -eq 1 || "$finite_rc" -ne 0 || "$post_rc" -ne 0 ]]; then
    echo "CASE_FAILED_NEGATIVE_EVIDENCE $(date -Is) case=$case_id numerical_failure=$numerical_failure finite_rc=$finite_rc post_rc=$post_rc" | tee -a "$batch_log"
    if [[ "$STOP_ON_NUMERICAL_FAILURE" != "0" ]]; then
      exit 6
    fi
  else
    touch "$case_dir/run.done"
  fi
done

mkdir -p "$RUN_ROOT/analysis_flat_cap_gate_combined"
combined_post_args=(
  --run-root "$RUN_ROOT"
  --out-dir "$RUN_ROOT/analysis_flat_cap_gate_combined"
)
if [[ "$CAP_POST_PLOT" != "0" ]]; then
  combined_post_args+=(--plot)
fi
python3 "$CAP_POST" "${combined_post_args[@]}" \
  > "$RUN_ROOT/analysis_flat_cap_gate_combined_stdout.log" \
  2> "$RUN_ROOT/analysis_flat_cap_gate_combined_stderr.log" || true

current_case_dir=""
echo "BATCH_END $(date -Is)" | tee -a "$batch_log"
