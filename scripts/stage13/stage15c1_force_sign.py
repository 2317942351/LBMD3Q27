#!/usr/bin/env python3
"""Stage 15C-1 — DynamicCLForceSign calibration via DIRECTION projection.

Approach A (per the 2026-06-19 handoff decision):
  Do NOT use the absolute ForceCandidate magnitude (it is ~1e-8 at sigma=5e-5,
  IntWidth=3, Coeff=0.02 by construction -- scale = sigma/IntWidth = 1.667e-5,
  so 0.02*1.667e-5*~0.1*~0.6 ~ 1e-8; that is the expected field, NOT a bug).
  Do NOT boost DynamicCLCoeff to a non-physical value (e.g. 12000) to make the
  force "visible" -- that would turn C1 from a direction-calibration into a
  large-coefficient perturbation test and pollute the conclusion.

  Instead use the coeff-INDEPENDENT direction drive:
      D_radial = ForceSign * sign(R_theta) * (t_CL . e_r)
  where e_r is the radial-outward unit vector in the x-z plane. sigma/IntWidth,
  Coeff and I_cl (>=0) only set the magnitude, never the direction; so they are
  dropped. The FORCE-SIGN-correct physical behaviour is:
      60->30  (target more wetting, droplet should SPREAD): D_radial > 0 (outward)
      120->150(target more hydrophobic, droplet should RETRACT): D_radial < 0 (inward)
  We report D_radial for both candidate ForceSign values (+1 and -1) and pick
  the one that makes BOTH decoupled cases agree with the physics.

Two masks (mandatory, per the handoff):
  Guard 1 (active-fluid-only): DynamicCLActive>0.5 AND IsItBoundary<0.5 AND
          contact-line band 0.05<q<0.95. This excludes wall nodes, which carry
          a known VTK display caveat (ForceCandidateX~37 artifact regions) that
          would otherwise be mistaken for a force-field residual bug.
  Guard 2 (tangent validity):  norm(t_CL) > 0.5  (ideally ~1). Nodes with a
          degenerate tangent do not participate in a direction projection.

Also sanity-reports the equilibrium cases (30/90/150) for the residual-is-near-
zero check (G1), as context -- the equilibrium drive should be small/ambiguous.

Pure post-processing of the existing Mode=1 shadow VTI. No source change, no
Mode=2, no re-run needed.
"""
from __future__ import annotations
import json, glob, sys, collections
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy as v2n

ROOT = Path("/home/yuan/stage15b_shadow_matrix")
OUT  = Path("/home/yuan/stage15c1_force_sign")
OUT.mkdir(parents=True, exist_ok=True)

CX = CZ = 48.0            # droplet center in x-z (matches 3gate script)
EPS_Q = 0.05              # contact-line band cutoff (DynamicCLEpsQ)
TAN_NORM_MIN = 0.5        # Guard 2: min |t_CL| to count a node's direction vote

def load(path):
    r = vtk.vtkXMLImageDataReader(); r.SetFileName(str(path)); r.Update()
    img = r.GetOutput(); d = img.GetCellData(); A = {}
    for i in range(d.GetNumberOfArrays()):
        a = d.GetArray(i); A[a.GetName()] = v2n(a).copy()
    dims = tuple(v - 1 for v in img.GetDimensions())
    return dims, A

def _stats(x):
    x = np.asarray(x, float)
    if x.size == 0:
        return dict(n=0, mean=float("nan"), median=float("nan"),
                    p10=float("nan"), p90=float("nan"),
                    frac_pos=float("nan"), frac_neg=float("nan"))
    return dict(n=int(x.size), mean=float(np.mean(x)),
                median=float(np.median(x)),
                p10=float(np.percentile(x, 10)),
                p90=float(np.percentile(x, 90)),
                frac_pos=float(np.mean(x > 0)),
                frac_neg=float(np.mean(x < 0)))

def analyze(name, dims, A, expected_sign):
    """Return per-case C1 direction report.

    D_radial(ForceSign) = ForceSign * sign(R_theta) * (t_CL . e_r)
    """
    nx, ny, nz = dims
    need = ["PhaseField", "IsItBoundary", "DynamicCLActive",
            "DynamicCLCosResidual", "DynamicCLTangentialX",
            "DynamicCLTangentialY", "DynamicCLTangentialZ",
            "DynamicCLRejectedReason"]
    miss = [f for f in need if f not in A]
    if miss:
        print(f"\n=== {name}  MISSING fields: {miss} ===")
        return None

    ph3 = A["PhaseField"].reshape((nx, ny, nz))
    isb = A["IsItBoundary"].reshape((nx, ny, nz))
    act = A["DynamicCLActive"].reshape((nx, ny, nz))
    cr  = A["DynamicCLCosResidual"].reshape((nx, ny, nz))
    TX  = A["DynamicCLTangentialX"].reshape((nx, ny, nz))
    TY  = A["DynamicCLTangentialY"].reshape((nx, ny, nz))
    TZ  = A["DynamicCLTangentialZ"].reshape((nx, ny, nz))
    rej = A["DynamicCLRejectedReason"].reshape(-1)

    # radial-outward unit vector e_r in the x-z plane
    xs = np.arange(nx)[:, None, None].astype(float)
    zs = np.arange(nz)[None, None, :].astype(float)
    rx = xs - CX; rz = zs - CZ
    rr = np.sqrt(rx * rx + rz * rz) + 1e-12
    erx = rx / rr; erz = rz / rr   # e_r components (er_y = 0)

    # tangent radial projection  t_CL . e_r   (range ~[-1,1])
    tan_radial = TX * erx + TZ * erz
    tnorm = np.sqrt(TX * TX + TY * TY + TZ * TZ)

    # ---- mask build-up (count how many survive each guard) ----
    m_active   = act > 0.5
    m_notwall  = isb < 0.5
    m_clband   = (ph3 > EPS_Q) & (ph3 < 1.0 - EPS_Q)
    m_guard1   = m_active & m_notwall & m_clband          # Guard 1: active fluid
    m_guard2   = tnorm > TAN_NORM_MIN                      # Guard 2: valid tangent
    m          = m_guard1 & m_guard2                       # final C1 node set

    n_active        = int(m_active.sum())
    n_active_notwall= int((m_active & m_notwall).sum())
    n_guard1        = int(m_guard1.sum())
    n_final         = int(m.sum())

    # rejected-reason histogram among active nodes that were NOT in the final set
    rej_active = rej[m_active.reshape(-1) & (~m).reshape(-1)]
    rej_active = rej_active[np.isfinite(rej_active)]
    rej_hist = dict(collections.Counter(np.round(rej_active).astype(int).tolist()))

    # ---- coeff-independent direction drive ----
    # base = sign(R_theta) * (t_CL . e_r); direction only, no magnitude.
    base = np.sign(cr) * tan_radial
    base_a = base[m]
    s_base = _stats(base_a)

    # D_radial for each candidate ForceSign
    d_pos = _stats(+1.0 * base_a)   # ForceSign = +1
    d_neg = _stats(-1.0 * base_a)   # ForceSign = -1

    # also report residual / tangent magnitudes on the final set (context)
    res_a  = cr[m]
    tnm_a  = tnorm[m]

    agree_pos = (np.sign(s_base["mean"]) == expected_sign) if expected_sign else None

    print(f"\n=== {name}  dims={dims}  expected_sign={expected_sign} ===")
    print(f"  node counts: active={n_active}  active&not-wall={n_active_notwall}"
          f"  guard1(active,notwall,clband)={n_guard1}  +guard2(tan>{TAN_NORM_MIN})={n_final}")
    print(f"  rejected-reason hist (active nodes dropped by guards): {rej_hist}")
    print(f"  residual on final: mean={np.mean(res_a):+.4f}  |mean|={np.mean(np.abs(res_a)):.4f}"
          f"  p95|.|={np.percentile(np.abs(res_a),95):.4f}")
    print(f"  |t_CL| on final:   mean={np.mean(tnm_a):.4f}  min={np.min(tnm_a):.4f}"
          f"  max={np.max(tnm_a):.4f}")
    print(f"  base drive (sign(R)*t.e_r, coeff-free):")
    print(f"     mean={s_base['mean']:+.4g}  median={s_base['median']:+.4g}"
          f"  p10={s_base['p10']:+.4g}  p90={s_base['p90']:+.4g}"
          f"  frac>0={s_base['frac_pos']:.3f}  frac<0={s_base['frac_neg']:.3f}"
          f"  n={s_base['n']}")
    print(f"  D_radial @ ForceSign=+1: mean={d_pos['mean']:+.4g}  frac_outward={d_pos['frac_pos']:.3f}")
    print(f"  D_radial @ ForceSign=-1: mean={d_neg['mean']:+.4g}  frac_outward={d_neg['frac_pos']:.3f}")
    if expected_sign:
        pick = "+1" if (np.sign(s_base["mean"]) == expected_sign) else "-1"
        print(f"  --> physics wants expected_sign={expected_sign:+d}; "
              f"base mean sign = {int(np.sign(s_base['mean'])):+d}; "
              f"so ForceSign={pick} makes D_radial agree with physics")

    return {
        "case": name,
        "expected_sign": expected_sign,
        "n_active": n_active,
        "n_active_notwall": n_active_notwall,
        "n_guard1": n_guard1,
        "n_final": n_final,
        "rej_hist_dropped_active": rej_hist,
        "res_mean": float(np.mean(res_a)),
        "res_abs_mean": float(np.mean(np.abs(res_a))),
        "res_abs_p95": float(np.percentile(np.abs(res_a), 95)),
        "tnorm_mean": float(np.mean(tnm_a)),
        "tnorm_min": float(np.min(tnm_a)),
        "base_mean": s_base["mean"], "base_median": s_base["median"],
        "base_p10": s_base["p10"], "base_p90": s_base["p90"],
        "base_frac_pos": s_base["frac_pos"],
        "base_frac_neg": s_base["frac_neg"],
        "force_sign_plus1_mean": d_pos["mean"],
        "force_sign_plus1_frac_outward": d_pos["frac_pos"],
        "force_sign_minus1_mean": d_neg["mean"],
        "force_sign_minus1_frac_outward": d_neg["frac_neg"],
    }

results = {"decoupled": [], "equilibrium": []}

# ---- decoupled: the C1 decision cases ----
# 60->30 expands footprint -> outward (+) ; 120->150 retracts -> inward (-)
exp_map = {"decouple_wall_60to30": +1, "decouple_wall_120to150": -1}
for cd in sorted((ROOT / "decoupled").glob("decouple_wall_*")):
    if cd.name not in exp_map:
        continue
    vtis = sorted(glob.glob(str(cd / "output" / "case_VTK_P00_*.vti")),
                  key=lambda p: int(p.split("_")[-1].split(".")[0]))
    if not vtis:
        print(f"NO vti in {cd}"); continue
    print(f"\n[using last VTI: {Path(vtis[-1]).name}]")
    dims, A = load(vtis[-1])
    r = analyze(f"dec/{cd.name}", dims, A, expected_sign=exp_map[cd.name])
    if r: results["decoupled"].append(r)

# ---- equilibrium: G1 context (residual should be small; drive ambiguous) ----
for cd in sorted((ROOT / "equilibrium").glob("diag_wall_t*")):
    vtis = sorted(glob.glob(str(cd / "output" / "case_VTK_P00_*.vti")),
                  key=lambda p: int(p.split("_")[-1].split(".")[0]))
    if not vtis:
        continue
    dims, A = load(vtis[-1])
    r = analyze(f"eq/{cd.name}", dims, A, expected_sign=None)
    if r: results["equilibrium"].append(r)

# ---- C1 verdict ----
def _sign_ok(c, exp):
    return np.sign(c["base_mean"]) == exp

verdict = {"decoupled_cases": {}, "force_sign_decision": None}
dec = results["decoupled"]
if len(dec) == 2:
    c60 = next(c for c in dec if "60to30" in c["case"])
    c120 = next(c for c in dec if "120to150" in c["case"])
    plus_ok  = _sign_ok(c60, +1) and _sign_ok(c120, -1)  # ForceSign=+1
    minus_ok = (not _sign_ok(c60, +1)) and (not _sign_ok(c120, -1)) and \
               _sign_ok(c60, -1) and _sign_ok(c120, +1)  # ForceSign=-1 flips both
    verdict["decoupled_cases"]["60to30_expected_+1_base_mean"] = c60["base_mean"]
    verdict["decoupled_cases"]["120to150_expected_-1_base_mean"] = c120["base_mean"]
    if plus_ok:
        verdict["force_sign_decision"] = "+1 (DynamicCLForceSign=+1: 60->30 outward AND 120->150 inward)"
    elif minus_ok:
        verdict["force_sign_decision"] = "-1 (DynamicCLForceSign=-1: 60->30 outward AND 120->150 inward)"
    else:
        verdict["force_sign_decision"] = ("AMBIGUOUS: 60->30 base mean sign="
            f"{int(np.sign(c60['base_mean'])):+d}, 120->150 base mean sign="
            f"{int(np.sign(c120['base_mean'])):+d}; inspect frac_outward")

results["verdict"] = verdict

print("\n\n================ C1 VERDOTE ================")
print(json.dumps(verdict, indent=2))
print("============================================")

(OUT / "summary.json").write_text(json.dumps(results, indent=2))
print(f"\nwrote {OUT / 'summary.json'}")
