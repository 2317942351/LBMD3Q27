#!/usr/bin/env bash
set -euo pipefail

BIN="${BIN:-/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main}"
ROOT="${ROOT:-/mnt/usb1t/RUNS/runs/stage18_semantics_smoke_20260623}"
TEMPLATE_ROOT="${TEMPLATE_ROOT:-$ROOT/templates}"
GPU_FLAT="${GPU_FLAT:-1}"
GPU_CYL="${GPU_CYL:-2}"

export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin
export LD_LIBRARY_PATH=/usr/local/cuda-12.6/lib64:${LD_LIBRARY_PATH:-}
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh
export CUDA_DEVICE_ORDER=PCI_BUS_ID

mkdir -p "$ROOT"

prepare_case() {
  local src="$1"
  local dst="$2"
  local relout="$3"
  mkdir -p "$dst"
  cp "$src" "$dst/case.xml"
  sed -i 's/output="[^"]*"/output="output\/"/' "$dst/case.xml"
  sed -i 's/<Solve Iterations="[^"]*">/<Solve Iterations="100">/' "$dst/case.xml"
  sed -i 's/<VTK Iterations="[^"]*" what/<VTK Iterations="100" what/' "$dst/case.xml"
  sed -i 's/<Log Iterations="[^"]*"\/>/<Log Iterations="50"\/>/' "$dst/case.xml"
  sed -i 's/<Failcheck Iterations="[^"]*"\/>/<Failcheck Iterations="50"\/>/' "$dst/case.xml"
  printf '%s\n' "$relout" > "$dst/case_label.txt"
}

prepare_case "$TEMPLATE_ROOT/plane_theta090.xml" "$ROOT/plane_theta090_100" "plane_theta090_100"
prepare_case "$TEMPLATE_ROOT/cylinder_theta090.xml" "$ROOT/cylinder_theta090_old_axis_100" "cylinder_theta090_old_axis_100"
if [ -f "$TEMPLATE_ROOT/cylinder_z_axis_theta090.xml" ]; then
  prepare_case "$TEMPLATE_ROOT/cylinder_z_axis_theta090.xml" "$ROOT/cylinder_theta090_z_axis_100" "cylinder_theta090_z_axis_100"
fi

run_one() {
  local name="$1"
  local gpu="$2"
  (
    cd "$ROOT/$name"
    export CUDA_VISIBLE_DEVICES="$gpu"
    {
      echo "case=$name"
      echo "gpu=$gpu"
      echo "bin=$BIN"
      echo "start=$(date -Is)"
      nvidia-smi || true
      timeout 600 "$BIN" case.xml
      rc=$?
      echo "rc=$rc"
      echo "end=$(date -Is)"
      find output -maxdepth 2 -type f -printf '%s %p\n' 2>/dev/null | sort -nr | head -n 20
      exit "$rc"
    } > run.log 2>&1
  )
}

run_one plane_theta090_100 "$GPU_FLAT" &
PID_FLAT=$!
run_one cylinder_theta090_old_axis_100 "$GPU_CYL" &
PID_CYL=$!

echo "$PID_FLAT" > "$ROOT/plane.pid"
echo "$PID_CYL" > "$ROOT/cylinder.pid"
wait "$PID_FLAT"; RC_FLAT=$?
wait "$PID_CYL"; RC_CYL=$?
RC_CYL_Z=99
if [ -d "$ROOT/cylinder_theta090_z_axis_100" ]; then
  run_one cylinder_theta090_z_axis_100 "$GPU_CYL"; RC_CYL_Z=$?
fi

{
  echo "root=$ROOT"
  echo "plane_rc=$RC_FLAT"
  echo "cylinder_old_axis_rc=$RC_CYL"
  echo "cylinder_z_axis_rc=$RC_CYL_Z"
  echo "complete=$(date -Is)"
} > "$ROOT/status.txt"

test "$RC_FLAT" -eq 0
test "$RC_CYL_Z" -eq 0
