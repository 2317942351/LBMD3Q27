#!/usr/bin/env python3
"""Compute Stage13 flat-wall shape contact angle from VTI snapshots.

This is a wall-only circle-arc-fit diagnostic. It measures the phi=0.5
interface shape in the droplet-center x-slice, then reports a time series and
PNG plot. It is diagnostic evidence only; it does not promote validation.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def step_of(path: Path) -> int:
    match = re.search(r"P00_(\d+)\.vti$", path.name)
    return int(match.group(1)) if match else -1


def load_vti(path: Path) -> tuple[tuple[int, int, int], dict[str, np.ndarray]]:
    try:
        import vtk
        from vtk.util.numpy_support import vtk_to_numpy
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "The vtk Python package is required to read VTI files. Run this "
            "script in the TCLB post-processing environment on the server."
        ) from exc

    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(str(path))
    reader.Update()
    image = reader.GetOutput()
    dims = tuple(int(v) - 1 for v in image.GetDimensions())
    cell_data = image.GetCellData()
    arrays: dict[str, np.ndarray] = {}
    for idx in range(cell_data.GetNumberOfArrays()):
        array = cell_data.GetArray(idx)
        arrays[array.GetName() or f"array_{idx}"] = vtk_to_numpy(array).copy()
    return dims, arrays


def wall_center_slice(
    arrays: dict[str, np.ndarray],
    dims: tuple[int, int, int],
    x_index: int,
) -> tuple[np.ndarray, np.ndarray | None]:
    nx, ny, nz = dims
    phase = arrays["PhaseField"].reshape((nz, ny, nx)).astype(float)
    boundary = arrays.get("IsItBoundary", arrays.get("BOUNDARY"))
    boundary_3d = boundary.reshape((nz, ny, nx)) if boundary is not None else None
    x_index = int(np.clip(x_index, 0, nx - 1))
    phase_2d = phase[:, :, x_index].T
    boundary_2d = boundary_3d[:, :, x_index].T if boundary_3d is not None else None
    return phase_2d, boundary_2d


def contour_points(phase: np.ndarray, level: float = 0.5) -> np.ndarray:
    points: list[tuple[float, float]] = []
    rows, cols = phase.shape
    field = np.where(np.isfinite(phase), phase, np.nan)
    for row in range(rows):
        for col in range(cols - 1):
            a, b = field[row, col], field[row, col + 1]
            if np.isfinite(a) and np.isfinite(b) and a != b and (a - level) * (b - level) <= 0:
                points.append((col + 0.5 + (level - a) / (b - a), row + 0.5))
    for col in range(cols):
        for row in range(rows - 1):
            a, b = field[row, col], field[row + 1, col]
            if np.isfinite(a) and np.isfinite(b) and a != b and (a - level) * (b - level) <= 0:
                points.append((col + 0.5, row + 0.5 + (level - a) / (b - a)))
    return np.asarray(points, dtype=float) if points else np.empty((0, 2), dtype=float)


def fit_circle(points: np.ndarray) -> dict[str, float] | None:
    if len(points) < 6:
        return None
    x = points[:, 0]
    y = points[:, 1]
    matrix = np.column_stack([2.0 * x, 2.0 * y, np.ones_like(x)])
    rhs = x * x + y * y
    sol, *_ = np.linalg.lstsq(matrix, rhs, rcond=None)
    cx, cy, c = sol
    radius2 = c + cx * cx + cy * cy
    if radius2 <= 0.0:
        return None
    radius = math.sqrt(radius2)
    residual = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) - radius
    return {
        "cx": float(cx),
        "cy": float(cy),
        "r": float(radius),
        "rms": float(np.sqrt(np.mean(residual ** 2))),
        "n_points": int(len(points)),
    }


def wall_contact_angle(circle: dict[str, float] | None) -> float | None:
    if circle is None:
        return None
    disc = circle["r"] ** 2 - circle["cy"] ** 2
    if disc <= 0.0:
        return None
    contact_dx = math.sqrt(disc)
    radial_x = contact_dx
    radial_y = -circle["cy"]
    radial_norm = math.hypot(radial_x, radial_y)
    if radial_norm <= 1.0e-12:
        return None
    tangent_x = radial_y / radial_norm
    tangent_y = -radial_x / radial_norm
    if tangent_y < 0.0:
        tangent_x, tangent_y = -tangent_x, -tangent_y
    acute = math.degrees(math.acos(max(-1.0, min(1.0, abs(tangent_x)))))
    return 180.0 - acute if circle["cy"] > 0.0 else acute


def analyze_case(case_dir: Path, max_vti: int = 0) -> dict[str, Any]:
    metadata = json.loads((case_dir / "case_metadata.json").read_text(encoding="utf-8"))
    vtis = sorted((case_dir / "output").glob("case_VTK_P00_*.vti"), key=step_of)
    if max_vti > 0 and len(vtis) > max_vti:
        indices = np.linspace(0, len(vtis) - 1, max_vti).astype(int)
        vtis = [vtis[idx] for idx in indices]
    if not vtis:
        raise FileNotFoundError(f"No VTI files found in {case_dir / 'output'}")
    series: list[dict[str, Any]] = []
    for vti in vtis:
        dims, arrays = load_vti(vti)
        x_index = int(round(float(metadata.get("liquid_probe", [dims[0] // 2])[0])))
        phase, boundary = wall_center_slice(arrays, dims, x_index)
        fluid_phase = np.where(boundary > 0.5, np.nan, phase) if boundary is not None else phase
        points = contour_points(fluid_phase)
        circle = fit_circle(points)
        theta = wall_contact_angle(circle)
        series.append(
            {
                "step": step_of(vti),
                "vti": str(vti),
                "theta_shape_deg": theta,
                "circle": circle,
            }
        )
    finite_angles = [
        item["theta_shape_deg"]
        for item in series
        if isinstance(item["theta_shape_deg"], (int, float)) and math.isfinite(item["theta_shape_deg"])
    ]
    end_angle = None
    end_std = None
    if finite_angles:
        tail = finite_angles[max(0, 3 * len(finite_angles) // 4):]
        end_angle = float(np.median(tail))
        end_std = float(np.std(tail))
    return {
        "case": case_dir.name,
        "case_dir": str(case_dir),
        "metadata": metadata,
        "theta_shape_series": series,
        "theta_shape_end_deg": end_angle,
        "theta_shape_tail_std_deg": end_std,
        "claim_limit": "shape-angle diagnostic only; not validation_passed",
    }


def plot_result(result: dict[str, Any], out_dir: Path) -> dict[str, str]:
    metadata = result["metadata"]
    steps = [item["step"] for item in result["theta_shape_series"]]
    angles = [item["theta_shape_deg"] for item in result["theta_shape_series"]]
    init_theta = float(metadata["init_theta_deg"])
    bc_theta = float(metadata["bc_theta_deg"])
    fig, ax = plt.subplots(figsize=(8.0, 4.8), constrained_layout=True)
    ax.plot(steps, angles, "o-", lw=1.5, ms=4, label="shape angle")
    ax.axhline(bc_theta, color="#d62728", ls="--", lw=1.2, label=f"BC {bc_theta:.0f} deg")
    if bool(metadata.get("decoupled", False)):
        ax.axhline(init_theta, color="0.45", ls=":", lw=1.2, label=f"init {init_theta:.0f} deg")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Flat-wall shape contact angle (deg)")
    ax.set_ylim(0, 180)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=9)
    ax.set_title(
        f"{result['case']} end={result['theta_shape_end_deg'] if result['theta_shape_end_deg'] is not None else 'n/a'}"
    )
    png = out_dir / f"{result['case']}_stage13_shape_angle.png"
    pdf = out_dir / f"{result['case']}_stage13_shape_angle.pdf"
    fig.savefig(png, dpi=220)
    fig.savefig(pdf)
    plt.close(fig)
    return {"png": str(png), "pdf": str(pdf)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_dir", type=Path)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--max-vti", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir or args.case_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    result = analyze_case(args.case_dir, max_vti=args.max_vti)
    result["figures"] = plot_result(result, out_dir)
    out_json = out_dir / f"{args.case_dir.name}_stage13_shape_angle.json"
    out_json.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
