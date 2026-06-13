#!/usr/bin/env bash
set -euo pipefail

# Run Stage8h CPU postprocessing as a parallel pool.
# Status: runtime_sanity / exploratory_not_validation.

source "/media/yuan/新加卷1/RUNS/scripts/tclb_runs_env.sh"

RUN_ROOT="${1:?RUN_ROOT required}"
CASE_KIND="${2:-flat}"
WORKERS="${WORKERS:-20}"
EXPECTED_COUNT="${EXPECTED_COUNT:-0}"
WATCH="${WATCH:-1}"
POLL_SECONDS="${POLL_SECONDS:-15}"
DELETE_RAW_AFTER_ANALYSIS="${DELETE_RAW_AFTER_ANALYSIS:-1}"
POSTPROCESS_SCRIPT="${POSTPROCESS_SCRIPT:-/tmp/stage8h_parallel_postprocess.py}"
FINITENESS="${FINITENESS:-/tmp/tclb_vti_finiteness_gate.py}"
CAP_POST="${CAP_POST:-/tmp/flat_wall_cap_gate_postprocess.py}"
ATTRIBUTION="${ATTRIBUTION:-/tmp/stage8h_shadow_attribution.py}"

mkdir -p "$RUN_ROOT"
log="$RUN_ROOT/stage8h_parallel_postprocess_pool.log"

args=(
  python3 "$POSTPROCESS_SCRIPT"
  --run-root "$RUN_ROOT"
  --case-kind "$CASE_KIND"
  --workers "$WORKERS"
  --finiteness "$FINITENESS"
  --cap-post "$CAP_POST"
  --attribution "$ATTRIBUTION"
  --delete-raw-after-analysis "$DELETE_RAW_AFTER_ANALYSIS"
  --poll-seconds "$POLL_SECONDS"
)
if [[ "$WATCH" != "0" ]]; then
  args+=(--watch)
fi
if [[ "$EXPECTED_COUNT" != "0" ]]; then
  args+=(--expected-count "$EXPECTED_COUNT")
fi

{
  echo "POSTPROCESS_POOL_START $(date -Is)"
  echo "status=runtime_sanity"
  echo "claim_limit=exploratory_not_validation"
  echo "run_root=$RUN_ROOT"
  echo "case_kind=$CASE_KIND"
  echo "workers=$WORKERS"
  echo "expected_count=$EXPECTED_COUNT"
  echo "delete_raw_after_analysis=$DELETE_RAW_AFTER_ANALYSIS"
  "${args[@]}"
  echo "POSTPROCESS_POOL_END $(date -Is)"
} | tee -a "$log"
