#!/usr/bin/env python3
"""Stage 14C-2 post-processing: equilibrium 30/90/150 at M=0.3.
Reads shape-angle JSON + final VTI (mass/U/nonfinite). Pure post-processing.
"""
from __future__ import annotations
import csv, glob, json, subprocess, sys
from pathlib import Path
import numpy as np

EQ_ROOT = Path("/home/yuan/stage14c_mobility_sweep/M0.3/equilibrium")
SHAPE = "/home/yuan/lbm2026_stage13_scripts_20260616/stage13_flat_wall_shape_angle.py"
OUT = Path("/home/yuan/stage14c2_post")
OUT.mkdir(parents=True, exist_ok=True)

def load_vti(path):
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy
    r = vtk.vtkXMLImageDataReader(); r.SetFileName(str(path)); r.Update()
    img = r.GetOutput(); d = img.GetCellData(); A = {}
    for i in range(d.GetNumberOfArrays()):
        a = d.GetArray(i); A[a.GetName()] = vtk_to_numpy(a).copy()
    return tuple(v-1 for v in img.GetDimensions()), A

def stats(path):
    dims, A = load_vti(path)
    phase = A["PhaseField"]; isbnd = A["IsItBoundary"]; U = A["U"]
    Umag = np.sqrt((U**2).sum(axis=1)) if U.ndim == 2 else np.abs(U)
    fin = np.isfinite(phase); fluid = fin & (isbnd < 0.5)
    mass = float(phase[fluid].sum()); nf = int((~fin).sum())
    ufin = Umag[np.isfinite(Umag)]; umax = float(ufin.max()) if ufin.size else float("nan")
    return mass, umax, nf

rows = []
for case_dir in sorted(EQ_ROOT.glob("diag_wall_t*")):
    cn = case_dir.name
    tgt = int(cn.split("_t")[1])
    # shape angle
    try:
        subprocess.run([sys.executable, SHAPE, str(case_dir),
                        "--out-dir", str(case_dir/"post"/"shape_angle")],
                       check=True, capture_output=True, text=True, timeout=300)
    except Exception as e:
        print("shape_angle err", cn, e); rows.append({"case":cn,"target":tgt,"error":str(e)}); continue
    sj = case_dir/"post"/"shape_angle"/f"{cn}_stage13_shape_angle.json"
    try: sd = json.loads(sj.read_text())
    except Exception as e: rows.append({"case":cn,"target":tgt,"error":str(e)}); continue
    series = sd.get("theta_shape_series", [])
    th_end = sd.get("theta_shape_end_deg")
    th0 = series[0]["theta_shape_deg"] if series else None
    rms_end = series[-1]["circle"]["rms"] if series else None
    rms0 = series[0]["circle"]["rms"] if series else None
    # mass/U at first and last
    vtis = sorted(glob.glob(str(case_dir/"output"/"case_VTK_P00_*.vti")),
                  key=lambda p: int(p.split("_")[-1].split(".")[0]))
    if not vtis: rows.append({"case":cn,"target":tgt,"error":"no_vti"}); continue
    m0,u0,nf0 = stats(vtis[0]); mE,uE,nfE = stats(vtis[-1])
    err = th_end - tgt if th_end is not None else None
    rows.append({"case":cn,"target":tgt,"theta_end":round(th_end,4) if th_end is not None else None,
                 "theta_err_deg":round(err,4) if err is not None else None,
                 "abs_err_deg":round(abs(err),4) if err is not None else None,
                 "theta_0":round(th0,4) if th0 is not None else None,
                 "RMS_end":round(rms_end,5) if rms_end is not None else None,
                 "RMS_0":round(rms0,5) if rms0 is not None else None,
                 "mass_drift_pct":round(100*(mE-m0)/abs(m0),4) if m0 else None,
                 "maxU_end":uE,"nonfinite_end":nfE})
    print("%s target=%d theta_end=%.3f err=%+.3f abs=%.3f RMS_end=%.4f massdrift=%.3f%% maxU=%.3g nf=%d" % (
        cn, tgt, th_end or 0, err or 0, abs(err) if err is not None else 0,
        rms_end or 0, 100*(mE-m0)/abs(m0) if m0 else 0, uE, nfE))

cols=["case","target","theta_end","theta_err_deg","abs_err_deg","theta_0",
      "RMS_end","RMS_0","mass_drift_pct","maxU_end","nonfinite_end","error"]
with (OUT/"summary.csv").open("w",newline="") as fh:
    w=csv.DictWriter(fh,fieldnames=cols); w.writeheader()
    for r in rows: w.writerow({k:r.get(k,"") for k in cols})
(OUT/"summary.json").write_text(json.dumps(rows,indent=2))
print("\nwritten", OUT/"summary.csv")
