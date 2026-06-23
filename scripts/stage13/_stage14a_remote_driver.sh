#!/bin/bash
# Remote driver for Stage 14A compact-stencil rejection audit.
# Symlinks the case dirs from the existing runs into one clean root, then runs
# the audit. No simulation, no recompile, no wetting-physics change.
set -euo pipefail

BASE=/home/yuan/stage13_flat_wall_runtime_20260616
ROOT=/home/yuan/stage14a_reject_root
SCRIPT=/home/yuan/stage14a_compact_reject_audit.py

rm -rf "$ROOT"
mkdir -p "$ROOT"

link_case() {
  local src="$1" name="$2"
  if [ -d "$src" ] && [ -f "$src/case_metadata.json" ]; then
    ln -s "$src" "$ROOT/$name"
    echo "linked $name -> $src"
  else
    echo "MISSING $src"
  fi
}

# 12000-step decoupled retries (longest, most-evolved droplets)
link_case "$BASE/p100_gpu2_decoupled_12000_t30_retry_20260616/decoupled_12000/decouple_wall_60to30"   "retry12k_60to30"
link_case "$BASE/p100_gpu2_decoupled_12000_t150_retry_20260616/decoupled_12000/decouple_wall_120to150" "retry12k_120to150"

# Clean equilibrium (init=bc) and short decoupled (4000 steps)
for t in 30 90 150; do
  link_case "$BASE/p100_gpu2_clean_20260616/equilibrium_1500/diag_wall_t$t" "eq1500_t$t"
done
link_case "$BASE/p100_gpu2_clean_20260616/decoupled_4000/decouple_wall_60to30"   "dec4k_60to30"
link_case "$BASE/p100_gpu2_clean_20260616/decoupled_4000/decouple_wall_120to150" "dec4k_120to150"

echo "=== running audit ==="
python3 "$SCRIPT" "$ROOT" --out-dir /home/yuan/stage14a_reject_audit 2>&1
echo "=== exit $? ==="
echo "=== outputs ==="
ls -la /home/yuan/stage14a_reject_audit/
