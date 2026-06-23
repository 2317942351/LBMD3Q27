#!/bin/bash
# Old-BC (stage12, no compact-stencil) cylinder theta 60/90/120 -- does NOT NaN (doc 44).
# Gives a first cylinder angle result while the compact-stencil curved-NaN (doc 46) is debugged.
set -u
BIN=/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
RUNNER=/home/yuan/stage12_cap_static_run.py
ROOT=/mnt/usb1t/RUNS/runs/stage17_cyl_oldbc_20260620
export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin
export LD_LIBRARY_PATH=/usr/local/cuda-12.6/lib64:${LD_LIBRARY_PATH:-}
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh CUDA_DEVICE_ORDER=PCI_BUS_ID
run_one(){ python3 "$RUNNER" "$1" cylinder "$2" 10000 --root "$ROOT" --binary "$BIN" --mobility 0.6 --int-width 3 --timeout 2400 --force >/dev/null 2>&1
  echo "[run] $1 rc=$?"; }
run_one cyl_t60_oldbc 60 & P1=$!
run_one cyl_t90_oldbc 90 & P2=$!
wait $P1; wait $P2
run_one cyl_t120_oldbc 120
echo "=== old-BC cylinder calibrated angle (final frame) ==="
for c in cyl_t60_oldbc cyl_t90_oldbc cyl_t120_oldbc; do
  f=$(ls "$ROOT/$c/output/case_VTK_P00_"*.pvti 2>/dev/null | tail -1)
  echo -n "$c: "; python3 /home/yuan/golden_cyl.py measure "$f" 2>/dev/null | grep -o "inverted_true=[0-9.]*"
done
echo CYL_OLDBC_DONE > "$ROOT/marker"
