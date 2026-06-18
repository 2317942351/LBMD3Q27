#!/bin/bash
# Stage 14C-2: equilibrium 30/90/150 at the chosen working mobility M=0.3.
# Verifies the static contact angle is preserved when M is raised from 0.1.
# All dynamic layers OFF, compact-write ON. Only case-parameter variation.
#
# Gate (per user 2026-06-18):
#   |theta_measured - theta_target| < 0.5 deg
#   mass drift < 1%
#   RMS_end <= 2x the M0.1 equilibrium RMS
#   nonfinite_phase_count == 0, no NaN
set -uo pipefail

RUNNER=/home/yuan/stage13_flat_wall_diagnostic_run.py
ROOT=/home/yuan/stage14c_mobility_sweep/M0.3/equilibrium
BIN=/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
GPU=2
M=0.3
ITERS=12000

mkdir -p "$ROOT"
echo "=== $(date +%H:%M:%S)  14C-2: equilibrium 30/90/150 @ M=$M, $ITERS steps, GPU$GPU ==="
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
