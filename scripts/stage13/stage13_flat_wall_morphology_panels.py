#!/usr/bin/env python3
"""Plot Stage13 flat-wall droplet morphology and wall diagnostics.

This is a post-processing tool for the Stage13 flat-wall diagnostic gate. It
reads VTI snapshots, extracts the droplet-center x-slice, overlays the
phi=0.5 interface, and writes visual panels plus machine-readable metrics.

It does not promote any case to validation; figures are diagnostic evidence.
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


DEFAULT_CASES = [
    "diag_wall_t30",
    "diag_wall_t90",
    "diag_wall_t150",
    "decouple_wall_60to30",
    "decouple_wall_120to150",
]


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


def reshape_scalar(arrays: dict[str, np.ndarray], name: str, dims: tuple[int, int, int]) -> np.ndarray | None:
    array = arrays.get(name)
    if array is None:
        return None
    nx, ny, nz = dims
    return array.reshape((nz, ny, nx)).astype(float)


def center_slice(
    arrays: dict[str, np.ndarray],
    dims: tuple[int, int, int],
    x_index: int,
    name: str,
) -> np.ndarray | None:
    arr3 = reshape_scalar(arrays, name, dims)
    if arr3 is None:
        return None
    nx, _ny, _nz = dims
    x_index = int(np.clip(x_index, 0, nx - 1))
    return arr3[:, :, x_index].T


def liquid_probe_x(metadata: dict[str, Any], dims: tuple[int, int, int]) -> int:
    if "liquid_probe" in metadata:
        return int(round(float(metadata["liquid_probe"][0])))
    nx, _ny, _nz = dims
    return nx // 2


def finite_stats(values: np.ndarray) -> dict[str, Any]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {"count": int(values.size), "finite": 0, "min": None, "max": None, "mean": None}
    return {
        "count": int(values.size),
        "finite": int(finite.size),
        "min": float(np.min(finite)),
        "max": float(np.max(finite)),
        "mean": float(np.mean(finite)),
    }


def morphology_metrics(phase: np.ndarray, boundary: np.ndarray | None) -> dict[str, Any]:
    fluid = np.isfinite(phase)
    if boundary is not None:
        fluid &= boundary <= 0.5
    liquid = (phase >= 0.5) & fluid
    if not np.any(liquid):
        return {
            "area_cells": 0,
            "footprint_cells": 0,
            "height_cells": 0,
            "aspect_width_over_height": None,
        }
    yy, xx = np.where(liquid)
    footprint = int(xx.max() - xx.min() + 1)
    height = int(yy.max() + 1)
    return {
        "area_cells": int(liquid.sum()),
        "footprint_cells": footprint,
        "height_cells": height,
        "aspect_width_over_height": float(footprint / height) if height else None,
        "z_min": int(xx.min()),
        "z_max": int(xx.max()),
        "y_max": int(yy.max()),
    }


def load_snapshot(case_dir: Path, step: int | None) -> dict[str, Any]:
    metadata = json.loads((case_dir / "case_metadata.json").read_text(encoding="utf-8"))
    vtis = sorted((case_dir / "output").glob("case_VTK_P00_*.vti"), key=step_of)
    if not vtis:
        raise FileNotFoundError(f"No VTI files found in {case_dir / 'output'}")
    if step is None:
        vti = vtis[-1]
    else:
        matches = [path for path in vtis if step_of(path) == step]
        if not matches:
            raise FileNotFoundError(f"No VTI step {step} in {case_dir}")
        vti = matches[0]
    dims, arrays = load_vti(vti)
    x_index = liquid_probe_x(metadata, dims)
    phase = center_slice(arrays, dims, x_index, "PhaseField")
    boundary = center_slice(arrays, dims, x_index, "IsItBoundary")
    if boundary is None:
        boundary = center_slice(arrays, dims, x_index, "BOUNDARY")
    if phase is None:
        raise KeyError(f"PhaseField missing in {vti}")
    phase_plot = np.where(boundary > 0.5, np.nan, phase) if boundary is not None else phase
    return {
        "case_dir": case_dir,
        "case": case_dir.name,
        "step": step_of(vti),
        "vti": str(vti),
        "dims": dims,
        "metadata": metadata,
        "x_index": x_index,
        "phase": phase_plot,
        "boundary": boundary,
        "wall_ghost_raw": center_slice(arrays, dims, x_index, "WallGhostRaw"),
        "wall_ghost_clamped": center_slice(arrays, dims, x_index, "WallGhostClamped"),
        "wall_ghost_clamp_hit": center_slice(arrays, dims, x_index, "WallGhostClampHit"),
        "wetting_path_id": center_slice(arrays, dims, x_index, "WettingPathId"),
        "local_rad_angle": center_slice(arrays, dims, x_index, "LocalRadAngle"),
        "force_iter_residual": center_slice(arrays, dims, x_index, "ForceIterResidual"),
        "metrics": morphology_metrics(phase, boundary),
        "available_arrays": sorted(arrays.keys()),
    }


def summarize_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    boundary = snapshot["boundary"]
    wall_mask = boundary > 0.5 if boundary is not None else np.zeros_like(snapshot["phase"], dtype=bool)
    path = snapshot["wetting_path_id"]
    clamp = snapshot["wall_ghost_clamp_hit"]
    angle = snapshot["local_rad_angle"]
    residual = snapshot["force_iter_residual"]
    path_hist: dict[str, int] = {}
    if path is not None and np.any(wall_mask):
        finite_path = path[wall_mask & np.isfinite(path)]
        values, counts = np.unique(finite_path, return_counts=True)
        path_hist = {str(float(v)): int(c) for v, c in zip(values, counts)}
    return {
        "case": snapshot["case"],
        "step": snapshot["step"],
        "vti": snapshot["vti"],
        "init_theta_deg": float(snapshot["metadata"]["init_theta_deg"]),
        "bc_theta_deg": float(snapshot["metadata"]["bc_theta_deg"]),
        "decoupled": bool(snapshot["metadata"].get("decoupled", False)),
        "morphology": snapshot["metrics"],
        "phase_stats": finite_stats(snapshot["phase"]),
        "wall_path_histogram": path_hist,
        "wall_ghost_clamp_fraction": (
            float(np.mean(clamp[wall_mask] > 0.5))
            if clamp is not None and np.any(wall_mask)
            else None
        ),
        "wall_local_angle_deg_stats": (
            finite_stats(angle[wall_mask] * 180.0 / math.pi)
            if angle is not None and np.any(wall_mask)
            else None
        ),
        "force_iter_residual_stats": finite_stats(residual) if residual is not None else None,
        "claim_limit": "morphology/diagnostic plot only; not validation_passed",
    }


def plot_case(snapshot: dict[str, Any], out_dir: Path) -> dict[str, str]:
    phase = snapshot["phase"]
    meta = snapshot["metadata"]
    fig, axes = plt.subplots(1, 3, figsize=(12.2, 4.2), constrained_layout=True)

    extent = [0, phase.shape[1], 0, phase.shape[0]]
    im0 = axes[0].imshow(
        phase,
        origin="lower",
        extent=extent,
        cmap="RdBu_r",
        vmin=0.0,
        vmax=1.0,
        interpolation="nearest",
        aspect="equal",
    )
    zz = np.arange(phase.shape[1]) + 0.5
    yy = np.arange(phase.shape[0]) + 0.5
    try:
        axes[0].contour(zz, yy, phase, levels=[0.5], colors="black", linewidths=1.1)
    except ValueError:
        pass
    axes[0].set_title("PhaseField and interface")
    axes[0].set_xlabel("z")
    axes[0].set_ylabel("y")
    axes[0].set_ylim(0, min(48, phase.shape[0]))
    fig.colorbar(im0, ax=axes[0], shrink=0.82, label="phi")

    clamp = snapshot["wall_ghost_clamp_hit"]
    path = snapshot["wetting_path_id"]
    diag = np.zeros_like(phase)
    if path is not None:
        diag = np.where(np.isfinite(path), path, 0.0)
    im1 = axes[1].imshow(diag, origin="lower", extent=extent, cmap="viridis", interpolation="nearest", aspect="equal")
    if clamp is not None:
        hit_y, hit_x = np.where(clamp > 0.5)
        if hit_x.size:
            axes[1].plot(hit_x + 0.5, hit_y + 0.5, "r.", ms=2.0, label="clamp hit")
            axes[1].legend(loc="upper right", fontsize=7)
    axes[1].set_title("WettingPathId / clamp hits")
    axes[1].set_xlabel("z")
    axes[1].set_ylim(0, min(48, phase.shape[0]))
    fig.colorbar(im1, ax=axes[1], shrink=0.82, label="path id")

    residual = snapshot["force_iter_residual"]
    if residual is None:
        residual_plot = np.full_like(phase, np.nan)
    else:
        residual_plot = np.where(residual > 0.0, np.log10(residual + 1.0e-30), np.nan)
    im2 = axes[2].imshow(
        residual_plot,
        origin="lower",
        extent=extent,
        cmap="magma",
        interpolation="nearest",
        aspect="equal",
    )
    axes[2].set_title("log10 force residual")
    axes[2].set_xlabel("z")
    axes[2].set_ylim(0, min(48, phase.shape[0]))
    fig.colorbar(im2, ax=axes[2], shrink=0.82, label="log10 residual")

    title = (
        f"{snapshot['case']} step {snapshot['step']} | "
        f"init {float(meta['init_theta_deg']):.0f} deg, BC {float(meta['bc_theta_deg']):.0f} deg"
    )
    fig.suptitle(title, fontsize=11)
    out_png = out_dir / f"{snapshot['case']}_stage13_wall_morphology_diag.png"
    out_pdf = out_dir / f"{snapshot['case']}_stage13_wall_morphology_diag.pdf"
    fig.savefig(out_png, dpi=220)
    fig.savefig(out_pdf)
    plt.close(fig)
    return {"png": str(out_png), "pdf": str(out_pdf)}


def plot_comparison(snapshots: list[dict[str, Any]], out_dir: Path) -> dict[str, str] | None:
    if not snapshots:
        return None
    ncols = min(3, len(snapshots))
    nrows = int(math.ceil(len(snapshots) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.0 * ncols, 3.5 * nrows), constrained_layout=True)
    axes_arr = np.atleast_1d(axes).reshape(nrows, ncols)
    last_im = None
    for ax in axes_arr.flat:
        ax.axis("off")
    for ax, snapshot in zip(axes_arr.flat, snapshots):
        ax.axis("on")
        phase = snapshot["phase"]
        meta = snapshot["metadata"]
        extent = [0, phase.shape[1], 0, phase.shape[0]]
        last_im = ax.imshow(
            phase,
            origin="lower",
            extent=extent,
            cmap="RdBu_r",
            vmin=0.0,
            vmax=1.0,
            interpolation="nearest",
            aspect="equal",
        )
        zz = np.arange(phase.shape[1]) + 0.5
        yy = np.arange(phase.shape[0]) + 0.5
        try:
            ax.contour(zz, yy, phase, levels=[0.5], colors="black", linewidths=1.0)
        except ValueError:
            pass
        ax.set_ylim(0, min(48, phase.shape[0]))
        ax.set_title(
            f"{snapshot['case']}\ninit {float(meta['init_theta_deg']):.0f}, BC {float(meta['bc_theta_deg']):.0f}, step {snapshot['step']}",
            fontsize=8,
        )
        ax.set_xlabel("z")
        ax.set_ylabel("y")
    if last_im is not None:
        fig.colorbar(last_im, ax=axes_arr, shrink=0.86, pad=0.015, label="PhaseField phi")
    fig.suptitle("Stage13 flat-wall morphology comparison", fontsize=11)
    out_png = out_dir / "stage13_flat_wall_morphology_comparison.png"
    out_pdf = out_dir / "stage13_flat_wall_morphology_comparison.pdf"
    fig.savefig(out_png, dpi=220)
    fig.savefig(out_pdf)
    plt.close(fig)
    return {"png": str(out_png), "pdf": str(out_pdf)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--cases", nargs="+", default=DEFAULT_CASES)
    parser.add_argument("--step", type=int, default=None, help="specific VTI step; default final")
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--allow-missing", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir or (args.run_root / "stage13_wall_morphology_figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    snapshots: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for case in args.cases:
        case_dir = args.run_root / case
        try:
            snapshot = load_snapshot(case_dir, args.step)
        except Exception as exc:
            if not args.allow_missing:
                raise
            errors.append({"case": case, "error": str(exc)})
            continue
        snapshot["figures"] = plot_case(snapshot, out_dir)
        snapshots.append(snapshot)
    comparison = plot_comparison(snapshots, out_dir)
    report = {
        "stage": "stage13_flat_wall_morphology_panels",
        "run_root": str(args.run_root),
        "out_dir": str(out_dir),
        "claim_limit": "exploratory_not_validation morphology diagnostics only",
        "comparison": comparison,
        "cases": [summarize_snapshot(snapshot) | {"figures": snapshot["figures"]} for snapshot in snapshots],
        "errors": errors,
    }
    report_path = out_dir / "stage13_flat_wall_morphology_metrics.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
