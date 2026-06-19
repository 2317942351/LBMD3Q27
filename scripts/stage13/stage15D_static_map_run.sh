#!/bin/bash
# Static target-angle map: 45/60/120/135 (init=target, Coeff=0, M=0.3, 4000 steps).
# Confirms compact-ghost static BC correct across the full range (30/90/150 done in doc 40).
set -u
BIN=/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
ROOT=/mnt/usb1t/RUNS/runs/stage15D_static_map_20260620
G=/home/yuan/gen_static_map.py
export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin
export LD_LIBRARY_PATH=/usr/local/cuda-12.6/lib64:${LD_LIBRARY_PATH:-}
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh CUDA_DEVICE_ORDER=PCI_BUS_ID
mkdir -p "$ROOT"
python3 "$G" "$ROOT"
run_one(){ ( cd "$ROOT/$1" || exit 9; export CUDA_VISIBLE_DEVICES=$2
  timeout 1200 "$BIN" case.xml > run.log 2>&1
  echo "[run] $1 rc=$? nan=$(grep -c NaN run.log)" ); }
# 4 cases, 2 GPUs, 2 waves
run_one diag_wall_t45 1 &  P1=$!
run_one diag_wall_t120 2 & P2=$!
wait $P1; wait $P2
run_one diag_wall_t60 1 &  P3=$!
run_one diag_wall_t135 2 & P4=$!
wait $P3; wait $P4
echo "=== static-angle map (calibrated TRUE @4000) ==="
for th in 45 60 120 135; do
  python3 /home/yuan/golden2.py traj static_t$th $th "$ROOT/diag_wall_t$th" 2>/dev/null | tail -1
done
echo "STATIC_MAP_DONE" > "$ROOT/marker"
