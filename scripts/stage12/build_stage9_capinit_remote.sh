#!/bin/bash
# Rebuild the Stage9 analytic-wetting binary after cap-initializer edits.
# Intended to run on 192.168.1.16.
set -o pipefail

export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin

SRC=/home/yuan/data_sda/RUNS/runs/stage9/src/TCLB_stage9_analytic_wetting_20260614
TARGET=d3q27_pf_velocity_q27_geometric
LOG=/home/yuan/build_stage9_capinit.log

cd "$SRC" || exit 2
rm -rf "CLB/$TARGET"

make "$TARGET" -j8 2>&1 | tee "$LOG"
rc=${PIPESTATUS[0]}
echo "BUILD_RC=$rc" | tee -a "$LOG"
if [ "$rc" -eq 0 ]; then
    sha256sum "CLB/$TARGET/main" | tee -a "$LOG"
fi
exit "$rc"
