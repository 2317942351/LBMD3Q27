#!/bin/bash
# Reprocess ALL completed cases with the latest (median-statistic) angle script.
# Safe to re-run. Run via: bash reprocess_all.sh
export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin
ROOT=/mnt/usb1t/RUNS/runs/stage12_validation_20260615
rm -rf "$ROOT/"'$c' 2>/dev/null  # cleanup stray literal dir if any

echo "=== reprocessing all completed cases ($(date +%H:%M:%S)) ==="
for d in "$ROOT"/*/; do
  n=$(basename "$d")
  case "$n" in
    smoke_*|*_QUICK|'$c') continue ;;
  esac
  grep -q "RUN_RC=0" "$d/run.log" 2>/dev/null || { echo "skip $n (not done/failed)"; continue; }
  echo ">>> $n"
  python3 /home/yuan/stage12_convergence_plot.py "$d" 2>&1 | grep -E '"converged"|"mass_converged"|"ke_converged"|"total_density_drift"'
  python3 /home/yuan/stage12_angle_timeseries.py "$d" 2>/dev/null | grep -E '"theta_grad_end_deg"|"theta_grad_last_few_median_deg"|"n_finite_angles"'
  echo
done
echo "=== overall progress ==="
done=0; run=0
for d in "$ROOT"/*/; do
  n=$(basename "$d")
  case "$n" in smoke_*|*_QUICK|'$c') continue ;; esac
  if grep -q "RUN_RC=0" "$d/run.log" 2>/dev/null; then done=$((done+1)); else run=$((run+1)); fi
done
echo "done=$done running=$run"
