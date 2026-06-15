#!/usr/bin/env python3
"""Extract contact-angle TIME SERIES from periodic VTK dumps of one case.

For each VTI in <case_dir>/output/, measure the contact angle from the LOCAL
PHASE GRADIENT at the contact line (the BC-response angle, NOT the
fitted-circle-intersection init-echo angle). Output a time series that, for a
decoupled case (init_theta != bc_theta), shows the interface relaxing from
init_theta toward bc_theta. For an equilibrium case, shows whether the angle
has settled to a plateau.

This is the PRIMARY evidence metric for Stage12 validation. The circle-
intersection angle is downgraded to a diagnostic-only column.

Usage:
  python3 stage12_angle_timeseries.py <case_dir> [--out-dir png_dir]

Reads case_metadata.json for init_theta, bc_theta, geometry, solid params.
Requires: vtk, numpy, matplotlib (all on the server).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy


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


def normalize(v: np.ndarray) -> np.ndarray | None:
    n = float(np.linalg.norm(v))
    if not np.isfinite(n) or n < 1e-14:
        return None
    return v / n


def step_from_name(name: str) -> int:
    m = re.search(r"P00_(\d+)\.vti$", name)
    return int(m.group(1)) if m else -1


def measure_gradient_angle(
    geom: str,
    phase2: np.ndarray,
    center2: tuple[float, float],
    radius: float,
    drop_center2: tuple[float, float],
    contact_tol: float = 2.5,
) -> float | None:
    """Measure contact angle from local phase gradient at the contact line.
    Returns the mean over left/right contact points, or None if no contact.

    This mirrors stage12_static_audit.py::gradient_angle logic but returns
    ONLY the gradient-based angle (the BC-response metric)."""
    level = 0.5
    rows, cols = phase2.shape
    # extract phi=0.5 contour points
    pts: list[tuple[float, float]] = []
    pnan = np.where(~np.isfinite(phase2), np.nan, phase2)
    for r in range(rows):
        row = pnan[r, :]
        for c in range(cols - 1):
            a, b = row[c], row[c + 1]
            if not np.isfinite(a) or not np.isfinite(b) or a == b:
                continue
            if (a - level) * (b - level) <= 0.0:
                pts.append((c + 0.5 + (level - a) / (b - a), r + 0.5))
    for c in range(cols):
        col = pnan[:, c]
        for r in range(rows - 1):
            a, b = col[r], col[r + 1]
            if not np.isfinite(a) or not np.isfinite(b) or a == b:
                continue
            if (a - level) * (b - level) <= 0.0:
                pts.append((c + 0.5, r + 0.5 + (level - a) / (b - a)))
    if not pts:
        return None
    pts_arr = np.array(pts, dtype=float)

    dphi_drow, dphi_dcol = np.gradient(np.nan_to_num(phase2, nan=0.0), 1.0, 1.0)
    grad_x = dphi_dcol
    grad_y = dphi_drow

    # find near-surface contact points.
    # ANGLE CONVENTION: phi=1 inside liquid, phi=0 in gas, so grad(phi) points
    # gas->liquid (into droplet interior). The physical contact angle theta
    # (through the liquid) = acos( grad(phi) . n_wall ), n_wall = solid->fluid.
    #   theta=90: vertical interface, grad(phi) horizontal, dot=0 -> 90.
    #   theta=30 (spreading): grad(phi) tilts along n_wall -> dot>0 -> <90.
    # The legacy stage12_static_audit.py used acos(-dot) which gives 180-theta;
    # we use acos(dot). theta_legacy = 180 - theta here.
    if geom == "wall":
        near = pts_arr[np.abs(pts_arr[:, 1]) <= contact_tol]
        if len(near) < 2:
            return None
        n_wall = np.array([0.0, 1.0])
        cx_drop = drop_center2[0]
        sides = [near[near[:, 0] < cx_drop], near[near[:, 0] >= cx_drop]]
        angs = []
        for cand in sides:
            if len(cand) < 1:
                continue
            cp = cand[np.argmin(cand[:, 1])]
            cc = int(np.clip(round(cp[0] - 0.5), 0, cols - 1))
            rr = int(np.clip(round(cp[1] - 0.5), 0, rows - 1))
            g = normalize(np.array([grad_x[rr, cc], grad_y[rr, cc]]))
            if g is None:
                continue
            dot = float(np.clip(np.dot(g, n_wall), -1.0, 1.0))
            angs.append(math.degrees(math.acos(np.clip(dot, -1.0, 1.0))))
        return float(np.mean(angs)) if angs else None
    else:
        cx, cy = center2
        dist = np.sqrt((pts_arr[:, 0] - cx) ** 2 + (pts_arr[:, 1] - cy) ** 2) - radius
        near = pts_arr[(np.abs(dist) <= contact_tol) & (pts_arr[:, 1] >= cy - 2.0)]
        if len(near) < 2:
            return None
        angs = []
        for sign in (-1, 1):
            cand = near[(near[:, 0] - cx) * sign > 0]
            if len(cand) < 1:
                continue
            cd = np.sqrt((cand[:, 0] - cx) ** 2 + (cand[:, 1] - cy) ** 2) - radius
            cp = cand[np.argmin(np.abs(cd))]
            radial = normalize(np.array([cp[0] - cx, cp[1] - cy]))
            if radial is None:
                continue
            cc = int(np.clip(round(cp[0] - 0.5), 0, cols - 1))
            rr = int(np.clip(round(cp[1] - 0.5), 0, rows - 1))
            g = normalize(np.array([grad_x[rr, cc], grad_y[rr, cc]]))
            if g is None:
                continue
            dot = float(np.clip(np.dot(g, radial), -1.0, 1.0))
            angs.append(math.degrees(math.acos(np.clip(dot, -1.0, 1.0))))
        return float(np.mean(angs)) if angs else None


def pick_slice(
    geom: str, arrays: dict[str, np.ndarray], dims: tuple[int, int, int],
    solid_center: tuple[float, float, float], drop_center: tuple[float, float, float],
    plane_axis: int,
) -> tuple[np.ndarray, tuple[float, float], float, tuple[float, float]]:
    """Pick the 2D slice through the droplet center. Returns (phase2, center2, radius, drop_center2)."""
    nx, ny, nz = dims
    phase = scalar3(arrays, "PhaseField", dims)
    boundary = scalar3(arrays, "IsItBoundary", dims)
    if "IsItBoundary" not in arrays:
        boundary = scalar3(arrays, "BOUNDARY", dims)
    phase = np.where(boundary > 0.5, np.nan, phase)

    dx, dy, dz = drop_center
    scx, scy, scz = solid_center
    if geom == "wall":
        ix = int(np.clip(round(dx), 0, phase.shape[2] - 1))
        phase2 = phase[:, :, ix].T
        return phase2, (float(dz), 0.0), 0.0, (float(dz), float(dy))
    if geom == "sphere":
        ix = int(np.clip(round(dx), 0, phase.shape[2] - 1))
        phase2 = phase[:, :, ix]
        return phase2, (float(scy), float(scz)), 20.0, (float(dy), float(dz))
    # cylinder axis = 2 (z): slice in x-y plane at droplet center z
    iz = int(np.clip(round(dz), 0, phase.shape[0] - 1))
    phase2 = phase[iz, :, :]
    return phase2, (float(scx), float(scy)), 20.0, (float(dx), float(dy))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("case_dir", type=Path)
    p.add_argument("--out-dir", type=Path, default=None)
    p.add_argument("--max-vti", type=int, default=0, help="0=all, else limit count (for quick check)")
    args = p.parse_args()

    meta_path = args.case_dir / "case_metadata.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    geom = meta.get("geometry", "wall")
    solid_center = tuple(meta.get("solid_center", [48.0, 0.0, 48.0]))
    solid_radius = float(meta.get("solid_radius", 0.0))
    drop_center = tuple(meta.get("liquid_probe", [48.0, 2.0, 48.0]))
    plane_axis = int(meta.get("plane_axis", 1))
    init_t = float(meta.get("init_theta_deg", 0.0))
    bc_t = float(meta.get("bc_theta_deg", 0.0))
    decoupled = bool(meta.get("decoupled", False))

    vtis = sorted((args.case_dir / "output").glob("case_VTK_P00_*.vti"), key=lambda p: step_from_name(p.name))
    if args.max_vti > 0 and len(vtis) > args.max_vti:
        # subsample evenly
        idx = np.linspace(0, len(vtis) - 1, args.max_vti).astype(int)
        vtis = [vtis[i] for i in idx]

    series: list[dict[str, Any]] = []
    for vti in vtis:
        step = step_from_name(vti.name)
        dims, arrays = load_vti(vti)
        phase2, center2, radius2, drop2 = pick_slice(geom, arrays, dims, solid_center, drop_center, plane_axis)
        ang = measure_gradient_angle(geom, phase2, center2, max(solid_radius, radius2), drop2)
        series.append({"step": step, "theta_grad_deg": ang})
        print(f"  step={step:6d}  theta_grad={ang}", file=sys.stderr)

    # ---- plot ----
    steps = [s["step"] for s in series]
    angs = [s["theta_grad_deg"] for s in series]

    out_dir = args.out_dir or args.case_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    mode = "DECOUPLE" if decoupled else "EQUILIBRIUM"

    fig, ax = plt.subplots(figsize=(8.5, 5.2), constrained_layout=True)
    ax.plot(steps, angs, "o-", color="#1f77b4", lw=1.6, ms=4, label="measured θ (phase gradient)")
    if decoupled:
        ax.axhline(init_t, color="#888888", ls="--", lw=1.2, label=f"init θ = {init_t:.0f}° (cap shape)")
        ax.axhline(bc_t, color="#d62728", ls="--", lw=1.4, label=f"BC θ = {bc_t:.0f}° (radAngle target)")
    else:
        ax.axhline(init_t, color="#d62728", ls="--", lw=1.4, label=f"target θ = {bc_t:.0f}°")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Contact angle θ (deg, from phase gradient)")
    ax.set_title(f"{geom} {mode}: init={init_t:.0f}° bc={bc_t:.0f}°\n(decisive BC-response evidence)")
    ax.set_ylim(0, 180)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=9)

    png = out_dir / f"{args.case_dir.name}_angle_evolution.png"
    fig.savefig(png, dpi=180)
    plt.close(fig)

    # ---- convergence-of-angle summary ----
    # Use the LAST QUARTER (not half) to avoid transient pollution from early
    # cap-relaxation. Use the MEDIAN (not mean) because curved-wall contact-line
    # gradient estimates are noisy (single-cell spikes of 20-150 deg). The last
    # few points' agreement is the real "settled" signal.
    finite_angs = [a for a in angs if a is not None and math.isfinite(a)]
    if len(finite_angs) >= 3:
        last_quarter = finite_angs[max(0, 3 * len(finite_angs) // 4):]
        ang_end = float(np.median(last_quarter))
        ang_drift = float(np.std(last_quarter))
        # also report the very last few raw values for transparency
        last_few = finite_angs[-min(5, len(finite_angs)):]
        ang_last_few_median = float(np.median(last_few))
    else:
        ang_end = float("nan")
        ang_drift = float("nan")
        ang_last_few_median = float("nan")

    summary = {
        "case": args.case_dir.name,
        "mode": mode,
        "geometry": geom,
        "init_theta_deg": init_t,
        "bc_theta_deg": bc_t,
        "n_vti_measured": len(series),
        "n_finite_angles": len(finite_angs),
        "theta_grad_end_deg": ang_end,
        "theta_grad_end_drift_deg": ang_drift,
        "theta_grad_last_few_median_deg": ang_last_few_median,
        "theta_grad_series": series,
        "figure": str(png),
    }
    (args.case_dir / f"{args.case_dir.name}_angle_timeseries.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps({k: v for k, v in summary.items() if k != "theta_grad_series"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
