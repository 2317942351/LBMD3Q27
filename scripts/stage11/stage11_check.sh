#!/bin/bash
echo "=== procs ==="
pgrep -af d3q27_pf_velocity 2>/dev/null | wc -l
echo "=== results so far ==="
cat /home/yuan/data_sda/RUNS/runs/stage11/results.txt 2>/dev/null
echo "=== per-case VTK counts ==="
for d in /home/yuan/data_sda/RUNS/runs/stage11/s1_* /home/yuan/data_sda/RUNS/runs/stage11/s2_*; do
    [ -d "$d" ] || continue
    n=$(ls "$d/output/"*.vti 2>/dev/null | wc -l)
    nan=$(grep -c NaN "$d/run.log" 2>/dev/null)
    echo "  $(basename $d): vti=$n nan=$nan"
done
