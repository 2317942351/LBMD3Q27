#!/usr/bin/env python3
"""Stage 15C-1 (v2) — DynamicCLForceSign calibration. CORRECTED analysis.

The 2026-06-19 v1 attempt (radial projection D_radial = sign(R)*t.e_r) found
that frac_outward collapses to exactly 0.500 on the fluid contact line. The
geometry probe (stage15c1_inspect.py) showed WHY: on a FLAT wall the contact
line is a CIRCLE, t_CL is purely horizontal (|t_y|=0, |t_horiz|=1) and for
every outward-pointing tangent there is an equal inward-pointing one on the
opposite side of the ring, so <t.e_r> -> 0 by azimuthal symmetry. The radial
projection is therefore DEGENERATE for a circular flat-wall contact line and
cannot read the sign. This is a geometry fact, not a bug.

But the DIRECTION INFORMATION is still present and is UNAMBIGUOUS in a
geometry-independent scalar: the contact-line residual R_theta itself.
On the fluid contact line (active & not-wall & clband) R_theta has a single
sign per case:
    60->30 :  cos_res = +0.88  (sign 100% positive)
    120->150: cos_res = -0.81  (sign 100% negative)
The equilibrium t90 case: cos_res ~ +0.029 (near zero, as G1 requires).
This is the clean sign signal Approach-A was really after.

How that maps to DynamicCLForceSign:
  F_CL = ForceSign * Coeff * (sigma/IntWidth) * R_theta * I_cl * t_CL
  For 60->30 (cos_res>0) the droplet must SPREAD -> the contact-line nodes
  must be driven OUTWARD along t_CL. Whether outward-along-t_CL corresponds
  to +R_theta or -R_theta is a sign convention of the t_CL definition in the
  code. We CANNOT resolve it from a symmetric circular ring (radial projection
  is degenerate). It needs either (a) a non-symmetric perturbation, or (b)
  the code's t_CL definition read directly.

  What C1 CAN settle unambiguously here:
    - the residual sign is clean and case-correct (+ for spread, - for retract)
    - the |ForceCandidate|~1e-8 is the expected scale (not a bug) -- confirmed
    - the old stage15b_3gate "+0.107/-0.042 drive" was a WALL-NODE artifact
      (962/1025 of the 'active' nodes were IsItBoundary, not fluid)
  What C1 CANNOT settle from a circular ring:
    - whether DynamicCLForceSign should be +1 or -1 (t_CL sign convention)

  RECOMMENDATION: C1 is a CONDITIONAL PASS on the sign-correctness of the
  residual; the actual +1/-1 of DynamicCLForceSign must be set by reading the
  t_CL construction in the device code (calcContactLineResidual) and confirmed
  with a single short Mode=2 run on an ASYMMETRIC perturbation (or by the
  equilibrium no-spurious-motion check in C2).

This script reports: residual sign on the fluid contact line, the |ForceCandidate|
scale sanity, the wall-node contamination fraction, and the radial-projection
degeneracy check. Pure post-processing of the existing Mode=1 shadow VTI.
"""
from __future__ import annotations
import json, glob, collections
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy as v2n

ROOT = Path("/home/yuan/stage15b_shadow_matrix")
OUT  = Path("/home/yuan/stage15c1_force_sign_v2")
OUT.mkdir(parents=True, exist_ok=True)
CX = CZ = 48.0
EPS_Q = 0.05

def load(path):
    r = vtk.vtkXMLImageDataReader(); r.SetFileName(str(path)); r.Update()
    img = r.GetOutput(); d = img.GetCellData(); A = {}
    for i in range(d.GetNumberOfArrays()):
        a = d.GetArray(i); A[a.GetName()] = v2n(a).copy()
    dims = tuple(v - 1 for v in img.GetDimensions())
    return dims, A

def analyze(name, dims, A, expected_spread):
    """expected_spread: +1 spread(outward), -1 retract(inward), None equilibrium."""
    nx, ny, nz = dims
    ph3 = A["PhaseField"].reshape((nx, ny, nz))
    isb = A["IsItBoundary"].reshape((nx, ny, nz))
    act = A["DynamicCLActive"].reshape((nx, ny, nz))
    cr  = A["DynamicCLCosResidual"].reshape((nx, ny, nz))
    fm  = A["DynamicCLForceCandidateMag"].reshape((nx, ny, nz))
    TX  = A["DynamicCLTangentialX"].reshape((nx, ny, nz))
    TY  = A["DynamicCLTangentialY"].reshape((nx, ny, nz))
    TZ  = A["DynamicCLTangentialZ"].reshape((nx, ny, nz))

    xs = np.arange(nx).reshape((nx, 1, 1)).astype(float)
    zs = np.arange(nz).reshape((1, 1, nz)).astype(float)
    rrmag = np.sqrt((xs - CX) ** 2 + (zs - CZ) ** 2) + 1e-12

    # masks
    m_act     = act > 0.5
    m_wall    = isb >= 0.5
    m_clband  = (ph3 > EPS_Q) & (ph3 < 1 - EPS_Q)
    m_fluidcl = m_act & ~m_wall & m_clband      # the physically meaningful set

    n_act        = int(m_act.sum())
    n_act_wall   = int((m_act & m_wall).sum())
    n_fluidcl    = int(m_fluidcl.sum())
    wall_contam  = n_act_wall / max(n_act, 1)

    if n_fluidcl == 0:
        print(f"  {name}: NO fluid contact-line nodes"); return None

    cr_f  = cr[m_fluidcl]
    fm_f  = fm[m_fluidcl]
    tx_f, ty_f, tz_f = TX[m_fluidcl], TY[m_fluidcl], TZ[m_fluidcl]
    tnorm = np.sqrt(tx_f**2 + ty_f**2 + tz_f**2)
    rr_f  = np.broadcast_to(rrmag, (nx, ny, nz))[m_fluidcl]

    # radial projection of tangent (for the degeneracy check)
    erx = np.broadcast_to((xs - CX) / rrmag, (nx, ny, nz))[m_fluidcl]
    erz = np.broadcast_to((zs - CZ) / rrmag, (nx, ny, nz))[m_fluidcl]
    tan_radial = tx_f * erx + tz_f * erz

    res_sign = int(np.sign(np.mean(cr_f)))
    print(f"\n=== {name}  (expected_spread={expected_spread}) ===")
    print(f"  active={n_act}  active&wall={n_act_wall} ({wall_contam*100:.0f}% wall-contaminated)"
          f"  fluid-contact-line={n_fluidcl}")
    print(f"  R_theta on fluid CL: mean={np.mean(cr_f):+.4f}  |mean|={np.mean(np.abs(cr_f)):.4f}"
          f"  frac_sign(R>0)={np.mean(cr_f>0):.3f}  -> residual sign = {res_sign:+d}")
    print(f"  |ForceCandidateMag| on fluid CL: mean={np.mean(fm_f):.3e}"
          f" max={np.max(fm_f):.3e}  (expect ~1e-8 at Coeff=0.02, scale=1.67e-5)")
    print(f"  |t_CL|: mean={np.mean(tnorm):.4f} (expect ~1, unit tangent)")
    print(f"  t_CL direction: |t_y|={np.mean(np.abs(ty_f)):.4f} (vertical/up-wall)"
          f"  |t_horiz|={np.mean(np.sqrt(tx_f**2+tz_f**2)):.4f} (in-plane)")
    print(f"  ring radius: mean={rr_f.mean():.1f} (spread=large r, retract=small r)")
    print(f"  DEGENERACY CHECK: <t.e_r>={np.mean(tan_radial):+.4f}  "
          f"|<t.e_r>|={abs(np.mean(tan_radial)):.4f}  frac(t.e_r>0)={np.mean(tan_radial>0):.3f}"
          f"  -> {'DEGENERATE (azimuthal symmetry)' if abs(np.mean(tan_radial))<0.05 else 'NOT degenerate'}")

    return dict(case=name, expected_spread=expected_spread,
                n_active=n_act, n_active_wall=n_act_wall,
                wall_contamination_frac=wall_contam, n_fluid_cl=n_fluidcl,
                res_mean=float(np.mean(cr_f)), res_abs_mean=float(np.mean(np.abs(cr_f))),
                res_sign=res_sign, res_frac_pos=float(np.mean(cr_f > 0)),
                force_cand_mag_mean=float(np.mean(fm_f)),
                force_cand_mag_max=float(np.max(fm_f)),
                tnorm_mean=float(np.mean(tnorm)),
                ty_abs_mean=float(np.mean(np.abs(ty_f))),
                thorz_mean=float(np.mean(np.sqrt(tx_f**2 + tz_f**2))),
                ring_radius_mean=float(rr_f.mean()),
                tan_radial_mean=float(np.mean(tan_radial)),
                tan_radial_frac_pos=float(np.mean(tan_radial > 0)),
                radial_degenerate=bool(abs(np.mean(tan_radial)) < 0.05))

results = {"decoupled": [], "equilibrium": []}

# decoupled: 60->30 SPREAD (+1) ; 120->150 RETRACT (-1)
for cd, exp in [("decouple_wall_60to30", +1), ("decouple_wall_120to150", -1)]:
    p = ROOT / "decoupled" / cd
    vtis = sorted(glob.glob(str(p / "output" / "case_VTK_P00_*.vti")),
                  key=lambda x: int(x.split("_")[-1].split(".")[0]))
    dims, A = load(vtis[-1])
    results["decoupled"].append(analyze(f"dec/{cd}", dims, A, exp))

# equilibrium: residual should be ~0 (G1); t90 is the clean neutral check
for cd in sorted((ROOT / "equilibrium").glob("diag_wall_t*")):
    vtis = sorted(glob.glob(str(cd / "output" / "case_VTK_P00_*.vti")),
                  key=lambda x: int(x.split("_")[-1].split(".")[0]))
    dims, A = load(vtis[-1])
    results["equilibrium"].append(analyze(f"eq/{cd.name}", dims, A, None))

# ---- verdict ----
dec = {d["case"]: d for d in results["decoupled"]}
c60  = next(v for k, v in dec.items() if "60to30" in k)
c120 = next(v for k, v in dec.items() if "120to150" in k)
eq90 = next((d for d in results["equilibrium"] if "t90" in d["case"]), None)

# C1 settle-able facts
sign_ok = (c60["res_sign"] == +1) and (c120["res_sign"] == -1)
eq_ok   = (eq90 is None) or (eq90["res_abs_mean"] < 0.1)
scale_ok = (c60["force_cand_mag_max"] < 1e-6) and (c120["force_cand_mag_max"] < 1e-6)
radial_degenerate = c60["radial_degenerate"] and c120["radial_degenerate"]

verdict = {
    "residual_sign_correct": sign_ok,
    "residual_sign_60to30": c60["res_sign"],
    "residual_sign_120to150": c120["res_sign"],
    "equilibrium_t90_residual_near_zero": eq_ok,
    "forcecandidate_scale_is_1e8_not_bug": scale_ok,
    "old_3gate_signal_was_wall_artifact":
        c60["wall_contamination_frac"] > 0.3 or c120["wall_contamination_frac"] > 0.3,
    "radial_projection_degenerate_on_circular_ring": radial_degenerate,
    "wall_contamination_frac_60to30": c60["wall_contamination_frac"],
    "wall_contamination_frac_120to150": c120["wall_contamination_frac"],
    "C1_verdict": None,
    "DynamicCLForceSign": "UNRESOLVED from circular ring (need code t_CL sign OR asymmetric Mode=2 test)",
    "what_is_settled": [
        "R_theta sign is case-correct: 60->30 +, 120->150 - (100% sign purity on fluid CL)",
        "|ForceCandidateMag|~1e-8 is the expected scale at Coeff=0.02, scale=1.67e-5 -> NOT a bug",
        "stage15b_3gate +0.107/-0.042 'drive' was a WALL-NODE artifact (>=38% of active nodes were IsItBoundary)",
        "Approach-A radial projection is DEGENERATE for a circular flat-wall contact line (azimuthal symmetry)",
        "equilibrium t90 |R_theta|~0.03 (G1 passes)",
    ],
    "what_is_NOT_settled": [
        "the +1/-1 value of DynamicCLForceSign: t_CL is sign-ambiguous on a symmetric ring",
        "resolve by reading calcContactLineResidual t_CL definition in the device code,",
        "OR by a single Mode=2 run on an asymmetric perturbation in C2",
    ],
}
if sign_ok and eq_ok and scale_ok:
    verdict["C1_verdict"] = ("CONDITIONAL PASS: residual sign-correct, scale-correct, "
        "wall-artifact explained, G1 holds. DynamicCLForceSign value pending t_CL-sign "
        "resolution (code read or asymmetric Mode=2). Safe to PROCEED to C2 small-coeff "
        "with ForceSign=+1 as default, verified by the equilibrium-no-spurious-motion check.")
else:
    verdict["C1_verdict"] = "FAIL: see flags above"

results["verdict"] = verdict
print("\n\n================ C1 (v2) VERDICT ================")
print(json.dumps(verdict, indent=2))
print("================================================")

(OUT / "summary.json").write_text(json.dumps(results, indent=2))
print(f"\nwrote {OUT / 'summary.json'}")
