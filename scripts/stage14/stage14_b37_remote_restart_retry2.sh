#!/usr/bin/env bash
set -euo pipefail

ROOT="/mnt/usb1t/RUNS/runs/stage14_B37_grad_phi_cap_retry2_20260628"
NOHUP="/home/yuan/stage14_B37_grad_cap_retry2_nohup.log"

echo "CURRENT_B37_PROCESSES_BEFORE"
ps -eo pid,ppid,stat,etime,cmd |
  grep -E 'stage14_s2_replay_smoke.py|d3q27_pf_velocity_q27_geometric/main case.xml|run_stage14_b37_grad_cap_remote.sh' |
  grep -v grep || true

mapfile -t pids < <(
  ps -eo pid=,cmd= |
    awk '/stage14_s2_replay_smoke.py|d3q27_pf_velocity_q27_geometric\/main case.xml|run_stage14_b37_grad_cap_remote.sh/ {print $1}'
)
if ((${#pids[@]})); then
  printf 'TERM_PIDS=%s\n' "${pids[*]}"
  kill -TERM "${pids[@]}" 2>/dev/null || true
  sleep 5
fi

mapfile -t pids < <(
  ps -eo pid=,cmd= |
    awk '/stage14_s2_replay_smoke.py|d3q27_pf_velocity_q27_geometric\/main case.xml|run_stage14_b37_grad_cap_remote.sh/ {print $1}'
)
if ((${#pids[@]})); then
  printf 'KILL_PIDS=%s\n' "${pids[*]}"
  kill -KILL "${pids[@]}" 2>/dev/null || true
  sleep 1
fi

echo "CURRENT_B37_PROCESSES_AFTER_CLEAN"
ps -eo pid,ppid,stat,etime,cmd |
  grep -E 'stage14_s2_replay_smoke.py|d3q27_pf_velocity_q27_geometric/main case.xml|run_stage14_b37_grad_cap_remote.sh' |
  grep -v grep || true

rm -rf "${ROOT}"
mkdir -p "${ROOT}"
{
  echo "reason=retry_after_confirming_B36_S0_takes_240s"
  echo "previous_default_root=/mnt/usb1t/RUNS/runs/stage14_B37_grad_phi_cap_20260628"
  date -Iseconds
} > "${ROOT}/retry_reason.txt"

env ROOT="${ROOT}" nohup bash /home/yuan/run_stage14_b37_grad_cap_remote.sh > "${NOHUP}" 2>&1 &
pid=$!
echo "B37_RETRY2_PID=${pid}"
sleep 2
tail -n 40 "${NOHUP}" || true
