#!/usr/bin/env python3
"""Analyze Stage17B B2 curved shadow-only VTI outputs.

This script checks diagnostic-field health only. It does not measure or validate
contact angle.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

import numpy as np


FIELDS = [
    "PhaseField",
    "Rho",
    "U",
    "WallGhost",
    "AnalyticFlag",
    "LocalRadAngle",
    "PsiSolid",
    "PsiGradMag",
    "PsiNormal",
    "PsiWallGhost",
    "PsiThetaImplied",
    "PsiJaggedness",
    "PsiWriteAllowedFlag",
    "PsiNormalAmbiguityFlag",
    "NearWallForceMag",
    "NearWallGradPhiMag",
    "NearWallForceOverRhoShadow",
]


REQUIRED_FIELDS = [
    "PhaseField",
    "PsiSolid",
    "PsiGradMag",
    "PsiNormal",
    "PsiWallGhost",
    "PsiWriteAllowedFlag",
    "PsiNormalAmbiguityFlag",
    "NearWallForceMag",
    "NearWallGradPhiMag",
    "NearWallForceOverRhoShadow",
]


def step_of(path: Path) -> int:
    match = re.search(r"P00_(\d+)\.vti$", path.name)
    return int(match.group(1)) if match else -1


def load_vti(path: Path) -> tuple[tuple[int, int, int], dict[str, np.ndarray]]:
    import vtk  # type: ignore
    from vtk.util.numpy_support import vtk_to_numpy  # type: ignore

    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(str(path))
    reader.Update()
    data = reader.GetOutput()
    dims = tuple(int(v) - 1 for v in data.GetDimensions())
    cell_data = data.GetCellData()
    arrays: dict[str, np.ndarray] = {}
    for idx in range(cell_data.GetNumberOfArrays()):
        arr = cell_data.GetArray(idx)
        if arr is None:
            continue
        arrays[arr.GetName()] = vtk_to_numpy(arr).copy()
    return dims, arrays


def values_for_stats(arr: np.ndarray) -> np.ndarray:
    values = np.asarray(arr, dtype=float)
    if values.ndim == 2:
        return np.linalg.norm(values, axis=1)
    return values.ravel()


def finite_stats(arr: np.ndarray) -> dict[str, Any]:
    values = values_for_stats(arr)
    finite = np.isfinite(values)
    finite_values = values[finite]
    out: dict[str, Any] = {
        "present": True,
        "count": int(values.size),
        "finite": int(np.count_nonzero(finite)),
        "nonfinite": int(values.size - np.count_nonzero(finite)),
    }
    if finite_values.size == 0:
        out.update({"min": None, "max": None, "mean": None, "max_abs": None})
        return out
    out.update(
        {
            "min": float(np.min(finite_values)),
            "max": float(np.max(finite_values)),
            "mean": float(np.mean(finite_values)),
            "max_abs": float(np.max(np.abs(finite_values))),
        }
    )
    return out


def scalar_array(arrays: dict[str, np.ndarray], name: str) -> np.ndarray | None:
    arr = arrays.get(name)
    if arr is None:
        return None
    values = np.asarray(arr, dtype=float)
    if values.ndim == 2:
        return np.linalg.norm(values, axis=1)
    return values.ravel()


def analyze_frame(path: Path) -> dict[str, Any]:
    dims, arrays = load_vti(path)
    stats: dict[str, Any] = {}
    for field in FIELDS:
        arr = arrays.get(field)
        stats[field] = {"present": False} if arr is None else finite_stats(arr)

    write_flag = scalar_array(arrays, "PsiWriteAllowedFlag")
    ambiguity = scalar_array(arrays, "PsiNormalAmbiguityFlag")
    psi_grad = scalar_array(arrays, "PsiGradMag")
    near_force_rho = scalar_array(arrays, "NearWallForceOverRhoShadow")
    psi_wall_ghost = scalar_array(arrays, "PsiWallGhost")

    near_mask = np.zeros(0, dtype=bool)
    if psi_grad is not None:
        near_mask = np.isfinite(psi_grad) & (psi_grad > 1.0e-4)

    frame: dict[str, Any] = {
        "vti": str(path),
        "step": step_of(path),
        "dims": dims,
        "stats": stats,
        "missing_fields": [field for field in REQUIRED_FIELDS if not stats[field].get("present")],
        "near_band_cells": int(np.count_nonzero(near_mask)),
    }
    if write_flag is not None:
        flag_finite = np.isfinite(write_flag)
        frame["write_allowed_cells"] = int(np.count_nonzero(flag_finite & (write_flag > 0.5)))
        frame["write_allowed_fraction_near_band"] = (
            float(frame["write_allowed_cells"] / max(int(np.count_nonzero(near_mask)), 1))
            if near_mask.size
            else 0.0
        )
    if ambiguity is not None and near_mask.size:
        frame["ambiguity_fraction_near_band"] = float(
            np.count_nonzero(near_mask & np.isfinite(ambiguity) & (ambiguity > 0.5))
            / max(int(np.count_nonzero(near_mask)), 1)
        )
    if near_force_rho is not None:
        finite = near_force_rho[np.isfinite(near_force_rho)]
        frame["near_wall_force_over_rho_max_abs"] = (
            float(np.max(np.abs(finite))) if finite.size else None
        )
    if psi_wall_ghost is not None:
        finite = psi_wall_ghost[np.isfinite(psi_wall_ghost)]
        if finite.size:
            frame["psi_wall_ghost_below_0_cells"] = int(np.count_nonzero(finite < -1.0e-9))
            frame["psi_wall_ghost_above_1_cells"] = int(np.count_nonzero(finite > 1.0 + 1.0e-9))
    return frame


def analyze_case(case_dir: Path, force_over_rho_limit: float, expected_final_step: int) -> dict[str, Any]:
    vtis = sorted((case_dir / "output").glob("case_VTK_P00_*.vti"), key=step_of)
    frames = [analyze_frame(path) for path in vtis]
    failures: list[str] = []
    run_log = case_dir / "run.log"
    run_status = case_dir / "run.status"
    log_text = run_log.read_text(encoding="utf-8", errors="replace") if run_log.exists() else ""
    status_text = run_status.read_text(encoding="utf-8", errors="replace") if run_status.exists() else ""
    if not vtis:
        failures.append("no_vti_outputs")
    if "NaN" in log_text or "Nan value" in log_text or "Stopping due to Nan" in log_text:
        failures.append("runtime_log_nan_stop")
    if "RC=0" not in status_text:
        failures.append("missing_success_rc")
    if expected_final_step >= 0 and expected_final_step not in [frame["step"] for frame in frames]:
        failures.append(f"missing_expected_final_step_{expected_final_step}")
    for frame in frames:
        for field in REQUIRED_FIELDS:
            stats = frame["stats"].get(field, {})
            if not stats.get("present"):
                failures.append(f"missing_{field}_step_{frame['step']}")
            elif stats.get("nonfinite", 0) > 0:
                failures.append(f"nonfinite_{field}_step_{frame['step']}")
        if frame.get("write_allowed_cells", 0) <= 0:
            failures.append(f"no_write_allowed_shadow_cells_step_{frame['step']}")
        if frame.get("psi_wall_ghost_below_0_cells", 0) > 0:
            failures.append(f"psi_wall_ghost_below_zero_step_{frame['step']}")
        if frame.get("psi_wall_ghost_above_1_cells", 0) > 0:
            failures.append(f"psi_wall_ghost_above_one_step_{frame['step']}")
        force_shadow = frame.get("near_wall_force_over_rho_max_abs")
        if force_shadow is not None and force_shadow > force_over_rho_limit:
            failures.append(f"near_wall_force_over_rho_spike_step_{frame['step']}")

    return {
        "case": case_dir.name,
        "case_dir": str(case_dir),
        "n_vti": len(vtis),
        "steps": [frame["step"] for frame in frames],
        "frames": frames,
        "failures": sorted(set(failures)),
        "runtime_log_has_nan": ("NaN" in log_text or "Nan value" in log_text),
        "run_status": status_text.strip(),
        "expected_final_step": expected_final_step,
        "status": "PASS_SHADOW_DIAGNOSTICS" if not failures else "FAIL",
        "claim_limit": "diagnostic-field health only; not contact-angle validation",
    }


def flatten_frames(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in summary["cases"]:
        for frame in case["frames"]:
            row: dict[str, Any] = {
                "case": case["case"],
                "step": frame["step"],
                "near_band_cells": frame.get("near_band_cells"),
                "write_allowed_cells": frame.get("write_allowed_cells"),
                "write_allowed_fraction_near_band": frame.get("write_allowed_fraction_near_band"),
                "ambiguity_fraction_near_band": frame.get("ambiguity_fraction_near_band"),
                "near_wall_force_over_rho_max_abs": frame.get("near_wall_force_over_rho_max_abs"),
                "psi_wall_ghost_below_0_cells": frame.get("psi_wall_ghost_below_0_cells"),
                "psi_wall_ghost_above_1_cells": frame.get("psi_wall_ghost_above_1_cells"),
            }
            for field in REQUIRED_FIELDS:
                stats = frame["stats"].get(field, {})
                row[f"{field}_present"] = stats.get("present")
                row[f"{field}_nonfinite"] = stats.get("nonfinite")
                row[f"{field}_min"] = stats.get("min")
                row[f"{field}_max"] = stats.get("max")
                row[f"{field}_max_abs"] = stats.get("max_abs")
            rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="run root containing case directories")
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-csv", type=Path)
    parser.add_argument("--force-over-rho-limit", type=float, default=1.0e3)
    parser.add_argument("--expected-final-step", type=int, default=1000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    case_dirs = sorted(
        path for path in args.root.iterdir() if path.is_dir() and (path / "case.xml").exists()
    )
    cases = [
        analyze_case(path, args.force_over_rho_limit, args.expected_final_step)
        for path in case_dirs
    ]
    failures = {case["case"]: case["failures"] for case in cases if case["failures"]}
    summary = {
        "root": str(args.root),
        "cases": cases,
        "status": "PASS_STAGE17B_B2_SHADOW_DIAGNOSTICS" if not failures else "FAIL",
        "failures": failures,
        "claim_limit": "B2 shadow diagnostics only; no contact-angle validation",
    }
    text = json.dumps(summary, indent=2, sort_keys=True)
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(text, encoding="utf-8")
    if args.out_csv:
        write_csv(args.out_csv, flatten_frames(summary))
    print(text)
    return 0 if summary["status"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
