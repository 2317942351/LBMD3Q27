#!/usr/bin/env python3
"""Audit and plot static wall/cylinder/sphere wetting VTI snapshots.

This script is a runtime/geometry diagnostic, not a validation certificate. It
uses IsItBoundary when available because BOUNDARY is a TCLB node-type bit field
in some model variants. The local contact angle is estimated from the phase
gradient at phi=0.5 contact-line candidates:

    theta = acos(- grad(phi)/|grad(phi)| dot n_wall)

where n_wall points from solid into fluid. This preserves obtuse angles; a
pure tangent-angle measurement would fold 150 deg into 30 deg.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import vtk
from matplotlib.patches import Circle, Rectangle
from vtk.util.numpy_support import vtk_to_numpy


def vtk_array(cell_data: vtk.vtkCellData, name: str) -> np.ndarray | None:
    arr = cell_data.GetArray(name)
    if arr is None:
        return None
    return vtk_to_numpy(arr).copy()


def finite_stats(values: np.ndarray) -> dict[str, Any]:
    flat = np.asarray(values).reshape(-1)
    finite = flat[np.isfinite(flat)]
    if finite.size == 0:
        return {"count": int(flat.size), "finite": 0, "nonfinite": int(flat.size), "min": None, "max": None}
    return {
        "count": int(flat.size),
        "finite": int(finite.size),
        "nonfinite": int(flat.size - finite.size),
        "min": float(finite.min()),
        "max": float(finite.max()),
    }


def load_vti(path: Path) -> tuple[tuple[int, int, int], dict[str, np.ndarray]]:
    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(str(path))
    reader.Update()
    image = reader.GetOutput()
    dims = tuple(int(v) - 1 for v in image.GetDimensions())
    cell_data = image.GetCellData()
    arrays: dict[str, np.ndarray] = {}
    for i in range(cell_data.GetNumberOfArrays()):
        arr = cell_data.GetArray(i)
        if arr is not None:
            arrays[arr.GetName() or f"array{i}"] = vtk_to_numpy(arr).copy()
    return dims, arrays


def scalar3(arrays: dict[str, np.ndarray], name: str, dims: tuple[int, int, int], default: float = 0.0) -> np.ndarray:
    nx, ny, nz = dims
    values = arrays.get(name)
    if values is None:
        return np.full((nz, ny, nx), default, dtype=float)
    if values.ndim > 1:
        values = values[:, 0]
    return values.astype(float, copy=False).reshape((nz, ny, nx))


def speed3(arrays: dict[str, np.ndarray], dims: tuple[int, int, int]) -> np.ndarray:
    nx, ny, nz = dims
    values = arrays.get("U")
    if values is None or values.ndim != 2 or values.shape[1] < 3:
        return np.zeros((nz, ny, nx), dtype=float)
    speed = np.linalg.norm(values[:, :3], axis=1)
    return speed.reshape((nz, ny, nx))


def signed_distance(
    geom: str,
    shape: tuple[int, int, int],
    solid_center: tuple[float, float, float],
    solid_radius: float,
    cylinder_axis: int,
    plane_axis: int,
    plane_offset: float,
) -> np.ndarray:
    nz, ny, nx = shape
    iz, iy, ix = np.indices((nz, ny, nx), dtype=float)
    cx, cy, cz = solid_center
    if geom == "wall":
        coord = [ix, iy, iz][plane_axis]
        return coord - plane_offset
    if geom == "cylinder":
        if cylinder_axis == 0:
            return np.sqrt((iy - cy) ** 2 + (iz - cz) ** 2) - solid_radius
        if cylinder_axis == 1:
            return np.sqrt((ix - cx) ** 2 + (iz - cz) ** 2) - solid_radius
        return np.sqrt((ix - cx) ** 2 + (iy - cy) ** 2) - solid_radius
    if geom == "sphere":
        return np.sqrt((ix - cx) ** 2 + (iy - cy) ** 2 + (iz - cz) ** 2) - solid_radius
    raise ValueError(f"unknown geometry: {geom}")


def extract_contour_points(phi2: np.ndarray, level: float = 0.5) -> np.ndarray:
    points: list[tuple[float, float]] = []
    rows, cols = phi2.shape
    for r in range(rows):
        row = phi2[r, :]
        for c in range(cols - 1):
            a, b = row[c], row[c + 1]
            if not np.isfinite(a) or not np.isfinite(b) or a == b:
                continue
            if (a - level) * (b - level) <= 0.0:
                frac = (level - a) / (b - a)
                if 0.0 <= frac <= 1.0:
                    points.append((c + 0.5 + frac, r + 0.5))
    for c in range(cols):
        col = phi2[:, c]
        for r in range(rows - 1):
            a, b = col[r], col[r + 1]
            if not np.isfinite(a) or not np.isfinite(b) or a == b:
                continue
            if (a - level) * (b - level) <= 0.0:
                frac = (level - a) / (b - a)
                if 0.0 <= frac <= 1.0:
                    points.append((c + 0.5, r + 0.5 + frac))
    if not points:
        return np.empty((0, 2), dtype=float)
    return np.array(points, dtype=float)


def normalize(v: np.ndarray) -> np.ndarray | None:
    n = float(np.linalg.norm(v))
    if not np.isfinite(n) or n < 1e-14:
        return None
    return v / n


def local_tangent(points: np.ndarray) -> np.ndarray | None:
    if len(points) < 3:
        return None
    centered = points - points.mean(axis=0)
    cov = np.cov(centered.T)
    if cov.shape != (2, 2) or not np.isfinite(cov).all():
        return None
    vals, vecs = np.linalg.eigh(cov)
    return normalize(vecs[:, int(np.argmax(vals))])


def fit_circle(points: np.ndarray) -> dict[str, Any] | None:
    """Least-squares fit x^2+y^2 = 2*cx*x + 2*cy*y + c."""
    if len(points) < 6:
        return None
    pts = points[np.isfinite(points).all(axis=1)]
    if len(pts) < 6:
        return None
    x = pts[:, 0]
    y = pts[:, 1]
    a = np.column_stack([2.0 * x, 2.0 * y, np.ones_like(x)])
    b = x * x + y * y
    try:
        sol, *_ = np.linalg.lstsq(a, b, rcond=None)
    except np.linalg.LinAlgError:
        return None
    cx, cy, c = [float(v) for v in sol]
    r2 = c + cx * cx + cy * cy
    if not np.isfinite(r2) or r2 <= 0.0:
        return None
    radius = math.sqrt(r2)
    residual = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) - radius
    return {
        "center": [cx, cy],
        "radius": float(radius),
        "rms_residual": float(np.sqrt(np.mean(residual * residual))),
        "points": int(len(pts)),
    }


def circle_fit_tangent_angle(
    circle: dict[str, Any] | None,
    cp: np.ndarray,
    solid_tangent: np.ndarray,
) -> float | None:
    if circle is None:
        return None
    center = np.array(circle["center"], dtype=float)
    interface_radial = normalize(cp.astype(float) - center)
    solid_t = normalize(solid_tangent.astype(float))
    if interface_radial is None or solid_t is None:
        return None
    interface_tangent = normalize(np.array([-interface_radial[1], interface_radial[0]], dtype=float))
    if interface_tangent is None:
        return None
    dot = float(np.clip(abs(np.dot(interface_tangent, solid_t)), -1.0, 1.0))
    return float(math.degrees(math.acos(dot)))


def circle_line_intersections(circle: dict[str, Any] | None, y_value: float = 0.0) -> np.ndarray:
    if circle is None:
        return np.empty((0, 2), dtype=float)
    cx, cy = [float(v) for v in circle["center"]]
    radius = float(circle["radius"])
    inside = radius * radius - (y_value - cy) ** 2
    if inside < -1e-10:
        return np.empty((0, 2), dtype=float)
    dx = math.sqrt(max(0.0, inside))
    return np.array([[cx - dx, y_value], [cx + dx, y_value]], dtype=float)


def circle_circle_intersections(
    circle: dict[str, Any] | None,
    solid_center: tuple[float, float],
    solid_radius: float,
) -> np.ndarray:
    if circle is None or solid_radius <= 0.0:
        return np.empty((0, 2), dtype=float)
    x0, y0 = [float(v) for v in circle["center"]]
    r0 = float(circle["radius"])
    x1, y1 = solid_center
    r1 = float(solid_radius)
    dx = x1 - x0
    dy = y1 - y0
    d = math.hypot(dx, dy)
    if d < 1e-12 or d > r0 + r1 + 1e-10 or d < abs(r0 - r1) - 1e-10:
        return np.empty((0, 2), dtype=float)
    a = (r0 * r0 - r1 * r1 + d * d) / (2.0 * d)
    h2 = r0 * r0 - a * a
    if h2 < -1e-10:
        return np.empty((0, 2), dtype=float)
    h = math.sqrt(max(0.0, h2))
    xm = x0 + a * dx / d
    ym = y0 + a * dy / d
    rx = -dy * h / d
    ry = dx * h / d
    return np.array([[xm + rx, ym + ry], [xm - rx, ym - ry]], dtype=float)


def angle_at_continuous_intersection(
    circle: dict[str, Any] | None,
    point: np.ndarray,
    solid_center: tuple[float, float] | None = None,
) -> float | None:
    if circle is None:
        return None
    interface_center = np.array(circle["center"], dtype=float)
    interface_radial = normalize(point.astype(float) - interface_center)
    if interface_radial is None:
        return None
    interface_tangent = normalize(np.array([-interface_radial[1], interface_radial[0]], dtype=float))
    if interface_tangent is None:
        return None
    if solid_center is None:
        solid_tangent = np.array([1.0, 0.0], dtype=float)
    else:
        solid_radial = normalize(point.astype(float) - np.array(solid_center, dtype=float))
        if solid_radial is None:
            return None
        solid_tangent = normalize(np.array([-solid_radial[1], solid_radial[0]], dtype=float))
        if solid_tangent is None:
            return None
    dot = float(np.clip(abs(np.dot(interface_tangent, solid_tangent)), -1.0, 1.0))
    return float(math.degrees(math.acos(dot)))


def select_intersection(points: np.ndarray, side: str, split_x: float) -> np.ndarray | None:
    if len(points) == 0:
        return None
    if side == "left":
        candidates = points[points[:, 0] < split_x]
    else:
        candidates = points[points[:, 0] >= split_x]
    if len(candidates) == 0:
        return None
    return candidates[np.argmin(np.abs(candidates[:, 0] - split_x))]


def gradient_angle(
    grad_x: np.ndarray,
    grad_y: np.ndarray,
    cp: np.ndarray,
    n_wall: np.ndarray,
) -> float | None:
    rows, cols = grad_x.shape
    c = int(np.clip(round(float(cp[0] - 0.5)), 0, cols - 1))
    r = int(np.clip(round(float(cp[1] - 0.5)), 0, rows - 1))
    g = normalize(np.array([grad_x[r, c], grad_y[r, c]], dtype=float))
    n = normalize(n_wall.astype(float))
    if g is None or n is None:
        return None
    dot = float(np.clip(np.dot(g, n), -1.0, 1.0))
    return float(math.degrees(math.acos(np.clip(-dot, -1.0, 1.0))))


def contact_angles(
    geom: str,
    phi2: np.ndarray,
    center2: tuple[float, float],
    radius: float,
    drop_center2: tuple[float, float],
    contact_tol: float = 2.5,
) -> tuple[list[dict[str, Any]], np.ndarray, dict[str, Any]]:
    pts = extract_contour_points(phi2)
    if pts.size == 0:
        return [], pts, {
            "status": "no_interface_contour",
            "min_abs_surface_distance": None,
            "contact_tolerance": float(contact_tol),
        }
    circle = fit_circle(pts)

    # Gradients in display coordinates: x is horizontal, y is vertical.
    dphi_drow, dphi_dcol = np.gradient(np.nan_to_num(phi2, nan=0.0), 1.0, 1.0)
    grad_x = dphi_dcol
    grad_y = dphi_drow

    out: list[dict[str, Any]] = []
    if geom == "wall":
        wall_distance = pts[:, 1]
        min_abs_surface_distance = float(np.min(np.abs(wall_distance)))
        near = pts[np.abs(wall_distance) <= contact_tol]
        if len(near) == 0:
            return [], pts, {
                "status": "not_contacted",
                "min_abs_surface_distance": min_abs_surface_distance,
                "contact_tolerance": float(contact_tol),
            }
        splits = [
            ("left", near[near[:, 0] < drop_center2[0]]),
            ("right", near[near[:, 0] >= drop_center2[0]]),
        ]
        continuous_points = circle_line_intersections(circle, y_value=0.0)
        for side, candidates in splits:
            if len(candidates) < 2:
                out.append({"side": side, "status": "insufficient_contact_points", "points": int(len(candidates))})
                continue
            cp = candidates[np.argmin(candidates[:, 1])]
            local = pts[np.linalg.norm(pts - cp, axis=1) <= 5.0]
            tangent = local_tangent(local)
            n_wall = np.array([0.0, 1.0])
            solid_tangent = np.array([1.0, 0.0])
            theta_grad = gradient_angle(grad_x, grad_y, cp, n_wall)
            theta_fit = circle_fit_tangent_angle(circle, cp, solid_tangent)
            continuous_cp = select_intersection(continuous_points, side, drop_center2[0])
            theta_intersection = (
                angle_at_continuous_intersection(circle, continuous_cp, None)
                if continuous_cp is not None else None
            )
            theta_tan = None
            if tangent is not None:
                theta_tan = float(math.degrees(math.acos(np.clip(abs(float(tangent[0])), -1.0, 1.0))))
            out.append({
                "side": side,
                "status": "ok",
                "contact_point": [float(cp[0]), float(cp[1])],
                "signed_distance": float(cp[1]),
                "points": int(len(candidates)),
                "local_points": int(len(local)),
                "theta_grad_deg": theta_grad,
                "theta_tangent_abs_deg": theta_tan,
                "theta_circle_fit_abs_deg": theta_fit,
                "continuous_contact_point": [float(v) for v in continuous_cp] if continuous_cp is not None else None,
                "theta_circle_intersection_abs_deg": theta_intersection,
            })
        return out, pts, {
            "status": "contacted" if any(c.get("status") == "ok" for c in out) else "insufficient_contact_points",
            "min_abs_surface_distance": min_abs_surface_distance,
            "contact_tolerance": float(contact_tol),
            "interface_circle_fit": circle,
            "continuous_intersections": continuous_points.tolist(),
            "continuous_angle_note": "theta_circle_intersection_abs_deg uses the fitted phi=0.5 circle and analytic wall intersection.",
            "note": "Angle is diagnostic only unless the initial condition is a validated cap/contact-line setup.",
        }

    cx, cy = center2
    dist = np.sqrt((pts[:, 0] - cx) ** 2 + (pts[:, 1] - cy) ** 2) - radius
    min_abs_surface_distance = float(np.min(np.abs(dist)))
    near_mask = (np.abs(dist) <= contact_tol) & (pts[:, 1] >= cy - 2.0)
    near = pts[near_mask]
    if len(near) == 0:
        return [], pts, {
            "status": "not_contacted",
            "min_abs_surface_distance": min_abs_surface_distance,
            "contact_tolerance": float(contact_tol),
        }
    splits = [
        ("left", near[near[:, 0] < cx]),
        ("right", near[near[:, 0] >= cx]),
    ]
    continuous_points = circle_circle_intersections(circle, center2, radius)
    for side, candidates in splits:
        if len(candidates) < 2:
            out.append({"side": side, "status": "insufficient_contact_points", "points": int(len(candidates))})
            continue
        cand_dist = np.sqrt((candidates[:, 0] - cx) ** 2 + (candidates[:, 1] - cy) ** 2) - radius
        cp = candidates[np.argmin(np.abs(cand_dist))]
        local = pts[np.linalg.norm(pts - cp, axis=1) <= 5.0]
        tangent = local_tangent(local)
        radial = normalize(np.array([cp[0] - cx, cp[1] - cy], dtype=float))
        theta_grad = gradient_angle(grad_x, grad_y, cp, radial) if radial is not None else None
        theta_tan = None
        theta_fit = None
        theta_intersection = None
        continuous_cp = select_intersection(continuous_points, side, cx)
        if tangent is not None and radial is not None:
            solid_tangent = normalize(np.array([-radial[1], radial[0]], dtype=float))
            if solid_tangent is not None:
                theta_tan = float(math.degrees(math.acos(np.clip(abs(float(np.dot(tangent, solid_tangent))), -1.0, 1.0))))
                theta_fit = circle_fit_tangent_angle(circle, cp, solid_tangent)
        if continuous_cp is not None:
            theta_intersection = angle_at_continuous_intersection(circle, continuous_cp, center2)
        out.append({
            "side": side,
            "status": "ok",
            "contact_point": [float(cp[0]), float(cp[1])],
            "signed_distance": float(np.sqrt((cp[0] - cx) ** 2 + (cp[1] - cy) ** 2) - radius),
            "points": int(len(candidates)),
            "local_points": int(len(local)),
            "theta_grad_deg": theta_grad,
            "theta_tangent_abs_deg": theta_tan,
            "theta_circle_fit_abs_deg": theta_fit,
            "continuous_contact_point": [float(v) for v in continuous_cp] if continuous_cp is not None else None,
            "theta_circle_intersection_abs_deg": theta_intersection,
        })
    return out, pts, {
        "status": "contacted" if any(c.get("status") == "ok" for c in out) else "insufficient_contact_points",
        "min_abs_surface_distance": min_abs_surface_distance,
        "contact_tolerance": float(contact_tol),
        "interface_circle_fit": circle,
        "continuous_intersections": continuous_points.tolist(),
        "continuous_angle_note": "theta_circle_intersection_abs_deg uses the fitted phi=0.5 circle and analytic solid intersection.",
        "note": "Angle is diagnostic only unless the initial condition is a validated cap/contact-line setup.",
    }


def classify_audit(
    geom: str,
    metrics: dict[str, Any],
    contact_info: dict[str, Any],
    require_contact: bool,
) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []

    phase = metrics.get("phase", {})
    if phase.get("nonfinite", 0):
        failures.append("PhaseField contains non-finite values")
    if metrics.get("fluid_phase_out_of_range_count", 0):
        failures.append("fluid PhaseField is outside [-0.1, 1.1]")
    if not metrics.get("drop_center_is_fluid", False):
        failures.append("droplet center is not in the fluid domain")

    outside_fraction = metrics.get("outside_far_fluid_fraction")
    if outside_fraction is None or outside_fraction < 0.98:
        failures.append("analytic exterior is not cleanly fluid")
    if geom != "wall":
        inside_fraction = metrics.get("inside_core_solid_fraction")
        if inside_fraction is None or inside_fraction < 0.98:
            failures.append("analytic solid interior is not cleanly solid")

    if contact_info.get("status") != "contacted":
        msg = (
            f"interface is {contact_info.get('status')} "
            f"(min_abs_surface_distance={contact_info.get('min_abs_surface_distance')})"
        )
        if require_contact:
            failures.append(msg)
        else:
            warnings.append(msg)

    if failures:
        status = "FAIL"
    elif contact_info.get("status") == "contacted":
        status = "PASS_RUNTIME_GEOMETRY_CONTACT_DIAGNOSTIC"
    else:
        status = "PASS_RUNTIME_GEOMETRY_NO_CONTACT"

    return {
        "status": status,
        "failures": failures,
        "warnings": warnings,
        "angle_validation": "diagnostic_only_not_a_contact_angle_validation",
    }


def domain_metrics(
    geom: str,
    phase: np.ndarray,
    boundary: np.ndarray,
    analytic: np.ndarray,
    speed: np.ndarray,
    sd: np.ndarray,
    drop_center: tuple[float, float, float],
) -> dict[str, Any]:
    nz, ny, nx = phase.shape
    iz, iy, ix = np.indices(phase.shape, dtype=float)
    interior = (ix > 1) & (ix < nx - 2) & (iy > 1) & (iy < ny - 2) & (iz > 1) & (iz < nz - 2)
    fluid = boundary < 0.5
    solid = boundary > 0.5
    if geom == "wall":
        object_near = interior & (np.abs(sd) <= 2.0)
        inside_core = interior & (sd < 0.5)
        outside_far = interior & (sd > 2.0)
    else:
        object_near = interior & (np.abs(sd) <= 2.0)
        inside_core = interior & (sd < -2.0)
        outside_far = interior & (sd > 2.0)
    dx, dy, dz = (int(round(v)) for v in drop_center)
    in_bounds = 0 <= dx < nx and 0 <= dy < ny and 0 <= dz < nz
    fluid_phase = phase[fluid & np.isfinite(phase)]
    return {
        "grid": [int(nx), int(ny), int(nz)],
        "solid_cells": int(np.count_nonzero(solid)),
        "fluid_cells": int(np.count_nonzero(fluid)),
        "analytic_flag_cells": int(np.count_nonzero(analytic > 0.5)),
        "analytic_near_surface_cells": int(np.count_nonzero((analytic > 0.5) & object_near)),
        "inside_core_cells": int(np.count_nonzero(inside_core)),
        "outside_far_cells": int(np.count_nonzero(outside_far)),
        "inside_core_solid_fraction": float(np.mean(solid[inside_core])) if np.any(inside_core) else None,
        "outside_far_fluid_fraction": float(np.mean(fluid[outside_far])) if np.any(outside_far) else None,
        "phase": finite_stats(phase),
        "fluid_phase_min": float(fluid_phase.min()) if fluid_phase.size else None,
        "fluid_phase_max": float(fluid_phase.max()) if fluid_phase.size else None,
        "fluid_phase_out_of_range_count": int(np.count_nonzero((fluid_phase < -0.1) | (fluid_phase > 1.1))) if fluid_phase.size else 0,
        "speed_max": float(np.nanmax(speed)) if np.isfinite(speed).any() else None,
        "drop_center_index": [dx, dy, dz],
        "drop_center_in_bounds": bool(in_bounds),
        "drop_center_boundary": float(boundary[dz, dy, dx]) if in_bounds else None,
        "drop_center_phase": float(phase[dz, dy, dx]) if in_bounds and np.isfinite(phase[dz, dy, dx]) else None,
        "drop_center_is_fluid": bool(in_bounds and boundary[dz, dy, dx] < 0.5),
    }


def plot_snapshot(
    out_png: Path,
    geom: str,
    phase2: np.ndarray,
    boundary2: np.ndarray,
    analytic2: np.ndarray,
    speed2: np.ndarray,
    wallghost2: np.ndarray,
    extent: list[float],
    center2: tuple[float, float],
    radius: float,
    contacts: list[dict[str, Any]],
    contour_pts: np.ndarray,
    title: str,
) -> None:
    fluid_phase = np.where(boundary2 > 0.5, np.nan, phase2)
    fluid_speed = np.where(boundary2 > 0.5, np.nan, speed2)
    fig, axes = plt.subplots(2, 2, figsize=(10.8, 8.2), constrained_layout=True)
    axes = axes.ravel()
    fig.suptitle(title, fontsize=11, fontweight="bold")

    im0 = axes[0].imshow(fluid_phase, origin="lower", extent=extent, cmap="cividis", vmin=0, vmax=1, interpolation="nearest", aspect="equal")
    if contour_pts.size:
        axes[0].plot(contour_pts[:, 0], contour_pts[:, 1], ".", color="white", ms=1.1, alpha=0.85)
    axes[0].set_title("PhaseField in fluid")
    fig.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.02).set_label("phi")

    im1 = axes[1].imshow(boundary2, origin="lower", extent=extent, cmap="Greys", vmin=0, vmax=1, interpolation="nearest", aspect="equal")
    try:
        axes[1].contour(analytic2, levels=[0.5], colors="#d62728", linewidths=1.0, origin="lower", extent=extent)
    except Exception:
        pass
    axes[1].set_title("Solid mask; red = analytic tag")
    fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.02).set_label("solid")

    vmax_speed = float(np.nanpercentile(fluid_speed, 99.5)) if np.isfinite(fluid_speed).any() else 1.0
    if vmax_speed <= 0:
        vmax_speed = 1e-12
    im2 = axes[2].imshow(fluid_speed, origin="lower", extent=extent, cmap="viridis", vmin=0, vmax=vmax_speed, interpolation="nearest", aspect="equal")
    axes[2].set_title("Velocity magnitude")
    fig.colorbar(im2, ax=axes[2], fraction=0.046, pad=0.02).set_label("|u|")

    im3 = axes[3].imshow(wallghost2, origin="lower", extent=extent, cmap="coolwarm", interpolation="nearest", aspect="equal")
    axes[3].set_title("WallGhost / contact points")
    fig.colorbar(im3, ax=axes[3], fraction=0.046, pad=0.02).set_label("WallGhost")
    if contour_pts.size:
        axes[3].plot(contour_pts[:, 0], contour_pts[:, 1], ".", color="black", ms=1.0, alpha=0.55)
    for c in contacts:
        if c.get("status") != "ok":
            continue
        x, y = c["contact_point"]
        theta = c.get("theta_grad_deg")
        theta_intersection = c.get("theta_circle_intersection_abs_deg")
        theta_fit = c.get("theta_circle_fit_abs_deg")
        label_theta = theta_intersection if theta_intersection is not None else theta_fit if theta_fit is not None else theta
        label = f"{c['side']} n/a" if label_theta is None else f"{c['side']} {label_theta:.1f} deg"
        axes[3].plot(x, y, "o", ms=4, color="#ff7f0e")
        axes[3].text(x + 1, y + 1, label, fontsize=7, color="#111111")

    for ax in axes:
        if geom == "wall":
            ax.set_xlabel("z")
            ax.set_ylabel("y")
        elif geom == "cylinder":
            ax.set_xlabel("perp-1")
            ax.set_ylabel("perp-2")
        else:
            ax.set_xlabel("y")
            ax.set_ylabel("z")
        if geom in {"cylinder", "sphere"}:
            ax.add_patch(Circle(center2, radius, fill=False, ec="#d62728", lw=1.25))
        else:
            ax.add_patch(Rectangle((extent[0], 0), extent[1] - extent[0], 1.0, color="#d62728", alpha=0.35, lw=0))

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=220)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vti", type=Path)
    parser.add_argument("out_png", type=Path)
    parser.add_argument("geom", choices=["wall", "cylinder", "sphere"])
    parser.add_argument("--solid-center", nargs=3, type=float, default=(0.0, 0.0, 0.0))
    parser.add_argument("--solid-radius", type=float, default=0.0)
    parser.add_argument("--cylinder-axis", type=int, choices=[0, 1, 2], default=0)
    parser.add_argument("--drop-center", nargs=3, type=float, required=True)
    parser.add_argument("--drop-radius", type=float, default=0.0)
    parser.add_argument("--plane-axis", type=int, default=1)
    parser.add_argument("--plane-offset", type=float, default=0.0)
    parser.add_argument("--physical-grid", nargs=3, type=int)
    parser.add_argument("--contact-tol", type=float, default=2.5)
    parser.add_argument("--require-contact", action="store_true")
    parser.add_argument("--title", default="")
    args = parser.parse_args()

    dims, arrays = load_vti(args.vti)
    nx, ny, nz = dims
    phase = scalar3(arrays, "PhaseField", dims)
    boundary = scalar3(arrays, "IsItBoundary", dims)
    if "IsItBoundary" not in arrays:
        boundary = scalar3(arrays, "BOUNDARY", dims)
    analytic = scalar3(arrays, "AnalyticFlag", dims)
    wallghost = scalar3(arrays, "WallGhost", dims)
    speed = speed3(arrays, dims)

    if args.physical_grid:
        px, py, pz = [min(v, limit) for v, limit in zip(args.physical_grid, dims)]
        phase = phase[:pz, :py, :px]
        boundary = boundary[:pz, :py, :px]
        analytic = analytic[:pz, :py, :px]
        wallghost = wallghost[:pz, :py, :px]
        speed = speed[:pz, :py, :px]
        dims = (px, py, pz)

    sd = signed_distance(
        args.geom,
        phase.shape,
        tuple(args.solid_center),
        args.solid_radius,
        args.cylinder_axis,
        args.plane_axis,
        args.plane_offset,
    )
    metrics = domain_metrics(args.geom, phase, boundary, analytic, speed, sd, tuple(args.drop_center))

    dx, dy, dz = args.drop_center
    solid_cx, solid_cy, solid_cz = args.solid_center
    if args.geom == "wall":
        ix = int(np.clip(round(dx), 0, phase.shape[2] - 1))
        phase2 = phase[:, :, ix].T
        boundary2 = boundary[:, :, ix].T
        analytic2 = analytic[:, :, ix].T
        wallghost2 = wallghost[:, :, ix].T
        speed2 = speed[:, :, ix].T
        extent = [0, phase.shape[0], 0, phase.shape[1]]
        center2 = (float(dz), 0.0)
        drop_center2 = (float(dz), float(dy))
    elif args.geom == "cylinder":
        if args.cylinder_axis == 0:
            ia = int(np.clip(round(dx), 0, phase.shape[2] - 1))
            phase2 = phase[:, :, ia]
            boundary2 = boundary[:, :, ia]
            analytic2 = analytic[:, :, ia]
            wallghost2 = wallghost[:, :, ia]
            speed2 = speed[:, :, ia]
            extent = [0, phase.shape[1], 0, phase.shape[0]]
            center2 = (float(solid_cy), float(solid_cz))
            drop_center2 = (float(dy), float(dz))
        elif args.cylinder_axis == 1:
            ia = int(np.clip(round(dy), 0, phase.shape[1] - 1))
            phase2 = phase[:, ia, :]
            boundary2 = boundary[:, ia, :]
            analytic2 = analytic[:, ia, :]
            wallghost2 = wallghost[:, ia, :]
            speed2 = speed[:, ia, :]
            extent = [0, phase.shape[2], 0, phase.shape[0]]
            center2 = (float(solid_cx), float(solid_cz))
            drop_center2 = (float(dx), float(dz))
        else:
            ia = int(np.clip(round(dz), 0, phase.shape[0] - 1))
            phase2 = phase[ia, :, :]
            boundary2 = boundary[ia, :, :]
            analytic2 = analytic[ia, :, :]
            wallghost2 = wallghost[ia, :, :]
            speed2 = speed[ia, :, :]
            extent = [0, phase.shape[2], 0, phase.shape[1]]
            center2 = (float(solid_cx), float(solid_cy))
            drop_center2 = (float(dx), float(dy))
    else:
        ix = int(np.clip(round(dx), 0, phase.shape[2] - 1))
        phase2 = phase[:, :, ix]
        boundary2 = boundary[:, :, ix]
        analytic2 = analytic[:, :, ix]
        wallghost2 = wallghost[:, :, ix]
        speed2 = speed[:, :, ix]
        extent = [0, phase.shape[1], 0, phase.shape[0]]
        center2 = (float(solid_cy), float(solid_cz))
        drop_center2 = (float(dy), float(dz))

    phase2_for_contour = np.where(boundary2 > 0.5, np.nan, phase2)
    contacts, contour_pts, contact_info = contact_angles(
        args.geom,
        phase2_for_contour,
        center2,
        args.solid_radius,
        drop_center2,
        contact_tol=args.contact_tol,
    )
    metrics["contact_angles"] = contacts
    metrics["contact_info"] = contact_info
    metrics["contour_point_count"] = int(len(contour_pts))
    metrics["vti"] = str(args.vti)
    metrics["figure"] = str(args.out_png)
    metrics["geometry"] = args.geom
    metrics["solid_center"] = [float(v) for v in args.solid_center]
    metrics["solid_radius"] = float(args.solid_radius)
    metrics["cylinder_axis"] = int(args.cylinder_axis) if args.geom == "cylinder" else None
    metrics["drop_center"] = [float(v) for v in args.drop_center]
    metrics["drop_radius"] = float(args.drop_radius)
    metrics["audit"] = classify_audit(args.geom, metrics, contact_info, args.require_contact)

    title = args.title or f"{args.geom} static wetting audit"
    title = f"{title}\n{metrics['audit']['status']}"
    plot_snapshot(
        args.out_png,
        args.geom,
        phase2,
        boundary2,
        analytic2,
        speed2,
        wallghost2,
        extent,
        center2,
        args.solid_radius,
        contacts,
        contour_pts,
        title,
    )
    out_json = args.out_png.with_suffix(".json")
    out_json.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(metrics, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
