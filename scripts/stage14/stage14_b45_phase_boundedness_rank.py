#!/usr/bin/env python3
"""Stage14-B45 phase h-update boundedness postprocess gate.

B45 reads B21/B22 VTI fields and determines whether PhaseFromH leaves [0, 1]
after h-update shadow quantities already leave bounds, or whether force/velocity
producers are the first observable trigger. It is diagnostic-only.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

import numpy as np


def step_of(path: Path) -> int:
    match = re.search(r"P00_(\d+)\.vti$", path.name)
    return int(match.group(1)) if match else -1


def load_vti(path: Path) -> tuple[tuple[int, int, int], dict[str, np.ndarray]]:
    import vtk  # type: ignore
    from vtk.util.numpy_support import vtk_to_numpy  # type: ignore

    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(str(path))
    reader.Update()
    image = reader.GetOutput()
    dims = tuple(int(v) - 1 for v in image.GetDimensions())
    cell_data = image.GetCellData()
    arrays: dict[str, np.ndarray] = {}
    for idx in range(cell_data.GetNumberOfArrays()):
        arr = cell_data.GetArray(idx)
        if arr is not None:
            arrays[arr.GetName() or f"array_{idx}"] = vtk_to_numpy(arr).copy()
    return dims, arrays


def crop(arr: np.ndarray, dims: tuple[int, int, int], physical_grid: list[int] | None) -> np.ndarray:
    values = np.asarray(arr)
    if not physical_grid:
        return values
    px, py, pz = [int(v) for v in physical_grid]
    nx, ny, nz = dims
    if px > nx or py > ny or pz > nz or values.shape[0] != nx * ny * nz:
        return values
    if values.ndim == 1:
        return values.reshape((nx, ny, nz))[:px, :py, :pz].reshape(-1)
    return values.reshape((nx, ny, nz, values.shape[1]))[:px, :py, :pz, :].reshape(-1, values.shape[1])


def read_metadata(case_dir: Path) -> dict[str, Any]:
    path = case_dir / "case_metadata.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def case_dirs(root: Path) -> list[Path]:
    if (root / "output").is_dir():
        return [root]
    return sorted(path.parent for path in root.rglob("output") if path.is_dir())


def finite_min(arr: np.ndarray) -> float | None:
    values = np.asarray(arr, dtype=float)
    values = values[np.isfinite(values)]
    return float(np.min(values)) if values.size else None


def finite_max(arr: np.ndarray) -> float | None:
    values = np.asarray(arr, dtype=float)
    values = values[np.isfinite(values)]
    return float(np.max(values)) if values.size else None


def finite_count_oob(arr: np.ndarray, lo: float = 0.0, hi: float = 1.0) -> int:
    values = np.asarray(arr, dtype=float)
    finite = np.isfinite(values)
    return int(np.count_nonzero(finite & ((values < lo) | (values > hi))))


def norm_vec(values: np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    return np.linalg.norm(arr, axis=1) if arr.ndim == 2 else np.abs(arr.reshape(-1))


def get_scalar(arrays: dict[str, np.ndarray], name: str) -> np.ndarray | None:
    if name not in arrays:
        return None
    return np.asarray(arrays[name], dtype=float).reshape(-1)


def summarize_case(case_dir: Path) -> dict[str, Any]:
    metadata = read_metadata(case_dir)
    vtis = sorted((case_dir / "output").glob("case_VTK_P00_*.vti"), key=step_of)
    rows: list[dict[str, Any]] = []
    missing: set[str] = set()
    for vti in vtis:
        dims, raw = load_vti(vti)
        arrays = {name: crop(values, dims, metadata.get("physical_grid")) for name, values in raw.items()}
        required = [
            "PhaseField",
            "ReplayPhaseFromH",
            "B21HPostSum",
            "B21HPostOutOfBoundsFlag",
            "B21HeqMaxAbs",
            "B21FphiMaxAbs",
            "B21HeqVelocityMachShadow",
            "B22ForceOverRhoMag",
            "B22PhaseAdvSpeed",
            "B22FmuMag",
            "B22FpressureMag",
            "B22FsurfMag",
        ]
        missing.update(name for name in required if name not in arrays)
        row: dict[str, Any] = {"case": case_dir.name, "step": step_of(vti)}
        for name in required:
            arr = get_scalar(arrays, name)
            if arr is None:
                row[f"{name}_max"] = None
                row[f"{name}_min"] = None
                continue
            row[f"{name}_max"] = finite_max(arr)
            row[f"{name}_min"] = finite_min(arr)
        row["phase_oob_count"] = finite_count_oob(arrays["PhaseField"]) if "PhaseField" in arrays else None
        row["phase_from_h_oob_count"] = finite_count_oob(arrays["ReplayPhaseFromH"]) if "ReplayPhaseFromH" in arrays else None
        row["hpost_oob_count"] = int(np.count_nonzero(np.asarray(arrays["B21HPostOutOfBoundsFlag"], dtype=float) > 0.5)) if "B21HPostOutOfBoundsFlag" in arrays else None
        if "ReplayForceOverRho" in arrays:
            row["ReplayForceOverRho_norm_max"] = finite_max(norm_vec(arrays["ReplayForceOverRho"]))
        rows.append(row)

    first = {
        "phase_from_h_oob": first_step(rows, "phase_from_h_oob_count", 0),
        "hpost_oob": first_step(rows, "hpost_oob_count", 0),
        "hpost_gt_1": first_threshold(rows, "B21HPostSum_max", 1.0),
        "heq_gt_1": first_threshold(rows, "B21HeqMaxAbs_max", 1.0),
        "fphi_gt_1": first_threshold(rows, "B21FphiMaxAbs_max", 1.0),
        "mach_gt_1": first_threshold(rows, "B21HeqVelocityMachShadow_max", 1.0),
        "force_over_rho_gt_100": first_threshold(rows, "B22ForceOverRhoMag_max", 100.0),
        "force_over_rho_gt_1000": first_threshold(rows, "B22ForceOverRhoMag_max", 1000.0),
        "fmu_gt_1": first_threshold(rows, "B22FmuMag_max", 1.0),
    }
    if first["hpost_oob"] is not None and (
        first["force_over_rho_gt_100"] is None or first["hpost_oob"] <= first["force_over_rho_gt_100"]
    ):
        verdict = "b45_h_update_boundedness_fails_first"
    elif first["force_over_rho_gt_100"] is not None:
        verdict = "b45_force_velocity_precedes_phase_failure"
    elif first["phase_from_h_oob"] is None and not missing:
        verdict = "b45_phase_bounded_in_window"
    else:
        verdict = "b45_phase_boundedness_inconclusive"
    return {
        "case": case_dir.name,
        "vti_count": len(vtis),
        "missing_fields": sorted(missing),
        "first_events": first,
        "verdict": verdict,
        "frames": rows,
    }


def first_step(rows: list[dict[str, Any]], key: str, threshold: float) -> int | None:
    for row in rows:
        value = row.get(key)
        if isinstance(value, (int, float)) and value > threshold:
            return int(row["step"])
    return None


def first_threshold(rows: list[dict[str, Any]], key: str, threshold: float) -> int | None:
    for row in rows:
        value = row.get(key)
        if isinstance(value, (int, float)) and value > threshold:
            return int(row["step"])
    return None


def summarize(root: Path) -> dict[str, Any]:
    cases = [summarize_case(case_dir) for case_dir in case_dirs(root)]
    verdicts = {case["verdict"] for case in cases}
    if any(v in verdicts for v in ["b45_h_update_boundedness_fails_first", "b45_force_velocity_precedes_phase_failure"]):
        verdict = "b45_phase_gate_failed"
    elif verdicts == {"b45_phase_bounded_in_window"}:
        verdict = "b45_phase_gate_passed_window_only"
    else:
        verdict = "b45_phase_gate_inconclusive"
    return {
        "claim_limit": "B45 phase boundedness diagnostic only; no solver writeback or contact-angle claim",
        "root": str(root),
        "cases": cases,
        "verdict": verdict,
    }


def write_csv(path: Path, cases: list[dict[str, Any]]) -> None:
    fields = [
        "case",
        "step",
        "phase_oob_count",
        "phase_from_h_oob_count",
        "hpost_oob_count",
        "ReplayPhaseFromH_min",
        "ReplayPhaseFromH_max",
        "B21HPostSum_min",
        "B21HPostSum_max",
        "B21HeqMaxAbs_max",
        "B21FphiMaxAbs_max",
        "B21HeqVelocityMachShadow_max",
        "B22ForceOverRhoMag_max",
        "ReplayForceOverRho_norm_max",
        "B22PhaseAdvSpeed_max",
        "B22FmuMag_max",
        "B22FpressureMag_max",
        "B22FsurfMag_max",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for case in cases:
            for row in case["frames"]:
                writer.writerow({field: row.get(field) for field in fields})


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def write_md(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Stage14-B45 Phase Boundedness Gate",
        "",
        "Status: diagnostic-only h-update and phase boundedness audit.",
        "",
        f"Root: `{report['root']}`",
        f"Verdict: `{report['verdict']}`",
        "",
        "| case | verdict | first hpost OOB | first PhaseFromH OOB | first F/rho>100 | first F/rho>1000 | first Mach>1 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for case in report["cases"]:
        events = case["first_events"]
        lines.append(
            "| "
            + " | ".join(
                [
                    case["case"],
                    case["verdict"],
                    fmt(events.get("hpost_oob")),
                    fmt(events.get("phase_from_h_oob")),
                    fmt(events.get("force_over_rho_gt_100")),
                    fmt(events.get("force_over_rho_gt_1000")),
                    fmt(events.get("mach_gt_1")),
                ]
            )
            + " |"
        )
    lines.extend([
        "",
        "## Stop Rule",
        "",
        "If B45 fails, flat-wall contact-angle gates must not be interpreted physically, because the phase update is not bounded in the short diagnostic window.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--prefix", default="b45")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    report = summarize(args.root.resolve())
    (args.out_dir / f"{args.prefix}_phase_boundedness_summary.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    write_csv(args.out_dir / f"{args.prefix}_phase_boundedness_frames.csv", report["cases"])
    write_md(args.out_dir / f"{args.prefix}_phase_boundedness_summary.md", report)
    print(json.dumps({"verdict": report["verdict"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
