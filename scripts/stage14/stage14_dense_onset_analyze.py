#!/usr/bin/env python3
"""Summarize dense-onset replay diagnostics and locate first failure."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


FIELDS = [
    "PhaseField",
    "ReplayPhaseConsumed",
    "ReplayPhaseFromH",
    "ReplayPhaseOutOfBoundsFlag",
    "ReplayTmp1",
    "ReplayTmp1BoundedShadow",
    "ReplayHPreSum",
    "ReplayHPostSum",
    "ReplayHeqSum",
    "ReplayHPreMaxAbs",
    "ReplayHPostMaxAbs",
    "ReplayHeqMaxAbs",
    "ReplayFphiSum",
    "ReplayFphiMaxAbs",
    "ReplayMu",
    "ReplayGradPhi",
    "ReplayFpressure",
    "ReplayPressureInput",
    "ReplayFmuRaw",
    "ReplayFmuDelta",
    "ReplayStressInputXX",
    "ReplayStressInputYY",
    "ReplayStressInputZZ",
    "ReplayStressPreForceShadowXX",
    "ReplayStressPreForceShadowYY",
    "ReplayStressPreForceShadowZZ",
    "ReplayStressPostForceShadowXX",
    "ReplayStressPostForceShadowYY",
    "ReplayStressPostForceShadowZZ",
    "ReplayFtotal",
    "ReplayForceOverRho",
]


THRESHOLDS = {
    "phase_bounds": ("ReplayPhaseFromH", 1.0 + 1e-3),
    "phase_output_bounds": ("PhaseField", 1.0 + 1e-3),
    "tmp1_large": ("ReplayTmp1", 1.0),
    "fphi_large": ("ReplayFphiMaxAbs", 1.0),
    "force_over_rho_large": ("ReplayForceOverRho", 1.0e3),
    "fmu_large": ("ReplayFmuRaw", 1.0e3),
    "stress_large": ("ReplayStressInputYY", 1.0e3),
    "pressure_large": ("ReplayPressureInput", 1.0e3),
}


def load_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stat(frame: dict[str, Any], field: str) -> dict[str, Any]:
    out = frame.get("stats", {}).get(field, {})
    if not out.get("present"):
        return {}
    return out


def build_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in summary.get("cases", []):
        for frame in sorted(case.get("frames", []), key=lambda item: item.get("step", -1)):
            row: dict[str, Any] = {"case": case.get("case"), "step": frame.get("step")}
            for field in FIELDS:
                s = stat(frame, field)
                row[f"{field}_max_abs"] = s.get("max_abs")
                row[f"{field}_min"] = s.get("min")
                row[f"{field}_max"] = s.get("max")
                row[f"{field}_nonfinite"] = s.get("nonfinite_count")
            rows.append(row)
    return rows


def first_failures(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        step = row["step"]
        for field in FIELDS:
            nonfinite = row.get(f"{field}_nonfinite")
            if nonfinite and nonfinite > 0:
                key = f"nonfinite_{field}"
                if key not in seen:
                    seen.add(key)
                    failures.append({"failure": key, "step": step, "value": nonfinite})
        for name, (field, threshold) in THRESHOLDS.items():
            key = f"threshold_{name}"
            value = row.get(f"{field}_max_abs")
            if value is not None and abs(float(value)) > threshold and key not in seen:
                seen.add(key)
                failures.append({"failure": key, "step": step, "value": value})
    return sorted(failures, key=lambda item: (item["step"], item["failure"]))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path)
    parser.add_argument("--frames-csv", type=Path)
    parser.add_argument("--failures-json", type=Path)
    parser.add_argument("--failures-csv", type=Path)
    args = parser.parse_args()

    summary = load_summary(args.summary)
    rows = build_rows(summary)
    failures = first_failures(rows)
    if args.frames_csv:
        write_csv(args.frames_csv, rows)
    if args.failures_json:
        args.failures_json.parent.mkdir(parents=True, exist_ok=True)
        args.failures_json.write_text(json.dumps(failures, indent=2, sort_keys=True), encoding="utf-8")
    if args.failures_csv:
        write_csv(args.failures_csv, failures)
    print(json.dumps({"frames": len(rows), "first_failures": failures[:20]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
