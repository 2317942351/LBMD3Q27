#!/usr/bin/env python3
"""Analyze Stage17B-B5 WallGhost consumption probe outputs.

This script checks producer-consumer diagnostics only. It does not validate a
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
    "WallGhost",
    "PsiWallGhost",
    "PsiWriteAppliedFlag",
    "WettingPathId",
    "PhaseStencilGhostUseCount",
    "ReplayPhaseConsumed",
    "ReplayPhaseFromH",
    "ReplayLapPhi",
    "ReplayMu",
    "ReplayGradPhi",
    "ReplayFphiSum",
    "ReplayFphiMaxAbs",
    "ReplayTmp1",
    "ReplayHPreSum",
    "ReplayHPostSum",
    "B5SignedDistance",
    "B5NearWallBandFlag",
    "B5ContactLineBandFlag",
    "B5WallGhostConsumedFlag",
    "B5GhostUseCount",
    "B5WallGhostMinusCenter",
    "B5WallGhostMinusFluidProbe",
    "B5WallGhostClampHitNeighbor",
    "B5GradPhiNormal",
    "B5GradPhiTangentialMag",
    "B5FphiSum",
    "B5FphiNormalProxy",
    "B5PhaseFromHDelta",
    "B5ExpectedResponseSign",
    "B5SignalSignOK",
]

REQUIRED_FIELDS = [
    "PhaseField",
    "B5NearWallBandFlag",
    "B5ContactLineBandFlag",
    "B5WallGhostConsumedFlag",
    "B5GhostUseCount",
    "B5WallGhostMinusCenter",
    "B5GradPhiNormal",
    "B5PhaseFromHDelta",
    "B5SignalSignOK",
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


def scalar(arrays: dict[str, np.ndarray], name: str) -> np.ndarray | None:
    arr = arrays.get(name)
    if arr is None:
        return None
    values = np.asarray(arr, dtype=float)
    if values.ndim == 2:
        return np.linalg.norm(values, axis=1)
    return values.ravel()


def finite_stats(values: np.ndarray, mask: np.ndarray | None = None) -> dict[str, Any]:
    vals = np.asarray(values, dtype=float).ravel()
    if mask is not None:
        vals = vals[np.asarray(mask, dtype=bool).ravel()]
    finite = np.isfinite(vals)
    out: dict[str, Any] = {
        "count": int(vals.size),
        "finite": int(np.count_nonzero(finite)),
        "nonfinite": int(vals.size - np.count_nonzero(finite)),
    }
    vals = vals[finite]
    if vals.size == 0:
        out.update({"min": None, "max": None, "mean": None, "median": None, "max_abs": None})
        return out
    out.update(
        {
            "min": float(np.min(vals)),
            "max": float(np.max(vals)),
            "mean": float(np.mean(vals)),
            "median": float(np.median(vals)),
            "max_abs": float(np.max(np.abs(vals))),
        }
    )
    return out


def signed_fraction(values: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    vals = np.asarray(values, dtype=float).ravel()[mask]
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return {"positive_fraction": None, "negative_fraction": None, "zero_fraction": None}
    eps = 1.0e-12
    return {
        "positive_fraction": float(np.count_nonzero(vals > eps) / vals.size),
        "negative_fraction": float(np.count_nonzero(vals < -eps) / vals.size),
        "zero_fraction": float(np.count_nonzero(np.abs(vals) <= eps) / vals.size),
    }


def analyze_frame(path: Path) -> dict[str, Any]:
    dims, arrays = load_vti(path)
    missing = [field for field in REQUIRED_FIELDS if field not in arrays]
    near = scalar(arrays, "B5NearWallBandFlag")
    contact = scalar(arrays, "B5ContactLineBandFlag")
    consumed = scalar(arrays, "B5WallGhostConsumedFlag")
    ghost_use = scalar(arrays, "B5GhostUseCount")
    signal_ok = scalar(arrays, "B5SignalSignOK")
    expected_sign = scalar(arrays, "B5ExpectedResponseSign")
    phase = scalar(arrays, "PhaseField")
    near_mask = np.isfinite(near) & (near > 0.5) if near is not None else np.zeros(0, dtype=bool)
    contact_mask = (
        near_mask & np.isfinite(contact) & (contact > 0.5)
        if contact is not None and near_mask.size
        else np.zeros_like(near_mask)
    )
    consumed_mask = (
        contact_mask & np.isfinite(consumed) & (consumed > 0.5)
        if consumed is not None and contact_mask.size
        else np.zeros_like(contact_mask)
    )

    out: dict[str, Any] = {
        "case": path.parents[1].name,
        "step": step_of(path),
        "vti": str(path),
        "dims": dims,
        "missing_fields": missing,
        "near_wall_cells": int(np.count_nonzero(near_mask)),
        "contact_line_cells": int(np.count_nonzero(contact_mask)),
        "consumed_contact_cells": int(np.count_nonzero(consumed_mask)),
    }
    if contact_mask.size:
        out["consumed_fraction_contact"] = float(
            np.count_nonzero(consumed_mask) / max(np.count_nonzero(contact_mask), 1)
        )
    if ghost_use is not None:
        out["ghost_use_count_contact"] = finite_stats(ghost_use, contact_mask)
    if signal_ok is not None and consumed_mask.size:
        vals = signal_ok[consumed_mask]
        finite = np.isfinite(vals)
        vals = vals[finite]
        out["signal_ok_positive_cells"] = int(np.count_nonzero(vals > 0.5))
        out["signal_ok_negative_cells"] = int(np.count_nonzero(vals < -0.5))
        out["signal_ok_fraction"] = (
            float(np.count_nonzero(vals > 0.5) / vals.size) if vals.size else None
        )
    if expected_sign is not None and consumed_mask.size:
        vals = expected_sign[consumed_mask]
        vals = vals[np.isfinite(vals)]
        out["expected_response_sign_max_abs"] = (
            float(np.max(np.abs(vals))) if vals.size else None
        )
        out["expected_response_sign_mean"] = float(np.mean(vals)) if vals.size else None
    for field in [
        "B5WallGhostMinusCenter",
        "B5WallGhostMinusFluidProbe",
        "B5GradPhiNormal",
        "B5GradPhiTangentialMag",
        "B5FphiSum",
        "B5FphiNormalProxy",
        "B5PhaseFromHDelta",
        "ReplayLapPhi",
        "ReplayMu",
        "ReplayFphiSum",
        "ReplayFphiMaxAbs",
        "ReplayTmp1",
    ]:
        values = scalar(arrays, field)
        if values is not None and contact_mask.size:
            out[f"{field}_contact"] = finite_stats(values, contact_mask)
            out[f"{field}_sign_contact"] = signed_fraction(values, contact_mask)
    if phase is not None:
        out["phase_nonfinite"] = int(phase.size - np.count_nonzero(np.isfinite(phase)))
        out["phase_min"] = float(np.nanmin(phase))
        out["phase_max"] = float(np.nanmax(phase))
    return out


def analyze_case(case_dir: Path, expected_final_step: int) -> dict[str, Any]:
    vtis = sorted((case_dir / "output").glob("case_VTK_P00_*.vti"), key=step_of)
    frames = [analyze_frame(path) for path in vtis]
    failures: list[str] = []
    if not frames:
        failures.append("no_vti")
    if frames and expected_final_step >= 0 and frames[-1]["step"] != expected_final_step:
        failures.append(f"final_step_{frames[-1]['step']}_expected_{expected_final_step}")
    for frame in frames:
        if frame["missing_fields"]:
            failures.append(f"missing_fields_step_{frame['step']}")
        if frame.get("phase_nonfinite", 0) > 0:
            failures.append(f"phase_nonfinite_step_{frame['step']}")
    final = frames[-1] if frames else {}
    if final:
        if final.get("contact_line_cells", 0) <= 0:
            failures.append("no_contact_line_cells_final")
        if final.get("consumed_fraction_contact", 0.0) <= 0.25:
            failures.append("low_wallghost_consumption_final")
        expected_nonzero = final.get("expected_response_sign_max_abs")
        if (
            expected_nonzero is not None
            and expected_nonzero > 0.5
            and final.get("signal_ok_fraction") is not None
            and final["signal_ok_fraction"] < 0.5
        ):
            failures.append("wallghost_signal_sign_opposite_or_mixed")
    return {
        "case": case_dir.name,
        "frames": frames,
        "frame_count": len(frames),
        "final": final,
        "failures": sorted(set(failures)),
        "status": "pass" if not failures else "fail",
    }


def flatten_frame(case: dict[str, Any], frame: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "case": case["case"],
        "status": case["status"],
        "step": frame.get("step"),
        "near_wall_cells": frame.get("near_wall_cells"),
        "contact_line_cells": frame.get("contact_line_cells"),
        "consumed_contact_cells": frame.get("consumed_contact_cells"),
        "consumed_fraction_contact": frame.get("consumed_fraction_contact"),
        "signal_ok_fraction": frame.get("signal_ok_fraction"),
        "expected_response_sign_mean": frame.get("expected_response_sign_mean"),
        "expected_response_sign_max_abs": frame.get("expected_response_sign_max_abs"),
        "phase_min": frame.get("phase_min"),
        "phase_max": frame.get("phase_max"),
        "phase_nonfinite": frame.get("phase_nonfinite"),
    }
    for field in [
        "B5WallGhostMinusCenter",
        "B5GradPhiNormal",
        "B5FphiNormalProxy",
        "B5PhaseFromHDelta",
        "ReplayMu",
        "ReplayLapPhi",
    ]:
        stats = frame.get(f"{field}_contact") or {}
        signs = frame.get(f"{field}_sign_contact") or {}
        row[f"{field}_mean"] = stats.get("mean")
        row[f"{field}_max_abs"] = stats.get("max_abs")
        row[f"{field}_positive_fraction"] = signs.get("positive_fraction")
        row[f"{field}_negative_fraction"] = signs.get("negative_fraction")
    return row


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-csv", type=Path)
    parser.add_argument("--expected-final-step", type=int, default=-1)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = [
        analyze_case(case_dir, args.expected_final_step)
        for case_dir in sorted(args.root.iterdir())
        if case_dir.is_dir() and (case_dir / "case.xml").exists()
    ]
    rows = [flatten_frame(case, frame) for case in cases for frame in case["frames"]]
    failures = [case["case"] for case in cases if case["status"] != "pass"]
    summary = {
        "status": "PASS_STAGE17B_B5_CONSUMPTION_PROBE" if not failures and cases else "FAIL",
        "claim_limit": "WallGhost consumption diagnostics only; not contact-angle validation",
        "root": str(args.root),
        "case_count": len(cases),
        "failures": failures,
        "cases": cases,
    }
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    if args.out_csv:
        args.out_csv.parent.mkdir(parents=True, exist_ok=True)
        with args.out_csv.open("w", newline="", encoding="utf-8") as handle:
            fieldnames = sorted({key for row in rows for key in row})
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
