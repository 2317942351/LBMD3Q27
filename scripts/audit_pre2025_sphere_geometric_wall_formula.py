#!/usr/bin/env python3
"""Approximate geometric wall-BC formula from VTI fields for PRE sphere frames."""

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


def finite_minmax_mean(values: np.ndarray) -> dict[str, float]:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return {"min": math.nan, "max": math.nan, "mean": math.nan}
    return {"min": float(np.min(values)), "max": float(np.max(values)), "mean": float(np.mean(values))}


def inside(idx: tuple[int, int, int], shape: tuple[int, int, int]) -> bool:
    return all(0 <= idx[i] < shape[i] for i in range(3))


def approximate_frame(path: pathlib.Path, rad_angle_deg: float, sample_limit: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    dims, arrays = read_vti(path)
    phi = reshape_scalar(arrays["PhaseField"], dims)
    boundary = reshape_scalar(arrays["BOUNDARY"], dims) if "BOUNDARY" in arrays else np.zeros_like(phi)
    normal = reshape_vector(arrays["Normal"], dims)
    grad = reshape_vector(arrays["GradPhi"], dims)
    is_boundary = np.isfinite(boundary) & (boundary != 0.0)
    over1 = is_boundary & (phi > 1.0 + 1.0e-8)

    coeff_tan = math.tan(math.pi / 2.0 - math.radians(rad_angle_deg))
    rows = []
    samples = []
    coords = np.argwhere(over1)
    for x, y, z in coords:
        n_raw = normal[x, y, z, :]
        n = np.rint(n_raw).astype(int)
        if np.all(n == 0):
            continue
        idx1 = (int(x + n[0]), int(y + n[1]), int(z + n[2]))
        idx2 = (int(x + 2 * n[0]), int(y + 2 * n[1]), int(z + 2 * n[2]))
        if not inside(idx1, phi.shape) or not inside(idx2, phi.shape):
            continue
        norm2 = float(np.dot(n_raw, n_raw))
        if norm2 <= 0.0:
            continue
        h = 0.5 * math.sqrt(norm2)
        der1 = grad[idx1]
        der2 = grad[idx2]
        coeff1 = float(np.dot(der1, n_raw) / norm2)
        coeff2 = float(np.dot(der2, n_raw) / norm2)
        proj1 = der1 - coeff1 * n_raw
        proj2 = der2 - coeff2 * n_raw
        tangent_vec = 1.5 * proj1 - 0.5 * proj2
        grad_tangent = float(np.linalg.norm(tangent_vec))
        pf_f = float(phi[idx1])
        predicted = coeff_tan * grad_tangent * 2.0 * h + pf_f
        err = predicted - float(phi[x, y, z])
        rec = {
            "xyz": [int(x), int(y), int(z)],
            "normal": [float(v) for v in n_raw],
            "idx1": list(idx1),
            "idx2": list(idx2),
            "phi_wall": float(phi[x, y, z]),
            "pf_f_phi_idx1": pf_f,
            "phi_idx2": float(phi[idx2]),
            "grad1_norm": float(np.linalg.norm(der1)),
            "grad2_norm": float(np.linalg.norm(der2)),
            "grad_tangent": grad_tangent,
            "two_h": 2.0 * h,
            "tan_coeff": coeff_tan,
            "predicted_wall_phi": predicted,
            "prediction_error": err,
            "idx1_boundary": bool(is_boundary[idx1]),
            "idx2_boundary": bool(is_boundary[idx2]),
        }
        rows.append(rec)
    if rows:
        order = np.argsort([r["phi_wall"] for r in rows])[::-1][:sample_limit]
        samples = [rows[int(i)] for i in order]

    valid = np.array([r["prediction_error"] for r in rows], dtype=float)
    abs_valid = np.abs(valid)
    predicted = np.array([r["predicted_wall_phi"] for r in rows], dtype=float)
    wall = np.array([r["phi_wall"] for r in rows], dtype=float)
    grad_tangent = np.array([r["grad_tangent"] for r in rows], dtype=float)
    pf_f = np.array([r["pf_f_phi_idx1"] for r in rows], dtype=float)
    summary = {
        "step": step_of(path),
        "file": str(path),
        "rad_angle_deg": rad_angle_deg,
        "over1_boundary_count": int(np.count_nonzero(over1)),
        "formula_valid_count": len(rows),
        "formula_valid_fraction": float(len(rows) / max(1, int(np.count_nonzero(over1)))),
        "wall_phi": finite_minmax_mean(wall),
        "pf_f_phi_idx1": finite_minmax_mean(pf_f),
        "grad_tangent": finite_minmax_mean(grad_tangent),
        "predicted_wall_phi": finite_minmax_mean(predicted),
        "prediction_error": finite_minmax_mean(valid),
        "abs_prediction_error": finite_minmax_mean(abs_valid),
        "abs_error_lt_1e_6_count": int(np.count_nonzero(abs_valid < 1.0e-6)),
        "abs_error_lt_1e_3_count": int(np.count_nonzero(abs_valid < 1.0e-3)),
        "abs_error_lt_1e_2_count": int(np.count_nonzero(abs_valid < 1.0e-2)),
        "idx1_boundary_count": int(sum(1 for r in rows if r["idx1_boundary"])),
        "idx2_boundary_count": int(sum(1 for r in rows if r["idx2_boundary"])),
    }
    return summary, samples


def write_csv(rows: list[dict[str, Any]], path: pathlib.Path) -> None:
    fields = [
        "step",
        "over1_boundary_count",
        "formula_valid_count",
        "formula_valid_fraction",
        "wall_phi_max",
        "pf_f_phi_idx1_min",
        "pf_f_phi_idx1_max",
        "grad_tangent_min",
        "grad_tangent_max",
        "predicted_wall_phi_max",
        "prediction_error_mean",
        "abs_prediction_error_max",
        "abs_error_lt_1e_3_count",
        "idx1_boundary_count",
        "idx2_boundary_count",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            flat = {
                "step": row["step"],
                "over1_boundary_count": row["over1_boundary_count"],
                "formula_valid_count": row["formula_valid_count"],
                "formula_valid_fraction": row["formula_valid_fraction"],
                "wall_phi_max": row["wall_phi"]["max"],
                "pf_f_phi_idx1_min": row["pf_f_phi_idx1"]["min"],
                "pf_f_phi_idx1_max": row["pf_f_phi_idx1"]["max"],
                "grad_tangent_min": row["grad_tangent"]["min"],
                "grad_tangent_max": row["grad_tangent"]["max"],
                "predicted_wall_phi_max": row["predicted_wall_phi"]["max"],
                "prediction_error_mean": row["prediction_error"]["mean"],
                "abs_prediction_error_max": row["abs_prediction_error"]["max"],
                "abs_error_lt_1e_3_count": row["abs_error_lt_1e_3_count"],
                "idx1_boundary_count": row["idx1_boundary_count"],
                "idx2_boundary_count": row["idx2_boundary_count"],
            }
            writer.writerow(flat)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-root", type=pathlib.Path, required=True)
    parser.add_argument("--out-dir", type=pathlib.Path, required=True)
    parser.add_argument("--rad-angle-deg", type=float, required=True)
    parser.add_argument("--sample-limit", type=int, default=12)
    args = parser.parse_args()

    frames = sorted((args.case_root / "output").glob("*_VTK_P00_*.vti"), key=step_of)
    summaries = []
    samples: dict[str, list[dict[str, Any]]] = {}
    for frame in frames:
        summary, frame_samples = approximate_frame(frame, args.rad_angle_deg, args.sample_limit)
        summaries.append(summary)
        samples[str(summary["step"])] = frame_samples
    args.out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"summaries": summaries, "top_samples": samples}
    (args.out_dir / "geometric_wall_formula_audit.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    write_csv(summaries, args.out_dir / "geometric_wall_formula_summary.csv")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
