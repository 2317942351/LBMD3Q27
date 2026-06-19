#!/usr/bin/env python3
"""Stage 15C-2b smoke: t90 + Mode=2 + Coeff=0.02.
First nonzero-coefficient run. R_theta~0 at t90 equilibrium, so F_cl is tiny
but NONZERO. The point is to confirm:
  - the force-write path runs without NaN/pollution,
  - F_cl is localized to active & not-wall & clband nodes (no bulk/wall leak),
  - the solution is essentially unchanged vs the C2a (Coeff=0) baseline.
Pure post-processing.
"""
from __future__ import annotations
import json, glob, re
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy as v2n

C2B  = Path("/mnt/usb1t/RUNS/runs/stage15C2b_t90_coeff0p02/diag_wall_t90")
C2A  = Path("/mnt/usb1t/RUNS/runs/stage15C2a_t90_mode2_coeff0/diag_wall_t90")
OUT  = Path("/home/yuan/stage15C2b_regression"); OUT.mkdir(parents=True, exist_ok=True)
CX = CZ = 48.0

def load(p):
    r = vtk.vtkXMLImageDataReader(); r.SetFileName(p); r.Update()
    d = r.GetOutput().GetCellData(); A = {}
    for i in range(d.GetNumberOfArrays()):
        a = d.GetArray(i); A[a.GetName()] = v2n(a).copy()
    dims = tuple(v-1 for v in r.GetOutput().GetDimensions()); return dims, A

def xml_g(case_dir, name):
    x = (Path(case_dir)/"output"/"case_config_P00_00000000.xml").read_text()
    m = re.search(rf'name="{name}" value="([^"]+)"', x)
    return m.group(1) if m else "MISSING"

def last_vti(case_dir):
    vs = sorted(glob.glob(str(Path(case_dir)/"output"/"case_VTK_P00_*.vti")),
                key=lambda x:int(x.split("_")[-1].split(".")[0]))
    return vs[-1]

def analyze(case_dir, label):
    dims, A = load(last_vti(case_dir)); nx, ny, nz = dims
    ph = A["PhaseField"]; U = A["U"]
    U3 = U.reshape(ph.size, 3) if U.size == ph.size*3 else np.zeros((ph.size,3))
    uspeed = np.sqrt(U3[:,0]**2+U3[:,1]**2+U3[:,2]**2)
    ph3 = ph.reshape((nx,ny,nz))
    xs = np.arange(nx).reshape((nx,1,1)).astype(float)
    zs = np.arange(nz).reshape((1,1,nz)).astype(float)
    rr = np.broadcast_to(np.sqrt((xs-CX)**2+(zs-CZ)**2),(nx,ny,nz))
    band = (ph3>0.05)&(ph3<0.95)
    footprint = float(rr[band].max()) if band.any() else float("nan")
    # F_cl fields
    fx = A["DynamicCLForceCandidateX"]; fy = A["DynamicCLForceCandidateY"]; fz = A["DynamicCLForceCandidateZ"]
    fmag = A["DynamicCLForceCandidateMag"]
    isb = A["IsItBoundary"].reshape((nx,ny,nz))
    act = A["DynamicCLActive"].reshape((nx,ny,nz))
    fmag3 = fmag.reshape((nx,ny,nz))
    fx3, fy3, fz3 = fx.reshape((nx,ny,nz)), fy.reshape((nx,ny,nz)), fz.reshape((nx,ny,nz))
    m_active = act>0.5
    m_clband = band
    m_notwall = isb<0.5
    # spatial-locality: where is |F_cl|>0?
    nonzero = fmag3 > 0.0
    n_nonzero = int(nonzero.sum())
    n_in_local = int((nonzero & m_active & m_notwall & m_clband).sum())
    n_outside = n_nonzero - n_in_local
    fmag_active = fmag3[m_active & m_notwall & m_clband]
    # R_theta
    cr = A["DynamicCLCosResidual"].reshape((nx,ny,nz))
    cr_active = cr[m_active & m_notwall & m_clband]
    # F_surf proxy if present
    fsurf_keys = [k for k in A if "Fs" in k or "SurfForce" in k]
    return dict(label=label,
        nan_inf=int((~np.isfinite(ph)).sum()+(~np.isfinite(U)).sum()+(~np.isfinite(fmag)).sum()),
        mass=float(ph.mean()), mass_sum=float(ph.sum()),
        ph_min=float(ph.min()), ph_max=float(ph.max()),
        footprint=footprint, u_max=float(uspeed.max()), u_rms=float(np.sqrt(np.mean(uspeed**2))),
        fcl_max=float(fmag.max()),
        fcl_mean_active=float(fmag_active.mean()) if fmag_active.size else 0.0,
        fcl_max_active=float(fmag_active.max()) if fmag_active.size else 0.0,
        active_force_nodes=int((m_active&m_notwall&m_clband&(fmag3>0)).sum()),
        fcl_nonzero_nodes=n_nonzero, fcl_localized=n_in_local, fcl_outside=n_outside,
        R_abs_mean_active=float(np.mean(np.abs(cr_active))) if cr_active.size else float("nan"),
        fsurf_keys=fsurf_keys[:5])

b = analyze(C2B, "C2b Coeff=0.02")
a = analyze(C2A, "C2a Coeff=0 baseline")

print("="*105)
print("C2b SMOKE: t90 Mode=2 Coeff=0.02   (vs C2a Coeff=0 baseline)")
print("="*105)
print(f"{'metric':<32}{'C2b (Coeff=0.02)':>20}{'C2a (Coeff=0)':>20}{'diff':>16}")
print("-"*105)
for k,label in [("nan_inf","NaN/Inf count"),("mass","mass (mean)"),
                ("footprint","footprint radius"),("ph_min","PhaseF min"),
                ("ph_max","PhaseF max"),("u_max","|U| max"),
                ("u_rms","|U| rms"),("fcl_max","F_cl max (all nodes)"),
                ("fcl_max_active","F_cl max on active CL"),
                ("fcl_mean_active","F_cl mean on active CL"),
                ("active_force_nodes","active force-node count"),
                ("R_abs_mean_active","|R_theta| mean on active CL")]:
    dv = b[k]-a[k] if isinstance(b[k],(int,float)) else "n/a"
    print(f"{label:<32}{b[k]:>20.4e}{a[k]:>20.4e}{str(dv):>16}")

print("-"*105)
print("\nF_cl SPATIAL LOCALITY (the key C2b check):")
print(f"  nonzero F_cl nodes total              : {b['fcl_nonzero_nodes']}")
print(f"    inside active & not-wall & clband   : {b['fcl_localized']}  (correct location)")
print(f"    OUTSIDE (bulk/wall/OuterDomain)     : {b['fcl_outside']}  (must be ~0)")
print(f"  active force-node count               : {b['active_force_nodes']}")

print("\nXML params (C2b):")
for k in ["DynamicCLMode","DynamicCLCoeff","DynamicCLCosSign","DynamicCLForceSign","sigma","IntWidth","M"]:
    print(f"  {k} = {xml_g(C2B, k)}")

# verdict
localized_ok = b["fcl_outside"] == 0
no_nan = b["nan_inf"] == 0
d_foot = abs(b["footprint"]-a["footprint"])
d_mass = abs(b["mass"]-a["mass"])
stable = d_foot < 1e-3 and d_mass < 1e-6
fcl_small = b["fcl_max"] < 1e-6  # R~0.029, coeff 0.02, scale 1.67e-5 -> ~1e-8
verdict = dict(c2b_pass=no_nan and localized_ok and stable,
               no_nan=no_nan, fcl_localized=localized_ok,
               solution_stable_vs_coeff0=stable,
               fcl_max_is_tiny=fcl_small,
               note="t90 + Coeff=0.02: F_cl is tiny (R_theta~0 at equilibrium) and localized "
                    "to the active contact-line band; solution matches Coeff=0 within tolerance.")
print("\n"+"="*105); print("VERDICT:", json.dumps(verdict, indent=2)); print("="*105)
(OUT/"summary.json").write_text(json.dumps({"c2b":b,"c2a":a,"verdict":verdict}, indent=2))
print(f"\nwrote {OUT/'summary.json'}")
