#!/usr/bin/env python3
"""Plot wall-droplet morphology panels from Stage12 VTI snapshots.

The report angle plots are useful diagnostics, but they do not show the actual
phase-field shape. This script reads wall-case VTI files, extracts the center
x-slice, overlays the phi=0.5 interface, and exports comparison figures plus a
small JSON metrics file.
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
import vtk
from vtk.util.numpy_support import vtk_to_numpy


WALL_CASES = [
    "equil_wall_t30",
    "equil_wall_t150",
    "decouple_wall_60to30",
    "decouple_wall_120to150",
]


def step_of(path: Path) -> int:
    match = re.search(r"P00_(\d+)\.vti$", path.name)
    return int(match.group(1)) if match else -1


def load_vti(path: Path) -> tuple[tuple[int, int, int], dict[str, np.ndarray]]:
    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(str(path))
    reader.Update()
    image = reader.GetOutput()
    dims = tuple(int(v) - 1 for v in image.GetDimensions())
    cell_data = image.GetCellData()
    arrays: dict[str, np.ndarray] = {}
    for i in range(cell_data.GetNumberOfArrays()):
        array = cell_data.GetArray(i)
        arrays[array.GetName() or f"array_{i}"] = vtk_to_numpy(array).copy()
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

    # Shape: rows are y, columns are z, matching the wall figure convention.
    phase_2d = phase[:, :, x_index].T
    boundary_2d = boundary_3d[:, :, x_index].T if boundary_3d is not None else None
    return phase_2d, boundary_2d


def morphology_metrics(phase_2d: np.ndarray, boundary_2d: np.ndarray | None) -> dict[str, Any]:
    fluid = np.isfinite(phase_2d)
    if boundary_2d is not None:
        fluid &= boundary_2d <= 0.5
    liquid = (phase_2d >= 0.5) & fluid
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
    aspect = float(footprint / height) if height > 0 else None
    return {
        "area_cells": int(liquid.sum()),
        "footprint_cells": footprint,
        "height_cells": height,
        "aspect_width_over_height": aspect,
        "z_min": int(xx.min()),
        "z_max": int(xx.max()),
        "y_max": int(yy.max()),
    }


def read_angle_summary(case_dir: Path) -> dict[str, Any]:
    path = case_dir / f"{case_dir.name}_shape_angle.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def angle_at_step(angle: dict[str, Any], step: int) -> float | None:
    for item in angle.get("theta_shape_series", []):
        if int(item.get("step", -1)) == int(step):
            theta = item.get("theta_shape_deg")
            return float(theta) if isinstance(theta, (int, float)) and math.isfinite(theta) else None
    theta = angle.get("theta_shape_end_deg")
    return float(theta) if isinstance(theta, (int, float)) and math.isfinite(theta) else None


def load_snapshot(case_dir: Path, step: int | None) -> dict[str, Any]:
    meta = json.loads((case_dir / "case_metadata.json").read_text(encoding="utf-8"))
    vtis = sorted((case_dir / "output").glob("case_VTK_P00_*.vti"), key=step_of)
    if not vtis:
        raise FileNotFoundError(f"No VTI files found in {case_dir / 'output'}")
    if step is None:
        vti = vtis[-1]
    else:
        candidates = [path for path in vtis if step_of(path) == step]
        if not candidates:
            raise FileNotFoundError(f"No VTI step {step} in {case_dir}")
        vti = candidates[0]
    dims, arrays = load_vti(vti)
    x_index = int(round(float(meta["liquid_probe"][0])))
    phase_2d, boundary_2d = wall_center_slice(arrays, dims, x_index)
    if boundary_2d is not None:
        phase_plot = np.where(boundary_2d > 0.5, np.nan, phase_2d)
    else:
        phase_plot = phase_2d
    return {
        "case_dir": case_dir,
        "case": case_dir.name,
        "meta": meta,
        "step": step_of(vti),
        "vti": str(vti),
        "phase": phase_plot,
        "boundary": boundary_2d,
        "metrics": morphology_metrics(phase_2d, boundary_2d),
        "angle": read_angle_summary(case_dir),
    }


def draw_panel(ax: plt.Axes, snap: dict[str, Any], title: str, show_labels: bool = True) -> None:
    phase = snap["phase"]
    meta = snap["meta"]
    angle = snap["angle"]
    extent = [0, phase.shape[1], 0, phase.shape[0]]
    image = ax.imshow(
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
    ax.contour(zz, yy, phase, levels=[0.5], colors="black", linewidths=1.2)
    ax.axhline(0.0, color="0.15", lw=1.0)
    ax.set_xlim(0, phase.shape[1])
    ax.set_ylim(0, min(42, phase.shape[0]))
    ax.set_title(title, fontsize=9)
    if show_labels:
        ax.set_xlabel("z (lattice units)")
        ax.set_ylabel("y (lattice units)")
    else:
        ax.set_xlabel("")
        ax.set_ylabel("")
    theta = angle.get("theta_shape_end_deg")
    theta = angle_at_step(angle, snap["step"])
    theta_text = f"{theta:.1f} deg" if isinstance(theta, (int, float)) and math.isfinite(theta) else "n/a"
    text = (
        f"init {float(meta['init_theta_deg']):.0f}, BC {float(meta['bc_theta_deg']):.0f}\n"
        f"shape {theta_text}, step {snap['step']}"
    )
    ax.text(
        0.02,
        0.96,
        text,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7.5,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "0.65", "alpha": 0.88},
    )
    return image


def final_comparison(root: Path, out_dir: Path, cases: list[str]) -> dict[str, Any]:
    snaps = [load_snapshot(root / case, None) for case in cases]
    fig, axes = plt.subplots(2, 2, figsize=(9.0, 6.2), constrained_layout=True)
    images = []
    for ax, snap in zip(axes.flat, snaps):
        mode = "decoupled" if snap["meta"].get("decoupled") else "equilibrium"
        title = f"{snap['case']} ({mode})"
        images.append(draw_panel(ax, snap, title))
    cbar = fig.colorbar(images[-1], ax=axes, shrink=0.88, pad=0.015)
    cbar.set_label("PhaseField phi")
    fig.suptitle("Stage12 wall droplet morphology at final output", fontsize=11)
    out_png = out_dir / "wall_morphology_final_panels.png"
    out_pdf = out_dir / "wall_morphology_final_panels.pdf"
    fig.savefig(out_png, dpi=240)
    fig.savefig(out_pdf)
    plt.close(fig)
    return {
        "figure_png": str(out_png),
        "figure_pdf": str(out_pdf),
        "snapshots": summarize_snaps(snaps),
    }


def initial_final_comparison(root: Path, out_dir: Path, cases: list[str]) -> dict[str, Any]:
    pairs = [(load_snapshot(root / case, 0), load_snapshot(root / case, 30000)) for case in cases]
    fig, axes = plt.subplots(len(cases), 2, figsize=(8.5, 10.2), constrained_layout=True)
    last_image = None
    for row, (initial, final) in enumerate(pairs):
        last_image = draw_panel(axes[row, 0], initial, f"{initial['case']} initial")
        last_image = draw_panel(axes[row, 1], final, f"{final['case']} final")
    cbar = fig.colorbar(last_image, ax=axes, shrink=0.86, pad=0.015)
    cbar.set_label("PhaseField phi")
    fig.suptitle("Stage12 wall droplet morphology: initial vs final", fontsize=11)
    out_png = out_dir / "wall_morphology_initial_final_panels.png"
    out_pdf = out_dir / "wall_morphology_initial_final_panels.pdf"
    fig.savefig(out_png, dpi=240)
    fig.savefig(out_pdf)
    plt.close(fig)
    return {
        "figure_png": str(out_png),
        "figure_pdf": str(out_pdf),
        "snapshots": summarize_snaps([snap for pair in pairs for snap in pair]),
    }


def summarize_snaps(snaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary = []
    for snap in snaps:
        meta = snap["meta"]
        angle = snap["angle"]
        theta = angle_at_step(angle, snap["step"])
        row = {
            "case": snap["case"],
            "step": snap["step"],
            "init_theta_deg": float(meta["init_theta_deg"]),
            "bc_theta_deg": float(meta["bc_theta_deg"]),
            "decoupled": bool(meta.get("decoupled", False)),
            "theta_shape_deg": theta,
            "theta_error_vs_bc_deg": float(theta - float(meta["bc_theta_deg"]))
            if isinstance(theta, (int, float)) and math.isfinite(theta)
            else None,
            **snap["metrics"],
        }
        summary.append(row)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--cases", nargs="+", default=WALL_CASES)
    args = parser.parse_args()

    out_dir = args.out_dir or args.run_root / "wall_morphology_figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    final = final_comparison(args.run_root, out_dir, args.cases)
    initial_final = initial_final_comparison(args.run_root, out_dir, args.cases)
    summary = {
        "run_root": str(args.run_root),
        "cases": args.cases,
        "final_comparison": final,
        "initial_final_comparison": initial_final,
    }
    summary_path = out_dir / "wall_morphology_metrics.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
