#!/bin/bash
# Stage12 validation orchestrator: 12 cases (6 decouple + 6 equilibrium) on 3 GPUs.
#
# DECISION PROVENANCE: see docs/stage9/stage12_validation_design_20260615.md
# (to be written). Root cause of prior "perfect angle": circular verification
# (init_theta == bc_theta + 200-step + circle_intersection metric). This script
# breaks all three: (1) decouple mode sets init != bc, (2) 30k steps, (3) angle
# read from local phase gradient, not fitted-circle intersection.
#
# GPU layout: device 1 & 2 = P100 (16GB), device 0 = P4000 (8GB, used sparingly).
# 12 cases split 4/4/4 across GPUs; each case ~15-30 min at 30k steps (96^3 grid).
#
# Usage on server:
#   bash run_stage12_validation_20260615.sh           # all 12
#   bash run_stage12_validation_20260615.sh smoke      # 1 quick 100-step sanity
set -u

RUNROOT=/mnt/usb1t/RUNS/runs/stage12_validation_20260615
PY=/home/yuan/stage12_validation_run.py
ITER=${ITER:-30000}
VTKP=${VTKP:-2000}
LOGP=${LOGP:-500}
mkdir -p "$RUNROOT"

run_one() {
  # args: name geom init_theta bc_theta gpu iterations
  local name="$1" geom="$2" init_t="$3" bc_t="$4" gpu="$5" iters="$6"
  echo "[$(date +%H:%M:%S)] LAUNCH $name geom=$geom init=$init_t bc=$bc_t gpu=$gpu iters=$iters"
  python3 "$PY" "$name" "$geom" \
    --init-theta "$init_t" --bc-theta "$bc_t" \
    --iterations "$iters" --vtk-period "$VTKP" --log-period "$LOGP" \
    --gpu "$gpu" --force > "$RUNROOT/$name.launch.log" 2>&1 &
}

if [ "${1:-}" = "smoke" ]; then
  echo "=== SMOKE: 100-step sanity on GPU1 (verify XML + periodic VTK + globals) ==="
  python3 "$PY" smoke_wall_test wall --init-theta 30 --bc-theta 30 \
    --iterations 100 --vtk-period 50 --log-period 25 --gpu 1 --force
  echo "=== smoke output count ==="
  ls -la "$RUNROOT/smoke_wall_test/output/" 2>&1
  exit 0
fi

echo "=== Stage12 validation: 12 cases, 3 GPUs, $ITER steps each ==="
echo "=== starting $(date) ==="

# --- DECOUPLE SET (6): init != bc, the decisive BC-response evidence ---
# Hydrophilic side: init 60 -> bc 30. Hydrophobic side: init 120 -> bc 150.
# GPU1 takes wall decouple, GPU2 takes sphere decouple, GPU0 takes cylinder decouple.
run_one decouple_wall_60to30    wall      60  30  1  "$ITER"
run_one decouple_wall_120to150  wall     120 150  1  "$ITER"
run_one decouple_sphere_60to30  sphere    60  30  2  "$ITER"
run_one decouple_sphere_120to150 sphere  120 150  2  "$ITER"
run_one decouple_cyl_60to30     cylinder  60  30  0  "$ITER"
run_one decouple_cyl_120to150   cylinder 120 150  0  "$ITER"

# --- EQUILIBRIUM SET (6): init == bc, long run, angle from gradient ---
# Load-bearing angles 30 and 150. theta=90 is a trivial special case (excluded).
# Same GPU assignment to balance load across the 3 decouple cases still running.
run_one equil_wall_t30          wall      30  30  1  "$ITER"
run_one equil_wall_t150         wall     150 150  1  "$ITER"
run_one equil_sphere_t30        sphere    30  30  2  "$ITER"
run_one equil_sphere_t150       sphere   150 150  2  "$ITER"
run_one equil_cyl_t30           cylinder  30  30  0  "$ITER"
run_one equil_cyl_t150          cylinder 150 150  0  "$ITER"

echo "=== all 12 launched; waiting for completion ==="
wait
echo "=== all done $(date) ==="

# --- summary ---
echo "=== SUMMARY ==="
for d in "$RUNROOT"/*/; do
  name=$(basename "$d")
  rc=$(grep -oP 'RUN_RC=\K[0-9]+' "$d/run.log" 2>/dev/null || echo "?")
  nvti=$(ls "$d/output/"*.vti 2>/dev/null | wc -l)
  nan=$(grep -ci nan "$d/run.log" 2>/dev/null || echo 0)
  echo "$name rc=$rc nvti=$nvti nan_lines=$nan"
done
