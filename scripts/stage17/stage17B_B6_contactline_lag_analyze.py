#!/usr/bin/env python3
"""Stage17B-B6 contact-line lag analysis for B5 VTI outputs.

This is an offline diagnostic. It reads the existing Stage17B-B5 cylinder VTI
frames and compares two time series:

* the controlled WallGhost/Fphi producer-consumer signal; and
* the geometric contact-line response of the liquid cap on the cylinder.

It does not validate a contact angle and it does not modify any TCLB field.
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


FIELDS = [
    "PhaseField",
    "BOUNDARY",
    "IsItBoundary",
    "B5ContactLineBandFlag",
    "B5WallGhostConsumedFlag",
    "B5WallGhostMinusCenter",
    "B5GradPhiNormal",
    "B5FphiNormalProxy",
    "B5ExpectedResponseSign",
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


def scalar_array(arrays: dict[str, np.ndarray], name: str) -> np.ndarray | None:
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


def weighted_percentile(values: np.ndarray, weights: np.ndarray, percentile: float) -> float | None:
    vals = np.asarray(values, dtype=float).ravel()
    wts = np.asarray(weights, dtype=float).ravel()
    good = np.isfinite(vals) & np.isfinite(wts) & (wts > 0.0)
    vals = vals[good]
    wts = wts[good]
    if vals.size == 0:
        return None
    order = np.argsort(vals)
    vals = vals[order]
    wts = wts[order]
    cdf = np.cumsum(wts)
    target = percentile / 100.0 * cdf[-1]
    idx = int(np.searchsorted(cdf, target, side="left"))
    idx = min(max(idx, 0), vals.size - 1)
    return float(vals[idx])


def load_metadata(case_dir: Path) -> dict[str, Any]:
    path = case_dir / "case_metadata.json"
    if not path.exists():
        raise FileNotFoundError(f"missing case metadata: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def cylinder_geometry(
    dims: tuple[int, int, int],
    meta: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    nx, ny, nz = dims
    sx, sy, _sz = [float(v) for v in meta["solid_center"]]
    sr = float(meta["solid_radius"])
    x = np.arange(nx, dtype=float)[None, None, :] + 0.5
    y = np.arange(ny, dtype=float)[None, :, None] + 0.5
    z = np.arange(nz, dtype=float)[:, None, None] + 0.5
    dx = x - sx
    dy = y - sy
    radius = np.sqrt(dx * dx + dy * dy)
    signed_distance = radius - sr
    # Angle is measured from the +y liquid axis: 0 deg is the top of cylinder.
    alpha_deg = np.degrees(np.arctan2(dx, dy))
    ycoord = np.broadcast_to(y, (nz, ny, nx))
    zcoord = np.broadcast_to(z, (nz, ny, nx))
    return (
        np.broadcast_to(signed_distance, (nz, ny, nx)),
        np.broadcast_to(alpha_deg, (nz, ny, nx)),
        ycoord,
        zcoord,
    )


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


def center_slice_metrics(
    phase: np.ndarray,
    boundary: np.ndarray | None,
    meta: dict[str, Any],
) -> dict[str, Any]:
    iz = int(np.clip(round(float(meta.get("slice_index", meta["solid_center"][2]))), 0, phase.shape[0] - 1))
    p2 = phase[iz, :, :]
    b2 = boundary[iz, :, :] if boundary is not None else None
    phase_plot = np.where(b2 > 0.5, np.nan, p2) if b2 is not None else p2
    fluid = np.isfinite(p2)
    if b2 is not None:
        fluid &= b2 <= 0.5
    liquid = (p2 >= 0.5) & fluid
    metrics: dict[str, Any]
    if np.any(liquid):
        rows, cols = np.where(liquid)
        metrics = {
            "liquid_area_cells": int(liquid.sum()),
            "footprint_cells": int(cols.max() - cols.min() + 1),
            "height_cells": int(rows.max() - rows.min() + 1),
            "centroid_x": float(np.mean(cols + 0.5)),
            "centroid_y": float(np.mean(rows + 0.5)),
            "bbox_y_min": int(rows.min()),
            "bbox_y_max": int(rows.max()),
        }
    else:
        metrics = {
            "liquid_area_cells": 0,
            "footprint_cells": 0,
            "height_cells": 0,
            "centroid_x": None,
            "centroid_y": None,
            "bbox_y_min": None,
            "bbox_y_max": None,
        }
    points = contour_points(phase_plot)
    fit = fit_circle(points)
    sx, sy, _sz = [float(v) for v in meta["solid_center"]]
    angle = tangent_angle_estimate(fit, (sx, sy), float(meta["solid_radius"]))
    metrics.update(
        {
            "slice_index": iz,
            "contour_point_count": int(len(points)),
            "circle_fit": fit,
            "angle_acute_deg": angle.get("angle_acute_deg"),
            "angle_obtuse_deg": angle.get("angle_obtuse_deg"),
            "contact_point": angle.get("contact_point"),
        }
    )
    return metrics


def analyze_frame(path: Path, meta: dict[str, Any], contact_band: float) -> dict[str, Any]:
    dims, arrays = load_vti(path)
    if "PhaseField" not in arrays:
        raise KeyError(f"PhaseField missing in {path}")
    phase = reshape_scalar(arrays["PhaseField"], dims)
    boundary_source = arrays.get("IsItBoundary", arrays.get("BOUNDARY"))
    boundary = reshape_scalar(boundary_source, dims) if boundary_source is not None else None
    sd, alpha, ycoord, zcoord = cylinder_geometry(dims, meta)
    fluid = np.isfinite(phase)
    if boundary is not None:
        fluid &= boundary <= 0.5
    near = fluid & (sd >= 0.0) & (sd <= contact_band)
    interface = near & (phase > 0.05) & (phase < 0.95)
    liquid = fluid & (phase >= 0.5)
    weights = np.maximum(phase * (1.0 - phase), 0.0)

    abs_alpha = np.abs(alpha[interface])
    contact_weights = weights[interface]
    if np.count_nonzero(interface):
        contact_half_width_max = float(np.nanmax(abs_alpha))
        contact_half_width_w95 = weighted_percentile(abs_alpha, contact_weights, 95.0)
        contact_half_width_w50 = weighted_percentile(abs_alpha, contact_weights, 50.0)
        contact_y_min = float(np.nanmin(ycoord[interface]))
        contact_y_mean = float(np.average(ycoord[interface], weights=contact_weights))
        contact_z_span = float(np.nanmax(zcoord[interface]) - np.nanmin(zcoord[interface]) + 1.0)
    else:
        contact_half_width_max = None
        contact_half_width_w95 = None
        contact_half_width_w50 = None
        contact_y_min = None
        contact_y_mean = None
        contact_z_span = None

    if np.count_nonzero(liquid):
        liquid_weights = np.ones(np.count_nonzero(liquid), dtype=float)
        liquid_centroid_y = float(np.average(ycoord[liquid], weights=liquid_weights))
        liquid_y_max = float(np.nanmax(ycoord[liquid]))
        liquid_y_min = float(np.nanmin(ycoord[liquid]))
    else:
        liquid_centroid_y = None
        liquid_y_max = None
        liquid_y_min = None

    flat_arrays = {name: scalar_array(arrays, name) for name in FIELDS}
    b5_contact = flat_arrays["B5ContactLineBandFlag"]
    b5_contact_mask = (
        np.isfinite(b5_contact) & (b5_contact > 0.5)
        if b5_contact is not None
        else np.zeros(phase.size, dtype=bool)
    )
    b5_consumed = flat_arrays["B5WallGhostConsumedFlag"]
    b5_consumed_mask = (
        b5_contact_mask & np.isfinite(b5_consumed) & (b5_consumed > 0.5)
        if b5_consumed is not None
        else np.zeros_like(b5_contact_mask)
    )

    b5_stats: dict[str, Any] = {
        "b5_contact_cells": int(np.count_nonzero(b5_contact_mask)),
        "b5_consumed_cells": int(np.count_nonzero(b5_consumed_mask)),
        "b5_consumed_fraction": (
            float(np.count_nonzero(b5_consumed_mask) / max(np.count_nonzero(b5_contact_mask), 1))
            if b5_contact_mask.size
            else None
        ),
    }
    for field in [
        "B5WallGhostMinusCenter",
        "B5GradPhiNormal",
        "B5FphiNormalProxy",
        "B5ExpectedResponseSign",
        "B5SignalSignOK",
    ]:
        values = flat_arrays.get(field)
        if values is not None:
            b5_stats[field] = finite_stats(values, b5_contact_mask)

    return {
        "case": path.parents[1].name,
        "step": step_of(path),
        "vti": str(path),
        "dims": dims,
        "phase_min": float(np.nanmin(phase)),
        "phase_max": float(np.nanmax(phase)),
        "phase_nonfinite": int(phase.size - np.count_nonzero(np.isfinite(phase))),
        "analytic_near_wall_cells": int(np.count_nonzero(near)),
        "analytic_contact_cells": int(np.count_nonzero(interface)),
        "contact_half_width_max_deg": contact_half_width_max,
        "contact_half_width_w95_deg": contact_half_width_w95,
        "contact_half_width_w50_deg": contact_half_width_w50,
        "contact_y_min": contact_y_min,
        "contact_y_mean": contact_y_mean,
        "contact_z_span_cells": contact_z_span,
        "liquid_volume_cells": int(np.count_nonzero(liquid)),
        "liquid_centroid_y": liquid_centroid_y,
        "liquid_y_min": liquid_y_min,
        "liquid_y_max": liquid_y_max,
        "slice": center_slice_metrics(phase, boundary, meta),
        "b5": b5_stats,
        "_phase": phase,
        "_near": near,
        "_interface": interface,
    }


def delta_value(value: float | None, base: float | None) -> float | None:
    if value is None or base is None:
        return None
    return float(value - base)


def attach_deltas(frames: list[dict[str, Any]]) -> None:
    if not frames:
        return
    first = frames[0]
    previous: dict[str, Any] | None = None
    for frame in frames:
        frame["delta_from_initial"] = {
            "contact_half_width_w95_deg": delta_value(
                frame.get("contact_half_width_w95_deg"), first.get("contact_half_width_w95_deg")
            ),
            "contact_y_min": delta_value(frame.get("contact_y_min"), first.get("contact_y_min")),
            "contact_y_mean": delta_value(frame.get("contact_y_mean"), first.get("contact_y_mean")),
            "liquid_centroid_y": delta_value(
                frame.get("liquid_centroid_y"), first.get("liquid_centroid_y")
            ),
            "slice_footprint_cells": delta_value(
                frame["slice"].get("footprint_cells"), first["slice"].get("footprint_cells")
            ),
            "slice_height_cells": delta_value(
                frame["slice"].get("height_cells"), first["slice"].get("height_cells")
            ),
            "slice_centroid_y": delta_value(
                frame["slice"].get("centroid_y"), first["slice"].get("centroid_y")
            ),
            "slice_angle_obtuse_deg": delta_value(
                frame["slice"].get("angle_obtuse_deg"), first["slice"].get("angle_obtuse_deg")
            ),
        }
        phase = frame["_phase"]
        first_phase = first["_phase"]
        near_union = frame["_near"] | first["_near"]
        if np.count_nonzero(near_union):
            diff = phase[near_union] - first_phase[near_union]
            frame["delta_from_initial"]["phase_mean_near_wall"] = float(np.mean(diff))
            frame["delta_from_initial"]["phase_mean_abs_near_wall"] = float(np.mean(np.abs(diff)))
            frame["delta_from_initial"]["phase_l2_near_wall"] = float(np.sqrt(np.mean(diff * diff)))
        if previous is not None:
            prev_phase = previous["_phase"]
            near_union_prev = frame["_near"] | previous["_near"]
            diff_prev = phase[near_union_prev] - prev_phase[near_union_prev]
            frame["delta_from_previous"] = {
                "step_delta": int(frame["step"] - previous["step"]),
                "contact_half_width_w95_deg": delta_value(
                    frame.get("contact_half_width_w95_deg"),
                    previous.get("contact_half_width_w95_deg"),
                ),
                "phase_mean_abs_near_wall": float(np.mean(np.abs(diff_prev)))
                if diff_prev.size
                else None,
                "phase_l2_near_wall": float(np.sqrt(np.mean(diff_prev * diff_prev)))
                if diff_prev.size
                else None,
            }
        else:
            frame["delta_from_previous"] = {}
        previous = frame


def compact_frame(frame: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in frame.items() if not key.startswith("_")}


def response_verdict(meta: dict[str, Any], final: dict[str, Any]) -> dict[str, Any]:
    init = float(meta.get("init_theta_deg", 90.0))
    target = float(meta.get("target_theta_deg", init))
    expected = "control"
    if target < init:
        expected = "spread"
    elif target > init:
        expected = "retract"
    delta_hw = final.get("delta_from_initial", {}).get("contact_half_width_w95_deg")
    delta_ymin = final.get("delta_from_initial", {}).get("contact_y_min")
    threshold_deg = 0.25
    direction = "weak_or_no_motion"
    if expected == "spread":
        if delta_hw is not None and delta_hw > threshold_deg:
            direction = "toward_target"
        elif delta_hw is not None and delta_hw < -threshold_deg:
            direction = "opposite"
    elif expected == "retract":
        if delta_hw is not None and delta_hw < -threshold_deg:
            direction = "toward_target"
        elif delta_hw is not None and delta_hw > threshold_deg:
            direction = "opposite"
    else:
        if delta_hw is not None and abs(delta_hw) <= threshold_deg:
            direction = "near_stationary_control"
        else:
            direction = "control_drift"
    return {
        "expected_response": expected,
        "direction_by_contact_half_width": direction,
        "contact_half_width_delta_deg": delta_hw,
        "contact_y_min_delta": delta_ymin,
        "claim_limit": "lag/response diagnostic only; not contact-angle validation",
    }


def draw_phase_panel(cases: list[dict[str, Any]], out_png: Path) -> None:
    if not cases:
        return
    fig, axes = plt.subplots(len(cases), 2, figsize=(8.6, 2.8 * len(cases)), constrained_layout=True)
    if len(cases) == 1:
        axes = np.asarray([axes])
    last_image = None
    for row, case in enumerate(cases):
        meta = case["metadata"]
        sx, sy, _sz = [float(v) for v in meta["solid_center"]]
        sr = float(meta["solid_radius"])
        for col, frame in enumerate([case["frames"][0], case["frames"][-1]]):
            ax = axes[row, col]
            phase = case["_phase_slices"][frame["step"]]
            extent = [0, phase.shape[1], 0, phase.shape[0]]
            last_image = ax.imshow(
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
                ax.contour(x, y, phase, levels=[0.5], colors="black", linewidths=0.8)
            circle = plt.Circle((sx, sy), sr, fill=False, color="0.2", linewidth=1.0)
            ax.add_patch(circle)
            label = "initial" if col == 0 else "final"
            ax.set_title(f"{case['case']} {label} step {frame['step']}", fontsize=8)
            ax.set_xlim(0, phase.shape[1])
            ax.set_ylim(max(0, sy - sr - 4), min(phase.shape[0], sy + sr + 36))
            ax.set_xlabel("x")
            ax.set_ylabel("y")
    if last_image is not None:
        cbar = fig.colorbar(last_image, ax=axes, shrink=0.9, pad=0.01)
        cbar.set_label("PhaseField")
    fig.savefig(out_png, dpi=220)
    plt.close(fig)


def draw_timeseries(cases: list[dict[str, Any]], out_png: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10.0, 7.2), constrained_layout=True)
    for case in cases:
        frames = case["frames"]
        steps = [frame["step"] for frame in frames]
        label = str(case["metadata"].get("target_theta_deg"))
        axes[0, 0].plot(
            steps,
            [frame.get("contact_half_width_w95_deg") for frame in frames],
            marker="o",
            label=f"theta {label}",
        )
        axes[0, 1].plot(
            steps,
            [
                frame.get("delta_from_initial", {}).get("contact_half_width_w95_deg")
                for frame in frames
            ],
            marker="o",
            label=f"theta {label}",
        )
        axes[1, 0].plot(
            steps,
            [
                frame.get("b5", {}).get("B5FphiNormalProxy", {}).get("mean")
                for frame in frames
            ],
            marker="o",
            label=f"theta {label}",
        )
        axes[1, 1].plot(
            steps,
            [
                frame.get("delta_from_initial", {}).get("phase_mean_abs_near_wall")
                for frame in frames
            ],
            marker="o",
            label=f"theta {label}",
        )
    axes[0, 0].set_ylabel("contact half-width w95 (deg)")
    axes[0, 1].set_ylabel("half-width delta from initial (deg)")
    axes[1, 0].set_ylabel("B5FphiNormalProxy mean")
    axes[1, 1].set_ylabel("near-wall |Phase delta| mean")
    for ax in axes.ravel():
        ax.set_xlabel("step")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
    fig.savefig(out_png, dpi=220)
    plt.close(fig)


def analyze_case(case_dir: Path, out_dir: Path, expected_final_step: int, contact_band: float) -> dict[str, Any]:
    meta = load_metadata(case_dir)
    if meta.get("geometry") != "cylinder":
        return {
            "case": case_dir.name,
            "status": "SKIP",
            "failures": ["b6_currently_supports_cylinder_only"],
            "metadata": meta,
            "frames": [],
        }
    vtis = sorted((case_dir / "output").glob("case_VTK_P00_*.vti"), key=step_of)
    failures: list[str] = []
    if not vtis:
        return {"case": case_dir.name, "status": "FAIL", "failures": ["no_vti"], "frames": []}
    frames = [analyze_frame(path, meta, contact_band) for path in vtis]
    attach_deltas(frames)
    if expected_final_step >= 0 and frames[-1]["step"] != expected_final_step:
        failures.append(f"final_step_{frames[-1]['step']}_expected_{expected_final_step}")
    for frame in frames:
        if frame["phase_nonfinite"] > 0:
            failures.append(f"phase_nonfinite_step_{frame['step']}")
        if frame["analytic_contact_cells"] <= 0:
            failures.append(f"no_analytic_contact_cells_step_{frame['step']}")
    status = "PASS_B6_ANALYSIS" if not failures else "FAIL"
    compact_frames = [compact_frame(frame) for frame in frames]
    case_summary = {
        "case": case_dir.name,
        "metadata": meta,
        "status": status,
        "failures": sorted(set(failures)),
        "response_verdict": response_verdict(meta, compact_frames[-1]),
        "frames": compact_frames,
        "claim_limit": "contact-line lag diagnostic only; not contact-angle validation",
    }
    case_out = out_dir / case_dir.name
    case_out.mkdir(parents=True, exist_ok=True)
    (case_out / f"{case_dir.name}_B6_contactline_lag.json").write_text(
        json.dumps(case_summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    phase_slices: dict[int, np.ndarray] = {}
    for frame in frames:
        iz = int(frame["slice"]["slice_index"])
        phase_slices[int(frame["step"])] = frame["_phase"][iz, :, :]
    case_summary["_phase_slices"] = phase_slices
    return case_summary


def flatten_rows(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        for frame in case.get("frames", []):
            b5 = frame.get("b5", {})
            delta0 = frame.get("delta_from_initial", {})
            row = {
                "case": case["case"],
                "status": case["status"],
                "target_theta_deg": case.get("metadata", {}).get("target_theta_deg"),
                "expected_response": case.get("response_verdict", {}).get("expected_response"),
                "response_direction": case.get("response_verdict", {}).get(
                    "direction_by_contact_half_width"
                ),
                "step": frame.get("step"),
                "phase_min": frame.get("phase_min"),
                "phase_max": frame.get("phase_max"),
                "phase_nonfinite": frame.get("phase_nonfinite"),
                "analytic_contact_cells": frame.get("analytic_contact_cells"),
                "contact_half_width_w95_deg": frame.get("contact_half_width_w95_deg"),
                "contact_half_width_delta_deg": delta0.get("contact_half_width_w95_deg"),
                "contact_y_min": frame.get("contact_y_min"),
                "contact_y_min_delta": delta0.get("contact_y_min"),
                "phase_mean_abs_near_wall_delta": delta0.get("phase_mean_abs_near_wall"),
                "slice_footprint_delta": delta0.get("slice_footprint_cells"),
                "slice_height_delta": delta0.get("slice_height_cells"),
                "slice_angle_obtuse_delta_deg": delta0.get("slice_angle_obtuse_deg"),
                "b5_contact_cells": b5.get("b5_contact_cells"),
                "b5_consumed_fraction": b5.get("b5_consumed_fraction"),
                "b5_fphi_normal_proxy_mean": b5.get("B5FphiNormalProxy", {}).get("mean"),
                "b5_grad_phi_normal_mean": b5.get("B5GradPhiNormal", {}).get("mean"),
                "b5_wallghost_minus_center_mean": b5.get("B5WallGhostMinusCenter", {}).get("mean"),
                "b5_signal_ok_mean": b5.get("B5SignalSignOK", {}).get("mean"),
            }
            rows.append(row)
    return rows


def classify_pair(cases: list[dict[str, Any]]) -> dict[str, Any]:
    by_target = {
        int(case.get("metadata", {}).get("target_theta_deg", -999)): case
        for case in cases
        if case.get("metadata")
    }
    out: dict[str, Any] = {
        "driver_opposite_sign_60_120": None,
        "geometry_pair_direction": None,
        "interpretation": "insufficient_cases",
    }
    c60 = by_target.get(60)
    c120 = by_target.get(120)
    if not c60 or not c120:
        return out
    f60 = c60["frames"][-1]["b5"]["B5FphiNormalProxy"]["mean"]
    f120 = c120["frames"][-1]["b5"]["B5FphiNormalProxy"]["mean"]
    d60 = c60["response_verdict"]["contact_half_width_delta_deg"]
    d120 = c120["response_verdict"]["contact_half_width_delta_deg"]
    out["driver_opposite_sign_60_120"] = (
        f60 is not None and f120 is not None and f60 * f120 < 0.0
    )
    if d60 is None or d120 is None:
        out["geometry_pair_direction"] = "missing"
    elif d60 > 0.25 and d120 < -0.25:
        out["geometry_pair_direction"] = "toward_targets"
    elif abs(d60) <= 0.25 and abs(d120) <= 0.25:
        out["geometry_pair_direction"] = "both_weak_or_lagged"
    else:
        out["geometry_pair_direction"] = "mixed_or_opposite"
    if out["driver_opposite_sign_60_120"] and out["geometry_pair_direction"] == "both_weak_or_lagged":
        out["interpretation"] = "driver_present_but_contactline_response_weak_or_lagged"
    elif out["driver_opposite_sign_60_120"] and out["geometry_pair_direction"] == "toward_targets":
        out["interpretation"] = "driver_and_geometry_direction_consistent_short_run"
    elif not out["driver_opposite_sign_60_120"]:
        out["interpretation"] = "driver_sign_not_clean"
    else:
        out["interpretation"] = "driver_present_geometry_mixed"
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--out-json", type=Path, default=None)
    parser.add_argument("--out-csv", type=Path, default=None)
    parser.add_argument("--expected-final-step", type=int, default=600)
    parser.add_argument("--contact-band", type=float, default=3.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir or (args.root / "post" / "B6_contactline_lag")
    out_dir.mkdir(parents=True, exist_ok=True)
    case_dirs = sorted(
        path for path in args.root.iterdir() if path.is_dir() and (path / "case.xml").exists()
    )
    cases = [
        analyze_case(case_dir, out_dir, args.expected_final_step, args.contact_band)
        for case_dir in case_dirs
    ]
    rows = flatten_rows(cases)
    out_json = args.out_json or (out_dir / "stage17B_B6_contactline_lag_analysis.json")
    out_csv = args.out_csv or (out_dir / "stage17B_B6_contactline_lag_frames.csv")
    if rows:
        with out_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    panel_png = out_dir / "stage17B_B6_contactline_initial_final_panel.png"
    timeseries_png = out_dir / "stage17B_B6_contactline_timeseries.png"
    draw_phase_panel(cases, panel_png)
    draw_timeseries(cases, timeseries_png)
    failures = {case["case"]: case["failures"] for case in cases if case.get("failures")}
    pair = classify_pair(cases)
    status = "PASS_STAGE17B_B6_ANALYSIS"
    if failures:
        status = "FAIL_STAGE17B_B6_ANALYSIS"
    summary = {
        "root": str(args.root),
        "out_dir": str(out_dir),
        "status": status,
        "pair_classification": pair,
        "failures": failures,
        "claim_limit": "contact-line lag/response diagnostic only; not contact-angle validation",
        "contact_band_lu": args.contact_band,
        "figures": {
            "initial_final_panel": str(panel_png),
            "timeseries": str(timeseries_png),
        },
        "frames_csv": str(out_csv),
        "cases": [
            {key: value for key, value in case.items() if key != "_phase_slices"}
            for case in cases
        ],
    }
    out_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "cases"}, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
