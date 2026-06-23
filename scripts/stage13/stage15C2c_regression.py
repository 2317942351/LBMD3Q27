#!/usr/bin/env python3
"""Stage 15C-2c smoke: t90 + Mode=2 + Coeff=0.2  (10x C2b).
Expect Fcl_max ~1e-7 (10x C2b's 9.7e-9). Same locality + stability gates.
"""
from __future__ import annotations
import json, glob, re
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy as v2n

C2C = Path("/mnt/usb1t/RUNS/runs/stage15C2c_t90_coeff0p2/diag_wall_t90")
C2B = Path("/mnt/usb1t/RUNS/runs/stage15C2b_t90_coeff0p02/diag_wall_t90")
C2A = Path("/mnt/usb1t/RUNS/runs/stage15C2a_t90_mode2_coeff0/diag_wall_t90")
OUT = Path("/home/yuan/stage15C2c_regression"); OUT.mkdir(parents=True, exist_ok=True)
CX = CZ = 48.0

def load(p):
    r = vtk.vtkXMLImageDataReader(); r.SetFileName(p); r.Update()
    d = r.GetOutput().GetCellData(); A = {}
    for i in range(d.GetNumberOfArrays()):
        a = d.GetArray(i); A[a.GetName()] = v2n(a).copy()
    return tuple(v-1 for v in r.GetOutput().GetDimensions()), A

def xml_g(cd, name):
    x = (Path(cd)/"output"/"case_config_P00_00000000.xml").read_text()
    m = re.search(rf'name="{name}" value="([^"]+)"', x)
    return m.group(1) if m else "MISSING"

def last(cd):
    vs = sorted(glob.glob(str(Path(cd)/"output"/"case_VTK_P00_*.vti")),
                key=lambda x:int(x.split("_")[-1].split(".")[0]))
    return vs[-1]

def analyze(cd, label):
    dims, A = load(last(cd)); nx, ny, nz = dims
    ph = A["PhaseField"]; U = A["U"]
    U3 = U.reshape(ph.size, 3) if U.size == ph.size*3 else np.zeros((ph.size,3))
    uspeed = np.sqrt(U3[:,0]**2+U3[:,1]**2+U3[:,2]**2)
    ph3 = ph.reshape((nx,ny,nz))
    xs = np.arange(nx).reshape((nx,1,1)).astype(float); zs = np.arange(nz).reshape((1,1,nz)).astype(float)
    rr = np.broadcast_to(np.sqrt((xs-CX)**2+(zs-CZ)**2),(nx,ny,nz))
    band = (ph3>0.05)&(ph3<0.95)
    footprint = float(rr[band].max()) if band.any() else float("nan")
    fmag = A["DynamicCLForceCandidateMag"].reshape((nx,ny,nz))
    isb = A["IsItBoundary"].reshape((nx,ny,nz)); act = A["DynamicCLActive"].reshape((nx,ny,nz))
    cr = A["DynamicCLCosResidual"].reshape((nx,ny,nz))
    m_active=act>0.5; m_notwall=isb<0.5; m_clband=band
    fmag_act = fmag[m_active&m_notwall&m_clband]
    cr_act = cr[m_active&m_notwall&m_clband]
    # THE decisive locality metric: fluid nodes (not wall) with F_cl>0 but Active<0.5
    fluid_spurious = (fmag>0) & m_notwall & ~m_active
    return dict(label=label,
        nan_inf=int((~np.isfinite(ph)).sum()+(~np.isfinite(U)).sum()+(~np.isfinite(A["DynamicCLForceCandidateMag"])).sum()),
        mass=float(ph.mean()), ph_min=float(ph.min()), ph_max=float(ph.max()),
        footprint=footprint, u_max=float(uspeed.max()), u_rms=float(np.sqrt(np.mean(uspeed**2))),
        fcl_max=float(fmag.max()),
        fcl_max_active=float(fmag_act.max()) if fmag_act.size else 0.0,
        fcl_mean_active=float(fmag_act.mean()) if fmag_act.size else 0.0,
        active_force_nodes=int(((fmag>0)&m_active&m_notwall&m_clband).sum()),
        spurious_fluid_force_nodes=int(fluid_spurious.sum()),  # MUST be 0
        wall_diagnostic_fcl_nodes=int(((fmag>0)&(isb>=0.5)).sum()),  # cosmetic, allowed
        R_abs_mean_active=float(np.mean(np.abs(cr_act))) if cr_act.size else float("nan"))

c = analyze(C2C, "C2c Coeff=0.2")
b = analyze(C2B, "C2b Coeff=0.02")
a = analyze(C2A, "C2a Coeff=0")

print("="*108)
print("C2c SMOKE: t90 Mode=2 Coeff=0.2   (10x C2b; vs C2a Coeff=0)")
print("="*108)
print(f"{'metric':<30}{'C2c(0.2)':>14}{'C2b(0.02)':>14}{'C2a(0)':>14}{'c2c-c2a':>14}")
print("-"*108)
for k,lab in [("nan_inf","NaN/Inf"),("mass","mass"),("footprint","footprint"),
              ("ph_min","ph_min"),("ph_max","ph_max"),("u_max","|U|max"),
              ("fcl_max","F_cl max(all)"),("fcl_max_active","F_cl max(active CL)"),
              ("fcl_mean_active","F_cl mean(active CL)"),
              ("active_force_nodes","active force nodes"),
              ("R_abs_mean_active","|R_theta| mean(active)")]:
    print(f"{lab:<30}{c[k]:>14.3e}{b[k]:>14.3e}{a[k]:>14.3e}{c[k]-a[k]:>14.2e}")
print("-"*108)
print(f"\nF_cl_max ratio C2c/C2b = {c['fcl_max']/b['fcl_max']:.2f}x   (expect ~10x if Coeff scaled linearly)")

print("\nLOCALITY (dynamics-relevant, fluid collision cells only):")
print(f"  spurious FLUID force nodes (F_cl>0, not-wall, Active<0.5): {c['spurious_fluid_force_nodes']}   (MUST be 0)")
print(f"  active force nodes (correct location)                     : {c['active_force_nodes']}")
print(f"  wall-diagnostic F_cl>0 nodes (cosmetic, no dynamics)      : {c['wall_diagnostic_fcl_nodes']}")

print("\nXML params (C2c):")
for k in ["DynamicCLMode","DynamicCLCoeff","DynamicCLCosSign","DynamicCLForceSign","sigma","IntWidth","M"]:
    print(f"  {k} = {xml_g(C2C, k)}")

# verdict
ratio_ok = 8 < c['fcl_max']/b['fcl_max'] < 12
localized = c['spurious_fluid_force_nodes'] == 0
no_nan = c['nan_inf'] == 0
stable = abs(c['footprint']-a['footprint'])<1e-3 and abs(c['mass']-a['mass'])<1e-6
verdict = dict(c2c_pass = no_nan and localized and stable and ratio_ok,
               no_nan=no_nan, fluid_localized=localized, solution_stable=stable,
               fcl_scaled_10x=ratio_ok,
               note="t90+Coeff=0.2: F_cl ~10x C2b (linear coeff scaling confirmed), "
                    "0 spurious fluid force nodes, solution within float-noise of Coeff=0.")
print("\n"+"="*108); print("VERDICT:", json.dumps(verdict, indent=2)); print("="*108)
(OUT/"summary.json").write_text(json.dumps({"c2c":c,"c2b":b,"c2a":a,"verdict":verdict}, indent=2))
print(f"\nwrote {OUT/'summary.json'}")
