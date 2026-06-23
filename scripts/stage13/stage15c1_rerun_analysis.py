#!/usr/bin/env python3
"""Stage 15C-1 re-run analysis (2026-06-19) — on the FIXED binary.

The previous C1 (doc 35) was INVALID: the shadow VTI it analysed were produced
by the pre-fix binary (cos_eq=0, theta_eq missing). This script analyses the
re-run VTI produced by the fixed binary, for BOTH DynamicCLCosSign candidates
(+1 and -1), and decides:
  C1-0 sanity : is cos_eq now == cos(theta_eq)? (the fix works)
  C1 ForceSign: from REAL R_theta = cos_eq - cos_app + the device t_CL sign.

Pure post-processing. No source change, Mode=1 only.

Inputs (server):
  /mnt/usb1t/RUNS/runs/stage15c1_shadow_cs_plus1/<case>/output/case_VTK_P00_00004000.vti
  /mnt/usb1t/RUNS/runs/stage15c1_shadow_cs_minus1/<case>/output/case_VTK_P00_00004000.vti
Output: /home/yuan/stage15c1_rerun_analysis/summary.json + printed tables.
"""
from __future__ import annotations
import json, glob
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy as v2n

ROOTS = {
    +1.0: Path("/mnt/usb1t/RUNS/runs/stage15c1_shadow_cs_plus1"),
    -1.0: Path("/mnt/usb1t/RUNS/runs/stage15c1_shadow_cs_minus1"),
}
OUT = Path("/home/yuan/stage15c1_rerun_analysis")
OUT.mkdir(parents=True, exist_ok=True)
CX = CZ = 48.0
EPS_Q = 0.05
TAN_MIN = 0.5

# expected cos_eq per target angle (gate-4 calibration reference)
COS_EQ_REF = {30: +0.8660254, 90: 0.0, 150: -0.8660254}

# case metadata: target angle, and (for decoupled) expected physical drive
CASES = {
    "diag_wall_t30":        dict(target=30,  kind="equilibrium"),
    "diag_wall_t90":        dict(target=90,  kind="equilibrium"),
    "diag_wall_t150":       dict(target=150, kind="equilibrium"),
    "decouple_wall_60to30": dict(target=30,  kind="decoupled", expected="spread"),  # outward
    "decouple_wall_120to150":dict(target=150, kind="decoupled", expected="retract"),# inward
}

def load(path):
    r = vtk.vtkXMLImageDataReader(); r.SetFileName(str(path)); r.Update()
    img = r.GetOutput(); d = img.GetCellData(); A = {}
    for i in range(d.GetNumberOfArrays()):
        a = d.GetArray(i); A[a.GetName()] = v2n(a).copy()
    dims = tuple(v - 1 for v in img.GetDimensions())
    return dims, A

def analyze(case, root, cos_sign):
    p = sorted(glob.glob(str(root / case / "output" / "case_VTK_P00_*.vti")),
               key=lambda x: int(x.split("_")[-1].split(".")[0]))[-1]
    dims, A = load(p)
    nx, ny, nz = dims
    ph = A["PhaseField"].reshape((nx, ny, nz))
    isb = A["IsItBoundary"].reshape((nx, ny, nz))
    act = A["DynamicCLActive"].reshape((nx, ny, nz))
    teq = A["DynamicCLThetaEq"].reshape((nx, ny, nz))
    ceq = A["DynamicCLCosEq"].reshape((nx, ny, nz))
    capp = A["DynamicCLCosApp"].reshape((nx, ny, nz))
    rth = A["DynamicCLCosResidual"].reshape((nx, ny, nz))
    wcf = A["DynamicCLWallContextFound"].reshape((nx, ny, nz))
    blk = A["DynamicCLBlockedReason"].reshape((nx, ny, nz))
    tx = A["DynamicCLTangentialX"].reshape((nx, ny, nz))
    tz = A["DynamicCLTangentialZ"].reshape((nx, ny, nz))
    tnorm = np.sqrt(tx**2 + A["DynamicCLTangentialY"].reshape((nx,ny,nz))**2 + tz**2)

    m = (act > 0.5) & (isb < 0.5) & (ph > EPS_Q) & (ph < 1 - EPS_Q) & (tnorm > TAN_MIN)
    n = int(m.sum())
    if n == 0:
        return None

    # radial projection of tangent (for force-direction read; degenerate on ring)
    xs = np.arange(nx).reshape((nx, 1, 1)).astype(float)
    zs = np.arange(nz).reshape((1, 1, nz)).astype(float)
    rrmag = np.sqrt((xs - CX)**2 + (zs - CZ)**2) + 1e-12
    erx = np.broadcast_to((xs - CX) / rrmag, (nx, ny, nz))
    erz = np.broadcast_to((zs - CZ) / rrmag, (nx, ny, nz))
    tan_radial = (tx * erx + tz * erz)[m]

    target = CASES[case]["target"]
    return dict(
        case=case, cos_sign=cos_sign, target=target, n_fluid_cl=n,
        theta_eq_rad=float(np.mean(teq[m])), theta_eq_deg=float(np.degrees(np.mean(teq[m]))),
        cos_eq=float(np.mean(ceq[m])), cos_app=float(np.mean(capp[m])),
        R_theta=float(np.mean(rth[m])),
        cos_eq_ref=COS_EQ_REF[target],
        cos_eq_err=abs(float(np.mean(ceq[m])) - COS_EQ_REF[target]),
        wall_context_found_frac=float(np.mean(wcf[m] > 0.5)),
        # blocked-reason distribution among NON-active wall/bulk (sanity: should be wall/bulk reasons, not 0)
        blocked_outside_hist=_hist(blk[~(act > 0.5)]),
        tan_radial_mean=float(np.mean(tan_radial)),
        tan_radial_frac_pos=float(np.mean(tan_radial > 0)),
        ring_radius=float(np.mean(np.broadcast_to(rrmag, (nx,ny,nz))[m])),
    )

def _hist(a):
    a = a[np.isfinite(a)]
    import collections
    return dict(collections.Counter(np.round(a).astype(int).tolist()))

results = {f"cos_sign_{cs:+.0f}": [] for cs in ROOTS}
for cs, root in ROOTS.items():
    for case in CASES:
        r = analyze(case, root, cs)
        if r:
            results[f"cos_sign_{cs:+.0f}"].append(r)

# ---------- C1-0 SANITY TABLE ----------
print("\n" + "=" * 100)
print("C1-0 SANITY TABLE  (cos_eq must match cos(theta_eq) -> fix works)")
print("=" * 100)
hdr = f"{'cos_sign':>8} {'case':<22} {'target':>6} {'theta_eq_deg':>12} {'cos_eq':>8} {'cos_eq_ref':>10} {'err':>7} {'WCF%':>5} {'verdict':>8}"
print(hdr)
print("-" * len(hdr))
sanity_pass = True
for cs in ROOTS:
    for r in results[f"cos_sign_{cs:+.0f}"]:
        ok = r["cos_eq_err"] < 0.05 and r["wall_context_found_frac"] > 0.95
        sanity_pass = sanity_pass and ok
        print(f"{cs:>+8.0f} {r['case']:<22} {r['target']:>6} "
              f"{r['theta_eq_deg']:>12.1f} {r['cos_eq']:>+8.4f} {r['cos_eq_ref']:>+10.4f} "
              f"{r['cos_eq_err']:>7.3f} {r['wall_context_found_frac']*100:>4.0f}% "
              f"{'PASS' if ok else 'FAIL':>8}")

# ---------- C1 ForceSign TABLE (only if sanity passed) ----------
print("\n" + "=" * 100)
print("C1 FORCESIGN TABLE  (REAL R_theta = cos_eq - cos_app)")
print("=" * 100)
print("Device: t_CL = normalized(n_i - (n_i.n_w)n_w) -> horizontal, points radially")
print("        OUTWARD on the contact-line ring. So +t_CL = outward (spread dir).")
print("Force:  F_CL = ForceSign * Coeff * scale * R_theta * I_cl * t_CL")
print("Goal:   60->30 spread (F along +t_CL) ; 120->150 retract (F along -t_CL)")
print("-" * 100)
hdr2 = f"{'cos_sign':>8} {'case':<22} {'target':>6} {'cos_eq':>8} {'cos_app':>8} {'R_theta':>8} {'expected':>9}"
print(hdr2)
print("-" * len(hdr2))
force_sign = None
for cs in ROOTS:
    for r in results[f"cos_sign_{cs:+.0f}"]:
        exp = CASES[r["case"]].get("expected", "eq")
        print(f"{cs:>+8.0f} {r['case']:<22} {r['target']:>6} "
              f"{r['cos_eq']:>+8.4f} {r['cos_app']:>+8.4f} {r['R_theta']:>+8.4f} {exp:>9}")

# decide which cos_sign makes equilibrium cos_app -> cos_eq (gate 4), then ForceSign
if sanity_pass:
    print("\n--- CosSign calibration (gate 4: equilibrium cos_app -> cos_eq) ---")
    for cs in ROOTS:
        rows = {r["case"]: r for r in results[f"cos_sign_{cs:+.0f}"]}
        # at equilibrium the apparent angle should have relaxed to theta_eq, so
        # |cos_app| should be close to |cos_eq| (sign aside). Use the t90 case as
        # the cleanest (cos_eq=0): there cos_app should also be ~0.
        t90 = rows.get("diag_wall_t90")
        gate4 = (t90 is not None and abs(t90["R_theta"]) < 0.1)
        print(f"  cos_sign={cs:+.0f}: eq-t90 |R_theta|={abs(t90['R_theta']) if t90 else float('nan'):.4f} "
              f"-> gate-4 {'PASS' if gate4 else 'FAIL'}")
    # ForceSign decision (from the physics, independent of cos_sign magnitude):
    # 60->30 R_theta>0 -> ForceSign=+1 gives +t_CL (spread); 120->150 R_theta<0 -> -t_CL (retract)
    # This holds for whichever cos_sign passes gate-4, because the sign of R_theta
    # is what matters and it must be consistent with the spread/retract intent.
    rows = {r["case"]: r for r in results["cos_sign_+1"]}
    r60 = rows["decouple_wall_60to30"]; r120 = rows["decouple_wall_120to150"]
    print("\n--- ForceSign decision (decoupled, real R_theta) ---")
    print(f"  60->30  R_theta = {r60['R_theta']:+.4f}  -> needs F along +t_CL (spread)")
    print(f"  120->150 R_theta = {r120['R_theta']:+.4f} -> needs F along -t_CL (retract)")
    plus_ok = (r60["R_theta"] > 0) and (r120["R_theta"] < 0)
    minus_ok = (r60["R_theta"] < 0) and (r120["R_theta"] > 0)
    if plus_ok:
        force_sign = +1
        print(f"  => ForceSign = +1  (R_60>0 -> +t_CL spread; R_120<0 -> -t_CL retract)")
    elif minus_ok:
        force_sign = -1
        print(f"  => ForceSign = -1")
    else:
        force_sign = None
        print(f"  => AMBIGUOUS (R signs do not split spread/retract as expected)")
else:
    print("\nSANITY FAILED -- do not judge ForceSign.")

verdict = dict(
    sanity_pass=sanity_pass,
    cos_eq_fix_confirmed=sanity_pass,
    force_sign=force_sign,
)
results["verdict"] = verdict
print("\n" + "=" * 100)
print("VERDICT:", json.dumps(verdict, indent=2))
print("=" * 100)

(OUT / "summary.json").write_text(json.dumps(results, indent=2))
print(f"\nwrote {OUT / 'summary.json'}")
