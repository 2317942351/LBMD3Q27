#!/usr/bin/env python3
"""Postprocess PRE 2025 Table II spherical-surface TCLB analogue cases."""

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


STATUS = "exploratory_not_validation"
STEP_RE = re.compile(r"_VTK_P\d+_(\d{8})\.vti$")
CS = math.sqrt(1.0 / 3.0)


def step_of(path: Path) -> int:
    match = STEP_RE.search(path.name)
    return int(match.group(1)) if match else -1


def read_vti(path: Path) -> tuple[tuple[int, int, int], dict[str, np.ndarray]]:
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy

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


def reshape_cell_data(values: np.ndarray, dims: tuple[int, int, int]) -> np.ndarray:
    nx, ny, nz = dims
    return values.reshape((nz, ny, nx)).transpose(2, 1, 0)


def scalar_array(arr: np.ndarray | None) -> np.ndarray | None:
    if arr is None:
        return None
    values = arr.astype(float)
    if values.ndim > 1:
        values = values[:, 0]
    return values


def vector_magnitude(arr: np.ndarray | None) -> np.ndarray | None:
    if arr is None:
        return None
    values = arr.astype(float)
    if values.ndim == 1:
        return np.abs(values)
    return np.linalg.norm(values[:, :3], axis=1)


def boundary_mask(boundary: np.ndarray | None) -> np.ndarray | None:
    values = scalar_array(boundary)
    if values is None:
        return None
    return np.isfinite(values) & (values != 0.0)


def relative_change(value: float, reference: float) -> float:
    if not math.isfinite(reference) or abs(reference) < 1.0e-30:
        return math.nan
    return (value - reference) / reference


def top_interface_z(phase: np.ndarray, threshold: float) -> float:
    nx, ny, nz = phase.shape
    best = math.nan
    for ix in range(nx):
        for iy in range(ny):
            column = phase[ix, iy, :]
            finite = np.isfinite(column)
            if not finite.any():
                continue
            above = np.where(finite & (column >= threshold))[0]
            if above.size == 0:
                continue
            z0 = int(above[-1])
            if z0 + 1 < nz and np.isfinite(column[z0 + 1]):
                p0 = float(column[z0])
                p1 = float(column[z0 + 1])
                if abs(p1 - p0) > 1.0e-30:
                    frac = (threshold - p0) / (p1 - p0)
                    z_cross = z0 + frac
                else:
                    z_cross = float(z0)
            else:
                z_cross = float(z0)
            if not math.isfinite(best) or z_cross > best:
                best = z_cross
    return best


def contour_points(section: np.ndarray, threshold: float) -> list[np.ndarray]:
    fig, ax = plt.subplots()
    contour = ax.contour(section, levels=[threshold])
    plt.close(fig)
    segments: list[np.ndarray] = []
    collections = getattr(contour, "collections", None)
    if collections is not None:
        for collection in collections:
            for path in collection.get_paths():
                vertices = path.vertices
                if vertices.size:
                    segments.append(vertices)
    elif getattr(contour, "allsegs", None):
        for level_segments in contour.allsegs:
            for vertices in level_segments:
                if vertices.size:
                    segments.append(vertices)
    return segments


def circle_fit(points: np.ndarray) -> tuple[float, float, float]:
    x = points[:, 0]
    z = points[:, 1]
    a = np.column_stack((2.0 * x, 2.0 * z, np.ones_like(x)))
    b = x * x + z * z
    cx, cz, c = np.linalg.lstsq(a, b, rcond=None)[0]
    radius = math.sqrt(max(float(c + cx * cx + cz * cz), 0.0))
    return float(cx), float(cz), radius


def analyze_slice_circle(
    phase_arr: np.ndarray,
    boundary_arr: np.ndarray | None,
    slice_axis: str,
    threshold: float,
    solid_center: tuple[float, float, float],
    solid_radius: float,
    min_points: int,
) -> dict[str, float | int | str]:
    cx, cy, cz = solid_center
    if slice_axis == "x":
        index = int(round(cx))
        section = phase_arr[index, :, :].T
        boundary_section = boundary_arr[index, :, :].T if boundary_arr is not None else None
        tangent_center = cy
    elif slice_axis == "y":
        index = int(round(cy))
        section = phase_arr[:, index, :].T
        boundary_section = boundary_arr[:, index, :].T if boundary_arr is not None else None
        tangent_center = cx
    else:
        raise ValueError(f"unsupported slice_axis={slice_axis}")

    if boundary_section is not None:
        masked = np.ma.array(section, mask=boundary_section)
    else:
        masked = np.ma.array(section)

    segments = contour_points(masked, threshold)
    if not segments:
        return {
            "slice_axis": slice_axis,
            "fit_point_count": 0,
            "contact_angle_deg": math.nan,
            "liquid_fit_radius_lu": math.nan,
            "liquid_fit_center_tangent_lu": math.nan,
            "liquid_fit_center_z_lu": math.nan,
            "liquid_solid_center_distance_lu": math.nan,
        }

    points = np.vstack(segments)
    tangent = points[:, 0]
    z = points[:, 1]
    dist_to_solid = np.sqrt((tangent - tangent_center) ** 2 + (z - cz) ** 2)
    keep = (
        np.isfinite(tangent)
        & np.isfinite(z)
        & (z >= cz - 1.0)
        & (dist_to_solid >= solid_radius - 1.0)
    )
    fit_points = points[keep]
    if fit_points.shape[0] < min_points:
        return {
            "slice_axis": slice_axis,
            "fit_point_count": int(fit_points.shape[0]),
            "contact_angle_deg": math.nan,
            "liquid_fit_radius_lu": math.nan,
            "liquid_fit_center_tangent_lu": math.nan,
            "liquid_fit_center_z_lu": math.nan,
            "liquid_solid_center_distance_lu": math.nan,
        }

    fit_tangent, fit_z, fit_radius = circle_fit(fit_points)
    center_distance = math.sqrt((fit_tangent - tangent_center) ** 2 + (fit_z - cz) ** 2)
    denom = 2.0 * solid_radius * fit_radius
    if denom <= 0.0:
        angle = math.nan
    else:
        cos_theta = (solid_radius**2 + fit_radius**2 - center_distance**2) / denom
        angle = math.degrees(math.acos(max(-1.0, min(1.0, cos_theta))))
    return {
        "slice_axis": slice_axis,
        "fit_point_count": int(fit_points.shape[0]),
        "contact_angle_deg": angle,
        "liquid_fit_radius_lu": fit_radius,
        "liquid_fit_center_tangent_lu": fit_tangent,
        "liquid_fit_center_z_lu": fit_z,
        "liquid_solid_center_distance_lu": center_distance,
    }


def numeric(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def parse_log_csv(root: Path) -> dict[str, Any]:
    candidates = sorted(root.rglob("*_Log_P00_*.csv"))
    if not candidates:
        candidates = sorted(root.rglob("*Log_P00*.csv"))
    if not candidates:
        return {"log_csv": None}
    path = candidates[0]
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
    if not rows:
        return {"log_csv": str(path)}
    final = rows[-1]
    interesting = {
        "log_csv": str(path),
        "log_final_iteration": numeric(final.get("Iteration")),
    }
    for key in [
        "NumSpecialPoints",
        "NumWallBoundaryPoints",
        "NumBoundaryPoints",
        "NumFluidCells",
        "TotalDensity",
        "LiqTotalVelocity",
        "LiqTotalVelocityX",
        "LiqTotalVelocityY",
        "LiqTotalVelocityZ",
        "LiqTotalPhase",
    ]:
        if key in final:
            interesting[f"log_final_{key}"] = numeric(final.get(key))
    for key in ["NumSpecialPoints", "NumWallBoundaryPoints", "NumBoundaryPoints"]:
        values = [numeric(row.get(key)) for row in rows if key in row]
        values = [value for value in values if math.isfinite(value)]
        if values:
            interesting[f"log_max_{key}"] = max(values)
    return interesting


def load_targets(path: Path | None, theta: int | None) -> dict[str, float]:
    if path is None or theta is None or not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            if int(float(row["theta_deg"])) == theta:
                return {
                    "target_expected_Hmax_lu": numeric(row.get("expected_Hmax_lu")),
                    "target_expected_H1_minus_H2_lu": numeric(
                        row.get("expected_H1_minus_H2_lu")
                    ),
                    "target_liquid_spherical_cap_radius_lu": numeric(
                        row.get("liquid_spherical_cap_radius_lu")
                    ),
                    "target_liquid_solid_center_distance_lu": numeric(
                        row.get("liquid_solid_center_distance_lu")
                    ),
                }
    return {}


def row_for_vti(
    path: Path,
    args: argparse.Namespace,
    targets: dict[str, float],
) -> tuple[dict[str, Any], dict[str, Any]]:
    dims, arrays = read_vti(path)
    if "PhaseField" not in arrays:
        raise SystemExit(f"PhaseField missing in {path}")
    phase_flat = scalar_array(arrays["PhaseField"])
    if phase_flat is None:
        raise SystemExit(f"PhaseField empty in {path}")
    phase_arr = reshape_cell_data(phase_flat, dims)

    boundary_flat = scalar_array(arrays.get("BOUNDARY"))
    wall_mask_flat = boundary_mask(arrays.get("BOUNDARY"))
    wall_mask_arr = (
        reshape_cell_data(wall_mask_flat.astype(bool), dims)
        if wall_mask_flat is not None
        else None
    )
    fluid_mask = ~wall_mask_flat if wall_mask_flat is not None else np.ones_like(phase_flat, dtype=bool)
    interface_mask = fluid_mask & (phase_flat >= args.interface_low) & (phase_flat <= args.interface_high)
    near_solid_mask = fluid_mask
    if args.contact_band_lu > 0:
        nx, ny, nz = dims
        grid_x, grid_y, grid_z = np.meshgrid(
            np.arange(nx), np.arange(ny), np.arange(nz), indexing="ij"
        )
        dist = np.sqrt(
            (grid_x.ravel() - args.solid_center_x) ** 2
            + (grid_y.ravel() - args.solid_center_y) ** 2
            + (grid_z.ravel() - args.solid_center_z) ** 2
        )
        near_solid_mask = fluid_mask & (np.abs(dist - args.solid_radius) <= args.contact_band_lu)
    contact_interface_mask = interface_mask & near_solid_mask

    velocity_mag = vector_magnitude(arrays.get("U"))
    rho_flat = scalar_array(arrays.get("Rho"))
    top_z = top_interface_z(phase_arr, args.threshold)
    measured_hmax = top_z - args.solid_center_z if math.isfinite(top_z) else math.nan
    measured_h1_minus_h2 = (
        top_z - (args.solid_center_z + args.solid_radius)
        if math.isfinite(top_z)
        else math.nan
    )

    x_fit = analyze_slice_circle(
        phase_arr,
        wall_mask_arr,
        "x",
        args.threshold,
        (args.solid_center_x, args.solid_center_y, args.solid_center_z),
        args.solid_radius,
        args.min_fit_points,
    )
    y_fit = analyze_slice_circle(
        phase_arr,
        wall_mask_arr,
        "y",
        args.threshold,
        (args.solid_center_x, args.solid_center_y, args.solid_center_z),
        args.solid_radius,
        args.min_fit_points,
    )
    fit_angles = [
        float(x_fit["contact_angle_deg"]),
        float(y_fit["contact_angle_deg"]),
    ]
    fit_angles = [value for value in fit_angles if math.isfinite(value)]
    fit_angle = float(np.mean(fit_angles)) if fit_angles else math.nan

    clipped = np.clip(phase_flat, 0.0, 1.0)
    row: dict[str, Any] = {
        "status": STATUS,
        "step": step_of(path),
        "file": str(path),
        "dims": "x".join(str(value) for value in dims),
        "phase_nonfinite_count": int((~np.isfinite(phase_flat)).sum()),
        "phase_min": float(np.nanmin(phase_flat)),
        "phase_max": float(np.nanmax(phase_flat)),
        "phase_sum": float(np.nansum(phase_flat)),
        "phase_clipped_sum": float(np.nansum(clipped)),
        "fluid_cell_count": int(fluid_mask.sum()),
        "fluid_phase_sum": float(np.nansum(phase_flat[fluid_mask])),
        "fluid_phase_clipped_sum": float(np.nansum(clipped[fluid_mask])),
        "boundary_cell_count": int(wall_mask_flat.sum()) if wall_mask_flat is not None else math.nan,
        "wall_phase_sum": (
            float(np.nansum(phase_flat[wall_mask_flat]))
            if wall_mask_flat is not None
            else math.nan
        ),
        "top_interface_z_lu": top_z,
        "measured_Hmax_lu": measured_hmax,
        "measured_H1_minus_H2_lu": measured_h1_minus_h2,
        "fit_contact_angle_deg": fit_angle,
        "fit_contact_angle_x_slice_deg": x_fit["contact_angle_deg"],
        "fit_contact_angle_y_slice_deg": y_fit["contact_angle_deg"],
        "fit_x_point_count": x_fit["fit_point_count"],
        "fit_y_point_count": y_fit["fit_point_count"],
    }
    if velocity_mag is not None:
        row.update(
            {
                "u_nonfinite_count": int((~np.isfinite(velocity_mag)).sum()),
                "u_max_fluid": float(np.nanmax(velocity_mag[fluid_mask])),
                "u_max_interface_band": (
                    float(np.nanmax(velocity_mag[interface_mask]))
                    if interface_mask.any()
                    else math.nan
                ),
                "u_max_contact_interface_band": (
                    float(np.nanmax(velocity_mag[contact_interface_mask]))
                    if contact_interface_mask.any()
                    else math.nan
                ),
            }
        )
        row["mach_max_fluid"] = row["u_max_fluid"] / CS
        row["mach_max_interface_band"] = (
            row["u_max_interface_band"] / CS
            if math.isfinite(row["u_max_interface_band"])
            else math.nan
        )
    if rho_flat is not None:
        row.update(
            {
                "rho_nonfinite_count": int((~np.isfinite(rho_flat)).sum()),
                "rho_sum": float(np.nansum(rho_flat)),
                "fluid_rho_sum": float(np.nansum(rho_flat[fluid_mask])),
            }
        )
    row.update(targets)
    if targets:
        hmax_target = targets.get("target_expected_Hmax_lu", math.nan)
        h12_target = targets.get("target_expected_H1_minus_H2_lu", math.nan)
        row["Hmax_relative_error_percent"] = (
            abs(measured_hmax - hmax_target) / hmax_target * 100.0
            if math.isfinite(measured_hmax) and math.isfinite(hmax_target) and hmax_target
            else math.nan
        )
        row["H1_minus_H2_relative_error_percent"] = (
            abs(measured_h1_minus_h2 - h12_target) / h12_target * 100.0
            if math.isfinite(measured_h1_minus_h2)
            and math.isfinite(h12_target)
            and h12_target
            else math.nan
        )
    fit_payload = {
        "x_slice": x_fit,
        "y_slice": y_fit,
    }
    return row, fit_payload


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def add_drift_columns(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    refs = {
        "phase_sum": float(rows[0].get("phase_sum", math.nan)),
        "phase_clipped_sum": float(rows[0].get("phase_clipped_sum", math.nan)),
        "fluid_phase_sum": float(rows[0].get("fluid_phase_sum", math.nan)),
        "fluid_phase_clipped_sum": float(rows[0].get("fluid_phase_clipped_sum", math.nan)),
        "rho_sum": float(rows[0].get("rho_sum", math.nan)),
        "fluid_rho_sum": float(rows[0].get("fluid_rho_sum", math.nan)),
    }
    for row in rows:
        for key, ref in refs.items():
            if key in row:
                row[f"{key}_rel_change"] = relative_change(float(row[key]), ref)


def max_abs(rows: list[dict[str, Any]], key: str) -> float:
    values = [abs(float(row[key])) for row in rows if key in row and math.isfinite(float(row[key]))]
    return max(values) if values else math.nan


def make_summary(
    args: argparse.Namespace,
    rows: list[dict[str, Any]],
    final_fit_payload: dict[str, Any],
    log_payload: dict[str, Any],
) -> dict[str, Any]:
    final = rows[-1]
    return {
        "status": STATUS,
        "root": str(args.root),
        "theta_deg": args.theta,
        "frame_count": len(rows),
        "first_step": rows[0]["step"],
        "final_step": final["step"],
        "final": final,
        "fit_payload_final": final_fit_payload,
        "log_payload": log_payload,
        "max_abs_fluid_phase_sum_rel_change": max_abs(rows, "fluid_phase_sum_rel_change"),
        "max_abs_fluid_phase_clipped_sum_rel_change": max_abs(
            rows, "fluid_phase_clipped_sum_rel_change"
        ),
        "max_abs_rho_sum_rel_change": max_abs(rows, "rho_sum_rel_change"),
        "max_abs_fluid_rho_sum_rel_change": max_abs(rows, "fluid_rho_sum_rel_change"),
        "max_mach_fluid": max_abs(rows, "mach_max_fluid"),
        "max_nonfinite_count": max(
            int(row.get("phase_nonfinite_count", 0))
            + int(row.get("u_nonfinite_count", 0))
            + int(row.get("rho_nonfinite_count", 0))
            for row in rows
        ),
        "claim_limit": (
            "Postprocessing output for TCLB analogue only. Requires read-only "
            "audit before any validation_candidate promotion."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-subdir", default="output")
    parser.add_argument("--glob", default="*VTK_P00_*.vti")
    parser.add_argument("--analysis-dir", type=Path)
    parser.add_argument("--targets-csv", type=Path)
    parser.add_argument("--theta", type=int)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--interface-low", type=float, default=0.05)
    parser.add_argument("--interface-high", type=float, default=0.95)
    parser.add_argument("--solid-radius", type=float, default=24.0)
    parser.add_argument("--solid-center-x", type=float, default=40.0)
    parser.add_argument("--solid-center-y", type=float, default=40.0)
    parser.add_argument("--solid-center-z", type=float, default=24.0)
    parser.add_argument("--contact-band-lu", type=float, default=6.0)
    parser.add_argument("--min-fit-points", type=int, default=24)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.root / args.output_subdir
    analysis_dir = args.analysis_dir or (args.root / "analysis_pre2025_sphere")
    analysis_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(output_dir.glob(args.glob), key=step_of)
    if not files:
        raise SystemExit(f"no VTI files matched {output_dir / args.glob}")

    targets = load_targets(args.targets_csv, args.theta)
    rows: list[dict[str, Any]] = []
    final_fit_payload: dict[str, Any] = {}
    for path in files:
        row, fit_payload = row_for_vti(path, args, targets)
        rows.append(row)
        final_fit_payload = fit_payload
    add_drift_columns(rows)
    log_payload = parse_log_csv(args.root)
    summary = make_summary(args, rows, final_fit_payload, log_payload)

    metrics_csv = analysis_dir / "pre2025_sphere_metrics.csv"
    summary_json = analysis_dir / "pre2025_sphere_summary.json"
    write_csv(metrics_csv, rows)
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
