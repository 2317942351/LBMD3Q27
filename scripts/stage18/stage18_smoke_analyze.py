#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

import numpy as np

try:
    from stage14_b106_extract_vti_stats import read_vti_arrays, stat
except ModuleNotFoundError:
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1] / "stage14"))
    from stage14_b106_extract_vti_stats import read_vti_arrays, stat


FIELDS = {
    "PhaseField",
    "PhaseFValid",
    "PhaseOutOfBoundsFlag",
    "Rho",
    "U",
    "P",
    "Pstar",
    "GradPhi",
    "WallPhase",
    "ForceTotal",
    "Stage18Violation",
    "PressureInput",
    "ForceOverRho",
    "ForceInsertionAudit",
    "ForceHalfVelocity",
    "ForceMomentumBefore",
    "ForceMomentumAfter",
    "ForceEquivalentInjected",
    "MassCorrectionApplied",
    "WallHNetMass",
    "WallHLinkWriteCount",
    "WallHMassBefore",
    "WallHMassAfter",
    "PhaseHPreSum",
    "PhaseHRawSum",
    "PhaseHRawMin",
    "PhaseHRawMax",
    "PhaseHRawNonfiniteCount",
    "PhaseHeqSum",
    "PhaseFphiSum",
    "PhaseHPostSum",
    "PhaseCorrectionDelta",
    "PhaseMassRedistributionWeight",
    "PhaseGlobalCorrectionApplied",
    "PhasePopulationRepairApplied",
    "PhaseFphiFirstMoment",
}


FAIL_PATTERNS = (
    "discovered NaN",
    "Stopping due to Nan",
    "NaN value discovered",
)


def step_from_name(path: Path) -> int:
    match = re.search(r"_(\d+)\.vti$", path.name)
    return int(match.group(1)) if match else -1


def flatten_stats(prefix: str, values: np.ndarray) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if values.ndim == 2 and values.shape[1] in (2, 3):
        labels = ("x", "y", "z")[: values.shape[1]]
        mag = np.linalg.norm(values, axis=1)
        for idx, label in enumerate(labels):
            for key, val in stat(values[:, idx]).items():
                result[f"{prefix}_{label}_{key}"] = val
        for key, val in stat(mag).items():
            result[f"{prefix}_mag_{key}"] = val
    else:
        for key, val in stat(values).items():
            result[f"{prefix}_{key}"] = val
    return result


def summarize_case(case_dir: Path) -> list[dict[str, Any]]:
    output = case_dir / "output"
    rows: list[dict[str, Any]] = []
    for vti in sorted(output.glob("*.vti"), key=step_from_name):
        arrays = read_vti_arrays(vti, FIELDS)
        row: dict[str, Any] = {
            "case": case_dir.name,
            "step": step_from_name(vti),
            "vti": str(vti),
            "missing": ";".join(sorted(FIELDS - set(arrays))),
        }
        for name, arr in arrays.items():
            row.update(flatten_stats(name, arr))
        rows.append(row)
    return rows


def summarize_logs(case_dir: Path) -> dict[str, Any]:
    status_path = case_dir / "run.status"
    log_path = case_dir / "run.log"
    stderr_path = case_dir / "run.stderr"
    info: dict[str, Any] = {
        "case": case_dir.name,
        "run_rc": None,
        "run_log_failcheck_nan": False,
        "run_log_fail_lines": [],
        "run_stderr_tail": "",
    }
    if status_path.exists():
        text = status_path.read_text(encoding="utf-8", errors="replace").strip()
        match = re.search(r"RC=(\d+)", text)
        if match:
            info["run_rc"] = int(match.group(1))
    if log_path.exists():
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        fail_lines = [line for line in lines if any(pattern in line for pattern in FAIL_PATTERNS)]
        info["run_log_fail_lines"] = fail_lines
        info["run_log_failcheck_nan"] = bool(fail_lines)
    if stderr_path.exists():
        stderr_lines = stderr_path.read_text(encoding="utf-8", errors="replace").splitlines()
        info["run_stderr_tail"] = "\n".join(stderr_lines[-20:])
    return info


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-csv", type=Path, required=True)
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    log_summaries: list[dict[str, Any]] = []
    for case_dir in sorted(p for p in args.root.iterdir() if p.is_dir()):
        if (case_dir / "run.log").exists() or (case_dir / "run.status").exists():
            log_summaries.append(summarize_logs(case_dir))
        if (case_dir / "output").is_dir():
            rows.extend(summarize_case(case_dir))

    verdict = "pass"
    failures: list[str] = []
    for log_info in log_summaries:
        case = log_info["case"]
        if log_info.get("run_rc") not in (0, None):
            failures.append(f"{case}: run RC {log_info['run_rc']}")
        if log_info.get("run_log_failcheck_nan"):
            for line in log_info.get("run_log_fail_lines", []):
                failures.append(f"{case}: {line.strip()}")
    for row in rows:
        if row.get("PhaseField_nonfinite_count", 0) not in (0, None):
            failures.append(f"{row['case']} step {row['step']}: nonfinite PhaseField")
        if row.get("Stage18Violation_max", 0) not in (0, 0.0, None):
            failures.append(f"{row['case']} step {row['step']}: Stage18Violation nonzero")
        phase_min = row.get("PhaseField_min")
        phase_max = row.get("PhaseField_max")
        if phase_min is not None and phase_min < -1e-9:
            failures.append(f"{row['case']} step {row['step']}: PhaseField min {phase_min}")
        if phase_max is not None and phase_max > 1.0 + 1e-9:
            failures.append(f"{row['case']} step {row['step']}: PhaseField max {phase_max}")
    if failures or not rows:
        verdict = "fail"

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with args.out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    result = {
        "root": str(args.root),
        "rows": rows,
        "run_logs": log_summaries,
        "verdict": verdict,
        "failures": failures,
        "claim_limit": "stage18_smoke_only_not_contact_angle_validation",
    }
    args.out_json.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"root": str(args.root), "rows": len(rows), "verdict": verdict}, indent=2))
    return 0 if verdict == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
