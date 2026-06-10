#!/usr/bin/env python3
"""Create per-frame morphology PNGs for one PRE 2025 sphere case."""

from __future__ import annotations

import argparse
import csv
import math
import re
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


STEP_RE = re.compile(r"_VTK_P\d+_(\d{8})\.vti$")
SOLID_CENTER_Y = 40.0
SOLID_CENTER_Z = 24.0
SOLID_RADIUS = 24.0
TARGET_H1_MINUS_H2 = 19.613732022279812
TARGET_LIQUID_RADIUS = 29.045304538144578
TARGET_CENTER_DISTANCE = 14.568427484135233
TARGET_LIQUID_CENTER_Z = SOLID_CENTER_Z + TARGET_CENTER_DISTANCE


def numeric(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return math.nan
    return out if math.isfinite(out) else math.nan


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


def scalar_array(values: np.ndarray | None) -> np.ndarray | None:
    if values is None:
        return None
    out = values.astype(float)
    if out.ndim > 1:
        out = out[:, 0]
    return out


def reshape_cell_data(values: np.ndarray, dims: tuple[int, int, int]) -> np.ndarray:
    nx, ny, nz = dims
    return values.astype(float).reshape((nz, ny, nx)).transpose(2, 1, 0)


def read_metrics(path: Path) -> dict[int, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    out: dict[int, dict[str, str]] = {}
    for row in rows:
        step = int(numeric(row.get("step")))
        out[step] = row
    return out


def add_reference(ax: plt.Axes, args: argparse.Namespace) -> None:
    target_liquid_center_z = args.solid_center_z + args.target_center_distance
    solid = plt.Circle(
        (args.solid_center_y, args.solid_center_z),
        args.solid_radius,
        facecolor="#d9d9d9",
        edgecolor="#666666",
        linewidth=1.0,
        alpha=0.9,
    )
    target = plt.Circle(
        (args.solid_center_y, target_liquid_center_z),
        args.target_liquid_radius,
        fill=False,
        edgecolor="#111111",
        linestyle="--",
        linewidth=1.1,
        alpha=0.9,
    )
    ax.add_patch(solid)
    ax.add_patch(target)
    ax.axhline(
        args.solid_center_z + args.solid_radius,
        color="#777777",
        linewidth=0.7,
        linestyle=":",
    )
    ax.axhline(
        args.solid_center_z + args.solid_radius + args.target_h1_minus_h2,
        color="#111111",
        linewidth=0.7,
        linestyle="--",
        alpha=0.7,
    )


def section_for(path: Path, args: argparse.Namespace) -> tuple[np.ma.MaskedArray, int, int]:
    dims, arrays = read_vti(path)
    phase_flat = scalar_array(arrays.get("PhaseField"))
    if phase_flat is None:
        raise KeyError(f"PhaseField missing in {path}")
    phase = reshape_cell_data(phase_flat, dims)
    boundary_flat = scalar_array(arrays.get("BOUNDARY"))
    boundary = reshape_cell_data(boundary_flat, dims) if boundary_flat is not None else None
    x_idx = min(max(int(round(args.solid_center_x)), 0), dims[0] - 1)
    section = phase[x_idx, :, :].T
    if boundary is None:
        masked = np.ma.array(section)
    else:
        masked = np.ma.array(section, mask=(boundary[x_idx, :, :].T != 0.0))
    return masked, dims[1], dims[2]


def title_for(step: int, row: dict[str, str] | None) -> str:
    if not row:
        return f"step {step}"
    return (
        f"step {step}, angle={numeric(row.get('fit_contact_angle_deg')):.2f} deg\n"
        f"Herr={numeric(row.get('H1_minus_H2_relative_error_percent')):.2f}%, "
        f"drift={100.0 * numeric(row.get('fluid_phase_sum_rel_change')):.2f}%, "
        f"phi_max={numeric(row.get('phase_max')):.2f}"
    )


def draw_frame(
    ax: plt.Axes,
    path: Path,
    metrics: dict[int, dict[str, str]],
    args: argparse.Namespace,
) -> None:
    step = step_of(path)
    section, ny, nz = section_for(path, args)
    ax.imshow(
        section,
        origin="lower",
        extent=(0, ny, 0, nz),
        cmap="viridis",
        vmin=0.0,
        vmax=1.2,
        aspect="equal",
    )
    y = np.arange(ny)
    z = np.arange(nz)
    yy, zz = np.meshgrid(y, z)
    ax.contour(yy, zz, section, levels=[0.5], colors="white", linewidths=1.2)
    add_reference(ax, args)
    ax.set_xlim(5, 75)
    ax.set_ylim(5, 105)
    ax.set_xlabel(f"y (lu), x={args.solid_center_x:g}")
    ax.set_ylabel("z (lu)")
    ax.set_title(title_for(step, metrics.get(step)), fontsize=9)


def write_individual_frames(
    paths: list[Path],
    metrics: dict[int, dict[str, str]],
    out_dir: Path,
    args: argparse.Namespace,
) -> None:
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for path in paths:
        step = step_of(path)
        fig, ax = plt.subplots(figsize=(6.0, 7.0))
        draw_frame(ax, path, metrics, args)
        fig.tight_layout()
        fig.savefig(frames_dir / f"theta030_frame_{step:06d}.png", dpi=180)
        plt.close(fig)


def write_gallery(
    paths: list[Path],
    metrics: dict[int, dict[str, str]],
    out_path: Path,
    title: str,
    args: argparse.Namespace,
) -> None:
    cols = 3
    rows = math.ceil(len(paths) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(5.2 * cols, 6.0 * rows), squeeze=False)
    for ax in axes.ravel():
        ax.axis("off")
    for ax, path in zip(axes.ravel(), paths):
        ax.axis("on")
        draw_frame(ax, path, metrics, args)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--analysis-subdir", default="analysis_pre2025_sphere")
    parser.add_argument("--title", default="PRE sphere theta030 morphology frames")
    parser.add_argument("--solid-center-x", type=float, default=40.0)
    parser.add_argument("--solid-center-y", type=float, default=SOLID_CENTER_Y)
    parser.add_argument("--solid-center-z", type=float, default=SOLID_CENTER_Z)
    parser.add_argument("--solid-radius", type=float, default=SOLID_RADIUS)
    parser.add_argument("--target-h1-minus-h2", type=float, default=TARGET_H1_MINUS_H2)
    parser.add_argument("--target-liquid-radius", type=float, default=TARGET_LIQUID_RADIUS)
    parser.add_argument("--target-center-distance", type=float, default=TARGET_CENTER_DISTANCE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    paths = sorted((args.case_root / "output").glob("*_VTK_P00_*.vti"), key=step_of)
    metrics = read_metrics(args.case_root / args.analysis_subdir / "pre2025_sphere_metrics.csv")
    write_individual_frames(paths, metrics, args.out_dir, args)
    write_gallery(
        paths,
        metrics,
        args.out_dir / "theta030_frame_gallery.png",
        args.title,
        args,
    )
    print(args.out_dir)


if __name__ == "__main__":
    main()
