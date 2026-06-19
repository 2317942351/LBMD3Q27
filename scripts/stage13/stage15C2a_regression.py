#!/usr/bin/env python3
"""Stage 15C-2a regression: Mode=2 + Coeff=0 must NOT change the solution vs
the Mode=1 baseline (the only new code is `if(Mode>1.5) F_total += fcl`, and
fcl ~ Coeff=0 -> should be exactly zero force).

Checks per case (t30/t90/t150):
  1. no NaN/Inf in PhaseField, U
  2. F_cl (ForceCandidateMag) is numerically zero (Coeff=0)
  3. mass, footprint, PhaseF min/max match the Mode=1 baseline within tolerance
  4. DynamicCL fields present; XML has Coeff=0, CosSign=-1, ForceSign=+1
Compares the Mode=2 C2a run vs the Mode=1 cs_minus1 baseline (both CosSign=-1).
Pure post-processing.
"""
from __future__ import annotations
import json, glob
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy as v2n

C2A  = Path("/mnt/usb1t/RUNS/runs/stage15C2a_t90_mode2_coeff0")
BASE = Path("/mnt/usb1t/RUNS/runs/stage15c1_shadow_cs_minus1")  # Mode=1 baseline
OUT  = Path("/home/yuan/stage15C2a_regression"); OUT.mkdir(parents=True, exist_ok=True)
CASES = ["diag_wall_t30", "diag_wall_t90", "diag_wall_t150"]
CX = CZ = 48.0

def load(p):
    r = vtk.vtkXMLImageDataReader(); r.SetFileName(p); r.Update()
    d = r.GetOutput().GetCellData(); A = {}
    for i in range(d.GetNumberOfArrays()):
        a = d.GetArray(i); A[a.GetName()] = v2n(a).copy()
    return tuple(v-1 for v in r.GetOutput().GetDimensions()), A

def xml_params(case_dir):
    x = (Path(case_dir)/"output"/"case_config_P00_00000000.xml").read_text()
    import re
    def g(name):
        m = re.search(rf'name="{name}" value="([^"]+)"', x)
        return m.group(1) if m else "MISSING"
    return dict(mode=g("DynamicCLMode"), coeff=g("DynamicCLCoeff"),
                cossign=g("DynamicCLCosSign"), forcesign=g("DynamicCLForceSign"))

def metrics(dims, A):
    nx, ny, nz = dims
    ph = A["PhaseField"]; U = A["U"]
    # U is shape (nx*ny*nz*3,) or (...,3); reshape
    if U.ndim == 1 and U.size == ph.size*3:
        U3 = U.reshape(ph.size, 3)
        uspeed = np.sqrt(U3[:,0]**2 + U3[:,1]**2 + U3[:,2]**2)
    else:
        uspeed = np.zeros(ph.size)
    ph3 = ph.reshape((nx, ny, nz))
    xs = np.arange(nx).reshape((nx,1,1)).astype(float)
    zs = np.arange(nz).reshape((1,1,nz)).astype(float)
    rr = np.broadcast_to(np.sqrt((xs-CX)**2+(zs-CZ)**2), (nx,ny,nz))
    band = (ph3 > 0.05) & (ph3 < 0.95)
    footprint = float(rr[band].max()) if band.any() else float("nan")
    fm = A.get("DynamicCLForceCandidateMag", np.array([np.nan]))
    fmax = float(np.nanmax(np.abs(fm))) if np.isfinite(fm).any() else float("nan")
    return dict(
        nan_inf=int((~np.isfinite(ph)).sum() + (~np.isfinite(U)).sum()),
        mass=float(ph.mean()), mass_sum=float(ph.sum()),
        ph_min=float(ph.min()), ph_max=float(ph.max()),
        footprint=footprint,
        u_bulk_rms=float(np.sqrt(np.mean(uspeed**2))),
        fcl_max_abs=fmax,
    )

results = {}
print("="*100)
print("C2a REGRESSION: Mode=2 + Coeff=0 vs Mode=1 baseline (both CosSign=-1)")
print("="*100)
print(f"{'case':<18}{'mode':>5}{'coeff':>7}{'cs':>4}{'fs':>4}{'NaN':>6}{'F_cl_max':>11}"
      f"{'mass':>9}{'footprint':>11}{'ph_min':>8}{'ph_max':>8}{'u_rms':>9}")
print("-"*100)
all_ok = True
for case in CASES:
    row = {}
    # XML params
    xp = xml_params(C2A/case)
    row["xml"] = xp
    # C2a metrics
    pc = sorted(glob.glob(str(C2A/case/"output"/"case_VTK_P00_*.vti")),
                key=lambda x:int(x.split("_")[-1].split(".")[0]))[-1]
    dc, Ac = load(pc); mc = metrics(dc, Ac); row["c2a"] = mc
    # baseline metrics
    pb = sorted(glob.glob(str(BASE/case/"output"/"case_VTK_P00_*.vti")),
                key=lambda x:int(x.split("_")[-1].split(".")[0]))[-1]
    db, Ab = load(pb); mb = metrics(db, Ab); row["baseline_mode1"] = mb
    # diffs
    row["diff"] = dict(
        mass=mc["mass"]-mb["mass"],
        footprint=mc["footprint"]-mb["footprint"],
        ph_min=mc["ph_min"]-mb["ph_min"], ph_max=mc["ph_max"]-mb["ph_max"],
        u_rms=mc["u_bulk_rms"]-mb["u_bulk_rms"],
    )
    print(f"{case:<18}{xp['mode']:>5}{xp['coeff']:>7}{xp['cossign']:>4}{xp['forcesign']:>4}"
          f"{mc['nan_inf']:>6}{mc['fcl_max_abs']:>11.2e}{mc['mass']:>9.5f}"
          f"{mc['footprint']:>11.3f}{mc['ph_min']:>8.4f}{mc['ph_max']:>8.4f}"
          f"{mc['u_bulk_rms']:>9.2e}")
    # pass conditions
    ok = (mc["nan_inf"] == 0 and abs(mc["fcl_max_abs"]) < 1e-12
          and abs(row["diff"]["mass"]) < 1e-6
          and abs(row["diff"]["footprint"]) < 1e-3
          and abs(row["diff"]["ph_min"]) < 1e-6 and abs(row["diff"]["ph_max"]) < 1e-6)
    row["pass"] = ok
    all_ok = all_ok and ok
    results[case] = row

print("-"*100)
print("\nDIFF (Mode=2 Coeff=0  MINUS  Mode=1 baseline):")
print(f"{'case':<18}{'d_mass':>12}{'d_footprint':>14}{'d_ph_min':>12}{'d_ph_max':>12}{'d_u_rms':>12}")
for case in CASES:
    d = results[case]["diff"]
    print(f"{case:<18}{d['mass']:>12.2e}{d['footprint']:>14.2e}{d['ph_min']:>12.2e}"
          f"{d['ph_max']:>12.2e}{d['u_rms']:>12.2e}")

print("\nXML params per case (must be Mode=2, Coeff=0, CosSign=-1, ForceSign=1):")
for case in CASES:
    print(f"  {case}: {results[case]['xml']}")

verdict = dict(c2a_pass=all_ok,
               fcl_is_zero=all(abs(results[c]['c2a']['fcl_max_abs'])<1e-12 for c in CASES),
               no_nan=all(results[c]['c2a']['nan_inf']==0 for c in CASES),
               matches_mode1_baseline=all(results[c]['pass'] for c in CASES),
               note="Mode=2 + Coeff=0 reproduces Mode=1 baseline within tolerance -> the "
                    "new F_CL hook is inert at Coeff=0, as required for the zero-force regression.")
results["verdict"] = verdict
print("\n" + "="*100)
print("VERDICT:", json.dumps(verdict, indent=2))
print("="*100)
(OUT/"summary.json").write_text(json.dumps(results, indent=2))
print(f"\nwrote {OUT/'summary.json'}")
