#!/usr/bin/env bash
set -euo pipefail

# Run flat-wall spherical-cap gate cases with the v4 CapInit diagnostic lane.
# Status: runtime_sanity / exploratory_not_validation.
# Raw VTI/PVTI stay on HM570; curated tar excludes raw VTI/PVTI/PRI.

RUN_ROOT="${1:-/mnt/8A0E24070E23EAC1/runs/tclb_flat_wall_cap_v4capdiag_gate_20260611}"
LOCAL_CASE_STAGING="${LOCAL_CASE_STAGING:-/tmp/flat_wall_cap_v4capdiag_gate_cases}"
BINARY="${BINARY:-/home/yuan/src/TCLB_clean_wall_signed_profile_v4capdiag_20260611/CLB/d3q27_pf_velocity_q27_geometric/main}"
FINITENESS="${FINITENESS:-/tmp/tclb_vti_finiteness_gate.py}"
CAP_POST="${CAP_POST:-/tmp/flat_wall_cap_gate_postprocess.py}"

CASE_IDS=(
  cap_theta030_wall030
  cap_theta090_wall090
  cap_theta150_wall150
  cap_theta030_wall011
)

cd /home/yuan/src/TCLB
export PATH=/usr/local/cuda-12.6/bin:$PATH
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh

mkdir -p "$RUN_ROOT"
batch_log="$RUN_ROOT/batch_flat_wall_cap_v4capdiag_gate.log"
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
  echo "purpose=flat_wall_spherical_cap_gate_v4capdiag"
  echo "run_root=$RUN_ROOT"
  echo "case_staging=$LOCAL_CASE_STAGING"
  echo "binary=$BINARY"
  echo "raw_policy=remote_only"
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
  python3 "$FINITENESS" \
    --root "$case_dir" \
    --out-dir "$case_dir/analysis_finiteness_gate" \
    --arrays PhaseField,U,P,Rho,WallPhasePred,WallPhaseProfilePred,WallPhaseSignedProfilePred \
    > "$case_dir/analysis_finiteness_gate_stdout.log" \
    2> "$case_dir/analysis_finiteness_gate_stderr.log"
  finite_rc=$?
  set -e
  printf '%s\n' "$finite_rc" > "$case_dir/analysis_finiteness_gate.returncode"
  echo "FINITENESS_END $(date -Is) case=$case_id rc=$finite_rc" | tee -a "$batch_log"
  if [[ "$finite_rc" -ne 0 ]]; then
    exit "$finite_rc"
  fi

  mkdir -p "$case_dir/analysis_flat_cap_gate"
  set +e
  python3 "$CAP_POST" \
    --run-root "$RUN_ROOT" \
    --case-root "$case_dir" \
    --out-dir "$case_dir/analysis_flat_cap_gate" \
    --plot \
    > "$case_dir/analysis_flat_cap_gate_stdout.log" \
    2> "$case_dir/analysis_flat_cap_gate_stderr.log"
  post_rc=$?
  set -e
  printf '%s\n' "$post_rc" > "$case_dir/analysis_flat_cap_gate.returncode"
  echo "CAP_POST_END $(date -Is) case=$case_id rc=$post_rc" | tee -a "$batch_log"
  if [[ "$post_rc" -ne 0 ]]; then
    exit "$post_rc"
  fi

  touch "$case_dir/run.done"
done

mkdir -p "$RUN_ROOT/analysis_flat_cap_gate_combined"
python3 "$CAP_POST" \
  --run-root "$RUN_ROOT" \
  --out-dir "$RUN_ROOT/analysis_flat_cap_gate_combined" \
  --plot \
  > "$RUN_ROOT/analysis_flat_cap_gate_combined_stdout.log" \
  2> "$RUN_ROOT/analysis_flat_cap_gate_combined_stderr.log"

tar -czf "$RUN_ROOT/curated_flat_wall_cap_v4capdiag_gate.tar.gz" \
  --exclude='*.vti' --exclude='*.pvti' --exclude='*.pri' \
  -C "$RUN_ROOT" .

current_case_dir=""
echo "BATCH_END $(date -Is)" | tee -a "$batch_log"
