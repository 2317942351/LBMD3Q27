#!/usr/bin/env python3
"""Audit PhaseField overshoot locations for PRE 2025 sphere VTI frames."""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import re

import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy


STEP_RE = re.compile(r"_(\d{8})\.vti$")


def step_of(path: pathlib.Path) -> int:
    match = STEP_RE.search(path.name)
    return int(match.group(1)) if match else -1


def read_vti(path: pathlib.Path) -> tuple[tuple[int, int, int], dict[str, np.ndarray]]:
    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(str(path))
    reader.Update()
    image = reader.GetOutput()
    dims = tuple(int(value) - 1 for value in image.GetDimensions())
    cell_data = image.GetCellData()
    arrays: dict[str, np.ndarray] = {}
    for i in range(cell_data.GetNumberOfArrays()):
        arr = cell_data.GetArray(i)
        if arr is not None:
            arrays[arr.GetName() or f"array{i}"] = vtk_to_numpy(arr)
    return dims, arrays


def scalar(values: np.ndarray) -> np.ndarray:
    out = np.asarray(values, dtype=float)
    if out.ndim > 1:
        out = out[:, 0]
    return out


def reshape_cell(values: np.ndarray, dims: tuple[int, int, int]) -> np.ndarray:
    nx, ny, nz = dims
    return scalar(values).reshape((nz, ny, nx)).transpose(2, 1, 0)


def masked_argmax(values: np.ndarray, mask: np.ndarray) -> tuple[float, list[int]]:
    if not np.any(mask):
        return math.nan, [-1, -1, -1]
    masked = np.where(mask, values, -np.inf)
    idx = np.unravel_index(np.nanargmax(masked), values.shape)
    return float(values[idx]), [int(v) for v in idx]


def masked_minmax(values: np.ndarray, mask: np.ndarray) -> tuple[float, float]:
    if not np.any(mask):
        return math.nan, math.nan
    sub = values[mask]
    return float(np.nanmin(sub)), float(np.nanmax(sub))


def audit_frame(path: pathlib.Path) -> dict[str, object]:
    dims, arrays = read_vti(path)
    phi = reshape_cell(arrays["PhaseField"], dims)
    boundary = reshape_cell(arrays["BOUNDARY"], dims) if "BOUNDARY" in arrays else np.zeros_like(phi)
    is_boundary = np.isfinite(boundary) & (boundary != 0.0)
    fluid = ~is_boundary
    finite = np.isfinite(phi)
    over1 = phi > 1.0 + 1.0e-8
    under0 = phi < -1.0e-8

    all_idx = np.unravel_index(np.nanargmax(phi), phi.shape)
    fluid_max, fluid_idx = masked_argmax(phi, fluid)
    boundary_max, boundary_idx = masked_argmax(phi, is_boundary)
    fluid_min, _ = masked_minmax(phi, fluid)
    boundary_min, _ = masked_minmax(phi, is_boundary)

    nx, ny, nz = dims
    x = np.arange(nx)[:, None, None] + 0.5
    y = np.arange(ny)[None, :, None] + 0.5
    z = np.arange(nz)[None, None, :] + 0.5
    rsolid = np.sqrt((x - 40.0) ** 2 + (y - 40.0) ** 2 + (z - 24.0) ** 2)
    near_solid = np.abs(rsolid - 24.0) <= 3.0
    near_contact = near_solid & (phi > 1.0e-3)

    near_solid_min, near_solid_max = masked_minmax(phi, near_solid)
    near_contact_min, near_contact_max = masked_minmax(phi, near_contact)

    return {
        "step": step_of(path),
        "file": str(path),
        "dims": list(dims),
        "phi_min_all": float(np.nanmin(phi)),
        "phi_max_all": float(phi[all_idx]),
        "phi_max_all_xyz": [int(v) for v in all_idx],
        "phi_max_all_boundary": bool(is_boundary[all_idx]),
        "phi_min_fluid": fluid_min,
        "phi_max_fluid": fluid_max,
        "phi_max_fluid_xyz": fluid_idx,
        "phi_min_boundary": boundary_min,
        "phi_max_boundary": boundary_max,
        "phi_max_boundary_xyz": boundary_idx,
        "over1_all_count": int(np.count_nonzero(over1 & finite)),
        "over1_fluid_count": int(np.count_nonzero(over1 & fluid)),
        "over1_boundary_count": int(np.count_nonzero(over1 & is_boundary)),
        "under0_all_count": int(np.count_nonzero(under0 & finite)),
        "under0_fluid_count": int(np.count_nonzero(under0 & fluid)),
        "under0_boundary_count": int(np.count_nonzero(under0 & is_boundary)),
        "fluid_sum": float(np.nansum(phi[fluid])),
        "boundary_sum": float(np.nansum(phi[is_boundary])),
        "near_solid_phi_min": near_solid_min,
        "near_solid_phi_max": near_solid_max,
        "near_solid_over1_count": int(np.count_nonzero(over1 & near_solid)),
        "near_contact_phi_min": near_contact_min,
        "near_contact_phi_max": near_contact_max,
        "near_contact_over1_count": int(np.count_nonzero(over1 & near_contact)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-root", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path)
    args = parser.parse_args()

    frames = sorted((args.case_root / "output").glob("*_VTK_P00_*.vti"), key=step_of)
    rows = [audit_frame(path) for path in frames]
    text = json.dumps(rows, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
