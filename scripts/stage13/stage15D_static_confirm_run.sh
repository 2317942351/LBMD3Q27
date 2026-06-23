#!/bin/bash
# Confirm the two static-map outliers (t60, t120) settle to target with more steps + higher M.
set -u
BIN=/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
ROOT=/mnt/usb1t/RUNS/runs/stage15D_static_confirm_20260620
G=/home/yuan/gen_static_map.py
export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin
export LD_LIBRARY_PATH=/usr/local/cuda-12.6/lib64:${LD_LIBRARY_PATH:-}
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh CUDA_DEVICE_ORDER=PCI_BUS_ID
# generate at M=0.6, 15k steps by patching the generator output is complex; instead
# reuse gen_static_map (M=0.3) then sed M and iterations in the two case.xmls.
mkdir -p "$ROOT"
python3 "$G" "$ROOT" >/dev/null 2>&1
for th in 60 120; do
  d="$ROOT/diag_wall_t$th"
  # keep only t60, t120 dirs
done
rm -rf "$ROOT/diag_wall_t45" "$ROOT/diag_wall_t135" "$ROOT/diag_wall_t30" "$ROOT/diag_wall_t90" "$ROOT/diag_wall_t150" 2>/dev/null
for th in 60 120; do
  d="$ROOT/diag_wall_t$th"
  sed -i 's/<Param name="M" value="[^"]*"/<Param name="M" value="0.6"/' "$d/case.xml"
  sed -i 's/<Solve Iterations="[^"]*">/<Solve Iterations="15000">/' "$d/case.xml"
  sed -i 's/<VTK Iterations="[^"]*" what/<VTK Iterations="3000" what/' "$d/case.xml"
done
run_one(){ ( cd "$ROOT/$1" || exit 9; export CUDA_VISIBLE_DEVICES=$2
  timeout 1800 "$BIN" case.xml > run.log 2>&1
  echo "[run] $1 rc=$? nan=$(grep -c NaN run.log)" ); }
run_one diag_wall_t60 1 &  P1=$!
run_one diag_wall_t120 2 & P2=$!
wait $P1; wait $P2
echo "=== confirm (M=0.6, 15k) calibrated TRUE ==="
python3 /home/yuan/golden2.py traj t60 60 "$ROOT/diag_wall_t60" 2>/dev/null | awk "NR>2{print}"
python3 /home/yuan/golden2.py traj t120 120 "$ROOT/diag_wall_t120" 2>/dev/null | awk "NR>2{print}"
echo "CONFIRM_DONE" > "$ROOT/marker"
