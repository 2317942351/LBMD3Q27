#!/usr/bin/env python3
"""Probe TCLB VTI fields around the first unstable nodes.

This is a diagnostic helper for S2/S3 runtime semantics. It reads one or more
VTI files, reports selected field ranges, and prints the top nodes by absolute
value or nonfinite status in a target array together with co-located values from
other arrays.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np


DEFAULT_FIELDS = [
    "PhaseField",
    "Rho",
    "U",
    "P",
    "GradPhi",
    "WallGhost",
    "WallGhostRaw",
    "WallGhostClamped",
    "WallGhostClampHit",
    "WettingPathId",
    "AnalyticFlag",
    "IsItBoundary",
    "ReplayPhaseConsumed",
    "ReplayPhaseFromH",
    "ReplayLapPhi",
    "ReplayMu",
    "ReplayGradPhi",
    "ReplayFsurf",
    "ReplayFpressure",
    "ReplayFmu",
    "ReplayFtotal",
    "ReplayRho",
    "ReplayTau",
    "ReplayPressureMoment",
    "ReplayUPreForce",
    "ReplayUPostForce",
    "ReplayPhaseAdvVelocity",
    "ReplayForceOverRho",
    "ReplayFmuIter1",
    "ReplayFtotalIter1",
    "ReplayUPostIter1",
    "ReplayNormal",
    "ReplayStressXX",
    "ReplayStressXY",
    "ReplayStressXZ",
    "ReplayStressYY",
    "ReplayStressYZ",
    "ReplayStressZZ",
    "ReplayFphiSum",
    "ReplayFphiMaxAbs",
    "ReplayTmp1",
    "PhaseStencilGhostUseCount",
    "PhaseStencilFallbackCount",
    "PhaseStencilMidpointFallbackCount",
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
        arrays[arr.GetName()] = vtk_to_numpy(arr)
    return dims, arrays


def finite_stats(arr: np.ndarray) -> dict[str, Any]:
    values = np.asarray(arr, dtype=float)
    finite = np.isfinite(values)
    finite_values = values[finite]
    if finite_values.size == 0:
        return {
            "size": int(values.size),
            "finite": 0,
            "nonfinite": int(values.size),
            "min": None,
            "max": None,
            "max_abs": None,
            "mean": None,
        }
    if values.ndim == 2:
        mag = np.linalg.norm(values, axis=1)
        finite_mag = mag[np.isfinite(mag)]
        max_abs = float(np.max(finite_mag)) if finite_mag.size else None
    else:
        max_abs = float(np.max(np.abs(finite_values)))
    return {
        "size": int(values.size),
        "finite": int(np.count_nonzero(finite)),
        "nonfinite": int(values.size - np.count_nonzero(finite)),
        "min": float(np.min(finite_values)),
        "max": float(np.max(finite_values)),
        "max_abs": max_abs,
        "mean": float(np.mean(finite_values)),
    }


def magnitude(arr: np.ndarray) -> np.ndarray:
    values = np.asarray(arr, dtype=float)
    if values.ndim == 2:
        return np.linalg.norm(values, axis=1)
    return np.abs(values)


def index_to_ijk(index: int, dims: tuple[int, int, int]) -> tuple[int, int, int]:
    nx, ny, _nz = dims
    i = index % nx
    j = (index // nx) % ny
    k = index // (nx * ny)
    return i, j, k


def scalar_at(arr: np.ndarray, index: int) -> Any:
    value = arr[index]
    if np.ndim(value) == 0:
        v = float(value)
        if math.isfinite(v):
            return v
        return str(v)
    out = []
    for item in np.asarray(value).ravel():
        v = float(item)
        out.append(v if math.isfinite(v) else str(v))
    return out


def top_indices(target: np.ndarray, count: int) -> list[int]:
    mag = magnitude(target)
    bad = np.flatnonzero(~np.isfinite(mag))
    if bad.size:
        return [int(v) for v in bad[:count]]
    finite_mag = np.where(np.isfinite(mag), mag, -np.inf)
    if finite_mag.size <= count:
        order = np.argsort(-finite_mag)
    else:
        part = np.argpartition(-finite_mag, count - 1)[:count]
        order = part[np.argsort(-finite_mag[part])]
    return [int(v) for v in order]


def probe_file(path: Path, args: argparse.Namespace) -> dict[str, Any]:
    dims, arrays = load_vti(path)
    fields = [field.strip() for field in args.fields.split(",") if field.strip()]
    report: dict[str, Any] = {
        "path": str(path),
        "step": step_of(path),
        "dims": dims,
        "stats": {},
        "top_nodes": [],
    }
    for field in fields:
        if field in arrays:
            report["stats"][field] = finite_stats(arrays[field])
    target = arrays.get(args.target)
    if target is None:
        report["target_missing"] = args.target
        return report
    for index in top_indices(target, args.top):
        node: dict[str, Any] = {
            "flat_index": index,
            "ijk": index_to_ijk(index, dims),
            args.target: scalar_at(target, index),
        }
        for field in fields:
            if field == args.target or field not in arrays:
                continue
            node[field] = scalar_at(arrays[field], index)
        report["top_nodes"].append(node)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--target", default="PhaseField")
    parser.add_argument("--fields", default=",".join(DEFAULT_FIELDS))
    parser.add_argument("--top", type=int, default=8)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    reports = [probe_file(path, args) for path in args.paths]
    if args.json:
        print(json.dumps(reports, indent=2, sort_keys=True))
        return 0
    for report in reports:
        print(f"FILE {report['path']} step={report['step']} dims={report['dims']}")
        for field, stats in report["stats"].items():
            print(
                f"  {field:34s} nf={stats['nonfinite']:8d} "
                f"min={stats['min']} max={stats['max']} max_abs={stats['max_abs']}"
            )
        print("  TOP_NODES")
        for node in report["top_nodes"]:
            print("   ", json.dumps(node, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
