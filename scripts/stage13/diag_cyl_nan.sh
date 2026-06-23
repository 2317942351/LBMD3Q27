#!/bin/bash
set -u
BIN=/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
ROOT=/mnt/usb1t/RUNS/runs/stage17_diag_nan_20260620
export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin
export LD_LIBRARY_PATH=/usr/local/cuda-12.6/lib64:${LD_LIBRARY_PATH:-}
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=1
python3 /home/yuan/gen_cyl_compact.py "$ROOT" >/dev/null 2>&1
# only t90; shorten to 2000 steps, vtk-period 250, failcheck 250
cd "$ROOT/cyl_t90"
sed -i 's/<Solve Iterations="12000">/<Solve Iterations="2000">/' case.xml
sed -i 's/<VTK Iterations="2000" what/<VTK Iterations="250" what/' case.xml
sed -i 's/<Failcheck Iterations="1000"/<Failcheck Iterations="250"/g' case.xml
timeout 600 "$BIN" case.xml > run.log 2>&1
echo "rc=$? nan=$(grep -c NaN run.log)"
echo "frames:"; ls output/*.pvti 2>/dev/null | wc -l
echo "=== ASCII PhaseF last good frame (z=center) ==="
python3 /home/yuan/diag_ascii.py output/*.pvti 2>/dev/null
echo DIAG_DONE
