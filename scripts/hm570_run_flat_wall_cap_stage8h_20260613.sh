#!/usr/bin/env bash
set -euo pipefail

# Launch Stage8h flat-wall shadow diagnostics as two independent P100 queues.
# Status: runtime_sanity / exploratory_not_validation.

source "/media/yuan/新加卷1/RUNS/scripts/tclb_runs_env.sh"

RUN_ROOT="${1:-$TCLB_RUNS_ROOT/stage8/stage8h_contact_relation_and_profile_path_audit_20260613/flat}"
CASE_STAGING="${CASE_STAGING:-/tmp/flat_wall_cap_stage8h_contact_relation_cases}"
QUEUE_SCRIPT="${QUEUE_SCRIPT:-/tmp/hm570_stage8h_run_queue_20260613.sh}"
GPU_A="${GPU_A:-GPU-f650e558-d920-2fcb-0a8e-45cbc17c1ca2}"
GPU_B="${GPU_B:-GPU-2abee638-4460-b364-cd98-08cb6eaf11f7}"
DELETE_RAW_AFTER_ANALYSIS="${DELETE_RAW_AFTER_ANALYSIS:-1}"
POSTPROCESS_POOL="${POSTPROCESS_POOL:-0}"
POSTPROCESS_WORKERS="${POSTPROCESS_WORKERS:-20}"
POSTPROCESS_SCRIPT="${POSTPROCESS_SCRIPT:-/tmp/stage8h_parallel_postprocess.py}"

mkdir -p "$RUN_ROOT"
batch_log="$RUN_ROOT/batch_stage8h_flat_launcher.log"

{
  echo "LAUNCH_PREP $(date -Is)"
  echo "status=runtime_sanity"
  echo "claim_limit=exploratory_not_validation"
  echo "purpose=flat_wall_spherical_cap_stage8h_shadow"
  echo "run_root=$RUN_ROOT"
  echo "case_staging=$CASE_STAGING"
  echo "queue_script=$QUEUE_SCRIPT"
  echo "gpu_a=$GPU_A"
  echo "gpu_b=$GPU_B"
  echo "delete_raw_after_analysis=$DELETE_RAW_AFTER_ANALYSIS"
  echo "postprocess_pool=$POSTPROCESS_POOL"
  echo "postprocess_workers=$POSTPROCESS_WORKERS"
} | tee -a "$batch_log"

if [[ ! -d "$CASE_STAGING" ]]; then
  echo "MISSING_CASE_STAGING $CASE_STAGING" | tee -a "$batch_log"
  exit 3
fi
if [[ ! -f "$QUEUE_SCRIPT" ]]; then
  echo "MISSING_QUEUE_SCRIPT $QUEUE_SCRIPT" | tee -a "$batch_log"
  exit 4
fi
chmod +x "$QUEUE_SCRIPT"

mapfile -t CASE_IDS < <(find "$CASE_STAGING" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)
if [[ "${#CASE_IDS[@]}" -eq 0 ]]; then
  echo "NO_CASES $CASE_STAGING" | tee -a "$batch_log"
  exit 5
fi

queue_a="$RUN_ROOT/case_queue_a.txt"
queue_b="$RUN_ROOT/case_queue_b.txt"
: > "$queue_a"
: > "$queue_b"
for i in "${!CASE_IDS[@]}"; do
  if (( i % 2 == 0 )); then
    printf '%s\n' "${CASE_IDS[$i]}" >> "$queue_a"
  else
    printf '%s\n' "${CASE_IDS[$i]}" >> "$queue_b"
  fi
done

QUEUE_NAME=flat_a GPU_ID="$GPU_A" RUN_ROOT="$RUN_ROOT" CASE_STAGING="$CASE_STAGING" CASE_LIST="$queue_a" \
  CASE_KIND=flat DELETE_RAW_AFTER_ANALYSIS="$DELETE_RAW_AFTER_ANALYSIS" DEFER_POSTPROCESS="$POSTPROCESS_POOL" "$QUEUE_SCRIPT" &
pid_a=$!
QUEUE_NAME=flat_b GPU_ID="$GPU_B" RUN_ROOT="$RUN_ROOT" CASE_STAGING="$CASE_STAGING" CASE_LIST="$queue_b" \
  CASE_KIND=flat DELETE_RAW_AFTER_ANALYSIS="$DELETE_RAW_AFTER_ANALYSIS" DEFER_POSTPROCESS="$POSTPROCESS_POOL" "$QUEUE_SCRIPT" &
pid_b=$!

if [[ "$POSTPROCESS_POOL" != "0" ]]; then
  python3 "$POSTPROCESS_SCRIPT" --run-root "$RUN_ROOT" --case-kind flat --workers "$POSTPROCESS_WORKERS" \
    --watch --expected-count "${#CASE_IDS[@]}" --delete-raw-after-analysis "$DELETE_RAW_AFTER_ANALYSIS" \
    > "$RUN_ROOT/stage8h_parallel_postprocess_stdout.log" \
    2> "$RUN_ROOT/stage8h_parallel_postprocess_stderr.log" &
  pid_post=$!
else
  pid_post=""
fi

wait "$pid_a"
wait "$pid_b"
if [[ -n "$pid_post" ]]; then
  wait "$pid_post"
fi

echo "LAUNCH_END $(date -Is) case_count=${#CASE_IDS[@]}" | tee -a "$batch_log"
