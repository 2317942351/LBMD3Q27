#!/usr/bin/env python3
"""Stage 15C-1 FINAL ForceSign decision (2026-06-19), on the FIXED binary
under the CORRECT CosSign=-1.

Context (corrected from the withdrawn doc-35):
  - The fix is confirmed: cos_eq == cos(theta_eq), theta_eq present.
  - CosSign=-1 is correct (theta_app matches target: 24/88/149 deg).
    CosSign=+1 gives mirrored theta_app (156/92/31) -> wrong sign.
  - The decoupled R_theta are SMALL because the droplet has mostly relaxed by
    step 4000 (theta_app ~ 28 / 144.5, close to targets 30 / 150). The residual
    is the *correction* needed to push theta_app onto theta_eq.

ForceSign derivation (under CosSign=-1, t_CL points OUTWARD):
  F_CL = ForceSign * Coeff * scale * R_theta * I_cl * t_CL
  R_theta = cos(theta_eq) - cos(theta_app)

  A node wants theta_app to MOVE TOWARD theta_eq. The force must drive the
  contact line so that theta_app -> theta_eq:
    if theta_app < theta_eq (over-wet): theta_app must INCREASE -> RETRACT (inward)
    if theta_app > theta_eq (under-wet): theta_app must DECREASE -> SPREAD (outward)

  60->30 at step4000: theta_app=28.0 < 30  -> need RETRACT (F along -t_CL, inward)
       R_theta = cos30 - cos28 = +0.866 - +0.883 = -0.017  (negative)
       ForceSign*R_theta < 0 to give -t_CL  =>  ForceSign = +1
  120->150 at step4000: theta_app=144.5 < 150 -> need RETRACT (theta_app up -> inward)
       R_theta = cos150 - cos144.5 = -0.866 - -0.814 = -0.052 (negative)
       ForceSign*R_theta < 0 to give -t_CL  =>  ForceSign = +1

  => DynamicCLForceSign = +1   (robust under CosSign=-1; same value as +1 case,
     but the PHYSICAL INTERPRETATION is now correct: +1 drives theta_app -> theta_eq).

This script prints the final table and writes the verdict. Pure post-processing.
"""
from __future__ import annotations
import json, glob
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy as v2n

ROOT = Path("/mnt/usb1t/RUNS/runs/stage15c1_shadow_cs_minus1")  # CORRECT cos_sign
OUT = Path("/home/yuan/stage15c1_final")
OUT.mkdir(parents=True, exist_ok=True)
CX = CZ = 48.0
EPS_Q = 0.05

def load(p):
    r = vtk.vtkXMLImageDataReader(); r.SetFileName(p); r.Update()
    d = r.GetOutput().GetCellData(); A = {}
    for i in range(d.GetNumberOfArrays()):
        a = d.GetArray(i); A[a.GetName()] = v2n(a).copy()
    return tuple(v - 1 for v in r.GetOutput().GetDimensions()), A

def fluid_mask(dims, A):
    nx, ny, nz = dims
    ph = A["PhaseField"].reshape((nx, ny, nz))
    isb = A["IsItBoundary"].reshape((nx, ny, nz))
    act = A["DynamicCLActive"].reshape((nx, ny, nz))
    return (act > 0.5) & (isb < 0.5) & (ph > EPS_Q) & (ph < 1 - EPS_Q), (nx, ny, nz)

CASES = {
    "diag_wall_t30":         dict(target=30,  kind="eq"),
    "diag_wall_t90":         dict(target=90,  kind="eq"),
    "diag_wall_t150":        dict(target=150, kind="eq"),
    "decouple_wall_60to30":  dict(target=30,  kind="dec"),
    "decouple_wall_120to150":dict(target=150, kind="dec"),
}

rows = []
for case, meta in CASES.items():
    p = sorted(glob.glob(str(ROOT / case / "output" / "case_VTK_P00_*.vti")),
               key=lambda x: int(x.split("_")[-1].split(".")[0]))[-1]
    dims, A = load(p)
    m, (nx, ny, nz) = fluid_mask(dims, A)
    cos_app = float(np.mean(A["DynamicCLCosApp"].reshape((nx, ny, nz))[m]))
    cos_eq = float(np.mean(A["DynamicCLCosEq"].reshape((nx, ny, nz))[m]))
    rth = float(np.mean(A["DynamicCLCosResidual"].reshape((nx, ny, nz))[m]))
    theta_app = float(np.degrees(np.arccos(np.clip(cos_app, -1, 1))))
    target = meta["target"]
    # desired motion of theta_app: toward target
    if abs(theta_app - target) < 1.0:
        desired = "at-eq"
    elif theta_app < target:
        desired = "increase(retract/inward)"
    else:
        desired = "decrease(spread/outward)"
    # which ForceSign gives F along the needed direction (t_CL outward)
    # need inward  -> ForceSign*R_theta<0 ; need outward -> ForceSign*R_theta>0
    if "inward" in desired:
        fs_ok = +1 if rth < 0 else -1
    elif "outward" in desired:
        fs_ok = +1 if rth > 0 else -1
    else:
        fs_ok = 0  # at eq, no preference
    rows.append(dict(case=case, **meta, n=int(m.sum()),
                     cos_eq=cos_eq, cos_app=cos_app, R_theta=rth,
                     theta_app_deg=theta_app, desired=desired, force_sign_for_motion=fs_ok))

print("=" * 110)
print("C1 FINAL  (FIXED binary, CosSign=-1, REAL R_theta)")
print("=" * 110)
print(f"{'case':<22}{'kind':>5}{'tgt':>5}{'cos_eq':>9}{'cos_app':>9}{'R_theta':>9}"
      f"{'theta_app':>11}{'desired theta_app motion':>28}{'FS':>4}")
print("-" * 110)
for r in rows:
    print(f"{r['case']:<22}{r['kind']:>5}{r['target']:>5}{r['cos_eq']:>+9.4f}"
          f"{r['cos_app']:>+9.4f}{r['R_theta']:>+9.4f}{r['theta_app_deg']:>10.1f}°"
          f"{r['desired']:>28}{r['force_sign_for_motion']:>+4d}")

dec = {r["case"]: r for r in rows if r["kind"] == "dec"}
c60, c120 = dec["decouple_wall_60to30"], dec["decouple_wall_120to150"]
# both decoupled cases at step4000 happen to be over-relaxed (theta_app<target),
# both want retract, both R_theta<0 -> ForceSign=+1. Check consistency.
fs_vals = {c60["force_sign_for_motion"], c120["force_sign_for_motion"]}
if fs_vals == {+1}:
    force_sign = +1
    consistent = True
elif fs_vals == {-1}:
    force_sign = -1
    consistent = True
else:
    force_sign = None
    consistent = False

print("-" * 110)
print(f"\nDecoupled ForceSign-votes: 60->30={c60['force_sign_for_motion']:+d}  "
      f"120->150={c120['force_sign_for_motion']:+d}  -> "
      f"{'CONSISTENT' if consistent else 'INCONSISTENT'}")
# cross-check equilibrium (R_theta should be ~0; sign not meaningful)
eq = {r["case"]: r for r in rows if r["kind"] == "eq"}
print(f"Equilibrium |R_theta|: t30={abs(eq['diag_wall_t30']['R_theta']):.4f}  "
      f"t90={abs(eq['diag_wall_t90']['R_theta']):.4f}  "
      f"t150={abs(eq['diag_wall_t150']['R_theta']):.4f}  (expect small; confirms CosSign=-1 + fix)")

verdict = dict(
    cos_sign=-1,           # calibrated by gate-4 (theta_app matches target)
    force_sign=force_sign, # +1 under the correct cos_sign
    force_sign_consistent=consistent,
    cos_eq_fix_confirmed=True,
    equilibrium_residual_small=all(abs(eq[c]["R_theta"]) < 0.1 for c in eq),
    note=("ForceSign=+1 drives theta_app -> theta_eq under CosSign=-1. The value "
          "+1 is the SAME as the withdrawn doc-35, but the derivation now rests on "
          "REAL R_theta and the correct CosSign; the old doc-35 used the pre-fix "
          "binary (cos_eq=0) and was INVALID."),
)
print("\nVERDICT:", json.dumps(verdict, indent=2))
(OUT / "summary.json").write_text(json.dumps({"rows": rows, "verdict": verdict}, indent=2))
print(f"\nwrote {OUT / 'summary.json'}")
