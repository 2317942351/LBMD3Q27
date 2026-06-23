#!/usr/bin/env python3
"""Stage 15C-2e: changed-angle trajectory under current cap.
  test: 60->30, 120->150  Mode=2 Coeff=2 cap=0.02 (F_cl saturated at 3.333e-7)
  base: same cases        Mode=2 Coeff=0           (F_cl=0, same binary/hook)
Compare footprint(t), theta_app(t), R_theta(t), mass, PhaseF, |U|, F_cl,
spurious-fluid-node count at each saved frame (step 0/500/.../4000).
Pure post-processing.
"""
from __future__ import annotations
import json, glob, re
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy as v2n

TEST = Path("/mnt/usb1t/RUNS/runs/stage15C2e_changed_angle_test")
BASE = Path("/mnt/usb1t/RUNS/runs/stage15C2e_changed_angle_base")
OUT  = Path("/home/yuan/stage15C2e_trajectory"); OUT.mkdir(parents=True, exist_ok=True)
CX = CZ = 48.0
CASES = ["decouple_wall_60to30", "decouple_wall_120to150"]
TARGETS = {"decouple_wall_60to30": 30, "decouple_wall_120to150": 150}

def load(p):
    r = vtk.vtkXMLImageDataReader(); r.SetFileName(p); r.Update()
    d = r.GetOutput().GetCellData(); A = {}
    for i in range(d.GetNumberOfArrays()):
        a = d.GetArray(i); A[a.GetName()] = v2n(a).copy()
    return tuple(v-1 for v in r.GetOutput().GetDimensions()), A

def frames(case_dir):
    vs = glob.glob(str(Path(case_dir)/"output"/"case_VTK_P00_*.vti"))
    return sorted(vs, key=lambda x:int(x.split("_")[-1].split(".")[0]))

def step_of(p): return int(p.split("_")[-1].split(".")[0])

def frame_metrics(p):
    dims, A = load(p); nx, ny, nz = dims
    ph = A["PhaseField"]; U = A["U"]
    U3 = U.reshape(ph.size, 3) if U.size == ph.size*3 else np.zeros((ph.size,3))
    uspeed = np.sqrt(U3[:,0]**2+U3[:,1]**2+U3[:,2]**2)
    ph3 = ph.reshape((nx,ny,nz))
    xs = np.arange(nx).reshape((nx,1,1)).astype(float); zs = np.arange(nz).reshape((1,1,nz)).astype(float)
    rr = np.broadcast_to(np.sqrt((xs-CX)**2+(zs-CX)**2),(nx,ny,nz))
    band = (ph3>0.05)&(ph3<0.95)
    footprint = float(rr[band].max()) if band.any() else float("nan")
    isb = A["IsItBoundary"].reshape((nx,ny,nz)); act = A["DynamicCLActive"].reshape((nx,ny,nz))
    fmag = A["DynamicCLForceCandidateMag"].reshape((nx,ny,nz))
    capp = A["DynamicCLCosApp"].reshape((nx,ny,nz)); ceq = A["DynamicCLCosEq"].reshape((nx,ny,nz))
    rth = A["DynamicCLCosResidual"].reshape((nx,ny,nz))
    m = (act>0.5)&(isb<0.5)&band
    cap = 0.02 * 5e-5/3.0  # ForceCap*scale
    active_fmag = fmag[m] if m.any() else np.array([0.0])
    capped_frac = float(np.mean(active_fmag >= cap*0.999)) if active_fmag.size else 0.0
    spurious = int(((fmag>0)&(isb<0.5)&~(act>0.5)).sum())
    if m.any():
        capp_m = capp[m].mean(); ceq_m = ceq[m].mean(); rth_m = rth[m].mean()
        theta_app = float(np.degrees(np.arccos(np.clip(capp_m,-1,1))))
    else:
        capp_m=ceq_m=rth_m=float("nan"); theta_app=float("nan")
    return dict(step=step_of(p),
        nan_inf=int((~np.isfinite(ph)).sum()+(~np.isfinite(U)).sum()),
        mass=float(ph.mean()), ph_min=float(ph.min()), ph_max=float(ph.max()),
        footprint=footprint, u_max=float(uspeed.max()),
        fcl_max=float(fmag.max()), capped_frac=capped_frac,
        spurious_fluid=spurious, active_nodes=int(m.sum()),
        cos_app=float(capp_m), cos_eq=float(ceq_m), R_theta=float(rth_m),
        theta_app=theta_app)

results = {}
for case in CASES:
    target = TARGETS[case]
    trows = [frame_metrics(p) for p in frames(TEST/case)]
    brows = [frame_metrics(p) for p in frames(BASE/case)]
    results[case] = dict(target=target, test=trows, base=brows)

for case in CASES:
    target = TARGETS[case]
    print("\n"+"="*120)
    print(f"CASE {case}   target={target}deg   (test Coeff=2 cap=0.02  vs  base Coeff=0)")
    print("="*120)
    print(f"{'step':>5} | {'theta_app TEST':>14} {'theta_app BASE':>15} {'|R| TEST':>9} {'|R| BASE':>9} | "
          f"{'footprint T':>11} {'footprint B':>11} | {'mass T':>9} {'mass B':>9} | {'Fcl_max T':>10} {'cap%':>5} {'spur':>4}")
    print("-"*120)
    # align by step
    bmap = {r["step"]: r for r in results[case]["base"]}
    for tr in results[case]["test"]:
        s = tr["step"]; br = bmap.get(s)
        if br is None: continue
        print(f"{s:>5} | {tr['theta_app']:>14.2f} {br['theta_app']:>15.2f} "
              f"{abs(tr['R_theta']):>9.4f} {abs(br['R_theta']):>9.4f} | "
              f"{tr['footprint']:>11.3f} {br['footprint']:>11.3f} | "
              f"{tr['mass']:>9.5f} {br['mass']:>9.5f} | "
              f"{tr['fcl_max']:>10.2e} {tr['capped_frac']*100:>4.0f}% {tr['spurious_fluid']:>4d}")
    # summary: does test move theta_app toward target faster than base?
    t_first, t_last = results[case]["test"][1], results[case]["test"][-1]   # skip step0
    b_first, b_last = bmap.get(t_first["step"]), bmap.get(t_last["step"])
    print(f"\n  theta_app toward target?  test: {t_first['theta_app']:.1f} -> {t_last['theta_app']:.1f} (target {target})"
          f"   base: {b_first['theta_app']:.1f} -> {b_last['theta_app']:.1f}")
    print(f"  |R_theta| change:         test: {abs(t_first['R_theta']):.4f} -> {abs(t_last['R_theta']):.4f}"
          f"   base: {abs(b_first['R_theta']):.4f} -> {abs(b_last['R_theta']):.4f}")
    print(f"  footprint change:         test: {t_first['footprint']:.2f} -> {t_last['footprint']:.2f}"
          f"   base: {b_first['footprint']:.2f} -> {b_last['footprint']:.2f}")
    print(f"  max NaN/Inf (test)        : {max(r['nan_inf'] for r in results[case]['test'])}")
    print(f"  max spurious fluid (test) : {max(r['spurious_fluid'] for r in results[case]['test'])}")

# overall verdict
def driven(case):
    t = results[case]["test"]; b = {r["step"]:r for r in results[case]["base"]}
    # compare |R_theta| reduction test vs base over the run
    rt_red = abs(t[1]["R_theta"]) - abs(t[-1]["R_theta"])
    rb_red = abs(b[t[1]["step"]]["R_theta"]) - abs(b[t[-1]["step"]]["R_theta"])
    return rt_red, rb_red
print("\n"+"="*120); print("VERDICT SUMMARY")
for case in CASES:
    rt, rb = driven(case)
    print(f"  {case}: |R_theta| reduction  test={rt:+.4f}  base={rb:+.4f}  "
          f"delta(test-base)={rt-rb:+.4f}  -> {'test reduces residual MORE' if rt>rb+1e-4 else 'test ~ same as base (force too weak)'}")
(OUT/"summary.json").write_text(json.dumps(results, indent=2))
print(f"\nwrote {OUT/'summary.json'}")
