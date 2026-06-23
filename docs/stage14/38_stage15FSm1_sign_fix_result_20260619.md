# Stage 15C-3 Result — DynamicCLForceSign sign correction (−1) — 2026-06-19

This doc resolves the OPEN ISSUE from doc 37 §4 / doc 36 §5d: the changed-angle
DynamicCL force pushed the obtuse (120->150) case AWAY from target. It was
diagnosed as a SIGN problem, not magnitude, and the fix is a global
`DynamicCLForceSign` flip from +1 to −1. The sign flip is a RUNTIME XML
parameter (no recompile); CosSign=−1 is unaffected.

```text
status_label: exploratory_not_validation
scope: read-only source audit + Mode=2 re-runs on the committed hook binary;
       no source change, no commit pushed. The force is still too weak to
       close the decoupled gate — this doc only closes the SIGN/direction issue.
verdict: SIGN FIX CONFIRMED. Force direction now correct in BOTH acute and
         obtuse regimes. Magnitude gate still open (separate work item).
```

## 0. What was wrong in doc 35 (root cause)

Doc 35 §4 asserted `t_CL` "points radially OUTWARD on the contact-line ring
(verified)". This was never dynamically confirmed. Source audit of
`calcDynamicCLShadow` (Dynamics.c.Rt, stage9 snapshot) shows:

```c
n_i   = gradPhi / |gradPhi|;                 // NOTE: +grad, opposite of paper's n_lg = -grad(phi)
t_CL  = n_i - (n_i . n_w) n_w;  normalized;  // projection of n_i onto the wall plane
F_CL  = ForceSign * Coeff * (sigma/IntWidth) * R_theta * I_cl * t_CL   (capped)
```

`t_CL`'s horizontal direction = the horizontal component of `grad(q)` at the
contact line. Since q=1 inside the droplet and q=0 outside, `grad(q)` at the
contact line points TOWARD the droplet interior = **INWARD**, for BOTH acute
and obtuse regimes (the overhang does not flip it). So doc 35's "outward" was
wrong; `t_CL` is inward in both regimes.

Consequence: `F_CL = ForceSign * R_theta * t_CL` pointed the wrong way under
`ForceSign=+1`:
- acute (R_theta>0, want spread/outward): F along +t_CL = inward  -> WRONG
- obtuse (R_theta<0, want retract/inward): F along -t_CL = outward -> WRONG

The acute failure was masked because the acute case never produced a
measurable dynamic response at any ForceCap tested (force too weak; natural
compact-ghost relaxation dominated). The obtuse case showed it first only
because its |R_theta| (~0.1) and |F_cand| (~2e-6) were larger.

Doc 35's C1 sign vote was performed on the step-4000 over-relaxed state, in
which BOTH regimes have theta_app < target (degenerate), so it could not
distinguish acute from obtuse — exactly the warning in doc 37 step 2.

## 1. Decisive evidence — gate_c1_force_dir.py (read on stage15C2f test VTIs)

Radial projection of (ForceCandidateX, ForceCandidateZ) on DynamicCLActive
nodes at step 500 (force strongest), convention F_parallel>0 = outward/spread:

| case (FS=+1, the old runs) | R_theta | F_parallel mean | frac>0 | desired | verdict |
|---|---|---|---|---|---|
| 60->30 acute   | +0.038 | −3.4e-7 (INWARD)  | 0.435 | outward | WRONG |
| 120->150 obtuse| −0.099 | +6.3e-7 (OUTWARD) | 0.609 | inward  | WRONG |

Both wrong. `t_CL` is inward (confirmed: when R>0, F=+t_CL measured inward).

Sign algebra for the fix (`t_CL` inward, want restoring force toward theta_eq):
- ForceSign=−1, acute R>0: F = −(+)(inward) = OUTWARD (spread, lower theta) OK
- ForceSign=−1, obtuse R<0: F = −(−)(inward) = INWARD (retract, raise theta) OK

=> `DynamicCLForceSign = -1`.

## 2. Re-validation runs (ForceSign=−1, ForceCap=0.2, Coeff=2, Mode=2)

Same committed hook binary, sha256 `f00f8ff7da214f0ecfae215e7ce73c0f08d8c058cbda37fc198dbba228674c69`.
Source commit HEAD `66b5efd` (hook in `47a6d22`). XML: DynamicCLMode=2,
DynamicCLCosSign=−1, DynamicCLForceSign=−1, DynamicCLCoeff=2,
DynamicCLForceCap=0.2 (injected), IntWidth=3, M=0.3, sigma=5e-5.
Run root: `/mnt/usb1t/RUNS/runs/stage15FSm1_revalidate_20260619`.
VTK what-list: all DynamicCL fields present (analyzer read them).

### 2a. t90 equilibrium safety smoke — PASS

theta_app stable 88.24 -> 88.37 deg over 4000 steps (drift +0.13 deg),
|R_theta|~0.029, run_rc=0, no NaN. As expected: at equilibrium R_theta~0 so
F_CL~0 regardless of sign (matches C2f-0's 88.354 deg). The sign flip does
not perturb equilibrium.

### 2b. changed-angle force direction — now CORRECT in both regimes

F_parallel (radial projection of candidate force, active nodes) at step 500:

| case (FS=−1) | R_theta | F_parallel mean | desired | verdict |
|---|---|---|---|---|
| 60->30 acute   | +0.047 | +4.5e-7 (OUTWARD) | outward | OK |
| 120->150 obtuse| −0.103 | −9.4e-7 (INWARD)  | inward  | OK |

Both flipped to the correct direction vs the FS=+1 runs in §1.

The force also behaves as a proper restoring force: in 60->30 it flips sign
(F_parallel goes + -> −) once theta_app crosses below the 30 deg target
(step 2000, theta_app=29.71), pulling theta back up toward 30. Under FS=+1 it
was anti-restoring.

### 2c. changed-angle trajectory — three-sign comparison (step 4000)

| case | target | base (no force) | FS=+1 Coeff=2 | FS=−1 Coeff=2 |
|---|---|---|---|---|
| 60->30  | 30  | 28.01 | 28.00 (weak) | 27.99 (weak; sign-correct restoring, too weak) |
| 120->150| 150 | 144.48 | 144.23 (AWAY from target) | **145.35 (toward target)** |

For 120->150, same magnitude, three sign conditions: only FS=−1 moves toward
the target. The sign blocker is resolved.

## 3. What this does NOT close (honest)

```text
The DIRECTION/SIGN issue (doc 37 OPEN ISSUE) is CLOSED.
The MAGNITUDE gate is still OPEN:
  - 60->30 trajectory is indistinguishable from base (force too weak to
    resist compact-ghost over-relaxation 60 -> ~28).
  - 120->150 reaches 145.35 vs target 150 (correct direction, +0.87 deg
    closer than base, but still 4.65 deg short).
  - Band-averaged |F_cand| ~5e-7..1e-6, well below the cap 3.33e-6, so this
    is NOT cap-limited; I_cl * R_theta itself is small. The next levers are
    Coeff/Cap (now meaningful under the correct sign) and, separately, the
    compact-ghost over-relaxation itself.
```

Do NOT mark validation_passed. Do not promote sphere/cylinder.

## 4. What is now SETTLED (supersedes doc 35 on ForceSign)

```text
DynamicCLCosSign   = -1   (unchanged; angle-reading calibration, independent of force sign)
DynamicCLForceSign = -1   (CORRECTED from doc 35's +1; runtime XML, no recompile)
DynamicCLMode      = 2    (to activate; 1 = shadow, 0 = off)
t_CL points INWARD (toward droplet interior) in both acute and obtuse regimes.
```

## 5. Reproducibility

```text
# generate (ForceSign=-1) + inject cap=0.2, no run:
python3 /home/yuan/stage13_flat_wall_diagnostic_run.py --matrix all \
  --root /mnt/usb1t/RUNS/runs/stage15FSm1_revalidate_20260619 \
  --binary /home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main \
  --dynamic-cl-mode 2 --cos-sign -1.0 --force-sign -1.0 --dynamic-cl-coeff 2 \
  --int-width 3 --mobility 0.3 --iterations 4000 --vtk-period 500 --force
for c in diag_wall_t90 decouple_wall_60to30 decouple_wall_120to150; do
  python3 /home/yuan/inject_forcecap.py <root>/$c/case.xml 0.2
done
# run + analyze:
bash /home/yuan/phase2.sh   # 60->30 on gpu1, 120->150 on gpu2 in parallel
python3 /home/yuan/analyze2.py    # trajectory: theta_app, |R|, F_parallel, NaN
# force-direction diagnostic (single frame):
python3 /home/yuan/gate_c1_force_dir.py <pvti> 48 48 <label>
scripts mirrored locally: repo/scripts/stage13/{gate_c1_force_dir.py, read_cl_traj.py}
```

## 6. Next (NOT done — separate work items)

1. Magnitude sweep under ForceSign=−1 (Coeff/Cap; C2d cap analysis still
   applies). t90 safety smoke before any changed-angle.
2. Investigate compact-ghost over-relaxation (60->28) as a possibly distinct
   cause of the acute under-shoot — may need a BC-level fix, not just force.
3. Only after the flat-wall decoupled gate is quantitatively closed should
   sphere/cylinder gates be revisited.
