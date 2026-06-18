#!/bin/bash
# Stage 14C-1 mobility sweep wrapper.
# Calls the existing stage13_flat_wall_diagnostic_run.py for each M, with ALL
# dynamic layers OFF (WallGradMode=0, WallMuMode=0) so only mobility varies.
# Compact-write stays on (the healthy contact-line drive from 14A/14C-prime).
#
# 14C-1 scope (per user approval 2026-06-17): DECOUPLED ONLY, 4 M x 2 cases = 8 runs.
# Equilibrium 30/90/150 is deferred to 14C-2, run only for the chosen M.
#
# NO wetting-physics source change. Only case-parameter variation + simulation.
# Each (M, matrix) is one TCLB invocation on GPU2 (P100). GPU1 is broken; GPU0
# may be in use by another job, so GPU2 is the safe lane.
#
# Usage (on server):
#   bash stage14c_mobility_sweep.sh                  # 8 decoupled runs (default)
#   MATRIX=all bash stage14c_mobility_sweep.sh       # + equilibrium (14C-2)
#   DRY=1 bash stage14c_mobility_sweep.sh            # write case XML only, no run
set -uo pipefail

RUNNER=/home/yuan/stage13_flat_wall_diagnostic_run.py
ROOT=/home/yuan/stage14c_mobility_sweep
BIN=/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
GPU=2                 # P100 device 2 (clean)
ITERS=12000
VTK_PERIOD=2000
LOG_PERIOD=1000
MOBILITIES="0.1 0.2 0.3 0.4"
MATRICES="${MATRIX:-decoupled}"   # default 14C-1 = decoupled only

RUN_FLAG=""
if [ "${DRY:-0}" = "1" ]; then RUN_FLAG=""; else RUN_FLAG="--run"; fi

for M in $MOBILITIES; do
  for MATRIX in $MATRICES; do
    SUB="$ROOT/M${M}/${MATRIX}"
    echo "=== $(date +%H:%M:%S)  M=$M matrix=$MATRIX root=$SUB ==="
    python3 "$RUNNER" \
      --matrix "$MATRIX" \
      --root "$SUB" \
      --binary "$BIN" \
      --iterations "$ITERS" \
      --vtk-period "$VTK_PERIOD" \
      --log-period "$LOG_PERIOD" \
      --int-width 3.0 \
      --mobility "$M" \
      --compact-mode write \
      --wall-grad-mode 0 \
      --wall-mu-mode 0 \
      --wetting-bc-mode 0 \
      --gpu "$GPU" \
      --force \
      $RUN_FLAG
    echo "=== $(date +%H:%M:%S)  exit $? for M=$M matrix=$MATRIX ==="
  done
done

echo ""
echo "=== Stage 14C-1 sweep complete. Post-process with:"
echo "  python3 stage13_flat_wall_shape_angle.py <each case dir>"
echo "  python3 stage14c_prime_dilution_audit.py <root-with-cases> --steps all"
