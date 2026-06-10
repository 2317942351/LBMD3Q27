#!/usr/bin/env python3
"""Audit liquid-film migration along the solid sphere surface.

The audit bins near-solid liquid phase by polar angle measured from the top of
the solid sphere. It is intended for morphology diagnostics only, not
validation.
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


STATUS = "exploratory_not_validation"
STEP_RE = re.compile(r"_VTK_P\d+_(\d{8})\.vti$")


def step_of(path: Path) -> int:
    match = STEP_RE.search(path.name)
    return int(match.group(1)) if match else -1


def read_vti(path: Path) -> tuple[tuple[int, int, int], dict[str, np.ndarray]]:
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


def scalar(values: np.ndarray | None) -> np.ndarray | None:
    if values is None:
        return None
    out = np.asarray(values, dtype=float)
    if out.ndim > 1:
        out = out[:, 0]
    return out


def reshape(values: np.ndarray, dims: tuple[int, int, int]) -> np.ndarray:
    nx, ny, nz = dims
    return np.asarray(values, dtype=float).reshape((nz, ny, nx)).transpose(2, 1, 0)


def weighted_percentile(values: np.ndarray, weights: np.ndarray, pct: float) -> float:
    mask = np.isfinite(values) & np.isfinite(weights) & (weights > 0.0)
    if not np.any(mask):
        return math.nan
    v = values[mask]
    w = weights[mask]
    order = np.argsort(v)
    v = v[order]
    w = w[order]
    cdf = np.cumsum(w)
    target = pct / 100.0 * cdf[-1]
    return float(v[min(int(np.searchsorted(cdf, target, side="left")), v.size - 1)])


def finite_max(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    return float(np.max(finite)) if finite.size else math.nan


def finite_sum(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    return float(np.sum(finite)) if finite.size else 0.0


def numeric(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return math.nan
    return out if math.isfinite(out) else math.nan


def read_global_metrics(case_root: Path, analysis_subdir: str) -> dict[int, dict[str, str]]:
    path = case_root / analysis_subdir / "pre2025_sphere_metrics.csv"
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    return {int(numeric(row.get("step"))): row for row in rows}


def shell_geometry(
    dims: tuple[int, int, int],
    center: tuple[float, float, float],
    radius: float,
    shell_min: float,
    shell_max: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    nx, ny, nz = dims
    x, y, z = np.indices((nx, ny, nz), dtype=float)
    cx, cy, cz = center
    rx = x - cx
    ry = y - cy
    rz = z - cz
    dist = np.sqrt(rx * rx + ry * ry + rz * rz)
    cos_theta = np.divide(rz, dist, out=np.zeros_like(dist), where=dist > 1.0e-12)
    theta = np.degrees(np.arccos(np.clip(cos_theta, -1.0, 1.0)))
    shell = (dist >= radius + shell_min) & (dist <= radius + shell_max)
    return dist, theta, shell


def row_for_frame(
    path: Path,
    args: argparse.Namespace,
    geom_cache: dict[tuple[int, int, int], tuple[np.ndarray, np.ndarray, np.ndarray]],
    global_metrics: dict[int, dict[str, str]],
) -> tuple[dict[str, Any], np.ndarray]:
    dims, arrays = read_vti(path)
    phase_flat = scalar(arrays.get("PhaseField"))
    if phase_flat is None:
        raise KeyError(f"PhaseField missing in {path}")
    phase = reshape(phase_flat, dims)
    boundary_flat = scalar(arrays.get("BOUNDARY"))
    if boundary_flat is None:
        boundary_flat = scalar(arrays.get("IsItBoundary"))
    boundary = reshape(boundary_flat, dims) if boundary_flat is not None else np.zeros(dims)
    fluid = np.isfinite(boundary) & (boundary == 0.0)

    center = (args.solid_center_x, args.solid_center_y, args.solid_center_z)
    if dims not in geom_cache:
        geom_cache[dims] = shell_geometry(
            dims, center, args.solid_radius, args.shell_min, args.shell_max
        )
    _dist, theta, shell = geom_cache[dims]
    z_index = np.indices(dims, dtype=float)[2]
    mask = shell & fluid & np.isfinite(phase) & (phase > args.phase_floor)
    shell_fluid = shell & fluid & np.isfinite(phase)
    theta_values = theta[mask]
    weights = phase[mask]
    total = finite_sum(weights)
    gt05 = mask & (phase >= 0.5)
    gt005 = mask & (phase >= 0.05)

    bins = np.arange(0.0, 180.0 + args.bin_deg, args.bin_deg)
    bin_phi, _ = np.histogram(theta_values, bins=bins, weights=weights)
    bin_count, _ = np.histogram(theta_values, bins=bins)

    def phi_sum_for(theta_low: float) -> float:
        return finite_sum(phase[mask & (theta >= theta_low)])

    lower = phi_sum_for(90.0)
    bottom120 = phi_sum_for(120.0)
    bottom135 = phi_sum_for(135.0)
    bottom150 = phi_sum_for(150.0)
    top60 = finite_sum(phase[mask & (theta <= 60.0)])
    top90 = finite_sum(phase[mask & (theta <= 90.0)])
    zmin_mask = (
        fluid
        & np.isfinite(phase)
        & (phase > args.phase_floor)
        & (z_index <= args.bottom_plane_zmax)
    )
    zmin_outside_sphere_mask = zmin_mask & (_dist >= args.solid_radius + args.shell_min)
    zmin_near_sphere_mask = zmin_mask & (_dist <= args.solid_radius + args.shell_max)
    zmin_outside_sum = finite_sum(phase[zmin_outside_sphere_mask])
    zmin_near_sum = finite_sum(phase[zmin_near_sphere_mask])

    step = step_of(path)
    gm = global_metrics.get(step, {})
    row = {
        "status": STATUS,
        "step": step,
        "file": str(path),
        "dims": "x".join(str(v) for v in dims),
        "shell_min_lu": args.shell_min,
        "shell_max_lu": args.shell_max,
        "phase_floor": args.phase_floor,
        "shell_fluid_cell_count": int(np.count_nonzero(shell_fluid)),
        "shell_liquid_cell_count": int(np.count_nonzero(mask)),
        "shell_phi_sum": total,
        "shell_phi_mean": total / max(int(np.count_nonzero(shell_fluid)), 1),
        "theta_weighted_mean_deg": (
            float(np.average(theta_values, weights=weights)) if total > 0.0 else math.nan
        ),
        "theta_weighted_p90_deg": weighted_percentile(theta_values, weights, 90.0),
        "theta_weighted_p95_deg": weighted_percentile(theta_values, weights, 95.0),
        "theta_weighted_p99_deg": weighted_percentile(theta_values, weights, 99.0),
        "theta_max_phi005_deg": finite_max(theta[gt005]),
        "theta_max_phi05_deg": finite_max(theta[gt05]),
        "theta_gt05_cell_count": int(np.count_nonzero(gt05)),
        "theta_gt005_cell_count": int(np.count_nonzero(gt005)),
        "top60_phi_sum": top60,
        "top90_phi_sum": top90,
        "lower90_phi_sum": lower,
        "bottom120_phi_sum": bottom120,
        "bottom135_phi_sum": bottom135,
        "bottom150_phi_sum": bottom150,
        "zmin_plane_zmax_lu": args.bottom_plane_zmax,
        "zmin_outside_sphere_phi_sum": zmin_outside_sum,
        "zmin_outside_sphere_phi_fraction_of_shell": (
            zmin_outside_sum / total if total > 0.0 else math.nan
        ),
        "zmin_outside_sphere_phi_max": finite_max(phase[zmin_outside_sphere_mask]),
        "zmin_outside_sphere_cell_count": int(np.count_nonzero(zmin_outside_sphere_mask)),
        "zmin_near_sphere_phi_sum": zmin_near_sum,
        "zmin_near_sphere_phi_fraction_of_shell": (
            zmin_near_sum / total if total > 0.0 else math.nan
        ),
        "zmin_near_sphere_phi_max": finite_max(phase[zmin_near_sphere_mask]),
        "zmin_near_sphere_cell_count": int(np.count_nonzero(zmin_near_sphere_mask)),
        "lower90_phi_fraction": lower / total if total > 0.0 else math.nan,
        "bottom120_phi_fraction": bottom120 / total if total > 0.0 else math.nan,
        "bottom135_phi_fraction": bottom135 / total if total > 0.0 else math.nan,
        "bottom150_phi_fraction": bottom150 / total if total > 0.0 else math.nan,
        "bottom150_phi_max": finite_max(phase[mask & (theta >= 150.0)]),
        "global_fit_angle_deg": numeric(gm.get("fit_contact_angle_deg")),
        "global_H1H2_error_percent": numeric(
            gm.get("H1_minus_H2_relative_error_percent")
        ),
        "global_H1H2_lu": numeric(gm.get("measured_H1_minus_H2_lu")),
        "global_fluid_phase_drift_percent": 100.0
        * numeric(gm.get("fluid_phase_sum_rel_change")),
    }
    return row, bin_phi


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_plots(
    rows: list[dict[str, Any]],
    bin_matrix: np.ndarray,
    args: argparse.Namespace,
    out_dir: Path,
) -> None:
    steps = np.array([numeric(row["step"]) for row in rows], dtype=float)
    bins = np.arange(0.0, 180.0 + args.bin_deg, args.bin_deg)
    centers = 0.5 * (bins[:-1] + bins[1:])

    fig, axes = plt.subplots(2, 3, figsize=(15, 8.5))
    panels = [
        ("theta_weighted_p95_deg", "Near-surface liquid p95 polar angle", "deg"),
        ("theta_max_phi05_deg", "Max polar angle with phi >= 0.5", "deg"),
        ("lower90_phi_fraction", "Lower-hemisphere near-surface fraction", "fraction"),
        ("bottom120_phi_fraction", "Bottom theta>120 fraction", "fraction"),
        ("bottom150_phi_max", "Max phi in theta>=150 shell", "phi"),
        (
            "zmin_outside_sphere_phi_fraction_of_shell",
            "z-min outside-sphere liquid / shell liquid",
            "fraction",
        ),
    ]
    for ax, (field, title, ylabel) in zip(axes.ravel(), panels):
        ax.plot(steps, [numeric(row[field]) for row in rows], marker="o")
        ax.set_title(title)
        ax.set_xlabel("step")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.25)
        if "theta" in field or "polar" in title:
            ax.axhline(90.0, color="0.4", linestyle=":", linewidth=0.9)
            ax.axhline(120.0, color="0.4", linestyle="--", linewidth=0.9)
    fig.suptitle("PRE sphere theta030 near-surface film audit")
    fig.tight_layout()
    fig.savefig(out_dir / "surface_film_audit_timeseries.png", dpi=180)
    plt.close(fig)

    normalized = bin_matrix.copy()
    totals = normalized.sum(axis=1)
    normalized = np.divide(
        normalized,
        totals[:, None],
        out=np.zeros_like(normalized),
        where=totals[:, None] > 0.0,
    )
    fig, ax = plt.subplots(figsize=(12, 6))
    im = ax.imshow(
        normalized.T,
        origin="lower",
        aspect="auto",
        extent=(steps[0], steps[-1], centers[0], centers[-1]),
        cmap="magma",
    )
    ax.axhline(90.0, color="white", linestyle=":", linewidth=0.9)
    ax.axhline(120.0, color="white", linestyle="--", linewidth=0.9)
    ax.axhline(150.0, color="white", linestyle="-.", linewidth=0.9)
    ax.set_xlabel("step")
    ax.set_ylabel("solid-sphere polar angle from top (deg)")
    ax.set_title("Normalized near-surface liquid phase distribution")
    fig.colorbar(im, ax=ax, label="bin phi sum / shell phi sum")
    fig.tight_layout()
    fig.savefig(out_dir / "surface_film_polar_heatmap.png", dpi=180)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--analysis-subdir", default="analysis_pre2025_sphere")
    parser.add_argument("--glob", default="*VTK_P00_*.vti")
    parser.add_argument("--solid-center-x", type=float, default=40.0)
    parser.add_argument("--solid-center-y", type=float, default=40.0)
    parser.add_argument("--solid-center-z", type=float, default=24.0)
    parser.add_argument("--solid-radius", type=float, default=24.0)
    parser.add_argument("--shell-min", type=float, default=0.0)
    parser.add_argument("--shell-max", type=float, default=8.0)
    parser.add_argument("--phase-floor", type=float, default=1.0e-6)
    parser.add_argument("--bin-deg", type=float, default=5.0)
    parser.add_argument("--bottom-plane-zmax", type=float, default=8.0)
    parser.add_argument("--plot", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    frames = sorted((args.case_root / "output").glob(args.glob), key=step_of)
    if not frames:
        raise SystemExit(f"no frames matched {args.case_root / 'output' / args.glob}")
    global_metrics = read_global_metrics(args.case_root, args.analysis_subdir)
    geom_cache: dict[tuple[int, int, int], tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    rows: list[dict[str, Any]] = []
    bin_rows: list[np.ndarray] = []
    for frame in frames:
        row, bin_phi = row_for_frame(frame, args, geom_cache, global_metrics)
        rows.append(row)
        bin_rows.append(bin_phi)
    bin_matrix = np.vstack(bin_rows)
    write_csv(rows, args.out_dir / "surface_film_audit_metrics.csv")
    np.savetxt(
        args.out_dir / "surface_film_polar_bin_phi.csv",
        bin_matrix,
        delimiter=",",
    )
    if args.plot:
        write_plots(rows, bin_matrix, args, args.out_dir)

    payload = {
        "status": STATUS,
        "case_root": str(args.case_root),
        "frame_count": len(rows),
        "first_step": rows[0]["step"],
        "final_step": rows[-1]["step"],
        "shell_min_lu": args.shell_min,
        "shell_max_lu": args.shell_max,
        "phase_floor": args.phase_floor,
        "final": rows[-1],
        "max_lower90_phi_fraction": max(
            numeric(row["lower90_phi_fraction"]) for row in rows
        ),
        "max_bottom120_phi_fraction": max(
            numeric(row["bottom120_phi_fraction"]) for row in rows
        ),
        "claim_limit": "Morphology diagnostic only; not validation evidence.",
    }
    (args.out_dir / "surface_film_audit_summary.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
