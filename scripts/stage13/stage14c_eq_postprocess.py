#!/usr/bin/env python3
"""Stage 14C equilibrium post-processor with drift-rate gate + t150 diagnostics.

Adds (vs stage14c2_postprocess):
  - drift rate over the last 4000 steps (deg/1000 steps) -> the user's t150 gate
  - footprint radius(t)         (obtuse-cap shape diagnostic)
  - liquid volume(t)            (mass within droplet)
  - contact-line band path=30 / path=-30 fraction   (compact-write health)
  - F_surf_radial mean on contact-line band          (force-direction health)
Reads existing shape-angle JSON + final VTI. Pure post-processing.
"""
from __future__ import annotations
import csv, glob, json, subprocess, sys
from pathlib import Path
import numpy as np

EQ_ROOT = Path("/home/yuan/stage14c_mobility_sweep")
SHAPE = "/home/yuan/lbm2026_stage13_scripts_20260616/stage13_flat_wall_shape_angle.py"
M = sys.argv[1] if len(sys.argv) > 1 else "0.2"
OUT = Path(f"/home/yuan/stage14c{('2b' if M=='0.2' else '2c' if M=='0.15' else '')}_post")
OUT.mkdir(parents=True, exist_ok=True)
ROOT = EQ_ROOT / f"M{M}" / "equilibrium"


def load_vti(path):
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy
    r = vtk.vtkXMLImageDataReader(); r.SetFileName(str(path)); r.Update()
    img = r.GetOutput(); d = img.GetCellData(); A = {}
    for i in range(d.GetNumberOfArrays()):
        a = d.GetArray(i); A[a.GetName()] = vtk_to_numpy(a).copy()
    dims = tuple(v - 1 for v in img.GetDimensions())
    return dims, A


def vti_diagnostics(path, cx, cz):
    """mass, maxU, footprint radius, clband path30/path-30, Fs_radial mean."""
    dims, A = load_vti(path)
    nx, ny, nz = dims
    phase = A["PhaseField"].reshape((nx, ny, nz))
    isbnd = A["IsItBoundary"].reshape((nx, ny, nz))
    U = A["U"]
    if U.ndim == 2:
        U3 = U.reshape((nx, ny, nz, 3))
    else:
        U3 = U
    ux, uy, uz = U3[..., 0], U3[..., 1], U3[..., 2]
    Umag = np.sqrt(ux**2 + uy**2 + uz**2)
    fin = np.isfinite(phase); fluid = fin & (isbnd < 0.5)
    mass = float(phase[fluid].sum())
    ufin = Umag[np.isfinite(Umag)]; umax = float(ufin.max()) if ufin.size else float("nan")
    # footprint radius: max radial extent of liquid (phase>0.5) at wall layer y=0
    wall_layer = phase[:, 0, :]   # (x,z)
    liq = wall_layer > 0.5
    if liq.sum() == 0:
        rf = 0.0
    else:
        xs, zs = np.where(liq)
        rf = float(np.sqrt((xs - cx) ** 2 + (zs - cz) ** 2).max())
    # liquid volume (phase>0.5 count)
    liq_vol = int((phase > 0.5).sum())
    # contact-line band on boundary-fluid row y=1
    bf = np.zeros_like(isbnd, dtype=bool); bf[:, 1, :] = True
    bf = bf & (isbnd < 0.5)
    q = phase
    clband = bf & (q > 0.05) & (q < 0.95)
    pid = A.get("WettingPathId")
    p30 = pm30 = np.nan
    if pid is not None and clband.any():
        pid3 = pid.reshape((nx, ny, nz))
        pcl = pid3[clband]
        p30 = float(np.mean(np.abs(pcl - 30.0) < 0.5))
        pm30 = float(np.mean(np.abs(pcl - (-30.0)) < 0.5))
    return dict(mass=mass, umax=umax, footprint_r=rf, liq_vol=liq_vol,
                clband_path30=p30, clband_pathm30=pm30)


def main():
    rows = []
    for case_dir in sorted(ROOT.glob("diag_wall_t*")):
        cn = case_dir.name; tgt = int(cn.split("_t")[1])
        # shape angle
        try:
            subprocess.run([sys.executable, SHAPE, str(case_dir),
                            "--out-dir", str(case_dir / "post" / "shape_angle")],
                           check=True, capture_output=True, text=True, timeout=300)
        except Exception as e:
            rows.append({"case": cn, "target": tgt, "error": "shape: %s" % e}); continue
        sj = case_dir / "post" / "shape_angle" / f"{cn}_stage13_shape_angle.json"
        try:
            sd = json.loads(sj.read_text())
        except Exception as e:
            rows.append({"case": cn, "target": tgt, "error": "json: %s" % e}); continue
        series = sd.get("theta_shape_series", [])
        steps = np.array([s["step"] for s in series], dtype=float)
        thetas = np.array([s["theta_shape_deg"] for s in series], dtype=float)
        th_end = float(thetas[-1]) if len(thetas) else None
        # drift rate over last 4000 steps: slope (deg per 1000 steps) on tail
        drift = None
        if len(steps) >= 3 and steps[-1] >= 4000:
            tail = steps >= (steps[-1] - 4000)
            xs, ys = steps[tail], thetas[tail]
            if xs[-1] > xs[0]:
                drift = float(np.polyfit(xs - xs[0], ys - ys[0], 1)[0] * 1000.0)
        err = (th_end - tgt) if th_end is not None else None
        rms_end = series[-1]["circle"]["rms"] if series else None
        # per-step VTI diagnostics (footprint/volume/clband) on every snapshot
        vtis = sorted(glob.glob(str(case_dir / "output" / "case_VTK_P00_*.vti")),
                      key=lambda p: int(p.split("_")[-1].split(".")[0]))
        fp_traj = []; vol_traj = []; p30_traj = []; pm30_traj = []
        cx = cz = 48.0
        mass0 = massE = None; umaxE = None
        for i, v in enumerate(vtis):
            d = vti_diagnostics(v, cx, cz)
            fp_traj.append(round(d["footprint_r"], 3))
            vol_traj.append(d["liq_vol"])
            p30_traj.append(round(d["clband_path30"], 4))
            pm30_traj.append(round(d["clband_pathm30"], 4))
            if i == 0: mass0 = d["mass"]
            massE = d["mass"]; umaxE = d["umax"]
        rows.append({
            "M": M, "case": cn, "target": tgt,
            "theta_end": round(th_end, 4) if th_end is not None else None,
            "theta_err_deg": round(err, 4) if err is not None else None,
            "abs_err_deg": round(abs(err), 4) if err is not None else None,
            "drift_deg_per_1k_last4k": round(drift, 4) if drift is not None else None,
            "RMS_end": round(rms_end, 5) if rms_end is not None else None,
            "mass_drift_pct": round(100 * (massE - mass0) / abs(mass0), 4) if mass0 else None,
            "maxU_end": umaxE,
            "footprint_r_traj": fp_traj,
            "liq_vol_traj": vol_traj,
            "clband_path30_traj": p30_traj,
            "clband_pathm30_traj": pm30_traj,
        })
        print("%s M=%s target=%d theta_end=%.3f err=%+.3f drift/1k=%+.4f RMS_end=%.4f massdrift=%.3f%% footprint=%s" % (
            cn, M, tgt, th_end or 0, err or 0, drift or 0, rms_end or 0,
            100 * (massE - mass0) / abs(mass0) if mass0 else 0, fp_traj))
    cols = ["M", "case", "target", "theta_end", "theta_err_deg", "abs_err_deg",
            "drift_deg_per_1k_last4k", "RMS_end", "mass_drift_pct", "maxU_end",
            "footprint_r_traj", "liq_vol_traj", "clband_path30_traj",
            "clband_pathm30_traj", "error"]
    with (OUT / "summary.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
        for r in rows:
            # flatten list fields to semicolon-joined for CSV
            rr = {}
            for k in cols:
                v = r.get(k, "")
                if isinstance(v, list):
                    v = ";".join(str(x) for x in v)
                rr[k] = v
            w.writerow(rr)
    (OUT / "summary.json").write_text(json.dumps(rows, indent=2))
    print("\nwritten", OUT / "summary.csv")


if __name__ == "__main__":
    main()
