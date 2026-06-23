#!/usr/bin/env python3
"""Plot a static Stage12 cylinder/wall LBM snapshot from a VTI file."""
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import vtk
from matplotlib.patches import Circle, Rectangle
from vtk.util.numpy_support import vtk_to_numpy


def vtk_array(cell_data, name):
    arr = cell_data.GetArray(name)
    if arr is None:
        return None
    return vtk_to_numpy(arr).copy()


def main():
    if len(sys.argv) != 15:
        raise SystemExit(
            "usage: stage12_static_plot.py <vti> <png> <cylinder|wall> "
            "<solid_cx> <solid_cy> <solid_cz> <solid_r> "
            "<drop_x> <drop_y> <drop_z> <drop_r> <phys_nx> <phys_ny> <phys_nz>"
        )

    vti = Path(sys.argv[1])
    out_png = Path(sys.argv[2])
    geom = sys.argv[3]
    solid_cx, solid_cy, solid_cz, solid_r = (float(x) for x in sys.argv[4:8])
    drop_x, drop_y, drop_z, drop_r = (float(x) for x in sys.argv[8:12])
    phys_nx, phys_ny, phys_nz = (int(float(x)) for x in sys.argv[12:15])

    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(str(vti))
    reader.Update()
    data = reader.GetOutput()
    dims = data.GetDimensions()
    nx, ny, nz = dims[0] - 1, dims[1] - 1, dims[2] - 1
    cell_data = data.GetCellData()

    phase = vtk_array(cell_data, "PhaseField")
    boundary = vtk_array(cell_data, "IsItBoundary")
    if boundary is None:
        boundary = vtk_array(cell_data, "BOUNDARY")
    u = vtk_array(cell_data, "U")
    p = vtk_array(cell_data, "P")
    analytic = vtk_array(cell_data, "AnalyticFlag")
    if phase is None or boundary is None:
        raise RuntimeError("PhaseField and boundary arrays are required")

    phase3 = phase.reshape((nz, ny, nx))
    bd3 = boundary.reshape((nz, ny, nx))
    af3 = analytic.reshape((nz, ny, nx)) if analytic is not None else np.zeros_like(phase3)
    p3 = p.reshape((nz, ny, nx)) if p is not None else np.zeros_like(phase3)
    if u is not None and u.ndim == 2 and u.shape[1] >= 3:
        speed3 = np.linalg.norm(u[:, :3], axis=1).reshape((nz, ny, nx))
    else:
        speed3 = np.zeros_like(phase3)

    # Restrict all hard statistics and plotting to the declared physical box.
    px = min(phys_nx, nx)
    py = min(phys_ny, ny)
    pz = min(phys_nz, nz)
    phase3 = phase3[:pz, :py, :px]
    bd3 = bd3[:pz, :py, :px]
    af3 = af3[:pz, :py, :px]
    p3 = p3[:pz, :py, :px]
    speed3 = speed3[:pz, :py, :px]

    if geom == "cylinder":
        ix = int(round(drop_x))
        ix = min(max(ix, 0), px - 1)
        phase_slice = phase3[:, :, ix]
        bd_slice = bd3[:, :, ix]
        speed_slice = speed3[:, :, ix]
        p_slice = p3[:, :, ix]
        af_slice = af3[:, :, ix]
        x_label, y_label = "y (lattice units)", "z (lattice units)"
        extent = [0, py, 0, pz]
        outline = ("circle", (solid_cy, solid_cz), solid_r)
        title_geom = f"cylinder wall, slice x={ix}"
        xlim = (max(0, solid_cy - 34), min(py, solid_cy + 34))
        ylim = (max(0, solid_cz - 18), min(pz, drop_z + drop_r + 12))
    elif geom == "wall":
        ix = int(round(drop_x))
        ix = min(max(ix, 0), px - 1)
        phase_slice = phase3[:, :, ix]
        bd_slice = bd3[:, :, ix]
        speed_slice = speed3[:, :, ix]
        p_slice = p3[:, :, ix]
        af_slice = af3[:, :, ix]
        x_label, y_label = "z (lattice units)", "y (lattice units)"
        # Transpose from (z,y) to y-vs-z for a natural lower-wall view.
        phase_slice = phase_slice.T
        bd_slice = bd_slice.T
        speed_slice = speed_slice.T
        p_slice = p_slice.T
        af_slice = af_slice.T
        extent = [0, pz, 0, py]
        outline = ("wall", None, None)
        title_geom = f"flat lower wall, slice x={ix}"
        xlim = (max(0, drop_z - drop_r - 12), min(pz, drop_z + drop_r + 12))
        ylim = (0, min(py, drop_y + drop_r + 18))
    else:
        raise SystemExit(f"unknown geometry: {geom}")

    fluid_phase = np.where(bd_slice > 0.5, np.nan, phase_slice)
    fluid_speed = np.where(bd_slice > 0.5, np.nan, speed_slice)
    fluid_p = np.where(bd_slice > 0.5, np.nan, p_slice)

    fig, axes = plt.subplots(1, 3, figsize=(12.6, 4.2), constrained_layout=True)
    fig.suptitle(
        f"Static LBM snapshot: {title_geom}, theta=90 deg",
        fontsize=11,
        fontweight="bold",
    )

    im0 = axes[0].imshow(
        fluid_phase,
        origin="lower",
        extent=extent,
        cmap="cividis",
        vmin=0.0,
        vmax=1.0,
        interpolation="nearest",
        aspect="equal",
    )
    axes[0].contour(
        fluid_phase,
        levels=[0.5],
        colors="white",
        linewidths=1.2,
        origin="lower",
        extent=extent,
    )
    axes[0].set_title("Phase field")
    cb0 = fig.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.02)
    cb0.set_label(r"$\phi$")

    im1 = axes[1].imshow(
        bd_slice,
        origin="lower",
        extent=extent,
        cmap="Greys",
        vmin=0.0,
        vmax=1.0,
        interpolation="nearest",
        aspect="equal",
    )
    axes[1].contour(
        af_slice,
        levels=[0.5],
        colors="#d62728",
        linewidths=1.0,
        origin="lower",
        extent=extent,
    )
    axes[1].set_title("Solid mask and analytic tag")
    cb1 = fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.02)
    cb1.set_label("solid mask")

    vmax_speed = float(np.nanpercentile(fluid_speed, 99.5)) if np.isfinite(fluid_speed).any() else 1.0
    if vmax_speed <= 0:
        vmax_speed = 1.0e-12
    im2 = axes[2].imshow(
        fluid_speed,
        origin="lower",
        extent=extent,
        cmap="viridis",
        vmin=0.0,
        vmax=vmax_speed,
        interpolation="nearest",
        aspect="equal",
    )
    finite_p = fluid_p[np.isfinite(fluid_p)]
    if finite_p.size and float(finite_p.max() - finite_p.min()) > 1.0e-14:
        axes[2].contour(
            fluid_p,
            levels=7,
            colors="white",
            linewidths=0.55,
            alpha=0.75,
            origin="lower",
            extent=extent,
        )
    axes[2].set_title("Velocity magnitude")
    cb2 = fig.colorbar(im2, ax=axes[2], fraction=0.046, pad=0.02)
    cb2.set_label(r"$|\mathbf{u}|$")

    for ax in axes:
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        if outline[0] == "circle":
            ax.add_patch(Circle(outline[1], outline[2], fill=False, ec="#d62728", lw=1.4))
        else:
            ax.add_patch(Rectangle((extent[0], 0), extent[1] - extent[0], 1.0,
                                   color="#d62728", alpha=0.35, lw=0))

    summary = {
        "vti": str(vti),
        "output": str(out_png),
        "geometry": geom,
        "vti_grid": [int(nx), int(ny), int(nz)],
        "physical_grid": [int(px), int(py), int(pz)],
        "solid_cells": int((bd3 > 0.5).sum()),
        "fluid_cells": int((bd3 < 0.5).sum()),
        "phase_min": float(np.nanmin(phase3)),
        "phase_max": float(np.nanmax(phase3)),
        "fluid_phase_min": float(np.nanmin(np.where(bd3 > 0.5, np.nan, phase3))),
        "fluid_phase_max": float(np.nanmax(np.where(bd3 > 0.5, np.nan, phase3))),
        "speed_max": float(np.nanmax(speed3)),
        "analytic_flag_cells": int((af3 > 0.5).sum()),
    }
    fig.text(
        0.01,
        0.01,
        f"grid={summary['physical_grid']}, solid={summary['solid_cells']}, "
        f"fluid phi=[{summary['fluid_phase_min']:.3g},{summary['fluid_phase_max']:.3g}], "
        f"max |u|={summary['speed_max']:.3e}",
        fontsize=8,
    )

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=220)
    plt.close(fig)
    out_json = out_png.with_suffix(".json")
    out_json.write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
