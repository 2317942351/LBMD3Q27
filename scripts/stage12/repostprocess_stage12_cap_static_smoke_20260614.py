#!/usr/bin/env python3
"""Re-audit existing Stage12 cap-static smoke VTI outputs."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


def run_audit(root: Path, audit: Path) -> None:
    for meta_path in sorted(root.glob("cap_*/case_metadata.json")):
        meta = json.loads(meta_path.read_text())
        case_dir = meta_path.parent
        vtis = sorted((case_dir / "output").glob("case_VTK_P00_*.vti"))
        if not vtis:
            raise RuntimeError(f"no VTI output for {case_dir}")
        png = case_dir / f"{meta['case']}_audit.png"
        cmd = [
            "python3",
            str(audit),
            str(vtis[-1]),
            str(png),
            meta["geometry"],
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
            f"{meta['case']}: cap-init {meta['geometry']} theta={meta['target_theta_deg']} deg, {meta['iterations']}-step smoke",
        ]
        if meta["geometry"] == "wall":
            cmd += ["--plane-axis", str(meta.get("plane_axis", 1)), "--plane-offset", str(meta.get("plane_offset", 0.0))]
        if meta["geometry"] == "cylinder":
            cmd += ["--cylinder-axis", str(meta.get("cylinder_axis", 0))]
        completed = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        png.with_suffix(".stdout.json").write_text(completed.stdout)
        if completed.returncode:
            raise RuntimeError(f"audit failed for {case_dir}:\n{completed.stdout}")


def summarize(root: Path) -> list[dict]:
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
        angle_keys = [
            "theta_grad_deg",
            "theta_tangent_abs_deg",
            "theta_circle_fit_abs_deg",
            "theta_circle_intersection_abs_deg",
        ]
        angle_values = {
            key: [
                c.get(key)
                for c in data.get("contact_angles", [])
                if c.get("status") == "ok" and c.get(key) is not None
            ]
            for key in angle_keys
        }
        audit_status = data.get("audit", {}).get("status")
        contact_status = data.get("contact_info", {}).get("status")
        if audit_status and audit_status.startswith("PASS") and contact_status == "contacted":
            classification = "validation_candidate" if data.get("geometry") in {"wall", "sphere"} else "runtime_sanity"
        else:
            classification = "exploratory_not_validation"
        row = {
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
            "interface_circle_fit": data.get("contact_info", {}).get("interface_circle_fit"),
            "figure": data.get("figure"),
            "final_vti": data.get("vti"),
            "binary_sha256": meta.get("binary_sha256"),
        }
        for key, values in angle_values.items():
            stem = key.removeprefix("theta_").removesuffix("_deg")
            row[f"contact_angle_mean_{stem}_deg"] = sum(values) / len(values) if values else None
            row[f"contact_angle_values_{stem}_deg"] = values
        rows.append(row)
    out = root / "stage12_cap_static_smoke_summary_20260614.json"
    out.write_text(json.dumps(rows, indent=2, sort_keys=True))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/home/yuan/data_sda/RUNS/runs/stage12_cap_static_smoke_20260614"))
    parser.add_argument("--audit", type=Path, default=Path("/home/yuan/stage12_static_audit.py"))
    parser.add_argument("--skip-audit", action="store_true")
    args = parser.parse_args()
    if not args.skip_audit:
        run_audit(args.root, args.audit)
    print(json.dumps(summarize(args.root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
