#!/usr/bin/env bash
set -euo pipefail

RUN="${1:?run root required}"

echo "TIME=$(date -Is)"
echo "RUN=$RUN"
if [[ -f "$RUN/batch.pid" ]]; then
  echo "BATCH_PID=$(tr -d '\r\n' < "$RUN/batch.pid")"
else
  echo "BATCH_PID="
fi

echo "BATCH_PROCESS"
if [[ -f "$RUN/batch.pid" ]]; then
  ps -p "$(tr -d '\r\n' < "$RUN/batch.pid")" -o pid=,stat=,etime=,args= || true
fi

echo "TCLB_PROCESSES"
ps -u "$USER" -o pid=,stat=,etime=,args= \
  | awk '$0 ~ /\/home\/yuan\/src\/TCLB\/CLB\/.*\/main( |$)/ { print }'

echo "GPU"
nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu \
  --format=csv,noheader,nounits

echo "BATCH_TAIL"
tail -n 20 "$RUN/batch_pre2025_sphere.log" 2>/dev/null || true

echo "CASE_STATUS"
while IFS= read -r d; do
  [[ -d "$d" ]] || continue
  name="${d#$RUN/}"
  rc="-"
  [[ -f "$d/run.returncode" ]] && rc="$(tr -d '\r\n' < "$d/run.returncode")"
  nf=0
  [[ -f "$d/run.numerical_failure" ]] && nf=1
  doneflag=0
  [[ -f "$d/run.done" ]] && doneflag=1
  postrc="-"
  [[ -f "$d/analysis_pre2025_sphere.returncode" ]] && postrc="$(tr -d '\r\n' < "$d/analysis_pre2025_sphere.returncode")"
  vti=0
  [[ -d "$d/output" ]] && vti="$(find "$d/output" -maxdepth 1 -name '*.vti' | wc -l)"
  last="-"
  log_csv="$(find "$d/output" -maxdepth 1 -name '*_Log_P00_*.csv' 2>/dev/null | head -n 1 || true)"
  if [[ -n "$log_csv" && -f "$log_csv" ]]; then
    last="$(tail -n 1 "$log_csv" | cut -d, -f1)"
  fi
  echo "$name rc=$rc postrc=$postrc nf=$nf done=$doneflag vti=$vti last=$last"
done < <(find "$RUN" -mindepth 1 -maxdepth 2 -type d -name 'theta???' | sort)
