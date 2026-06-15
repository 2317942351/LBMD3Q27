#!/usr/bin/env python3
"""FINAL Stage12 angle analysis: circle-arc-fit tangent angle (robust).

Why this metric (not the gradient angle): single-cell phase-gradient at the
contact line is dominated by lattice-alignment noise (all wall cases collapsed
to ~45 deg regardless of BC). The circle-arc fit measures the INTERFACE SHAPE,
which is what the BC actually controls. At 30k steps the shape is the BC-driven
equilibrium shape (NOT the initialization echo that plagued the 200-step run).

For each VTI in <case_dir>/output/:
  1. extract phi=0.5 contour in the droplet-center slice
  2. fit a circle arc
  3. measure the tangent angle at the contact line (interface tangent vs solid
     surface tangent, through the liquid -> physical contact angle)

Plots a time series. For decoupled cases, the angle must move init->bc.
For equilibrium cases, it must settle near bc (+ model-intrinsic offset).

Usage: python3 stage12_shape_angle_analysis.py <case_dir>
"""
from __future__ import annotations
import argparse, json, math, re, sys
from pathlib import Path
from typing import Any
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy


def load_vti(path):
    r = vtk.vtkXMLImageDataReader(); r.SetFileName(str(path)); r.Update()
    im = r.GetOutput(); dims = tuple(int(v) - 1 for v in im.GetDimensions())
    cd = im.GetCellData(); arr = {}
    for i in range(cd.GetNumberOfArrays()):
        a = cd.GetArray(i); arr[a.GetName() or f"a{i}"] = vtk_to_numpy(a).copy()
    return dims, arr


def step_of(name):
    m = re.search(r"P00_(\d+)\.vti$", name)
    return int(m.group(1)) if m else -1


def get_slice(arrays, dims, geom, drop, sc, srad):
    nx, ny, nz = dims
    ph = arrays.get("PhaseField").reshape((nz, ny, nx)).astype(float)
    bd = arrays.get("IsItBoundary", arrays.get("BOUNDARY"))
    if bd is not None:
        bd = bd.reshape((nz, ny, nx))
    dx, dy, dz = drop
    scx, scy, scz = sc
    if geom == "wall":
        ix = int(np.clip(round(dx), 0, nx - 1))
        p2 = ph[:, :, ix].T; b2 = bd[:, :, ix].T if bd is not None else None
        return p2, b2, (float(dz), 0.0), 0.0, (float(dz), float(dy))
    if geom == "sphere":
        ix = int(np.clip(round(dx), 0, nx - 1))
        p2 = ph[:, :, ix]; b2 = bd[:, :, ix] if bd is not None else None
        return p2, b2, (float(scy), float(scz)), float(srad), (float(dy), float(dz))
    iz = int(np.clip(round(dz), 0, nz - 1))
    p2 = ph[iz, :, :]; b2 = bd[iz, :, :] if bd is not None else None
    return p2, b2, (float(scx), float(scy)), float(srad), (float(dx), float(dy))


def contour(p2, level=0.5):
    pts = []
    rows, cols = p2.shape
    pn = np.where(~np.isfinite(p2), np.nan, p2)
    for r in range(rows):
        for c in range(cols - 1):
            a, b = pn[r, c], pn[r, c + 1]
            if np.isfinite(a) and np.isfinite(b) and a != b and (a - level) * (b - level) <= 0:
                pts.append((c + 0.5 + (level - a) / (b - a), r + 0.5))
    for c in range(cols):
        for r in range(rows - 1):
            a, b = pn[r, c], pn[r + 1, c]
            if np.isfinite(a) and np.isfinite(b) and a != b and (a - level) * (b - level) <= 0:
                pts.append((c + 0.5, r + 0.5 + (level - a) / (b - a)))
    return np.array(pts, dtype=float) if pts else np.empty((0, 2))


def fit_circle(pts):
    if len(pts) < 6:
        return None
    x = pts[:, 0]; y = pts[:, 1]
    A = np.column_stack([2 * x, 2 * y, np.ones_like(x)])
    b = x * x + y * y
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy, c = sol
    r2 = c + cx * cx + cy * cy
    if r2 <= 0:
        return None
    r = math.sqrt(r2)
    res = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) - r
    return {"cx": float(cx), "cy": float(cy), "r": float(r), "rms": float(np.sqrt(np.mean(res ** 2)))}


def tangent_angle(circ, geom, center2, srad):
    """Physical contact angle (through liquid) at the contact line from the
    fitted interface circle. wall: intersect with y=0; curved: circle-circle."""
    if circ is None:
        return None
    if geom == "wall":
        disc = circ["r"] ** 2 - circ["cy"] ** 2
        if disc <= 0:
            return None
        xc = math.sqrt(disc)
        # contact point to the right of center
        px = circ["cx"] + xc; py = 0.0
        rx = px - circ["cx"]; ry = py - circ["cy"]
        rm = math.hypot(rx, ry)
        if rm < 1e-12:
            return None
        # interface tangent (perp to radial), oriented pointing up (+y) into liquid
        tx = ry / rm; ty = -rx / rm
        if ty < 0:
            tx, ty = -tx, -ty
        # wall surface tangent is (1,0); angle through liquid between interface tangent and wall
        # acute part:
        acute = math.degrees(math.acos(max(-1.0, min(1.0, abs(tx)))))
        # if circle center is ABOVE the wall (cy>0), droplet bulges up -> obtuse contact angle
        return 180.0 - acute if circ["cy"] > 0 else acute
    # curved (sphere/cylinder): circle-circle intersection
    x0, y0, r0 = circ["cx"], circ["cy"], circ["r"]
    x1, y1, r1 = center2[0], center2[1], srad
    ddx = x1 - x0; ddy = y1 - y0; dd = math.hypot(ddx, ddy)
    if dd < 1e-12 or dd > r0 + r1 or dd < abs(r0 - r1):
        return None
    a = (r0 ** 2 - r1 ** 2 + dd ** 2) / (2 * dd)
    h2 = r0 ** 2 - a ** 2
    if h2 < 0:
        return None
    h = math.sqrt(h2)
    xm = x0 + a * ddx / dd; ym = y0 + a * ddy / dd
    best = None
    for sg in (1, -1):
        px = xm - sg * h * ddy / dd; py = ym + sg * h * ddx / dd
        if py < y1 - 2:
            continue  # only upper contact
        rix = px - x0; riy = py - y0; rim = math.hypot(rix, riy)
        tix = riy / rim; tiy = -rix / rim
        if tiy < 0:
            tix, tiy = -tix, -tiy
        rsx = px - x1; rsy = py - y1; rsm = math.hypot(rsx, rsy)
        tsx = rsy / rsm; tsy = -rsx / rsm
        if tsy < 0:
            tsx, tsy = -tsx, -tsy
        ang = math.degrees(math.acos(max(-1.0, min(1.0, tix * tsx + tiy * tsy))))
        # obtuse if interface tangent points more outward than solid tangent allows
        # heuristic: if the droplet is taller than wide near contact (bulging), obtuse
        best = ang
        break
    if best is None:
        return None
    # determine acute/obtuse: if circle center is farther from solid center than r1+r0-ish,
    # the cap sits on top -> could be either. Use height of interface circle center vs solid top.
    # Simpler: if interface center y0 is above solid top (y1+r1), droplet perches -> acute;
    # if below, wraps -> obtuse. Approximate:
    if y0 > y1 + r1 * 0.5:
        return best  # acute-ish as computed
    return 180.0 - best


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("case_dir", type=Path)
    p.add_argument("--max-vti", type=int, default=0)
    args = p.parse_args()
    meta = json.loads((args.case_dir / "case_metadata.json").read_text())
    geom = meta["geometry"]
    sc = tuple(meta["solid_center"]); srad = float(meta.get("solid_radius", 0))
    drop = tuple(meta["liquid_probe"])
    init_t = float(meta["init_theta_deg"]); bc_t = float(meta["bc_theta_deg"])
    dec = bool(meta.get("decoupled", False))

    vtis = sorted((args.case_dir / "output").glob("case_VTK_P00_*.vti"), key=lambda q: step_of(q.name))
    if args.max_vti > 0 and len(vtis) > args.max_vti:
        idx = np.linspace(0, len(vtis) - 1, args.max_vti).astype(int)
        vtis = [vtis[i] for i in idx]

    series = []
    for vti in vtis:
        step = step_of(vti.name)
        dims, arrays = load_vti(vti)
        p2, b2, c2, sr, drop2 = get_slice(arrays, dims, geom, drop, sc, srad)
        pf = np.where(b2 > 0.5, np.nan, p2) if b2 is not None else p2
        pts = contour(pf)
        circ = fit_circle(pts)
        ang = tangent_angle(circ, geom, c2, sr)
        series.append({"step": step, "theta_shape_deg": ang,
                       "circle_cy": circ["cy"] if circ else None,
                       "circle_r": circ["r"] if circ else None})
        print(f"  step={step:6d}  theta_shape={ang}  circ_cy={circ['cy'] if circ else None}", file=sys.stderr)

    steps = [s["step"] for s in series]
    angs = [s["theta_shape_deg"] for s in series]
    fin = [a for a in angs if a is not None and math.isfinite(a)]
    if len(fin) >= 3:
        lastq = fin[max(0, 3 * len(fin) // 4):]
        ang_end = float(np.median(lastq)); ang_drift = float(np.std(lastq))
    else:
        ang_end = float("nan"); ang_drift = float("nan")

    mode = "DECOUPLE" if dec else "EQUILIBRIUM"
    fig, ax = plt.subplots(figsize=(8.5, 5.2), constrained_layout=True)
    ax.plot(steps, angs, "o-", color="#1f77b4", lw=1.6, ms=4, label="measured θ (circle-arc fit)")
    if dec:
        ax.axhline(init_t, color="#888", ls="--", lw=1.2, label=f"init θ = {init_t:.0f}°")
        ax.axhline(bc_t, color="#d62728", ls="--", lw=1.4, label=f"BC θ = {bc_t:.0f}°")
    else:
        ax.axhline(bc_t, color="#d62728", ls="--", lw=1.4, label=f"target θ = {bc_t:.0f}°")
    ax.set_xlabel("Iteration"); ax.set_ylabel("Contact angle θ (deg, shape-based)")
    ax.set_title(f"{geom} {mode}: init={init_t:.0f}° bc={bc_t:.0f}°  end={ang_end:.1f}°")
    ax.set_ylim(0, 180); ax.grid(True, alpha=0.3); ax.legend(loc="best", fontsize=9)
    out_png = args.case_dir / f"{args.case_dir.name}_shape_angle.png"
    fig.savefig(out_png, dpi=180); plt.close(fig)

    summary = {
        "case": args.case_dir.name, "mode": mode, "geometry": geom,
        "init_theta_deg": init_t, "bc_theta_deg": bc_t,
        "n_vti": len(series), "n_finite": len(fin),
        "theta_shape_end_deg": ang_end, "theta_shape_end_drift_deg": ang_drift,
        "theta_shape_series": series, "figure": str(out_png),
        "metric": "circle_arc_fit_tangent (robust shape-based, not single-cell gradient)",
    }
    (args.case_dir / f"{args.case_dir.name}_shape_angle.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps({k: v for k, v in summary.items() if k != "theta_shape_series"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
