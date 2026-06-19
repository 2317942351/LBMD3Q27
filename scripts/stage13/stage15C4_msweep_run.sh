#!/bin/bash
# C4 side (gpu2): compact-ghost baseline audit -- eq30 @ Coeff=0 (DynamicCL off), M=0.1/0.3/0.6.
set -u
BIN=/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
ROOT=/mnt/usb1t/RUNS/runs/stage15C4_Msweep_20260619
RUNNER=/home/yuan/stage13_flat_wall_diagnostic_run.py
A3=/home/yuan/analyze3.py
export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin
export LD_LIBRARY_PATH=/usr/local/cuda-12.6/lib64:${LD_LIBRARY_PATH:-}
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh CUDA_DEVICE_ORDER=PCI_BUS_ID
mkdir -p "$ROOT"
for M in 0.1 0.3 0.6; do
  TAG=$(echo "$M" | tr '.' 'p')
  R="$ROOT/M${TAG}"
  python3 "$RUNNER" --matrix equilibrium --root "$R" --binary "$BIN" \
    --dynamic-cl-mode 2 --cos-sign -1.0 --force-sign -1.0 --dynamic-cl-coeff 0 \
    --int-width 3 --mobility "$M" --iterations 4000 --vtk-period 500 --gpu 2 --force >/dev/null 2>&1
  ( cd "$R/diag_wall_t30" || exit 9; export CUDA_VISIBLE_DEVICES=2
    timeout 3000 "$BIN" case.xml > run.log 2>&1
    echo "[run] M=$M rc=$? nan=$(grep -c NaN run.log)" )
  echo "### C4 eq30 M=$M"
  python3 "$A3" "$R/diag_wall_t30" 30 0 | tee "$ROOT/c4_M${TAG}.txt"
done
echo "C4_DONE" > "$ROOT/marker"
