#!/usr/bin/env python3
"""Create 2D morphology figures and metrics for Stage17B curved cases.

The output is a diagnostic visual check. It reads PhaseField VTI snapshots,
extracts the geometry center plane, overlays the phi=0.5 interface and the
analytic solid cross-section, and writes PNG/JSON/CSV summaries.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy


def step_of(path: Path) -> int:
    match = re.search(r"P00_(\d+)\.vti$", path.name)
    return int(match.group(1)) if match else -1


def load_vti(path: Path) -> tuple[tuple[int, int, int], dict[str, np.ndarray]]:
    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(str(path))
    reader.Update()
    image = reader.GetOutput()
    dims = tuple(int(v) - 1 for v in image.GetDimensions())
    arrays: dict[str, np.ndarray] = {}
    cell_data = image.GetCellData()
    for idx in range(cell_data.GetNumberOfArrays()):
        array = cell_data.GetArray(idx)
        if array is not None:
            arrays[array.GetName() or f"array_{idx}"] = vtk_to_numpy(array).copy()
    return dims, arrays


def reshape_scalar(values: np.ndarray, dims: tuple[int, int, int]) -> np.ndarray:
    nx, ny, nz = dims
    return np.asarray(values, dtype=float).reshape((nz, ny, nx))


def load_metadata(case_dir: Path) -> dict[str, Any]:
    meta_path = case_dir / "case_metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"missing case metadata: {meta_path}")
    return json.loads(meta_path.read_text(encoding="utf-8"))


def center_slice(
    arrays: dict[str, np.ndarray],
    dims: tuple[int, int, int],
    meta: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray | None, tuple[float, float], float, str, str]:
    phase = reshape_scalar(arrays["PhaseField"], dims)
    boundary_source = arrays.get("IsItBoundary", arrays.get("BOUNDARY"))
    boundary = reshape_scalar(boundary_source, dims) if boundary_source is not None else None
    sx, sy, sz = [float(v) for v in meta["solid_center"]]
    sr = float(meta["solid_radius"])
    geometry = str(meta["geometry"])

    if geometry == "cylinder":
        iz = int(np.clip(round(float(meta.get("slice_index", sz))), 0, dims[2] - 1))
        p2 = phase[iz, :, :]
        b2 = boundary[iz, :, :] if boundary is not None else None
        return p2, b2, (sx, sy), sr, "x", "y"
    if geometry == "sphere":
        iy = int(np.clip(round(float(meta.get("slice_index", sy))), 0, dims[1] - 1))
        p2 = phase[:, iy, :]
        b2 = boundary[:, iy, :] if boundary is not None else None
        return p2, b2, (sx, sz), sr, "x", "z"
    raise ValueError(f"unsupported geometry: {geometry}")


def contour_points(phase_2d: np.ndarray, level: float = 0.5) -> np.ndarray:
    pts: list[tuple[float, float]] = []
    rows, cols = phase_2d.shape
    values = np.where(np.isfinite(phase_2d), phase_2d, np.nan)
    for row in range(rows):
        for col in range(cols - 1):
            a, b = values[row, col], values[row, col + 1]
            if np.isfinite(a) and np.isfinite(b) and a != b and (a - level) * (b - level) <= 0:
                pts.append((col + 0.5 + (level - a) / (b - a), row + 0.5))
    for col in range(cols):
        for row in range(rows - 1):
            a, b = values[row, col], values[row + 1, col]
            if np.isfinite(a) and np.isfinite(b) and a != b and (a - level) * (b - level) <= 0:
                pts.append((col + 0.5, row + 0.5 + (level - a) / (b - a)))
    return np.asarray(pts, dtype=float) if pts else np.empty((0, 2), dtype=float)


def fit_circle(points: np.ndarray) -> dict[str, float] | None:
    if len(points) < 8:
        return None
    x = points[:, 0]
    y = points[:, 1]
    matrix = np.column_stack([2.0 * x, 2.0 * y, np.ones_like(x)])
    rhs = x * x + y * y
    sol, *_ = np.linalg.lstsq(matrix, rhs, rcond=None)
    cx, cy, c0 = [float(v) for v in sol]
    r2 = c0 + cx * cx + cy * cy
    if r2 <= 0.0:
        return None
    radius = math.sqrt(r2)
    residual = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) - radius
    return {
        "cx": cx,
        "cy": cy,
        "r": radius,
        "rms": float(np.sqrt(np.mean(residual * residual))),
    }


def circle_intersections(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> list[tuple[float, float]]:
    x0, y0, r0 = a
    x1, y1, r1 = b
    dx = x1 - x0
    dy = y1 - y0
    distance = math.hypot(dx, dy)
    if distance < 1.0e-12 or distance > r0 + r1 or distance < abs(r0 - r1):
        return []
    along = (r0 * r0 - r1 * r1 + distance * distance) / (2.0 * distance)
    h2 = r0 * r0 - along * along
    if h2 < -1.0e-9:
        return []
    h = math.sqrt(max(0.0, h2))
    xm = x0 + along * dx / distance
    ym = y0 + along * dy / distance
    return [
        (xm - h * dy / distance, ym + h * dx / distance),
        (xm + h * dy / distance, ym - h * dx / distance),
    ]


def tangent_angle_estimate(
    fitted: dict[str, float] | None,
    solid_center: tuple[float, float],
    solid_radius: float,
) -> dict[str, Any]:
    if fitted is None:
        return {"angle_acute_deg": None, "angle_obtuse_deg": None, "contact_point": None}
    points = circle_intersections(
        (fitted["cx"], fitted["cy"], fitted["r"]),
        (solid_center[0], solid_center[1], solid_radius),
    )
    if not points:
        return {"angle_acute_deg": None, "angle_obtuse_deg": None, "contact_point": None}
    point = max(points, key=lambda item: item[1])
    ix = point[0] - fitted["cx"]
    iy = point[1] - fitted["cy"]
    sx = point[0] - solid_center[0]
    sy = point[1] - solid_center[1]
    im = math.hypot(ix, iy)
    sm = math.hypot(sx, sy)
    if im < 1.0e-12 or sm < 1.0e-12:
        return {"angle_acute_deg": None, "angle_obtuse_deg": None, "contact_point": point}
    it = np.asarray([-iy / im, ix / im], dtype=float)
    st = np.asarray([-sy / sm, sx / sm], dtype=float)
    dot = abs(float(np.dot(it, st)))
    acute = math.degrees(math.acos(max(-1.0, min(1.0, dot))))
    return {
        "angle_acute_deg": acute,
        "angle_obtuse_deg": 180.0 - acute,
        "contact_point": [float(point[0]), float(point[1])],
    }


def morphology_metrics(phase_2d: np.ndarray, boundary_2d: np.ndarray | None) -> dict[str, Any]:
    fluid = np.isfinite(phase_2d)
    if boundary_2d is not None:
        fluid &= boundary_2d <= 0.5
    liquid = (phase_2d >= 0.5) & fluid
    if not np.any(liquid):
        return {
            "liquid_area_cells": 0,
            "footprint_cells": 0,
            "height_cells": 0,
            "centroid_x": None,
            "centroid_y": None,
        }
    rows, cols = np.where(liquid)
    return {
        "liquid_area_cells": int(liquid.sum()),
        "footprint_cells": int(cols.max() - cols.min() + 1),
        "height_cells": int(rows.max() - rows.min() + 1),
        "centroid_x": float(np.mean(cols + 0.5)),
        "centroid_y": float(np.mean(rows + 0.5)),
        "bbox_x_min": int(cols.min()),
        "bbox_x_max": int(cols.max()),
        "bbox_y_min": int(rows.min()),
        "bbox_y_max": int(rows.max()),
    }


def analyze_vti(path: Path, meta: dict[str, Any]) -> dict[str, Any]:
    dims, arrays = load_vti(path)
    phase_2d, boundary_2d, solid_center, solid_radius, xlabel, ylabel = center_slice(arrays, dims, meta)
    phase_plot = np.where(boundary_2d > 0.5, np.nan, phase_2d) if boundary_2d is not None else phase_2d
    points = contour_points(phase_plot)
    fitted = fit_circle(points)
    angle = tangent_angle_estimate(fitted, solid_center, solid_radius)
    stats = {
        "phase_min": float(np.nanmin(phase_2d)),
        "phase_max": float(np.nanmax(phase_2d)),
        "phase_nonfinite": int(np.size(phase_2d) - np.count_nonzero(np.isfinite(phase_2d))),
    }
    return {
        "step": step_of(path),
        "vti": str(path),
        "dims": dims,
        "xlabel": xlabel,
        "ylabel": ylabel,
        "phase_2d": phase_plot,
        "boundary_2d": boundary_2d,
        "solid_center_2d": solid_center,
        "solid_radius": solid_radius,
        "contour_points": points,
        "circle_fit": fitted,
        "angle_estimate": angle,
        "stats": stats,
        "metrics": morphology_metrics(phase_2d, boundary_2d),
    }


def draw_snapshot(ax: plt.Axes, snap: dict[str, Any], meta: dict[str, Any], title: str) -> None:
    phase = snap["phase_2d"]
    extent = [0, phase.shape[1], 0, phase.shape[0]]
    image = ax.imshow(
        phase,
        origin="lower",
        extent=extent,
        vmin=0.0,
        vmax=1.0,
        cmap="RdBu_r",
        interpolation="nearest",
        aspect="equal",
    )
    x = np.arange(phase.shape[1]) + 0.5
    y = np.arange(phase.shape[0]) + 0.5
    if np.any(np.isfinite(phase)):
        ax.contour(x, y, phase, levels=[0.5], colors="black", linewidths=1.0)
    center = snap["solid_center_2d"]
    circle = plt.Circle(center, snap["solid_radius"], fill=False, color="0.2", linewidth=1.0)
    ax.add_patch(circle)
    cp = snap["angle_estimate"].get("contact_point")
    if cp is not None:
        ax.plot([cp[0]], [cp[1]], marker="o", ms=3, color="#f28e2b")
    ax.set_title(title, fontsize=8)
    ax.set_xlabel(str(snap["xlabel"]))
    ax.set_ylabel(str(snap["ylabel"]))
    ax.set_xlim(0, phase.shape[1])
    y_max = min(phase.shape[0], center[1] + snap["solid_radius"] + 38)
    y_min = max(0, center[1] - snap["solid_radius"] - 4)
    ax.set_ylim(y_min, y_max)
    text = (
        f"init {meta['init_theta_deg']} -> target {meta['target_theta_deg']}\n"
        f"step {snap['step']}, area {snap['metrics']['liquid_area_cells']}"
    )
    ax.text(
        0.02,
        0.96,
        text,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7,
        bbox={"boxstyle": "round,pad=0.22", "facecolor": "white", "edgecolor": "0.65", "alpha": 0.9},
    )
    return image


def compact_snapshot(snap: dict[str, Any]) -> dict[str, Any]:
    angle = snap["angle_estimate"]
    fit = snap["circle_fit"]
    return {
        "step": snap["step"],
        "vti": snap["vti"],
        "stats": snap["stats"],
        "metrics": snap["metrics"],
        "circle_fit": fit,
        "angle_acute_deg": angle.get("angle_acute_deg"),
        "angle_obtuse_deg": angle.get("angle_obtuse_deg"),
        "contact_point": angle.get("contact_point"),
    }


def analyze_case(case_dir: Path, out_dir: Path, expected_final_step: int) -> dict[str, Any]:
    meta = load_metadata(case_dir)
    vtis = sorted((case_dir / "output").glob("case_VTK_P00_*.vti"), key=step_of)
    if not vtis:
        return {"case": case_dir.name, "status": "FAIL", "failures": ["no_vti"], "frames": []}
    snapshots = [analyze_vti(path, meta) for path in vtis]
    failures: list[str] = []
    if expected_final_step >= 0 and expected_final_step not in [snap["step"] for snap in snapshots]:
        failures.append(f"missing_expected_final_step_{expected_final_step}")
    for snap in snapshots:
        if snap["stats"]["phase_nonfinite"] > 0:
            failures.append(f"phase_nonfinite_step_{snap['step']}")

    case_out = out_dir / case_dir.name
    case_out.mkdir(parents=True, exist_ok=True)
    first = snapshots[0]
    final = snapshots[-1]
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 4.0), constrained_layout=True)
    image = draw_snapshot(axes[0], first, meta, "initial")
    draw_snapshot(axes[1], final, meta, "final")
    cbar = fig.colorbar(image, ax=axes, shrink=0.85, pad=0.02)
    cbar.set_label("PhaseField")
    fig.suptitle(f"{case_dir.name}: Stage17B-B4 morphology smoke", fontsize=10)
    case_png = case_out / f"{case_dir.name}_initial_final.png"
    fig.savefig(case_png, dpi=220)
    plt.close(fig)

    rows = []
    for snap in snapshots:
        row = {
            "case": case_dir.name,
            "geometry": meta["geometry"],
            "init_theta_deg": meta["init_theta_deg"],
            "target_theta_deg": meta["target_theta_deg"],
            "step": snap["step"],
            "phase_min": snap["stats"]["phase_min"],
            "phase_max": snap["stats"]["phase_max"],
            "phase_nonfinite": snap["stats"]["phase_nonfinite"],
            "liquid_area_cells": snap["metrics"]["liquid_area_cells"],
            "footprint_cells": snap["metrics"]["footprint_cells"],
            "height_cells": snap["metrics"]["height_cells"],
            "centroid_x": snap["metrics"]["centroid_x"],
            "centroid_y": snap["metrics"]["centroid_y"],
            "angle_acute_deg": snap["angle_estimate"].get("angle_acute_deg"),
            "angle_obtuse_deg": snap["angle_estimate"].get("angle_obtuse_deg"),
        }
        rows.append(row)
    with (case_out / f"{case_dir.name}_frames.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "case": case_dir.name,
        "metadata": meta,
        "status": "PASS_MORPHOLOGY_SMOKE" if not failures else "FAIL",
        "failures": failures,
        "claim_limit": "morphology response smoke only; not contact-angle validation",
        "figure": str(case_png),
        "frames": [compact_snapshot(snap) for snap in snapshots],
    }
    (case_out / f"{case_dir.name}_morphology.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    return summary


def write_summary_panel(cases: list[dict[str, Any]], out_dir: Path) -> str | None:
    if not cases:
        return None
    final_entries: list[tuple[dict[str, Any], Path]] = []
    for case in cases:
        if case.get("status") == "FAIL":
            continue
        figure = Path(str(case["figure"]))
        final_entries.append((case, figure))
    if not final_entries:
        return None
    n = len(final_entries)
    fig, axes = plt.subplots(n, 2, figsize=(8.0, max(3.0, 2.35 * n)), constrained_layout=True)
    if n == 1:
        axes = np.asarray([axes])
    last_image = None
    for row, (case, _figure) in enumerate(final_entries):
        meta = case["metadata"]
        case_dir = Path(case["frames"][0]["vti"]).parents[1]
        snapshots = [analyze_vti(Path(frame["vti"]), meta) for frame in [case["frames"][0], case["frames"][-1]]]
        last_image = draw_snapshot(axes[row, 0], snapshots[0], meta, f"{case['case']} initial")
        last_image = draw_snapshot(axes[row, 1], snapshots[1], meta, f"{case['case']} final")
    if last_image is not None:
        cbar = fig.colorbar(last_image, ax=axes, shrink=0.9, pad=0.01)
        cbar.set_label("PhaseField")
    out_png = out_dir / "stage17B_B4_morphology_initial_final_panel.png"
    fig.savefig(out_png, dpi=220)
    plt.close(fig)
    return str(out_png)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--expected-final-step", type=int, default=3000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir or (args.root / "post" / "morphology")
    out_dir.mkdir(parents=True, exist_ok=True)
    case_dirs = sorted(
        path for path in args.root.iterdir() if path.is_dir() and (path / "case.xml").exists()
    )
    cases = [analyze_case(case_dir, out_dir, args.expected_final_step) for case_dir in case_dirs]
    failures = {case["case"]: case["failures"] for case in cases if case.get("failures")}
    panel = write_summary_panel(cases, out_dir)
    summary = {
        "root": str(args.root),
        "out_dir": str(out_dir),
        "status": "PASS_STAGE17B_B4_MORPHOLOGY_SMOKE" if not failures else "FAIL",
        "failures": failures,
        "claim_limit": "morphology response smoke only; not contact-angle validation",
        "summary_panel": panel,
        "cases": cases,
    }
    (out_dir / "stage17B_B4_morphology_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    csv_rows: list[dict[str, Any]] = []
    for case in cases:
        for frame in case.get("frames", []):
            csv_rows.append(
                {
                    "case": case["case"],
                    "geometry": case.get("metadata", {}).get("geometry"),
                    "init_theta_deg": case.get("metadata", {}).get("init_theta_deg"),
                    "target_theta_deg": case.get("metadata", {}).get("target_theta_deg"),
                    "step": frame["step"],
                    "phase_min": frame["stats"]["phase_min"],
                    "phase_max": frame["stats"]["phase_max"],
                    "phase_nonfinite": frame["stats"]["phase_nonfinite"],
                    "liquid_area_cells": frame["metrics"]["liquid_area_cells"],
                    "footprint_cells": frame["metrics"]["footprint_cells"],
                    "height_cells": frame["metrics"]["height_cells"],
                    "centroid_x": frame["metrics"]["centroid_x"],
                    "centroid_y": frame["metrics"]["centroid_y"],
                    "angle_acute_deg": frame.get("angle_acute_deg"),
                    "angle_obtuse_deg": frame.get("angle_obtuse_deg"),
                }
            )
    if csv_rows:
        with (out_dir / "stage17B_B4_morphology_frames.csv").open(
            "w", newline="", encoding="utf-8"
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
            writer.writeheader()
            writer.writerows(csv_rows)
    print(json.dumps({k: v for k, v in summary.items() if k != "cases"}, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
