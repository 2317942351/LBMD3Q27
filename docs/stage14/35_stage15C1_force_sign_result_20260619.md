# Stage 15C-1 Result — DynamicCLForceSign calibration (RE-RUN on fixed binary) — 2026-06-19

This is the C1 ForceSign decision. It INDEPENDENTLY CONFIRMS the CosSign=-1
calibration already committed in `da9564e` (doc 32_dynamicCL_15b_cos_eq_and_gate_fix)
and adds the ForceSign=+1 derivation that `da9564e` deliberately left untouched
("DynamicCLForceSign untouched" in its message).

```text
status_label: exploratory_not_validation
scope: Mode=1 shadow post-processing on the fixed binary; no source change
verdict: PASS  ->  DynamicCLCosSign = -1,  DynamicCLForceSign = +1
```

## 0. The verification error that forced the re-run (recorded, do not repeat)

```text
old stage15b_shadow_matrix VTI built 2026-06-18 20:15 (pre-fix binary):
   DynamicCLCosEq present but == 0;  DynamicCLThetaEq / WallContextFound /
   BlockedReason NOT in the VTK what-list -> theta_eq NOT resolved.
fixed binary e2a10d0e built 2026-06-19 01:33 (theta_eq resolved from wetting wall):
   cos_eq == cos(theta_eq), all three fix fields present.
=> any C1 read off the 06-18 VTI used R_theta = -cos_app, not the real residual.
   da9564e (06-19 10:51) re-ran on e2a10d0e and got the correct CosSign=-1.
   This doc's re-run (06-19, also on e2a10d0e) independently confirms it and
   extends to ForceSign.
```

Lesson: binary hash + commit + case XML + VTK field list must be bound into one
manifest per run. The runner already writes `binary_sha256`; the field list is
now verified present before interpretation.

## 1. Hard checks (all PASS before any interpretation)

```text
binary sha256 : e2a10d0e82b52d88b366c46d55852ddccf3a9ac5ca79c71339c30ca2fdd38d69
binary mtime  : 2026-06-19 01:33:04  (post-fix)
fields in binary (strings): DynamicCLThetaEq, DynamicCLWallContextFound,
                            DynamicCLBlockedReason  all registered
case XML params: DynamicCLMode=1, sigma=5e-5, IntWidth=3, M=0.3, Coeff=0.02
VTK what-list  : all 23 DynamicCL fields incl. the 3 fix fields
runner_rc      : 0 for both matrices (cs+1, cs-1), 5 cases each = 10 runs
post-run VTI   : all 23 DynamicCL DataArrays present (verified on t30 pvti)
```

## 2. C1-0 sanity: the cos_eq fix WORKS

On the fluid contact line (active & not-wall & clband), cos_eq now matches
cos(theta_eq) to <0.001, and WallContextFound=100% on all active nodes:

| cos_sign | case | target | theta_eq_deg | cos_eq | cos_eq_ref | err | WCF | verdict |
|---|---|---|---|---|---|---|---|---|
| +1 | t30 | 30 | 30.0 | +0.8660 | +0.8660 | 0.000 | 100% | PASS |
| +1 | t90 | 90 | 90.0 | 0.0000 | 0.0000 | 0.000 | 100% | PASS |
| +1 | t150 | 150 | 150.0 | −0.8660 | −0.8660 | 0.000 | 100% | PASS |
| +1 | 60→30 | 30 | 30.0 | +0.8660 | +0.8660 | 0.000 | 100% | PASS |
| +1 | 120→150 | 150 | 150.0 | −0.8660 | −0.8660 | 0.000 | 100% | PASS |
| −1 | (all 5) | … | … | … | … | 0.000 | 100% | PASS |

The fix is confirmed for both CosSign candidates (cos_eq is CosSign-independent;
it only depends on theta_eq from the adjacent wetting wall, which is now found).

## 3. CosSign calibration (gate 4) — RESOLVED = −1

The sign convention is chosen by which value makes the *apparent* contact angle
theta_app relax onto theta_eq. theta_app = arccos(cos_app), cos_app = CosSign·(n_i·n_w):

| case | target | θ_app @ CosSign=+1 | θ_app @ CosSign=−1 | winner |
|---|---|---|---|---|
| t30 | 30 | **156.3** (mirrored) | **23.7** ✓ | −1 |
| t90 | 90 | 91.6 | 88.4 ✓ | −1 (both near) |
| t150 | 150 | **31.4** (mirrored) | **148.6** ✓ | −1 |
| 60→30 | 30 | 152.2 (mirrored) | 27.8 ✓ | −1 |
| 120→150 | 150 | 35.0 (mirrored) | 145.0 ✓ | −1 |

```text
=> DynamicCLCosSign = -1   (this is NOT the code default +1; it must be set in XML)
```

This is the value the user specified in both messages. The withdrawn doc-35 used
+1 and that was the root of its invalid conclusion.

## 4. ForceSign derivation (REAL R_theta, under CosSign=−1)

Device code: `t_CL = normalize(n_i − (n_i·n_w)n_w)`, horizontal, points radially
OUTWARD on the contact-line ring (verified: |t_horiz|=1, |t_y|=0). So +t_CL =
outward (spread). Force: `F_CL = ForceSign·Coeff·scale·R_theta·I_cl·t_CL`.

At step 4000 the droplet has mostly relaxed, so R_theta is small; the *sign* is
what matters. R_theta = cos(theta_eq) − cos(theta_app):

| case | target | cos_eq | cos_app | R_theta | θ_app | desired θ_app motion | FS |
|---|---|---|---|---|---|---|---|
| 60→30 | 30 | +0.866 | +0.883 | **−0.017** | 28.0° | increase (retract, inward) | +1 |
| 120→150 | 150 | −0.866 | −0.814 | **−0.052** | 144.5° | increase (retract, inward) | +1 |
| t30 (eq) | 30 | +0.866 | +0.916 | −0.050 | 23.7° | (small) | — |
| t90 (eq) | 90 | 0.000 | +0.029 | −0.029 | 88.4° | (small) | — |
| t150 (eq) | 150 | −0.866 | −0.850 | −0.016 | 148.2° | (small) | — |

Logic (sign-robust): to move theta_app onto theta_eq, if theta_app<target the
contact line must retract (F along −t_CL) → ForceSign·R_theta<0. Both decoupled
cases give the SAME vote, **ForceSign = +1**, and the rule is symmetric (if a
future run under-shoots so theta_app>target, R_theta>0 and ForceSign=+1 still
gives +t_CL = spread = correct). So the value does not depend on the over-relax.

```text
=> DynamicCLForceSign = +1   (the code default; no change needed)
```

The *value* is the same as the withdrawn doc-35, but the derivation now rests on
REAL R_theta and the correct CosSign. The old conclusion was right by accident;
this one is right for the right reason.

## 5. What this does NOT settle (honest)

- The decoupled R_theta are SMALL because the droplet over-relaxes by step 4000
  (theta_app < target in both cases). This is consistent with the separate t150
  static-drift issue (doc 32) — the dynamic CL residual is near-zero at the
  sampled time. A C1 with a SHORTER run (e.g. step 500–1000, before relaxation)
  would give larger R_theta and a sharper sign read; the sign vote would not
  change, but the confidence margin would be larger. Not required for C1 PASS.
- ForceSign is calibrated on a FLAT wall. Curved-wall t_CL orientation is a
  separate question for later stages.
- This is Mode=1 shadow. No force has been added to F_total yet. The real
  end-to-end sign check is the C2 equilibrium-t90-no-motion regression.

## 6. Reproducibility

```text
# server (yuan@192.168.1.16), fixed binary:
python3 /home/yuan/stage13_flat_wall_diagnostic_run.py --matrix all \
  --root /mnt/usb1t/RUNS/runs/stage15c1_shadow_cs_minus1 \
  --binary /home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main \
  --iterations 4000 --vtk-period 2000 --dynamic-cl-mode 1 \
  --cos-sign -1.0 --force-sign 1.0 --dynamic-cl-coeff 0.02 --run --force
python3 /home/yuan/stage15c1_rerun_analysis.py     # sanity + both-cos-sign tables
python3 /home/yuan/stage15c1_final_force_sign.py   # final ForceSign table (cs=-1)
# outputs: /home/yuan/stage15c1_rerun_analysis/summary.json, /home/yuan/stage15c1_final/summary.json
# scripts mirrored locally: lbm2026/scripts/stage13/stage15c1_{rerun_analysis,final_force_sign}.py
```

## 7. C1 verdict

```text
PASS.
  - cos_eq fix confirmed (cos_eq == cos(theta_eq), WallContextFound 100%).
  - DynamicCLCosSign = -1   (calibrated by gate-4: theta_app matches target).
  - DynamicCLForceSign = +1 (drives theta_app -> theta_eq under CosSign=-1).
  - equilibrium |R_theta| < 0.05 (vanishes at eq, by construction).
```

## 8. Next (NOT done — pending user authorisation)

C2-pre: prepare the minimal Dynamics.c.Rt diff that adds the `if (DynamicCLMode
> 1.5) F_total += F_cl` hook in BOTH CollisionMRT and BGK force-iteration blocks,
shadow-only at Mode=1, no PhaseF/gradPhi/mu/WallGhost edits, cap preserved, no
double scaling. Diff-only review; no compile, no run, no commit. Then, on
approval: C2a coeff=0 regression (t90 must not move) before any nonzero coeff.
