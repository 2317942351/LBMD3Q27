#!/bin/bash
# Remote driver for Stage 14C-prime stencil-dilution / F_surf / spurious-current audit.
# Reads EXISTING VTI only. No rerun, no recompile, no wetting-physics change.
set -uo pipefail
BASE=/home/yuan/stage13_flat_wall_runtime_20260616
ROOT=/home/yuan/stage14c_prime_root
SCRIPT=/home/yuan/stage14c_prime_dilution_audit.py

rm -rf "$ROOT"; mkdir -p "$ROOT"
link_case() {
  local src="$1" name="$2"
  if [ -d "$src" ] && [ -f "$src/case_metadata.json" ]; then
    ln -s "$src" "$ROOT/$name"; echo "linked $name"
  else echo "MISSING $src"; fi
}
# 12000-step decoupled retries + equilibrium + short decoupled
link_case "$BASE/p100_gpu2_decoupled_12000_t30_retry_20260616/decoupled_12000/decouple_wall_60to30"   "retry12k_60to30"
link_case "$BASE/p100_gpu2_decoupled_12000_t150_retry_20260616/decoupled_12000/decouple_wall_120to150" "retry12k_120to150"
for t in 30 90 150; do
  link_case "$BASE/p100_gpu2_clean_20260616/equilibrium_1500/diag_wall_t$t" "eq1500_t$t"
done
link_case "$BASE/p100_gpu2_clean_20260616/decoupled_4000/decouple_wall_60to30"   "dec4k_60to30"
link_case "$BASE/p100_gpu2_clean_20260616/decoupled_4000/decouple_wall_120to150" "dec4k_120to150"

# first pass: final timestep only (fast, the headline numbers)
echo "=== first pass: final timestep ==="
python3 "$SCRIPT" "$ROOT" --steps last --out /home/yuan/stage14c_prime_audit_last.json 2>&1
echo "=== second pass: trajectory 0/4000/8000/12000 for the two long cases ==="
python3 "$SCRIPT" "$ROOT" --steps 0,4000,8000,12000 --out /home/yuan/stage14c_prime_audit_traj.json 2>&1
echo "=== exit $? ==="
