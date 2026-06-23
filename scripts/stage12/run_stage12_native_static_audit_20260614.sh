#!/bin/bash
# Execute the Stage12 native-geometry static audit matrix on HM570.
# Short 200-step runs are geometry/runtime diagnostics only.
set -euo pipefail

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-1}"

ROOT="${STAGE12_NATIVE_ROOT:-/home/yuan/data_sda/RUNS/runs/stage12_native_static}"
ITERATIONS="${STAGE12_NATIVE_ITERATIONS:-200}"

run_case() {
  local name="$1"
  local geom="$2"
  local theta="$3"
  local solid_center="$4"
  local solid_radius="$5"
  local drop_center="$6"
  local physical_grid="$7"
  local cylinder_axis="${8:-0}"
  local plane_args=()
  if [ "$geom" = "wall" ]; then
    plane_args=(--plane-axis 1 --plane-offset 0)
  fi

  echo "=== running $name ==="
  bash /home/yuan/stage12_native_static_run.sh "$name" "$geom" "$theta" "$ITERATIONS"
  local dir="$ROOT/$name"
  local vti
  vti=$(find "$dir/output" -maxdepth 1 -name 'case_VTK_P00_*.vti' | sort | tail -1)
  if [ -z "$vti" ]; then
    echo "missing VTI for $name" >&2
    return 3
  fi
  python3 /home/yuan/stage12_static_audit.py \
    "$vti" "$dir/${name}_audit.png" "$geom" \
    --solid-center $solid_center \
    --solid-radius "$solid_radius" \
    --cylinder-axis "$cylinder_axis" \
    --drop-center $drop_center \
    --drop-radius 16 \
    --physical-grid $physical_grid \
    "${plane_args[@]}" \
    --title "$name: native $geom theta=${theta} deg, 200-step geometry audit" \
    > "$dir/${name}_audit.stdout.json"
}

run_case native_wall_theta090 wall 90 "48 0 48" 0 "48 17 48" "96 80 96"
run_case native_wall_theta030 wall 30 "48 0 48" 0 "48 17 48" "96 80 96"
run_case native_cylinder_theta090 cylinder 90 "48 48 48" 20 "48 70 48" "96 96 96" 2
run_case native_cylinder_theta030 cylinder 30 "48 48 48" 20 "48 70 48" "96 96 96" 2
run_case native_sphere_theta090 sphere 90 "40 40 48" 20 "40 40 90" "80 80 140"
run_case native_sphere_theta030 sphere 30 "40 40 48" 20 "40 40 90" "80 80 140"

python3 - "$ROOT" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
rows = []
for path in sorted(root.glob("native_*/*_audit.json")):
    data = json.loads(path.read_text())
    angles = [
        c.get("theta_grad_deg")
        for c in data.get("contact_angles", [])
        if c.get("status") == "ok" and c.get("theta_grad_deg") is not None
    ]
    rows.append({
        "case": path.parent.name,
        "geometry": data.get("geometry"),
        "cylinder_axis": data.get("cylinder_axis"),
        "audit_status": data.get("audit", {}).get("status"),
        "audit_failures": data.get("audit", {}).get("failures"),
        "audit_warnings": data.get("audit", {}).get("warnings"),
        "contact_status": data.get("contact_info", {}).get("status"),
        "min_abs_surface_distance": data.get("contact_info", {}).get("min_abs_surface_distance"),
        "grid": data.get("grid"),
        "solid_cells": data.get("solid_cells"),
        "fluid_cells": data.get("fluid_cells"),
        "inside_core_solid_fraction": data.get("inside_core_solid_fraction"),
        "outside_far_fluid_fraction": data.get("outside_far_fluid_fraction"),
        "drop_center_is_fluid": data.get("drop_center_is_fluid"),
        "phase_nonfinite": data.get("phase", {}).get("nonfinite"),
        "fluid_phase_min": data.get("fluid_phase_min"),
        "fluid_phase_max": data.get("fluid_phase_max"),
        "fluid_phase_out_of_range_count": data.get("fluid_phase_out_of_range_count"),
        "speed_max": data.get("speed_max"),
        "contact_angle_mean_grad_deg": sum(angles) / len(angles) if angles else None,
        "contact_angle_values_grad_deg": angles,
        "figure": data.get("figure"),
    })
out = root / "stage12_native_static_audit_summary_20260614.json"
out.write_text(json.dumps(rows, indent=2, sort_keys=True))
print(json.dumps(rows, indent=2, sort_keys=True))
PY
