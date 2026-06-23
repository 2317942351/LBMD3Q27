#!/usr/bin/env bash
set -u

STAMP="${1:-$(date +%Y%m%d_%H%M%S)}"
OUT_ROOT="${OUT_ROOT:-/home/yuan/lbm2026_logs/remote_space_audit_${STAMP}}"
RUN_ROOTS=(
  "/mnt/usb1t/RUNS/runs"
  "/mnt/win_sda2/RUNS/runs"
  "/home/yuan/runs"
  "/home/yuan/data_sda/RUNS/runs"
  "/home/yuan/data_sdb/RUNS/runs"
)
SOURCE_ROOTS=(
  "/home/yuan/src"
  "/home/yuan/src/TCLB"
  "/home/yuan/src/TCLB_lbm2026_compile_lane"
  "/mnt/win_sda2/RUNS/runs/stage9/src/TCLB_stage9_analytic_wetting_20260614"
)

mkdir -p "$OUT_ROOT"
exec > >(tee "$OUT_ROOT/audit_stdout.log") 2> >(tee "$OUT_ROOT/audit_stderr.log" >&2)

section() {
  printf '\n===== %s =====\n' "$1"
}

write_cmd() {
  local name="$1"
  shift
  section "$name"
  {
    printf '$'
    printf ' %q' "$@"
    printf '\n'
    "$@"
  } > "$OUT_ROOT/${name}.txt" 2>&1
  cat "$OUT_ROOT/${name}.txt"
}

write_shell() {
  local name="$1"
  local cmd="$2"
  section "$name"
  {
    printf '$ %s\n' "$cmd"
    bash -lc "$cmd"
  } > "$OUT_ROOT/${name}.txt" 2>&1
  cat "$OUT_ROOT/${name}.txt"
}

section "metadata"
{
  printf 'stamp=%s\n' "$STAMP"
  printf 'host=%s\n' "$(hostname -f 2>/dev/null || hostname)"
  printf 'user=%s\n' "$(id -un)"
  printf 'date_iso=%s\n' "$(date -Is)"
  printf 'out_root=%s\n' "$OUT_ROOT"
} | tee "$OUT_ROOT/metadata.txt"

write_cmd "uname" uname -a
write_cmd "mounts_df_hT" df -hT
write_cmd "block_devices" lsblk -o NAME,SIZE,FSTYPE,LABEL,UUID,MOUNTPOINTS
write_shell "gpu_status" "if command -v nvidia-smi >/dev/null 2>&1; then nvidia-smi; else echo nvidia-smi_not_found; fi"
write_shell "active_processes_lbm" "ps -eo pid,ppid,user,stat,etimes,pcpu,pmem,args --sort=-etimes | egrep 'CLB|main|stage1[0-9]|lbm|TCLB|python|mpirun|cuda' | head -n 120"

{
  printf 'path,type,exists,target\n'
  for path in "${RUN_ROOTS[@]}" "${SOURCE_ROOTS[@]}"; do
    if [ -L "$path" ]; then
      printf '%s,symlink,%s,%s\n' "$path" "$(test -e "$path" && echo yes || echo no)" "$(readlink -f "$path" 2>/dev/null || readlink "$path")"
    elif [ -e "$path" ]; then
      printf '%s,plain,yes,\n' "$path"
    else
      printf '%s,missing,no,\n' "$path"
    fi
  done
} | tee "$OUT_ROOT/path_status.csv"

{
  printf 'path,du_bytes,du_human\n'
  for root in "${RUN_ROOTS[@]}" "${SOURCE_ROOTS[@]}"; do
    if [ -e "$root" ]; then
      bytes=$(du -sb "$root" 2>/dev/null | awk '{print $1}')
      human=$(du -sh "$root" 2>/dev/null | awk '{print $1}')
      printf '%s,%s,%s\n' "$root" "${bytes:-NA}" "${human:-NA}"
    fi
  done
} | tee "$OUT_ROOT/top_root_usage.csv"

{
  printf 'root,path,du_human,mtime_epoch,mtime_iso\n'
  for root in "${RUN_ROOTS[@]}"; do
    [ -d "$root" ] || continue
    find "$root" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null |
      while IFS= read -r -d '' d; do
        human=$(du -sh "$d" 2>/dev/null | awk '{print $1}')
        mtime=$(stat -c '%Y' "$d" 2>/dev/null || echo 0)
        iso=$(date -d "@$mtime" -Is 2>/dev/null || echo NA)
        printf '%s,%s,%s,%s,%s\n' "$root" "$d" "${human:-NA}" "$mtime" "$iso"
      done
  done
} | tee "$OUT_ROOT/run_dir_usage.csv"

sort -t, -k4,4nr "$OUT_ROOT/run_dir_usage.csv" > "$OUT_ROOT/run_dirs_newest_first.csv" || true
sort -t, -k4,4n "$OUT_ROOT/run_dir_usage.csv" > "$OUT_ROOT/run_dirs_oldest_first.csv" || true

{
  printf 'bytes,path\n'
  for root in "${RUN_ROOTS[@]}"; do
    [ -d "$root" ] || continue
    find "$root" -type f \( -name '*.vti' -o -name '*.pvti' -o -name '*.pri' -o -name '*.vtk' -o -name '*.log' -o -name 'main' -o -name 'case.xml' -o -name '*.json' \) -printf '%s,%p\n' 2>/dev/null
  done
} | sort -t, -k1,1nr | head -n 500 | tee "$OUT_ROOT/largest_relevant_files.csv"

{
  printf 'mtime_epoch,mtime_iso,bytes,path\n'
  for root in "${RUN_ROOTS[@]}"; do
    [ -d "$root" ] || continue
    find "$root" -type f -printf '%T@,%TY-%Tm-%TdT%TH:%TM:%TS%Tz,%s,%p\n' 2>/dev/null
  done
} | sort -t, -k1,1nr | head -n 500 | tee "$OUT_ROOT/newest_files.csv"

{
  printf 'classification,path,reason\n'
  for root in "${RUN_ROOTS[@]}"; do
    [ -d "$root" ] || continue
    find "$root" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null |
      while IFS= read -r -d '' d; do
        base=$(basename "$d")
        if find "$d" -maxdepth 3 -type f \( -name 'run.log' -o -name 'case.xml' -o -name '*summary*.json' -o -name '*shape_angle*.json' \) 2>/dev/null | grep -q .; then
          printf 'KEEP,%s,has_run_or_summary_evidence\n' "$d"
        elif printf '%s' "$base" | grep -Eiq 'tmp|scratch|test|debug|nan|failed|old|rerun'; then
          printf 'DELETE_CANDIDATE,%s,name_suggests_scratch_or_failed_and_no_summary_detected\n' "$d"
        else
          printf 'ARCHIVE_CANDIDATE,%s,no_summary_detected_requires_manual_review\n' "$d"
        fi
      done
  done
} | tee "$OUT_ROOT/cleanup_manifest_candidate.csv"

{
  printf 'classification,bytes,path,reason\n'
  for root in "${RUN_ROOTS[@]}"; do
    [ -d "$root" ] || continue
    find "$root" -type f \( -name '*.vti' -o -name '*.pvti' -o -name '*.pri' \) -printf '%s,%p\n' 2>/dev/null |
      while IFS=, read -r bytes file; do
        dir=$(dirname "$file")
        parent="$dir"
        while [ "$parent" != "/" ] && [ ! -f "$parent/case.xml" ] && [ ! -f "$parent/run.log" ]; do
          next=$(dirname "$parent")
          [ "$next" = "$parent" ] && break
          parent="$next"
        done
        if find "$parent" -maxdepth 4 -type f \( -name '*summary*.json' -o -name '*shape_angle*.json' -o -name '*.png' -o -name 'run.log' -o -name 'case.xml' \) 2>/dev/null | grep -q .; then
          printf 'ARCHIVE_OR_DELETE_RAW_CANDIDATE,%s,%s,raw_field_has_neighboring_audit_artifacts_review_before_delete\n' "$bytes" "$file"
        else
          printf 'KEEP_RAW_UNSUMMARIZED,%s,%s,no_neighboring_summary_or_plot_detected\n' "$bytes" "$file"
        fi
      done
  done
} | sort -t, -k2,2nr | tee "$OUT_ROOT/raw_field_cleanup_candidates.csv"

awk -F, '$1!="classification" {sum[$1]+=$2; count[$1]++} END {print "classification,count,bytes"; for (k in sum) print k "," count[k] "," sum[k]}' \
  "$OUT_ROOT/raw_field_cleanup_candidates.csv" | tee "$OUT_ROOT/raw_field_cleanup_summary.csv"

tar -C "$(dirname "$OUT_ROOT")" -czf "${OUT_ROOT}.tar.gz" "$(basename "$OUT_ROOT")" >/dev/null 2>&1 || true
printf '\nAUDIT_OUT_ROOT=%s\n' "$OUT_ROOT" | tee "$OUT_ROOT/complete.txt"
