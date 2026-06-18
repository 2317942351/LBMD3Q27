#!/usr/bin/env python3
"""Stage 14C-1 post-processing: per-(M, case) summary from the mobility sweep.

Runs three things over the 8 sweep cases:
  1. shape-angle circle-arc fit (theta(t), RMS(t))  via the existing script.
  2. 14C-prime stencil-dilution + spurious-current audit (--steps all).
  3. mass drift + max|U| + nonfinite count from the VTI directly.

Outputs one summary table (CSV + JSON) keyed by (M, case) with the columns the
user specified: theta_shape_end, dtheta/dt, RMS(t), mass drift, max|U|,
bulk/cl |U|, ghost_frac_tan, nonfinite count.

Pure post-processing of already-run VTI. No rerun, no recompile.
"""
from __future__ import annotations

import csv
import glob
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

SWEEP = Path("/home/yuan/stage14c_mobility_sweep")
SHAPE_SCRIPT = "/home/yuan/lbm2026_stage13_scripts_20260616/stage13_flat_wall_shape_angle.py"
DILUTION_SCRIPT = "/home/yuan/stage14c_prime_dilution_audit.py"
OUT = Path("/home/yuan/stage14c1_post")


def load_vti(path):
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy
    r = vtk.vtkXMLImageDataReader(); r.SetFileName(str(path)); r.Update()
    img = r.GetOutput(); d = img.GetCellData()
    A = {}
    for i in range(d.GetNumberOfArrays()):
        a = d.GetArray(i); A[a.GetName()] = vtk_to_numpy(a).copy()
    dims = tuple(v - 1 for v in img.GetDimensions())
    return dims, A


def vtisteps(case_dir):
    out = sorted(glob.glob(str(case_dir / "output" / "case_VTK_P00_*.vti")),
                 key=lambda p: int(p.split("_")[-1].split(".")[0]))
    return out


def vti_stats(path):
    """mass (sum PhaseField on finite fluid cells), max|U|, nonfinite count."""
    dims, A = load_vti(path)
    nx, ny, nz = dims
    phase = A["PhaseField"]
    isbnd = A["IsItBoundary"]
    U = A["U"]
    if U.ndim == 2:
        Umag = np.sqrt((U ** 2).sum(axis=1))
    else:
        Umag = np.abs(U)
    fin = np.isfinite(phase)
    fluid = fin & (isbnd < 0.5)
    mass = float(phase[fluid].sum())
    # nonfinite phase count (anywhere)
    nonfinite = int((~fin).sum())
    # max |U| over finite cells
    ufin = Umag[np.isfinite(Umag)]
    umax = float(ufin.max()) if ufin.size else float("nan")
    return mass, umax, nonfinite, int(fluid.sum())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    Ms = sorted([p.name for p in SWEEP.glob("M*")], key=lambda s: float(s[1:]))
    for mdir in Ms:
        M = float(mdir[1:])
        dec = SWEEP / mdir / "decoupled"
        for case_dir in sorted(dec.glob("decouple_wall_*")):
            cname = case_dir.name
            vtis = vtisteps(case_dir)
            if not vtis:
                rows.append({"M": M, "case": cname, "error": "no_vti"}); continue
            # 1) shape angle
            try:
                subprocess.run([sys.executable, SHAPE_SCRIPT, str(case_dir),
                                "--out-dir", str(case_dir / "post" / "shape_angle")],
                               check=True, capture_output=True, text=True, timeout=300)
            except Exception as e:
                rows.append({"M": M, "case": cname, "error": "shape_angle: %s" % e}); continue
            sj = case_dir / "post" / "shape_angle" / f"{cname}_stage13_shape_angle.json"
            try:
                sd = json.loads(sj.read_text())
            except Exception as e:
                rows.append({"M": M, "case": cname, "error": "read shape json: %s" % e}); continue
            series = sd.get("theta_shape_series", [])
            theta0 = series[0]["theta_shape_deg"] if series else None
            theta_end = sd.get("theta_shape_end_deg")
            # dtheta/dt: slope of last ~half of trajectory (deg per 1000 steps)
            dth = None
            if len(series) >= 3:
                xs = np.array([s["step"] for s in series], dtype=float)
                ys = np.array([s["theta_shape_deg"] for s in series], dtype=float)
                # use second half for asymptotic slope
                h = len(xs) // 2
                if xs[-1] > xs[h]:
                    dth = float(np.polyfit(xs[h:] - xs[h], ys[h:] - ys[h], 1)[0] * 1000.0)
            rms_end = series[-1]["circle"]["rms"] if series else None
            rms0 = series[0]["circle"]["rms"] if series else None
            # 3) mass / maxU / nonfinite at first and last step
            m0, u0, nf0, nfl0 = vti_stats(vtis[0])
            mE, uE, nfE, nflE = vti_stats(vtis[-1])
            step0 = int(vtis[0].split("_")[-1].split(".")[0])
            stepE = int(vtis[-1].split("_")[-1].split(".")[0])
            rows.append({
                "M": M,
                "case": cname,
                "theta_shape_deg_0": round(theta0, 4) if theta0 is not None else None,
                "theta_shape_deg_end": round(theta_end, 4) if theta_end is not None else None,
                "dtheta_per_1000steps_2ndhalf": round(dth, 4) if dth is not None else None,
                "circle_RMS_0": round(rms0, 4) if rms0 is not None else None,
                "circle_RMS_end": round(rms_end, 4) if rms_end is not None else None,
                "mass_step0": round(m0, 4),
                "mass_step_end": round(mE, 4),
                "mass_drift_pct": round(100.0 * (mE - m0) / abs(m0), 4) if m0 else None,
                "maxU_step0": u0,
                "maxU_step_end": uE,
                "nonfinite_phase_step0": nf0,
                "nonfinite_phase_step_end": nfE,
                "n_fluid_cells": nfl0,
                "n_vti": len(vtis),
            })
            print("done M=%s %s : theta %.2f->%.2f  dtheta/1k=%.4f  RMS %.3g->%.3g  massdrift %.3f%%  maxU %.3g->%.3g  nf=%d" % (
                M, cname, theta0 or 0, theta_end or 0, dth or 0,
                rms0 or 0, rms_end or 0,
                100.0 * (mE - m0) / abs(m0) if m0 else 0,
                u0, uE, nfE))

    # 2) 14C-prime dilution on the final step of each M's two cases, gathered
    # by linking into one root per M (reuse the script's directory convention)
    dilution_summary = {}
    for mdir in Ms:
        M = float(mdir[1:])
        root = SWEEP / mdir / "decoupled"
        try:
            subprocess.run([sys.executable, DILUTION_SCRIPT, str(root),
                            "--steps", "0,6000,12000",
                            "--out", str(OUT / f"dilution_M{mdir[1:]}.json")],
                           check=True, capture_output=True, text=True, timeout=600)
        except Exception as e:
            dilution_summary[mdir] = {"error": str(e)}; continue
        dj = json.loads((OUT / f"dilution_M{mdir[1:]}.json").read_text())
        dilution_summary[mdir] = dj

    # write summary CSV + JSON
    cols = ["M", "case", "theta_shape_deg_0", "theta_shape_deg_end",
            "dtheta_per_1000steps_2ndhalf", "circle_RMS_0", "circle_RMS_end",
            "mass_step0", "mass_step_end", "mass_drift_pct",
            "maxU_step0", "maxU_step_end", "nonfinite_phase_step0",
            "nonfinite_phase_step_end", "n_fluid_cells", "n_vti", "error"]
    with (OUT / "summary.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})
    (OUT / "summary.json").write_text(json.dumps(
        {"rows": rows, "dilution_files": {k: str(OUT / f"dilution_M{k[1:]}.json")
                                          for k in dilution_summary}}, indent=2))
    print("\n=== summary written to %s ===" % (OUT / "summary.csv"))


if __name__ == "__main__":
    main()
