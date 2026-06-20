#!/bin/bash
# gate-A cylinder 60/90/120 LONG run (30k, M=0.6) to test if settled angles are on target
# (before committing to option B). Uses gate-A binary (compact write flat-only, analytic ghost on curve).
set -u
BIN=/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
ROOT=/mnt/usb1t/RUNS/runs/stage17_gateA_long_20260620
export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin
export LD_LIBRARY_PATH=/usr/local/cuda-12.6/lib64:${LD_LIBRARY_PATH:-}
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh CUDA_DEVICE_ORDER=PCI_BUS_ID
python3 /home/yuan/gen_cyl_compact.py "$ROOT" >/dev/null 2>&1
for c in cyl_t60 cyl_t90 cyl_t120; do
  sed -i 's/<Solve Iterations="12000">/<Solve Iterations="30000">/' "$ROOT/$c/case.xml"
  sed -i 's/<VTK Iterations="2000" what/<VTK Iterations="5000" what/' "$ROOT/$c/case.xml"
done
run_one(){ ( cd "$ROOT/$1" || exit 9; export CUDA_VISIBLE_DEVICES=$2
  timeout 3600 "$BIN" case.xml > run.log 2>&1
  echo "[run] $1 rc=$? nan=$(grep -c 'Nan value' run.log)" ); }
run_one cyl_t60 1 & P1=$!
run_one cyl_t90 2 & P2=$!
wait $P1; wait $P2
run_one cyl_t120 1
echo "=== gate-A cylinder long-run calibrated angle (final frame) ==="
for th in 60 90 120; do
  f=$(ls "$ROOT/cyl_t$th/output/case_VTK_P00_"*.pvti 2>/dev/null | tail -1)
  echo -n "t$th target=$th: "; python3 /home/yuan/golden_cyl.py measure "$f" 2>/dev/null | grep -oE "grad_meas=[0-9.]+|inverted_true=[0-9.]+|n=[0-9]+" | tr '\n' ' '; echo
done
echo GATEA_LONG_DONE > "$ROOT/marker"
