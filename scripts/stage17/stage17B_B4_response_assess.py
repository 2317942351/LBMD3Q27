#!/usr/bin/env python3
"""Assess Stage17B-B4 morphology response direction from summary CSV.

This script is intentionally conservative. It does not claim contact-angle
validation. It checks whether short-run morphology metrics show a clear response
from init theta toward target theta.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def as_float(value: str) -> float | None:
    if value in {"", "None", "nan", "NaN"}:
        return None
    return float(value)


def as_int(value: str) -> int:
    return int(float(value))


def delta(last: dict[str, str], first: dict[str, str], field: str) -> float | None:
    a = as_float(last.get(field, ""))
    b = as_float(first.get(field, ""))
    if a is None or b is None:
        return None
    return a - b


def assess_case(rows: list[dict[str, str]]) -> dict[str, Any]:
    rows = sorted(rows, key=lambda item: as_int(item["step"]))
    first = rows[0]
    last = rows[-1]
    init = as_float(last["init_theta_deg"]) or 0.0
    target = as_float(last["target_theta_deg"]) or init
    expected = "control"
    if target < init:
        expected = "spread"
    elif target > init:
        expected = "retract"

    metrics = {
        "area_delta_cells": as_int(last["liquid_area_cells"]) - as_int(first["liquid_area_cells"]),
        "footprint_delta_cells": as_int(last["footprint_cells"]) - as_int(first["footprint_cells"]),
        "height_delta_cells": as_int(last["height_cells"]) - as_int(first["height_cells"]),
        "centroid_y_delta": delta(last, first, "centroid_y"),
        "angle_acute_delta_deg": delta(last, first, "angle_acute_deg"),
        "angle_obtuse_delta_deg": delta(last, first, "angle_obtuse_deg"),
        "phase_min_final": as_float(last["phase_min"]),
        "phase_max_final": as_float(last["phase_max"]),
        "phase_nonfinite_final": as_int(last["phase_nonfinite"]),
    }

    signals: list[str] = []
    if expected == "spread":
        if metrics["footprint_delta_cells"] > 1:
            signals.append("footprint_spreads")
        if metrics["height_delta_cells"] < -1:
            signals.append("height_flattens")
        if metrics["footprint_delta_cells"] < -1:
            signals.append("footprint_contracts_opposite")
        if metrics["height_delta_cells"] > 1:
            signals.append("height_increases_opposite")
    elif expected == "retract":
        if metrics["footprint_delta_cells"] < -1:
            signals.append("footprint_contracts")
        if metrics["height_delta_cells"] > 1:
            signals.append("height_increases")
        if metrics["footprint_delta_cells"] > 1:
            signals.append("footprint_spreads_opposite")
        if metrics["height_delta_cells"] < -1:
            signals.append("height_flattens_opposite")
    else:
        if abs(metrics["footprint_delta_cells"]) <= 1 and abs(metrics["height_delta_cells"]) <= 1:
            signals.append("near_stationary")
        else:
            signals.append("control_drift")

    if metrics["phase_nonfinite_final"] != 0:
        verdict = "fail_nonfinite"
    elif expected == "control":
        verdict = "control_stable" if "near_stationary" in signals else "control_drift"
    else:
        positive = [item for item in signals if not item.endswith("_opposite")]
        opposite = [item for item in signals if item.endswith("_opposite")]
        if positive and not opposite:
            verdict = "direction_plausible_short_run"
        elif opposite and not positive:
            verdict = "direction_opposite_or_not_coupled"
        else:
            verdict = "weak_or_mixed_response"

    return {
        "case": last["case"],
        "geometry": last["geometry"],
        "init_theta_deg": init,
        "target_theta_deg": target,
        "expected_response": expected,
        "signals": signals,
        "verdict": verdict,
        "metrics": metrics,
        "claim_limit": "short-run morphology response assessment only; not contact-angle validation",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frames_csv", type=Path)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-csv", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with args.frames_csv.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["case"], []).append(row)
    cases = [assess_case(group) for _, group in sorted(grouped.items())]
    failures = [
        case
        for case in cases
        if case["verdict"] in {"fail_nonfinite", "direction_opposite_or_not_coupled"}
    ]
    summary = {
        "status": "B4_RESPONSE_NOT_VALIDATED" if failures else "B4_RESPONSE_WEAK_OR_MIXED",
        "claim_limit": "short-run morphology response assessment only; not contact-angle validation",
        "source_csv": str(args.frames_csv),
        "cases": cases,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    flat_rows: list[dict[str, Any]] = []
    for case in cases:
        row = {
            "case": case["case"],
            "geometry": case["geometry"],
            "init_theta_deg": case["init_theta_deg"],
            "target_theta_deg": case["target_theta_deg"],
            "expected_response": case["expected_response"],
            "verdict": case["verdict"],
            "signals": ";".join(case["signals"]),
        }
        row.update(case["metrics"])
        flat_rows.append(row)
    with args.out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0]))
        writer.writeheader()
        writer.writerows(flat_rows)
    print(json.dumps({k: v for k, v in summary.items() if k != "cases"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
