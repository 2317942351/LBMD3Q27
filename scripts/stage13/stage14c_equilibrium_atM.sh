#!/bin/bash
# Stage 14C equilibrium-at-M runner (parameterized). Used for 14C-2b (M=0.2),
# 14C-2c (M=0.15 if needed), etc.
# Usage:  bash stage14c_equilibrium_atM.sh <M>   e.g.  bash ... 0.2
set -uo pipefail
M="${1:?usage: $0 <M>}"
RUNNER=/home/yuan/stage13_flat_wall_diagnostic_run.py
ROOT=/home/yuan/stage14c_mobility_sweep/M${M}/equilibrium
BIN=/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
GPU=2
ITERS=12000
mkdir -p "$ROOT"
echo "=== $(date +%H:%M:%S)  equilibrium 30/90/150 @ M=$M, $ITERS steps, GPU$GPU ==="
python3 "$RUNNER" \
  --matrix equilibrium \
  --root "$ROOT" \
  --binary "$BIN" \
  --iterations "$ITERS" \
  --vtk-period 2000 \
  --log-period 1000 \
  --int-width 3.0 \
  --mobility "$M" \
  --compact-mode write \
  --wall-grad-mode 0 \
  --wall-mu-mode 0 \
  --wetting-bc-mode 0 \
  --gpu "$GPU" \
  --force \
  --run
echo "=== $(date +%H:%M:%S)  exit $? ==="
