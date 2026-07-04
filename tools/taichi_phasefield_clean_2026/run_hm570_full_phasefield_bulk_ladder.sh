#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_ROOT="${RUN_ROOT:-/mnt/usb1t/RUNS/runs/stage18_full_phasefield_bulk_ladder_20260704}"
CONDA_ENV="${CONDA_ENV:-taichi-lbm-py311}"
GPU_ID="${GPU_ID:-1}"
PYTHON_BIN="/home/yuan/miniforge3/envs/$CONDA_ENV/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing Python env: $PYTHON_BIN" >&2
  exit 2
fi

mkdir -p "$RUN_ROOT"
cp "$SCRIPT_DIR/phasefield_full_solver.py" "$RUN_ROOT/"

export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES="$GPU_ID"
export TI_DEVICE_MEMORY_GB=6

{
  date -Is
  nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader || true
  "$PYTHON_BIN" - <<'PY'
import taichi as ti
import numpy as np
print("taichi", ti.__version__)
print("numpy", np.__version__)
PY
} > "$RUN_ROOT/env.log" 2>&1

BASE_ARGS=(
  --arch cuda
  --device-memory-gb 6
  --nx 24 --ny 24 --nz 24
  --steps 1000
  --output-period 100
  --nu-l 0.1 --nu-g 0.1
  --radius 6 --width 4
  --omega-h 1.0
  --beta 0.01 --kappa 0.01
  --phase-equation-mode 2
  --phase-source-scale-mode 3
  --phase-mobility -1
  --phase-bound-mode 2
  --wetting-mode 0
  --phase-wall-mode 0
  --force-mode 0
  --force-closure-mode 1
  --force-insertion-mode 1
  --pressure-model 2
  --pressure-reference 0.3333333333333333
  --momentum-mode 1
  --momentum-density-mode 1
  --velocity-density-mode 0
  --momentum-rho-ref 1.0
  --rho-force-floor 1e-12
  --mass-tol 1e-7
  --umax-tol 0.005
)

run_case() {
  local name="$1"
  local rho_g="$2"
  mkdir -p "$RUN_ROOT/$name"
  set +e
  "$PYTHON_BIN" "$RUN_ROOT/phasefield_full_solver.py" \
    "${BASE_ARGS[@]}" \
    --rho-l 1.0 --rho-g "$rho_g" \
    --out "$RUN_ROOT/$name/output" \
    > "$RUN_ROOT/$name/run.log" 2> "$RUN_ROOT/$name/run.stderr"
  local rc=$?
  set -e
  echo "RC=$rc" > "$RUN_ROOT/$name/run.status"
}

run_case "ratio0010_bulk_1000" "0.1"
run_case "ratio0050_bulk_1000" "0.02"
run_case "ratio0200_bulk_1000" "0.005"
run_case "ratio1000_bulk_1000" "0.001"

"$PYTHON_BIN" - "$RUN_ROOT" <<'PY'
import csv
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
rows = []
for metrics_path in sorted(root.glob("ratio*_bulk_1000/output/metrics.json")):
    case_dir = metrics_path.parents[1]
    status_text = (case_dir / "run.status").read_text(encoding="utf-8").strip() if (case_dir / "run.status").exists() else "RC=?"
    data = json.loads(metrics_path.read_text(encoding="utf-8"))
    final = data["final"]
    ratio = float(data["density_ratio"])
    mass_tol = 1e-8 if ratio <= 50 else 1e-7
    umax_tol = 1e-3 if ratio <= 50 else 5e-3
    pass_gate = (
        status_text == "RC=0"
        and data["status"] == "pass"
        and final["nonfinite_count"] == 0
        and final["c_oob_low"] == 0
        and final["c_oob_high"] == 0
        and abs(final["mass_correction_delta"]) <= 1e-12
        and data["max_abs_mass_drift"] <= mass_tol
        and final["u_max"] <= umax_tol
    )
    rows.append({
        "case": case_dir.name,
        "rc": status_text,
        "solver_status": data["status"],
        "gate_status": "pass" if pass_gate else "fail",
        "density_ratio": ratio,
        "mass_drift": data["max_abs_mass_drift"],
        "mass_correction_delta": final["mass_correction_delta"],
        "c_min": final["c_min"],
        "c_max": final["c_max"],
        "u_max": final["u_max"],
        "spurious_u_rms_interface": final["spurious_u_rms_interface"],
        "laplace_delta_p": final["laplace_delta_p"],
        "laplace_delta_p_target": final["laplace_delta_p_target"],
        "laplace_delta_p_relative_error": final["laplace_delta_p_relative_error"],
        "nonfinite_count": final["nonfinite_count"],
    })

with (root / "bulk_ladder_summary.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

report = {
    "status": "pass" if all(row["gate_status"] == "pass" for row in rows) else "fail",
    "claim_limit": "bulk density ladder only; not wetting validation",
    "rows": rows,
}
(root / "bulk_ladder_summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"status": report["status"], "cases": len(rows), "run_root": str(root)}, indent=2))
PY

echo "DONE $(date -Is)" > "$RUN_ROOT/done.status"
echo "$RUN_ROOT"
