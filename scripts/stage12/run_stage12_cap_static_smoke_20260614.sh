#!/bin/bash
# Run cap-initialized Stage12 static-contact smoke cases on HM570.
set -euo pipefail

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-1}"

ROOT="${STAGE12_CAP_ROOT:-/home/yuan/data_sda/RUNS/runs/stage12_cap_static_smoke_20260614}"
ITERATIONS="${STAGE12_CAP_ITERATIONS:-200}"
RUNNER="${STAGE12_CAP_RUNNER:-/home/yuan/stage12_cap_static_run.py}"
AUDIT="${STAGE12_AUDIT:-/home/yuan/stage12_static_audit.py}"

run_case() {
  local name="$1"
  local geom="$2"
  local theta="$3"

  echo "=== cap smoke $name ==="
  python3 "$RUNNER" "$name" "$geom" "$theta" "$ITERATIONS" --root "$ROOT" --force

  local dir="$ROOT/$name"
  local meta="$dir/case_metadata.json"
  local vti
  vti=$(find "$dir/output" -maxdepth 1 -name 'case_VTK_P00_*.vti' | sort | tail -1)
  if [ -z "$vti" ]; then
    echo "missing VTI for $name" >&2
    return 3
  fi

  python3 - "$meta" "$vti" "$dir/${name}_audit.png" "$AUDIT" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

meta = json.loads(Path(sys.argv[1]).read_text())
vti = sys.argv[2]
png = sys.argv[3]
audit = sys.argv[4]
geom = meta["geometry"]
cmd = [
    "python3",
    audit,
    vti,
    png,
    geom,
    "--solid-center",
    *[str(v) for v in meta["solid_center"]],
    "--solid-radius",
    str(meta["solid_radius"]),
    "--drop-center",
    *[str(v) for v in meta["liquid_probe"]],
    "--drop-radius",
    str(meta["volume_equivalent_radius"]),
    "--physical-grid",
    *[str(v) for v in meta["grid"]],
    "--require-contact",
    "--title",
    f"{meta['case']}: cap-init {geom} theta={meta['target_theta_deg']} deg, {meta['iterations']}-step smoke",
]
if geom == "wall":
    cmd += ["--plane-axis", str(meta.get("plane_axis", 1)), "--plane-offset", str(meta.get("plane_offset", 0.0))]
if geom == "cylinder":
    cmd += ["--cylinder-axis", str(meta.get("cylinder_axis", 0))]
completed = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
Path(png).with_suffix(".stdout.json").write_text(completed.stdout)
print(completed.stdout)
raise SystemExit(completed.returncode)
PY
}

run_case cap_wall_theta030 wall 30
run_case cap_wall_theta090 wall 90
run_case cap_sphere_theta030 sphere 30
run_case cap_sphere_theta090 sphere 90
run_case cap_cylinder_theta030 cylinder 30
run_case cap_cylinder_theta090 cylinder 90

python3 - "$ROOT" <<'PY'
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
rows = []
for path in sorted(root.glob("cap_*/*_audit.json")):
    data = json.loads(path.read_text())
    meta_path = path.parent / "case_metadata.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    run_log = path.parent / "run.log"
    rc = None
    nan_lines = None
    if run_log.exists():
        text = run_log.read_text(errors="replace")
        m = re.search(r"RUN_RC=(-?\d+)", text)
        if m:
            rc = int(m.group(1))
        nan_lines = len(re.findall(r"nan", text, re.IGNORECASE))
    angles = [
        c.get("theta_grad_deg")
        for c in data.get("contact_angles", [])
        if c.get("status") == "ok" and c.get("theta_grad_deg") is not None
    ]
    tangent_angles = [
        c.get("theta_tangent_abs_deg")
        for c in data.get("contact_angles", [])
        if c.get("status") == "ok" and c.get("theta_tangent_abs_deg") is not None
    ]
    circle_fit_angles = [
        c.get("theta_circle_fit_abs_deg")
        for c in data.get("contact_angles", [])
        if c.get("status") == "ok" and c.get("theta_circle_fit_abs_deg") is not None
    ]
    circle_intersection_angles = [
        c.get("theta_circle_intersection_abs_deg")
        for c in data.get("contact_angles", [])
        if c.get("status") == "ok" and c.get("theta_circle_intersection_abs_deg") is not None
    ]
    audit_status = data.get("audit", {}).get("status")
    contact_status = data.get("contact_info", {}).get("status")
    if audit_status and audit_status.startswith("PASS") and contact_status == "contacted":
        classification = "runtime_sanity"
    else:
        classification = "exploratory_not_validation"
    rows.append({
        "case": path.parent.name,
        "geometry": data.get("geometry"),
        "target_theta_deg": meta.get("target_theta_deg"),
        "classification": classification,
        "claim_limit": meta.get("claim_limit"),
        "run_rc": rc,
        "run_log_nan_lines": nan_lines,
        "audit_status": audit_status,
        "audit_failures": data.get("audit", {}).get("failures"),
        "audit_warnings": data.get("audit", {}).get("warnings"),
        "contact_status": contact_status,
        "min_abs_surface_distance": data.get("contact_info", {}).get("min_abs_surface_distance"),
        "inside_core_solid_fraction": data.get("inside_core_solid_fraction"),
        "outside_far_fluid_fraction": data.get("outside_far_fluid_fraction"),
        "phase_nonfinite": data.get("phase", {}).get("nonfinite"),
        "fluid_phase_min": data.get("fluid_phase_min"),
        "fluid_phase_max": data.get("fluid_phase_max"),
        "fluid_phase_out_of_range_count": data.get("fluid_phase_out_of_range_count"),
        "speed_max": data.get("speed_max"),
        "contact_angle_mean_grad_deg": sum(angles) / len(angles) if angles else None,
        "contact_angle_values_grad_deg": angles,
        "contact_angle_mean_tangent_abs_deg": sum(tangent_angles) / len(tangent_angles) if tangent_angles else None,
        "contact_angle_values_tangent_abs_deg": tangent_angles,
        "contact_angle_mean_circle_fit_abs_deg": sum(circle_fit_angles) / len(circle_fit_angles) if circle_fit_angles else None,
        "contact_angle_values_circle_fit_abs_deg": circle_fit_angles,
        "contact_angle_mean_circle_intersection_abs_deg": sum(circle_intersection_angles) / len(circle_intersection_angles) if circle_intersection_angles else None,
        "contact_angle_values_circle_intersection_abs_deg": circle_intersection_angles,
        "interface_circle_fit": data.get("contact_info", {}).get("interface_circle_fit"),
        "figure": data.get("figure"),
        "final_vti": data.get("vti"),
        "binary_sha256": meta.get("binary_sha256"),
    })
out = root / "stage12_cap_static_smoke_summary_20260614.json"
out.write_text(json.dumps(rows, indent=2, sort_keys=True))
print(json.dumps(rows, indent=2, sort_keys=True))
PY
