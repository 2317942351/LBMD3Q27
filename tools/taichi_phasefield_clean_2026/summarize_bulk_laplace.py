"""Summarize Stage18 bulk ladder and Laplace-radius Taichi artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def summarize_ladder(root: Path) -> dict[str, object]:
    rows = []
    for metrics_path in sorted(root.glob("ratio*_bulk_1000/output/metrics.json")):
        case_dir = metrics_path.parents[1]
        status_path = case_dir / "run.status"
        status_text = status_path.read_text(encoding="utf-8").strip() if status_path.exists() else "RC=?"
        data = json.loads(metrics_path.read_text(encoding="utf-8"))
        final = data["final"]
        ratio = float(data["density_ratio"])
        mass_tol = 1.0e-8 if ratio <= 50.0 else 1.0e-7
        umax_tol = 1.0e-3 if ratio <= 50.0 else 5.0e-3
        pass_gate = (
            status_text == "RC=0"
            and data["status"] == "pass"
            and final["nonfinite_count"] == 0
            and final["c_oob_low"] == 0
            and final["c_oob_high"] == 0
            and abs(final["mass_correction_delta"]) <= 1.0e-12
            and data["max_abs_mass_drift"] <= mass_tol
            and final["u_max"] <= umax_tol
        )
        rows.append(
            {
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
            }
        )
    return {"status": "pass" if rows and all(row["gate_status"] == "pass" for row in rows) else "fail", "rows": rows}


def summarize_laplace(root: Path) -> dict[str, object]:
    rows = []
    for metrics_path in sorted(root.glob("radius*_ratio10_3000/output/metrics.json")):
        case_dir = metrics_path.parents[1]
        status_path = case_dir / "run.status"
        status_text = status_path.read_text(encoding="utf-8").strip() if status_path.exists() else "RC=?"
        data = json.loads(metrics_path.read_text(encoding="utf-8"))
        final = data["final"]
        volume_radius = final["droplet_volume_radius"]
        rows.append(
            {
                "case": case_dir.name,
                "rc": status_text,
                "solver_status": data["status"],
                "volume_radius": volume_radius,
                "inv_R": 1.0 / volume_radius if volume_radius else 0.0,
                "delta_p": final["laplace_delta_p"],
                "target": final["laplace_delta_p_target"],
                "rel_err": final["laplace_delta_p_relative_error"],
                "u_max": final["u_max"],
                "spurious_u_rms_interface": final["spurious_u_rms_interface"],
                "mass_drift": data["max_abs_mass_drift"],
                "mass_correction_delta": final["mass_correction_delta"],
                "nonfinite_count": final["nonfinite_count"],
            }
        )
    xs = [row["inv_R"] for row in rows]
    ys = [row["delta_p"] for row in rows]
    slope = sum(x * y for x, y in zip(xs, ys)) / max(sum(x * x for x in xs), 1.0e-30)
    sigma_fit = slope / 2.0
    for row in rows:
        row["fit_slope"] = slope
        row["fit_sigma"] = sigma_fit
    pass_gate = bool(rows) and all(
        row["rc"] == "RC=0"
        and row["solver_status"] == "pass"
        and row["nonfinite_count"] == 0
        and abs(row["mass_correction_delta"]) <= 1.0e-12
        and row["u_max"] <= 1.0e-3
        for row in rows
    )
    return {"status": "pass" if pass_gate else "fail", "fit_slope": slope, "fit_sigma": sigma_fit, "rows": rows}


def write_table(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--kind", choices=("ladder", "laplace"), required=True)
    args = parser.parse_args()

    report = summarize_ladder(args.root) if args.kind == "ladder" else summarize_laplace(args.root)
    stem = "bulk_ladder_summary" if args.kind == "ladder" else "laplace_radius_summary"
    write_table(args.root / f"{stem}.csv", report["rows"])
    (args.root / f"{stem}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "rows": len(report["rows"]), "root": str(args.root)}, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
