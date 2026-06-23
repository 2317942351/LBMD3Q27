#!/bin/bash
# Long base run (Coeff=0, no DynamicCL) to test whether changed-angle relaxation
# converges to target (natural slow timescale) or stalls (BC under-driven).
set -u
BIN=/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
ROOT=/mnt/usb1t/RUNS/runs/stage15D_long_base_20260620
RUNNER=/home/yuan/stage13_flat_wall_diagnostic_run.py
COMMON="--binary $BIN --dynamic-cl-mode 2 --cos-sign -1.0 --force-sign -1.0 --dynamic-cl-coeff 0 --int-width 3 --mobility 0.3 --iterations 30000 --vtk-period 5000"
export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin
export LD_LIBRARY_PATH=/usr/local/cuda-12.6/lib64:${LD_LIBRARY_PATH:-}
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh CUDA_DEVICE_ORDER=PCI_BUS_ID
python3 "$RUNNER" --matrix decoupled --root "$ROOT" $COMMON --gpu 1 --force >/dev/null 2>&1
run_one(){ ( cd "$ROOT/$1" || exit 9; export CUDA_VISIBLE_DEVICES=$2
  timeout 5400 "$BIN" case.xml > run.log 2>&1
  echo "[run] $1 rc=$? nan=$(grep -c NaN run.log)" ); }
run_one decouple_wall_60to30 1 &
P1=$!
run_one decouple_wall_120to150 2 &
P2=$!
wait $P1; wait $P2
python3 /home/yuan/golden2.py traj long_60to30 30 "$ROOT/decouple_wall_60to30" | tee "$ROOT/traj_60to30.txt"
python3 /home/yuan/golden2.py traj long_120to150 150 "$ROOT/decouple_wall_120to150" | tee "$ROOT/traj_120to150.txt"
echo "LONG_DONE" > "$ROOT/marker"
