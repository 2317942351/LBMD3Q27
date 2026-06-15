#!/bin/bash
# Run shape-angle analysis on all completed cases.
export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin
ROOT=/mnt/usb1t/RUNS/runs/stage12_validation_20260615
ANG=/home/yuan/stage12_shape_angle_analysis.py
for d in "$ROOT"/*/; do
  n=$(basename "$d")
  case "$n" in smoke_*|*_QUICK|'$c') continue ;; esac
  grep -q "RUN_RC=0" "$d/run.log" 2>/dev/null || continue
  python3 "$ANG" "$d" 2>/dev/null | grep -E '"theta_shape_end_deg"|"case"|"geometry"|"mode"'
  echo
done
echo "=== cylinder progress ==="
for n in decouple_cyl_60to30 decouple_cyl_120to150 equil_cyl_t30 equil_cyl_t150; do
  f="$ROOT/$n/run.log"
  grep -q "RUN_RC=" "$f" 2>/dev/null && echo "$n DONE" || echo "$n running"
done
