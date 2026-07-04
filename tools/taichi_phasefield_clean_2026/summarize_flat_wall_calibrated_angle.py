"""Batch calibrated bbox contact-angle analysis for flat-wall Taichi artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from analyze_flat_wall_calibrated_angle import analyze


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="artifact root containing */output/final_fields.npz")
    parser.add_argument("--radius", type=float, default=None)
    parser.add_argument("--width", type=float, default=None)
    parser.add_argument("--z-slices", type=int, default=3)
    args = parser.parse_args()

    rows: list[dict[str, object]] = []
    for npz_path in sorted(args.root.glob("*/output/final_fields.npz")):
        case_dir = npz_path.parent.parent
        out_dir = case_dir / "analysis_calibrated_bbox"
        report = analyze(npz_path, out_dir, args.radius, args.width, args.z_slices)
        rows.append(
            {
                "case": case_dir.name,
                "target_theta_deg": report.get("target_theta_deg"),
                "init_contact_angle_deg": report.get("init_contact_angle_deg"),
                "theta_bbox_raw_mean_deg": report.get("theta_bbox_raw_mean_deg"),
                "theta_calibrated_bbox_deg": report.get("theta_calibrated_bbox_deg"),
                "target_error_calibrated_deg": report.get("target_error_calibrated_deg"),
                "calibration_outside_range": report.get("calibration_outside_range"),
                "radius_used_for_calibration": report.get("radius_used_for_calibration"),
                "width_used_for_calibration": report.get("width_used_for_calibration"),
                "z_indices": " ".join(str(v) for v in report.get("z_indices", [])),
            }
        )

    summary = {
        "root": str(args.root),
        "method": "Stage15D calibrated bbox h/a adapted to Taichi NPZ",
        "claim_limit": "measurement summary only; use with morphology/mass/velocity evidence",
        "cases": rows,
    }
    (args.root / "flat_wall_calibrated_bbox_summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=True),
        encoding="utf-8",
    )
    if rows:
        with (args.root / "flat_wall_calibrated_bbox_summary.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps({"root": str(args.root), "cases": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
