"""Merge Taichi flat-wall morphology and runtime metrics into one table."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()

    rows: list[dict[str, object]] = []
    for case_dir in sorted(p for p in args.root.iterdir() if p.is_dir()):
        metrics = load_json(case_dir / "output" / "metrics.json")
        morph = load_json(case_dir / "analysis" / "morphology_metrics.json")
        final = metrics.get("final", {}) if isinstance(metrics.get("final"), dict) else {}
        row = {
            "case": case_dir.name,
            "status": metrics.get("status"),
            "theta_deg": metrics.get("theta_deg"),
            "init_contact_angle_deg": metrics.get("init_contact_angle_deg"),
            "phase_advection_mode": metrics.get("phase_advection_mode"),
            "wetting_ghost_distance": metrics.get("wetting_ghost_distance"),
            "wetting_ghost_sign": metrics.get("wetting_ghost_sign"),
            "measured_mean_deg": morph.get("mean_deg"),
            "target_error_deg": morph.get("target_error_deg"),
            "mass_drift": final.get("mass_drift"),
            "mass_correction_delta": final.get("mass_correction_delta"),
            "phase_wall_delta_mass": final.get("phase_wall_delta_mass"),
            "u_max": final.get("u_max"),
            "force_over_rho_max": final.get("force_over_rho_max"),
            "near_wall_interface_cells": final.get("near_wall_interface_cells"),
            "near_wall_force_over_rho_max": final.get("near_wall_force_over_rho_max"),
            "near_wall_mu_abs_max": final.get("near_wall_mu_abs_max"),
            "wall_ghost_min": final.get("wall_ghost_min"),
            "wall_ghost_max": final.get("wall_ghost_max"),
            "wall_ghost_clamp_low_cells": final.get("wall_ghost_clamp_low_cells"),
            "wall_ghost_clamp_high_cells": final.get("wall_ghost_clamp_high_cells"),
            "nonfinite_count": final.get("nonfinite_count"),
        }
        rows.append(row)

    out_csv = args.root / "flat_wall_runtime_morphology_merged.csv"
    out_json = args.root / "flat_wall_runtime_morphology_merged.json"
    out_json.write_text(json.dumps({"cases": rows}, indent=2, allow_nan=True), encoding="utf-8")
    if rows:
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps({"root": str(args.root), "cases": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
