#!/bin/bash
set -u
BIN=/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
ROOT=/mnt/usb1t/RUNS/runs/stage17_cyl_compact_20260620
export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin
export LD_LIBRARY_PATH=/usr/local/cuda-12.6/lib64:${LD_LIBRARY_PATH:-}
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh CUDA_DEVICE_ORDER=PCI_BUS_ID
python3 /home/yuan/gen_cyl_compact.py "$ROOT"
run_one(){ ( cd "$ROOT/$1" || exit 9; export CUDA_VISIBLE_DEVICES=$2
  timeout 2400 "$BIN" case.xml > run.log 2>&1
  echo "[run] $1 rc=$? nan=$(grep -c NaN run.log)" ); }
run_one cyl_t60 1 & P1=$!
run_one cyl_t90 2 & P2=$!
wait $P1; wait $P2
run_one cyl_t120 1
echo "=== cylinder compact-stencil calibrated angle (final frame) ==="
for th in 60 90 120; do
  f=$(ls "$ROOT/cyl_t$th/output/case_VTK_P00_"*.pvti 2>/dev/null | tail -1)
  echo -n "t$th target=$th: "; python3 /home/yuan/golden_cyl.py measure "$f" 2>/dev/null
done
echo CYL17_DONE > "$ROOT/marker"
