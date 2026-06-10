#!/usr/bin/env python3
"""Context audit for boundary PhaseField overshoot in PRE 2025 sphere frames."""

from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib
import re
from collections import Counter
from typing import Any

import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy


STEP_RE = re.compile(r"_(\d{8})\.vti$")
NEIGHBOR_6 = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
NEIGHBOR_26 = [
    (dx, dy, dz)
    for dx in (-1, 0, 1)
    for dy in (-1, 0, 1)
    for dz in (-1, 0, 1)
    if (dx, dy, dz) != (0, 0, 0)
]


def step_of(path: pathlib.Path) -> int:
    match = STEP_RE.search(path.name)
    return int(match.group(1)) if match else -1


def read_vti(path: pathlib.Path) -> tuple[tuple[int, int, int], tuple[float, ...], tuple[float, ...], tuple[int, ...], dict[str, np.ndarray]]:
    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(str(path))
    reader.Update()
    image = reader.GetOutput()
    dims = tuple(int(value) - 1 for value in image.GetDimensions())
    origin = tuple(float(value) for value in image.GetOrigin())
    spacing = tuple(float(value) for value in image.GetSpacing())
    extent = tuple(int(value) for value in image.GetExtent())
    cell_data = image.GetCellData()
    arrays: dict[str, np.ndarray] = {}
    for i in range(cell_data.GetNumberOfArrays()):
        arr = cell_data.GetArray(i)
        if arr is not None:
            arrays[arr.GetName() or f"array{i}"] = vtk_to_numpy(arr)
    return dims, origin, spacing, extent, arrays


def scalar(values: np.ndarray) -> np.ndarray:
    out = np.asarray(values, dtype=float)
    if out.ndim > 1:
        out = out[:, 0]
    return out


def reshape_scalar(values: np.ndarray, dims: tuple[int, int, int]) -> np.ndarray:
    nx, ny, nz = dims
    return scalar(values).reshape((nz, ny, nx)).transpose(2, 1, 0)


def reshape_vector(values: np.ndarray, dims: tuple[int, int, int]) -> np.ndarray:
    nx, ny, nz = dims
    out = np.asarray(values, dtype=float)
    if out.ndim == 1:
        out = out[:, None]
    comps = min(out.shape[1], 3)
    vec = np.zeros((out.shape[0], 3), dtype=float)
    vec[:, :comps] = out[:, :comps]
    return vec.reshape((nz, ny, nx, 3)).transpose(2, 1, 0, 3)


def finite_minmax(values: np.ndarray) -> tuple[float, float]:
    if values.size == 0:
        return math.nan, math.nan
    return float(np.nanmin(values)), float(np.nanmax(values))


def unique_counts(values: np.ndarray, limit: int = 12) -> list[dict[str, Any]]:
    rounded = np.round(values[np.isfinite(values)], 6)
    counts = Counter(float(v) for v in rounded.ravel())
    return [{"value": value, "count": count} for value, count in counts.most_common(limit)]


def shifted_fluid_context(phi: np.ndarray, fluid: np.ndarray, mask: np.ndarray, offsets: list[tuple[int, int, int]]) -> dict[str, Any]:
    max_neighbor_phi = np.full(phi.shape, -np.inf, dtype=float)
    fluid_neighbor_count = np.zeros(phi.shape, dtype=np.int16)
    nx, ny, nz = phi.shape

    for dx, dy, dz in offsets:
        src_x0 = max(0, -dx)
        src_x1 = min(nx, nx - dx)
        src_y0 = max(0, -dy)
        src_y1 = min(ny, ny - dy)
        src_z0 = max(0, -dz)
        src_z1 = min(nz, nz - dz)
        dst_x0 = src_x0 + dx
        dst_x1 = src_x1 + dx
        dst_y0 = src_y0 + dy
        dst_y1 = src_y1 + dy
        dst_z0 = src_z0 + dz
        dst_z1 = src_z1 + dz

        src_fluid = fluid[src_x0:src_x1, src_y0:src_y1, src_z0:src_z1]
        src_phi = phi[src_x0:src_x1, src_y0:src_y1, src_z0:src_z1]
        dst_slice = (slice(dst_x0, dst_x1), slice(dst_y0, dst_y1), slice(dst_z0, dst_z1))
        fluid_neighbor_count[dst_slice] += src_fluid.astype(np.int16)
        max_neighbor_phi[dst_slice] = np.maximum(
            max_neighbor_phi[dst_slice],
            np.where(src_fluid, src_phi, -np.inf),
        )

    sub = mask
    values = max_neighbor_phi[sub]
    counts = fluid_neighbor_count[sub]
    finite_values = values[np.isfinite(values)]
    return {
        "with_fluid_neighbor_count": int(np.count_nonzero(counts > 0)),
        "max_neighbor_phi_min": float(np.nanmin(finite_values)) if finite_values.size else math.nan,
        "max_neighbor_phi_max": float(np.nanmax(finite_values)) if finite_values.size else math.nan,
        "max_neighbor_phi_mean": float(np.nanmean(finite_values)) if finite_values.size else math.nan,
        "neighbor_phi_gt_1e-3_count": int(np.count_nonzero(values > 1.0e-3)),
        "neighbor_phi_gt_0p05_count": int(np.count_nonzero(values > 0.05)),
        "neighbor_phi_gt_0p5_count": int(np.count_nonzero(values > 0.5)),
        "neighbor_phi_0p05_to_0p95_count": int(np.count_nonzero((values > 0.05) & (values < 0.95))),
        "fluid_neighbor_count_max": int(np.max(counts)) if counts.size else 0,
    }


def sample_top_cells(
    phi: np.ndarray,
    mask: np.ndarray,
    boundary: np.ndarray,
    is_boundary_q: np.ndarray | None,
    normal: np.ndarray | None,
    gradphi: np.ndarray | None,
    rsolid: np.ndarray,
    fluid_context_26: dict[str, np.ndarray] | None,
    limit: int,
) -> list[dict[str, Any]]:
    coords = np.argwhere(mask)
    if coords.size == 0:
        return []
    values = phi[mask]
    order = np.argsort(values)[::-1][:limit]
    samples: list[dict[str, Any]] = []
    for idx in order:
        x, y, z = (int(v) for v in coords[idx])
        row: dict[str, Any] = {
            "xyz": [x, y, z],
            "phi": float(phi[x, y, z]),
            "boundary": float(boundary[x, y, z]),
            "solid_radius_distance": float(rsolid[x, y, z] - 24.0),
            "is_outer_index_face": bool(x in (0, phi.shape[0] - 1) or y in (0, phi.shape[1] - 1) or z in (0, phi.shape[2] - 1)),
        }
        if is_boundary_q is not None:
            row["IsItBoundary"] = float(is_boundary_q[x, y, z])
        if normal is not None:
            row["Normal"] = [float(v) for v in normal[x, y, z, :]]
        if gradphi is not None:
            g = gradphi[x, y, z, :]
            row["GradPhi"] = [float(v) for v in g]
            row["GradPhi_norm"] = float(np.linalg.norm(g))
        if fluid_context_26 is not None:
            row["max_26_neighbor_fluid_phi"] = float(fluid_context_26["max_neighbor_phi"][x, y, z])
            row["fluid_26_neighbor_count"] = int(fluid_context_26["fluid_neighbor_count"][x, y, z])
        samples.append(row)
    return samples


def full_neighbor_context_arrays(phi: np.ndarray, fluid: np.ndarray, offsets: list[tuple[int, int, int]]) -> dict[str, np.ndarray]:
    max_neighbor_phi = np.full(phi.shape, -np.inf, dtype=float)
    fluid_neighbor_count = np.zeros(phi.shape, dtype=np.int16)
    nx, ny, nz = phi.shape
    for dx, dy, dz in offsets:
        src_x0 = max(0, -dx)
        src_x1 = min(nx, nx - dx)
        src_y0 = max(0, -dy)
        src_y1 = min(ny, ny - dy)
        src_z0 = max(0, -dz)
        src_z1 = min(nz, nz - dz)
        dst_x0 = src_x0 + dx
        dst_x1 = src_x1 + dx
        dst_y0 = src_y0 + dy
        dst_y1 = src_y1 + dy
        dst_z0 = src_z0 + dz
        dst_z1 = src_z1 + dz
        src_fluid = fluid[src_x0:src_x1, src_y0:src_y1, src_z0:src_z1]
        src_phi = phi[src_x0:src_x1, src_y0:src_y1, src_z0:src_z1]
        dst = (slice(dst_x0, dst_x1), slice(dst_y0, dst_y1), slice(dst_z0, dst_z1))
        fluid_neighbor_count[dst] += src_fluid.astype(np.int16)
        max_neighbor_phi[dst] = np.maximum(max_neighbor_phi[dst], np.where(src_fluid, src_phi, -np.inf))
    return {"max_neighbor_phi": max_neighbor_phi, "fluid_neighbor_count": fluid_neighbor_count}


def audit_frame(path: pathlib.Path, sample_limit: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    dims, origin, spacing, extent, arrays = read_vti(path)
    phi = reshape_scalar(arrays["PhaseField"], dims)
    boundary = reshape_scalar(arrays["BOUNDARY"], dims) if "BOUNDARY" in arrays else np.zeros_like(phi)
    is_boundary = np.isfinite(boundary) & (boundary != 0.0)
    fluid = ~is_boundary
    over1_boundary = is_boundary & (phi > 1.0 + 1.0e-8)

    is_boundary_q = reshape_scalar(arrays["IsItBoundary"], dims) if "IsItBoundary" in arrays else None
    normal = reshape_vector(arrays["Normal"], dims) if "Normal" in arrays else None
    gradphi = reshape_vector(arrays["GradPhi"], dims) if "GradPhi" in arrays else None

    nx, ny, nz = dims
    x = np.arange(nx)[:, None, None] + 0.5
    y = np.arange(ny)[None, :, None] + 0.5
    z = np.arange(nz)[None, None, :] + 0.5
    rsolid = np.sqrt((x - 40.0) ** 2 + (y - 40.0) ** 2 + (z - 24.0) ** 2)

    solid_core = rsolid < 21.0
    solid_shell = np.abs(rsolid - 24.0) <= 3.0
    solid_near = rsolid < 30.0
    outside_solid_near = (rsolid >= 24.0) & (rsolid < 30.0)
    outside_solid_far = rsolid >= 30.0
    index_outer_face = np.zeros(phi.shape, dtype=bool)
    index_outer_face[0, :, :] = True
    index_outer_face[-1, :, :] = True
    index_outer_face[:, 0, :] = True
    index_outer_face[:, -1, :] = True
    index_outer_face[:, :, 0] = True
    index_outer_face[:, :, -1] = True

    ctx6 = shifted_fluid_context(phi, fluid, over1_boundary, NEIGHBOR_6)
    ctx26 = shifted_fluid_context(phi, fluid, over1_boundary, NEIGHBOR_26)
    ctx_arrays_26 = full_neighbor_context_arrays(phi, fluid, NEIGHBOR_26)

    def count(mask: np.ndarray) -> int:
        return int(np.count_nonzero(over1_boundary & mask))

    phi_over1_values = phi[over1_boundary]
    phi_boundary_values = phi[is_boundary]
    row: dict[str, Any] = {
        "step": step_of(path),
        "file": str(path),
        "dims": list(dims),
        "origin": list(origin),
        "spacing": list(spacing),
        "extent": list(extent),
        "array_names": sorted(arrays.keys()),
        "boundary_unique_top": unique_counts(boundary),
        "IsItBoundary_unique_top": unique_counts(is_boundary_q) if is_boundary_q is not None else [],
        "boundary_count": int(np.count_nonzero(is_boundary)),
        "fluid_count": int(np.count_nonzero(fluid)),
        "boundary_phi_min": finite_minmax(phi_boundary_values)[0],
        "boundary_phi_max": finite_minmax(phi_boundary_values)[1],
        "fluid_phi_min": finite_minmax(phi[fluid])[0],
        "fluid_phi_max": finite_minmax(phi[fluid])[1],
        "boundary_over1_count": int(np.count_nonzero(over1_boundary)),
        "boundary_over1_phi_min": finite_minmax(phi_over1_values)[0],
        "boundary_over1_phi_max": finite_minmax(phi_over1_values)[1],
        "boundary_over1_in_solid_core_count": count(solid_core),
        "boundary_over1_in_solid_shell_count": count(solid_shell),
        "boundary_over1_in_solid_near_count": count(solid_near),
        "boundary_over1_outside_solid_near_count": count(outside_solid_near),
        "boundary_over1_outside_solid_far_count": count(outside_solid_far),
        "boundary_over1_on_index_outer_face_count": count(index_outer_face),
        "boundary_over1_not_on_index_outer_face_count": count(~index_outer_face),
        "neighbor6_context": ctx6,
        "neighbor26_context": ctx26,
    }
    if gradphi is not None and np.any(over1_boundary):
        grad_norm = np.linalg.norm(gradphi[over1_boundary], axis=1)
        row["boundary_over1_gradphi_norm_min"] = float(np.nanmin(grad_norm))
        row["boundary_over1_gradphi_norm_max"] = float(np.nanmax(grad_norm))
        row["boundary_over1_gradphi_norm_mean"] = float(np.nanmean(grad_norm))

    samples = sample_top_cells(
        phi,
        over1_boundary,
        boundary,
        is_boundary_q,
        normal,
        gradphi,
        rsolid,
        ctx_arrays_26,
        sample_limit,
    )
    return row, samples


def write_csv(rows: list[dict[str, Any]], path: pathlib.Path) -> None:
    fields = [
        "step",
        "boundary_over1_count",
        "boundary_phi_max",
        "fluid_phi_max",
        "boundary_over1_in_solid_core_count",
        "boundary_over1_in_solid_shell_count",
        "boundary_over1_in_solid_near_count",
        "boundary_over1_outside_solid_near_count",
        "boundary_over1_outside_solid_far_count",
        "boundary_over1_on_index_outer_face_count",
        "neighbor6_with_fluid_neighbor_count",
        "neighbor6_neighbor_phi_gt_0p5_count",
        "neighbor6_neighbor_phi_0p05_to_0p95_count",
        "neighbor26_with_fluid_neighbor_count",
        "neighbor26_neighbor_phi_gt_0p5_count",
        "neighbor26_neighbor_phi_0p05_to_0p95_count",
        "boundary_over1_gradphi_norm_max",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            flat: dict[str, Any] = dict(row)
            for key, value in row["neighbor6_context"].items():
                flat[f"neighbor6_{key}"] = value
            for key, value in row["neighbor26_context"].items():
                flat[f"neighbor26_{key}"] = value
            writer.writerow({field: flat.get(field, "") for field in fields})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-root", type=pathlib.Path, required=True)
    parser.add_argument("--out-dir", type=pathlib.Path, required=True)
    parser.add_argument("--sample-limit", type=int, default=12)
    args = parser.parse_args()

    frames = sorted((args.case_root / "output").glob("*_VTK_P00_*.vti"), key=step_of)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    samples_by_step: dict[str, list[dict[str, Any]]] = {}
    for frame in frames:
        row, samples = audit_frame(frame, args.sample_limit)
        rows.append(row)
        samples_by_step[str(row["step"])] = samples

    (args.out_dir / "boundary_phi_context_audit.json").write_text(
        json.dumps({"rows": rows, "top_samples": samples_by_step}, indent=2) + "\n",
        encoding="utf-8",
    )
    write_csv(rows, args.out_dir / "boundary_phi_context_summary.csv")
    print(json.dumps({"rows": rows, "top_samples": samples_by_step}, indent=2))


if __name__ == "__main__":
    main()
