"""Summarize flat-wall morphology analyses for a run root."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from analyze_flat_wall_morphology import analyze, run_synthetic_checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="local artifact root containing case/output/final_fields.npz")
    parser.add_argument("--wall-y", type=float, default=None)
    args = parser.parse_args()

    run_synthetic_checks()
    rows: list[dict[str, object]] = []
    for npz in sorted(args.root.glob("*/output/final_fields.npz")):
        case_dir = npz.parent.parent
        report = analyze(npz, case_dir / "analysis", args.wall_y)
        row = {"case": case_dir.name, **report}
        rows.append(row)

    args.root.mkdir(parents=True, exist_ok=True)
    (args.root / "flat_wall_morphology_summary.json").write_text(
        json.dumps({"cases": rows}, indent=2, allow_nan=True),
        encoding="utf-8",
    )
    keys = [
        "case",
        "target_theta_deg",
        "init_contact_angle_deg",
        "mean_deg",
        "target_error_deg",
        "left_deg",
        "right_deg",
        "fit_center_y",
        "fit_radius",
        "wall_y",
        "interface_points",
    ]
    with (args.root / "flat_wall_morphology_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(json.dumps({"root": str(args.root), "cases": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
