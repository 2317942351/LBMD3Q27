#!/usr/bin/env python3
"""Replay the geometric wall-BC formula with alternative input angles.

This is a postprocess-only diagnostic. It does not represent a rerun of the
solver because the phase field and gradients are taken from an existing case.
The purpose is to quantify how strongly the normal geometric wall formula can
amplify boundary ghost PhaseField values through tan(pi/2-radAngle).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib
import re
from typing import Any

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
    arrays: dict[str, np.ndarray] = {}
    cell_data = image.GetCellData()
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


def reshape_scalar(values: np.ndarray, dims: tuple[int, int, int]) -> np.ndarray:
    nx, ny, nz = dims
    return scalar(values).reshape((nz, ny, nx)).transpose(2, 1, 0)


def reshape_vector(values: np.ndarray, dims: tuple[int, int, int]) -> np.ndarray:
    nx, ny, nz = dims
    out = np.asarray(values, dtype=float)
    if out.ndim == 1:
        out = out[:, None]
    vec = np.zeros((out.shape[0], 3), dtype=float)
    vec[:, : min(out.shape[1], 3)] = out[:, : min(out.shape[1], 3)]
    return vec.reshape((nz, ny, nx, 3)).transpose(2, 1, 0, 3)


def inside(idx: tuple[int, int, int], shape: tuple[int, int, int]) -> bool:
    return all(0 <= idx[i] < shape[i] for i in range(3))


def finite_stats(values: np.ndarray) -> dict[str, float]:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return {"min": math.nan, "max": math.nan, "mean": math.nan}
    return {
        "min": float(np.min(finite)),
        "max": float(np.max(finite)),
        "mean": float(np.mean(finite)),
    }


def base_wall_formula_terms(path: pathlib.Path) -> tuple[int, dict[str, np.ndarray]]:
    dims, arrays = read_vti(path)
    phi = reshape_scalar(arrays["PhaseField"], dims)
    boundary = reshape_scalar(arrays["BOUNDARY"], dims) if "BOUNDARY" in arrays else np.zeros_like(phi)
    normal = reshape_vector(arrays["Normal"], dims)
    grad = reshape_vector(arrays["GradPhi"], dims)

    is_boundary = np.isfinite(boundary) & (boundary != 0.0)
    coords = np.argwhere(is_boundary)
    pf_f_values: list[float] = []
    grad_tangent_values: list[float] = []
    two_h_values: list[float] = []
    wall_phi_values: list[float] = []

    for x, y, z in coords:
        n_raw = normal[x, y, z, :]
        n_rounded = np.rint(n_raw).astype(int)
        if np.all(n_rounded == 0):
            continue
        idx1 = (int(x + n_rounded[0]), int(y + n_rounded[1]), int(z + n_rounded[2]))
        idx2 = (int(x + 2 * n_rounded[0]), int(y + 2 * n_rounded[1]), int(z + 2 * n_rounded[2]))
        if not inside(idx1, phi.shape) or not inside(idx2, phi.shape):
            continue
        if is_boundary[idx1] or is_boundary[idx2]:
            continue
        norm2 = float(np.dot(n_raw, n_raw))
        if norm2 <= 0.0:
            continue

        der1 = grad[idx1]
        der2 = grad[idx2]
        coeff1 = float(np.dot(der1, n_raw) / norm2)
        coeff2 = float(np.dot(der2, n_raw) / norm2)
        proj1 = der1 - coeff1 * n_raw
        proj2 = der2 - coeff2 * n_raw
        tangent_vec = 1.5 * proj1 - 0.5 * proj2

        pf_f_values.append(float(phi[idx1]))
        grad_tangent_values.append(float(np.linalg.norm(tangent_vec)))
        two_h_values.append(float(math.sqrt(norm2)))
        wall_phi_values.append(float(phi[x, y, z]))

    return step_of(path), {
        "pf_f": np.asarray(pf_f_values, dtype=float),
        "grad_tangent": np.asarray(grad_tangent_values, dtype=float),
        "two_h": np.asarray(two_h_values, dtype=float),
        "wall_phi": np.asarray(wall_phi_values, dtype=float),
    }


def summarize_angle(step: int, terms: dict[str, np.ndarray], angle_deg: float) -> dict[str, Any]:
    coeff = math.tan(math.pi / 2.0 - math.radians(angle_deg))
    predicted = terms["pf_f"] + coeff * terms["grad_tangent"] * terms["two_h"]
    wall_phi = terms["wall_phi"]
    over1 = predicted > 1.0 + 1.0e-8
    over2 = predicted > 2.0
    under0 = predicted < -1.0e-8
    actual_over1 = wall_phi > 1.0 + 1.0e-8
    return {
        "step": step,
        "angle_deg": angle_deg,
        "tan_coeff": coeff,
        "valid_boundary_formula_points": int(predicted.size),
        "pred_phi_min": float(np.nanmin(predicted)) if predicted.size else math.nan,
        "pred_phi_max": float(np.nanmax(predicted)) if predicted.size else math.nan,
        "pred_phi_mean": float(np.nanmean(predicted)) if predicted.size else math.nan,
        "pred_over1_count": int(np.count_nonzero(over1)),
        "pred_over1_fraction": float(np.count_nonzero(over1) / predicted.size) if predicted.size else math.nan,
        "pred_over2_count": int(np.count_nonzero(over2)),
        "pred_under0_count": int(np.count_nonzero(under0)),
        "actual_wall_phi_min": float(np.nanmin(wall_phi)) if wall_phi.size else math.nan,
        "actual_wall_phi_max": float(np.nanmax(wall_phi)) if wall_phi.size else math.nan,
        "actual_wall_over1_count": int(np.count_nonzero(actual_over1)),
        "pf_f_min": finite_stats(terms["pf_f"])["min"],
        "pf_f_max": finite_stats(terms["pf_f"])["max"],
        "grad_tangent_max": finite_stats(terms["grad_tangent"])["max"],
        "two_h_max": finite_stats(terms["two_h"])["max"],
    }


def write_csv(rows: list[dict[str, Any]], path: pathlib.Path) -> None:
    fields = [
        "step",
        "angle_deg",
        "tan_coeff",
        "valid_boundary_formula_points",
        "pred_phi_min",
        "pred_phi_max",
        "pred_phi_mean",
        "pred_over1_count",
        "pred_over1_fraction",
        "pred_over2_count",
        "pred_under0_count",
        "actual_wall_phi_min",
        "actual_wall_phi_max",
        "actual_wall_over1_count",
        "pf_f_min",
        "pf_f_max",
        "grad_tangent_max",
        "two_h_max",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-root", type=pathlib.Path, required=True)
    parser.add_argument("--out-dir", type=pathlib.Path, required=True)
    parser.add_argument("--angles", type=float, nargs="+", required=True)
    args = parser.parse_args()

    frames = sorted((args.case_root / "output").glob("*_VTK_P00_*.vti"), key=step_of)
    rows: list[dict[str, Any]] = []
    for frame in frames:
        step, terms = base_wall_formula_terms(frame)
        for angle in args.angles:
            rows.append(summarize_angle(step, terms, angle))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(rows, args.out_dir / "geometric_wall_angle_sensitivity_summary.csv")
    payload = {
        "case_root": str(args.case_root),
        "angles": args.angles,
        "note": (
            "Postprocess-only replay on existing fields; alternative angles are "
            "not independent solver results."
        ),
        "rows": rows,
    }
    (args.out_dir / "geometric_wall_angle_sensitivity_audit.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
