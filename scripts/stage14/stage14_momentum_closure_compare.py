#!/usr/bin/env python3
"""Compare Stage14 momentum-closure probe summaries.

This postprocessor reads probe_A*/s2_replay_smoke_summary.json files produced
by run_stage14_momentum_closure_probe_remote.sh. It reports max-absolute VTI
statistics for the shortest diagnostics that answer whether the MRT g update
injects the selected F/rho once, half, or not at all.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any


FIELDS = [
    "PhaseField",
    "ReplayPhaseFromH",
    "ReplayFtotal",
    "ReplayForceOverRho",
    "ReplayM0",
    "ReplayVelocityHalfForce",
    "ReplayMF",
    "ReplayMomentumAfterG",
    "ReplayMomentumDeltaG",
    "ReplayPressureInput",
    "ReplayPressureForceScale",
    "ReplayPressurePhysicalInput",
    "ReplayFpressureNoThird",
    "ReplayFpressurePhysical",
    "ReplayFmuRaw",
    "ReplayFmuDelta",
    "ReplayHPreSum",
    "ReplayHPostSum",
    "ReplayHeqSum",
    "ReplayHPreMaxAbs",
    "ReplayHPostMaxAbs",
    "ReplayHeqMaxAbs",
    "ReplayFphiSum",
    "ReplayFphiMaxAbs",
    "ReplayTmp1",
    "ReplayTmp1BoundedShadow",
    "ReplayPhaseOutOfBoundsFlag",
    "ReplayStressInputXX",
    "ReplayStressInputYY",
    "ReplayStressInputZZ",
    "ReplayStressIter1XX",
    "ReplayStressIter1YY",
    "ReplayStressIter1ZZ",
    "ReplayStressPreForceShadowXX",
    "ReplayStressPreForceShadowYY",
    "ReplayStressPreForceShadowZZ",
    "ReplayStressPostForceShadowXX",
    "ReplayStressPostForceShadowYY",
    "ReplayStressPostForceShadowZZ",
    "ReplayTauUsed",
    "ReplayRhoForForce",
    "ReplayForceInjectionMode",
    "ReplayPressureClosureMode",
    "ReplayForceDensityClosureMode",
    "ReplayForceFixedPointMode",
    "ReplayForceRhoRaw",
    "ReplayForceRhoEffective",
    "ForceIterCount",
    "ForceIterResidual",
]


def probe_name(path: Path) -> str:
    for part in path.parts:
        if part.startswith("probe_"):
            return part
    match = re.search(r"(probe_[^/\\]+)", str(path))
    return match.group(1) if match else ""


def probe_mode(path: Path) -> int:
    match = re.search(r"probe_A(\d+)", str(path))
    return int(match.group(1)) if match else -1


def load_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def frame_at(summary: dict[str, Any], step: int) -> dict[str, Any] | None:
    for case in summary.get("cases", []):
        for frame in case.get("frames", []):
            if frame.get("step") == step:
                return frame
    return None


def stat_max_abs(frame: dict[str, Any], field: str) -> Any:
    stats = frame.get("stats", {}).get(field, {})
    if not stats.get("present"):
        return None
    return stats.get("max_abs")


def stat_nonfinite(frame: dict[str, Any], field: str) -> Any:
    stats = frame.get("stats", {}).get(field, {})
    if not stats.get("present"):
        return None
    return stats.get("nonfinite_count")


def build_rows(root: Path, step: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for summary_path in sorted(root.glob("probe_*/s2_replay_smoke_summary.json")):
        summary = load_summary(summary_path)
        frame = frame_at(summary, step)
        row: dict[str, Any] = {
            "probe": probe_name(summary_path),
            "probe_mode": probe_mode(summary_path),
            "summary_path": str(summary_path),
            "step": step,
            "failures": ";".join(summary.get("failures", [])),
        }
        if frame is None:
            row["missing_step"] = True
        else:
            row["missing_step"] = False
            for field in FIELDS:
                row[f"{field}_max_abs"] = stat_max_abs(frame, field)
                row[f"{field}_nonfinite"] = stat_nonfinite(frame, field)
        rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--step", type=int, default=6)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    rows = build_rows(args.root, args.step)
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        fields = sorted({key for row in rows for key in row})
        with args.csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(rows, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(rows, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
