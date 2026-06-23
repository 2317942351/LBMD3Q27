#!/usr/bin/env python3
"""C2f-0: t90 equilibrium safety smoke at ForceCap=0.2 (max F_cl=3.333e-6, 10x).
Must confirm the larger force ceiling does NOT perturb equilibrium:
  - Fcl_max ~ 3.33e-6 (or below, since R_theta~0.029 at t90)
  - no NaN, 0 spurious fluid force nodes
  - mass/footprint/PhaseF/theta_app stable vs the Coeff=0 baseline (C2a)
Pure post-processing.
"""
from __future__ import annotations
import json, glob, re
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy as v2n

C2F = Path("/mnt/usb1t/RUNS/runs/stage15C2f0_t90_cap0p2/diag_wall_t90")
C2A = Path("/mnt/usb1t/RUNS/runs/stage15C2a_t90_mode2_coeff0/diag_wall_t90")
OUT = Path("/home/yuan/stage15C2f0_regression"); OUT.mkdir(parents=True, exist_ok=True)
CX = CZ = 48.0

def load(p):
    r = vtk.vtkXMLImageDataReader(); r.SetFileName(p); r.Update()
    d = r.GetOutput().GetCellData(); A = {}
    for i in range(d.GetNumberOfArrays()):
        a = d.GetArray(i); A[a.GetName()] = v2n(a).copy()
    return tuple(v-1 for v in r.GetOutput().GetDimensions()), A

def last(cd):
    vs = sorted(glob.glob(str(Path(cd)/"output"/"case_VTK_P00_*.vti")),
                key=lambda x:int(x.split("_")[-1].split(".")[0]))
    return vs[-1]

def analyze(cd, label):
    dims, A = load(last(cd)); nx, ny, nz = dims
    ph = A["PhaseField"]; U = A["U"]
    U3 = U.reshape(ph.size,3) if U.size==ph.size*3 else np.zeros((ph.size,3))
    uspeed = np.sqrt(U3[:,0]**2+U3[:,1]**2+U3[:,2]**2)
    ph3 = ph.reshape((nx,ny,nz))
    xs = np.arange(nx).reshape((nx,1,1)).astype(float); zs = np.arange(nz).reshape((1,1,nz)).astype(float)
    rr = np.broadcast_to(np.sqrt((xs-CX)**2+(zs-CZ)**2),(nx,ny,nz))
    band = (ph3>0.05)&(ph3<0.95)
    footprint = float(rr[band].max()) if band.any() else float("nan")
    fmag = A["DynamicCLForceCandidateMag"].reshape((nx,ny,nz))
    isb = A["IsItBoundary"].reshape((nx,ny,nz)); act = A["DynamicCLActive"].reshape((nx,ny,nz))
    cr = A["DynamicCLCosResidual"].reshape((nx,ny,nz)); capp = A["DynamicCLCosApp"].reshape((nx,ny,nz))
    m = (act>0.5)&(isb<0.5)&band
    cap = 0.2 * 5e-5/3.0  # NEW cap at ForceCap=0.2
    active_fmag = fmag[m]
    capped_frac = float(np.mean(active_fmag >= cap*0.999)) if active_fmag.size else 0.0
    spurious = int(((fmag>0)&(isb<0.5)&~(act>0.5)).sum())
    capp_m = float(capp[m].mean()) if m.any() else float("nan")
    theta_app = float(np.degrees(np.arccos(np.clip(capp_m,-1,1)))) if m.any() else float("nan")
    return dict(label=label,
        nan_inf=int((~np.isfinite(ph)).sum()+(~np.isfinite(U)).sum()+(~np.isfinite(fmag.reshape(-1))).sum()),
        mass=float(ph.mean()), ph_min=float(ph.min()), ph_max=float(ph.max()),
        footprint=footprint, u_max=float(uspeed.max()),
        fcl_max=float(fmag.max()), capped_frac=capped_frac,
        spurious_fluid=spurious, active_nodes=int(m.sum()),
        R_abs_mean=float(np.mean(np.abs(cr[m]))) if m.any() else float("nan"),
        theta_app=theta_app, cap_value=cap)

f = analyze(C2F, "C2f-0 ForceCap=0.2 Coeff=2")
a = analyze(C2A, "C2a Coeff=0 baseline")

print("="*100)
print("C2f-0: t90 equilibrium safety smoke  ForceCap=0.2 (max F_cl=3.333e-6, 10x)")
print("="*100)
print(f"{'metric':<28}{'C2f-0(cap=0.2)':>18}{'C2a(cap=0.02,Co=0)':>22}{'diff':>14}")
print("-"*100)
for k,lab in [("nan_inf","NaN/Inf"),("mass","mass"),("footprint","footprint"),
              ("ph_min","ph_min"),("ph_max","ph_max"),("u_max","|U|max"),
              ("fcl_max","F_cl max"),("capped_frac","capped_frac"),
              ("active_nodes","active nodes"),("spurious_fluid","spurious FLUID"),
              ("R_abs_mean","|R_theta| mean"),("theta_app","theta_app(deg)")]:
    fv = f[k]; av = a[k]
    if k=="capped_frac": fv=fv*100; av=av*100
    print(f"{lab:<28}{fv:>18.4e}{av:>22.4e}{fv-av:>14.2e}")

print("-"*100)
print(f"\nNEW cap (ForceCap=0.2) = {f['cap_value']:.4e}")
print(f"F_cl_max measured      = {f['fcl_max']:.4e}   (expect ~3.33e-6 if capped, else the uncapped value)")
print(f"capped_frac            = {f['capped_frac']*100:.0f}%")

no_nan = f["nan_inf"]==0
localized = f["spurious_fluid"]==0
stable = abs(f["footprint"]-a["footprint"])<1e-2 and abs(f["mass"]-a["mass"])<1e-5 and abs(f["theta_app"]-a["theta_app"])<1.0
verdict = dict(c2f0_pass = no_nan and localized and stable,
               no_nan=no_nan, fluid_localized=localized, equilibrium_stable=stable,
               note="t90 + ForceCap=0.2 (10x larger force ceiling): confirm equilibrium is not perturbed.")
print("\n"+"="*100); print("VERDICT:", json.dumps(verdict, indent=2)); print("="*100)
(OUT/"summary.json").write_text(json.dumps({"c2f0":f,"c2a":a,"verdict":verdict}, indent=2))
print(f"\nwrote {OUT/'summary.json'}")
